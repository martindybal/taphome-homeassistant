"""TapHome Digital Output Device."""

from dataclasses import dataclass
from typing import TypeVar

from .device import ValueType
from .device_digital_output import DigitalOutputDevice, DigitalOutputState
from .switch_state import SwitchState


@dataclass(slots=True)
class AnalogOutputState(DigitalOutputState):
    """State for a digital output device."""

    output_value: float | None = None

    def device_values_changed(self, initial: bool) -> None:
        """Update state attributes when device values change."""
        DigitalOutputState.device_values_changed(self, initial)
        self.output_value = self.get_device_value(ValueType.ANALOG_OUTPUT_VALUE)


StateT = TypeVar("StateT", bound=AnalogOutputState)


@dataclass(slots=True)
class AnalogOutputDeviceBase(DigitalOutputDevice[StateT]):
    """Representation of a digital output device in TapHome."""

    async def async_set_output_value(self, output_value: float) -> None:
        """Set device to the provided ``switch_state``."""
        await self.async_set_device_values(
            {
                ValueType.SWITCH_STATE: SwitchState.ON.value,
                ValueType.ANALOG_OUTPUT_DESIRED_VALUE: output_value,
            }
        )


@dataclass(slots=True)
class AnalogOutputDevice(AnalogOutputDeviceBase[AnalogOutputState]):
    """Representation of a digital output device in TapHome."""
