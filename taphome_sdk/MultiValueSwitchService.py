import logging

from .Device import Device
from .TapHomeApiService import TapHomeApiService
from .taphome_device_state import TapHomeState
from .ValueChangeResult import ValueChangeResult
from .ValueType import ValueType

_LOGGER = logging.getLogger(__name__)


class MultiValueSwitchState(TapHomeState):
    def __init__(
        self,
        multi_value_switch_values: dict,
    ):
        super().__init__(multi_value_switch_values)
        self.multi_value_switch_state: int = self.get_device_value(
            multi_value_switch_values, ValueType.MultiValueSwitchState
        )

    def __eq__(self, other):
        if isinstance(other, MultiValueSwitchState):
            return (
                super().__eq__(other)
                and self.multi_value_switch_state == other.multi_value_switch_state
            )

        return False


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
