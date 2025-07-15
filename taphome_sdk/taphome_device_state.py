"""Base state class for TapHome devices."""

import logging

from .value_type import ValueType

_LOGGER = logging.getLogger(__name__)


class TapHomeState:
    """Base class holding raw values from TapHome."""

    def __init__(
        self,
        device_values: dict,
    ):
        """Store ``device_values`` for future lookups."""
        self._device_values = device_values

    def __eq__(self, other):
        """Return ``True`` if ``other`` has the same values."""
        if isinstance(other, TapHomeState):
            return self._device_values == other._device_values

        return False

    def get_device_bool_value(self, value_type: ValueType) -> bool | None:
        """Return boolean representation of ``value_type``."""
        return self.get_device_value(value_type) == 1

    def get_device_value(self, value_type: ValueType) -> float | None:
        """Return value for ``value_type`` if available."""
        value = next(
            (
                device_value["value"]
                for device_value in self._device_values
                if device_value.get("valueTypeId") == value_type.value
            ),
            None,
        )
        return None if value == "NaN" else value
