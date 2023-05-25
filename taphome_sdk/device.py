import logging
from typing import Optional

from .value_type import ValueType

_LOGGER = logging.getLogger(__name__)


class SupportedValue:
    def __init__(
        self,
        value_type: ValueType,
        read_only: bool,
        allowed_values: list[dict],
        min_value: Optional[int],
        max_value: Optional[int],
    ) -> None:
        self._value_type = value_type
        self._read_only = read_only
        self._allowed_values = allowed_values
        self._min_value = min_value
        self._max_value = max_value

    @property
    def value_type(self) -> ValueType:
        return self._value_type

    @property
    def read_only(self) -> bool:
        return self._read_only

    @property
    def allowed_values(self) -> list[dict]:
        return self._allowed_values

    @property
    def min_value(self) -> Optional[int]:
        return self._min_value

    @property
    def max_value(self) -> Optional[int]:
        return self._max_value


class Device:
    def __init__(
        self,
        id: int,
        name: str,
        description: str,
        type: str,
        supported_values,
    ):
        self._id = id
        self._name = name
        self._description = description
        self._type = type
        self._supported_values = supported_values

    @staticmethod
    def create(device: dict):
        id = device["deviceId"]
        name = device["name"]
        description = device["description"]
        type = device["type"]
        supported_values = {}
        for supported_value in device["supportedValues"]:
            try:
                value_type = ValueType(supported_value["valueTypeId"])
                read_only = supported_value["readOnly"]
                allowed_values = supported_value.get("enumeratedValues", [])
                min_value = supported_value.get("minValue")
                max_value = supported_value.get("maxValue")
                supported_values[value_type] = SupportedValue(
                    value_type, read_only, allowed_values, min_value, max_value
                )

            except Exception:
                _LOGGER.warning(f"{supported_value} is not a valid ValueType")
        return Device(id, name, description, type, supported_values)

    @property
    def id(self):
        return self._id

    @property
    def name(self):
        return self._name

    @property
    def description(self):
        return self._description

    @property
    def type(self):
        return self._type

    @property
    def supported_values(self) -> dict[ValueType, SupportedValue]:
        return self._supported_values

    def supports_value(self, value_type: ValueType):
        return value_type in self.supported_values
