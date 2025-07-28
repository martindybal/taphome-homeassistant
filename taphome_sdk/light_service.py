"""Light control utilities for TapHome devices."""

from .device import Device
from .switch_states import SwitchStates
from .taphome_api_service import TapHomeApiService
from .taphome_device_state import TapHomeState
from .value_type import ValueType


class LightState(TapHomeState):
    """State representation for a light device."""

    def __init__(
        self,
        light_values: dict,
    ):
        """Create state from ``light_values`` dictionary."""
        super().__init__(light_values)

        self.switch_state = self.get_device_enum_value(
            SwitchStates, ValueType.SWITCH_STATE
        )

        self.hue = self.get_device_value(ValueType.HUE_DEGREES)
        self.saturation = self.get_device_value(ValueType.SATURATION)

        self.brightness = self.get_device_value(ValueType.ANALOG_OUTPUT_VALUE)
        if self.brightness is None:
            self.brightness = self.get_device_value(ValueType.HUE_BRIGHTNESS)

        self.color_temperature = self.get_device_value(
            ValueType.CORRELATED_COLOR_TEMPERATURE
        )


class LightService:
    """Service for controlling TapHome lights."""

    def __init__(self, taphome_api_service: TapHomeApiService) -> None:
        """Initialize with the provided API service."""
        self.taphome_api_service = taphome_api_service

    async def async_get_state(self, device: Device) -> LightState:
        """Return the current ``LightState`` for ``device``."""
        light_values = await self.taphome_api_service.async_get_device_values(device.id)

        return LightState(light_values)

    async def async_turn_on(
        self,
        device: Device,
        brightness=None,
        color_temp=None,
        hue=None,
        saturation=None,
    ) -> None:
        """Turn the light on with the optional parameters provided."""
        if brightness is color_temp is hue is saturation is None:
            await self.taphome_api_service.async_set_device_value(
                device.id, ValueType.SWITCH_STATE, SwitchStates.ON.value
            )
            return

        values = []

        def append_value(value_type: ValueType, value):
            values.append(
                self.taphome_api_service.create_device_value(value_type, value)
            )

        if brightness is not None:
            append_value(ValueType.SWITCH_STATE, SwitchStates.ON.value)

            if device.supports_value(ValueType.ANALOG_OUTPUT_DESIRED_VALUE):
                append_value(ValueType.ANALOG_OUTPUT_DESIRED_VALUE, brightness)
            elif device.supports_value(ValueType.HUE_BRIGHTNESS_DESIRED_VALUE):
                append_value(ValueType.HUE_BRIGHTNESS_DESIRED_VALUE, brightness)

        if color_temp is not None:
            append_value(ValueType.CORRELATED_COLOR_TEMPERATURE, color_temp)

        if hue is not None:
            append_value(ValueType.HUE_DEGREES, hue)

        if saturation is not None:
            append_value(ValueType.SATURATION, saturation)

        await self.taphome_api_service.async_set_device_values(device.id, values)

    async def async_turn_off(self, device: Device) -> None:
        """Turn ``device`` off."""
        await self.taphome_api_service.async_set_device_value(
            device.id, ValueType.SWITCH_STATE, SwitchStates.OFF.value
        )
