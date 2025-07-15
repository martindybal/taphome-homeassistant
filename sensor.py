"""TapHome sensor integration."""

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


class TapHomeSensorType:
    """Base metadata for a TapHome sensor value."""

    def __init__(
        self,
        value_type: ValueType,
        device_class: SensorDeviceClass = None,
        unit_of_measurement: str | None = None,
        state_class: SensorStateClass = None,
        last_reset: datetime | None = None,
    ) -> None:
        """Initialize generic sensor description."""
        self.device_class = device_class
        self.value_type = value_type
        self.unit_of_measurement = unit_of_measurement
        self.state_class = state_class
        self.last_reset = last_reset

    def convert_taphome_to_ha(self, value: int) -> int:
        """Convert value from TapHome scale to HA scale."""
        return value


class TapHomeHumiditySensorType(TapHomeSensorType):
    """Sensor type returning relative humidity."""

    def __init__(self) -> None:
        """Initialize humidity sensor metadata."""
        super().__init__(
            ValueType.Humidity,
            SensorDeviceClass.HUMIDITY,
            PERCENTAGE,
            SensorStateClass.MEASUREMENT,
        )

    def convert_taphome_to_ha(self, value: int) -> int:
        """Convert percentage from TapHome to Home Assistant."""
        return TapHomeEntity.convert_taphome_percentage_to_ha(value)


class TapHomeTemperatureSensorType(TapHomeSensorType):
    """Sensor type returning temperature values."""

    def __init__(self) -> None:
        """Initialize temperature sensor metadata."""
        super().__init__(
            ValueType.RealTemperature,
            SensorDeviceClass.TEMPERATURE,
            UnitOfTemperature.CELSIUS,
            SensorStateClass.MEASUREMENT,
        )

    def convert_taphome_to_ha(self, value: int) -> int:
        """Convert temperature value to one decimal place."""
        return round(value, 1)


class TapHomeElectricCounterElectricityDemandSensorType(TapHomeSensorType):
    """Sensor type for instantaneous power demand."""

    def __init__(self) -> None:
        """Initialize demand sensor metadata."""
        super().__init__(
            ValueType.ElectricityDemand,
            SensorDeviceClass.POWER,
            UnitOfPower.KILO_WATT,
            SensorStateClass.MEASUREMENT,
        )

    def convert_taphome_to_ha(self, value: int) -> int:
        """Convert power demand to kilowatts with three decimals."""
        return round(value, 3)


class TapHomeElectricCounterElectricityConsumptionSensorType(TapHomeSensorType):
    """Sensor type for total energy consumption."""

    def __init__(self) -> None:
        """Initialize consumption sensor metadata."""
        super().__init__(
            ValueType.ElectricityConsumption,
            SensorDeviceClass.ENERGY,
            UnitOfEnergy.KILO_WATT_HOUR,
            SensorStateClass.TOTAL_INCREASING,
        )

    def convert_taphome_to_ha(self, value: int) -> int:
        """Convert energy consumption to kilowatt-hours."""
        return round(value, 2)


class TapHomeCo2SensorType(TapHomeSensorType):
    """Sensor type for CO2 concentration."""

    def __init__(self) -> None:
        """Initialize CO2 sensor metadata."""
        super().__init__(
            ValueType.Co2,
            SensorDeviceClass.CO2,
            CONCENTRATION_PARTS_PER_MILLION,
            SensorStateClass.MEASUREMENT,
        )

    def convert_taphome_to_ha(self, value: int) -> int:
        """Convert CO2 value to integer ppm."""
        return round(value)


class TapHomeBrightnessSensorType(TapHomeSensorType):
    """Sensor type for brightness measurement."""

    def __init__(self) -> None:
        """Initialize brightness sensor metadata."""
        super().__init__(
            ValueType.SensorBrightness,
            SensorDeviceClass.ILLUMINANCE,
            LIGHT_LUX,
            SensorStateClass.MEASUREMENT,
        )

    def convert_taphome_to_ha(self, value: int) -> int:
        """Convert brightness value to lux."""
        value = value * 100_000
        return round(value, 2)


class TapHomeWindSpeedSensorType(TapHomeSensorType):
    """Sensor type for wind speed."""

    def __init__(self) -> None:
        """Initialize wind speed sensor metadata."""
        super().__init__(
            ValueType.WindSpeed,
            None,
            UnitOfSpeed.KILOMETERS_PER_HOUR,
            SensorStateClass.MEASUREMENT,
        )

    def convert_taphome_to_ha(self, value: int) -> int:
        """Convert wind speed to km/h with one decimal."""
        return round(value, 1)


class TapHomeAnalogInputSensorType(TapHomeSensorType):
    """Sensor type for analog input percentages."""

    def __init__(self) -> None:
        """Initialize analog input sensor metadata."""
        super().__init__(
            ValueType.AnalogInputValue,
            None,
            PERCENTAGE,
            SensorStateClass.MEASUREMENT,
        )

    def convert_taphome_to_ha(self, value: int) -> int:
        """Convert analog input percentage value."""
        return TapHomeEntity.convert_taphome_percentage_to_ha(value)


