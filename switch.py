"""TapHome switch integration."""

from __future__ import annotations

from typing import Any

from homeassistant.components.switch import (
    DOMAIN as SWITCH_DOMAIN,
    SwitchDeviceClass,
    SwitchEntity,
)
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .add_entry_request import add_taphome_entities
from .taphome_config_entry import AddEntryRequest, TapHomeEntityConfig
from .taphome_data import TapHomeConfigEntry
from .taphome_entity import TapHomeEntity
from taphome_sdk import DigitalOutputDevice, DigitalOutputState


class TapHomeSwitchConfig(TapHomeEntityConfig):
    """Configuration for a TapHome switch device."""

    def __init__(self, device_config: dict) -> None:
        """Store config and extract switch limits."""
        super().__init__(device_config)
        self.device_class: SwitchDeviceClass = self.get_optional("device_class", None)


class TapHomeSwitch(TapHomeEntity, SwitchEntity):
    """Representation of a TapHome switch entity."""

    def __init__(self, config: AddEntryRequest[TapHomeSwitchConfig]) -> None:
        """Initialize TapHome switch entity."""
        self._attr_device_class = config.entity.device_class

        self._switch = config.hub.get_typed_device(
            config.entity.id, DigitalOutputDevice
        )
        self._switch.state.changed += self._on_switch_state_change

        super().__init__(config, self._switch, SWITCH_DOMAIN)

    def _on_switch_state_change(
        self, _: DigitalOutputState | None, current_state: DigitalOutputState
    ) -> None:
        self._attr_is_on = current_state.is_on

    async def async_turn_on(self, **kwargs: Any) -> None:
        """Turn the entity on."""
        await self._switch.async_turn_on()

    async def async_turn_off(self, **kwargs: Any) -> None:
        """Turn the entity off."""
        await self._switch.async_turn_off()


async def async_setup_entry(
    hass: HomeAssistant,
    entry: TapHomeConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up TapHome switches from a config entry."""
    add_taphome_entities(entry, async_add_entities, SWITCH_DOMAIN, TapHomeSwitch)
