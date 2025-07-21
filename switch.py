"""TapHome switch integration."""

from typing import Any

from homeassistant.components.switch import (
    DOMAIN as SWITCH_DOMAIN,
    SwitchDeviceClass,
    SwitchEntity,
)
from homeassistant.const import CONF_SWITCHES
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity_platform import (
    AddEntitiesCallback,
    ConfigType,
    DiscoveryInfoType,
)

from .add_entry_request import add_taphome_entities
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
        self._device_class: SwitchDeviceClass | None = self.get_optional(
            "device_class", None
        )

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
    config: ConfigType,
    add_entities: AddEntitiesCallback,
    discovery_info: DiscoveryInfoType | None = None,
) -> None:
    """Set up the switch platform."""
    add_taphome_entities(
        hass, add_entities, CONF_SWITCHES, SwitchService, TapHomeSwitch
    )
