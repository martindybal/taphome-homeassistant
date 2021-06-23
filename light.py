"""TapHome light integration."""
import typing

from homeassistant.components.light import (
    LightEntity,
    ATTR_BRIGHTNESS,
    ATTR_HS_COLOR,
    SUPPORT_BRIGHTNESS,
    SUPPORT_COLOR,
)

from homeassistant.const import CONF_LIGHTS
from homeassistant.core import HomeAssistant

from .add_entry_request import AddEntryRequest
from .const import DOMAIN
from .coordinator import TapHomeDataUpdateCoordinator
from .taphome_sdk import *
from .taphome_entity import *


class TapHomeLight(TapHomeEntity, LightEntity):
    """Representation of an light"""

    def __init__(
        self,
        config_entry: TapHomeConfigEntry,
        coordinator: TapHomeDataUpdateCoordinator,
        light_service: LightService,
    ):
        super().__init__(config_entry.id, coordinator, LightState)

        self.light_service = light_service

        self._supported_features = None

    @property
    def supported_features(self):
        """Flag supported features."""
        if self.taphome_state is None:
            return 0

        if self._supported_features is None:
            self._supported_features = 0

            if self.taphome_state.hue is not None:
                self._supported_features = self._supported_features | SUPPORT_COLOR

            if self.taphome_state.brightness is not None:
                self._supported_features = self._supported_features | SUPPORT_BRIGHTNESS

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

        hue, saturation = None, None
        if ATTR_HS_COLOR in kwargs:
            (hue, saturation) = kwargs[ATTR_HS_COLOR]
            saturation = TapHomeEntity.convert_ha_percentage_to_taphome(saturation)

        async with UpdateTapHomeState(self) as state:
            await self.light_service.async_turn_on_light(
                self.taphome_device, brightness, hue, saturation
            )
            state.switch_state = SwitchStates.ON
            if brightness is not None:
                state.brightness = brightness
            if hue is not None:
                state.hue = hue
            if saturation is not None:
                state.saturation = saturation

    async def async_turn_off(self, **kwargs):
        """Turn device off."""
        async with UpdateTapHomeState(self) as state:
            await self.light_service.async_turn_off_light(self.taphome_device)
            state.switch_state = SwitchStates.OFF


def setup_platform(
    hass: HomeAssistant,
    config,
    add_entities,
    discovery_info=None,
) -> None:
    """Set up the light platform."""
    add_entry_requests: typing.List[AddEntryRequest] = hass.data[DOMAIN][CONF_LIGHTS]
    lights = []
    for add_entry_request in add_entry_requests:
        light_service = LightService(add_entry_request.tapHome_api_service)
        light = TapHomeLight(
            add_entry_request.config_entry,
            add_entry_request.coordinator,
            light_service,
        )
        lights.append(light)

    add_entities(lights)