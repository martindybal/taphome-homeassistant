"""TapHome number integration."""

from __future__ import annotations

import logging

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
from .taphome_data import TapHomeConfigEntry
from .taphome_entity import TapHomeEntity
from .taphome_sdk import DeviceState, ValueType, VariableDevice, VariableState

_LOGGER = logging.getLogger(__name__)


class TapHomeNumber(TapHomeEntity, NumberEntity):
    """Representation of a TapHome number entity."""

    def __init__(self, config: AddEntryRequest[TapHomeEntityConfig]) -> None:
        """Initialize TapHome number entity."""
        self._variable = config.hub.get_typed_device(config.entity.id, VariableDevice)

        self._read_only = False
        supported_value = self._variable.supported_values.get(ValueType.VARIABLE_STATE)
        if supported_value is not None:
            if supported_value.read_only:
                self._read_only = True
                _LOGGER.info(
                    "TapHome variable %s is read-only; writes will be ignored",
                    self._variable.id,
                )
            if supported_value.min_value is not None:
                self._attr_native_min_value = float(supported_value.min_value)
            if supported_value.max_value is not None:
                self._attr_native_max_value = float(supported_value.max_value)

        super().__init__(config, self._variable, NUMBER_DOMAIN)

    def _state_changed(self, _: DeviceState | None, current_state: DeviceState) -> None:
        """Update native value before HA state is refreshed."""
        if isinstance(current_state, VariableState):
            self._attr_native_value = current_state.value
        super()._state_changed(_, current_state)

    async def async_set_native_value(self, value: float) -> None:
        """Set new value."""
        if self._read_only:
            _LOGGER.warning(
                "Cannot set value for read-only TapHome variable %s",
                self._variable.id,
            )
            return
        await self._variable.async_set_value(value)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: TapHomeConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up TapHome numbers from a config entry."""
    add_taphome_entities(entry, async_add_entities, CONF_NUMBERS, TapHomeNumber)
