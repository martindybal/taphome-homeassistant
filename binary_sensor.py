"""TapHome binary_sensor integration."""

from __future__ import annotations

from dataclasses import dataclass

from .taphome_sdk.taphome_api import ApiConnectionType
from homeassistant.components.binary_sensor import (
    DOMAIN as BINARY_SENSOR_DOMAIN,
    BinarySensorDeviceClass,
    BinarySensorEntity,
)
from homeassistant.const import CONF_BINARY_SENSORS
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import TAPHOME_PLATFORM
from .taphome_config_entry import (
    AddEntryRequest,
    TapHomeCoreConfig,
    TapHomeEntityConfig,
)
from .taphome_entity import TapHomeEntity
from .taphome_sdk import (
    Device,
    DeviceState,
    HubConnectionState,
    TapHomeHub,
    ValueType,
)


class TapHomeIsAliveSensor(BinarySensorEntity):
    """Binary sensor reporting availability of the TapHome core."""

    sensor_value_type = ValueType.MOTION

    def __init__(
        self,
        core_config: TapHomeCoreConfig,
        hub: TapHomeHub,
    ) -> None:
        """Initialize is-alive sensor for a given core."""
        self._core_config = core_config

        core_id = f" {core_config.id}" if core_config.id else ""
        self._attr_unique_id = (
            f"taphome{core_id.replace(' ', '.')}.{BINARY_SENSOR_DOMAIN}.isalive".lower()
        )

        self._attr_name = f"TapHome{core_id} is alive sensor"
        self._attr_device_class = BinarySensorDeviceClass.CONNECTIVITY

        hub.connection_state.changed += self._on_hub_connection_state_change
        hub.connection_type.changed += self._on_hub_connection_type_change
        self._add_connection_type_attribute(hub.connection_type.value)

    def _on_hub_connection_state_change(
        self, _: HubConnectionState | None, current_state: HubConnectionState
    ) -> None:
        """Handle hub connection state changes."""
        if not hasattr(self, "_attr_extra_state_attributes"):
            self._attr_extra_state_attributes = {}
        self._attr_is_on = current_state == HubConnectionState.CONNECTED

    def _on_hub_connection_type_change(
        self, old_type: ApiConnectionType | None, current_type: ApiConnectionType
    ) -> None:
        """Handle hub connection state changes."""
        self._add_connection_type_attribute(current_type)

    def _add_connection_type_attribute(self, current_type: ApiConnectionType):
        self._attr_extra_state_attributes["connection_type"] = current_type.value


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


RAINING_BINARY_SENSOR = TapHomeBinarySensorType(
    ValueType.RAINING,
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


class BinarySensorEntityConfig(TapHomeEntityConfig):
    """Configuration for TapHome binary sensors."""

    def __init__(self, device_config: dict) -> None:
        """Initialize binary sensor config entry."""
        super().__init__(device_config)
        self.device_class: BinarySensorDeviceClass | None = self.get_optional(
            "device_class", None
        )
        self.value_type: ValueType | None = self.get_optional("value_type", None)


class TapHomeBinarySensor(TapHomeEntity, BinarySensorEntity):
    """Representation of an binary sensor."""

    def __init__(
        self,
        config: AddEntryRequest[BinarySensorEntityConfig],
        sensor_type: TapHomeBinarySensorType,
    ) -> None:
        """Initialize TapHome binary sensor entity."""
        self._sensor_type = sensor_type
        unique_id_determination = f"{BINARY_SENSOR_DOMAIN}.{self._sensor_type.value_type.name.replace('_', '')}"

        self._attr_device_class = sensor_type.device_class

        self._device = config.hub.get_typed_device(config.entity.id, Device)

        self._device.state.changed += self._on_device_state_change
        super().__init__(config, self._device, unique_id_determination)

    def _on_device_state_change(
        self, _: DeviceState | None, current_state: DeviceState
    ) -> None:
        """Handle device state change event."""
        value = current_state.get_device_value(self._sensor_type.value_type)
        self._attr_is_on = TapHomeEntity.convert_th_bool_to_ha(value)


class TapHomeBinarySensorFactory:
    """Create TapHomeBinarySensor from BinarySensorConfigEntry when devices is discovered."""

    def __init__(self, config: AddEntryRequest[BinarySensorEntityConfig]) -> None:
        """Initialize request for given configuration entry."""
        self.config = config

    def create_entities(self) -> list[TapHomeBinarySensor]:
        """Instantiate sensors for each supported value type."""
        binary_sensors: list[TapHomeBinarySensor] = []
        _device = self.config.hub.get_typed_device(self.config.entity.id, Device)
        if _device is not None:
            supported_sensor_types: list[TapHomeBinarySensorType] = [
                MOTION_BINARY_SENSOR,
                REED_CONTACT_BINARY_SENSOR,
                VARIABLE_BINARY_SENSOR,
                SMOKE_BINARY_SENSOR,
                FLOOD_BINARY_SENSOR,
                RAINING_BINARY_SENSOR,
                IS_WINDOW_OPEN_BINARY_SENSOR,
            ]

            if self.config.entity.value_type:
                supported_sensor_types.append(
                    TapHomeBinarySensorType(
                        ValueType(self.config.entity.value_type),
                        self.config.entity.device_class,
                    )
                )

            binary_sensors = []
            for sensor_type in supported_sensor_types:
                if _device.supports_value(sensor_type.value_type):
                    if self.config.entity.device_class is not None:
                        sensor_type.device_class = self.config.entity.device_class

                    binary_sensor = TapHomeBinarySensor(
                        self.config,
                        sensor_type,
                    )
                    binary_sensors.append(binary_sensor)
        return binary_sensors


def setup_platform(
    hass: HomeAssistant,
    _config,
    add_entities: AddEntitiesCallback,
    _discovery_info=None,
) -> None:
    """Set up the binary sensor platform."""
    add_entry_requests: list[AddEntryRequest[BinarySensorEntityConfig]] = hass.data[
        TAPHOME_PLATFORM
    ][CONF_BINARY_SENSORS]

    binary_sensors: list[BinarySensorEntity] = []
    for config in add_entry_requests:
        binary_sensors.extend(TapHomeBinarySensorFactory(config).create_entities())

    cores = {}
    for domain in hass.data[TAPHOME_PLATFORM]:
        for add_entry_request in hass.data[TAPHOME_PLATFORM][domain]:
            cores[add_entry_request.core] = add_entry_request.hub

    for core_config, hub in cores.items():
        binary_sensors.append(TapHomeIsAliveSensor(core_config, hub))

    add_entities(binary_sensors)
