"""TapHome binary_sensor integration."""

from dataclasses import dataclass

from homeassistant.components.binary_sensor import (
    DOMAIN as BINARY_SENSOR_DOMAIN,
    BinarySensorDeviceClass,
    BinarySensorEntity,
)
from homeassistant.const import CONF_BINARY_SENSORS
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import cached_property
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .add_entry_request import AddEntryRequest
from .const import TAPHOME_PLATFORM
from .coordinator import TapHomeDataUpdateCoordinator
from .taphome_entity import (
    TapHomeConfigEntry,
    TapHomeCoreConfigEntry,
    TapHomeDataUpdateCoordinatorObject,
    TapHomeEntity,
    callback,
)
from .taphome_sdk import TapHomeState, ValueType


class TapHomeIsAliveSensor(BinarySensorEntity):
    """Binary sensor reporting availability of the TapHome core."""

    sensor_value_type = ValueType.MOTION

    def __init__(
        self,
        core_config: TapHomeCoreConfigEntry,
        coordinator: TapHomeDataUpdateCoordinator,
    ) -> None:
        """Initialize is-alive sensor for a given core."""
        self._core_config = core_config
        self.coordinator = coordinator

        unique_id_core_id = f".{core_config.id}" if core_config.id is not None else ""
        self._attr_unique_id = (
            f"taphome{unique_id_core_id}.{BINARY_SENSOR_DOMAIN}.isalive".lower()
        )

    @cached_property
    def name(self) -> str | None:
        """Return human readable name for this sensor."""
        core_id = f" {self._core_config.id}" if self._core_config.id is not None else ""
        return f"TapHome{core_id} is alive sensor"

    @cached_property
    def device_class(self) -> BinarySensorDeviceClass | None:
        """Return type of binary sensor from component DEVICE_CLASSES."""
        return BinarySensorDeviceClass.CONNECTIVITY

    @property
    def is_on(self) -> bool | None:
        """Return if the binary sensor is currently on or off."""
        return self.coordinator.last_update_success


@dataclass(slots=True)
class TapHomeBinarySensorType:
    """Metadata about a TapHome binary sensor value."""

    value_type: ValueType
    device_class: BinarySensorDeviceClass | None = None


MOTION_BINARY_SENSOR = TapHomeBinarySensorType(
    ValueType.MOTION,
    BinarySensorDeviceClass.MOTION,
)


REED_CONTACT_BINARY_SENSOR = TapHomeBinarySensorType(
    ValueType.REED_CONTACT,
    None,
)


SMOKE_BINARY_SENSOR = TapHomeBinarySensorType(
    ValueType.SMOKE,
    BinarySensorDeviceClass.SMOKE,
)


FLOOD_BINARY_SENSOR = TapHomeBinarySensorType(
    ValueType.FLOOD_STATE,
    BinarySensorDeviceClass.MOISTURE,
)


IS_WINDOW_OPEN_BINARY_SENSOR = TapHomeBinarySensorType(
    ValueType.IS_WINDOW_OPEN,
    BinarySensorDeviceClass.WINDOW,
)


VARIABLE_BINARY_SENSOR = TapHomeBinarySensorType(
    ValueType.VARIABLE_STATE,
    None,
)


class BinarySensorConfigEntry(TapHomeConfigEntry):
    """Configuration for TapHome binary sensors."""

    def __init__(self, device_config: dict) -> None:
        """Initialize binary sensor config entry."""
        super().__init__(device_config)
        self._device_class = self.get_optional("device_class", None)
        self._value_type = self.get_optional("value_type", None)

    @property
    def device_class(self) -> BinarySensorDeviceClass | None:
        """Return Home Assistant device class if configured."""
        return self._device_class

    @property
    def value_type(self) -> ValueType | None:
        """Return TapHome value type used by this sensor."""
        return self._value_type


@dataclass(slots=True, frozen=True)
class BinarySensorInitContext:
    """Grouping of dependencies required to create a binary sensor."""

    hass: HomeAssistant
    core_config: TapHomeCoreConfigEntry
    config_entry: "BinarySensorConfigEntry"
    coordinator: TapHomeDataUpdateCoordinator


