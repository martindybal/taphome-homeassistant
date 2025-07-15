import logging

from .value_type import ValueType

_LOGGER = logging.getLogger(__name__)


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

    def get_device_bool_value(self, value_type: ValueType) -> bool | None:
        return self.get_device_value(value_type) == 1

    def get_device_value(self, value_type: ValueType) -> float | None:
        value = next(
            (
                device_value["value"]
                for device_value in self._device_values
                if device_value.get("valueTypeId") == value_type.value
            ),
            None,
        )
        return None if value == "NaN" else value
