"""TapHome sensor integration."""

from collections.abc import Callable
from dataclasses import dataclass, replace
from datetime import datetime
import logging

from homeassistant.components.sensor import (
    DOMAIN as SENSOR_DOMAIN,
    SensorDeviceClass,
    SensorEntity,
)
from homeassistant.components.sensor.const import SensorStateClass
from homeassistant.const import (
    CONCENTRATION_PARTS_PER_MILLION,
    CONF_SENSORS,
    LIGHT_LUX,
    PERCENTAGE,
    UnitOfElectricCurrent,
    UnitOfElectricPotential,
    UnitOfEnergy,
    UnitOfFrequency,
    UnitOfPower,
    UnitOfPressure,
    UnitOfSpeed,
    UnitOfTemperature,
    UnitOfVolume,
    UnitOfVolumetricFlux,
)
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .add_entry_request import AddEntryRequest
from .const import TAPHOME_PLATFORM
from .coordinator import TapHomeDataUpdateCoordinator
from .taphome_entity import (
    TapHomeConfigEntry,
    TapHomeCoreConfigEntry,
    TapHomeDataUpdateCoordinatorObject,
    TapHomeEntity,
)
from .taphome_sdk import TapHomeState, ValueType

_LOGGER = logging.getLogger(__name__)


@dataclass(slots=True)
class TapHomeSensorType:
    """Metadata describing how to interpret a TapHome sensor value."""

    value_type: ValueType
    device_class: SensorDeviceClass | None = None
    unit_of_measurement: str | None = None
    state_class: SensorStateClass | None = None
    last_reset: datetime | None = None
    convert_fn: Callable[[int], int] = lambda value: value

    def convert_taphome_to_ha(self, value: int) -> int:
        """Convert value from TapHome scale to Home Assistant scale."""
        return self.convert_fn(value)

    def with_overrides(
        self,
        *,
        device_class: SensorDeviceClass | None = None,
        unit_of_measurement: str | None = None,
        state_class: SensorStateClass | None = None,
    ) -> "TapHomeSensorType":
        """Return a copy with selected fields overridden."""
        return replace(
            self,
            device_class=device_class or self.device_class,
            unit_of_measurement=unit_of_measurement or self.unit_of_measurement,
            state_class=state_class or self.state_class,
        )


def _convert_percentage(value: int) -> int:
    """Convert TapHome percentage scale to Home Assistant."""
    return TapHomeEntity.convert_taphome_percentage_to_ha(value)


HUMIDITY_SENSOR = TapHomeSensorType(
    ValueType.HUMIDITY,
    SensorDeviceClass.HUMIDITY,
    PERCENTAGE,
    SensorStateClass.MEASUREMENT,
    convert_fn=_convert_percentage,
)

TEMPERATURE_SENSOR = TapHomeSensorType(
    ValueType.REAL_TEMPERATURE,
    SensorDeviceClass.TEMPERATURE,
    UnitOfTemperature.CELSIUS,
    SensorStateClass.MEASUREMENT,
    convert_fn=lambda v: round(v, 1),
)

ELECTRIC_DEMAND_SENSOR = TapHomeSensorType(
    ValueType.ELECTRICITY_DEMAND,
    SensorDeviceClass.POWER,
    UnitOfPower.KILO_WATT,
    SensorStateClass.MEASUREMENT,
    convert_fn=lambda v: round(v, 3),
)

ELECTRIC_CONSUMPTION_SENSOR = TapHomeSensorType(
    ValueType.ELECTRICITY_CONSUMPTION,
    SensorDeviceClass.ENERGY,
    UnitOfEnergy.KILO_WATT_HOUR,
    SensorStateClass.TOTAL_INCREASING,
    convert_fn=lambda v: round(v, 2),
)

CO2_SENSOR = TapHomeSensorType(
    ValueType.CO2,
    SensorDeviceClass.CO2,
    CONCENTRATION_PARTS_PER_MILLION,
    SensorStateClass.MEASUREMENT,
    convert_fn=round,
)

BRIGHTNESS_SENSOR = TapHomeSensorType(
    ValueType.SENSOR_BRIGHTNESS,
    SensorDeviceClass.ILLUMINANCE,
    LIGHT_LUX,
    SensorStateClass.MEASUREMENT,
    convert_fn=lambda v: round(v * 100_000, 2),
)

WIND_SPEED_SENSOR = TapHomeSensorType(
    ValueType.WIND_SPEED,
    unit_of_measurement=UnitOfSpeed.KILOMETERS_PER_HOUR,
    state_class=SensorStateClass.MEASUREMENT,
    convert_fn=lambda v: round(v, 1),
)

