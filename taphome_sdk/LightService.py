from .ValueChangeResult import ValueChangeResult
from .ValueType import ValueType
from .SwitchState import SwitchState
from .TapHomeApiService import TapHomeApiService
from .DeviceServiceHelper import __DeviceServiceHelper as DeviceServiceHelper


class LightService:
    def __init__(self, tapHomeApiService: TapHomeApiService):
        self.tapHomeApiService = tapHomeApiService

    async def async_get_light_state(self, deviceId: int):
        lightValues = await self.tapHomeApiService.async_get_device_values(deviceId)

        state = dict()
        state[ValueType.SwitchState] = SwitchState(
            self.get_light_value(lightValues, ValueType.SwitchState)
        )

        state[ValueType.HueBrightness] = DeviceServiceHelper.get_device_value(
            lightValues, ValueType.HueBrightness
        )

        state[ValueType.HueDegrees] = DeviceServiceHelper.get_device_value(
            lightValues, ValueType.HueDegrees
        )

        state[ValueType.Saturation] = DeviceServiceHelper.get_device_value(
            lightValues, ValueType.Saturation
        )

        return state

    def async_turn_on_light(
        self, lightId: int, brightness=None, hue=None, saturation=None
    ) -> ValueChangeResult:
        values = [
            self.tapHomeApiService.create_device_value(
                ValueType.SwitchState, SwitchState.ON.value
            )
        ]

        if brightness is not None:
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

        return self.tapHomeApiService.async_set_device_values(lightId, values)

    def async_turn_off_light(self, lightId: int) -> ValueChangeResult:
        values = [
            self.tapHomeApiService.create_device_value(
                ValueType.SwitchState, SwitchState.OFF.value
            )
        ]
        return self.tapHomeApiService.async_set_device_values(lightId, values)