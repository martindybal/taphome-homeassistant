"""Provides the taphome DataUpdateCoordinator."""

import copy
from datetime import timedelta
import logging
from types import TracebackType
from typing import Generic, TypeVar

from aiohttp import ClientResponseError
from aiohttp.web import Request

from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .const import TAPHOME_PLATFORM
from .taphome_issue_registry import TapHomeIssueRegistry
from .taphome_sdk import Device, TapHomeApiService, TapHomeState

_LOGGER = logging.getLogger(__name__)


class TapHomeDataUpdateCoordinatorDevice:
    """Internal container for device data and listeners."""

    def __init__(self) -> None:
        """Initialize device container."""
        self._taphome_device_change_listeners = []
        self._taphome_state_change_listeners = []
        self._taphome_device = None
        self._taphome_values = None
        self._taphome_state_types = []
        self._taphome_states = {}

    @property
    def taphome_device(self):
        """Return the cached TapHome device."""
        return self._taphome_device

    @taphome_device.setter
    def taphome_device(self, device):
        self._taphome_device = device
        self.invoke_taphome_device_change()

    def attach_taphome_device_change_handler(self, taphome_device_change_handler):
        """Subscribe to device change notifications."""
        self._taphome_device_change_listeners.append(taphome_device_change_handler)

    def invoke_taphome_device_change(self):
        """Notify listeners that device reference has changed."""
        for taphome_device_change_handler in self._taphome_device_change_listeners:
            taphome_device_change_handler()

    @property
    def taphome_values(self):
        """Return the latest values for the device."""
        return self._taphome_values

    @taphome_values.setter
    def taphome_values(self, new_state):
        last_values = self._taphome_values
        self._taphome_values = new_state
        self.update_taphome_states()
        self.invoke_taphome_state_change(last_values)

    def get_state(self, state_type):
        """Return cached state instance of ``state_type``."""
        if state_type not in self._taphome_state_types:
            self._taphome_state_types.append(state_type)

        if state_type not in self._taphome_states:
            self.update_taphome_state(state_type)
        return self._taphome_states[state_type]

    def update_taphome_states(self):
        """Recompute all registered state objects."""
        for state_type in self._taphome_state_types:
            self.update_taphome_state(state_type)

    def update_taphome_state(self, state_type):
        """Refresh cached state of given type from latest values."""
        try:
            state = (
                None if self.taphome_values is None else state_type(self.taphome_values)
            )
        except (ValueError, TypeError, KeyError):
            _LOGGER.exception(
                "Error update_taphome_state for device %s", self.taphome_device.id
            )
            state = None
        self._taphome_states[state_type] = state

    def attach_taphome_state_change_handler(self, taphome_state_change_handler):
        """Subscribe to state change notifications."""
        self._taphome_state_change_listeners.append(taphome_state_change_handler)

    def invoke_taphome_state_change(self, last_values: dict | None = None):
        """Notify state change listeners."""
        for taphome_state_change_handler in self._taphome_state_change_listeners:
            taphome_state_change_handler(last_values)


