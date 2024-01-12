from .device import Device
from .switch_states import SwitchStates
from .taphome_api_service import TapHomeApiService
from .taphome_device_state import TapHomeState
from .value_type import ValueType


class HumidifierState(TapHomeState):
    def __init__(
        self,
        fan_values: dict,
    ):
        super().__init__(fan_values)
        self.humidity = self.get_device_value(ValueType.AnalogOutputDesiredValue)
        self.switch_state = SwitchStates(self.get_device_value(ValueType.SwitchState))


class HumidifierService:
    def __init__(self, taphome_api_service: TapHomeApiService):
        self.taphome_api_service = taphome_api_service
        self.analog_humidifier_service = AnalogHumidifierService(taphome_api_service)

    async def async_get_state(self, device: Device) -> HumidifierState:
        fan_values = await self.taphome_api_service.async_get_device_values(
            device.deviceId
        )
        return HumidifierState(fan_values)

    def async_turn_on(self, device: Device) -> None:
        humidifier_service = self.get_humidifier_service(device)
        return humidifier_service.async_turn_on(device)

    def async_turn_off(self, device: Device) -> None:
        humidifier_service = self.get_humidifier_service(device)
        return humidifier_service.async_turn_off(device)

    def async_set_humidity(self, device: Device, humidity=None) -> None:
        humidifier_service = self.get_humidifier_service(device)
        return humidifier_service.async_set_humidity(device, humidity)

    def get_humidifier_service(self, device: Device) -> None:
        if device.supports_value(ValueType.AnalogOutputDesiredValue):
            return self.analog_humidifier_service


class AnalogHumidifierService:
    def __init__(self, taphome_api_service: TapHomeApiService):
        self.taphome_api_service = taphome_api_service

    def async_turn_on(self, device: Device) -> None:
        values = [
            self.taphome_api_service.create_device_value(
                ValueType.SwitchState, SwitchStates.ON.value
            )
        ]
        return self.taphome_api_service.async_set_device_values(device.id, values)

    def async_turn_off(self, device: Device) -> None:
        values = [
            self.taphome_api_service.create_device_value(
                ValueType.SwitchState, SwitchStates.OFF.value
            )
        ]
        return self.taphome_api_service.async_set_device_values(device.id, values)

    def async_set_humidity(self, device: Device, humidity=None) -> None:
        values = [
            self.taphome_api_service.create_device_value(
                ValueType.SwitchState, SwitchStates.ON.value
            ),
            self.taphome_api_service.create_device_value(
                ValueType.AnalogOutputDesiredValue, humidity
            ),
        ]

        return self.taphome_api_service.async_set_device_values(device.id, values)
