"""Provides the taphome DataUpdateCoordinator."""

# from .switch import TapHomeSwitch
from datetime import timedelta
import logging
from types import TracebackType
from typing import Generic, TypeVar

from aiohttp.client_reqrep import ClientResponseError

from homeassistant.core import callback
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
        self._taphome_state = None
        self.taphome_state_type = None

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
    def taphome_state(self):
        return self._taphome_state

    @taphome_state.setter
    def taphome_state(self, new_state):
        self._taphome_state = new_state
        self.invoke_taphome_state_change()

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
        self._last_all_devices_values = {}
        update_interval = timedelta(seconds=update_interval)
        super().__init__(
            hass, _LOGGER, name=TAPHOME_PLATFORM, update_interval=update_interval
        )

    def register_entity(
        self,
        taphome_device_id: int,
        taphome_state_type,
        taphome_device_change_handler,
        taphome_state_change_handler,
    ) -> None:
        device = self.get_device_data(taphome_device_id)
        device.taphome_state_type = taphome_state_type
        self.restore_last_known_device_state(taphome_device_id)
        device.attach_taphome_device_change_handler(taphome_device_change_handler)
        device.attach_taphome_state_change_handler(taphome_state_change_handler)

    def get_device(self, taphome_device_id: int) -> Device:
        device = self.get_device_data(taphome_device_id)
        return device.taphome_device

    def get_state(self, taphome_device_id: int):
        device = self.get_device_data(taphome_device_id)
        return device.taphome_state

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
                exception_info = f"{ex.code} - {ex.request_info.url} {ex.message}"
                raise UpdateFailed(
                    f"Invalid response from API: {exception_info}"
                ) from ex

        except Exception as ex:
            raise UpdateFailed from ex

    async def async_discovery_devices(self) -> None:
        if not self._was_devices_discovered:
            discovery_devices = await self.taphome_api_service.async_discovery_devices()
            if discovery_devices is not None:
                for taphome_device in discovery_devices:
                    device = self.get_device_data(taphome_device.id)
                    device.taphome_device = taphome_device
                self._was_devices_discovered = True

    async def async_refresh_all_devices_values(self) -> None:
        self._last_all_devices_values = (
            await self.taphome_api_service.async_get_all_devices_values()
        )
        if self._last_all_devices_values is not None:
            self.update_devices_values(self._last_all_devices_values)
        else:
            for device in self._devices.items():
                device.taphome_state = None
            raise UpdateFailed

    def update_devices_values(self, new_values: dict):
        for new_device_value in new_values["devices"]:
            self.update_device_values(new_device_value)
        self.async_set_updated_data(self._devices)

    def restore_last_known_device_state(self, device_id: str):
        for device in self._last_all_devices_values["devices"]:
            if device_id == device["deviceId"]:
                self.update_device_values(device)

    def update_device_values(self, new_device_value):
        new_device_id = new_device_value["deviceId"]
        new_device_values = new_device_value["values"]

        device = self.get_device_data(new_device_id)

        # taphome_state_type je zaregistrován až později, proto zde nic není při prvním loadu
        if device.taphome_state_type is not None:
            current_state = device.taphome_state_type(new_device_values)
            if device.taphome_state != current_state:
                device.taphome_state = current_state

    def get_device_data(
        self, taphome_device_id: int
    ) -> TapHomeDataUpdateCoordinatorDevice:
        if taphome_device_id not in self._devices:
            self._devices[taphome_device_id] = TapHomeDataUpdateCoordinatorDevice()
        return self._devices[taphome_device_id]


class TapHomeDataUpdateCoordinatorObject(Generic[TState]):
    def __init__(
        self,
        taphome_device_id: int,
        coordinator: TapHomeDataUpdateCoordinator,
        taphome_state_type,
    ):
        self._taphome_device_id = taphome_device_id
        self.coordinator = coordinator

        coordinator.register_entity(
            taphome_device_id,
            taphome_state_type,
            self.handle_taphome_device_change,
            self.handle_taphome_state_change,
        )

    @property
    def taphome_state(self) -> TState:
        return self.coordinator.get_state(self._taphome_device_id)

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
