from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryNotReady
from homeassistant.helpers.entity import async_generate_entity_id
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .coordinator import *
from .taphome_core_config_entry import TapHomeCoreConfigEntry
from .taphome_sdk import *


class TapHomeConfigEntry:
    def __init__(self, device_config: dict):
        self._device_config = device_config
        if isinstance(device_config, int):
            self._id = device_config
        else:
            self._id = self.get_required("id")

        self._unique_id = self.get_optional("unique_id", None)

    @property
    def id(self):
        return self._id

    @property
    def unique_id(self):
        return self._unique_id

    def get_required(self, key: str):
        if isinstance(self._device_config, dict):
            if key in self._device_config:
                return self._device_config[key]
        raise ConfigEntryNotReady()

    def get_optional(self, key: str, default):
        if isinstance(self._device_config, dict):
            if key in self._device_config:
                return self._device_config[key]
        return default


class TapHomeEntity(CoordinatorEntity, TapHomeDataUpdateCoordinatorObject[TState]):
    def __init__(
        self,
        hass: HomeAssistant,
        core_config: TapHomeCoreConfigEntry,
        config: TapHomeConfigEntry,
        unique_id_determination: str,
        coordinator: TapHomeDataUpdateCoordinator,
        taphome_state_type,
    ):
        self._taphome_device_id = config.id

        if config.unique_id == None:
            unique_id_core_id = (
                f".{core_config.id}" if core_config.id is not None else ""
            )
            self._unique_id = f"taphome{unique_id_core_id}.{unique_id_determination}.{self._taphome_device_id}".lower()
        else:
            self._unique_id = config.unique_id

        self._core_config = core_config

        TapHomeDataUpdateCoordinatorObject.__init__(
            self, self._taphome_device_id, coordinator, taphome_state_type
        )
        CoordinatorEntity.__init__(self, coordinator)

        if (
            self._core_config.use_description_as_entity_id
            and self.taphome_device is not None
        ):
            ENTITY_ID_FORMAT = unique_id_determination + ".{}"
            self.entity_id = async_generate_entity_id(
                ENTITY_ID_FORMAT, self.taphome_device.description, hass=hass
            )

    def _handle_coordinator_update(self) -> None:
        """Handle updated data from the coordinator. Coordinator call schedule_update_ha_state when is needed"""

    @callback
    def handle_taphome_state_change(self) -> None:
        if self.hass is not None:  # chack if entity was added to hass
            self.schedule_update_ha_state()

    @property
    def unique_id(self):
        return self._unique_id

    @property
    def available(self):
        return not self.taphome_state is None and not self.taphome_device is None

    @property
    def name(self):
        if not self.taphome_device is None:
            if self._core_config.use_description_as_name:
                return self.taphome_device.description
            return self.taphome_device.name

    @staticmethod
    def convert_taphome_byte_to_ha(value: int):
        """Convert 0..1 to 0..255 scale."""
        if value is None:
            return None
        return value * 255

    @staticmethod
    def convert_ha_byte_to_taphome(value: int):
        """Convert 0..255 to 0..1 scale."""
        if value is None:
            return None
        return max(1, round((value / 255) * 100)) / 100

    @staticmethod
    def convert_taphome_percentage_to_ha(value: int):
        """Convert 0..1 to 0..100 scale."""
        if value is None:
            return None
        return value * 100

    @staticmethod
    def convert_ha_percentage_to_taphome(value: int):
        """Convert 0..100 to 0..1 scale."""
        if value is None:
            return None
        return value / 100

    @staticmethod
    def convert_taphome_bool_to_ha(value: int):
        if value == 1:
            return True
        elif value == 0:
            return False
        else:
            return None
