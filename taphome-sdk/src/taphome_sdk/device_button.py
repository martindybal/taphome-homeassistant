"""TapHome Digital Output Device."""

from dataclasses import dataclass, field
from enum import Enum

from .device import Device, DeviceState, ValueType
from .observable import Event


class ButtonAction(Enum):
    """Enumeration of available button press actions."""

    NONE = 0
    PRESS = 1
    LONG_PRESS = 2
    DOUBLE_PRESS = 3
    TRIPLE_PRESS = 4


@dataclass(slots=True)
class ButtonState(DeviceState):
    """State for a TapHome button device."""

    action: ButtonAction | None = None

    def device_values_changed(self, initial: bool) -> None:
        """Update state attributes when device values change."""

        if not initial:
            self.action = self.get_device_enum_value(
                ButtonAction, ValueType.BUTTON_PRESSED
            )


@dataclass(slots=True)
class ButtonDevice(Device[ButtonState]):
    """Representation of a TapHome button device."""

    clicked: Event[ButtonAction] = field(default_factory=Event)

    async def async_press(self, action: ButtonAction = ButtonAction.PRESS) -> None:
        """Trigger the desired button ``action`` on ``device``."""
        await self.async_set_device_value(ValueType.BUTTON_PRESSED, action.value)

    def __post_init__(self) -> None:
        """Initialize the button device."""
        self.state.changed += self._on_state_change

    def _on_state_change(self, _: ButtonState | None, state: ButtonState) -> None:
        """Handle state changes."""
        if state.action and state.action != ButtonAction.NONE:
            self.clicked(state.action)