class TapHomePulseCounterTotalImpulseCountSensorType(TapHomeSensorType):
    """Sensor type for total impulse count."""

    def __init__(self) -> None:
        """Initialize impulse counter sensor metadata."""
        super().__init__(
            ValueType.TotalImpulseCount,
            state_class=SensorStateClass.TOTAL_INCREASING,
        )


class TapHomePulseCounterCurrentHourImpulseCountSensorType(TapHomeSensorType):
    """Sensor type for current hour impulse count."""

    def __init__(self) -> None:
        """Initialize impulse counter sensor metadata."""
        super().__init__(
            ValueType.CurrentHourImpulseCount,
            state_class=SensorStateClass.MEASUREMENT,
        )


class TapHomePulseCounterLastMeasuredFrequencySensorType(TapHomeSensorType):
    """Sensor type for impulse frequency."""

    def __init__(self) -> None:
        """Initialize frequency sensor metadata."""
        super().__init__(
            ValueType.LastMeasuredFrequency,
            None,
            UnitOfFrequency.HERTZ,
            SensorStateClass.MEASUREMENT,
        )

    def convert_taphome_to_ha(self, value: int) -> int:
        """Convert frequency measurement to hertz."""
        return round(value, 1)


class TapHomeGasConsumptionSensorType(TapHomeSensorType):
    """Sensor type for gas consumption."""

    def __init__(self) -> None:
        """Initialize gas consumption sensor metadata."""
        super().__init__(
            ValueType.GasConsumption,
            SensorDeviceClass.GAS,
            UnitOfVolume.CUBIC_METERS,
            SensorStateClass.TOTAL_INCREASING,
        )

    def convert_taphome_to_ha(self, value: int) -> int:
        """Convert gas consumption to cubic meters."""
        return round(value, 2)


class TapHomeRainfallRateSensorType(TapHomeSensorType):
    """Sensor type for rainfall rate."""

    def __init__(self) -> None:
        """Initialize rainfall rate sensor metadata."""
        super().__init__(
            ValueType.RainfallRate,
            SensorDeviceClass.PRECIPITATION_INTENSITY,
            UnitOfVolumetricFlux.MILLIMETERS_PER_HOUR,
            SensorStateClass.MEASUREMENT,
        )

    def convert_taphome_to_ha(self, value: int) -> int:
        """Convert rainfall rate to millimeters per hour."""
        return round(value, 1)


class TapHomeWaterPressureSensorType(TapHomeSensorType):
    """Sensor type for water pressure."""

    def __init__(self) -> None:
        """Initialize water pressure sensor metadata."""
        super().__init__(
            ValueType.WaterPressure,
            SensorDeviceClass.PRESSURE,
            UnitOfPressure.BAR,
            SensorStateClass.MEASUREMENT,
        )

    def convert_taphome_to_ha(self, value: int) -> int:
        """Convert water pressure to bar."""
        return round(value, 2)


class TapHomeLightIntensitySensorType(TapHomeSensorType):
    """Sensor type for light intensity."""

    def __init__(self) -> None:
        """Initialize light intensity sensor metadata."""
        super().__init__(
            ValueType.LightIntensity,
            SensorDeviceClass.ILLUMINANCE,
            LIGHT_LUX,
            SensorStateClass.MEASUREMENT,
        )

    def convert_taphome_to_ha(self, value: int) -> int:
        """Convert light intensity to integer lux."""
        return round(value, 0)


class TapHomeBatteryPercentageSensorType(TapHomeSensorType):
    """Sensor type for battery percentage."""

    def __init__(self) -> None:
        """Initialize battery sensor metadata."""
        super().__init__(
            ValueType.BatteryPercentageRemaining,
            SensorDeviceClass.BATTERY,
            PERCENTAGE,
            SensorStateClass.MEASUREMENT,
        )

    def convert_taphome_to_ha(self, value: int) -> int:
        """Convert battery level to percent with one decimal."""
        return round(value, 1)


class TapHomeElectricVoltageSensorType(TapHomeSensorType):
    """Sensor type for electric voltage."""

    def __init__(self) -> None:
        """Initialize voltage sensor metadata."""
        super().__init__(
            ValueType.ElectricVoltage,
            SensorDeviceClass.VOLTAGE,
            UnitOfElectricPotential.VOLT,
            SensorStateClass.MEASUREMENT,
        )

    def convert_taphome_to_ha(self, value: int) -> int:
        """Convert voltage value to volts with one decimal."""
        return round(value, 1)


class TapHomeElectricCurrentSensorType(TapHomeSensorType):
    """Sensor type for electric current."""

    def __init__(self) -> None:
        """Initialize electric current sensor metadata."""
        super().__init__(
            ValueType.ElectricCurrent,
            SensorDeviceClass.CURRENT,
            UnitOfElectricCurrent.AMPERE,
            SensorStateClass.MEASUREMENT,
        )

    def convert_taphome_to_ha(self, value: int) -> int:
        """Convert electric current to amperes with one decimal."""
        return round(value, 1)


