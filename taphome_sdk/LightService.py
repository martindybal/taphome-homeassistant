from .Device import Device
from .SwitchStates import SwitchStates
from .taphome_device_state import TapHomeState
from .TapHomeApiService import TapHomeApiService
from .ValueChangeResult import ValueChangeResult
from .ValueType import ValueType


class LightState(TapHomeState):
    def __init__(
        self,
        light_values: dict,
    ):
        super().__init__(light_values)

        self.switch_state = SwitchStates(
            self.get_device_value(light_values, ValueType.SwitchState)
        )

        self.brightness = self.get_device_value(
            light_values, ValueType.AnalogOutputValue
        )

        if self.brightness is None:
            self.brightness = self.get_device_value(
                light_values, ValueType.HueBrightness
            )

        self.hue = self.get_device_value(light_values, ValueType.HueDegrees)
        self.saturation = self.get_device_value(light_values, ValueType.Saturation)

    def __eq__(self, other):
        if isinstance(other, LightState):
            return (
                super().__eq__(other)
                and self.switch_state == other.switch_state
                and self.brightness == other.brightness
                and self.hue == other.hue
                and self.saturation == other.saturation
            )

        return False


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
            if ValueType.AnalogOutputValue in device.supported_values:
                values.append(
                    self.tapHomeApiService.create_device_value(
                        ValueType.AnalogOutputValue, brightness
                    )
                )
            else:
                values.append(
                    self.tapHomeApiService.create_device_value(
                        ValueType.HueBrightness, brightness
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
