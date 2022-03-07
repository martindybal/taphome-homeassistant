"""TapHome climate integration."""
import logging
import typing

from homeassistant.components.climate import ClimateEntity
from homeassistant.components.climate.const import (
    DOMAIN,
    HVAC_MODE_COOL,
    HVAC_MODE_HEAT,
    HVAC_MODE_HEAT_COOL,
    HVAC_MODE_OFF,
    SUPPORT_TARGET_TEMPERATURE,
)
from homeassistant.const import ATTR_TEMPERATURE, TEMP_CELSIUS
from homeassistant.core import CALLBACK_TYPE, HomeAssistant

from .add_entry_request import AddEntryRequest
from .const import CONF_CLIMATES, TAPHOME_PLATFORM
from .coordinator import TapHomeDataUpdateCoordinator
from .taphome_entity import *
from .taphome_sdk import *

_LOGGER = logging.getLogger(__name__)


class TapHomeClimateController:
    def __init__(self) -> None:
        self._listeners: list[CALLBACK_TYPE] = []

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

    @callback
    def add_hvac_mode_changed_listener(
        self, update_callback: CALLBACK_TYPE
    ) -> typing.Callable[[], None]:
        """Listen for data updates."""
        self._listeners.append(update_callback)

    def _invoke_hvac_mode_changed(self) -> None:
        for update_callback in self._listeners:
            update_callback()


class TapHomeNoneClimateController(TapHomeClimateController):
    def __init__(self) -> None:
        super().__init__()

    @property
    def hvac_mode(self):
        return None

    @property
    def hvac_modes(self):
        return []

    async def async_set_hvac_mode(self, hvac_mode):
        pass


class TapHomeCoordinatorObjectClimateController(
    TapHomeClimateController, TapHomeDataUpdateCoordinatorObject[TState]
):
    def __init__(
        self,
        taphome_device_id: int,
        taphome_state_type,
        coordinator: TapHomeDataUpdateCoordinator,
    ) -> None:
        TapHomeClimateController.__init__(self)
        TapHomeDataUpdateCoordinatorObject.__init__(
            self, taphome_device_id, coordinator, taphome_state_type
        )
        self.coordinator = coordinator

    @callback
    def handle_taphome_state_change(self) -> None:
        self._invoke_hvac_mode_changed()


class TapHomeSwitchClimateController(
    TapHomeCoordinatorObjectClimateController[SwitchState]
):
    def __init__(
        self,
        taphome_device_id: int,
        on_hvac_mode,
        tapHome_api_service: TapHomeApiService,
        coordinator: TapHomeDataUpdateCoordinator,
    ) -> None:
        super().__init__(taphome_device_id, SwitchState, coordinator)
        self.switch_service = SwitchService(tapHome_api_service)
        self.on_hvac_mode = on_hvac_mode

    @property
    def hvac_mode(self):
        if not self.taphome_state is None:
            if self.taphome_state.switch_state == SwitchStates.ON:
                return self.on_hvac_mode
            else:
                return HVAC_MODE_OFF

    @property
    def hvac_modes(self):
        return [HVAC_MODE_OFF, self.on_hvac_mode]

    async def async_set_hvac_mode(self, hvac_mode):
        switch_state: SwitchStates
        if hvac_mode == HVAC_MODE_OFF:
            switch_state = SwitchStates.OFF
        elif hvac_mode == self.on_hvac_mode:
            switch_state = SwitchStates.ON
        else:
            raise Exception(f"Unknown hvac mode: {hvac_mode}")

        async with UpdateTapHomeState(self) as state:
            await self.switch_service.async_turn(switch_state, self.taphome_device)
            state.switch_state = switch_state


class TapHomeModeClimateController(
    TapHomeCoordinatorObjectClimateController[MultiValueSwitchState]
):
    def __init__(
        self,
        taphome_device_id: int,
        tapHome_api_service: TapHomeApiService,
        coordinator: TapHomeDataUpdateCoordinator,
    ) -> None:
        super().__init__(taphome_device_id, MultiValueSwitchState, coordinator)
        self.multi_value_switch_service = MultiValueSwitchService(tapHome_api_service)

    @property
    def hvac_modes(self):
        return [HVAC_MODE_OFF, HVAC_MODE_HEAT, HVAC_MODE_COOL, HVAC_MODE_HEAT_COOL]

    @property
    def hvac_mode(self):
        if not self.taphome_state is None:
            modes = {
                0: HVAC_MODE_OFF,
                1: HVAC_MODE_HEAT,
                2: HVAC_MODE_COOL,
                3: HVAC_MODE_HEAT_COOL,
            }
            return modes.get(self.taphome_state.multi_value_switch_state, None)

    async def async_set_hvac_mode(self, hvac_mode):
        modes = {
            HVAC_MODE_OFF: 0,
            HVAC_MODE_HEAT: 1,
            HVAC_MODE_COOL: 2,
            HVAC_MODE_HEAT_COOL: 3,
        }
        multi_value_switch_state = modes.get(hvac_mode, None)

        async with UpdateTapHomeState(self) as state:
            await self.multi_value_switch_service.async_set_value(
                multi_value_switch_state, self.taphome_device
            )
            state.multi_value_switch_state = multi_value_switch_state


