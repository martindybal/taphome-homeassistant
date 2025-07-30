"""TapHome fan integration."""

from __future__ import annotations

from typing import Any

from homeassistant.components.fan import (
    DOMAIN as FAN_DOMAIN,
    FanEntity,
    FanEntityFeature,
)
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import (
    AddEntitiesCallback,
    ConfigType,
    DiscoveryInfoType,
)

from .add_entry_request import add_taphome_entities
from .const import CONF_FAN
from .taphome_config_entry import AddEntryRequest, TapHomeEntityConfig
from .taphome_entity import TapHomeEntity
from .taphome_sdk import (
    GenericOutputAdapter,
    GenericOutputState,
    MultiValueSwitchDevice,
    MultiValueSwitchState,
)


class TapHomeFanConfig(TapHomeEntityConfig):
    """Configuration for a TapHome fan device."""

    def __init__(self, device_config: dict) -> None:
        """Store config and extract fan settings."""
        super().__init__(device_config)
        self.preset_mode_id: int | None = self.get_optional("preset_mode_id", None)


class TapHomeFan(TapHomeEntity, FanEntity):
    """Representation of an fan."""

    def __init__(
        self,
        config: AddEntryRequest[TapHomeFanConfig],
    ) -> None:
        """Initialize TapHome fan entity."""
        self._fan_device = config.hub.get_generic_output_capable_device(
            config.entity.id
        )
        self._fan_generic_output = GenericOutputAdapter(self._fan_device)
        self._fan_generic_output.state_changed += self._on_fan_state_change

        self._attr_supported_features = (
            FanEntityFeature.TURN_ON | FanEntityFeature.TURN_OFF
        )

        if self._fan_generic_output.support_set_output_value():
            self._attr_supported_features |= FanEntityFeature.SET_SPEED

        if config.entity.preset_mode_id:
            self._preset_mode_device = config.hub.get_typed_device(
                config.entity.preset_mode_id, MultiValueSwitchDevice
            )
            self._attr_supported_features |= FanEntityFeature.PRESET_MODE
            self._attr_preset_modes = self._preset_mode_device.options
            self._preset_mode_device.state.changed += self._on_preset_mode_change
            self._schedule_update_when_changed(self._preset_mode_device)

        super().__init__(config, self._fan_device, FAN_DOMAIN)

    @property
    # HA 2025.8, FanEntity don't used cached_property
    # The FanEntity assumes
    # self.percentage is not None and self.percentage > 0
    # or self.preset_mode is not None
    def is_on(self) -> bool | None:
        """Return true if the entity is on."""
        return self._attr_is_on

    def _on_fan_state_change(
        self, _: GenericOutputState | None, current_state: GenericOutputState
    ) -> None:
        """Handle fan state change event."""
        self._attr_is_on = current_state.is_on
        self._attr_percentage = self.convert_th_percentage_to_ha(
            current_state.output_value
        )

    def _on_preset_mode_change(
        self, _: MultiValueSwitchState | None, current_state: MultiValueSwitchState
    ) -> None:
        self._attr_preset_mode = self._preset_mode_device.selected_option

    async def async_turn_on(
        self,
        percentage: int | None = None,
        preset_mode: str | None = None,
        **kwargs: Any,
    ) -> None:
        """Turn on the fan."""
        if percentage is not None:
            await self.async_set_percentage(percentage)
        else:
            await self._fan_generic_output.async_turn_on()

        if preset_mode is not None:
            await self.async_set_preset_mode(preset_mode)

    async def async_set_percentage(self, percentage: int) -> None:
        """Set the speed percentage of the fan."""
        await self._fan_generic_output.async_set_output_value(
            self.convert_ha_percentage_to_th(percentage)
        )

    async def async_set_preset_mode(self, preset_mode: str) -> None:
        """Set the preset mode of the fan."""
        if self._preset_mode_device:
            await self._preset_mode_device.async_select_option(preset_mode)

    async def async_turn_off(self, **kwargs: Any) -> None:
        """Turn off the fan."""
        await self._fan_generic_output.async_turn_off()


def setup_platform(
    hass: HomeAssistant,
    config: ConfigType,
    add_entities: AddEntitiesCallback,
    discovery_info: DiscoveryInfoType | None = None,
) -> None:
    """Set up the switch platform."""
    add_taphome_entities(hass, add_entities, CONF_FAN, TapHomeFan)
