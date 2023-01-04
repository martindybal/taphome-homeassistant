from .device import Device
from .switch_states import SwitchStates
from .taphome_api_service import TapHomeApiService
from .taphome_device_state import TapHomeState
from .value_type import ValueType


class FanState(TapHomeState):
    def __init__(
        self,
        fan_values: dict,
    ):
        super().__init__(fan_values)
        self.switch_state = SwitchStates(self.get_device_value(ValueType.SwitchState))
        self.percentage = self.get_device_value(ValueType.AnalogOutputValue)


class FanService:
    def __init__(self, tapHomeApiService: TapHomeApiService):
        self.tapHomeApiService = tapHomeApiService

    async def async_get_state(self, device: Device) -> FanState:
        fan_values = await self.tapHomeApiService.async_get_device_values(
            device.deviceId
        )

        return FanState(fan_values)

    def async_turn_on(self, device: Device) -> None:
        values = [
            self.tapHomeApiService.create_device_value(
                ValueType.SwitchState, SwitchStates.ON.value
            )
        ]
        return self.tapHomeApiService.async_set_device_values(device.id, values)

    def async_turn_off(self, device: Device) -> None:
        values = [
            self.tapHomeApiService.create_device_value(
                ValueType.SwitchState, SwitchStates.OFF.value
            )
        ]
        return self.tapHomeApiService.async_set_device_values(device.id, values)

    def async_set_percentage(self, device: Device, percentage=None) -> None:
        if percentage == 0:
            return self.async_turn_off(device)
        else:
            values = [
                self.tapHomeApiService.create_device_value(
                    ValueType.SwitchState, SwitchStates.ON.value
                ),
                self.tapHomeApiService.create_device_value(
                    ValueType.AnalogOutputDesiredValue, percentage
                ),
            ]

            return self.tapHomeApiService.async_set_device_values(device.id, values)
