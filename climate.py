"""TapHome climate integration."""

from abc import ABC, abstractmethod
from collections.abc import Generator
from typing import final

from taphome_sdk import (
    AnalogOutputDevice,
    AnalogOutputState,
    DigitalOutputDevice,
    MultiValueSwitchDevice,
    MultiValueSwitchState,
    ObservableValue,
    TapHomeHub,
    ThermostatDevice,
    ThermostatState,
    ValueType,
    enum_from_string_optional,
)

from homeassistant.components.climate import (
    DOMAIN as CLIMATE_DOMAIN,
    ClimateEntity,
    ClimateEntityFeature,
    HVACAction,
    HVACMode,
)
from homeassistant.core import HomeAssistant
from homeassistant.helpers.config_validation import UnitOfTemperature
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .add_entry_request import add_taphome_entities
from .entity import TapHomeEntity
from .taphome_config_entry import AddEntryRequest, TapHomeEntityConfig
from .taphome_data import TapHomeConfigEntry


class TapHomeClimateConfig(TapHomeEntityConfig):
    """Configuration for a TapHome climate device."""

    def __init__(self, device_config: dict) -> None:
        """Initialize config and handle backward compatibility."""
        self._device_config = TapHomeClimateConfig._backwards_compatibility(
            device_config
        )

        if (
            isinstance(device_config, dict)
            and "range_high_thermostat_id" in device_config
        ):
            device_config["id"] = device_config["range_high_thermostat_id"]

        super().__init__(self._device_config)

        self.hvac_switch_id: int | None = self.get_optional("hvac_switch_id", None)
        self.hvac_mode: HVACMode | None = self.get_optional("hvac_mode", None)
        self.hvac_mode_id: int | None = self.get_optional("hvac_mode_id", None)
        self.hvac_action_id: int | None = self.get_optional("hvac_action_id", None)

        self.range_high_thermostat_id: int | None = self.get_optional(
            "range_high_thermostat_id", None
        )
        self.range_low_thermostat_id: int | None = self.get_optional(
            "range_low_thermostat_id", None
        )

        self.preset_mode_id: int | None = self.get_optional("preset_mode_id", None)
        self.fan_mode_id: int | None = self.get_optional("fan_mode_id", None)
        self.swing_mode_id: int | None = self.get_optional("swing_mode_id", None)
        self.swing_horizontal_mode_id: int | None = self.get_optional(
            "swing_horizontal_mode_id", None
        )
        self.target_humidity_id: int | None = self.get_optional(
            "target_humidity_id", None
        )
        self.min_humidity: int | None = self.get_optional("min_humidity", None)
        self.max_humidity: int | None = self.get_optional("max_humidity", None)
        self.precision: float | None = self.get_optional("precision", None)
        self.target_temperature_step: float | None = self.get_optional(
            "target_temperature_step", None
        )

    @staticmethod
    def _backwards_compatibility(config):
        """Translate deprecated config keys to the new format."""
        if isinstance(config, dict):
            if "thermostat" in config:
                config["id"] = config["thermostat"]
            if "heat" in config:
                config["heating_switch_id"] = config["heat"]
            if "cool" in config:
                config["cooling_switch_id"] = config["cool"]
            if "mode" in config:
                config["heating_cooling_mode_id"] = config["mode"]

            if "heating_cooling_mode_id" in config:
                config["hvac_mode_id"] = config["heating_cooling_mode_id"]

            if "heating_switch_id" in config:
                config["hvac_switch_id"] = config["heating_switch_id"]
                config["hvac_mode"] = HVACMode.HEAT

            if "cooling_switch_id" in config:
                config["hvac_switch_id"] = config["cooling_switch_id"]
                config["hvac_mode"] = HVACMode.COOL

        return config


