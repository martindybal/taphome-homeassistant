from .Device import Device
from .ValueChangeResult import ValueChangeResult
from .ValueType import ValueType
from .TapHomeApiService import TapHomeApiService
from .DeviceServiceHelper import __DeviceServiceHelper as DeviceServiceHelper
from .SwitchState import SwitchState

class SwitchIntState:
    def __init__(
        self,
        switch_state: SwitchState,
    ):
        self._switch_state = switch_state

    @property
    def switch_state(self):
        return self._switch_state

class SwitchService:
    def __init__(self, tapHomeApiService: TapHomeApiService):
        self.tapHomeApiService = tapHomeApiService

    async def async_get_switch_state(self, device: Device):
        switchValues = await self.tapHomeApiService.async_get_device_values(
            device.deviceId
        )
        switch_state = SwitchState(
            DeviceServiceHelper.get_device_value(switchValues, ValueType.SwitchState)
        )
        
        return SwitchIntState(switch_state)

    def async_turn_on_switch(
        self, device: Device
    ) -> ValueChangeResult:
        values = [
            self.tapHomeApiService.create_device_value(
                ValueType.SwitchState, SwitchState.ON.value
            )
        ]
        
        return self.tapHomeApiService.async_set_device_values(device.deviceId, values)

    def async_turn_off_switch(self, device: Device) -> ValueChangeResult:
        values = [
            self.tapHomeApiService.create_device_value(
                ValueType.SwitchState, SwitchState.OFF.value
            )
        ]
        return self.tapHomeApiService.async_set_device_values(device.deviceId, values)
