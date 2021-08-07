"""TapHome light integration."""
import typing

from homeassistant.components.binary_sensor import (
    DEVICE_CLASS_CONNECTIVITY,
    DEVICE_CLASS_MOTION,
    BinarySensorEntity,
)
from homeassistant.const import CONF_BINARY_SENSORS
from homeassistant.core import HomeAssistant

from .add_entry_request import AddEntryRequest
from .const import DOMAIN
from .coordinator import TapHomeDataUpdateCoordinator
from .taphome_entity import *
from .taphome_sdk import *


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
    """Representation of an binary_sensor"""

    def __init__(
        self,
        config_entry: BinarySensorConfigEntry,
        coordinator: TapHomeDataUpdateCoordinator,
    ):
        super().__init__(config_entry.id, coordinator, TapHomeState)
        self._device_class = config_entry.device_class
        self._value_type = config_entry.value_type
        self.auto_resolve()

    @property
    def is_on(self) -> bool:
        """Return if the binary sensor is currently on or off."""
        if not self.taphome_state is None and self._value_type is not None:
            sensor_value = self.taphome_state.get_device_value(self._value_type)
            return TapHomeEntity.convert_taphome_bool_to_ha(sensor_value)

    @property
    def device_class(self):
        """Return the class of this device, from component DEVICE_CLASSES."""
        return self._device_class

    @callback
    def handle_taphome_device_change(self) -> None:
        self.auto_resolve()

    def auto_resolve(self) -> None:
        if self.taphome_device is not None and self._value_type is None:
            supported_sensor_types = [
                {"value_type": ValueType.Motion, "device_class": DEVICE_CLASS_MOTION},
                {"value_type": ValueType.ReedContact, "device_class": None},
                {"value_type": ValueType.VariableState, "device_class": None},
            ]

            for sensor_types in supported_sensor_types:
                if self.taphome_device.supports_value(sensor_types["value_type"]):
                    self._value_type = sensor_types["value_type"]
                    if self._device_class is None:
                        self._device_class = sensor_types["device_class"]


def setup_platform(
    hass: HomeAssistant,
    config,
    add_entities,
    discovery_info=None,
) -> None:
    """Set up the binary_sensor platform."""
    add_entry_requests: typing.List[AddEntryRequest] = hass.data[DOMAIN][
        CONF_BINARY_SENSORS
    ]
    binary_sensors = []
    for add_entry_request in add_entry_requests:
        binary_sensor = TapHomeBinarySensor(
            add_entry_request.config_entry, add_entry_request.coordinator
        )
        binary_sensors.append(binary_sensor)

    add_entities(binary_sensors)