class HvacController(ABC):
    """Representation of a TapHome HVAC controller."""

    def __init__(
        self,
        hub: TapHomeHub,
        hvac_action_id: int | None,
    ) -> None:
        """Initialize a TapHome HVAC controller."""
        self.hvac_action: ObservableValue[HVACAction | None] = ObservableValue(None)
        self.hvac_mode: ObservableValue[HVACMode | None] = ObservableValue(None)
        self.hvac_modes: ObservableValue[list[HVACMode]] = ObservableValue([])

    @abstractmethod
    async def async_set_hvac_mode(self, hvac_mode: HVACMode):
        """Set new target hvac mode."""
        raise NotImplementedError("This method should be overridden in subclasses.")

    MODES_BY_INDEX = {
        0: HVACMode.OFF,
        1: HVACMode.HEAT,
        2: HVACMode.COOL,
        3: HVACMode.HEAT_COOL,
    }
    INDEX_BY_MODE = {v: k for k, v in MODES_BY_INDEX.items()}

    def _map_hvac_modes(self, device: MultiValueSwitchDevice) -> Generator[HVACMode]:
        for value in device.allowed_values:
            mode = (
                self._map_heating_cooling_multivalue_switch_hvac_mode(value.value)
                if self._is_heating_cooling_multivalue_switch(device)
                else enum_from_string_optional(HVACMode, value.name)
            )

            if value.is_enabled and mode is not None:
                yield mode

    def _map_hvac_mode(self, device: MultiValueSwitchDevice) -> HVACMode | None:
        if self._is_heating_cooling_multivalue_switch(device):
            index = device.state.selected_value
            return self._map_heating_cooling_multivalue_switch_hvac_mode(index)
        return enum_from_string_optional(HVACMode, device.selected_option)

    def _map_heating_cooling_multivalue_switch_hvac_mode(
        self, index: int | None
    ) -> HVACMode | None:
        return None if index is None else self.MODES_BY_INDEX.get(index)

    def _map_hvac_mode_to_option(
        self, device: MultiValueSwitchDevice, hvac_mode: HVACMode
    ) -> str | None:
        if self._is_heating_cooling_multivalue_switch(device):
            index = None if hvac_mode is None else self.INDEX_BY_MODE.get(hvac_mode)
            return device.get_option(index)
        return hvac_mode.name.replace("_", " ").lower()

    def _map_hvac_action(self, device: MultiValueSwitchDevice) -> HVACAction | None:
        if self._is_heating_cooling_multivalue_switch(device):
            index = device.state.selected_value
            if index is None:
                return None

            modes = {
                0: HVACAction.OFF,
                1: HVACAction.HEATING,
                2: HVACAction.COOLING,
            }
            return modes.get(index)
        return enum_from_string_optional(HVACAction, device.selected_option)

    def _is_heating_cooling_multivalue_switch(self, device):
        return device.usage == "HeatingCooling"


class SwitchHvacControllerBase(HvacController, ABC):
    """Representation of a TapHome HVAC controller."""

    _hvac_action_device: MultiValueSwitchDevice | None = None

    def __init__(
        self,
        hub: TapHomeHub,
        hvac_switch_id: int,
        hvac_action_id: int | None,
    ) -> None:
        """Initialize a TapHome switch HVAC controller."""
        super().__init__(hub, hvac_action_id)

        self._set_hvac_modes()
        self._hvac_switch_device = hub.get_typed_device(
            hvac_switch_id, DigitalOutputDevice
        )
        self._hvac_switch_device.state.changed.subscribe(self._on_hvac_can_changed)

        if hvac_action_id is not None:
            self._hvac_action_device = hub.get_typed_device(
                hvac_action_id, MultiValueSwitchDevice
            )
            self._hvac_action_device.state.changed.subscribe(self._on_hvac_can_changed)

    @abstractmethod
    def _hvac_mode_when_on(self) -> HVACMode | None:
        """Return the HVAC mode when the switch is on."""
        raise NotImplementedError("This method should be overridden in subclasses.")

    async def async_set_hvac_mode(self, hvac_mode: HVACMode):
        """Set new target hvac mode."""
        if hvac_mode == HVACMode.OFF:
            await self._hvac_switch_device.async_turn_off()
        elif hvac_mode == self._hvac_mode_when_on():
            await self._hvac_switch_device.async_turn_on()
        else:
            raise ValueError("Invalid HVAC mode")

    def _set_hvac_modes(self):
        mode = self._hvac_mode_when_on()
        if mode is not None and mode != HVACMode.OFF:
            self.hvac_modes.value = [HVACMode.OFF, mode]
        else:
            self.hvac_modes.value = []

    def _on_hvac_can_changed(self, _, __) -> None:
        """Handle HVAC switch state changes."""
        if self._hvac_switch_device.state.is_on:
            self.hvac_mode.value = self._hvac_mode_when_on()
            self.hvac_action.value = self._get_hvac_action(True)
        else:
            self.hvac_mode.value = HVACMode.OFF
            self.hvac_action.value = self._get_hvac_action(False)

    def _get_hvac_action(self, is_on: bool) -> HVACAction | None:
        if self._hvac_action_device is None:
            return None
        if is_on:
            return self._map_hvac_action(self._hvac_action_device)
        return HVACAction.OFF