ANALOG_INPUT_SENSOR = TapHomeSensorType(
    ValueType.ANALOG_INPUT_VALUE,
    unit_of_measurement=PERCENTAGE,
    state_class=SensorStateClass.MEASUREMENT,
    convert_fn=_convert_percentage,
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
    convert_fn=lambda v: round(v, 1),
)

GAS_CONSUMPTION_SENSOR = TapHomeSensorType(
    ValueType.GAS_CONSUMPTION,
    SensorDeviceClass.GAS,
    UnitOfVolume.CUBIC_METERS,
    SensorStateClass.TOTAL_INCREASING,
    convert_fn=lambda v: round(v, 2),
)

RAINFALL_RATE_SENSOR = TapHomeSensorType(
    ValueType.RAINFALL_RATE,
    SensorDeviceClass.PRECIPITATION_INTENSITY,
    UnitOfVolumetricFlux.MILLIMETERS_PER_HOUR,
    SensorStateClass.MEASUREMENT,
    convert_fn=lambda v: round(v, 1),
)

WATER_PRESSURE_SENSOR = TapHomeSensorType(
    ValueType.WATER_PRESSURE,
    SensorDeviceClass.PRESSURE,
    UnitOfPressure.BAR,
    SensorStateClass.MEASUREMENT,
    convert_fn=lambda v: round(v, 2),
)

LIGHT_INTENSITY_SENSOR = TapHomeSensorType(
    ValueType.LIGHT_INTENSITY,
    SensorDeviceClass.ILLUMINANCE,
    LIGHT_LUX,
    SensorStateClass.MEASUREMENT,
    convert_fn=lambda v: round(v, 0),
)

BATTERY_PERCENTAGE_SENSOR = TapHomeSensorType(
    ValueType.BATTERY_PERCENTAGE_REMAINING,
    SensorDeviceClass.BATTERY,
    PERCENTAGE,
    SensorStateClass.MEASUREMENT,
    convert_fn=lambda v: round(v, 1),
)

ELECTRIC_VOLTAGE_SENSOR = TapHomeSensorType(
    ValueType.ELECTRIC_VOLTAGE,
    SensorDeviceClass.VOLTAGE,
    UnitOfElectricPotential.VOLT,
    SensorStateClass.MEASUREMENT,
    convert_fn=lambda v: round(v, 1),
)

ELECTRIC_CURRENT_SENSOR = TapHomeSensorType(
    ValueType.ELECTRIC_CURRENT,
    SensorDeviceClass.CURRENT,
    UnitOfElectricCurrent.AMPERE,
    SensorStateClass.MEASUREMENT,
    convert_fn=lambda v: round(v, 1),
)

PERCENTAGES_SENSOR = TapHomeSensorType(
    ValueType.PERCENTAGES,
    unit_of_measurement=PERCENTAGE,
    state_class=SensorStateClass.MEASUREMENT,
    convert_fn=_convert_percentage,
)

VARIABLE_SENSOR = TapHomeSensorType(
    ValueType.VARIABLE_STATE,
    state_class=SensorStateClass.MEASUREMENT,
    convert_fn=lambda v: round(v, 1),
)


@dataclass(slots=True)
class SensorInitContext:
    """Grouping of dependencies required to create a sensor."""

    hass: HomeAssistant
    core_config: TapHomeCoreConfigEntry
    config_entry: "SensorConfigEntry"
    coordinator: TapHomeDataUpdateCoordinator


class SensorConfigEntry(TapHomeConfigEntry):
    """Configuration options for TapHome sensor entities."""

    def __init__(self, device_config: dict):
        """Initialize configuration entry from raw device config."""
        super().__init__(device_config)
        self._device_class = self.get_optional("device_class", None)
        self._value_type = self.get_optional("value_type", None)
        self._unit_of_measurement = self.get_optional("unit_of_measurement", None)
        self._state_class = self.get_optional("state_class", None)
        if self.get_optional("was_measured", None) is True:
            self._state_class = SensorStateClass.MEASUREMENT

    @property
    def device_class(self) -> str:
        """Return configured Home Assistant device class."""
        return self._device_class

    @property
    def value_type(self) -> ValueType:
        """Return TapHome value type of the sensor."""
        return self._value_type

    @property
    def unit_of_measurement(self) -> str:
        """Return unit of measurement if defined."""
        return self._unit_of_measurement

    @property
    def state_class(self) -> str:
        """Return state class used for the sensor."""
        return self._state_class


