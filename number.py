"""TapHome number integration."""

from __future__ import annotations

from homeassistant.components.number import DOMAIN as NUMBER_DOMAIN, NumberEntity
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import (
    AddEntitiesCallback,
    ConfigType,
    DiscoveryInfoType,
)

from .add_entry_request import add_taphome_entities
from .const import CONF_NUMBERS
from .taphome_config_entry import AddEntryRequest, TapHomeEntityConfig
from .taphome_entity import TapHomeEntity
from .taphome_sdk import ValueType, VariableDevice, VariableState


class TapHomeNumber(TapHomeEntity, NumberEntity):
    """Representation of a TapHome number entity."""

    def __init__(self, config: AddEntryRequest[TapHomeEntityConfig]) -> None:
        """Initialize TapHome number entity."""
        self._variable = config.hub.get_typed_device(
            config.entity.id, VariableDevice
        )
        self._variable.state.changed += self._on_variable_state_change

        supported_value = self._variable.supported_values.get(
            ValueType.VARIABLE_STATE
        )
        if supported_value is not None:
            if supported_value.min_value is not None:
                self._attr_native_min_value = float(supported_value.min_value)
            if supported_value.max_value is not None:
                self._attr_native_max_value = float(supported_value.max_value)

        super().__init__(config, self._variable, NUMBER_DOMAIN)

    def _on_variable_state_change(
        self,
        _: VariableState | None,
        current_state: VariableState,
    ) -> None:
        """Handle variable state change."""
        self._attr_native_value = current_state.value

    async def async_set_native_value(self, value: float) -> None:
        """Set new value."""
        await self._variable.async_set_value(value)


def setup_platform(
    hass: HomeAssistant,
    config: ConfigType,
    add_entities: AddEntitiesCallback,
    discovery_info: DiscoveryInfoType | None = None,
) -> None:
    """Set up the number platform."""
    add_taphome_entities(hass, add_entities, CONF_NUMBERS, TapHomeNumber)