class StaticSwitchHvacController(SwitchHvacControllerBase):
    """Representation of a TapHome static switch HVAC controller."""

    def __init__(
        self,
        hub: TapHomeHub,
        hvac_switch_id: int,
        hvac_mode: HVACMode,
        hvac_action_id: int | None,
    ) -> None:
        """Initialize a TapHome switch HVAC controller."""
        self._mode = hvac_mode
        super().__init__(hub, hvac_switch_id, hvac_action_id)

    def _hvac_mode_when_on(self) -> HVACMode | None:
        """Return the HVAC mode when the switch is on."""
        return self._mode


class DynamicSwitchHvacController(SwitchHvacControllerBase):
    """Representation of a TapHome dynamic switch HVAC controller."""

    def __init__(
        self,
        hub: TapHomeHub,
        hvac_switch_id: int,
        hvac_mode_id: int,
        hvac_action_id: int | None,
    ) -> None:
        """Initialize a TapHome switch HVAC controller."""
        self._hvac_mode_device = hub.get_typed_device(
            hvac_mode_id, MultiValueSwitchDevice
        )

        super().__init__(hub, hvac_switch_id, hvac_action_id)
        self._hvac_mode_device.state.changed += self._on__hvac_mode_changed
        self._hvac_mode_device.state.changed.subscribe(self._on_hvac_can_changed)

    def _hvac_mode_when_on(self) -> HVACMode | None:
        """Return the HVAC mode when the switch is on."""
        return self._map_hvac_mode(self._hvac_mode_device)

    def _on__hvac_mode_changed(self, _, __) -> None:
        """Handle HVAC mode changes."""
        self._set_hvac_modes()


class EmptyHvacController(HvacController):
    """Representation of a TapHome valve HVAC controller."""

    def __init__(
        self,
        hub: TapHomeHub,
        hvac_action_id: int | None,
    ) -> None:
        """Initialize a TapHome mode HVAC controller."""
        super().__init__(hub, hvac_action_id)

        self.hvac_modes.value = []
        self.hvac_mode.value = None

        if hvac_action_id is not None:
            self._hvac_action_device = hub.get_typed_device(
                hvac_action_id, MultiValueSwitchDevice
            )
            self._hvac_action_device.state.changed += self.__hvac_action_device_changed

    def __hvac_action_device_changed(
        self,
        _: MultiValueSwitchState | None,
        new_state: MultiValueSwitchState,
    ):
        """Handle changes in the HVAC action device state."""
        self.hvac_action.value = self._map_hvac_action(self._hvac_action_device)

    async def async_set_hvac_mode(self, hvac_mode: HVACMode):
        """Set new target hvac mode."""
        raise NotImplementedError("HVAC mode control is not supported for this device")


class ModeHvacController(EmptyHvacController):
    """Representation of a TapHome valve HVAC controller."""

    def __init__(
        self,
        hub: TapHomeHub,
        hvac_mode_id: int,
        hvac_action_id: int | None,
    ) -> None:
        """Initialize a TapHome mode HVAC controller."""
        super().__init__(hub, hvac_action_id)
        self._hvac_mode_device = hub.get_typed_device(
            hvac_mode_id, MultiValueSwitchDevice
        )
        self.hvac_modes.value = list(self._map_hvac_modes(self._hvac_mode_device))
        self._hvac_mode_device.state.changed += self._on_hvac_mode_changed

    def _on_hvac_mode_changed(
        self,
        old_state: MultiValueSwitchState | None,
        new_state: MultiValueSwitchState,
    ):
        """Handle changes in the HVAC mode device state."""
        self.hvac_mode.value = self._map_hvac_mode(self._hvac_mode_device)

    async def async_set_hvac_mode(self, hvac_mode: HVACMode):
        """Set new target hvac mode."""

        hvac_mode_option = self._map_hvac_mode_to_option(
            self._hvac_mode_device, hvac_mode
        )
        if hvac_mode_option is not None:
            await self._hvac_mode_device.async_select_option(hvac_mode_option)


