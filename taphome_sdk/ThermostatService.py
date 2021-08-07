import logging

from .Device import Device
from .TapHomeApiService import TapHomeApiService
from .ValueChangeResult import ValueChangeResult
from .ValueType import ValueType
from .taphome_device_state import TapHomeState

_LOGGER = logging.getLogger(__name__)


class ThermostatState(TapHomeState):
    def __init__(
        self,
        thermostat_values: dict,
    ):
        super().__init__(thermostat_values)

        self.desired_temperature = self.get_device_value(ValueType.DesiredTemperature)
        self.real_temperature = self.get_device_value(ValueType.RealTemperature)
        self.min_temperature = self.get_device_value(ValueType.MinTemperature)
        self.max_temperature = self.get_device_value(ValueType.MaxTemperature)


class ThermostatService:
    def __init__(self, taphome_api_service: TapHomeApiService):
        self.taphome_api_service = taphome_api_service

    async def async_get_state(self, device: Device) -> ThermostatState:
        try:
            thermostat_values = await self.taphome_api_service.async_get_device_values(
                device.deviceId
            )

            return ThermostatState(thermostat_values)
        except:
            _LOGGER.error(f"TapHome async_get_state for {device.id} failed")
            return None

    def async_set_desired_temperature(
        self, device: Device, desired_temperature
    ) -> None:
        values = [
            self.taphome_api_service.create_device_value(
                ValueType.DesiredTemperature, desired_temperature
            )
        ]

        return self.taphome_api_service.async_set_device_values(device.id, values)
