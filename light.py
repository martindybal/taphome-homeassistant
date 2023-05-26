"""TapHome light integration."""
from __future__ import annotations

import typing

from homeassistant.components.light import (
    ATTR_BRIGHTNESS,
    ATTR_COLOR_TEMP_KELVIN,
    ATTR_HS_COLOR,
    DOMAIN,
    SUPPORT_BRIGHTNESS,
    SUPPORT_COLOR,
    SUPPORT_COLOR_TEMP,
    LightEntity,
)
from homeassistant.const import CONF_LIGHTS
from homeassistant.core import HomeAssistant

from .add_entry_request import AddEntryRequest
from .const import TAPHOME_PLATFORM
from .coordinator import *
from .taphome_entity import *
from .taphome_sdk import *


class TapHomeLight(TapHomeEntity[LightState], LightEntity):
    """Representation of an light"""

    def __init__(
        self,
        hass: HomeAssistant,
        core_config: TapHomeCoreConfigEntry,
        config_entry: TapHomeConfigEntry,
        coordinator: TapHomeDataUpdateCoordinator,
        light_service: LightService,
    ):
        super().__init__(
            hass, core_config, config_entry, DOMAIN, coordinator, LightState
        )
        self.light_service = light_service
        self._supported_features = None
        self._supported_features = None

    @property
    def supported_features(self):
        """Flag supported features."""
        if self._supported_features is None and self.taphome_state is None:
            return 0

        if self._supported_features is None:
            self._supported_features = 0

            if self.taphome_state.brightness is not None:
                self._supported_features = self._supported_features | SUPPORT_BRIGHTNESS

            if self.taphome_state.color_temperature is not None:
                self._supported_features = self._supported_features | SUPPORT_COLOR_TEMP

            if self.taphome_state.hue is not None:
                self._supported_features = self._supported_features | SUPPORT_COLOR

        return self._supported_features

    @property
    def is_on(self):
        """Returns if the light entity is on or not."""
        if not self.taphome_state is None:
            return self.taphome_state.switch_state == SwitchStates.ON

    @property
    def brightness(self):
        """Return the brightness of this light between 0..255."""
        if not self.taphome_state is None:
            return TapHomeEntity.convert_taphome_byte_to_ha(
                self.taphome_state.brightness
            )

    @property
    def color_temp_kelvin(self) -> int | None:
        """Return the CT color value in Kelvin."""
        if not self.taphome_state is None:
            return self.taphome_state.color_temperature

    @property
    def min_color_temp_kelvin(self) -> int:
        """Return the warmest color_temp_kelvin that this light supports."""
        if not self.taphome_device is None:
            return self.taphome_device.supported_values[
                ValueType.CorrelatedColorTemperature
            ].min_value

    @property
    def max_color_temp_kelvin(self) -> int:
        """Return the coldest color_temp_kelvin that this light supports."""
        if not self.taphome_device is None:
            return self.taphome_device.supported_values[
                ValueType.CorrelatedColorTemperature
            ].max_value

    @property
    def hs_color(self):
        """Return the hs color value."""
        if not self.taphome_state is None:
            saturation = TapHomeEntity.convert_taphome_percentage_to_ha(
                self.taphome_state.saturation
            )
            return (self.taphome_state.hue, saturation)

    async def async_turn_on(self, **kwargs):
        """Turn device on."""
        brightness = None
        if ATTR_BRIGHTNESS in kwargs:
            brightness = TapHomeEntity.convert_ha_byte_to_taphome(
                kwargs[ATTR_BRIGHTNESS]
            )

        color_temp = None
        if ATTR_COLOR_TEMP_KELVIN in kwargs:
            color_temp = kwargs[ATTR_COLOR_TEMP_KELVIN]

        hue, saturation = None, None
        if ATTR_HS_COLOR in kwargs:
            (hue, saturation) = kwargs[ATTR_HS_COLOR]
            saturation = TapHomeEntity.convert_ha_percentage_to_taphome(saturation)

        async with UpdateTapHomeState(self) as state:
            await self.light_service.async_turn_on(
                self.taphome_device, brightness, color_temp, hue, saturation
            )
            if brightness or (brightness is color_temp is hue is saturation is None):
                state.switch_state = SwitchStates.ON
            if brightness:
                state.brightness = brightness
            if color_temp:
                state.color_temp = color_temp
            if hue:
                state.hue = hue
            if saturation:
                state.saturation = saturation

    async def async_turn_off(self, **kwargs):
        """Turn device off."""
        async with UpdateTapHomeState(self) as state:
            await self.light_service.async_turn_off(self.taphome_device)
            state.switch_state = SwitchStates.OFF


def setup_platform(
    hass: HomeAssistant,
    config,
    add_entities,
    discovery_info=None,
) -> None:
    """Set up the light platform."""
    add_entry_requests: typing.List[AddEntryRequest] = hass.data[TAPHOME_PLATFORM][
        CONF_LIGHTS
    ]
    lights = []
    for add_entry_request in add_entry_requests:
        light_service = LightService(add_entry_request.tapHome_api_service)
        light = TapHomeLight(
            hass,
            add_entry_request.core_config,
            add_entry_request.config_entry,
            add_entry_request.coordinator,
            light_service,
        )
        lights.append(light)

    add_entities(lights)
