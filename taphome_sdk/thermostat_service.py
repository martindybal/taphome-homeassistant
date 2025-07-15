import logging

from .device import Device
from .taphome_api_service import TapHomeApiService
from .taphome_device_state import TapHomeState
from .value_type import ValueType

_LOGGER = logging.getLogger(__name__)


class ThermostatState(TapHomeState):
    def __init__(
        self,
        thermostat_values: dict,
    ):
        super().__init__(thermostat_values)

        self.desired_temperature = self.get_device_value(ValueType.TemperatureSetPoint)
        self.real_temperature = self.get_device_value(ValueType.RealTemperature)
        self.real_humidity = self.get_device_value(ValueType.Humidity)


class ThermostatService:
    def __init__(self, taphome_api_service: TapHomeApiService):
        self.taphome_api_service = taphome_api_service

    async def async_get_state(self, device: Device) -> ThermostatState:
        try:
            thermostat_values = await self.taphome_api_service.async_get_device_values(
                device.id
            )

            return ThermostatState(thermostat_values)
        except Exception:
            _LOGGER.exception("TapHome async_get_state for %s failed", device.id)
            return None

    def async_set_desired_temperature(
        self, device: Device, desired_temperature
    ) -> None:
        values = [
            self.taphome_api_service.create_device_value(
                ValueType.TemperatureSetPoint, desired_temperature
            )
        ]

        return self.taphome_api_service.async_set_device_values(device.id, values)