class TapHomeDataUpdateCoordinator(DataUpdateCoordinator):
    """Class to manage fetching TapHome data."""

    def __init__(
        self,
        hass: HomeAssistant,
        update_interval: int,
        taphome_api_service: TapHomeApiService,
        core_id: str | None,
    ) -> None:
        """Initialize coordinator with API service and polling interval."""
        self.taphome_api_service = taphome_api_service
        self.core_id = core_id
        self._was_devices_discovered = False
        self._devices: dict[int, TapHomeDataUpdateCoordinatorDevice] = {}
        update_interval_timedelta = timedelta(seconds=update_interval)
        self.taphome_issue_registry = TapHomeIssueRegistry(hass, core_id)
        super().__init__(
            hass,
            _LOGGER,
            name=TAPHOME_PLATFORM,
            update_interval=update_interval_timedelta,
        )

    def register_entity(
        self,
        taphome_device_id: int,
        taphome_device_change_handler,
        taphome_state_change_handler,
    ) -> None:
        """Register entity callbacks for a given TapHome device."""
        device = self.get_device_data(taphome_device_id)

        if device is None:
            _LOGGER.error(
                "TapHome register entity failed. Device with id %s has "
                "not been exposed in the TapHome API",
                taphome_device_id,
            )

            self.taphome_issue_registry.create_device_not_exposed_issue(
                taphome_device_id
            )
        else:
            self.taphome_issue_registry.try_delete_device_not_exposed_issue(
                taphome_device_id
            )
            device.attach_taphome_device_change_handler(taphome_device_change_handler)
            device.attach_taphome_state_change_handler(taphome_state_change_handler)
            taphome_device_change_handler()
            taphome_state_change_handler()

    def get_device(self, taphome_device_id: int) -> Device | None:
        """Return TapHome device instance for ``taphome_device_id``."""
        device = self.get_device_data(taphome_device_id)
        if device is None:
            return None
        return device.taphome_device

    def get_state(self, taphome_device_id: int, state_type):
        """Return cached state object for ``taphome_device_id``."""
        device = self.get_device_data(taphome_device_id)
        if device is None:
            return None
        return device.get_state(state_type)

    async def _async_update_data(self):
        """Fetch data from TapHome."""
        try:
            await self.async_discovery_devices()
            await self.async_refresh_all_devices_values()
            self.taphome_issue_registry.try_delete_core_unavailable_issue()
            return self._devices  # noqa: TRY300
        except ClientResponseError as ex:
            if ex.status == 501:
                _LOGGER.error(
                    "Core doesn't support get all devices api endpoint. "
                    "Please update your TapHome Core",
                )
                raise NotImplementedError from ex
            exception_message = (
                f"Invalid response from API: {ex.code} - {ex.request_info.url} "
                f"{ex.message}"
            )
            self._core_unavailable(ex, exception_message)

        except Exception as ex:  # noqa: BLE001
            self._core_unavailable(ex, "TapHome data update failed")

    def _core_unavailable(self, ex, exception_message):
        _LOGGER.error(exception_message)
        self.taphome_issue_registry.create_core_unavailable_issue()
        raise UpdateFailed(exception_message) from ex

    async def async_discovery_devices(self) -> None:
        """Discover devices exposed by the TapHome core."""
        if not self._was_devices_discovered:
            discovery_devices = await self.taphome_api_service.async_discovery_devices()
            if discovery_devices is not None:
                for taphome_device in discovery_devices:
                    device = TapHomeDataUpdateCoordinatorDevice()
                    device.taphome_device = taphome_device
                    self._devices[taphome_device.id] = device
                self._was_devices_discovered = True

    async def async_refresh_all_devices_values(self) -> None:
        """Refresh values for all registered devices."""
        last_all_devices_values = (
            await self.taphome_api_service.async_get_all_devices_values()
        )

        if last_all_devices_values is None:
            for device in self._devices.values():
                device.taphome_values = None
            raise UpdateFailed

        self.update_devices_values(last_all_devices_values, True)

    async def async_handle_webhook(
        self, _hass: HomeAssistant, webhook_id: str, request: Request
    ) -> None:
        """Handle incoming webhook - we will trigger an update poll here."""
        _LOGGER.info("Taphome webhook triggered - webhook_id: %s", webhook_id)
        all_devices_values = await request.json()
        self.update_devices_values(all_devices_values)

    def update_devices_values(self, changed_values: dict, force: bool = False):
        """Update cached values for all devices."""
        for changed_device in changed_values["devices"]:
            device_id = changed_device["deviceId"]
            device_changed_values = changed_device["values"]
            device = self.get_device_data(device_id)
            device_new_values = (
                device_changed_values
                if force
                else self.apply_changes(device, device_changed_values)
            )
            if device.taphome_values != device_new_values:
                device.taphome_values = device_new_values
        self.async_set_updated_data(self._devices)

    def apply_changes(
        self, device: TapHomeDataUpdateCoordinatorDevice, device_changed_values: dict
    ):
        """Merge ``device_changed_values`` into cached values."""
        new_values = copy.deepcopy(device.taphome_values)
        for changed_value in device_changed_values:
            for value_entry in new_values:
                if value_entry["valueTypeId"] == changed_value["valueTypeId"]:
                    value_entry["value"] = changed_value["value"]
                    break

        return new_values

    def get_device_data(
        self, taphome_device_id: int
    ) -> TapHomeDataUpdateCoordinatorDevice | None:
        """Return internal device container for ``taphome_device_id``."""
        if taphome_device_id not in self._devices:
            return None
        return self._devices[taphome_device_id]


StateT = TypeVar("StateT", bound="TapHomeState")


class TapHomeDataUpdateCoordinatorObject(Generic[StateT]):
    """Base mixin that exposes TapHome device and state via a coordinator."""

    def __init__(
        self,
        taphome_device_id: int,
        coordinator: TapHomeDataUpdateCoordinator,
        taphome_state_type,
    ) -> None:
        """Bind TapHome device and coordinator together."""
        self._taphome_device_id = taphome_device_id
        self._taphome_state_type = taphome_state_type
        self.coordinator = coordinator

        coordinator.register_entity(
            taphome_device_id,
            self.handle_taphome_device_change,
            self.handle_taphome_values_change,
        )

    @property
    def taphome_state(self) -> StateT | None:
        """Return the latest state for this device."""
        return self.coordinator.get_state(
            self._taphome_device_id, self._taphome_state_type
        )

    @property
    def taphome_device(self) -> Device:
        """Return the TapHome device representation."""
        return self.coordinator.get_device(self._taphome_device_id)

    @callback
    def handle_taphome_device_change(self) -> None:
        """Handle taphome_device change."""

    @callback
    def handle_taphome_values_change(self, last_values: dict | None = None) -> None:
        """Handle change when taphome_values is updated."""
        last_state = (
            None if last_values is None else self._taphome_state_type(last_values)
        )
        self.handle_taphome_state_change(last_state)

    @callback
    def handle_taphome_state_change(self, last_state: StateT | None) -> None:
        """Handle changes when taphome_state is updated."""


class UpdateTapHomeState(Generic[StateT]):
    """Context manager for temporarily storing last TapHome state."""

    def __init__(
        self, coordinator_object: TapHomeDataUpdateCoordinatorObject[StateT]
    ) -> None:
        """Initialize context with reference to coordinator object."""
        self._coordinator_object = coordinator_object
        self._last_state: StateT

    async def __aenter__(self):
        """Return current state and store it for later comparison."""
        self._last_state = self._coordinator_object.taphome_state
        return self._last_state

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: TracebackType | None,
    ) -> None:
        """Invoke state change handler on successful exit."""
        if exc_type is None:
            self._coordinator_object.handle_taphome_state_change(self._last_state)
