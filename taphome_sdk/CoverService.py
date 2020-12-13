from .ValueChangeResult import ValueChangeResult
from .ValueType import ValueType
from .SwitchState import SwitchState
from .TapHomeHttpClientFactory import TapHomeHttpClientFactory
from .TapHomeApiService import TapHomeApiService


class CoverService:
    def __init__(self, tapHomeApiService: TapHomeApiService):
        self.tapHomeApiService = tapHomeApiService

    async def async_get_cover_state(self, coverId: int):
        coverValues = await self.tapHomeApiService.async_get_device_values(coverId)

        state = dict()
        state[ValueType.BlindsLevel] = self.get_light_value(
            coverValues, ValueType.BlindsLevel
        )

        state[ValueType.BlindsSlope] = self.get_light_value(
            coverValues, ValueType.BlindsSlope
        )

        state[ValueType.ManualTimeout] = self.get_light_value(
            coverValues, ValueType.ManualTimeout
        )

        state[ValueType.OperationMode] = self.get_light_value(
            coverValues, ValueType.OperationMode
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

    def async_set_cover_position(self, coverId, position) -> ValueChangeResult:
        values = [
            self.tapHomeApiService.create_device_value(ValueType.BlindsLevel, position)
        ]

        return self.tapHomeApiService.async_set_device_values(coverId, values)

    def async_set_cover_tilt(self, coverId, tilt) -> ValueChangeResult:
        values = [
            self.tapHomeApiService.create_device_value(ValueType.BlindsSlope, tilt)
        ]

        return self.tapHomeApiService.async_set_device_values(coverId, values)