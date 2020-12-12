"""TapHome light integration."""
from voluptuous.schema_builder import Self
from .taphome_sdk import *

import logging
from homeassistant.components.light import (
    LightEntity,
    ATTR_BRIGHTNESS,
    ATTR_HS_COLOR,
    SUPPORT_BRIGHTNESS,
    SUPPORT_COLOR,
)
from . import TAPHOME_API_SERVICE

_LOGGER = logging.getLogger(__name__)


async def async_setup_platform(hass, config, async_add_entities, devices: list):
    tapHomeApiService = hass.data[TAPHOME_API_SERVICE]
    lightService = LightService(tapHomeApiService)

    lights = []
    for device in devices:
        light = await async_create_light(lightService, device)
        lights.append(light)

    async_add_entities(lights)


async def async_create_light(lightService: LightService, device: Device):
    light = TapHomeLight(
        lightService, device.deviceId, device.name, device.supportedValues
    )
    await light.async_refresh_state()
    return light


class TapHomeLight(LightEntity):
    """Representation of an Light"""

    def __init__(
        self, lightService: LightService, deviceId: int, name: str, supportedValues
    ):
        self._lightService = lightService
        self._name = name
        self._deviceId = deviceId

        self._supported_features = 0
        if ValueType.HueDegrees in supportedValues:
            self._supported_features = self._supported_features | SUPPORT_COLOR

        if ValueType.HueBrightness in supportedValues:
            self._supported_features = self._supported_features | SUPPORT_BRIGHTNESS

        self._state = None

    @property
    def supported_features(self):
        """Flag supported features."""
        return self._supported_features

    @property
    def name(self):
        """Return the name of the light."""
        return self._name

    @property
    def is_on(self):
        """Returns if the light entity is on or not."""
        return self._state[ValueType.SwitchState] == SwitchState.ON

    @property
    def brightness(self):
        """Return the brightness of this light between 0..255."""
        """Convert taphome 0..1 brightness to hass 0..255 scale."""
        return self._state[ValueType.HueBrightness] * 255

    @property
    def hs_color(self):
        """Return the hs color value."""
        hue = self._state[ValueType.HueDegrees]
        saturation = self._state[ValueType.Saturation] * 100
        return (hue, saturation)

    async def async_turn_on(self, **kwargs):
        """Turn device on."""

        brightness = None
        if ATTR_BRIGHTNESS in kwargs:
            brightness = TapHomeLight.hass_to_taphome_brightness(
                kwargs[ATTR_BRIGHTNESS]
            )

        hue, saturation = None, None
        if ATTR_HS_COLOR in kwargs:
            (hue, saturation) = kwargs[ATTR_HS_COLOR]
            saturation = saturation / 100

        result = await self._lightService.async_turn_on_light(
            self._deviceId, brightness, hue, saturation
        )

        if result == ValueChangeResult.FAILED:
            await self.async_refresh_state()
        else:
            self._state[ValueType.SwitchState] = SwitchState.ON
            if brightness is not None:
                self._state[ValueType.HueBrightness] = brightness
            if hue is not None:
                self._state[ValueType.HueDegrees] = hue
            if saturation is not None:
                self._state[ValueType.Saturation] = saturation

    async def async_turn_off(self):
        """Turn device off."""
        result = await self._lightService.async_turn_off_light(self._deviceId)

        if result == ValueChangeResult.FAILED:
            await self.async_refresh_state()
        else:
            self._state[ValueType.SwitchState] = SwitchState.OFF

    # TODO don't use polling. Issue #4
    # https://developers.home-assistant.io/docs/integration_fetching_data/#separate-polling-for-each-individual-entity
    # https://developers.home-assistant.io/docs/core/entity/#polling
    def async_update(self):
        return self.async_refresh_state()

    async def async_refresh_state(self):
        self._state = await self._lightService.async_get_light_state(self._deviceId)

    @staticmethod
    def hass_to_taphome_brightness(value: int):
        """Convert hass brightness 0..255 to taphome 0..1 scale."""
        return max(1, round((value / 255) * 100)) / 100
