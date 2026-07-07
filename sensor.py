"""TapHome sensor integration."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, replace
from datetime import date, datetime
from decimal import Decimal
from typing import Any

from taphome_sdk import Device, DeviceState, ValueType

from homeassistant.components.sensor import (
    DOMAIN as SENSOR_DOMAIN,
    SensorDeviceClass,
    SensorEntity,
)
from homeassistant.components.sensor.const import SensorStateClass, UnitOfVolumeFlowRate
from homeassistant.const import (
    CONCENTRATION_PARTS_PER_MILLION,
    LIGHT_LUX,
    PERCENTAGE,
    UnitOfElectricCurrent,
    UnitOfElectricPotential,
    UnitOfEnergy,
    UnitOfFrequency,
    UnitOfLength,
    UnitOfPower,
    UnitOfPressure,
    UnitOfSpeed,
    UnitOfTemperature,
    UnitOfVolume,
    UnitOfVolumetricFlux,
)
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .add_entry_request import add_taphome_entities
from .entity import TapHomeEntity
from .taphome_config_entry import AddEntryRequest, TapHomeEntityConfig
from .taphome_data import TapHomeConfigEntry


@dataclass(slots=True)
class TapHomeSensorType:
    """Metadata describing how to interpret a TapHome sensor value."""

    value_type: ValueType
    device_class: SensorDeviceClass | None = None
    unit_of_measurement: str | None = None
    state_class: SensorStateClass | None = None
    convert_th_to_ha: Callable[
        [float], str | int | float | date | datetime | Decimal | None
    ] = lambda value: value

    def with_overrides(
        self,
        *,
        device_class: SensorDeviceClass | None = None,
        unit_of_measurement: str | None = None,
        state_class: SensorStateClass | None = None,
    ) -> TapHomeSensorType:
        """Return a copy with selected fields overridden."""
        return replace(
            self,
            device_class=device_class or self.device_class,
            unit_of_measurement=unit_of_measurement or self.unit_of_measurement,
            state_class=state_class or self.state_class,
        )


HUMIDITY_SENSOR = TapHomeSensorType(
    ValueType.HUMIDITY,
    SensorDeviceClass.HUMIDITY,
    PERCENTAGE,
    SensorStateClass.MEASUREMENT,
    TapHomeEntity.convert_th_percentage_to_ha,
)

TEMPERATURE_SENSOR = TapHomeSensorType(
    ValueType.REAL_TEMPERATURE,
    SensorDeviceClass.TEMPERATURE,
    UnitOfTemperature.CELSIUS,
    SensorStateClass.MEASUREMENT,
    lambda v: round(v, 1),
)

ELECTRIC_DEMAND_SENSOR = TapHomeSensorType(
    ValueType.ELECTRICITY_DEMAND,
    SensorDeviceClass.POWER,
    UnitOfPower.KILO_WATT,
    SensorStateClass.MEASUREMENT,
    lambda v: round(v, 3),
)

ELECTRIC_CONSUMPTION_SENSOR = TapHomeSensorType(
    ValueType.ELECTRICITY_CONSUMPTION,
    SensorDeviceClass.ENERGY,
    UnitOfEnergy.KILO_WATT_HOUR,
    SensorStateClass.TOTAL_INCREASING,
    lambda v: round(v, 2),
)

CO2_SENSOR = TapHomeSensorType(
    ValueType.CO2,
    SensorDeviceClass.CO2,
    CONCENTRATION_PARTS_PER_MILLION,
    SensorStateClass.MEASUREMENT,
    round,
)

BRIGHTNESS_SENSOR = TapHomeSensorType(
    ValueType.SENSOR_BRIGHTNESS,
    SensorDeviceClass.ILLUMINANCE,
    LIGHT_LUX,
    SensorStateClass.MEASUREMENT,
    lambda v: round(v * 100_000, 2),
)

WIND_SPEED_SENSOR = TapHomeSensorType(
    ValueType.WIND_SPEED,
    unit_of_measurement=UnitOfSpeed.KILOMETERS_PER_HOUR,
    state_class=SensorStateClass.MEASUREMENT,
    convert_th_to_ha=lambda v: round(v, 1),
)

ANALOG_INPUT_SENSOR = TapHomeSensorType(
    ValueType.ANALOG_INPUT_VALUE,
    unit_of_measurement=PERCENTAGE,
    state_class=SensorStateClass.MEASUREMENT,
    convert_th_to_ha=TapHomeEntity.convert_th_percentage_to_ha,
)

PULSE_TOTAL_IMPULSE_SENSOR = TapHomeSensorType(
    ValueType.TOTAL_IMPULSE_COUNT,
    state_class=SensorStateClass.TOTAL_INCREASING,
)

PULSE_CURRENT_HOUR_SENSOR = TapHomeSensorType(
    ValueType.CURRENT_HOUR_IMPULSE_COUNT,
    state_class=SensorStateClass.MEASUREMENT,
)

PULSE_FREQUENCY_SENSOR = TapHomeSensorType(
    ValueType.LAST_MEASURED_FREQUENCY,
    unit_of_measurement=UnitOfFrequency.HERTZ,
    state_class=SensorStateClass.MEASUREMENT,
    convert_th_to_ha=lambda v: round(v, 1),
)

GAS_CONSUMPTION_SENSOR = TapHomeSensorType(
    ValueType.GAS_CONSUMPTION,
    SensorDeviceClass.GAS,
    UnitOfVolume.CUBIC_METERS,
    SensorStateClass.TOTAL_INCREASING,
    lambda v: round(v, 2),
)

GAS_DEMAND_SENSOR = TapHomeSensorType(
    ValueType.GAS_DEMAND,
    SensorDeviceClass.POWER,
    UnitOfPower.KILO_WATT,
    SensorStateClass.MEASUREMENT,
    lambda v: round(v, 3),
)

WATER_CONSUMPTION_SENSOR = TapHomeSensorType(
    ValueType.WATER_CONSUMPTION,
    SensorDeviceClass.WATER,
    UnitOfVolume.CUBIC_METERS,
    SensorStateClass.TOTAL_INCREASING,
    lambda v: round(v, 2),
)

WATER_LEVEL_SENSOR = TapHomeSensorType(
    ValueType.WATER_LEVEL,
    SensorDeviceClass.DISTANCE,
    UnitOfLength.METERS,
    SensorStateClass.MEASUREMENT,
    lambda v: round(v, 2),
)

WATER_DEMAND_SENSOR = TapHomeSensorType(
    ValueType.WATER_DEMAND,
    SensorDeviceClass.VOLUME_FLOW_RATE,
    UnitOfVolumeFlowRate.CUBIC_METERS_PER_HOUR,
    SensorStateClass.MEASUREMENT,
    lambda v: round(v, 3),
)

RAINFALL_RATE_SENSOR = TapHomeSensorType(
    ValueType.RAINFALL_RATE,
    SensorDeviceClass.PRECIPITATION_INTENSITY,
    UnitOfVolumetricFlux.MILLIMETERS_PER_HOUR,
    SensorStateClass.MEASUREMENT,
    lambda v: round(v, 1),
)

RAIN_COUNTER_SENSOR = TapHomeSensorType(
    ValueType.RAIN_COUNTER,
    SensorDeviceClass.PRECIPITATION,
    UnitOfVolumetricFlux.MILLIMETERS_PER_HOUR,
    SensorStateClass.TOTAL_INCREASING,
    lambda v: round(v, 1),
)

WATER_PRESSURE_SENSOR = TapHomeSensorType(
    ValueType.WATER_PRESSURE,
    SensorDeviceClass.PRESSURE,
    UnitOfPressure.BAR,
    SensorStateClass.MEASUREMENT,
    lambda v: round(v, 2),
)

LIGHT_INTENSITY_SENSOR = TapHomeSensorType(
    ValueType.LIGHT_INTENSITY,
    SensorDeviceClass.ILLUMINANCE,
    LIGHT_LUX,
    SensorStateClass.MEASUREMENT,
    lambda v: round(v, 0),
)

BATTERY_PERCENTAGE_SENSOR = TapHomeSensorType(
    ValueType.BATTERY_PERCENTAGE_REMAINING,
    SensorDeviceClass.BATTERY,
    PERCENTAGE,
    SensorStateClass.MEASUREMENT,
    lambda v: round(v, 1),
)

ELECTRIC_VOLTAGE_SENSOR = TapHomeSensorType(
    ValueType.ELECTRIC_VOLTAGE,
    SensorDeviceClass.VOLTAGE,
    UnitOfElectricPotential.VOLT,
    SensorStateClass.MEASUREMENT,
    lambda v: round(v, 1),
)

ELECTRIC_CURRENT_SENSOR = TapHomeSensorType(
    ValueType.ELECTRIC_CURRENT,
    SensorDeviceClass.CURRENT,
    UnitOfElectricCurrent.AMPERE,
    SensorStateClass.MEASUREMENT,
    lambda v: round(v, 1),
)

PERCENTAGES_SENSOR = TapHomeSensorType(
    ValueType.PERCENTAGES,
    unit_of_measurement=PERCENTAGE,
    state_class=SensorStateClass.MEASUREMENT,
    convert_th_to_ha=TapHomeEntity.convert_th_percentage_to_ha,
)

VARIABLE_SENSOR = TapHomeSensorType(
    ValueType.VARIABLE_STATE,
    state_class=SensorStateClass.MEASUREMENT,
    convert_th_to_ha=lambda v: round(v, 1),
)


class TapHomeSensorConfig(TapHomeEntityConfig):
    """Configuration options for TapHome sensor entities."""

    def __init__(self, device_config: dict) -> None:
        """Initialize configuration entry from raw device config."""
        super().__init__(device_config)
        self.device_class: SensorDeviceClass | None = self.get_optional(
            "device_class", None
        )
        self.value_type: ValueType | None = self.get_optional("value_type", None)
        self.unit_of_measurement: str | None = self.get_optional(
            "unit_of_measurement", None
        )
        self.state_class: str | None = self.get_optional("state_class", None)
        if self.get_optional("was_measured", None) is True:
            self.state_class = SensorStateClass.MEASUREMENT


class TapHomeSensor(TapHomeEntity, SensorEntity):
    """Representation of a TapHome sensor."""

    def __init__(
        self,
        config: AddEntryRequest[TapHomeSensorConfig],
        sensor_type: TapHomeSensorType,
    ) -> None:
        """Initialize TapHome sensor entity."""
        self._sensor_type = sensor_type

        self._attr_device_class = sensor_type.device_class
        self._attr_state_class = sensor_type.state_class
        self._attr_native_unit_of_measurement = sensor_type.unit_of_measurement

        self._device = config.hub.get_typed_device(config.entity.id, Device)

        self._subscribe(self._device.state.changed, self._on_device_state_change)
        super().__init__(
            config,
            self._device,
            SENSOR_DOMAIN,
            self._sensor_type.value_type.name.replace("_", ""),
        )

    def _on_device_state_change(
        self, _: DeviceState | None, current_state: DeviceState
    ) -> None:
        """Handle device state change event."""
        value = current_state.get_device_value(self._sensor_type.value_type)
        self._attr_native_value = (
            None if value is None else self._sensor_type.convert_th_to_ha(value)
        )


def create_entities(
    config: AddEntryRequest[TapHomeSensorConfig],
) -> list[TapHomeSensor]:
    """Instantiate sensor entities for each supported value type."""

    sensors: list[TapHomeSensor] = []
    device = config.hub.get_typed_device(config.entity.id, Device)
    if device is not None:
        supported_sensor_types: list[TapHomeSensorType] = [
            HUMIDITY_SENSOR,
            TEMPERATURE_SENSOR,
            ELECTRIC_DEMAND_SENSOR,
            ELECTRIC_CONSUMPTION_SENSOR,
            CO2_SENSOR,
            BRIGHTNESS_SENSOR,
            WIND_SPEED_SENSOR,
            ANALOG_INPUT_SENSOR,
            PULSE_TOTAL_IMPULSE_SENSOR,
            PULSE_CURRENT_HOUR_SENSOR,
            PULSE_FREQUENCY_SENSOR,
            GAS_CONSUMPTION_SENSOR,
            GAS_DEMAND_SENSOR,
            WATER_CONSUMPTION_SENSOR,
            WATER_DEMAND_SENSOR,
            WATER_LEVEL_SENSOR,
            RAINFALL_RATE_SENSOR,
            RAIN_COUNTER_SENSOR,
            WATER_PRESSURE_SENSOR,
            LIGHT_INTENSITY_SENSOR,
            BATTERY_PERCENTAGE_SENSOR,
            ELECTRIC_VOLTAGE_SENSOR,
            ELECTRIC_CURRENT_SENSOR,
            VARIABLE_SENSOR,
            PERCENTAGES_SENSOR,
        ]

        if config.entity.value_type:
            supported_sensor_types.append(
                TapHomeSensorType(
                    ValueType(config.entity.value_type),
                    config.entity.device_class,
                    config.entity.unit_of_measurement,
                    SensorStateClass.MEASUREMENT,
                    lambda v: v,
                )
            )

        for sensor_type in supported_sensor_types:
            if device.supports_value(sensor_type.value_type):
                overrides: dict[str, Any] = {}
                if config.entity.device_class is not None:
                    overrides["device_class"] = config.entity.device_class
                if config.entity.unit_of_measurement is not None:
                    overrides["unit_of_measurement"] = config.entity.unit_of_measurement
                if config.entity.state_class is not None:
                    overrides["state_class"] = config.entity.state_class

                sensor = TapHomeSensor(config, sensor_type.with_overrides(**overrides))
                sensors.append(sensor)
    return sensors


async def async_setup_entry(
    hass: HomeAssistant,
    entry: TapHomeConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up TapHome sensors from a config entry."""
    add_taphome_entities(entry, async_add_entities, SENSOR_DOMAIN, create_entities)
