import logging

from .device import Device
from .taphome_api_service import TapHomeApiService
from .taphome_device_state import TapHomeState
from .value_type import ValueType

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

    def async_set_level(self, device: Device, position, tilt=None) -> None:
        values = [
            self.taphome_api_service.create_device_value(
                ValueType.BlindsLevel, position
            )
        ]

        if tilt is not None:
            values.append(self.taphome_api_service.create_device_value(ValueType.BlindsSlope, tilt))

        return self.taphome_api_service.async_set_device_values(device.id, values)

    def async_set_slope(self, device: Device, tilt) -> None:
        values = [
            self.taphome_api_service.create_device_value(ValueType.BlindsSlope, tilt)
        ]

        return self.taphome_api_service.async_set_device_values(device.id, values)
