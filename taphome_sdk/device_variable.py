"""TapHome Digital Output Device."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import time
import logging
from typing import TypeVar

from .device import Device, DeviceState, ValueType

_LOGGER = logging.getLogger(__name__)


@dataclass(slots=True)
class VariableState(DeviceState):
    """State for a variable device."""

    value: float | None = None

    def device_values_changed(self, initial: bool) -> None:
        """Update state attributes when device values change."""
        self.value = self.get_device_value(ValueType.VARIABLE_STATE)


StateT = TypeVar("StateT", bound=VariableState)


@dataclass(slots=True)
class VariableDeviceBase(Device[StateT]):
    """Representation of a variable device in TapHome."""

    async def async_set_value(self, value: float) -> None:
        """Set the value of the variable device."""
        await self.async_set_device_value(ValueType.VARIABLE_STATE, value)


@dataclass(slots=True)
class VariableDevice(VariableDeviceBase[VariableState]):
    """Representation of a variable device in TapHome."""


@dataclass(slots=True)
class SessionDurationVariableState(VariableState):
    """State for a session duration device."""

    total_seconds: int | None = None

    def device_values_changed(self, initial: bool) -> None:
        """Update state attributes when device values change."""
        VariableState.device_values_changed(self, initial)
        self.total_seconds = self.get_device_int_value(ValueType.SESSION_DURATION)

    def to_time(self) -> time | None:
        """Convert second count to a ``time`` instance."""
        if self.total_seconds is None:
            return None

        one_day_total_seconds = 86400
        if self.total_seconds < 0 or self.total_seconds >= one_day_total_seconds:
            _LOGGER.error(
                "Seconds value cannot exceed one day (86400 seconds). Provided value %s",
                self.total_seconds,
            )
            return None

        hours, remainder = divmod(self.total_seconds, 3600)
        minutes, seconds = divmod(remainder, 60)
        return time(hour=hours, minute=minutes, second=seconds)


@dataclass(slots=True)
class SessionDurationVariableDevice(VariableDeviceBase[SessionDurationVariableState]):
    """Representation of a session duration device in TapHome."""

    async def async_set_time(self, value: time) -> None:
        """Set the value of the session duration device."""
        total_seconds = value.hour * 3600 + value.minute * 60 + value.second
        await self.async_set_value(total_seconds)