class TapHomePercentagesSensorType(TapHomeSensorType):
    """Sensor type for generic percentages."""

    def __init__(self) -> None:
        """Initialize percentages sensor metadata."""
        super().__init__(
            ValueType.Percentages,
            None,
            PERCENTAGE,
            SensorStateClass.MEASUREMENT,
        )

    def convert_taphome_to_ha(self, value: int) -> int:
        """Convert percentage value from TapHome to Home Assistant."""
        return TapHomeEntity.convert_taphome_percentage_to_ha(value)


class TapHomeVariableType(TapHomeSensorType):
    """Sensor type for custom variable state."""

    def __init__(self) -> None:
        """Initialize variable state sensor metadata."""
        super().__init__(
            ValueType.VariableState,
            state_class=SensorStateClass.MEASUREMENT,
        )

    def convert_taphome_to_ha(self, value: int) -> int:
        """Convert variable state to rounded value."""
        return round(value, 1)


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
    """Representation of an sensor."""

    def __init__(
        self,
        hass: HomeAssistant,
        core_config: TapHomeCoreConfigEntry,
        config_entry: SensorConfigEntry,
        coordinator: TapHomeDataUpdateCoordinator,
        sensor_type: TapHomeSensorType,
    ):
        """Initialize TapHome sensor entity."""
        assert sensor_type is not None
        self._sensor_type = sensor_type
        unique_id_determination = f"{SENSOR_DOMAIN}.{self._sensor_type.value_type.name}"

        super().__init__(
            hass,
            core_config,
            config_entry,
            unique_id_determination,
            coordinator,
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

    def __init__(
        self,
        hass: HomeAssistant,
        core_config: TapHomeCoreConfigEntry,
        config_entry: SensorConfigEntry,
        coordinator: TapHomeDataUpdateCoordinator,
        add_entities: AddEntitiesCallback,
    ):
        """Initialize request for the provided configuration entry."""
        super().__init__(config_entry.id, coordinator, TapHomeState)
        self._hass = hass
        self._core_config = core_config
        self._config_entry = config_entry
        self.coordinator = coordinator
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
                TapHomeHumiditySensorType(),
                TapHomeTemperatureSensorType(),
                TapHomeElectricCounterElectricityDemandSensorType(),
                TapHomeElectricCounterElectricityConsumptionSensorType(),
                TapHomeCo2SensorType(),
                TapHomeBrightnessSensorType(),
                TapHomeWindSpeedSensorType(),
                TapHomeAnalogInputSensorType(),
                TapHomePulseCounterTotalImpulseCountSensorType(),
                TapHomePulseCounterCurrentHourImpulseCountSensorType(),
                TapHomePulseCounterLastMeasuredFrequencySensorType(),
                TapHomeGasConsumptionSensorType(),
                TapHomeRainfallRateSensorType(),
                TapHomeWaterPressureSensorType(),
                TapHomeLightIntensitySensorType(),
                TapHomeBatteryPercentageSensorType(),
                TapHomeElectricVoltageSensorType(),
                TapHomeElectricCurrentSensorType(),
                TapHomeVariableType(),
                TapHomePercentagesSensorType(),
            ]

            if self._config_entry.value_type:
                supported_sensor_types.append(
                    TapHomeSensorType(
                        ValueType(self._config_entry.value_type),
                        self._config_entry.device_class,
                        SensorStateClass.MEASUREMENT,
                    )
                )

            sensors = []
            for sensor_type in supported_sensor_types:
                if self.taphome_device.supports_value(sensor_type.value_type):
                    if self._config_entry.device_class is not None:
                        sensor_type.device_class = self._config_entry.device_class
                    if self._config_entry.unit_of_measurement is not None:
                        sensor_type.unit_of_measurement = (
                            self._config_entry.unit_of_measurement
                        )
                    if self._config_entry.state_class is not None:
                        sensor_type.state_class = self._config_entry.state_class

                    sensor = TapHomeSensor(
                        self._hass,
                        self._core_config,
                        self._config_entry,
                        self.coordinator,
                        sensor_type,
                    )
                    sensors.append(sensor)
            self.add_entities(sensors)


def setup_platform(
    hass: HomeAssistant,
    config,
    add_entities: AddEntitiesCallback,
    discovery_info=None,
) -> None:
    """Set up the sensor platform."""
    add_entry_requests: list[AddEntryRequest] = hass.data[TAPHOME_PLATFORM][
        CONF_SENSORS
    ]
    for add_entry_request in add_entry_requests:
        TapHomeSensorCreateRequest(
            hass,
            add_entry_request.core_config,
            add_entry_request.config_entry,
            add_entry_request.coordinator,
            add_entities,
        )
