"""TapHome valve integration."""

from __future__ import annotations

from taphome_sdk import (
    BidirectionalDeviceState,
    GenericOutputAdapter,
    GenericOutputState,
    PositionState,
)

from homeassistant.components.valve import (
    DOMAIN as VALVE_DOMAIN,
    ValveDeviceClass,
    ValveEntity,
    ValveEntityFeature,
)
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .add_entry_request import add_taphome_entities
from .entity import TapHomeEntity
from .taphome_config_entry import AddEntryRequest, TapHomeEntityConfig
from .taphome_data import TapHomeConfigEntry


class TapHomeValveConfig(TapHomeEntityConfig):
    """Configuration for a TapHome valve device."""

    def __init__(self, device_config: dict) -> None:
        """Store config and extract valve limits."""
        super().__init__(device_config)
        self.device_class: ValveDeviceClass = self.get_optional("device_class", None)


class TapHomeValve(TapHomeEntity, ValveEntity):
    """Representation of an valve."""

    def __init__(self, config: AddEntryRequest[TapHomeValveConfig]) -> None:
        """Initialize TapHome valve entity."""

        self._valve_device = config.hub.get_generic_output_capable_device(
            config.entity.id
        )
        self._valve_generic_output = GenericOutputAdapter(self._valve_device)
        self._valve_generic_output.state_changed += self._on_valve_state_change

        self._attr_reports_position = True
        self._attr_device_class = config.entity.device_class
        self._attr_supported_features = (
            ValveEntityFeature.OPEN | ValveEntityFeature.CLOSE
        )

        if self._valve_generic_output.support_set_output_value():
            self._attr_supported_features |= ValveEntityFeature.SET_POSITION

        super().__init__(config, self._valve_device, VALVE_DOMAIN)

    def _on_valve_state_change(
        self, _: GenericOutputState | None, current_state: GenericOutputState
    ) -> None:
        """Handle valve state change event."""
        self._attr_current_valve_position = self.convert_th_percentage_to_ha(
            current_state.output_value
        )

        match current_state.device_state:
            case BidirectionalDeviceState() as bidirectional_state:
                position_state = bidirectional_state.get_position_state()
                self._attr_is_closed = position_state == PositionState.CLOSED
                self._attr_is_opening = position_state == PositionState.OPENING
                self._attr_is_closing = position_state == PositionState.CLOSING
            case _:
                self._attr_is_closed = not current_state.is_on

    async def async_open_valve(self) -> None:
        """Open the valve."""
        # After turning on, the last value is ignored and 100 % is used.
        # This behaviour is not desired.
        await self._valve_generic_output.async_turn_on()

    async def async_close_valve(self) -> None:
        """Close the valve."""
        await self._valve_generic_output.async_turn_off()

    async def async_set_valve_position(self, position: int) -> None:
        """Move the valve to a specific position."""
        await self._valve_generic_output.async_set_output_value(
            self.convert_ha_percentage_to_th(position)
        )


async def async_setup_entry(
    hass: HomeAssistant,
    entry: TapHomeConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up TapHome valves from a config entry."""
    add_taphome_entities(entry, async_add_entities, VALVE_DOMAIN, TapHomeValve)
