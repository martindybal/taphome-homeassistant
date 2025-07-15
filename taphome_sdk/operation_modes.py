from enum import Enum
from typing import Optional


class OperationModes(Enum):
    MANUAL = 1
    AUTO = 2

    @staticmethod
    def create(value: int) -> Optional["OperationModes"]:
        return OperationModes._value2member_map_.get(value)
