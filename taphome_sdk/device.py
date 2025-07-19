"""Models TapHome devices and supported value types."""

import logging
from dataclasses import dataclass

from .value_type import ValueType

_LOGGER = logging.getLogger(__name__)


@dataclass(slots=True)
class SupportedValue:
    """Describe a supported value on a TapHome device."""

    value_type: ValueType
    read_only: bool
    allowed_values: list[dict]
    min_value: int | None
    max_value: int | None


@dataclass(slots=True)
class Device:
    """Representation of a device connected to TapHome."""

    device_id: int
    name: str
    description: str
    zone: str | None
    category: str | None
    device_type: str
    supported_values: dict[ValueType, SupportedValue]

    @staticmethod
    def create(device: dict) -> "Device":
        """Instantiate ``Device`` from raw ``device`` dictionary."""
        device_id = device["deviceId"]
        name = device["name"]
        description = device["description"]
        zone = device.get("zone")
        category = device.get("category")
        device_type = device["type"]
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
            device_id,
            name,
            description,
            zone,
            category,
            device_type,
            supported_values,
        )

    @property
    def id(self) -> int:
        """Return the device identifier."""
        return self.device_id

    @property
    def type(self) -> str:
        """Return the device type string."""
        return self.device_type

    def supports_value(self, value_type: ValueType):
        """Return ``True`` if ``value_type`` is supported by the device."""
        return value_type in self.supported_values
