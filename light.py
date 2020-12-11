"""TapHome light integration."""
from .taphome_sdk import *

import logging
from homeassistant.components.light import LightEntity

from . import TAPHOME_HTTP_CLIENT_FACTORY

_LOGGER = logging.getLogger(__name__)


async def async_setup_platform(hass, config, async_add_entities, devices: list):
    tapHomeHttpClient = hass.data[TAPHOME_HTTP_CLIENT_FACTORY]
    lightService = LightService(tapHomeHttpClient)

    lights = []
    for device in devices:
        light = await async_create_light(lightService, device)
        lights.append(light)

    async_add_entities(lights)


async def async_create_light(lightService: LightService, device: Device):
    light = SimpleTapHomeLight(lightService, device.deviceId, device.name)
    await light.async_refresh_state()
    return light


class SimpleTapHomeLight(LightEntity):
    """Representation of an Light without brightness or color setting."""

    def __init__(self, lightService: LightService, deviceId: int, name: str):
        self._lightService = lightService
        self._name = name
        self._deviceId = deviceId
        self._is_on: bool = None

    @property
    def name(self):
        """Return the name of the light."""
        return self._name

    @property
    def is_on(self):
        """Returns if the light entity is on or not."""
        return self._is_on

    async def async_turn_on(self, **kwargs):
        """Turn device on."""
        result = await self._lightService.async_turn_on_light(self._deviceId)

        if result == ValueChangeResult.FAILED:
            await self.async_refresh_state()
        else:
            self._is_on = True

    async def async_turn_off(self):
        """Turn device off."""
        result = await self._lightService.async_turn_off_light(self._deviceId)

        if result == ValueChangeResult.FAILED:
            await self.async_refresh_state()
        else:
            self._is_on = False

    async def async_refresh_state(self):
        state = await self._lightService.async_get_light_state(self._deviceId)
        self._is_on = state[ValueType.SwitchState] == SwitchState.ON