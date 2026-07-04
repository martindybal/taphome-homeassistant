"""Text constants for the TapHome integration."""

from enum import StrEnum


class Issues(StrEnum):
    """Class containing text constants for issues in the TapHome integration."""

    DEVICE_NOT_EXPOSED = "device_not_exposed"
    CORE_UNAVAILABLE = "core_unavailable"
    DEVICE_TYPE_MISMATCH = "device_type_mismatch"
    YAML_DEPRECATED = "yaml_deprecated"
