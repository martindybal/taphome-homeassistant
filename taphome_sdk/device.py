"""Models TapHome devices and supported value types."""

import logging

from .value_type import ValueType

_LOGGER = logging.getLogger(__name__)


class SupportedValue:
    """Describe a supported value on a TapHome device."""

    def __init__(
        self,
        value_type: ValueType,
        read_only: bool,
        allowed_values: list[dict],
        min_value: int | None,
        max_value: int | None,
    ) -> None:
        """Initialize a supported value definition."""
        self._value_type = value_type
        self._read_only = read_only
        self._allowed_values = allowed_values
        self._min_value = min_value
        self._max_value = max_value

    @property
    def value_type(self) -> ValueType:
        """Return the ``ValueType`` of this supported value."""
        return self._value_type

    @property
    def read_only(self) -> bool:
        """Return ``True`` if the value is read only."""
        return self._read_only

    @property
    def allowed_values(self) -> list[dict]:
        """Return list of allowed values for enumerated types."""
        return self._allowed_values

    @property
    def min_value(self) -> int | None:
        """Return minimum value if defined."""
        return self._min_value

    @property
    def max_value(self) -> int | None:
        """Return maximum value if defined."""
        return self._max_value


class Device:
    """Representation of a device connected to TapHome."""

    def __init__(
        self,
        id: int,
        name: str,
        description: str,
        zone: str | None,
        category: str | None,
        type: str,
        supported_values,
    ):
        """Create a device description from raw parameters."""
        self._id = id
        self._name = name
        self._description = description
        self._zone = zone
        self._category = category
        self._type = type
        self._supported_values = supported_values

    @staticmethod
    def create(device: dict):
        """Instantiate ``Device`` from raw ``device`` dictionary."""
        deviceId = device["deviceId"]
        name = device["name"]
        description = device["description"]
        zone = device.get("zone")
        category = device.get("category")
        deviceType = device["type"]
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

            except ValueError:
                _LOGGER.warning("%s is not a valid ValueType", supported_value)
        return Device(
            deviceId, name, description, zone, category, deviceType, supported_values
        )

    @property
    def id(self):
        """Return the device identifier."""
        return self._id

    @property
    def name(self):
        """Return the device name."""
        return self._name

    @property
    def description(self):
        """Return the device description."""
        return self._description

    @property
    def zone(self):
        """Return the device zone if any."""
        return self._zone

    @property
    def category(self):
        """Return the device category if any."""
        return self._category

    @property
    def type(self):
        """Return the device type string."""
        return self._type

    @property
    def supported_values(self) -> dict[ValueType, SupportedValue]:
        """Return mapping of supported value types."""
        return self._supported_values

    def supports_value(self, value_type: ValueType):
        """Return ``True`` if ``value_type`` is supported by the device."""
        return value_type in self.supported_values
