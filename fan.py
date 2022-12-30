"""TapHome fan integration."""
from __future__ import annotations

from homeassistant.components.fan import DOMAIN, FanEntity, SUPPORT_SET_SPEED

from homeassistant.core import HomeAssistant

from .add_entry_request import AddEntryRequest
from .const import CONF_FAN, TAPHOME_PLATFORM
from .coordinator import *
from .taphome_entity import *
from .taphome_sdk import *

from typing import (
    Any,
    Optional,
)


class TapHomeFan(TapHomeEntity[FanState], FanEntity):
    """Representation of an fan"""

    def __init__(
        self,
        hass: HomeAssistant,
        core_config: TapHomeCoreConfigEntry,
        config_entry: TapHomeConfigEntry,
        coordinator: TapHomeDataUpdateCoordinator,
        fan_service: FanService,
    ):
        super().__init__(hass, core_config, config_entry, DOMAIN, coordinator, FanState)
        self.fan_service = fan_service
        self._attr_supported_features = SUPPORT_SET_SPEED

    @property
    def is_on(self):
        """Returns if the fan entity is on or not."""
        if not self.taphome_state is None:
            return self.taphome_state.switch_state == SwitchStates.ON

    @property
    def percentage(self) -> int | None:
        """Return the current speed."""
        if not self.taphome_state is None:
            return TapHomeEntity.convert_taphome_percentage_to_ha(
                self.taphome_state.percentage
            )

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
    config,
    add_entities,
    discovery_info=None,
) -> None:
    """Set up the fan platform."""
    add_entry_requests: typing.List[AddEntryRequest] = hass.data[TAPHOME_PLATFORM][
        CONF_FAN
    ]
    fans = []
    for add_entry_request in add_entry_requests:
        fan_service = FanService(add_entry_request.tapHome_api_service)
        fan = TapHomeFan(
            hass,
            add_entry_request.core_config,
            add_entry_request.config_entry,
            add_entry_request.coordinator,
            fan_service,
        )
        fans.append(fan)

    add_entities(fans)
