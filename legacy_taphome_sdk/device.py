"""Models TapHome devices and supported value types."""

from dataclasses import dataclass
import logging

from .value_type import ValueType

_LOGGER = logging.getLogger(__name__)


@dataclass(slots=True)
class EnumeratedValue:
    """Describe a allowed value for SupportedValue."""

    value: int
    name: str
    is_enabled: bool

    @classmethod
    def from_dict(cls, data: dict) -> "EnumeratedValue":
        """Create EnumeratedValue instance from dictionary."""
        return cls(value=data["value"], name=data["name"], is_enabled=data["isEnabled"])


@dataclass(slots=True)
class SupportedValue:
    """Describe a supported value on a TapHome device."""

    value_type: ValueType
    read_only: bool
    allowed_values: list[EnumeratedValue]
    min_value: int | None
    max_value: int | None

    @classmethod
    def from_dict(cls, data: dict) -> "SupportedValue":
        """Create SupportedValue instance from dictionary."""
        return cls(
            value_type=ValueType(data["valueTypeId"]),
            read_only=data["readOnly"],
            allowed_values=[
                EnumeratedValue.from_dict(value)
                for value in data.get("enumeratedValues", [])
            ],
            min_value=data.get("minValue"),
            max_value=data.get("maxValue"),
        )


@dataclass(slots=True)
class Device:
    """Representation of a device connected to TapHome."""

    id: int
    device_type: str
    usage: str | None
    name: str
    description: str
    zone: str | None
    category: str | None
    supported_values: dict[ValueType, SupportedValue]

    @classmethod
    def from_dict(cls, data: dict) -> "Device":
        """Create Device instance from dictionary."""
        supported_values: dict[ValueType, SupportedValue] = {}
        for supported_value in data["supportedValues"]:
            try:
                supported_value = SupportedValue.from_dict(supported_value)
                supported_values[supported_value.value_type] = supported_value
            except ValueError:
                _LOGGER.warning("%s is not a valid ValueType", supported_value)

        return Device(
            data["deviceId"],
            data["type"],
            data.get("usage"),
            data["name"],
            data["description"],
            data.get("zone"),
            data.get("category"),
            supported_values,
        )

    def supports_value(self, value_type: ValueType) -> bool:
        """Return ``True`` if ``value_type`` is supported by the device."""
        return value_type in self.supported_values
