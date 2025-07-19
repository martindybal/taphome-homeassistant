"""Base state class for TapHome devices."""

from enum import Enum
import logging
from typing import TypeVar

from .value_type import ValueType

_LOGGER = logging.getLogger(__name__)


class TapHomeState:
    """Base class holding raw values from TapHome."""

    def __init__(
        self,
        device_values: dict | None,
    ):
        """Store ``device_values`` for future lookups."""
        self._device_values = device_values if device_values else {}

    def __eq__(self, other):
        """Return ``True`` if ``other`` has the same values."""
        if isinstance(other, TapHomeState):
            return self._device_values == other._device_values

        return False

    TEnum = TypeVar("TEnum", bound=Enum)

    def get_device_enum_value(
        self, enum_type: type[TEnum], value_type: ValueType
    ) -> TEnum | None:
        """Return ``enum_type`` Enum representation of ``value_type``."""
        value = self.get_device_value(value_type)
        try:
            return enum_type(value)
        except (ValueError, TypeError):
            _LOGGER.warning(
                "Failed to create enum %s with value %s",
                enum_type.__name__,
                value,
            )
            return None

    def get_device_bool_value(self, value_type: ValueType) -> bool | None:
        """Return boolean representation of ``value_type``."""
        return self.get_device_value(value_type) == 1

    def get_device_int_value(self, value_type: ValueType) -> int | None:
        """Return integer representation of ``value_type`` or None."""
        value = self.get_device_value(value_type)
        try:
            if value is None:
                return None
            return int(value)
        except (TypeError, ValueError):
            return None

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
