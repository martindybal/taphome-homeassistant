from .Device import Device
from .TapHomeApiService import TapHomeApiService
from .ValueChangeResult import ValueChangeResult
from .ValueType import ValueType


class ThermostatState:
    def __init__(
        self, desired_temperature, real_temperature, min_temperature, max_temperature
    ):
        self._desired_temperature = desired_temperature
        self._real_temperature = real_temperature
        self._min_temperature = min_temperature
        self._max_temperature = max_temperature

    @property
    def desired_temperature(self):
        return self._desired_temperature

    @property
    def real_temperature(self):
        return self._real_temperature

    @property
    def min_temperature(self):
        return self._min_temperature

    @property
    def max_temperature(self):
        return self._max_temperature


class ThermostatService:
    def __init__(self, tapHomeApiService: TapHomeApiService):
        self.tapHomeApiService = tapHomeApiService

    async def async_get_thermostat_state(self, device: Device) -> ThermostatState:
        thermostat_values = await self.tapHomeApiService.async_get_device_values(
            device.deviceId
        )

        desired_temperature = DeviceServiceHelper.get_device_value(
            thermostat_values, ValueType.DesiredTemperature
        )

        real_temperature = DeviceServiceHelper.get_device_value(
            thermostat_values, ValueType.RealTemperature
        )

        min_temperature = DeviceServiceHelper.get_device_value(
            thermostat_values, ValueType.MinTemperature
        )

        max_temperature = DeviceServiceHelper.get_device_value(
            thermostat_values, ValueType.MaxTemperature
        )

        return ThermostatState(
            desired_temperature, real_temperature, min_temperature, max_temperature
        )

    def async_set_desired_temperature(
        self, device: Device, desired_temperature
    ) -> ValueChangeResult:
        values = [
            self.tapHomeApiService.create_device_value(
                ValueType.DesiredTemperature, desired_temperature
            )
        ]

        return self.tapHomeApiService.async_set_device_values(device.deviceId, values)