class ClimateConfigEntry(TapHomeConfigEntry):
    def __init__(self, device_config: dict):
        self._device_config = ClimateConfigEntry._backwards_compatibility(device_config)
        super().__init__(self._device_config)

        self._min_temperature = self.get_optional("min_temperature", None)
        self._max_temperature = self.get_optional("max_temperature", None)

    @property
    def min_temperature(self):
        return self._min_temperature

    @property
    def max_temperature(self):
        return self._max_temperature

    def create_climate_controller(
        self,
        tapHome_api_service: TapHomeApiService,
        coordinator: TapHomeDataUpdateCoordinator,
    ) -> TapHomeClimateController:
        if isinstance(self._device_config, dict):
            if "heating_switch_id" in self._device_config:
                return TapHomeSwitchClimateController(
                    self._device_config["heating_switch_id"],
                    HVAC_MODE_HEAT,
                    tapHome_api_service,
                    coordinator,
                )
            if "cooling_switch_id" in self._device_config:
                return TapHomeSwitchClimateController(
                    self._device_config["cooling_switch_id"],
                    HVAC_MODE_COOL,
                    tapHome_api_service,
                    coordinator,
                )
            if "heating_cooling_mode_id" in self._device_config:
                return TapHomeModeClimateController(
                    self._device_config["heating_cooling_mode_id"],
                    tapHome_api_service,
                    coordinator,
                )

        return TapHomeNoneClimateController()

    @staticmethod
    def _backwards_compatibility(device_config):
        if isinstance(device_config, dict):
            if "thermostat" in device_config:
                device_config["id"] = device_config["thermostat"]
            if "heat" in device_config:
                device_config["heating_switch_id"] = device_config["heat"]
            if "cool" in device_config:
                device_config["cooling_switch_id"] = device_config["cool"]
            if "mode" in device_config:
                device_config["heating_cooling_mode_id"] = device_config["mode"]

        return device_config


class TapHomeClimate(TapHomeEntity[ThermostatState], ClimateEntity):
    """Representation of an climate"""

    def __init__(
        self,
        core_config: TapHomeCoreConfigEntry,
        config_entry: ClimateConfigEntry,
        tapHome_api_service: TapHomeApiService,
        coordinator: TapHomeDataUpdateCoordinator,
    ):
        super().__init__(
            core_config, config_entry, DOMAIN, coordinator, ThermostatState
        )

        self.thermostat_service = ThermostatService(tapHome_api_service)
        self.climate_controller = config_entry.create_climate_controller(
            tapHome_api_service, coordinator
        )
        self.climate_controller.add_hvac_mode_changed_listener(
            self.handle_taphome_state_change
        )

        self._config_min_temperature = config_entry.min_temperature
        self._config_max_temperature = config_entry.max_temperature

        self._supported_features = SUPPORT_TARGET_TEMPERATURE

    @property
    def supported_features(self):
        return self._supported_features

    @property
    def temperature_unit(self):
        return TEMP_CELSIUS

    @property
    def target_temperature(self):
        if self.taphome_state is not None:
            return self.taphome_state.desired_temperature

    @property
    def current_temperature(self):
        if self.taphome_state is not None:
            return self.taphome_state.real_temperature

    @property
    def min_temp(self):
        if self._config_min_temperature is not None:
            return self._config_min_temperature

        if (
            self.taphome_state is not None
            and self.taphome_state.min_temperature is not None
        ):
            return self.taphome_state.min_temperature

        return 10

    @property
    def max_temp(self):
        if self._config_max_temperature is not None:
            return self._config_max_temperature

        if (
            self.taphome_state is not None
            and self.taphome_state.max_temperature is not None
        ):
            return self.taphome_state.max_temperature

        return 30

    @property
    def hvac_modes(self):
        """Return the list of available operation/controller modes."""
        return self.climate_controller.hvac_modes

    @property
    def hvac_mode(self):
        """Return the list of available operation/controller modes."""
        return self.climate_controller.hvac_mode

    async def async_set_temperature(self, **kwargs):
        new_target_temperature = kwargs.get(ATTR_TEMPERATURE)

        async with UpdateTapHomeState(self) as state:
            await self.thermostat_service.async_set_desired_temperature(
                self.taphome_device, new_target_temperature
            )
            state.desired_temperature = new_target_temperature

    async def async_set_hvac_mode(self, hvac_mode):
        """Set new target hvac mode."""
        await self.climate_controller.async_set_hvac_mode(hvac_mode)


def setup_platform(
    hass: HomeAssistant,
    config,
    add_entities,
    discovery_info=None,
) -> None:
    """Set up the climate platform."""
    add_entry_requests: typing.List[AddEntryRequest] = hass.data[TAPHOME_PLATFORM][
        CONF_CLIMATES
    ]
    climates = []
    for add_entry_request in add_entry_requests:
        climate = TapHomeClimate(
            add_entry_request.core_config,
            add_entry_request.config_entry,
            add_entry_request.tapHome_api_service,
            add_entry_request.coordinator,
        )
        climates.append(climate)

    add_entities(climates)
