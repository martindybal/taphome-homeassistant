import logging
from .ValueType import ValueType


_LOGGER = logging.getLogger(__name__)


class Device:
    def __init__(
        self,
        id: int,
        name: str,
        description: str,
        type: str,
        supported_values: list,
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
        supported_values = []
        for supported_value in device["supportedValues"]:
            try:
                supported_values.append(ValueType(supported_value["valueTypeId"]))
            except Exception:
                _LOGGER.exception(f"Unkown ValueType")

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
    def supported_values(self):
        return self._supported_values
