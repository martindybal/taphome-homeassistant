from enum import Enum
from typing import TypeVar

TEnum = TypeVar("TEnum", bound=Enum)


class Helpers:
    """Helper functions for TapHome integration."""

    @staticmethod
    def enum_from_string(enum_type: type[TEnum], value: str) -> TEnum:
        """Create a ButtonAction from a string."""
        for enum_value in enum_type:
            if enum_value.name.replace("_", "").lower() == value.lower():
                return enum_value
        raise ValueError(f"Unknown button action: {value}")
