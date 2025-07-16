"""Enumeration utilities for TapHome operation modes."""

from enum import Enum


class OperationModes(Enum):
    """Known modes in which a device can operate."""

    MANUAL = 1
    AUTO = 2
