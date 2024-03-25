from .device import Device
from .switch_states import SwitchStates
from .taphome_api_service import TapHomeApiService
from .taphome_device_state import TapHomeState
from .value_type import ValueType


class PercentageState(TapHomeState):
    def __init__(
        self,
        percentage_values: dict,
    ):
        super().__init__(percentage_values)
        if self.get_device_value(ValueType.AnalogOutputValue) is not None:
            self.create_analog_state()
        else:
            self.create_blind_state()

    def create_analog_state(self) -> None:
        self.percentage = self.get_device_value(ValueType.AnalogOutputValue)
        self.switch_state = SwitchStates(self.get_device_value(ValueType.SwitchState))

    def create_blind_state(self) -> None:
        self.percentage = self.get_device_value(ValueType.BlindsLevel)
        switch_state = self.percentage != 0
        self.switch_state = SwitchStates(switch_state)


class PercentageService:
    def __init__(self, taphome_api_service: TapHomeApiService):
        self.taphome_api_service = taphome_api_service
        self.analog_percentage_service = AnalogPercentageService(taphome_api_service)
        self.blind_percentage_service = BlindPercentageService(taphome_api_service)

    async def async_get_state(self, device: Device) -> PercentageState:
        percentage_values = await self.taphome_api_service.async_get_device_values(
            device.deviceId
        )
        return PercentageState(percentage_values)

    def async_turn_on(self, device: Device) -> None:
        percentage_service = self._get_percentage_service(device)
        return percentage_service.async_turn_on(device)

    def async_turn_off(self, device: Device) -> None:
        percentage_service = self._get_percentage_service(device)
        return percentage_service.async_turn_off(device)

    def async_set_percentage(self, device: Device, percentage=None) -> None:
        percentage_service = self._get_percentage_service(device)
        return percentage_service.async_set_percentage(device, percentage)

    def _get_percentage_service(self, device: Device) -> None:
        if device.supports_value(ValueType.AnalogOutputDesiredValue):
            return self.analog_percentage_service
        elif device.supports_value(ValueType.BlindsLevel):
            return self.blind_percentage_service


class AnalogPercentageService:
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

    def async_set_percentage(self, device: Device, percentage=None) -> None:
        if percentage == 0:
            return self.async_turn_off(device)
        else:
            values = [
                self.taphome_api_service.create_device_value(
                    ValueType.SwitchState, SwitchStates.ON.value
                ),
                self.taphome_api_service.create_device_value(
                    ValueType.AnalogOutputDesiredValue, percentage
                ),
            ]

            return self.taphome_api_service.async_set_device_values(device.id, values)


class BlindPercentageService:
    def __init__(self, taphome_api_service: TapHomeApiService):
        self.taphome_api_service = taphome_api_service

    def async_turn_on(self, device: Device) -> None:
        return self.async_set_percentage(device, 1)

    def async_turn_off(self, device: Device) -> None:
        return self.async_set_percentage(device, 0)

    def async_set_percentage(self, device: Device, percentage=None) -> None:
        values = [
            self.taphome_api_service.create_device_value(
                ValueType.BlindsLevel, percentage
            ),
        ]

        return self.taphome_api_service.async_set_device_values(device.id, values)
