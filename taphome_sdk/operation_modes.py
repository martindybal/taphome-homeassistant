"""Enumeration utilities for TapHome operation modes."""

from enum import Enum
from typing import Optional


class OperationModes(Enum):
    """Known modes in which a device can operate."""

    MANUAL = 1
    AUTO = 2

    @staticmethod
    def create(value: int) -> Optional["OperationModes"]:
        """Return the enum member for ``value`` if present."""
        return OperationModes._value2member_map_.get(value)
