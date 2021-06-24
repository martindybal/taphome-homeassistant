import logging
import typing

from homeassistant.components.climate.const import (HVAC_MODE_COOL,
                                                    HVAC_MODE_HEAT,
                                                    HVAC_MODE_HEAT_COOL,
                                                    HVAC_MODE_OFF)

from .taphome_sdk import *

_LOGGER = logging.getLogger(__name__)


class TapHomeClimateController:
    @property
    def hvac_mode(self):
        """Return current operation ie. heat, cool, idle."""
        pass

    @property
    def hvac_modes(self):
        """Return the list of available operation/controller modes."""
        pass

    async def async_set_hvac_mode(self, hvac_mode):
        """Set new target hvac mode."""
        pass

    async def async_refresh_state(self):
        pass


class TapHomeNoneClimateController(TapHomeClimateController):
    @property
    def hvac_mode(self):
        """Return current operation ie. heat, cool, idle."""
        return None

    @property
    def hvac_modes(self):
        """Return the list of available operation/controller modes."""
        return []

    async def async_set_hvac_mode(self, hvac_mode):
        """This is null object pattern. It can not set new target hvac mode."""

    async def async_refresh_state(self):
        """This is null object pattern. It can not refresh state."""


class TapHomeSwitchClimateController(TapHomeClimateController):
    def __init__(
        self, switchService: SwitchService, device: Device, supported_hvac_mode
    ):
        self._switchService = switchService
        self._device = device
        self._hvac_mode = None
        self._supported_hvac_mode = supported_hvac_mode
        self._hvac_modes = [HVAC_MODE_OFF, supported_hvac_mode]

    @property
    def hvac_mode(self):
        """Return current operation ie. heat, cool, idle."""
        return self._hvac_mode

    @property
    def hvac_modes(self):
        """Return the list of available operation/controller modes."""
        return self._hvac_modes

    async def async_set_hvac_mode(self, hvac_mode):
        """Set new target hvac mode."""
        if hvac_mode == HVAC_MODE_OFF:
            result = await self._switchService.async_turn_off_switch(self._device)
        elif hvac_mode == self._supported_hvac_mode:
            result = await self._switchService.async_turn_on_switch(self._device)
        else:
            _LOGGER.warning(
                f"{self._device.deviceId} - {self._device.name} changing hvac to {hvac_mode} failed!"
            )
            return

        if result == ValueChangeResult.FAILED:
            await self.async_refresh_state()
        else:
            self._hvac_mode = hvac_mode

    async def async_refresh_state(self):
        state = await self._switchService.async_get_switch_state(self._device)
        switch_is_on = state.switch_state == SwitchStates.ON
        self._hvac_mode = self._supported_hvac_mode if switch_is_on else HVAC_MODE_OFF


class TapHomeHVACClimateController(TapHomeClimateController):
    def __init__(
        self, multiValueSwitchService: MultiValueSwitchService, device: Device
    ):
        self._multiValueSwitchService = multiValueSwitchService
        self._device = device
        self._hvac_mode = None

    @property
    def hvac_mode(self):
        """Return current operation ie. heat, cool, idle."""
        return self._hvac_mode

    @property
    def hvac_modes(self):
        """Return the list of available operation/controller modes."""
        return [HVAC_MODE_OFF, HVAC_MODE_HEAT, HVAC_MODE_COOL, HVAC_MODE_HEAT_COOL]

    async def async_set_hvac_mode(self, hvac_mode):
        """Set new target hvac mode."""
        taphome_hvac_mode = TapHomeHVACClimateController.hass_to_taphome_hvac(hvac_mode)

        if taphome_hvac_mode is not None:
            result = await self._multiValueSwitchService.async_set_value(
                self._device, taphome_hvac_mode
            )

            if result == ValueChangeResult.FAILED:
                _LOGGER.warning(
                    f"{self._device.deviceId} - {self._device.name} changing hvac to {hvac_mode} failed!"
                )
                await self.async_refresh_state()
            else:
                self._hvac_mode = hvac_mode
        else:
            _LOGGER.warning(
                f"{hvac_mode} is unknown hvac mode for {self._device.deviceId}"
            )

    async def async_refresh_state(self):
        mode_state = (
            await self._multiValueSwitchService.async_get_multi_value_switch_state(
                self._device
            )
        )
        self._hvac_mode = TapHomeHVACClimateController.taphome_to_hass_hvac(
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


class TapHomeClimateControllerFactory:
    def __init__(
        self,
        thermostat: Device,
        controller: TapHomeClimateController,
    ):
        self.thermostat = thermostat
        self.controller = controller

    def create(
        devices: typing.List[Device],
        tapHomeApiService: TapHomeApiService,
        mode_id: typing.Optional[int],
        heat_id: typing.Optional[int],
        cool_id: typing.Optional[int],
    ) -> TapHomeClimateController:
        assert (
            len(
                list(
                    filter(
                        lambda controllerId: controllerId is not None,
                        [mode_id, heat_id, cool_id],
                    )
                )
            )
            <= 1
        )

        if mode_id is not None and mode_id >= 0:
            controller_device = TapHomeClimateControllerFactory.__filter_devices_by_id(
                devices, mode_id
            )
            return TapHomeHVACClimateController(
                MultiValueSwitchService(tapHomeApiService), controller_device
            )
        elif heat_id is not None and heat_id >= 0:
            return TapHomeClimateControllerFactory.__create_switch_controller(
                devices, tapHomeApiService, heat_id, HVAC_MODE_HEAT
            )
        elif cool_id is not None and cool_id >= 0:
            return TapHomeClimateControllerFactory.__create_switch_controller(
                devices, tapHomeApiService, cool_id, HVAC_MODE_COOL
            )
        else:
            return TapHomeNoneClimateController()

    @staticmethod
    def __filter_devices_by_id(devices: typing.List[Device], deviceId: int):
        return next(device for device in devices if device.deviceId == deviceId)

    @staticmethod
    def __create_switch_controller(
        devices: typing.List[Device],
        tapHomeApiService: TapHomeApiService,
        deviceId: int,
        hvac_mode,
    ):
        controller_device = TapHomeClimateControllerFactory.__filter_devices_by_id(
            devices, deviceId
        )
        return TapHomeSwitchClimateController(
            SwitchService(tapHomeApiService), controller_device, hvac_mode
        )