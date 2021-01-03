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
        multiValueSwitchService = MultiValueSwitchService(tapHomeApiService)
        thermostat = TapHomeClimate(thermostatService, multiValueSwitchService, device)
        await thermostat.async_refresh_state()
        climates.append(thermostat)
    return climates


class TapHomeClimate(ClimateEntity):
    """Representation of an Thermostat"""

    def __init__(
        self,
        thermostatService: ThermostatService,
        multiValueSwitchService: MultiValueSwitchService,
        device: TapHomeClimateDevice,
    ):
        self._thermostatService = thermostatService
        self._multiValueSwitchService = multiValueSwitchService
        self._device = device
        self._supported_features = SUPPORT_TARGET_TEMPERATURE
        self._target_temperature = None
        self._hvac_mode = None
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
        return self._hvac_mode

    @property
    def hvac_modes(self):
        """Return the list of available operation/controller modes."""
        if self._device.mode == None:
            return []
        else:
            return [HVAC_MODE_OFF, HVAC_MODE_HEAT, HVAC_MODE_COOL, HVAC_MODE_HEAT_COOL]

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

        mode_value = TapHomeClimate.hass_to_taphome_hvac(hvac_mode)

        if mode_value is not None:
            result = await self._multiValueSwitchService.async_set_value(
                self._device.mode, mode_value
            )

            if result == ValueChangeResult.FAILED:
                _LOGGER.warning(
                    f"{self._device.mode.deviceId} - {self._device.mode.name} changing hvac to {hvac_mode} failed!"
                )
                await self.async_refresh_mode_state()
            else:
                self._hvac_mode = hvac_mode
        else:
            _LOGGER.warning(
                f"{hvac_mode} is unknown hvac mode for {self._device.mode.deviceId}"
            )

    def async_update(self, **kwargs):
        return self.async_refresh_state()

    async def async_refresh_state(self):
        await self.async_refresh_thermostat_state()
        await self.async_refresh_mode_state()

    async def async_refresh_thermostat_state(self):
        state = await self._thermostatService.async_get_thermostat_state(
            self._device.thermostat
        )
        self._target_temperature = state.desired_temperature
        self._current_temperature = state.real_temperature
        self._min_temperature = state.min_temperature
        self._max_temperature = state.max_temperature

    async def async_refresh_mode_state(self):
        if self._device.mode:
            mode_state = (
                await self._multiValueSwitchService.async_get_multi_value_switch_state(
                    self._device.mode
                )
            )
            self._hvac_mode = TapHomeClimate.taphome_to_hass_hvac(
                mode_state.multi_value_switch_state
            )

    @staticmethod
    def hass_to_taphome_hvac(hvac: str) -> int:
        modes = {
            HVAC_MODE_OFF: 0,
            HVAC_MODE_HEAT: 1,
            HVAC_MODE_COOL: 2,
            HVAC_MODE_HEAT_COOL: 3,
        }

        return modes.get(hvac, None)

    @staticmethod
    def taphome_to_hass_hvac(hvac: int) -> str:
        modes = {
            0: HVAC_MODE_OFF,
            1: HVAC_MODE_HEAT,
            2: HVAC_MODE_COOL,
            3: HVAC_MODE_HEAT_COOL,
        }
        return modes.get(hvac, None)