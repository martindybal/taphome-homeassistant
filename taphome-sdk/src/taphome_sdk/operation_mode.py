"""Enumeration utilities for TapHome operation modes."""

from enum import Enum


class OperationMode(Enum):
    """Known modes in which a device can operate."""

    NONE = 0
    MANUAL = 1
    AUTO = 2
