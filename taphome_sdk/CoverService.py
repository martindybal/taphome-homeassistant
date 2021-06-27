import logging

from .Device import Device
from .TapHomeApiService import TapHomeApiService
from .ValueChangeResult import ValueChangeResult
from .ValueType import ValueType
from .taphome_device_state import TapHomeState

_LOGGER = logging.getLogger(__name__)


class CoverState(TapHomeState):
    def __init__(
        self,
        switch_values: dict,
    ):
        super().__init__(switch_values)
        self.blinds_level = self.get_device_value(ValueType.BlindsLevel)
        self.blinds_slope = self.get_device_value(ValueType.BlindsSlope)


class CoverService:
    def __init__(self, taphome_api_service: TapHomeApiService):
        self.taphome_api_service = taphome_api_service

    async def async_get_state(self, device: Device) -> CoverState:
        try:
            cover_values = await self.taphome_api_service.async_get_device_values(
                device.id
            )

            return CoverState(cover_values)
        except:
            _LOGGER.error(f"TapHome async_get_state for {device.id} failed")
            return None

    def async_set_level(self, device: Device, position) -> None:
        values = [
            self.taphome_api_service.create_device_value(
                ValueType.BlindsLevel, position
            )
        ]

        return self.taphome_api_service.async_set_device_values(device.id, values)

    def async_set_slope(self, device: Device, tilt) -> None:
        values = [
            self.taphome_api_service.create_device_value(ValueType.BlindsSlope, tilt)
        ]

        return self.taphome_api_service.async_set_device_values(device.id, values)
