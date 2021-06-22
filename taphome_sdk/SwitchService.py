from voluptuous.schema_builder import Undefined
from .Device import Device
from .ValueChangeResult import ValueChangeResult
from .ValueType import ValueType
from .TapHomeApiService import TapHomeApiService
from .taphome_device_state import TapHomeState
from .DeviceServiceHelper import __DeviceServiceHelper as DeviceServiceHelper
from .SwitchStates import SwitchStates

import logging

_LOGGER = logging.getLogger(__name__)


class SwitchState(TapHomeState):
    def __init__(
        self,
        switch_values: dict,
    ):
        super().__init__(switch_values)
        self.switch_state = SwitchStates(
            self.get_device_value(switch_values, ValueType.SwitchState)
        )

    def __eq__(self, other):
        if isinstance(other, SwitchState):
            return super().__eq__(other) and self.switch_state == other.switch_state

        return False


class SwitchService:
    def __init__(self, taphome_api_service: TapHomeApiService):
        self.taphome_api_service = taphome_api_service

    async def async_get_switch_state(self, device_id: int):
        try:
            switch_values = await self.taphome_api_service.async_get_device_values(
                device_id
            )

            if switch_values is None:
                return None

            return SwitchState(switch_values)
        except:
            _LOGGER.exception(f"async_get_switch_state for {device_id} fails")
            return None

    def async_turn_switch(self, switch_state: SwitchStates, device: Device) -> None:
        values = [
            self.taphome_api_service.create_device_value(
                ValueType.SwitchState, switch_state.value
            )
        ]

        return self.taphome_api_service.async_set_device_values(device.id, values)