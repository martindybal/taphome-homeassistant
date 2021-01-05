"""TapHome climate integration."""
from .taphome_sdk import *
from enum import Enum

import logging
import typing
from homeassistant.components.climate import ClimateEntity

from homeassistant.const import ATTR_TEMPERATURE, TEMP_CELSIUS
from homeassistant.components.climate.const import (
    SUPPORT_TARGET_TEMPERATURE,
    HVAC_MODE_OFF,
    HVAC_MODE_HEAT,
    HVAC_MODE_COOL,
    HVAC_MODE_HEAT_COOL,
)

from . import TAPHOME_API_SERVICE, TAPHOME_DEVICES, TapHomeClimateDevice

_LOGGER = logging.getLogger(__name__)


async def async_setup_platform(hass, config, async_add_entities, platformConfig):
    tapHomeApiService = platformConfig[TAPHOME_API_SERVICE]
    devices = platformConfig[TAPHOME_DEVICES]

    climates = []
    for device in devices:
        for climate in await async_create_climate(tapHomeApiService, device):
            climates.append(climate)

    async_add_entities(climates)


async def async_create_climate(
    tapHomeApiService: TapHomeApiService, device: TapHomeClimateDevice
) -> typing.List[ClimateEntity]:
    climates = []
    if "VirtualThermostatDummy" == device.thermostat.type:
        thermostatService = ThermostatService(tapHomeApiService)
        thermostat = TapHomeClimate(thermostatService, device)
        climates.append(thermostat)
    return climates


class TapHomeClimate(ClimateEntity):
    """Representation of an Thermostat"""

    def __init__(
        self,
        thermostatService: ThermostatService,
        device: TapHomeClimateDevice,
    ):
        self._thermostatService = thermostatService
        self._device = device
        self._supported_features = SUPPORT_TARGET_TEMPERATURE
        self._target_temperature = None
        self._current_temperature = None
        self._min_temperature = None
        self._max_temperature = None

    @property
    def supported_features(self):
        return self._supported_features

    @property
    def name(self):
        return self._device.thermostat.name

    @property
    def temperature_unit(self):
        return TEMP_CELSIUS

    @property
    def target_temperature(self):
        return self._target_temperature

    @property
    def current_temperature(self):
        return self._current_temperature

    @property
    def min_temp(self):
        return self._min_temperature

    @property
    def max_temp(self):
        return self._max_temperature

    @property
    def hvac_mode(self):
        """Return current operation ie. heat, cool, idle."""
        return self._device.controller.hvac_mode

    @property
    def hvac_modes(self):
        """Return the list of available operation/controller modes."""
        return self._device.controller.hvac_modes

    async def async_set_temperature(self, **kwargs):
        temp = kwargs.get(ATTR_TEMPERATURE)

        result = await self._thermostatService.async_set_desired_temperature(
            self._device.thermostat, temp
        )

        if result == ValueChangeResult.FAILED:
            await self.async_refresh_thermostat_state()
        else:
            self._target_temperature = temp

    async def async_set_hvac_mode(self, hvac_mode):
        """Set new target hvac mode."""
        await self._device.controller.async_set_hvac_mode(hvac_mode)

    def async_update(self, **kwargs):
        return self.async_refresh_state()

    async def async_refresh_state(self):
        await self.async_refresh_thermostat_state()
        await self._device.controller.async_refresh_state()

    async def async_refresh_thermostat_state(self):
        state = await self._thermostatService.async_get_thermostat_state(
            self._device.thermostat
        )
        self._target_temperature = state.desired_temperature
        self._current_temperature = state.real_temperature
        self._min_temperature = state.min_temperature
        self._max_temperature = state.max_temperature