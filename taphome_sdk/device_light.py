"""TapHome Digital Output Device."""

from dataclasses import dataclass
from typing import TypeVar

from .device import ValueType
from .device_digital_output import DigitalOutputDevice, DigitalOutputState
from .switch_state import SwitchState


class DimmableLightState(DigitalOutputState):
    """State for a digital output device."""

    brightness: float | None = None

    def device_values_changed(self, initial: bool) -> None:
        """Update state attributes when device values change."""
        DigitalOutputState.device_values_changed(self, initial)
        self.brightness = self.get_device_value(ValueType.HUE_BRIGHTNESS)


class DualWhiteLightState(DimmableLightState):
    """State for a digital output device."""

    color_temperature: int | None = None

    def device_values_changed(self, initial: bool) -> None:
        """Update state attributes when device values change."""
        DimmableLightState.device_values_changed(self, initial)
        self.color_temperature = self.get_device_int_value(
            ValueType.CORRELATED_COLOR_TEMPERATURE
        )


DualWhiteLightStateT = TypeVar("DualWhiteLightStateT", bound=DualWhiteLightState)


@dataclass(slots=True)
class DualWhiteLightDeviceBase(DigitalOutputDevice[DualWhiteLightStateT]):
    """Representation of a digital output device in TapHome."""

    @property
    def min_color_temperature(self) -> int | None:
        """Return the allowed values for the multi-value switch."""
        return self.supported_values[ValueType.CORRELATED_COLOR_TEMPERATURE].min_value

    @property
    def max_color_temperature(self) -> int | None:
        """Return the allowed values for the multi-value switch."""
        return self.supported_values[ValueType.CORRELATED_COLOR_TEMPERATURE].max_value

    async def async_turn_on_color_temperature(
        self, brightness: float | None, color_temperature: float | None
    ) -> None:
        """Set device to the provided ``switch_state``."""
        await self.async_set_device_values(
            {
                ValueType.SWITCH_STATE: SwitchState.ON.value,
                ValueType.HUE_BRIGHTNESS_DESIRED_VALUE: brightness,
                ValueType.CORRELATED_COLOR_TEMPERATURE: color_temperature,
            }
        )


@dataclass(slots=True)
class DualWhiteLightDevice(DualWhiteLightDeviceBase[DualWhiteLightState]):
    """Representation of a digital output device in TapHome."""


@dataclass(slots=True)
class RGBLightState(DualWhiteLightState):
    """State for a digital output device."""

    hue_degrees: float | None = None
    saturation: float | None = None

    def device_values_changed(self, initial: bool) -> None:
        """Update state attributes when device values change."""
        DualWhiteLightState.device_values_changed(self, initial)
        self.hue_degrees = self.get_device_value(ValueType.HUE_DEGREES)
        self.saturation = self.get_device_value(ValueType.SATURATION)


@dataclass(slots=True)
class RGBLightDevice(DualWhiteLightDeviceBase[RGBLightState]):
    """Representation of a digital output device in TapHome."""

    async def async_turn_on_color(
        self, brightness: float | None, hue: float | None, saturation: float | None
    ) -> None:
        """Set device to the provided ``switch_state``."""

        await self.async_set_device_values(
            {
                ValueType.SWITCH_STATE: SwitchState.ON.value,
                ValueType.HUE_BRIGHTNESS_DESIRED_VALUE: brightness,
                ValueType.HUE_DEGREES: hue,
                ValueType.SATURATION: saturation,
            }
        )
