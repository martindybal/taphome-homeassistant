import typing

from .device_operation_mode import DeviceOperationMode
from .ValueType import ValueType


class TapHomeState:
    OperationMode: DeviceOperationMode

    def __init__(
        self,
        values: dict,
    ):
        self.operation_mode = DeviceOperationMode(
            self.get_device_value(values, ValueType.OperationMode)
        )

    def __eq__(self, other):
        if isinstance(other, TapHomeState):
            return self.operation_mode == other.operation_mode

        return False

    def get_device_value(self, device_values: dict, vylue_type: ValueType):
        try:
            return next(
                device_value
                for device_value in device_values
                if device_value["valueTypeId"] == vylue_type.value
            )["value"]
        except:
            return None