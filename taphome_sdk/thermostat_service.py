"""Thermostat services for the TapHome platform."""

import logging

from .device import Device
from .taphome_api_service import TapHomeApiService
from .taphome_device_state import TapHomeState
from .value_type import ValueType

_LOGGER = logging.getLogger(__name__)


class ThermostatState(TapHomeState):
    """State representation for a thermostat device."""

    def __init__(
        self,
        thermostat_values: dict,
    ):
        """Create state from ``thermostat_values``."""
        super().__init__(thermostat_values)

        self.desired_temperature = self.get_device_value(ValueType.TEMPERATURE_SET_POINT)
        self.real_temperature = self.get_device_value(ValueType.REAL_TEMPERATURE)
        self.real_humidity = self.get_device_value(ValueType.HUMIDITY)


class ThermostatService:
    """Service for controlling TapHome thermostats."""

    def __init__(self, taphome_api_service: TapHomeApiService):
        """Initialize with the TapHome API service."""
        self.taphome_api_service = taphome_api_service

    async def async_get_state(self, device: Device) -> ThermostatState | None:
        """Return ``ThermostatState`` for ``device`` if available."""
        try:
            thermostat_values = await self.taphome_api_service.async_get_device_values(
                device.id
            )
            return ThermostatState(thermostat_values)
        except Exception:
            _LOGGER.exception("TapHome async_get_state for %s failed", device.id)
            return None

    async def async_set_desired_temperature(
        self, device: Device, desired_temperature
    ) -> None:
        """Set the desired temperature on ``device``."""
        values = [
            self.taphome_api_service.create_device_value(
                ValueType.TEMPERATURE_SET_POINT, desired_temperature
            )
        ]

        await self.taphome_api_service.async_set_device_values(device.id, values)
