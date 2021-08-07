from .device import Device
from .switch_states import SwitchStates
from .taphome_api_service import TapHomeApiService
from .value_change_result import ValueChangeResult
from .value_type import ValueType
from .taphome_device_state import TapHomeState


class LightState(TapHomeState):
    def __init__(
        self,
        light_values: dict,
    ):
        super().__init__(light_values)

        self.switch_state = SwitchStates(self.get_device_value(ValueType.SwitchState))

        self.hue = self.get_device_value(ValueType.HueDegrees)
        self.saturation = self.get_device_value(ValueType.Saturation)

        self.brightness = self.get_device_value(ValueType.AnalogOutputValue)
        if self.brightness is None:
            self.brightness = self.get_device_value(ValueType.HueBrightness)


class LightService:
    def __init__(self, tapHomeApiService: TapHomeApiService):
        self.tapHomeApiService = tapHomeApiService

    async def async_get_state(self, device: Device) -> LightState:
        light_values = await self.tapHomeApiService.async_get_device_values(
            device.deviceId
        )

        return LightState(light_values)

    def async_turn_on(
        self, device: Device, brightness=None, hue=None, saturation=None
    ) -> None:
        values = [
            self.tapHomeApiService.create_device_value(
                ValueType.SwitchState, SwitchStates.ON.value
            )
        ]

        if brightness is not None:
            if device.supports_value(ValueType.AnalogOutputDesiredValue):
                values.append(
                    self.tapHomeApiService.create_device_value(
                        ValueType.AnalogOutputDesiredValue, brightness
                    )
                )
            elif device.supports_value(ValueType.HueBrightnessDesiredValue):
                values.append(
                    self.tapHomeApiService.create_device_value(
                        ValueType.HueBrightnessDesiredValue, brightness
                    )
                )

        if hue is not None:
            values.append(
                self.tapHomeApiService.create_device_value(ValueType.HueDegrees, hue)
            )

        if saturation is not None:
            values.append(
                self.tapHomeApiService.create_device_value(
                    ValueType.Saturation, saturation
                )
            )

        return self.tapHomeApiService.async_set_device_values(device.id, values)

    def async_turn_off(self, device: Device) -> None:
        values = [
            self.tapHomeApiService.create_device_value(
                ValueType.SwitchState, SwitchStates.OFF.value
            )
        ]
        return self.tapHomeApiService.async_set_device_values(device.id, values)
