"""TapHome sensor integration."""
import datetime
import typing

from homeassistant.components.sensor import (
    DOMAIN,
    STATE_CLASS_MEASUREMENT,
    STATE_CLASS_TOTAL,
    STATE_CLASS_TOTAL_INCREASING,
    SensorEntity,
)
from homeassistant.const import (
    CONCENTRATION_PARTS_PER_MILLION,
    CONF_SENSORS,
    DEVICE_CLASS_CO2,
    DEVICE_CLASS_ENERGY,
    DEVICE_CLASS_HUMIDITY,
    DEVICE_CLASS_ILLUMINANCE,
    DEVICE_CLASS_POWER,
    DEVICE_CLASS_TEMPERATURE,
    ENERGY_KILO_WATT_HOUR,
    FREQUENCY_HERTZ,
    LIGHT_LUX,
    PERCENTAGE,
    POWER_KILO_WATT,
    SPEED_KILOMETERS_PER_HOUR,
    TEMP_CELSIUS,
)
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .add_entry_request import AddEntryRequest
from .const import TAPHOME_PLATFORM
from .coordinator import TapHomeDataUpdateCoordinator
from .taphome_entity import *
from .taphome_sdk import *

_LOGGER = logging.getLogger(__name__)


class TapHomeSensorType:
    def __init__(
        self,
        value_type: ValueType,
        device_class: str = None,
        unit_of_measurement: str = None,
        state_class: str = None,
        last_reset: datetime = None,
    ) -> None:
        self.device_class = device_class
        self.value_type = value_type
        self.unit_of_measurement = unit_of_measurement
        self.state_class = state_class
        self.last_reset = last_reset

    def convert_taphome_to_ha(self, value: int) -> int:
        return value


class TapHomeHumiditySensorType(TapHomeSensorType):
    def __init__(self) -> None:
        super().__init__(
            ValueType.Humidity,
            DEVICE_CLASS_HUMIDITY,
            PERCENTAGE,
            STATE_CLASS_MEASUREMENT,
        )

    def convert_taphome_to_ha(self, value: int) -> int:
        return TapHomeEntity.convert_taphome_percentage_to_ha(value)


class TapHomeTemperatureSensorType(TapHomeSensorType):
    def __init__(self) -> None:
        super().__init__(
            ValueType.RealTemperature,
            DEVICE_CLASS_TEMPERATURE,
            TEMP_CELSIUS,
            STATE_CLASS_MEASUREMENT,
        )

    def convert_taphome_to_ha(self, value: int) -> int:
        return round(value, 1)


class TapHomeElectricCounterElectricityDemandSensorType(TapHomeSensorType):
    def __init__(self) -> None:
        super().__init__(
            ValueType.ElectricityDemand,
            DEVICE_CLASS_POWER,
            POWER_KILO_WATT,
            STATE_CLASS_MEASUREMENT,
        )

    def convert_taphome_to_ha(self, value: int) -> int:
        return round(value, 3)


class TapHomeElectricCounterElectricityConsumptionSensorType(TapHomeSensorType):
    def __init__(self) -> None:
        super().__init__(
            ValueType.ElectricityConsumption,
            DEVICE_CLASS_ENERGY,
            ENERGY_KILO_WATT_HOUR,
            STATE_CLASS_TOTAL_INCREASING,
        )

    def convert_taphome_to_ha(self, value: int) -> int:
        return round(value, 2)


class TapHomeCo2SensorType(TapHomeSensorType):
    def __init__(self) -> None:
        super().__init__(
            ValueType.Co2,
            DEVICE_CLASS_CO2,
            CONCENTRATION_PARTS_PER_MILLION,
            STATE_CLASS_MEASUREMENT,
        )

    def convert_taphome_to_ha(self, value: int) -> int:
        return round(value)


class TapHomeBrightnessSensorType(TapHomeSensorType):
    def __init__(self) -> None:
        super().__init__(
            ValueType.SensorBrightness,
            DEVICE_CLASS_ILLUMINANCE,
            LIGHT_LUX,
            STATE_CLASS_MEASUREMENT,
        )

    def convert_taphome_to_ha(self, value: int) -> int:
        value = value * 100_000
        return round(value, 2)


