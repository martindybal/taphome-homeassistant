import logging

from .device import Device
from .taphome_api_service import TapHomeApiService
from .value_change_result import ValueChangeResult
from .value_type import ValueType
from .taphome_device_state import TapHomeState

_LOGGER = logging.getLogger(__name__)


class MultiValueSwitchState(TapHomeState):
    def __init__(
        self,
        multi_value_switch_values: dict,
    ):
        super().__init__(multi_value_switch_values)
        self.multi_value_switch_state: int = self.get_device_value(
            ValueType.MultiValueSwitchState
        )


class MultiValueSwitchService:
    def __init__(self, taphome_api_service: TapHomeApiService):
        self.taphome_api_service = taphome_api_service

    async def async_get_state(self, device: Device) -> MultiValueSwitchState:
        try:
            multi_value_switch_values = (
                await self.taphome_api_service.async_get_device_values(device.id)
            )
            return MultiValueSwitchState(multi_value_switch_values)
        except:
            _LOGGER.error(f"TapHome async_get_state for {device.id} failed")
            return None

    def async_set_value(self, value: int, device: Device) -> ValueChangeResult:
        values = [
            self.taphome_api_service.create_device_value(
                ValueType.MultiValueSwitchState, value
            )
        ]

        return self.taphome_api_service.async_set_device_values(device.id, values)
