"""Provides the taphome DataUpdateCoordinator."""
# from .switch import TapHomeSwitch
import logging
from datetime import timedelta
from typing import List

from aiohttp.client_reqrep import ClientResponseError
from async_timeout import timeout
from homeassistant.helpers.entity import Entity
from homeassistant.helpers.update_coordinator import (ConfigEntryAuthFailed,
                                                      DataUpdateCoordinator,
                                                      UpdateFailed)
from voluptuous.schema_builder import Undefined

from .const import DOMAIN
from .taphome_sdk import *

_LOGGER = logging.getLogger(__name__)


class TapHomeDataUpdateCoordinatorDevice:
    def __init__(self):
        self._ha_entity = None
        self._taphome_device = None
        self._taphome_state = None
        self.taphome_state_type = None

    @property
    def ha_entity(self) -> Entity:
        return self._ha_entity

    @ha_entity.setter
    def ha_entity(self, entity: Entity):
        self._ha_entity = entity
        self._schedule_update_ha_state()

    @property
    def taphome_device(self):
        return self._taphome_device

    @taphome_device.setter
    def taphome_device(self, device):
        self._taphome_device = device
        self._schedule_update_ha_state()

    @property
    def taphome_state(self):
        return self._taphome_state

    @taphome_state.setter
    def taphome_state(self, new_state):
        self._taphome_state = new_state
        self._schedule_update_ha_state()

    def _schedule_update_ha_state(self) -> None:
        if self.ha_entity is not None and self.ha_entity.hass is not None:
            self.ha_entity.schedule_update_ha_state()


class TapHomeDataUpdateCoordinator(DataUpdateCoordinator):
    """Class to manage fetching TapHome data."""

    def __init__(
        self, hass, update_interval: int, taphome_api_service: TapHomeApiService
    ):
        """Initialize global TapHome data updater."""
        self.taphome_api_service = taphome_api_service
        self._was_devices_discovered = False
        self.last_update_devices_values_timestamp = 0
        self._devices = {}
        update_interval = timedelta(seconds=update_interval)
        super().__init__(hass, _LOGGER, name=DOMAIN, update_interval=update_interval)

    def register_entity(
        self, taphome_device_id: int, ha_entity: Entity, taphome_state_type
    ) -> None:
        device = self.get_device_data(taphome_device_id)
        device.ha_entity = ha_entity
        device.taphome_state_type = taphome_state_type

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
            await self.async_update_devices_values()
            return self._devices
        except Exception as ex:
            exception_info = ""
            _LOGGER.warning(ex.__class__.__name__)
            if isinstance(ex, ClientResponseError):
                if ex.status == 501:
                    raise NotImplementedError()  # NotImplementedError is reraised to fail integration loading
                else:
                    exception_info = f"{ex.code} - {ex.request_info.url} {ex.message}"
            # raise
            raise UpdateFailed(f"Invalid response from API: {exception_info}") from ex

    async def async_discovery_devices(self) -> None:
        if not self._was_devices_discovered:
            discovery_devices = await self.taphome_api_service.async_discovery_devices()
            if discovery_devices is not None:
                for taphome_device in discovery_devices:
                    device = self.get_device_data(taphome_device.id)
                    device.taphome_device = taphome_device
                self._was_devices_discovered = True

    async def async_update_devices_values(self) -> None:
        all_devices_values = (
            await self.taphome_api_service.async_get_all_devices_values()
        )
        if all_devices_values is not None:
            if (
                self.last_update_devices_values_timestamp
                < all_devices_values["timestamp"]
            ):
                self.last_update_devices_values_timestamp = all_devices_values[
                    "timestamp"
                ]

                for device_value in all_devices_values["devices"]:
                    device = self.get_device_data(device_value["deviceId"])

                    if device.taphome_state_type is not None:
                        current_state = device.taphome_state_type(
                            device_value["values"]
                        )
                        if not device.taphome_state == current_state:
                            device.taphome_state = current_state

        else:
            for device_id in self._devices:
                self._devices[device_id].taphome_state = None

    def get_device_data(
        self, taphome_device_id: int
    ) -> TapHomeDataUpdateCoordinatorDevice:
        if not taphome_device_id in self._devices:
            self._devices[taphome_device_id] = TapHomeDataUpdateCoordinatorDevice()
        return self._devices[taphome_device_id]
