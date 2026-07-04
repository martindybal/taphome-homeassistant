"""Table of per-platform device options driving the options flow forms."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

from homeassistant.components.binary_sensor import BinarySensorDeviceClass
from homeassistant.components.button import ButtonDeviceClass
from homeassistant.components.climate import HVACMode
from homeassistant.components.cover import CoverDeviceClass
from homeassistant.components.humidifier import HumidifierDeviceClass
from homeassistant.components.sensor import SensorDeviceClass, SensorStateClass
from homeassistant.components.switch import SwitchDeviceClass
from homeassistant.components.valve import ValveDeviceClass
from homeassistant.const import (
    CONF_BINARY_SENSORS,
    CONF_COVERS,
    CONF_LIGHTS,
    CONF_SENSORS,
    CONF_SWITCHES,
)

from .const import (
    CONF_BUTTONS,
    CONF_CLIMATES,
    CONF_FAN,
    CONF_HUMIDIFIER,
    CONF_MULTIVALUE_SWITCHES,
    CONF_TIMES,
    CONF_VALVE,
)
from .taphome_sdk import (
    AnalogOutputDevice,
    BidirectionalDevice,
    ButtonAction,
    ButtonDevice,
    DigitalOutputDevice,
    DualWhiteLightDevice,
    MultiValueSwitchDevice,
    RGBLightDevice,
    SessionDurationVariableDevice,
    ThermostatDevice,
)


class FieldKind(Enum):
    """Kinds of per-device option fields rendered in the options flow."""

    DEVICE_ID = "device_id"
    ENUM = "enum"
    MULTI_ENUM = "multi_enum"
    VALUE_TYPE = "value_type"
    TEXT = "text"
    NUMBER_INT = "number_int"
    NUMBER_FLOAT = "number_float"


@dataclass(slots=True, frozen=True)
class OptionField:
    """Describe a single per-device option."""

    key: str
    kind: FieldKind
    options: tuple[str, ...] = ()
    device_types: tuple[type, ...] = ()
    min_value: float | None = None
    max_value: float | None = None
    step: float | None = None


@dataclass(slots=True, frozen=True)
class PlatformDescriptor:
    """Describe device selection and options of one TapHome platform."""

    config_key: str
    candidate_types: tuple[type, ...]
    fields: tuple[OptionField, ...]


def _enum_values(enum_type: type[Enum]) -> tuple[str, ...]:
    return tuple(str(value.value) for value in enum_type)


_GENERIC_OUTPUT_TYPES = (
    DigitalOutputDevice,
    AnalogOutputDevice,
    BidirectionalDevice,
)

_BUTTON_ACTIONS = tuple(
    action.name.lower() for action in ButtonAction if action != ButtonAction.NONE
)

# One descriptor per device-list configuration key. The candidate types must
# match the get_typed_device calls of the corresponding platform.
PLATFORM_DESCRIPTORS: tuple[PlatformDescriptor, ...] = (
    PlatformDescriptor(
        CONF_LIGHTS,
        (RGBLightDevice, DualWhiteLightDevice, AnalogOutputDevice, DigitalOutputDevice),
        (
            OptionField(
                "effect_id", FieldKind.DEVICE_ID, device_types=(MultiValueSwitchDevice,)
            ),
        ),
    ),
    PlatformDescriptor(
        CONF_BUTTONS,
        (ButtonDevice,),
        (
            OptionField(
                "device_class", FieldKind.ENUM, options=_enum_values(ButtonDeviceClass)
            ),
            OptionField("actions", FieldKind.MULTI_ENUM, options=_BUTTON_ACTIONS),
        ),
    ),
    PlatformDescriptor(
        CONF_COVERS,
        (BidirectionalDevice,),
        (
            OptionField(
                "device_class", FieldKind.ENUM, options=_enum_values(CoverDeviceClass)
            ),
            OptionField(
                "close_threshold", FieldKind.NUMBER_INT, min_value=0, max_value=100
            ),
        ),
    ),
    PlatformDescriptor(
        CONF_CLIMATES,
        (ThermostatDevice,),
        (
            OptionField(
                "range_high_thermostat_id",
                FieldKind.DEVICE_ID,
                device_types=(ThermostatDevice,),
            ),
            OptionField(
                "range_low_thermostat_id",
                FieldKind.DEVICE_ID,
                device_types=(ThermostatDevice,),
            ),
            OptionField(
                "target_temperature_step",
                FieldKind.NUMBER_FLOAT,
                min_value=0.1,
                max_value=10,
                step=0.1,
            ),
            OptionField(
                "precision",
                FieldKind.NUMBER_FLOAT,
                min_value=0.1,
                max_value=1,
                step=0.1,
            ),
            OptionField(
                "hvac_switch_id",
                FieldKind.DEVICE_ID,
                device_types=(DigitalOutputDevice,),
            ),
            OptionField("hvac_mode", FieldKind.ENUM, options=_enum_values(HVACMode)),
            OptionField(
                "hvac_mode_id",
                FieldKind.DEVICE_ID,
                device_types=(MultiValueSwitchDevice,),
            ),
            OptionField(
                "hvac_action_id",
                FieldKind.DEVICE_ID,
                device_types=(MultiValueSwitchDevice,),
            ),
            OptionField(
                "preset_mode_id",
                FieldKind.DEVICE_ID,
                device_types=(MultiValueSwitchDevice,),
            ),
            OptionField(
                "fan_mode_id",
                FieldKind.DEVICE_ID,
                device_types=(MultiValueSwitchDevice,),
            ),
            OptionField(
                "swing_mode_id",
                FieldKind.DEVICE_ID,
                device_types=(MultiValueSwitchDevice,),
            ),
            OptionField(
                "swing_horizontal_mode_id",
                FieldKind.DEVICE_ID,
                device_types=(MultiValueSwitchDevice,),
            ),
            OptionField(
                "target_humidity_id",
                FieldKind.DEVICE_ID,
                device_types=(AnalogOutputDevice,),
            ),
            OptionField(
                "min_humidity", FieldKind.NUMBER_INT, min_value=0, max_value=100
            ),
            OptionField(
                "max_humidity", FieldKind.NUMBER_INT, min_value=0, max_value=100
            ),
        ),
    ),
    PlatformDescriptor(
        CONF_FAN,
        _GENERIC_OUTPUT_TYPES,
        (
            OptionField(
                "preset_mode_id",
                FieldKind.DEVICE_ID,
                device_types=(MultiValueSwitchDevice,),
            ),
        ),
    ),
    PlatformDescriptor(
        CONF_HUMIDIFIER,
        _GENERIC_OUTPUT_TYPES,
        (
            OptionField(
                "switch_id", FieldKind.DEVICE_ID, device_types=(DigitalOutputDevice,)
            ),
            OptionField(
                "action_id",
                FieldKind.DEVICE_ID,
                device_types=(MultiValueSwitchDevice,),
            ),
            OptionField(
                "mode_id", FieldKind.DEVICE_ID, device_types=(MultiValueSwitchDevice,)
            ),
            OptionField("humidity_sensor_id", FieldKind.DEVICE_ID),
            OptionField(
                "min_humidity", FieldKind.NUMBER_INT, min_value=0, max_value=100
            ),
            OptionField(
                "max_humidity", FieldKind.NUMBER_INT, min_value=0, max_value=100
            ),
            OptionField(
                "device_class",
                FieldKind.ENUM,
                options=_enum_values(HumidifierDeviceClass),
            ),
        ),
    ),
    PlatformDescriptor(CONF_MULTIVALUE_SWITCHES, (MultiValueSwitchDevice,), ()),
    PlatformDescriptor(
        CONF_SWITCHES,
        (DigitalOutputDevice,),
        (
            OptionField(
                "device_class", FieldKind.ENUM, options=_enum_values(SwitchDeviceClass)
            ),
        ),
    ),
    PlatformDescriptor(
        CONF_SENSORS,
        (),
        (
            OptionField(
                "device_class", FieldKind.ENUM, options=_enum_values(SensorDeviceClass)
            ),
            OptionField("value_type", FieldKind.VALUE_TYPE),
            OptionField("unit_of_measurement", FieldKind.TEXT),
            OptionField(
                "state_class", FieldKind.ENUM, options=_enum_values(SensorStateClass)
            ),
        ),
    ),
    PlatformDescriptor(
        CONF_BINARY_SENSORS,
        (),
        (
            OptionField(
                "device_class",
                FieldKind.ENUM,
                options=_enum_values(BinarySensorDeviceClass),
            ),
            OptionField("value_type", FieldKind.VALUE_TYPE),
        ),
    ),
    PlatformDescriptor(
        CONF_VALVE,
        _GENERIC_OUTPUT_TYPES,
        (
            OptionField(
                "device_class", FieldKind.ENUM, options=_enum_values(ValveDeviceClass)
            ),
        ),
    ),
    PlatformDescriptor(CONF_TIMES, (SessionDurationVariableDevice,), ()),
)

PLATFORM_DESCRIPTORS_BY_KEY: dict[str, PlatformDescriptor] = {
    descriptor.config_key: descriptor for descriptor in PLATFORM_DESCRIPTORS
}
