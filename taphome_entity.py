"""Common entity abstractions for the TapHome integration."""

from typing import Any

from homeassistant.helpers import (
    area_registry as ar,
    entity_registry as er,
    label_registry as lr,
)
from homeassistant.helpers.entity import (
    Entity,
    async_generate_entity_id,
    cached_property,
)

from .taphome_config_entry import AddEntryRequest, TapHomeEntityConfigT
from .taphome_sdk import Device, DeviceState, HubConnectionState


class TapHomeEntity(Entity):
    """Base class for all TapHome entities."""

    def __init__(
        self,
        config: AddEntryRequest[TapHomeEntityConfigT],
        taphome_device: Device,
        unique_id_determination: str,
    ) -> None:
        """Initialize shared entity state."""
        super().__init__()
        self._core_config = config.core

        self._attr_available = False

        self._zone = taphome_device.zone
        self._category = taphome_device.category

        if config.entity.unique_id is not None:
            self._attr_unique_id = config.entity.unique_id
        else:
            unique_id_core_id = (
                f".{config.core.id}" if config.core.id is not None else ""
            )
            self._attr_unique_id = f"taphome{unique_id_core_id}.{unique_id_determination}.{taphome_device.id}".lower()

        if config.core.use_description_as_entity_id:
            # Home Assistant 2026.2 enforces strict entity ID validation 
            # Replace dots with underscores to ensure valid entity_id format
            # e.g., "button.PRESS" becomes "button_PRESS.{}" then "button_PRESS.device_name"
            entity_id_format = unique_id_determination.replace('.', '_') + ".{}"
            self.entity_id = async_generate_entity_id(
                entity_id_format,
                taphome_device.description,
                hass=config.hass,
            )

        if config.core.use_description_as_name:
            self._attr_name = taphome_device.description
        else:
            self._attr_name = taphome_device.name

        self._add_state_attributes_if_allowed("taphome_id", taphome_device.id)
        if taphome_device is not None:
            self._add_state_attributes_if_allowed("taphome_name", taphome_device.name)
            self._add_state_attributes_if_allowed(
                "taphome_description", taphome_device.description
            )
            self._add_state_attributes_if_allowed(
                "taphome_category", taphome_device.category
            )
            self._add_state_attributes_if_allowed("taphome_zone", self._zone)

        config.hub.connection_state.changed += self._connection_state_changed
        taphome_device.state.changed += self._state_changed

    async def async_added_to_hass(self) -> None:
        """Run when entity about to be added to hass."""
        await super().async_added_to_hass()
        await self._async_set_area()
        await self._async_set_label()

    async def _async_set_area(self) -> None:
        mapping = self._core_config.zone_mapping
        if mapping is None or self._zone is None or mapping.is_ignored(self._zone):
            return
        area_name = mapping.map(self._zone)
        area_registry = ar.async_get(self.hass)
        entity_registry = er.async_get(self.hass)

        area = area_registry.async_get_area_by_name(area_name)
        if area is None:
            area = area_registry.async_create(area_name)
        entity_registry.async_update_entity(self.entity_id, area_id=area.id)

    async def _async_set_label(self) -> None:
        mapping = self._core_config.label_mapping
        if (
            mapping is None
            or self._category is None
            or mapping.is_ignored(self._category)
        ):
            return

        label_name = mapping.map(self._category)
        label_registry = lr.async_get(self.hass)
        entity_registry = er.async_get(self.hass)

        entry = entity_registry.async_get(self.entity_id)
        if entry is None:
            return

        label = label_registry.async_get_label_by_name(label_name)
        if label is None:
            label = label_registry.async_create(label_name)

        entity_registry.async_update_entity(
            self.entity_id, labels=entry.labels | {label.label_id}
        )

    def _schedule_update_when_changed(self, device):
        device.state.changed += lambda _, __: self.schedule_update_ha_state()

    @cached_property
    def should_poll(self) -> bool:
        """No need to poll. Coordinator notifies entity of updates."""
        return False

    def schedule_update_ha_state(self, force_refresh: bool = False) -> None:
        """Write the state to the state machine."""
        if self.hass is not None:
            super().schedule_update_ha_state(force_refresh)

    def _connection_state_changed(
        self, _: HubConnectionState, current_state: HubConnectionState
    ) -> None:
        """Handle connection state changes."""
        self._attr_available = current_state == HubConnectionState.CONNECTED

    def _state_changed(self, _: DeviceState | None, current_state: DeviceState) -> None:
        self._add_state_attributes_if_allowed(
            "taphome_operation_mode",
            current_state.operation_mode,
            lambda value: value.name.lower(),
        )
        self.schedule_update_ha_state()

    def _add_state_attributes_if_allowed(
        self,
        key: str,
        value: Any,
        value_transform=lambda v: v,
    ) -> None:
        if self._core_config.is_attribute_enabled(key) and value is not None:
            self._add_state_attributes(key, value, value_transform)

    def _add_state_attributes(
        self,
        key: str,
        value: Any,
        value_transform=lambda v: v,
    ):
        if not hasattr(self, "_attr_extra_state_attributes"):
            self._attr_extra_state_attributes = {}
        self._attr_extra_state_attributes[key] = value_transform(value)

    @staticmethod
    def convert_th_percentage_to_ha_byte(value: float | None) -> int | None:
        """Convert 0..1 to 0..255 scale."""
        if value is None:
            return None
        value = max(0.0, min(1.0, value))
        return round(value * 255)

    @staticmethod
    def convert_ha_byte_to_th(value: float | None) -> float | None:
        """Convert 0..255 to 0..1 scale."""
        if value is None:
            return None
        value = max(0.0, min(255, value))
        return round(value / 255, 2)

    @staticmethod
    def convert_th_percentage_to_ha(value: float | None) -> int | None:
        """Convert 0..1 to 0..100 scale."""
        if value is None:
            return None
        value = max(0.0, min(1.0, value))
        return round(value * 100)

    @staticmethod
    def convert_ha_percentage_to_th(value: float) -> float:
        """Convert 0..100 to 0..1 scale."""
        value = max(0, min(100, value))
        return round(value / 100, 2)

    @staticmethod
    def convert_th_bool_to_ha(value: float | None) -> bool | None:
        """Convert 0/1 values to boolean."""
        if value == 1:
            return True
        if value == 0:
            return False
        return None

    @staticmethod
    def invert_th_percentage_to_ha(value: float | None) -> int | None:
        """Invert 0..1 to 0..100 scale."""
        if value is None:
            return None
        value = max(0.0, min(1.0, value))
        return TapHomeEntity.convert_th_percentage_to_ha(1 - value)

    @staticmethod
    def invert_ha_percentage_to_th(value: float | None) -> float | None:
        """Invert 0..100 to 0..1 scale."""
        if value is None:
            return None
        value = max(0, min(100, value))
        return 1 - TapHomeEntity.convert_ha_percentage_to_th(value)
