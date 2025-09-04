"""TapHome Digital Output Device."""

from dataclasses import dataclass

from .device import ValueType
from .device_digital_output import DigitalOutputDevice, DigitalOutputState
from .taphome_api import EnumeratedValue


@dataclass(slots=True)
class MultiValueSwitchState(DigitalOutputState):
    """State for a multi-value switch device."""

    selected_value: int | None = None

    def device_values_changed(self, initial: bool) -> None:
        """Update state attributes when device values change."""
        DigitalOutputState.device_values_changed(self, initial)
        self.selected_value = self.get_device_int_value(
            ValueType.MULTI_VALUE_SWITCH_STATE
        )


@dataclass(slots=True)
class MultiValueSwitchDevice(DigitalOutputDevice[MultiValueSwitchState]):
    """Representation of a multi-value switch device in TapHome."""

    @property
    def allowed_values(self) -> list[EnumeratedValue]:
        """Return the allowed values for the multi-value switch."""
        return self.supported_values[ValueType.MULTI_VALUE_SWITCH_STATE].allowed_values

    @property
    def selected_option(self) -> str | None:
        """Return the currently selected option."""
        return self.get_option(self.state.selected_value)

    @property
    def options(self) -> list[str]:
        """Return the options for the multi-value switch."""
        return [value.name for value in self.allowed_values if value.is_enabled]

    def get_option(self, index: int | None) -> str | None:
        """Return the option by index."""
        if index is None:
            return None
        return next(
            (value.name for value in self.allowed_values if value.value == index),
            None,
        )

    async def async_select_option(self, option: str) -> None:
        """Select the option for the multi-value switch."""
        value = next((v.value for v in self.allowed_values if v.name == option), None)
        if value is not None:
            await self.async_select_value(value)

    async def async_select_value(self, value: int) -> None:
        """Set the value of the multi-value switch."""
        await self.async_set_device_value(ValueType.MULTI_VALUE_SWITCH_STATE, value)
