"""Provides the taphome DataUpdateCoordinator."""
# from .switch import TapHomeSwitch
from datetime import timedelta
from typing import List
from homeassistant.helpers.entity import Entity
import logging

from async_timeout import timeout
from voluptuous.schema_builder import Undefined

from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .const import DOMAIN
from .taphome_sdk import *

_LOGGER = logging.getLogger(__name__)


class TapHomeDataUpdateCoordinatorDevice:
    taphome_device_id: int
    taphome_device: Device
    ha_entity: Entity

    def __init__(self, taphome_device_id: int):
        self.taphome_device_id = taphome_device_id
        self.taphome_device = None
        self.ha_entity = None
        self.taphome_state = None
        self.taphome_state_type = None


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
            _LOGGER.info(f"Fetch data from TapHome Core")

            await self.async_discovery_devices()

            async with timeout(10):
                await self.async_update_devices_values()

                return self._devices
        except Exception as ex:
            raise  # For development reason
            raise UpdateFailed(f"Invalid response from API: {ex}") from ex

    async def async_discovery_devices(self) -> None:
        if not self._was_devices_discovered:
            for (
                taphome_device
            ) in await self.taphome_api_service.async_discovery_devices():
                device = self.get_device_data(taphome_device.id)
                device.taphome_device = taphome_device
                self.schedule_update_ha_state(device)
            self._was_devices_discovered = True

    async def async_update_devices_values(self) -> None:
        all_devices_values = (
            await self.taphome_api_service.async_get_all_devices_values()
        )

        if self.last_update_devices_values_timestamp < all_devices_values["timestamp"]:
            self.last_update_devices_values_timestamp = all_devices_values["timestamp"]

            for device_value in all_devices_values["devices"]:
                device = self.get_device_data(device_value["deviceId"])

                if device.taphome_state_type is not None:
                    current_state = device.taphome_state_type(device_value["values"])
                    if not device.taphome_state == current_state:
                        device.taphome_state = current_state
                        self.schedule_update_ha_state(device)

    def get_device_data(
        self, taphome_device_id: int
    ) -> TapHomeDataUpdateCoordinatorDevice:
        if not taphome_device_id in self._devices:
            self._devices[taphome_device_id] = TapHomeDataUpdateCoordinatorDevice(
                taphome_device_id
            )
        return self._devices[taphome_device_id]

    def schedule_update_ha_state(
        self, device: TapHomeDataUpdateCoordinatorDevice
    ) -> None:
        if device.ha_entity is not None and device.ha_entity.hass is not None:
            device.ha_entity.schedule_update_ha_state()