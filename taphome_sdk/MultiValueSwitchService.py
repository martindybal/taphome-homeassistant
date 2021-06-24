from .Device import Device
from .TapHomeApiService import TapHomeApiService
from .ValueChangeResult import ValueChangeResult
from .ValueType import ValueType


class MultiValueSwitchState:
    def __init__(
        self,
        multi_value_switch_state: int,
    ):
        self._multi_value_switch_state = multi_value_switch_state

    @property
    def multi_value_switch_state(self):
        return self._multi_value_switch_state


class MultiValueSwitchService:
    def __init__(self, tapHomeApiService: TapHomeApiService):
        self.tapHomeApiService = tapHomeApiService

    async def async_get_multi_value_switch_state(
        self, device: Device
    ) -> MultiValueSwitchState:
        switchValues = await self.tapHomeApiService.async_get_device_values(
            device.deviceId
        )
        multi_value_switch_state = DeviceServiceHelper.get_device_value(
            switchValues, ValueType.MultiValueSwitchState
        )

        return MultiValueSwitchState(multi_value_switch_state)

    def async_set_value(self, device: Device, value: int) -> ValueChangeResult:
        values = [
            self.tapHomeApiService.create_device_value(
                ValueType.MultiValueSwitchState, value
            )
        ]

        return self.tapHomeApiService.async_set_device_values(device.deviceId, values)
