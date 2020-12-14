from .ValueChangeResult import ValueChangeResult
from .ValueType import ValueType
from .TapHomeApiService import TapHomeApiService
from .DeviceServiceHelper import __DeviceServiceHelper as DeviceServiceHelper


class CoverService:
    def __init__(self, tapHomeApiService: TapHomeApiService):
        self.tapHomeApiService = tapHomeApiService

    async def async_get_cover_state(self, coverId: int):
        coverValues = await self.tapHomeApiService.async_get_device_values(coverId)

        state = dict()
        state[ValueType.BlindsLevel] = DeviceServiceHelper.get_device_value(
            coverValues, ValueType.BlindsLevel
        )

        state[ValueType.BlindsSlope] = DeviceServiceHelper.get_device_value(
            coverValues, ValueType.BlindsSlope
        )

        state[ValueType.ManualTimeout] = DeviceServiceHelper.get_device_value(
            coverValues, ValueType.ManualTimeout
        )

        state[ValueType.OperationMode] = DeviceServiceHelper.get_device_value(
            coverValues, ValueType.OperationMode
        )

        return state

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