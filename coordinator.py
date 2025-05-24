"""Provides the taphome DataUpdateCoordinator."""

# from .switch import TapHomeSwitch
import copy
import logging
from datetime import timedelta
from types import TracebackType
from typing import Generic, TypeVar

from aiohttp.client_reqrep import ClientResponseError
from aiohttp.web import Request
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .const import TAPHOME_PLATFORM
from .taphome_sdk.taphome_api_service import Device, TapHomeApiService

_LOGGER = logging.getLogger(__name__)


TState = TypeVar("TState")


class TapHomeDataUpdateCoordinatorDevice:
    def __init__(self):
        self._taphome_device_change_listeners = []
        self._taphome_state_change_listeners = []
        self._taphome_device = None
        self._taphome_values = None
        self._taphome_state_types = []
        self._taphome_states = {}

    @property
    def taphome_device(self):
        return self._taphome_device

    @taphome_device.setter
    def taphome_device(self, device):
        self._taphome_device = device
        self.invoke_taphome_device_change()

    def attach_taphome_device_change_handler(self, taphome_device_change_handler):
        self._taphome_device_change_listeners.append(taphome_device_change_handler)

    def invoke_taphome_device_change(self):
        for taphome_device_change_handler in self._taphome_device_change_listeners:
            taphome_device_change_handler()

    @property
    def taphome_values(self):
        return self._taphome_values

    @taphome_values.setter
    def taphome_values(self, new_state):
        self._taphome_values = new_state
        self.update_taphome_states()
        self.invoke_taphome_state_change()

    def get_state(self, state_type):
        if state_type not in self._taphome_state_types:
            self._taphome_state_types.append(state_type)

        if state_type not in self._taphome_states:
            self.update_taphome_state(state_type)
        return self._taphome_states[state_type]

    def update_taphome_states(self):
        for state_type in self._taphome_state_types:
            self.update_taphome_state(state_type)

    def update_taphome_state(self, state_type):
        state = None if self.taphome_values is None else state_type(self.taphome_values)
        self._taphome_states[state_type] = state

    def attach_taphome_state_change_handler(self, taphome_state_change_handler):
        self._taphome_state_change_listeners.append(taphome_state_change_handler)

    def invoke_taphome_state_change(self):
        for taphome_state_change_handler in self._taphome_state_change_listeners:
            taphome_state_change_handler()


class TapHomeDataUpdateCoordinator(DataUpdateCoordinator):
    """Class to manage fetching TapHome data."""

    def __init__(
        self, hass, update_interval: int, taphome_api_service: TapHomeApiService
    ):
        self.taphome_api_service = taphome_api_service
        self._was_devices_discovered = False
        self._devices = {}
        update_interval = timedelta(seconds=update_interval)
        super().__init__(
            hass, _LOGGER, name=TAPHOME_PLATFORM, update_interval=update_interval
        )

    def register_entity(
        self,
        taphome_device_id: int,
        taphome_device_change_handler,
        taphome_state_change_handler,
    ) -> None:
        device = self.get_device_data(taphome_device_id)
        if device is None:
            _LOGGER.error(
                "TapHome register entity failed. Device with id %s has not been exposed in the TapHome API",
                taphome_device_id,
            )
        else:
            device.attach_taphome_device_change_handler(taphome_device_change_handler)
            device.attach_taphome_state_change_handler(taphome_state_change_handler)

    def get_device(self, taphome_device_id: int) -> Device:
        device = self.get_device_data(taphome_device_id)
        if device is None:
            return None
        return device.taphome_device

    def get_state(self, taphome_device_id: int, state_type):
        device = self.get_device_data(taphome_device_id)
        if device is None:
            return None
        return device.get_state(state_type)

    async def _async_update_data(self):
        """Fetch data from TapHome."""
        try:
            await self.async_discovery_devices()
            await self.async_refresh_all_devices_values()
            return self._devices

        except ClientResponseError as ex:
            if ex.status == 501:
                _LOGGER.error(
                    "Core don't support get all devices api endpoint. Please update your TapHome Core"
                )
                raise NotImplementedError  # NotImplementedError is reraised to fail integration loading.
            else:
                exception_message = f"Invalid response from API: {ex.code} - {ex.request_info.url} {ex.message}"
                _LOGGER.error(exception_message)
                raise UpdateFailed(exception_message) from ex

        except Exception as ex:
            _LOGGER.exception("TapHome data update failed")
            raise UpdateFailed from ex

    async def async_discovery_devices(self) -> None:
        if not self._was_devices_discovered:
            discovery_devices = await self.taphome_api_service.async_discovery_devices()
            if discovery_devices is not None:
                for taphome_device in discovery_devices:
                    device = TapHomeDataUpdateCoordinatorDevice()
                    device.taphome_device = taphome_device
                    self._devices[taphome_device.id] = device
                self._was_devices_discovered = True

    async def async_refresh_all_devices_values(self) -> None:
        last_all_devices_values = (
            await self.taphome_api_service.async_get_all_devices_values()
        )
        if last_all_devices_values is not None:
            self.update_devices_values(last_all_devices_values, True)
        else:
            for device in self._devices.items():
                device.taphome_state = None
            raise UpdateFailed

    async def handle_webhook(
        self, hass: HomeAssistant, webhook_id: str, request: Request
    ):
        """Handle incoming webhook - we will trigger an update poll here."""
        _LOGGER.info("Taphome webhook triggered - webhook_id: %s", webhook_id)
        all_devices_values = await request.json()
        self.update_devices_values(all_devices_values)

    def update_devices_values(self, changed_values: dict, force: bool = False):
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
        new_values = copy.deepcopy(device.taphome_values)
        for changed_value in device_changed_values:
            for value_entry in new_values:
                if value_entry["valueTypeId"] == changed_value["valueTypeId"]:
                    value_entry["value"] = changed_value["value"]
                    break

        return new_values

    def get_device_data(
        self, taphome_device_id: int
    ) -> TapHomeDataUpdateCoordinatorDevice:
        if taphome_device_id not in self._devices:
            return None
        return self._devices[taphome_device_id]


class TapHomeDataUpdateCoordinatorObject(Generic[TState]):
    def __init__(
        self,
        taphome_device_id: int,
        coordinator: TapHomeDataUpdateCoordinator,
        taphome_state_type,
    ):
        self._taphome_device_id = taphome_device_id
        self._taphome_state_type = taphome_state_type
        self.coordinator = coordinator

        coordinator.register_entity(
            taphome_device_id,
            self.handle_taphome_device_change,
            self.handle_taphome_state_change,
        )

    @property
    def taphome_state(self) -> TState:
        return self.coordinator.get_state(
            self._taphome_device_id, self._taphome_state_type
        )

    @property
    def taphome_device(self) -> Device:
        return self.coordinator.get_device(self._taphome_device_id)

    @callback
    def handle_taphome_device_change(self) -> None:
        """This method is called when taphome_device is changed."""
        pass

    @callback
    def handle_taphome_state_change(self) -> None:
        """This method is called when taphome_state is changed."""
        pass


class UpdateTapHomeState(object):
    def __init__(self, coordinator_object: TapHomeDataUpdateCoordinatorObject[TState]):
        self._coordinator_object = coordinator_object

    async def __aenter__(self):
        return self._coordinator_object.taphome_state

    async def __aexit__(
        self,
        exc_type: type[BaseException],
        exc_val: BaseException,
        exc_tb: TracebackType,
    ) -> None:
        if exc_type is None:
            self._coordinator_object.handle_taphome_state_change()