def create_hvac_controller(
    hub: TapHomeHub,
    thermostat_id: int,
    hvac_switch_id: int | None,
    hvac_mode: HVACMode | None,
    hvac_mode_id: int | None = None,
    hvac_action_id: int | None = None,
) -> HvacController:
    """Create a new TapHome HVAC controller."""
    if hvac_switch_id is not None and hvac_mode_id is not None and hvac_mode is None:
        return DynamicSwitchHvacController(
            hub,
            hvac_switch_id,
            hvac_mode_id,
            hvac_action_id,
        )

    if hvac_switch_id is not None and hvac_mode_id is None and hvac_mode is not None:
        return StaticSwitchHvacController(
            hub,
            hvac_switch_id,
            hvac_mode,
            hvac_action_id,
        )

    if hvac_switch_id is None and hvac_mode_id is not None and hvac_mode is None:
        return ModeHvacController(
            hub,
            hvac_mode_id,
            hvac_action_id,
        )

    if hvac_switch_id is None and hvac_mode_id is None and hvac_mode is None:
        return EmptyHvacController(
            hub,
            hvac_action_id,
        )

    raise ValueError(f"Invalid HVAC configuration for {thermostat_id}")


class TapHomeClimateBase(TapHomeEntity, ClimateEntity, ABC):
    """Representation of a TapHome climate entity."""

    def __init__(
        self,
        config: AddEntryRequest[TapHomeClimateConfig],
    ) -> None:
        """Initialize TapHome climate entity."""
        self._attr_temperature_unit = UnitOfTemperature.CELSIUS

        thermostat = config.hub.get_typed_device(config.entity.id, ThermostatDevice)
        self._subscribe(thermostat.state.changed, self._on_thermostat_state_change)

        if config.entity.precision is not None:
            self._attr_precision = config.entity.precision

        self._attr_target_temperature_step = config.entity.target_temperature_step

        set_point = thermostat.supported_values[ValueType.TEMPERATURE_SET_POINT]
        if set_point.min_value is not None:
            self._attr_min_temp = set_point.min_value
        if set_point.max_value is not None:
            self._attr_max_temp = set_point.max_value

        self._attr_supported_features |= (
            ClimateEntityFeature.TURN_ON | ClimateEntityFeature.TURN_OFF
        )

        self.hvac_controller = create_hvac_controller(
            config.hub,
            config.entity.id,
            config.entity.hvac_switch_id,
            config.entity.hvac_mode,
            config.entity.hvac_mode_id,
            config.entity.hvac_action_id,
        )
        self._subscribe(
            self.hvac_controller.hvac_action.changed, self._on_hvac_action_changed
        )
        self._subscribe(
            self.hvac_controller.hvac_mode.changed, self._on_hvac_mode_changed
        )
        self._subscribe(
            self.hvac_controller.hvac_modes.changed, self._on_hvac_modes_changed
        )

        if config.entity.preset_mode_id:
            self._preset_mode_device = config.hub.get_typed_device(
                config.entity.preset_mode_id, MultiValueSwitchDevice
            )
            self._attr_supported_features |= ClimateEntityFeature.PRESET_MODE
            self._attr_preset_modes = self._preset_mode_device.options
            self._subscribe(
                self._preset_mode_device.state.changed, self._on_preset_mode_change
            )
            self._schedule_update_when_changed(self._preset_mode_device)

        if config.entity.fan_mode_id:
            self._fan_mode_device = config.hub.get_typed_device(
                config.entity.fan_mode_id, MultiValueSwitchDevice
            )
            self._attr_supported_features |= ClimateEntityFeature.FAN_MODE
            self._attr_fan_modes = self._fan_mode_device.options
            self._subscribe(
                self._fan_mode_device.state.changed, self._on_fan_mode_change
            )
            self._schedule_update_when_changed(self._fan_mode_device)

        if config.entity.swing_mode_id:
            self._swing_mode_device = config.hub.get_typed_device(
                config.entity.swing_mode_id, MultiValueSwitchDevice
            )
            self._attr_supported_features |= ClimateEntityFeature.SWING_MODE
            self._attr_swing_modes = self._swing_mode_device.options
            self._subscribe(
                self._swing_mode_device.state.changed, self._on_swing_mode_change
            )
            self._schedule_update_when_changed(self._swing_mode_device)

        if config.entity.swing_horizontal_mode_id:
            self._swing_horizontal_mode_device = config.hub.get_typed_device(
                config.entity.swing_horizontal_mode_id, MultiValueSwitchDevice
            )
            self._attr_supported_features |= ClimateEntityFeature.SWING_HORIZONTAL_MODE
            self._attr_swing_horizontal_modes = (
                self._swing_horizontal_mode_device.options
            )
            self._subscribe(
                self._swing_horizontal_mode_device.state.changed,
                self._on_swing_horizontal_mode_change,
            )
            self._schedule_update_when_changed(self._swing_horizontal_mode_device)

        if config.entity.target_humidity_id:
            if config.entity.min_humidity is not None:
                self._attr_min_humidity = config.entity.min_humidity
            if config.entity.max_humidity is not None:
                self._attr_max_humidity = config.entity.max_humidity
            self._attr_supported_features |= ClimateEntityFeature.TARGET_HUMIDITY

            self._target_humidity_device = config.hub.get_typed_device(
                config.entity.target_humidity_id, AnalogOutputDevice
            )
            self._subscribe(
                self._target_humidity_device.state.changed,
                self._on_target_humidity_change,
            )
            self._schedule_update_when_changed(self._target_humidity_device)

        super().__init__(config, thermostat, CLIMATE_DOMAIN)

    def _on_hvac_action_changed(self, _, hvac_action: HVACAction | None) -> None:
        self._attr_hvac_action = hvac_action
        self.schedule_update_ha_state()

    def _on_hvac_mode_changed(self, _, hvac_mode: HVACMode | None) -> None:
        self._attr_hvac_mode = hvac_mode
        self.schedule_update_ha_state()

    def _on_hvac_modes_changed(self, _, hvac_modes: list[HVACMode]) -> None:
        self._attr_hvac_modes = hvac_modes
        self.schedule_update_ha_state()

    def _on_preset_mode_change(
        self, _: MultiValueSwitchState | None, current_state: MultiValueSwitchState
    ) -> None:
        self._attr_preset_mode = self._preset_mode_device.selected_option

    async def async_set_preset_mode(self, preset_mode: str) -> None:
        """Set new preset mode."""
        await self._preset_mode_device.async_select_option(preset_mode)

    def _on_fan_mode_change(
        self, _: MultiValueSwitchState | None, current_state: MultiValueSwitchState
    ) -> None:
        self._attr_fan_mode = self._fan_mode_device.selected_option

    async def async_set_fan_mode(self, fan_mode: str) -> None:
        """Set new target fan mode."""
        await self._fan_mode_device.async_select_option(fan_mode)

    def _on_swing_mode_change(
        self, _: MultiValueSwitchState | None, current_state: MultiValueSwitchState
    ) -> None:
        self._attr_swing_mode = self._swing_mode_device.selected_option

    async def async_set_swing_mode(self, swing_mode: str) -> None:
        """Set new target swing mode."""
        await self._swing_mode_device.async_select_option(swing_mode)

    def _on_swing_horizontal_mode_change(
        self, _: MultiValueSwitchState | None, current_state: MultiValueSwitchState
    ) -> None:
        self._attr_swing_horizontal_mode = (
            self._swing_horizontal_mode_device.selected_option
        )

    async def async_set_swing_horizontal_mode(self, swing_horizontal_mode: str) -> None:
        """Set new target horizontal swing mode."""
        await self._swing_horizontal_mode_device.async_select_option(
            swing_horizontal_mode
        )

    def _on_target_humidity_change(
        self, _: AnalogOutputState | None, current_state: AnalogOutputState
    ) -> None:
        self._attr_target_humidity = TapHomeEntity.convert_th_percentage_to_ha(
            current_state.output_value
        )

    async def async_set_humidity(self, humidity: int) -> None:
        """Set new target humidity."""
        await self._target_humidity_device.async_set_output_value(
            self.convert_ha_percentage_to_th(humidity)
        )

    @final
    def _on_thermostat_state_change(
        self, _: ThermostatState | None, current_state: ThermostatState
    ) -> None:
        self._attr_current_temperature = current_state.temperature
        self._attr_current_humidity = TapHomeEntity.convert_th_percentage_to_ha(
            current_state.humidity
        )

    async def async_set_hvac_mode(self, hvac_mode: HVACMode):
        """Set new target hvac mode."""
        await self.hvac_controller.async_set_hvac_mode(hvac_mode)


