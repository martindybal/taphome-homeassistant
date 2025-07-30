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
from .coordinator import UpdateTapHomeState
from .taphome_entity import (
    TapHomeConfigEntry,
    TapHomeCoreConfigEntry,
    TapHomeDataUpdateCoordinator,
    TapHomeEntity,
)
from .legacy_taphome_sdk import FanService, FanState, SwitchStates


class TapHomeFan(TapHomeEntity[FanState], FanEntity):
    """Representation of an fan."""

    def __init__(
        self,
        hass: HomeAssistant,
        core_config: TapHomeCoreConfigEntry,
        config_entry: TapHomeConfigEntry,
        coordinator: TapHomeDataUpdateCoordinator,
        fan_service: FanService,
    ) -> None:
        """Initialize TapHome fan entity."""
        super().__init__(
            hass, core_config, config_entry, FAN_DOMAIN, coordinator, FanState
        )
        self.fan_service = fan_service
        self._attr_supported_features = (
            FanEntityFeature.TURN_ON
            | FanEntityFeature.TURN_OFF
            | FanEntityFeature.SET_SPEED
        )

    @property
    def is_on(self):
        """Returns if the fan entity is on or not."""
        if self.taphome_state is not None:
            return self.taphome_state.switch_state == SwitchStates.ON
        return None

    @property
    def percentage(self) -> int | None:
        """Return the current speed."""
        if self.taphome_state is not None:
            return TapHomeEntity.convert_taphome_percentage_to_ha(
                self.taphome_state.percentage
            )
        return None

    async def async_turn_on(
        self,
        percentage: int | None = None,
        preset_mode: str | None = None,
        **kwargs: Any,
    ) -> None:
        """Turn on the fan."""
        async with UpdateTapHomeState(self) as state:
            await self.fan_service.async_turn_on(self.taphome_device)
            state.switch_state = SwitchStates.ON

    async def async_turn_off(self, **kwargs: Any) -> None:
        """Turn the fan off."""
        async with UpdateTapHomeState(self) as state:
            await self.fan_service.async_turn_off(self.taphome_device)
            state.switch_state = SwitchStates.OFF

    async def async_set_percentage(self, percentage: int) -> None:
        """Set the speed percentage of the fan."""
        percentage = TapHomeEntity.convert_ha_percentage_to_taphome(percentage)

        async with UpdateTapHomeState(self) as state:
            await self.fan_service.async_set_percentage(self.taphome_device, percentage)

            if percentage is not None:
                state.percentage = percentage
                state.switch_state = (
                    SwitchStates.OFF if percentage == 0 else SwitchStates.ON
                )


def setup_platform(
    hass: HomeAssistant,
    config: ConfigType,
    add_entities: AddEntitiesCallback,
    discovery_info: DiscoveryInfoType | None = None,
) -> None:
    """Set up the switch platform."""
    add_taphome_entities(hass, add_entities, CONF_FAN, FanService, TapHomeFan)
