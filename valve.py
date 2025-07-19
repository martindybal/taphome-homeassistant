"""TapHome valve integration."""

from __future__ import annotations

from homeassistant.components.valve import (
    DOMAIN as VALVE_DOMAIN,
    ValveEntity,
    ValveEntityFeature,
)
from homeassistant.core import HomeAssistant

from .add_entry_request import AddEntryRequest
from .const import CONF_VALVE, TAPHOME_PLATFORM
from .coordinator import TapHomeDataUpdateCoordinator, UpdateTapHomeState
from .taphome_entity import TapHomeConfigEntry, TapHomeCoreConfigEntry, TapHomeEntity
from .taphome_sdk import SwitchStates, ValveService, ValveState


class ValveConfigEntry(TapHomeConfigEntry):
    """Configuration options for TapHome valve devices."""

    def __init__(self, device_config: dict) -> None:
        """Initialize valve config entry."""
        super().__init__(device_config)
        self._device_class = self.get_optional("device_class", None)

    @property
    def device_class(self):
        """Return Home Assistant valve device class if configured."""
        return self._device_class


class TapHomeValve(TapHomeEntity[ValveState], ValveEntity):
    """Representation of an valve."""

    def __init__(
        self,
        hass: HomeAssistant,
        core_config: TapHomeCoreConfigEntry,
        config_entry: ValveConfigEntry,
        coordinator: TapHomeDataUpdateCoordinator,
        valve_service: ValveService,
    ) -> None:
        """Initialize TapHome valve entity."""
        super().__init__(
            hass, core_config, config_entry, VALVE_DOMAIN, coordinator, ValveState
        )
        self.valve_service = valve_service
        self._device_class = config_entry.device_class

        self._attr_supported_features = (
            ValveEntityFeature.OPEN | ValveEntityFeature.CLOSE
        )
        if self.valve_service.support_set_position(self.taphome_device):
            self._attr_supported_features = (
                self._attr_supported_features | ValveEntityFeature.SET_POSITION
            )

    @property
    def device_class(self):
        """Return the class of this device, from component DEVICE_CLASSES."""
        return self._device_class

    @property
    def reports_position(self) -> bool:
        """Return True if entity reports position, False otherwise."""
        return self.valve_service.support_set_position(self.taphome_device)

    @property
    def is_closed(self) -> bool | None:
        """Return if the valve is closed or not."""
        if self.taphome_state is not None:
            return self.taphome_state.switch_state == SwitchStates.OFF
        return None

    @property
    def current_valve_position(self) -> int | None:
        """Return current position of valve."""
        if self.taphome_state is not None and self.valve_service.support_set_position(
            self.taphome_device
        ):
            return TapHomeEntity.convert_taphome_percentage_to_ha(
                self.taphome_state.percentage
            )
        return None

    async def async_open_valve(self) -> None:
        """Open the valve if supported."""
        # After turning on, the last value is ignored and 100 % is used.
        # This behaviour is not desired.
        await self.valve_service.async_turn_on(self.taphome_device)

    async def async_close_valve(self) -> None:
        """For valves that can set position, this method should be left unimplemented and only set_valve_position is required."""
        await self.valve_service.async_turn_off(self.taphome_device)

    async def async_set_valve_position(self, position: int) -> None:
        """Move the valve to a specific position."""
        position = TapHomeEntity.convert_ha_percentage_to_taphome(position)

        async with UpdateTapHomeState(self) as state:
            await self.valve_service.async_set_percentage(self.taphome_device, position)

            if position is not None:
                state.percentage = position


def setup_platform(
    hass: HomeAssistant,
    _config,
    add_entities,
    _discovery_info=None,
) -> None:
    """Set up the valve platform."""
    add_entry_requests: list[AddEntryRequest] = hass.data[TAPHOME_PLATFORM][CONF_VALVE]
    valves = []
    for add_entry_request in add_entry_requests:
        valve_service = ValveService(add_entry_request.taphome_api_service)
        valve = TapHomeValve(
            hass,
            add_entry_request.core_config,
            add_entry_request.config_entry,
            add_entry_request.coordinator,
            valve_service,
        )
        valves.append(valve)

    add_entities(valves)
