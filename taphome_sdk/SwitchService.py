from .Device import Device
from .ValueChangeResult import ValueChangeResult
from .ValueType import ValueType
from .TapHomeApiService import TapHomeApiService
from .DeviceServiceHelper import __DeviceServiceHelper as DeviceServiceHelper
from .SwitchStates import SwitchStates


class SwitchState:
    def __init__(
        self,
        switch_state: SwitchStates,
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
        switch_state = SwitchStates(
            DeviceServiceHelper.get_device_value(switchValues, ValueType.SwitchState)
        )

        return SwitchState(switch_state)

    def async_turn_on_switch(self, device: Device) -> ValueChangeResult:
        values = [
            self.tapHomeApiService.create_device_value(
                ValueType.SwitchState, SwitchStates.ON.value
            )
        ]

        return self.tapHomeApiService.async_set_device_values(device.deviceId, values)

    def async_turn_off_switch(self, device: Device) -> ValueChangeResult:
        values = [
            self.tapHomeApiService.create_device_value(
                ValueType.SwitchState, SwitchStates.OFF.value
            )
        ]
        return self.tapHomeApiService.async_set_device_values(device.deviceId, values)
