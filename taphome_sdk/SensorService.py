from .Device import Device
from .ValueType import ValueType
from .TapHomeApiService import TapHomeApiService


class SensorService:
    def __init__(self, tapHomeApiService: TapHomeApiService):
        self.tapHomeApiService = tapHomeApiService

    async def async_get_sensor_value(self, device: Device, value_type: ValueType):
        switchValues = await self.tapHomeApiService.async_get_device_values(
            device.deviceId
        )

        sensor_value = DeviceServiceHelper.get_device_value(switchValues, value_type)

        return sensor_value