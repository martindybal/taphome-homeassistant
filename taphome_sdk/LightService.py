from .ValueChangeResult import ValueChangeResult
from .ValueType import ValueType
from .SwitchState import SwitchState
from .TapHomeHttpClientFactory import TapHomeHttpClientFactory
from .TapHomeApiService import TapHomeApiService


class LightService:
    def __init__(self, tapHomeApiService: TapHomeApiService):
        self.tapHomeApiService = tapHomeApiService

    async def async_get_light_state(self, deviceId: int):
        lightValues = await self.tapHomeApiService.async_get_device_values(deviceId)

        state = dict()
        state[ValueType.SwitchState] = SwitchState(
            self.get_light_value(lightValues, ValueType.SwitchState)
        )

        state[ValueType.HueBrightness] = self.get_light_value(
            lightValues, ValueType.HueBrightness
        )

        state[ValueType.HueDegrees] = self.get_light_value(
            lightValues, ValueType.HueDegrees
        )

        state[ValueType.Saturation] = self.get_light_value(
            lightValues, ValueType.Saturation
        )

        return state

    def get_light_value(self, lightValues: dict, vylueType: ValueType):
        try:
            return next(
                lightValue
                for lightValue in lightValues
                if lightValue["valueTypeId"] == vylueType.value
            )["value"]
        except:
            return None

    def async_turn_on_light(
        self, lightId: int, brightness=None, hue=None, saturation=None
    ) -> ValueChangeResult:
        values = [
            self.tapHomeApiService.create_device_value(
                ValueType.SwitchState, SwitchState.ON.value
            )
        ]

        if brightness:
            values.append(
                self.tapHomeApiService.create_device_value(
                    ValueType.HueBrightness, brightness
                )
            )

        if hue:
            values.append(
                self.tapHomeApiService.create_device_value(ValueType.HueDegrees, hue)
            )

        if saturation:
            values.append(
                self.tapHomeApiService.create_device_value(
                    ValueType.Saturation, saturation
                )
            )

        return self.tapHomeApiService.async_set_device_values(lightId, values)

    def async_turn_off_light(self, lightId: int) -> ValueChangeResult:
        values = [
            self.tapHomeApiService.create_device_value(
                ValueType.SwitchState, SwitchState.OFF.value
            )
        ]
        return self.tapHomeApiService.async_set_device_values(lightId, values)