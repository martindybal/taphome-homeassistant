"""Common entity abstractions for the TapHome integration."""

from collections.abc import Callable
from typing import Any

from taphome_sdk import Device, DeviceState, Event, HubConnectionState

from homeassistant.helpers import (
    device_registry as dr,
    entity_registry as er,
    label_registry as lr,
)
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity import Entity, cached_property

from .const import DOMAIN
from .taphome_config_entry import AddEntryRequest, TapHomeEntityConfigT


class TapHomeSubscriptionMixin:
    """Defer SDK event subscriptions to the entity lifecycle.

    Handlers run once at registration time to seed the entity attributes
    (Event.subscribe replays the last value); the permanent subscription
    is made in async_added_to_hass and removed with the entity.
    """

    def _subscribe(self, event: Event, handler: Callable) -> None:
        """Seed the handler now and subscribe when the entity is added."""
        if not hasattr(self, "_pending_subscriptions"):
            self._pending_subscriptions: list[tuple[Event, Callable]] = []
        self._pending_subscriptions.append((event, handler))
        event.subscribe(handler)
        event.unsubscribe(handler)

    async def async_added_to_hass(self) -> None:
        """Activate the recorded subscriptions."""
        await super().async_added_to_hass()  # type: ignore[misc]
        for event, handler in getattr(self, "_pending_subscriptions", []):
            event.subscribe(handler)
            self.async_on_remove(  # type: ignore[attr-defined]
                lambda event=event, handler=handler: event.unsubscribe(handler)
            )


class TapHomeEntity(TapHomeSubscriptionMixin, Entity):
    """Base class for all TapHome entities."""

    _attr_has_entity_name = True

    def __init__(
        self,
        config: AddEntryRequest[TapHomeEntityConfigT],
        taphome_device: Device,
        domain: str,
        unique_id_determination: str = "",
    ) -> None:
        """Initialize shared entity state."""
        super().__init__()
        self._core_config = config.core

        self._attr_available = False
        self._attr_name = None

        self._zone = taphome_device.zone
        self._category = taphome_device.category

        unique_id_core = f".{config.core.id}" if config.core.id is not None else ""
        unique_id_device = (
            f"{domain}.{unique_id_determination}" if unique_id_determination else domain
        )
        self._attr_unique_id = (
            f"taphome{unique_id_core}.{unique_id_device}.{taphome_device.id}".lower()
        )

        location = config.hub.location
        location_id = location.location_id if location else config.core.id or DOMAIN
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, f"{location_id}_{taphome_device.id}")},
            name=taphome_device.name,
            manufacturer="TapHome",
            model=taphome_device.device_type,
            suggested_area=self._zone,
            via_device=(DOMAIN, location_id),
        )

        self._add_state_attributes_if_allowed("taphome_id", taphome_device.id)
        self._add_state_attributes_if_allowed("taphome_name", taphome_device.name)
        self._add_state_attributes_if_allowed(
            "taphome_description", taphome_device.description
        )
        self._add_state_attributes_if_allowed(
            "taphome_category", taphome_device.category
        )
        self._add_state_attributes_if_allowed("taphome_zone", self._zone)

        self._subscribe(
            config.hub.connection_state.changed, self._connection_state_changed
        )
        self._subscribe(taphome_device.state.changed, self._state_changed)

    def _schedule_update_when_changed(self, device: Device) -> None:
        """Refresh the entity state whenever the given device changes."""
        self._subscribe(
            device.state.changed, lambda _, __: self.schedule_update_ha_state()
        )

    async def async_added_to_hass(self) -> None:
        """Subscribe to the SDK events and apply the zone/label mappings."""
        await super().async_added_to_hass()
        self._apply_zone_mapping()
        self._apply_label_mapping()

    def _apply_zone_mapping(self) -> None:
        """Move the device to the area its TapHome zone is mapped to."""
        mapping = self._core_config.zone_mapping
        if mapping is None or self._zone is None:
            return
        area_id = mapping.get(self._zone)
        if area_id is None:
            return
        device_registry = dr.async_get(self.hass)
        device = device_registry.async_get_device(self._attr_device_info["identifiers"])
        if device is not None and device.area_id != area_id:
            device_registry.async_update_device(device.id, area_id=area_id)

    def _apply_label_mapping(self) -> None:
        """Add the label its TapHome category is mapped to."""
        mapping = self._core_config.label_mapping
        if mapping is None or self._category is None:
            return
        label_id = mapping.get(self._category)
        if label_id is None:
            return
        entity_registry = er.async_get(self.hass)
        entry = entity_registry.async_get(self.entity_id)
        if entry is None or lr.async_get(self.hass).async_get_label(label_id) is None:
            return
        entity_registry.async_update_entity(
            self.entity_id, labels=entry.labels | {label_id}
        )

    @cached_property
    def should_poll(self) -> bool:
        """No need to poll. The hub pushes state updates to the entity."""
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
        self.schedule_update_ha_state()

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
