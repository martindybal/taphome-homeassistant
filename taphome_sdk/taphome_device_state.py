from .value_type import ValueType


class TapHomeState:
    def __init__(
        self,
        device_values: dict,
    ):
        self._device_values = device_values

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
