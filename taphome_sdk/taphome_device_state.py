import typing

from .device_operation_mode import DeviceOperationMode
from .ValueType import ValueType


class TapHomeState:
    OperationMode: DeviceOperationMode

    def __init__(
        self,
        device_values: dict,
    ):
        self._device_values = device_values
        self.operation_mode = DeviceOperationMode(
            self.get_device_value(ValueType.OperationMode)
        )

    def __eq__(self, other):
        if isinstance(other, TapHomeState):
            return self._device_values == other._device_values

        return False

    def get_device_value(self, vylue_type: ValueType):
        try:
            return next(
                device_value
                for device_value in self._device_values
                if device_value["valueTypeId"] == vylue_type.value
            )["value"]
        except:
            return None
