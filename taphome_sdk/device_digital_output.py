"""TapHome Digital Output Device."""

from dataclasses import dataclass
from typing import TypeVar

from .device import Device, DeviceState, ValueType
from .switch_state import SwitchState


@dataclass(slots=True)
class DigitalOutputState(DeviceState):
    """State for a digital output device."""

    switch_state: SwitchState | None = None

    @property
    def is_on(self) -> bool | None:
        """Return True if entity is on."""
        if self.switch_state is None:
            return None
        return self.switch_state == SwitchState.ON

    def device_values_changed(self, initial: bool) -> None:
        """Update state attributes when device values change."""
        self.switch_state = self.get_device_enum_value(
            SwitchState, ValueType.SWITCH_STATE
        )


StateT = TypeVar("StateT", bound=DigitalOutputState)


@dataclass(slots=True)
class DigitalOutputDevice(Device[StateT]):
    """Representation of a digital output device in TapHome."""

    async def async_turn_on(self) -> None:
        """Turn on the device."""
        await self.async_turn(SwitchState.ON)

    async def async_turn_off(self) -> None:
        """Turn off the device."""
        await self.async_turn(SwitchState.OFF)

    async def async_turn(self, switch_state: SwitchState) -> None:
        """Set device to the provided ``switch_state``."""
        await self.async_set_device_value(ValueType.SWITCH_STATE, switch_state.value)
