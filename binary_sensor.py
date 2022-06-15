"""TapHome binary_sensor integration."""
import typing

from homeassistant.components.binary_sensor import (
    DEVICE_CLASS_CONNECTIVITY,
    DEVICE_CLASS_MOTION,
    DOMAIN,
    BinarySensorEntity,
)
from homeassistant.const import CONF_BINARY_SENSORS
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .add_entry_request import AddEntryRequest
from .const import TAPHOME_PLATFORM
from .coordinator import TapHomeDataUpdateCoordinator
from .taphome_entity import *
from .taphome_sdk import *


class TapHomeIsAliveSensor(BinarySensorEntity):
    sensor_value_type = ValueType.Motion

    def __init__(
        self,
        core_config: TapHomeCoreConfigEntry,
        coordinator: TapHomeDataUpdateCoordinator,
    ):
        self._core_config = core_config
        self.coordinator = coordinator

        unique_id_core_id = f".{core_config.id}" if core_config.id is not None else ""
        self._unique_id = f"taphome{unique_id_core_id}.{DOMAIN}.isalive".lower()

    @property
    def unique_id(self):
        return self._unique_id

    @property
    def name(self):
        core_id = f" {self._core_config.id}" if self._core_config.id is not None else ""
        return f"TapHome{core_id} is alive sensor"

    @property
    def device_class(self):
        """Return type of binary sensor from component DEVICE_CLASSES."""
        return DEVICE_CLASS_CONNECTIVITY

    @property
    def is_on(self) -> bool:
        """Return if the binary sensor is currently on or off."""
        return self.coordinator.last_update_success


class TapHomeBinarySensorType:
    def __init__(self, value_type: ValueType, device_class: str = None) -> None:
        self.value_type = value_type
        self.device_class = device_class


class TapHomeMotionBinarySensorType(TapHomeBinarySensorType):
    def __init__(self) -> None:
        super().__init__(
            ValueType.Motion,
            DEVICE_CLASS_MOTION,
        )


class TapHomeReedContactBinarySensorType(TapHomeBinarySensorType):
    def __init__(self) -> None:
        super().__init__(
            ValueType.ReedContact,
            None,
        )


class TapHomeVariableBinarySensorType(TapHomeBinarySensorType):
    def __init__(self) -> None:
        super().__init__(
            ValueType.VariableState,
            None,
        )


class BinarySensorConfigEntry(TapHomeConfigEntry):
    def __init__(self, device_config: dict):
        super().__init__(device_config)
        self._device_class = self.get_optional("device_class", None)
        self._value_type = self.get_optional("value_type", None)

    @property
    def device_class(self) -> str:
        return self._device_class

    @property
    def value_type(self) -> ValueType:
        return self._value_type


class TapHomeBinarySensor(TapHomeEntity[TapHomeState], BinarySensorEntity):
    """Representation of an binary sensor"""

    def __init__(
        self,
        hass: HomeAssistant,
        core_config: TapHomeCoreConfigEntry,
        config_entry: BinarySensorConfigEntry,
        coordinator: TapHomeDataUpdateCoordinator,
        sensor_type: TapHomeBinarySensorType,
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
    def device_class(self) -> str:
        """Return type of binary sensor from component DEVICE_CLASSES."""
        return self._sensor_type.device_class

    @property
    def is_on(self) -> bool:
        """Return if the binary sensor is currently on or off."""
        if self.taphome_state is not None:
            sensor_type = self._sensor_type
            sensor_value = self.taphome_state.get_device_value(sensor_type.value_type)
            return TapHomeEntity.convert_taphome_bool_to_ha(sensor_value)


class TapHomeBinarySensorCreateRequest(
    TapHomeDataUpdateCoordinatorObject[TapHomeState]
):
    """Create TapHomeBinarySensor from BinarySensorConfigEntry when devices is discovered"""

    def __init__(
        self,
        hass: HomeAssistant,
        core_config: TapHomeCoreConfigEntry,
        config_entry: BinarySensorConfigEntry,
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

            supported_sensor_types: typing.List[TapHomeBinarySensorType] = [
                TapHomeMotionBinarySensorType(),
                TapHomeReedContactBinarySensorType(),
                TapHomeVariableBinarySensorType(),
            ]

            binary_sensors = []
            for sensor_type in supported_sensor_types:
                if self.taphome_device.supports_value(sensor_type.value_type):
                    if self._config_entry.device_class is not None:
                        sensor_type.device_class = self._config_entry.device_class

                    binary_sensor = TapHomeBinarySensor(
                        self._hass,
                        self._core_config,
                        self._config_entry,
                        self.coordinator,
                        sensor_type,
                    )
                    binary_sensors.append(binary_sensor)
            self.add_entities(binary_sensors)


def setup_platform(
    hass: HomeAssistant,
    config,
    add_entities: AddEntitiesCallback,
    discovery_info=None,
) -> None:
    """Set up the binary sensor platform."""
    add_entry_requests: typing.List[AddEntryRequest] = hass.data[TAPHOME_PLATFORM][
        CONF_BINARY_SENSORS
    ]

    for add_entry_request in add_entry_requests:
        TapHomeBinarySensorCreateRequest(
            hass,
            add_entry_request._core_config,
            add_entry_request.config_entry,
            add_entry_request.coordinator,
            add_entities,
        )

    cores = {}
    is_alive_sensors = []
    for domain in hass.data[TAPHOME_PLATFORM]:
        for add_entry_request in hass.data[TAPHOME_PLATFORM][domain]:
            cores[add_entry_request._core_config] = add_entry_request.coordinator

    # todo prověřit
    for core_config in cores:
        is_alive_sensors.append(TapHomeIsAliveSensor(core_config, cores[core_config]))
    add_entities(is_alive_sensors)
