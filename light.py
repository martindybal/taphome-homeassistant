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
from datetime import timedelta

SCAN_INTERVAL = timedelta(seconds=10)
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
    light = TapHomeLight(lightService, device)
    await light.async_refresh_state()
    return light


class TapHomeLight(LightEntity):
    """Representation of an Light"""

    def __init__(self, lightService: LightService, device: Device):
        self._lightService = lightService
        self._device = device

        self._is_on = None
        self._brightness = None
        self._hue = None
        self._saturation = None

        self._supported_features = 0
        print(device.supportedValues)
        if ValueType.HueDegrees in device.supportedValues:
            self._supported_features = self._supported_features | SUPPORT_COLOR

        if (
            ValueType.HueBrightness in device.supportedValues
            or ValueType.AnalogOutputValue in device.supportedValues
        ):
            self._supported_features = self._supported_features | SUPPORT_BRIGHTNESS

    @property
    def supported_features(self):
        """Flag supported features."""
        return self._supported_features

    @property
    def name(self):
        """Return the name of the light."""
        return self._device.name

    @property
    def is_on(self):
        """Returns if the light entity is on or not."""
        return self._is_on

    @property
    def brightness(self):
        """Return the brightness of this light between 0..255."""
        """Convert taphome 0..1 brightness to hass 0..255 scale."""
        return self._brightness

    @property
    def hs_color(self):
        """Return the hs color value."""
        return (self._hue, self._saturation)

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
            saturation = TapHomeLight.hass_to_taphome_saturation(saturation)

        result = await self._lightService.async_turn_on_light(
            self._device, brightness, hue, saturation
        )

        if result == ValueChangeResult.FAILED:
            await self.async_refresh_state()
        else:
            self._is_on = True
            if brightness is not None:
                self._brightness = TapHomeLight.taphome_to_hass_brightness(brightness)
            if hue is not None:
                self._hue = hue
            if saturation is not None:
                self._saturation = TapHomeLight.taphome_to_hass_saturation(saturation)

    async def async_turn_off(self):
        """Turn device off."""
        result = await self._lightService.async_turn_off_light(self._device)

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
        state = await self._lightService.async_get_light_state(self._device)
        self._is_on = state.switch_state == SwitchState.ON
        self._brightness = TapHomeLight.taphome_to_hass_brightness(state.brightness)
        self._hue = state.hue
        self._saturation = TapHomeLight.taphome_to_hass_saturation(state.saturation)

    @staticmethod
    def hass_to_taphome_brightness(value: int):
        """Convert hass brightness 0..255 to taphome 0..1 scale."""
        if value is None:
            return None
        return max(1, round((value / 255) * 100)) / 100

    @staticmethod
    def taphome_to_hass_brightness(value: int):
        """Convert taphome 0..1 to hass brightness 0..255 scale."""
        if value is None:
            return None
        return value * 255

    @staticmethod
    def hass_to_taphome_saturation(value: int):
        """Convert hass brightness 0..100 to taphome 0..1 scale."""
        if value is None:
            return None
        return value / 100

    @staticmethod
    def taphome_to_hass_saturation(value: int):
        """Convert taphome 0..1 to hass brightness 0..100 scale."""
        if value is None:
            return None
        return value * 100
