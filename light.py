"""TapHome light integration."""
from .taphome_sdk import *

import logging
from homeassistant.components.light import LightEntity

from . import TAPHOME

_LOGGER = logging.getLogger(__name__)


async def async_setup_platform(hass, config, async_add_entities, devices: list):
    tapHome = hass.data[TAPHOME]

    lights = []
    for device in devices:
        light = await async_create_light(tapHome, device)
        lights.append(light)

    async_add_entities(lights)


async def async_create_light(tapHome: TapHome, device: TapHome.TapHomeDevice):
    lightValues = (await tapHome.async_get_device_value(device.deviceId))["values"]
    isLightOn = (
        next(
            lightValue
            for lightValue in lightValues
            if lightValue["valueTypeId"] == TapHome.ValueType.SwitchState.value
        )["value"]
        == TapHome.SwitchState.ON.value
    )
    return SimpleTapHomeLight(tapHome, device.deviceId, device.name, isLightOn)


class SimpleTapHomeLight(LightEntity):
    """Representation of an Light without brightness or color setting."""

    def __init__(self, tapHome: TapHome, deviceId: int, name: str, is_on: bool):
        self._tapHome = tapHome
        self._name = name
        self._deviceId = deviceId
        self._is_on = is_on

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
        result = await self._tapHome.async_turn_on_light(self._deviceId)
        self._is_on = result == TapHome.ValueChangeResult.CHANGED

    async def async_turn_off(self):
        """Turn device off."""
        result = await self._tapHome.async_turn_off_light(self._deviceId)
        self._is_on = not result == TapHome.ValueChangeResult.CHANGED