import logging

from .device import Device
from .taphome_api_service import TapHomeApiService
from .taphome_device_state import TapHomeState
from .value_type import ValueType

_LOGGER = logging.getLogger(__name__)


class TimeState(TapHomeState):
    def __init__(
        self,
        switch_values: dict,
    ):
        super().__init__(switch_values)
        self.total_seconds = self.get_device_value(ValueType.SessionDuration)


class TimeService:
    def __init__(self, taphome_api_service: TapHomeApiService):
        self.taphome_api_service = taphome_api_service

    async def async_get_state(self, device: Device):
        try:
            time_values = await self.taphome_api_service.async_get_device_values(
                device.id
            )

            if time_values is None:
                return None

            return TimeState(time_values)
        except:
            _LOGGER.error("TapHome async_get_state for %s failed", device.id)
            return None

    def async_set_value(self, total_seconds: int, device: Device) -> None:
        values = [
            self.taphome_api_service.create_device_value(
                # Be care here. Only variable state can be changed. Value conversions are readonly.
                ValueType.VariableState,
                total_seconds,
            )
        ]

        return self.taphome_api_service.async_set_device_values(device.id, values)
