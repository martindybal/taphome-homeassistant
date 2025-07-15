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

    def get_device_bool_value(self, vylue_type: ValueType) -> bool | None:
        return self.get_device_value(vylue_type) == 1

    def get_device_value(self, vylue_type: ValueType) -> float | None:
        try:
            value = next(
                device_value
                for device_value in self._device_values
                if device_value["valueTypeId"] == vylue_type.value
            )["value"]
        except:
            return None
        else:
            return value if value != "NaN" else None
