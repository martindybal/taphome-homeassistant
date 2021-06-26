"""TapHome light integration."""
import logging

from homeassistant.components.binary_sensor import (DEVICE_CLASS_CONNECTIVITY,
                                                    DEVICE_CLASS_MOTION,
                                                    BinarySensorEntity)

from . import TAPHOME_API_SERVICE, TAPHOME_DEVICES
from .taphome_entity import TapHomeEntity
from .taphome_sdk import *


class TapHomeIsAliveSensor(BinarySensorEntity):
    sensor_value_type = ValueType.Motion

    def __init__(self, tapHomeApiService: TapHomeApiService):
        self._tapHomeApiService = tapHomeApiService
        self._is_on = None

    @property
    def unique_id(self):
        return "taphome_is_alive_sensor.taphome".lower()

    @property
    def name(self):
        return "TapHome is alive sensor"

    @property
    def device_class(self):
        """Return type of sensor."""
        return DEVICE_CLASS_CONNECTIVITY

    @property
    def is_on(self) -> bool:
        """Return if the binary sensor is currently on or off."""
        return self._is_on

    async def async_update(self):
        try:
            location = await self._tapHomeApiService.async_get_location()
            self._is_on = location is not None
        except Exception:
            self._is_on = False


class TapHomeBinarySensorBase(TapHomeEntity, BinarySensorEntity):
    def __init__(self, sensorService: SensorService, device: Device):
        super(TapHomeBinarySensorBase, self).__init__(device=device)

        self._sensorService = sensorService
        self._device = device

        self._is_on = None

    @property
    def is_on(self) -> bool:
        """Return if the binary sensor is currently on or off."""
        return self._is_on

    @property
    def sensor_value_type(self) -> ValueType:
        """Return type of sensor."""
        pass

    def async_update(self):
        return self.async_refresh_state()

    async def async_refresh_state(self):
        value = await self._sensorService.async_get_sensor_value(
            self._device, self.sensor_value_type
        )
        self._is_on = self.taphome_to_hass_value(value)

    def taphome_to_hass_value(self, value: int):
        if value == 1:
            return True
        elif value == 0:
            return False
        else:
            return None


class TapHomeMotionSensor(TapHomeBinarySensorBase):
    sensor_value_type = ValueType.Motion

    def __init__(self, sensorService: SensorService, device: Device):
        super(TapHomeMotionSensor, self).__init__(sensorService, device)

    @property
    def device_class(self):
        """Return type of sensor."""
        return DEVICE_CLASS_MOTION


class TapHomeGenericReedContact(TapHomeBinarySensorBase):
    sensor_value_type = ValueType.ReedContact

    def __init__(self, sensorService: SensorService, device: Device):
        super(TapHomeGenericReedContact, self).__init__(sensorService, device)


class TapHomeBinaryVariable(TapHomeBinarySensorBase):
    sensor_value_type = ValueType.VariableState

    def __init__(self, sensorService: SensorService, device: Device):
        super(TapHomeBinaryVariable, self).__init__(sensorService, device)


async def async_setup_platform(hass, config, async_add_entities, platformConfig):
    tapHomeApiService = platformConfig[TAPHOME_API_SERVICE]
    devices = platformConfig[TAPHOME_DEVICES]
    sensorService = SensorService(tapHomeApiService)

    sensors = [TapHomeIsAliveSensor(tapHomeApiService)]
    for device in devices:
        for sensor in await async_create_sensors(sensorService, device):
            sensors.append(sensor)

    async_add_entities(sensors)


async def async_create_sensors(sensorService: SensorService, device: Device):
    sensors = []
    sensorTypes = [
        TapHomeMotionSensor,
        TapHomeGenericReedContact,
        TapHomeBinaryVariable,
    ]
    for sensorType in sensorTypes:
        if sensorType.sensor_value_type in device.supportedValues:
            sensor = sensorType(sensorService, device)
            sensors.append(sensor)

    return sensors
