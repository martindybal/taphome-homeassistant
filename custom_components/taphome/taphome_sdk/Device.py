from .ValueType import ValueType


class Device:
    def __init__(
        self,
        deviceId: int,
        name: str,
        description: str,
        type: str,
        supportedValues: list,
    ):
        self._deviceId = deviceId
        self._name = name
        self._description = description
        self._type = type
        self._supportedValues = supportedValues

    @staticmethod
    def create(device: dict):
        deviceId = device["deviceId"]
        name = device["name"]
        description = device["description"]
        type = device["type"]
        supportedValues = list(
            map(
                lambda supportedValue: ValueType(supportedValue["valueTypeId"]),
                device["supportedValues"],
            )
        )

        return Device(deviceId, name, description, type, supportedValues)

    @property
    def deviceId(self):
        return self._deviceId

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
    def supportedValues(self):
        return self._supportedValues
