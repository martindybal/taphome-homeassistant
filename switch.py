"""TapHome light integration."""
from voluptuous.schema_builder import Self
from .taphome_sdk import *

import logging
from homeassistant.components.switch import (
    SwitchEntity,
)
from . import TAPHOME_API_SERVICE, TAPHOME_DEVICES
from datetime import timedelta

SCAN_INTERVAL = timedelta(seconds=10)
_LOGGER = logging.getLogger(__name__)


async def async_setup_platform(hass, config, async_add_entities, platformConfig):
    tapHomeApiService = platformConfig[TAPHOME_API_SERVICE]
    devices = platformConfig[TAPHOME_DEVICES]
    switchService = SwitchService(tapHomeApiService)

    switches = []
    for device in devices:
        switch = await async_create_switch(switchService, device)
        switches.append(switch)

    async_add_entities(switches)


async def async_create_switch(switchService: SwitchService, device: Device):
    switch = TapHomeSwitch(switchService, device)
    await switch.async_refresh_state()
    return switch


class TapHomeSwitch(SwitchEntity):
    """Representation of an Switch"""

    def __init__(self, switchService: SwitchService, device: Device):
        self._switchService = switchService
        self._device = device

        self._is_on = None

    @property
    def name(self):
        """Return the name of the switch."""
        return self._device.name

    @property
    def is_on(self):
        """Returns if the switch entity is on or not."""
        return self._is_on

    async def async_turn_on(self, **kwargs):
        """Turn device on."""

        result = await self._switchService.async_turn_on_switch(
            self._device
        )

        if result == ValueChangeResult.FAILED:
            await self.async_refresh_state()
        else:
            self._is_on = True

    async def async_turn_off(self):
        """Turn device off."""
        result = await self._switchService.async_turn_off_switch(self._device)

        if result == ValueChangeResult.FAILED:
            await self.async_refresh_state()
        else:
            self._is_on = False

    # TODO don't use polling. Issue #4
    # https://developers.home-assistant.io/docs/integration_fetching_data/#separate-polling-for-each-individual-entity
    # https://developers.home-assistant.io/docs/core/entity/#polling
    def async_update(self):
        return self.async_refresh_state()

    async def async_refresh_state(self):
        state = await self._switchService.async_get_switch_state(self._device)
        self._is_on = state.switch_state == SwitchStates.ON
