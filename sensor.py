"""TapHome light integration."""
from .taphome_sdk import *

import logging
from homeassistant.helpers.entity import Entity
from . import TAPHOME_API_SERVICE, TAPHOME_DEVICES

from homeassistant.const import (
    DEVICE_CLASS_HUMIDITY,
    DEVICE_CLASS_TEMPERATURE,
    PERCENTAGE,
    TEMP_CELSIUS,
)


class TapHomeSensorBase(Entity):
    def __init__(self, sensorService: SensorService, device: Device):
        self._sensorService = sensorService
        self._device = device

        self._state = None

    @property
    def name(self):
        """Return the name of the light."""
        return self._device.name

    @property
    def state(self):
        """Return the value of the sensor."""
        return self._state

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
        self._state = self.taphome_to_hass_value(value)

    def taphome_to_hass_value(self, value: int):
        return value


class TapHomeHumiditySensor(TapHomeSensorBase):
    sensor_value_type = ValueType.Humidity

    def __init__(self, sensorService: SensorService, device: Device):
        super(TapHomeHumiditySensor, self).__init__(sensorService, device)

    @property
    def unit_of_measurement(self):
        """Return the unit of measurement that the sensor is expressed in."""
        return PERCENTAGE

    @property
    def device_class(self):
        """Return type of sensor."""
        return DEVICE_CLASS_HUMIDITY

    def taphome_to_hass_value(self, value: int):
        return value * 100


class TapHomeTemperatureSensor(TapHomeSensorBase):
    sensor_value_type = ValueType.RealTemperature

    def __init__(self, sensorService: SensorService, device: Device):
        super(TapHomeTemperatureSensor, self).__init__(sensorService, device)

    @property
    def unit_of_measurement(self):
        """Return the unit of measurement that the sensor is expressed in."""
        return TEMP_CELSIUS

    @property
    def device_class(self):
        """Return type of sensor."""
        return DEVICE_CLASS_TEMPERATURE


class TapHomeVariable(TapHomeSensorBase):
    sensor_value_type = ValueType.VariableState

    def __init__(self, sensorService: SensorService, device: Device):
        super(TapHomeVariable, self).__init__(sensorService, device)


async def async_setup_platform(hass, config, async_add_entities, platformConfig):
    tapHomeApiService = platformConfig[TAPHOME_API_SERVICE]
    devices = platformConfig[TAPHOME_DEVICES]
    sensorService = SensorService(tapHomeApiService)

    sensors = []
    for device in devices:
        for sensor in await async_create_sensors(sensorService, device):
            sensors.append(sensor)

    async_add_entities(sensors)


async def async_create_sensors(sensorService: SensorService, device: Device):
    sensors = []
    if TapHomeHumiditySensor.sensor_value_type in device.supportedValues:
        sensor = TapHomeHumiditySensor(sensorService, device)
        sensors.append(sensor)

    if TapHomeTemperatureSensor.sensor_value_type in device.supportedValues:
        sensor = TapHomeTemperatureSensor(sensorService, device)
        sensors.append(sensor)

    if TapHomeVariable.sensor_value_type in device.supportedValues:
        sensor = TapHomeVariable(sensorService, device)
        sensors.append(sensor)

    for sensor in sensors:
        await sensor.async_refresh_state()

    return sensors