class TapHomeWindSpeedSensorType(TapHomeSensorType):
    def __init__(self) -> None:
        super().__init__(
            ValueType.WindSpeed,
            None,
            SPEED_KILOMETERS_PER_HOUR,
            STATE_CLASS_MEASUREMENT,
        )

    def convert_taphome_to_ha(self, value: int) -> int:
        return round(value, 1)


class TapHomeAnalogInputSensorType(TapHomeSensorType):
    def __init__(self) -> None:
        super().__init__(
            ValueType.AnalogInputValue,
            None,
            PERCENTAGE,
            STATE_CLASS_MEASUREMENT,
        )

    def convert_taphome_to_ha(self, value: int) -> int:
        return TapHomeEntity.convert_taphome_percentage_to_ha(value)


class TapHomePulseCounterTotalImpulseCountSensorType(TapHomeSensorType):
    def __init__(self) -> None:
        super().__init__(
            ValueType.TotalImpulseCount,
            None,
            " ",
            STATE_CLASS_TOTAL_INCREASING,
        )


class TapHomePulseCounterCurrentHourImpulseCountSensorType(TapHomeSensorType):
    def __init__(self) -> None:
        super().__init__(
            ValueType.CurrentHourImpulseCount,
            None,
            " ",
            STATE_CLASS_MEASUREMENT,
        )


class TapHomePulseCounterLastMeasuredFrequencySensorType(TapHomeSensorType):
    def __init__(self) -> None:
        super().__init__(
            ValueType.LastMeasuredFrequency,
            None,
            FREQUENCY_HERTZ,
            STATE_CLASS_MEASUREMENT,
        )

    def convert_taphome_to_ha(self, value: int) -> int:
        return round(value, 1)


class TapHomeVariableType(TapHomeSensorType):
    def __init__(self) -> None:
        super().__init__(
            ValueType.VariableState,
            None,
            " ",  # this is workaround for https://github.com/home-assistant/architecture/issues/478
            STATE_CLASS_MEASUREMENT,
        )

    def convert_taphome_to_ha(self, value: int) -> int:
        return round(value, 1)


class SensorConfigEntry(TapHomeConfigEntry):
    def __init__(self, device_config: dict):
        super().__init__(device_config)
        self._device_class = self.get_optional("device_class", None)
        self._value_type = self.get_optional("value_type", None)
        self._unit_of_measurement = self.get_optional("unit_of_measurement", None)
        self._state_class = self.get_optional("state_class", None)
        if self.get_optional("was_measured", None) is True:
            self._state_class = STATE_CLASS_MEASUREMENT

    @property
    def device_class(self) -> str:
        return self._device_class

    @property
    def value_type(self) -> ValueType:
        return self._value_type

    @property
    def unit_of_measurement(self) -> str:
        return self._unit_of_measurement

    @property
    def state_class(self) -> str:
        return self._state_class


class TapHomeSensor(TapHomeEntity[TapHomeState], SensorEntity):
    """Representation of an sensor"""

    def __init__(
        self,
        hass: HomeAssistant,
        core_config: TapHomeCoreConfigEntry,
        config_entry: SensorConfigEntry,
        coordinator: TapHomeDataUpdateCoordinator,
        sensor_type: TapHomeSensorType,
    ):
        assert sensor_type is not None
        self._sensor_type = sensor_type
        unique_id_determination = f"{DOMAIN}.{self._sensor_type.value_type.name}"

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
            if sensor_value is None:
                return None
            try:
                return sensor_type.convert_taphome_to_ha(sensor_value)
            except:
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
    """Create TapHomeSensors from SensorConfigEntry when devices is discovered"""

    def __init__(
        self,
        hass: HomeAssistant,
        core_config: TapHomeCoreConfigEntry,
        config_entry: SensorConfigEntry,
        coordinator: TapHomeDataUpdateCoordinator,
        add_entities: AddEntitiesCallback,
    ):
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
        self.create_entities()

    def create_entities(self) -> None:
        if self.taphome_device is not None:
            self._was_entities_created = True

            supported_sensor_types: typing.List[TapHomeSensorType] = [
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
                TapHomeVariableType(),
            ]

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
    add_entry_requests: typing.List[AddEntryRequest] = hass.data[TAPHOME_PLATFORM][
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