class TapHomeClimate(TapHomeClimateBase):
    """Representation of a TapHome climate entity."""

    def __init__(
        self,
        config: AddEntryRequest[TapHomeClimateConfig],
    ) -> None:
        """Initialize TapHome climate entity."""
        self._attr_supported_features |= ClimateEntityFeature.TARGET_TEMPERATURE
        self.thermostat = config.hub.get_typed_device(
            config.entity.id, ThermostatDevice
        )
        self._subscribe(
            self.thermostat.state.changed, self._on_target_thermostat_change
        )
        super().__init__(config)

    def _on_target_thermostat_change(
        self, _: ThermostatState | None, current_state: ThermostatState
    ) -> None:
        self._attr_target_temperature = current_state.desired_temperature

    async def async_set_temperature(self, *, temperature: float, **kwargs):
        """Set new target temperature."""
        await self.thermostat.async_set_desired_temperature(temperature)


class TapHomeRangeClimate(TapHomeClimateBase):
    """Representation of a TapHome range climate entity."""

    def __init__(
        self,
        config: AddEntryRequest[TapHomeClimateConfig],
    ) -> None:
        """Initialize TapHome range climate entity."""
        self._attr_supported_features |= ClimateEntityFeature.TARGET_TEMPERATURE_RANGE
        if (
            not config.entity.range_low_thermostat_id
            or not config.entity.range_high_thermostat_id
        ):
            raise ValueError(
                "Both range_low_thermostat_id and range_high_thermostat_id must be set for TapHomeRangeClimate."
            )

        self.high_thermostat = config.hub.get_typed_device(
            config.entity.range_high_thermostat_id, ThermostatDevice
        )
        self._subscribe(
            self.high_thermostat.state.changed, self._on_high_temperature_change
        )

        self.low_thermostat = config.hub.get_typed_device(
            config.entity.range_low_thermostat_id, ThermostatDevice
        )
        self._subscribe(
            self.low_thermostat.state.changed, self._on_low_temperature_change
        )

        super().__init__(config)

    def _on_high_temperature_change(
        self, _: ThermostatState | None, current_state: ThermostatState
    ) -> None:
        self._attr_target_temperature_high = current_state.desired_temperature

    def _on_low_temperature_change(
        self, _: ThermostatState | None, current_state: ThermostatState
    ) -> None:
        self._attr_target_temperature_low = current_state.desired_temperature

    async def async_set_temperature(
        self, *, target_temp_low: float, target_temp_high: float, **kwargs
    ):
        """Set new target temperature."""
        await self.low_thermostat.async_set_desired_temperature(target_temp_low)
        await self.high_thermostat.async_set_desired_temperature(target_temp_high)


def _create_climate_entity(
    config: AddEntryRequest[TapHomeClimateConfig],
) -> TapHomeClimateBase:
    """Create TapHome climate entity."""
    if config.entity.range_high_thermostat_id and config.entity.range_low_thermostat_id:
        return TapHomeRangeClimate(config)
    if (
        config.entity.range_high_thermostat_id is None
        and config.entity.range_low_thermostat_id is None
    ):
        return TapHomeClimate(config)
    raise ValueError(
        "Invalid configuration for TapHome climate entity. "
        "Both range_high_thermostat_id and range_low_thermostat_id must be set or both must be None."
    )


async def async_setup_entry(
    hass: HomeAssistant,
    entry: TapHomeConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up TapHome climates from a config entry."""
    add_taphome_entities(
        entry, async_add_entities, CLIMATE_DOMAIN, _create_climate_entity
    )
