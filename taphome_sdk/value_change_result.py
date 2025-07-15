"""Enum helpers describing the result of a value change."""

from enum import Enum


class ValueChangeResult(Enum):
    """Possible outcomes of setting a value via the API."""

    CHANGED = 1
    NOT_CHANGED = 2
    FAILED = 3

    @staticmethod
    def from_string(value: str):
        """Map string ``value`` to the corresponding enum member."""
        return {
            "CHANGED": ValueChangeResult.CHANGED,
            "NOT_CHANGED": ValueChangeResult.NOT_CHANGED,
            "NOTCHANGED": ValueChangeResult.NOT_CHANGED,
            "FAILED": ValueChangeResult.FAILED,
        }[value.upper()]
