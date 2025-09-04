"""TapHome Digital Output Device."""

from dataclasses import dataclass

from .device import Device, DeviceState
from .value_type import ValueType


@dataclass(slots=True)
class ThermostatState(DeviceState):
    """State for a thermostat device."""

    humidity: float | None = None
    temperature: float | None = None
    desired_temperature: float | None = None

    def device_values_changed(self, initial: bool) -> None:
        """Update state attributes when device values change."""
        self.humidity = self.get_device_value(ValueType.HUMIDITY)
        self.temperature = self.get_device_value(ValueType.REAL_TEMPERATURE)
        self.desired_temperature = self.get_device_value(
            ValueType.TEMPERATURE_SET_POINT
        )


@dataclass(slots=True)
class ThermostatDevice(Device[ThermostatState]):
    """Representation of a thermostat device in TapHome."""

    async def async_set_desired_temperature(self, desired_temperature: float) -> None:
        """Set device provided ``desired_temperature``."""
        await self.async_set_device_value(
            ValueType.TEMPERATURE_SET_POINT, desired_temperature
        )
