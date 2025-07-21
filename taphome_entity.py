"""Common entity abstractions for the TapHome integration."""

from typing import Any, Generic, TypeVar

from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryNotReady
from homeassistant.helpers.entity import async_generate_entity_id, cached_property
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .coordinator import (
    StateT,
    TapHomeDataUpdateCoordinator,
    TapHomeDataUpdateCoordinatorObject,
    callback,
)
from .taphome_core_config_entry import TapHomeCoreConfigEntry
from .taphome_sdk import OperationModes, ValueType


class TapHomeConfigEntry:
    """Wrapper over raw device configuration data."""

    def __init__(self, device_config: dict) -> None:
        """Store device configuration and extract mandatory fields."""
        self._device_config = device_config
        if isinstance(device_config, int):
            self._id = device_config
        else:
            self._id = self.get_required("id")

        self._unique_id = self.get_optional("unique_id", None)

    @property
    def id(self):
        """Return TapHome device identifier."""
        return self._id

    @property
    def unique_id(self):
        """Return Home Assistant unique identifier if defined."""
        return self._unique_id

    def get_required(self, key: str):
        """Return value for ``key`` or raise if missing."""
        if isinstance(self._device_config, dict):
            if key in self._device_config:
                return self._device_config[key]
        raise ConfigEntryNotReady

    def get_optional(self, key: str, default):
        """Return value for ``key`` or ``default`` if not present."""
        if isinstance(self._device_config, dict):
            if key in self._device_config:
                return self._device_config[key]
        return default


class TapHomeEntity(CoordinatorEntity, TapHomeDataUpdateCoordinatorObject[StateT]):
    """Base class for all TapHome entities."""

    def __init__(
        self,
        hass: HomeAssistant,
        core_config: TapHomeCoreConfigEntry,
        config: TapHomeConfigEntry,
        unique_id_determination: str,
        coordinator: TapHomeDataUpdateCoordinator,
        taphome_state_type,
    ) -> None:
        """Initialize shared entity state."""
        self._taphome_device_id = config.id
        self._attr_available = False

        if config.unique_id is None:
            unique_id_core_id = (
                f".{core_config.id}" if core_config.id is not None else ""
            )
            self._attr_unique_id = f"taphome{unique_id_core_id}.{unique_id_determination}.{self._taphome_device_id}".lower()
        else:
            self._attr_unique_id = config.unique_id

        self._core_config = core_config

        TapHomeDataUpdateCoordinatorObject.__init__(
            self, self._taphome_device_id, coordinator, taphome_state_type
        )
        CoordinatorEntity.__init__(self, coordinator)

        if (
            self._core_config.use_description_as_entity_id
            and self.taphome_device is not None
        ):
            entity_id_format = unique_id_determination + ".{}"
            self.entity_id = async_generate_entity_id(
                entity_id_format, self.taphome_device.description, hass=hass
            )

    @cached_property
    def available(self) -> bool:
        """Return True if entity is available."""
        return self._attr_available

    @property
    def operation_mode(self) -> OperationModes | None:
        """Return current operation mode if available."""
        if self.taphome_state is not None:
            operation_mode = self.taphome_state.get_device_enum_value(
                OperationModes, ValueType.OPERATION_MODE
            )
            if operation_mode is not OperationModes.NONE:
                return operation_mode

        return None

    def _handle_coordinator_update(self) -> None:
        """Handle updated data from the coordinator."""

    @callback
    def handle_taphome_device_change(self) -> None:
        """Handle taphome_device change."""
        self._update_available()
        self._update_name()

        self.add_state_attributes("taphome_id", self._taphome_device_id)
        if self.taphome_device is not None:
            self.add_state_attributes("taphome_name", self.taphome_device.name)
            self.add_state_attributes(
                "taphome_description", self.taphome_device.description
            )
            self.add_state_attributes("taphome_category", self.taphome_device.category)
            self.add_state_attributes("taphome_zone", self.taphome_device.zone)
        return super().handle_taphome_device_change()

    @callback
    def handle_taphome_state_change(self, last_state: StateT | None) -> None:
        """Schedule state update when TapHome state changes."""

        self._update_available()

        self.add_state_attributes(
            "taphome_operation_mode",
            self.operation_mode,
            lambda value: value.name.lower(),
        )

        if self.hass is not None:  # check if entity was added to hass
            self.schedule_update_ha_state()

        super().handle_taphome_state_change(last_state)

    def _update_available(self):
        self._attr_available = (
            self.taphome_state is not None and self.taphome_device is not None
        )

    def _update_name(self):
        if self.taphome_device is not None:
            if self._core_config.use_description_as_name:
                self._attr_name = self.taphome_device.description
            else:
                self._attr_name = self.taphome_device.name

    def add_state_attributes(
        self,
        key: str,
        value: Any,
        value_transform=lambda v: v,
    ) -> None:
        """Add state attribute to the attributes dictionary."""
        if value is not None:
            if not hasattr(self, "_attr_extra_state_attributes"):
                self._attr_extra_state_attributes = {}
            self._attr_extra_state_attributes[key] = value_transform(value)

    @staticmethod
    def convert_taphome_byte_to_ha(value: float | None) -> float | None:
        """Convert 0..1 to 0..255 scale."""
        if value is None:
            return None
        return value * 255

    @staticmethod
    def convert_ha_byte_to_taphome(value: float | None) -> float | None:
        """Convert 0..255 to 0..1 scale."""
        if value is None:
            return None
        return max(1, round((value / 255) * 100)) / 100

    @staticmethod
    def convert_taphome_percentage_to_ha(value: float | None) -> float | None:
        """Convert 0..1 to 0..100 scale."""
        if value is None:
            return None
        return value * 100

    @staticmethod
    def convert_ha_percentage_to_taphome(value: float | None) -> float | None:
        """Convert 0..100 to 0..1 scale."""
        if value is None:
            return None
        return value / 100

    @staticmethod
    def convert_taphome_bool_to_ha(value: int | None) -> bool | None:
        """Convert 0/1 values to boolean."""
        if value == 1:
            return True
        if value == 0:
            return False
        return None
