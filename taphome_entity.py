import copy
from types import TracebackType
from typing import Type

from homeassistant.helpers.update_coordinator import CoordinatorEntity
from homeassistant.exceptions import ConfigEntryNotReady
from .taphome_sdk import *
from .coordinator import TapHomeDataUpdateCoordinator


class TapHomeConfigEntry:
    def __init__(self, device_config: dict):
        if isinstance(device_config, int):
            self._id = device_config
        else:
            self._id = self.get_required(device_config, "id")

    @property
    def id(self):
        return self._id

    def get_required(self, device_config: dict, key: str):
        if isinstance(device_config, dict):
            if key in device_config:
                return device_config[key]
        raise ConfigEntryNotReady()

    def get_optional(self, device_config: dict, key: str, default):
        if isinstance(device_config, dict):
            if key in device_config:
                return device_config[key]
        return default


class TapHomeEntity(CoordinatorEntity):
    def __init__(
        self,
        taphome_device_id: int,
        coordinator: TapHomeDataUpdateCoordinator,
        taphome_state_type,
    ):
        CoordinatorEntity.__init__(self, coordinator)
        coordinator.register_entity(taphome_device_id, self, taphome_state_type)
        self._taphome_device_id = taphome_device_id

    def _handle_coordinator_update(self) -> None:
        """Handle updated data from the coordinator. Coordinator call schedule_update_ha_state when is needed"""

    @property
    def unique_id(self):
        return f"{self.__class__.__name__}.taphome_{self._taphome_device_id}".lower()

    @property
    def available(self):
        return not self.taphome_state is None and not self.taphome_device is None

    @property
    def name(self):
        if not self.taphome_device is None:
            return self.taphome_device.name

    @property
    def taphome_state(self):
        return self.coordinator.get_state(self._taphome_device_id)

    @property
    def taphome_device(self) -> Device:
        return self.coordinator.get_device(self._taphome_device_id)


class UpdateTapHomeState(object):
    def __init__(self, taphome_entity: TapHomeEntity):
        self._taphome_entity = taphome_entity

    async def __aenter__(self):
        return self._taphome_entity.taphome_state

    async def __aexit__(
        self,
        exc_type: Type[BaseException],
        exc_val: BaseException,
        exc_tb: TracebackType,
    ) -> None:
        if exc_type is None:
            self._taphome_entity.schedule_update_ha_state()
