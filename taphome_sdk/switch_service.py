import logging

from voluptuous.schema_builder import Undefined

from .device import Device
from .switch_states import SwitchStates
from .taphome_api_service import TapHomeApiService
from .value_type import ValueType
from .taphome_device_state import TapHomeState

_LOGGER = logging.getLogger(__name__)


class SwitchState(TapHomeState):
    def __init__(
        self,
        switch_values: dict,
    ):
        super().__init__(switch_values)
        self.switch_state = SwitchStates(self.get_device_value(ValueType.SwitchState))


class SwitchService:
    def __init__(self, taphome_api_service: TapHomeApiService):
        self.taphome_api_service = taphome_api_service

    async def async_get_state(self, device: Device):
        try:
            switch_values = await self.taphome_api_service.async_get_device_values(
                device.id
            )

            if switch_values is None:
                return None

            return SwitchState(switch_values)
        except:
            _LOGGER.error(f"TapHome async_get_state for {device.id} failed")
            return None

    def async_turn(self, switch_state: SwitchStates, device: Device) -> None:
        values = [
            self.taphome_api_service.create_device_value(
                ValueType.SwitchState, switch_state.value
            )
        ]

        return self.taphome_api_service.async_set_device_values(device.id, values)
