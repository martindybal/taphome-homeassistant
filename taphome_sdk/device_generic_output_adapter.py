"""Common interface for handling both digital and analog output devices."""

from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from typing import Any

from .device_analog_output import AnalogOutputDevice, AnalogOutputState
from .device_bidirectional import (
    BidirectionalDevice,
    BidirectionalDeviceState,
    PositionState,
)
from .device_digital_output import DigitalOutputDevice, DigitalOutputState
from .observable import Event

type OutputCapableDevice = (
    DigitalOutputDevice | AnalogOutputDevice | BidirectionalDevice
)


@dataclass(slots=True, frozen=True)
class GenericOutputState:
    """State for a digital output device."""

    is_on: bool | None = None
    output_value: float | None = None
    device_state: (
        AnalogOutputState | BidirectionalDeviceState | DigitalOutputState | None
    ) = None


class GenericOutputAdapter:
    """Common interface for output devices."""

    _support_set_output_value: bool
    _async_turn_on: Callable[[], Awaitable[None]]
    _async_turn_off: Callable[[], Awaitable[None]]
    _async_set_output_value: Callable[[float], Awaitable[None]]
    _map_state: Callable[
        [Any],
        GenericOutputState,
    ]
    _state: GenericOutputState
    _state_changed: Event[GenericOutputState | None, GenericOutputState]

    def __init__(
        self,
        device: OutputCapableDevice,
    ) -> None:
        """Initialize the generic output adapter."""
        self._state = GenericOutputState()
        self._state_changed = Event()
        match device:
            case BidirectionalDevice() as bidirectional_device:

                def _map_bidirectional_state(
                    state: BidirectionalDeviceState,
                ) -> GenericOutputState:
                    is_on = state.get_position_state() in (
                        PositionState.OPEN,
                        PositionState.OPENING,
                    )
                    return GenericOutputState(is_on, state.position, state)

                self._support_set_output_value = True
                self._async_turn_on = bidirectional_device.async_open
                self._async_turn_off = bidirectional_device.async_close
                self._async_set_output_value = bidirectional_device.async_set_position
                self._map_state = _map_bidirectional_state

            case AnalogOutputDevice() as analog_device:

                def _map_analog_state(state: AnalogOutputState) -> GenericOutputState:
                    return GenericOutputState(state.is_on, state.output_value, state)

                self._support_set_output_value = True
                self._async_turn_on = analog_device.async_turn_on
                self._async_turn_off = analog_device.async_turn_off
                self._async_set_output_value = analog_device.async_set_output_value
                self._map_state = _map_analog_state

            case DigitalOutputDevice() as digital_device:

                def _map_digital_state(state: DigitalOutputState) -> GenericOutputState:
                    output_value = (
                        state.switch_state.value if state.switch_state else None
                    )
                    return GenericOutputState(state.is_on, output_value, state)

                async def _async_turn_on_or_off(output_value: float) -> None:
                    if output_value == 0:
                        await self._async_turn_off()
                    else:
                        await self._async_turn_on()

                self._support_set_output_value = False
                self._async_turn_on = digital_device.async_turn_on
                self._async_turn_off = digital_device.async_turn_off
                self._async_set_output_value = _async_turn_on_or_off
                self._map_state = _map_digital_state

            case _:
                raise TypeError("Unsupported device type for GenericOutputAdapter")

        device.state.changed.subscribe(self._on_device_state_change)

    @property
    def state(self) -> GenericOutputState:
        """Return the current output value."""
        return self._state

    @property
    def state_changed(self) -> Event[GenericOutputState | None, GenericOutputState]:
        """Return the event that is triggered when the state changes."""
        return self._state_changed

    @state_changed.setter
    def state_changed(
        self,
        value: Event,
    ) -> None:
        self._state_changed = value

    def _on_device_state_change(self, old_state, current_state) -> None:
        """Handle device state changes."""
        if old_state is not None:
            old_state = self._map_state(old_state)
        self._state = self._map_state(current_state)
        self._state_changed(old_state, self._state)

    def support_set_output_value(self) -> bool:
        """True if device supports setting output value."""
        return self._support_set_output_value

    async def async_turn_on(self) -> None:
        """Turn on."""
        await self._async_turn_on()

    async def async_turn_off(self) -> None:
        """Turn off."""
        await self._async_turn_off()

    async def async_set_output_value(self, output_value: float) -> None:
        """Set normalized ``output_value`` value (0.0-1.0)."""
        await self._async_set_output_value(output_value)
