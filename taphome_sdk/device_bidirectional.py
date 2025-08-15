"""TapHome Digital Output Device."""

from dataclasses import dataclass
from datetime import datetime, timedelta
from enum import Enum

from .device import Device, DeviceState, ValueType


class PositionState(Enum):
    """Enum representing the position state."""

    OPENING = "opening"
    OPEN = "open"
    CLOSING = "closing"
    CLOSED = "closed"

    def __str__(self):
        """Return string representation of the position state."""
        return self.value


MOVEMENT_PENDING_TIMEOUT = timedelta(seconds=10)


class BidirectionalDeviceState(DeviceState):
    """State for a digital output device."""

    position: float | None = None
    tilt: float | None = None

    _movement_pending_until: datetime | None = None

    def set_movement_pending(self) -> None:
        """TapHome didn't change BLINDS_IS_MOVING immediately."""
        self._movement_pending_until = datetime.now() + MOVEMENT_PENDING_TIMEOUT

    def device_values_changed(self, initial: bool) -> None:
        """Update state attributes when device values change."""
        self.position = self.get_device_value(ValueType.BLINDS_LEVEL)
        self.tilt = self.get_device_value(ValueType.BLINDS_SLOPE)
        is_moving = self.get_device_bool_value(ValueType.BLINDS_IS_MOVING)
        if is_moving:
            self._movement_pending_until = None

    def get_inverted_position_state(
        self, close_threshold: float | None = None
    ) -> PositionState | None:
        """Get the inverted position state based on the current position. Especialy for covers."""
        close_threshold = 1 if close_threshold is None else close_threshold + 0.01
        position_state = self.get_position_state(1 - close_threshold)

        match position_state:
            case PositionState.OPEN:
                return PositionState.CLOSED
            case PositionState.OPENING:
                return PositionState.CLOSING
            case PositionState.CLOSED:
                return PositionState.OPEN
            case PositionState.CLOSING:
                return PositionState.OPENING
            case _:
                return None

    def get_position_state(
        self, close_threshold: float | None = None
    ) -> PositionState | None:
        """Get the position state based on the position, is moving and close threshold."""
        close_threshold = close_threshold or 0
        final_position_state = self._compute_final_position_state(close_threshold)
        is_moving = self.get_device_bool_value(ValueType.BLINDS_IS_MOVING)
        movement_pending = (
            self._movement_pending_until is not None
            and datetime.now() < self._movement_pending_until
        )
        if is_moving or movement_pending:
            return (
                PositionState.CLOSING
                if final_position_state is PositionState.CLOSED
                else PositionState.OPENING
            )
        return final_position_state

    def _compute_final_position_state(
        self, close_threshold: float
    ) -> PositionState | None:
        return (
            None
            if self.position is None
            else PositionState.CLOSED
            if close_threshold >= self.position
            else PositionState.OPEN
        )


@dataclass(slots=True)
class BidirectionalDevice(Device[BidirectionalDeviceState]):
    """Representation of a bidirectional tap home device in TapHome."""

    @property
    def supports_tilt(self) -> float | None:
        """Return if the device supports tilt."""
        return self.supports_value(ValueType.BLINDS_SLOPE)

    async def async_open(self) -> None:
        """Open the device."""
        await self.async_set_position(1)

    async def async_close(self) -> None:
        """Close the device."""
        await self.async_set_position(0)

    async def async_set_position(
        self, position: float, tilt: float | None = None
    ) -> None:
        """Set device to the provided ``position``."""
        if not self.supports_tilt:
            tilt = None

        self.state.set_movement_pending()
        await self.async_set_device_values(
            {ValueType.BLINDS_LEVEL: position, ValueType.BLINDS_SLOPE: tilt}
        )

    async def async_set_tilt(self, tilt: float) -> None:
        """Set device to the provided ``tilt``."""
        await self.async_set_device_values({ValueType.BLINDS_SLOPE: tilt})
