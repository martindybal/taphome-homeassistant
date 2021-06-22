from voluptuous.schema_builder import Undefined
from .Device import Device
from .ValueChangeResult import ValueChangeResult
from .ValueType import ValueType
from .TapHomeApiService import TapHomeApiService
from .DeviceServiceHelper import __DeviceServiceHelper as DeviceServiceHelper
from .SwitchStates import SwitchStates

import logging

_LOGGER = logging.getLogger(__name__)


class SwitchState:
    def __init__(
        self,
        switch_state: SwitchStates,
    ):
        self.switch_state = switch_state

    @staticmethod
    def create(values: dict):
        switch_state = SwitchStates(
            DeviceServiceHelper.get_device_value(values, ValueType.SwitchState)
        )
        return SwitchState(switch_state)


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

            return SwitchState.create(switch_values)
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