class TapHomeBinarySensor(TapHomeEntity[TapHomeState], BinarySensorEntity):
    """Representation of an binary sensor."""

    def __init__(
        self, context: BinarySensorInitContext, sensor_type: TapHomeBinarySensorType
    ) -> None:
        """Initialize TapHome binary sensor entity."""
        assert sensor_type is not None
        self._sensor_type = sensor_type
        unique_id_determination = f"{BINARY_SENSOR_DOMAIN}.{self._sensor_type.value_type.name.replace('_', '')}"

        super().__init__(
            context.hass,
            context.core_config,
            context.config_entry,
            unique_id_determination,
            context.coordinator,
            TapHomeState,
        )

    @cached_property
    def device_class(self) -> BinarySensorDeviceClass | None:
        """Return type of binary sensor from component DEVICE_CLASSES."""
        return self._sensor_type.device_class

    @property
    def is_on(self) -> bool | None:
        """Return if the binary sensor is currently on or off."""

        if self.taphome_state is not None:
            sensor_type = self._sensor_type
            sensor_value = self.taphome_state.get_device_int_value(
                sensor_type.value_type
            )
            return TapHomeEntity.convert_taphome_bool_to_ha(sensor_value)
        return None


class TapHomeBinarySensorCreateRequest(
    TapHomeDataUpdateCoordinatorObject[TapHomeState]
):
    """Create TapHomeBinarySensor from BinarySensorConfigEntry when devices is discovered."""

    def __init__(
        self, context: BinarySensorInitContext, add_entities: AddEntitiesCallback
    ) -> None:
        """Initialize request for given configuration entry."""
        self._context = context
        self.add_entities = add_entities
        self._was_entities_created = False

        super().__init__(context.config_entry.id, context.coordinator, TapHomeState)

    @callback
    def handle_taphome_device_change(self) -> None:
        """Create sensors again when TapHome device is replaced."""
        self.create_entities()

    def create_entities(self) -> None:
        """Instantiate sensors for each supported value type."""
        if self.taphome_device is not None:
            self._was_entities_created = True

            supported_sensor_types: list[TapHomeBinarySensorType] = [
                MOTION_BINARY_SENSOR,
                REED_CONTACT_BINARY_SENSOR,
                VARIABLE_BINARY_SENSOR,
                SMOKE_BINARY_SENSOR,
                FLOOD_BINARY_SENSOR,
                IS_WINDOW_OPEN_BINARY_SENSOR,
            ]

            if self._context.config_entry.value_type:
                supported_sensor_types.append(
                    TapHomeBinarySensorType(
                        ValueType(self._context.config_entry.value_type),
                        self._context.config_entry.device_class,
                    )
                )

            binary_sensors = []
            for sensor_type in supported_sensor_types:
                if self.taphome_device.supports_value(sensor_type.value_type):
                    if self._context.config_entry.device_class is not None:
                        sensor_type.device_class = (
                            self._context.config_entry.device_class
                        )

                    binary_sensor = TapHomeBinarySensor(
                        self._context,
                        sensor_type,
                    )
                    binary_sensors.append(binary_sensor)
            self.add_entities(binary_sensors)


def setup_platform(
    hass: HomeAssistant,
    _config,
    add_entities: AddEntitiesCallback,
    _discovery_info=None,
) -> None:
    """Set up the binary sensor platform."""
    add_entry_requests: list[AddEntryRequest[BinarySensorConfigEntry]] = hass.data[
        TAPHOME_PLATFORM
    ][CONF_BINARY_SENSORS]

    for add_entry_request in add_entry_requests:
        context = BinarySensorInitContext(
            hass=hass,
            core_config=add_entry_request.core_config,
            config_entry=add_entry_request.config_entry,
            coordinator=add_entry_request.coordinator,
        )
        TapHomeBinarySensorCreateRequest(context, add_entities)

    cores = {}
    is_alive_sensors = []
    for domain in hass.data[TAPHOME_PLATFORM]:
        for add_entry_request in hass.data[TAPHOME_PLATFORM][domain]:
            cores[add_entry_request.core_config] = add_entry_request.coordinator

    for core_config, coordinator in cores.items():
        is_alive_sensors.append(TapHomeIsAliveSensor(core_config, coordinator))
    add_entities(is_alive_sensors)
