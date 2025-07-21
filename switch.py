"""TapHome switch integration."""

from typing import Any

from homeassistant.components.switch import DOMAIN as SWITCH_DOMAIN, SwitchEntity
from homeassistant.const import CONF_SWITCHES
from homeassistant.core import HomeAssistant, callback

from .add_entry_request import AddEntryRequest
from .const import TAPHOME_PLATFORM
from .coordinator import UpdateTapHomeState
from .taphome_entity import (
    TapHomeConfigEntry,
    TapHomeCoreConfigEntry,
    TapHomeDataUpdateCoordinator,
    TapHomeEntity,
)
from .taphome_sdk import SwitchService, SwitchState, SwitchStates


class SwitchConfigEntry(TapHomeConfigEntry):
    """Configuration for TapHome switch device."""

    def __init__(self, device_config: dict) -> None:
        """Initialize switch config entry."""
        super().__init__(device_config)
        self._device_class = self.get_optional("device_class", None)

    @property
    def device_class(self):
        """Return Home Assistant switch device class if configured."""
        return self._device_class


class TapHomeSwitch(TapHomeEntity[SwitchState], SwitchEntity):
    """Representation of an switch."""

    def __init__(
        self,
        hass: HomeAssistant,
        core_config: TapHomeCoreConfigEntry,
        config_entry: SwitchConfigEntry,
        coordinator: TapHomeDataUpdateCoordinator,
        switch_service: SwitchService,
    ) -> None:
        """Initialize TapHome switch entity."""
        super().__init__(
            hass, core_config, config_entry, SWITCH_DOMAIN, coordinator, SwitchState
        )
        self.switch_service = switch_service
        self._attr_device_class = config_entry.device_class

    @callback
    def handle_taphome_state_change(self, last_state: SwitchState | None) -> None:
        """Update state of entity."""
        if self.taphome_state is None:
            self._attr_is_on = None
        else:
            self._attr_is_on = self.taphome_state.switch_state == SwitchStates.ON

        super().handle_taphome_state_change(last_state)

    async def async_turn_on(self, **kwargs: Any) -> None:
        """Turn device on."""
        await self.async_turn(SwitchStates.ON)

    async def async_turn_off(self, **kwargs: Any) -> None:
        """Turn device off."""
        await self.async_turn(SwitchStates.OFF)

    async def async_turn(self, switch_state: SwitchStates):
        """Change the switch state on the TapHome device."""
        async with UpdateTapHomeState(self) as state:
            await self.switch_service.async_turn(switch_state, self.taphome_device)
            state.switch_state = switch_state


def setup_platform(
    hass: HomeAssistant,
    config,
    add_entities,
    discovery_info=None,
) -> None:
    """Set up the switch platform."""
    add_entry_requests: list[AddEntryRequest[SwitchConfigEntry]] = hass.data[
        TAPHOME_PLATFORM
    ][CONF_SWITCHES]
    switches = []
    for add_entry_request in add_entry_requests:
        switch_service = SwitchService(add_entry_request.taphome_api_service)
        switch = TapHomeSwitch(
            hass,
            add_entry_request.core_config,
            add_entry_request.config_entry,
            add_entry_request.coordinator,
            switch_service,
        )
        switches.append(switch)

    add_entities(switches)
