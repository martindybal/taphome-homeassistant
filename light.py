"""TapHome light integration."""

from __future__ import annotations

from abc import ABC

from homeassistant.components.light import (
    DOMAIN as LIGHT_DOMAIN,
    ColorMode,
    LightEntity,
    LightEntityFeature,
)
from homeassistant.const import CONF_LIGHTS
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback, ConfigType
from homeassistant.helpers.typing import DiscoveryInfoType

from .add_entry_request import add_taphome_entities
from .taphome_config_entry import AddEntryRequest, TapHomeEntityConfig
from .taphome_entity import TapHomeEntity
from .taphome_sdk import (
    AnalogOutputDevice,
    AnalogOutputState,
    DigitalOutputDevice,
    DigitalOutputState,
    DualWhiteLightDevice,
    DualWhiteLightState,
    MultiValueSwitchDevice,
    MultiValueSwitchState,
    RGBLightDevice,
    RGBLightState,
)


class TapHomeLightConfig(TapHomeEntityConfig):
    """Configuration for a TapHome valve device."""

    def __init__(self, device_config: dict) -> None:
        """Store config and extract valve limits."""
        super().__init__(device_config)
        self.effect_id: int | None = self.get_optional("effect_id", None)


class TapHomeLight(TapHomeEntity, LightEntity, ABC):
    """Representation of an light."""

    def __init__(
        self,
        config: AddEntryRequest[TapHomeLightConfig],
        light: RGBLightDevice
        | DualWhiteLightDevice
        | AnalogOutputDevice
        | DigitalOutputDevice,
    ) -> None:
        """Initialize TapHome light entity."""
        self._light = light
        self._light.state.changed.subscribe(self._on_light_state_change)

        if config.entity.effect_id:
            self._attr_supported_features = LightEntityFeature.EFFECT
            self._effect_device = config.hub.get_typed_device(
                config.entity.effect_id, MultiValueSwitchDevice
            )
            self._attr_effect_list = self._effect_device.options
            self._effect_device.state.changed += self._on_effect_change
            self._schedule_update_when_changed(self._effect_device)

        super().__init__(config, self._light, LIGHT_DOMAIN)

    def _on_light_state_change(
        self, _: DigitalOutputState | None, current_state: DigitalOutputState
    ) -> None:
        """Handle light state changes."""
        self._attr_is_on = current_state.is_on

    def _on_effect_change(
        self,
        _: MultiValueSwitchState | None,
        _current_state: MultiValueSwitchState,
    ) -> None:
        self._attr_effect = self._effect_device.selected_option

    async def async_turn_off(self, **kwargs):
        """Turn device off."""
        await self._light.async_turn_off()


class TapHomeGenericOutputLight(TapHomeLight):
    """Representation of an on/off or dimmable light."""

    _light: AnalogOutputDevice | DigitalOutputDevice

    def __init__(
        self,
        config: AddEntryRequest[TapHomeLightConfig],
        light: AnalogOutputDevice | DigitalOutputDevice,
    ) -> None:
        """Initialize TapHome light entity."""

        match light:
            case AnalogOutputDevice():
                self._attr_supported_color_modes = {
                    ColorMode.BRIGHTNESS,
                }
                self._attr_color_mode = ColorMode.BRIGHTNESS
                light.state.changed += self._light_analog_output_state_change
            case DigitalOutputDevice():
                self._attr_supported_color_modes = {
                    ColorMode.ONOFF,
                }
                self._attr_color_mode = ColorMode.ONOFF

        super().__init__(config, light)

    def _light_analog_output_state_change(
        self, _: AnalogOutputState | None, current_state: AnalogOutputState
    ) -> None:
        """Handle light state change event."""
        self._attr_brightness = self.convert_th_byte_to_ha(current_state.output_value)

    async def async_turn_on(
        self,
        *,
        brightness: int | None = None,
        **kwargs,
    ) -> None:
        """Turn device on."""
        th_brightness = self.convert_ha_byte_to_th(brightness)
        if th_brightness is not None and isinstance(self._light, AnalogOutputDevice):
            await self._light.async_set_output_value(th_brightness)
        else:
            await self._light.async_turn_on()


class TapHomeColorLight(TapHomeLight):
    """Representation of an color light."""

    _light: RGBLightDevice | DualWhiteLightDevice

    def __init__(
        self,
        config: AddEntryRequest[TapHomeLightConfig],
        light: RGBLightDevice | DualWhiteLightDevice,
    ) -> None:
        """Initialize TapHome light entity."""

        self._attr_min_color_temp_kelvin = light.min_color_temperature
        self._attr_max_color_temp_kelvin = light.max_color_temperature

        match light:
            case RGBLightDevice():
                self._attr_supported_color_modes = {
                    ColorMode.HS,
                    ColorMode.COLOR_TEMP,
                }
            case DualWhiteLightDevice():
                self._attr_supported_color_modes = {
                    ColorMode.COLOR_TEMP,
                }

        light.state.changed.subscribe(self._on_color_light_state_change)
        super().__init__(config, light)

    def _on_color_light_state_change(
        self,
        _: RGBLightState | DualWhiteLightState | None,
        current_state: RGBLightState | DualWhiteLightState,
    ) -> None:
        """Handle light state changes."""
        self._attr_brightness = self.convert_th_byte_to_ha(current_state.brightness)
        self._attr_color_temp_kelvin = current_state.color_temperature

        if isinstance(current_state, RGBLightState):
            hue = current_state.hue_degrees
            saturation = self.convert_th_percentage_to_ha(current_state.saturation)
            self._attr_hs_color = (
                (hue, saturation)
                if hue is not None and saturation is not None
                else None
            )

        self._attr_color_mode = (
            ColorMode.COLOR_TEMP
            if self._attr_color_temp_kelvin is not None
            else ColorMode.HS
            if self._attr_hs_color is not None
            else None
        )

    async def async_turn_on(
        self,
        *,
        brightness: int | None = None,
        color_temp_kelvin: int | None = None,
        hs_color: tuple[float, float] | None = None,
        **kwargs,
    ) -> None:
        """Turn device on."""

        th_brightness = self.convert_ha_byte_to_th(brightness)

        if isinstance(self._light, RGBLightDevice) and hs_color is not None:
            hue, saturation = hs_color
            th_saturation = self.convert_ha_percentage_to_th(saturation)
            await self._light.async_turn_on_color(th_brightness, hue, th_saturation)
        else:
            await self._light.async_turn_on_color_temperature(
                th_brightness,
                color_temp_kelvin,
            )


def _create_light_entity(
    config: AddEntryRequest[TapHomeLightConfig],
) -> TapHomeLight:
    """Create TapHome light entity."""
    light = config.hub.get_typed_device(
        config.entity.id,
        RGBLightDevice,
        DualWhiteLightDevice,
        AnalogOutputDevice,
        DigitalOutputDevice,
    )
    match light:
        case RGBLightDevice() | DualWhiteLightDevice():
            return TapHomeColorLight(config, light)
        case AnalogOutputDevice() | DigitalOutputDevice():
            return TapHomeGenericOutputLight(config, light)
        case _:
            raise ValueError(f"Unsupported light device type: {type(light)}")


def setup_platform(
    hass: HomeAssistant,
    _config: ConfigType,
    add_entities: AddEntitiesCallback,
    _discovery_info: DiscoveryInfoType | None = None,
) -> None:
    """Set up the switch platform."""
    add_taphome_entities(hass, add_entities, CONF_LIGHTS, _create_light_entity)
