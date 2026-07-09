"""TapHome binary_sensor integration."""

from __future__ import annotations

from dataclasses import dataclass, replace
from datetime import datetime

from taphome_sdk import Device, DeviceState, HubConnectionState, TapHomeHub, ValueType
from taphome_sdk.taphome_api import ApiConnectionType

from homeassistant.components.binary_sensor import (
    DOMAIN as BINARY_SENSOR_DOMAIN,
    BinarySensorDeviceClass,
    BinarySensorEntity,
)
from homeassistant.const import EntityCategory
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from .add_entry_request import add_taphome_entities
from .const import DOMAIN
from .entity import TapHomeEntity, TapHomeSubscriptionMixin, hub_device_id
from .taphome_config_entry import (
    AddEntryRequest,
    TapHomeCoreConfig,
    TapHomeEntityConfig,
)
from .taphome_data import TapHomeConfigEntry

PARALLEL_UPDATES = 0


class TapHomeIsAliveSensor(TapHomeSubscriptionMixin, BinarySensorEntity):
    """Binary sensor reporting availability of the TapHome core."""

    sensor_value_type = ValueType.MOTION

    _attr_has_entity_name = True
    _attr_should_poll = False
    _attr_device_class = BinarySensorDeviceClass.CONNECTIVITY
    _attr_entity_category = EntityCategory.DIAGNOSTIC

    def __init__(
        self,
        core_config: TapHomeCoreConfig,
        hub: TapHomeHub,
    ) -> None:
        """Initialize is-alive sensor for a given core."""
        self._core_config = core_config

        segment = f".{core_config.unique_id_segment}" if core_config.unique_id_segment else ""
        self._attr_unique_id = (
            f"taphome{segment}.{BINARY_SENSOR_DOMAIN}.isalive".lower()
        )

        # The connectivity device class provides the entity name; the sensor
        # belongs to the Core hub device registered in async_setup_entry.
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, hub_device_id(hub.location, core_config.id))}
        )

        if not hasattr(self, "_attr_extra_state_attributes"):
            self._attr_extra_state_attributes = {}

        self._subscribe(
            hub.connection_state.changed, self._on_hub_connection_state_change
        )
        self._subscribe(
            hub.connection_type.changed, self._on_hub_connection_type_change
        )
        self._subscribe(
            hub.last_update_success_time.changed,
            self._on_hub_last_update_success_time_change,
        )

    def _on_hub_connection_state_change(
        self, _: HubConnectionState | None, current_state: HubConnectionState
    ) -> None:
        """Handle hub connection state changes."""

        self._attr_is_on = current_state is HubConnectionState.CONNECTED

    def _on_hub_connection_type_change(
        self, old_type: ApiConnectionType | None, current_type: ApiConnectionType
    ) -> None:
        """Handle hub connection state changes."""
        self._attr_extra_state_attributes["connection_type"] = current_type.value

    def _on_hub_last_update_success_time_change(
        self, old: datetime | None, last_update_success: datetime | None
    ) -> None:
        """Handle hub connection state changes."""
        self._attr_extra_state_attributes["last_update_success_time"] = (
            last_update_success
        )


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

# Every value interpretation the binary sensor platform can auto-detect; the
# subentry add flow offers these per device so a single value can be exposed.
KNOWN_BINARY_SENSOR_TYPES: tuple[TapHomeBinarySensorType, ...] = (
    MOTION_BINARY_SENSOR,
    REED_CONTACT_BINARY_SENSOR,
    VARIABLE_BINARY_SENSOR,
    SMOKE_BINARY_SENSOR,
    FLOOD_BINARY_SENSOR,
    RAINING_BINARY_SENSOR,
    IS_WINDOW_OPEN_BINARY_SENSOR,
)


class BinarySensorEntityConfig(TapHomeEntityConfig):
    """Configuration for TapHome binary sensors."""

    def __init__(self, device_config: dict) -> None:
        """Initialize binary sensor config entry."""
        super().__init__(device_config)
        self.device_class: BinarySensorDeviceClass | None = self.get_optional(
            "device_class", None
        )
        # Expose exactly this device value (per-value subentries); None keeps
        # the legacy behavior of auto-detecting every known supported value.
        self.value: int | None = self.get_optional("value", None)
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

        self._attr_device_class = sensor_type.device_class

        self._device = config.hub.get_typed_device(config.entity.id, Device)

        self._subscribe(self._device.state.changed, self._on_device_state_change)
        super().__init__(
            config,
            self._device,
            BINARY_SENSOR_DOMAIN,
            self._sensor_type.value_type.name.replace("_", ""),
        )

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
            if self.config.entity.value is not None:
                # A per-value subentry exposes exactly the selected value.
                selected = ValueType(self.config.entity.value)
                supported_sensor_types = [
                    next(
                        (
                            known
                            for known in KNOWN_BINARY_SENSOR_TYPES
                            if known.value_type is selected
                        ),
                        TapHomeBinarySensorType(selected, None),
                    )
                ]
            else:
                supported_sensor_types = list(KNOWN_BINARY_SENSOR_TYPES)

                if self.config.entity.value_type:
                    supported_sensor_types.append(
                        TapHomeBinarySensorType(
                            ValueType(self.config.entity.value_type),
                            self.config.entity.device_class,
                        )
                    )

            for sensor_type in supported_sensor_types:
                if _device.supports_value(sensor_type.value_type):
                    if self.config.entity.device_class is not None:
                        # Copy before overriding: the known types are shared.
                        sensor_type = replace(
                            sensor_type, device_class=self.config.entity.device_class
                        )

                    binary_sensor = TapHomeBinarySensor(
                        self.config,
                        sensor_type,
                    )
                    binary_sensors.append(binary_sensor)
        return binary_sensors


async def async_setup_entry(
    hass: HomeAssistant,
    entry: TapHomeConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up TapHome binary sensors from a config entry."""

    def _create_entities(
        config: AddEntryRequest[BinarySensorEntityConfig],
    ) -> list[TapHomeBinarySensor]:
        return TapHomeBinarySensorFactory(config).create_entities()

    # Per-device binary sensors are added under their device subentry; the
    # core-level "is alive" sensor has no device and belongs to the entry.
    add_taphome_entities(entry, async_add_entities, BINARY_SENSOR_DOMAIN, _create_entities)

    runtime_data = entry.runtime_data
    async_add_entities(
        [TapHomeIsAliveSensor(runtime_data.core_config, runtime_data.hub)]
    )