class TapHomeSensor(TapHomeEntity[TapHomeState], SensorEntity):
    """Representation of a TapHome sensor."""

    def __init__(self, context: SensorInitContext, sensor_type: TapHomeSensorType):
        """Initialize TapHome sensor entity."""
        assert sensor_type is not None
        self._sensor_type = sensor_type
        unique_id_determination = f"{SENSOR_DOMAIN}.{self._sensor_type.value_type.name}"

        super().__init__(
            context.hass,
            context.core_config,
            context.config_entry,
            unique_id_determination,
            context.coordinator,
            TapHomeState,
        )

    @property
    def native_value(self):
        """Return the value of the sensor."""
        sensor_type = self._sensor_type
        if self.taphome_state is not None:
            sensor_value = self.taphome_state.get_device_value(sensor_type.value_type)
            if sensor_value is None or sensor_value == "NaN":
                return None
            try:
                return sensor_type.convert_taphome_to_ha(sensor_value)
            except (ValueError, TypeError, ArithmeticError):
                return None
        return None

    @property
    def device_class(self) -> str:
        """Return the class of this device, from component DEVICE_CLASSES."""
        return self._sensor_type.device_class

    @property
    def state_class(self) -> str:
        """Return the state class of this entity, from STATE_CLASSES, if any."""
        return self._sensor_type.state_class

    @property
    def native_unit_of_measurement(self) -> str:
        """Return the unit of measurement of this entity, if any."""
        return self._sensor_type.unit_of_measurement

    @property
    def last_reset(self) -> datetime:
        """Return the time when the sensor was last reset, if any."""
        return self._sensor_type.last_reset


class TapHomeSensorCreateRequest(TapHomeDataUpdateCoordinatorObject[TapHomeState]):
    """Create TapHomeSensors from SensorConfigEntry when devices is discovered."""

    def __init__(self, context: SensorInitContext, add_entities: AddEntitiesCallback):
        """Initialize request for the provided configuration entry."""
        super().__init__(context.config_entry.id, context.coordinator, TapHomeState)
        self._context = context
        self.add_entities = add_entities

        self._was_entities_created = False
        self.create_entities()

    @callback
    def handle_taphome_device_change(self) -> None:
        """Recreate sensor entities when TapHome device changes."""
        self.create_entities()

    def create_entities(self) -> None:
        """Instantiate sensor entities for each supported value type."""
        if self.taphome_device is not None:
            self._was_entities_created = True

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
                RAINFALL_RATE_SENSOR,
                WATER_PRESSURE_SENSOR,
                LIGHT_INTENSITY_SENSOR,
                BATTERY_PERCENTAGE_SENSOR,
                ELECTRIC_VOLTAGE_SENSOR,
                ELECTRIC_CURRENT_SENSOR,
                VARIABLE_SENSOR,
                PERCENTAGES_SENSOR,
            ]

            if self._context.config_entry.value_type:
                supported_sensor_types.append(
                    TapHomeSensorType(
                        ValueType(self._context.config_entry.value_type),
                        self._context.config_entry.device_class,
                        self._context.config_entry.unit_of_measurement,
                        SensorStateClass.MEASUREMENT,
                        convert_fn=lambda v: v,
                    )
                )

            sensors = []
            for sensor_type in supported_sensor_types:
                if self.taphome_device.supports_value(sensor_type.value_type):
                    overrides = {}
                    if self._context.config_entry.device_class is not None:
                        overrides["device_class"] = (
                            self._context.config_entry.device_class
                        )
                    if self._context.config_entry.unit_of_measurement is not None:
                        overrides["unit_of_measurement"] = (
                            self._context.config_entry.unit_of_measurement
                        )
                    if self._context.config_entry.state_class is not None:
                        overrides["state_class"] = (
                            self._context.config_entry.state_class
                        )

                    sensor = TapHomeSensor(
                        self._context,
                        sensor_type.with_overrides(**overrides),
                    )
                    sensors.append(sensor)
            self.add_entities(sensors)


def setup_platform(
    hass: HomeAssistant,
    _config,
    add_entities: AddEntitiesCallback,
    _discovery_info=None,
) -> None:
    """Set up the sensor platform."""
    add_entry_requests: list[AddEntryRequest] = hass.data[TAPHOME_PLATFORM][
        CONF_SENSORS
    ]
    for add_entry_request in add_entry_requests:
        context = SensorInitContext(
            hass=hass,
            core_config=add_entry_request.core_config,
            config_entry=add_entry_request.config_entry,
            coordinator=add_entry_request.coordinator,
        )
        TapHomeSensorCreateRequest(context, add_entities)
