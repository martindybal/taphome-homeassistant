from enum import Enum


class ValueChangeResult(Enum):
    CHANGED = 1
    NOT_CHANGED = 2
    FAILED = 3

    @staticmethod
    def from_string(value: str):
        return {
            "CHANGED": ValueChangeResult.CHANGED,
            "NOT_CHANGED": ValueChangeResult.NOT_CHANGED,
            "NOTCHANGED": ValueChangeResult.NOT_CHANGED,
            "FAILED": ValueChangeResult.FAILED,
        }[value.upper()]