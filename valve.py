"""TapHome valve integration."""
from __future__ import annotations

from homeassistant.components.valve import DOMAIN, ValveEntity, ValveEntityFeature
from homeassistant.core import HomeAssistant

from .add_entry_request import AddEntryRequest
from .const import CONF_VALVE, TAPHOME_PLATFORM
from .coordinator import *
from .taphome_entity import *
from .taphome_sdk import *


class ValveConfigEntry(TapHomeConfigEntry):
    def __init__(self, device_config: dict):
        super().__init__(device_config)
        self._device_class = self.get_optional("device_class", None)

    @property
    def device_class(self):
        return self._device_class


class TapHomeValve(TapHomeEntity[ValveState], ValveEntity):
    """Representation of an valve"""

    def __init__(
        self,
        hass: HomeAssistant,
        core_config: TapHomeCoreConfigEntry,
        config_entry: ValveConfigEntry,
        coordinator: TapHomeDataUpdateCoordinator,
        valve_service: ValveService,
    ):
        super().__init__(
            hass, core_config, config_entry, DOMAIN, coordinator, ValveState
        )
        self.valve_service = valve_service
        self._device_class = config_entry.device_class
        self._attr_supported_features = (
            ValveEntityFeature.OPEN
            | ValveEntityFeature.CLOSE
            | ValveEntityFeature.SET_POSITION
        )

    @property
    def device_class(self):
        """Return the class of this device, from component DEVICE_CLASSES."""
        return self._device_class

    @property
    def reports_position(self) -> bool:
        """Return True if entity reports position, False otherwise."""
        # TapHome always knows state of valve
        return True

    @property
    def current_valve_position(self) -> int | None:
        """Return current position of valve."""
        if not self.taphome_state is None:
            return TapHomeEntity.convert_taphome_percentage_to_ha(
                self.taphome_state.percentage
            )

    async def async_open_valve(self) -> None:
        """For valves that can set position, this method should be left unimplemented and only set_valve_position is required."""
        # this causes a bug / unintended behavior . After switching on, the last value is not used, but 100%

    async def async_close_valve(self) -> None:
        """For valves that can set position, this method should be left unimplemented and only set_valve_position is required."""

    async def async_set_valve_position(self, position: int) -> None:
        """Move the valve to a specific position."""

        position = TapHomeEntity.convert_ha_percentage_to_taphome(position)

        async with UpdateTapHomeState(self) as state:
            await self.valve_service.async_set_percentage(self.taphome_device, position)

            if position is not None:
                state.percentage = position


def setup_platform(
    hass: HomeAssistant,
    config,
    add_entities,
    discovery_info=None,
) -> None:
    """Set up the valve platform."""
    add_entry_requests: list[AddEntryRequest] = hass.data[TAPHOME_PLATFORM][CONF_VALVE]
    valves = []
    for add_entry_request in add_entry_requests:
        valve_service = ValveService(add_entry_request.tapHome_api_service)
        valve = TapHomeValve(
            hass,
            add_entry_request.core_config,
            add_entry_request.config_entry,
            add_entry_request.coordinator,
            valve_service,
        )
        valves.append(valve)

    add_entities(valves)
