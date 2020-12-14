from .ValueChangeResult import ValueChangeResult
from .ValueType import ValueType
from .TapHomeApiService import TapHomeApiService
from .DeviceServiceHelper import __DeviceServiceHelper as DeviceServiceHelper


class CoverState:
    def __init__(self, blinds_level, blinds_slope, manual_timeout, operation_mode):
        self._blinds_level = blinds_level
        self._blinds_slope = blinds_slope
        self._manual_timeout = manual_timeout
        self._operation_mode = operation_mode

    @property
    def blinds_level(self):
        return self._blinds_level

    @property
    def blinds_slope(self):
        return self._blinds_slope

    @property
    def manual_timeout(self):
        return self._manual_timeout

    @property
    def operation_mode(self):
        return self._operation_mode


class CoverService:
    def __init__(self, tapHomeApiService: TapHomeApiService):
        self.tapHomeApiService = tapHomeApiService

    async def async_get_cover_state(self, coverId: int) -> CoverState:
        cover_values = await self.tapHomeApiService.async_get_device_values(coverId)

        blinds_level = DeviceServiceHelper.get_device_value(
            cover_values, ValueType.BlindsLevel
        )
        blinds_slope = DeviceServiceHelper.get_device_value(
            cover_values, ValueType.BlindsSlope
        )
        manual_timeout = DeviceServiceHelper.get_device_value(
            cover_values, ValueType.ManualTimeout
        )
        operation_mode = DeviceServiceHelper.get_device_value(
            cover_values, ValueType.OperationMode
        )

        return CoverState(blinds_level, blinds_slope, manual_timeout, operation_mode)

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