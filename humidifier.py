"""TapHome humidifier integration."""

from __future__ import annotations

from typing import Any

from homeassistant.components.humidifier import (
    DOMAIN as HUMIDIFIER_DOMAIN,
    HumidifierAction,
    HumidifierDeviceClass,
    HumidifierEntity,
    HumidifierEntityFeature,
)
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import (
    AddEntitiesCallback,
    ConfigType,
    DiscoveryInfoType,
)

from .add_entry_request import add_taphome_entities
from .const import CONF_HUMIDIFIER
from .taphome_config_entry import AddEntryRequest, TapHomeEntityConfig
from .taphome_entity import TapHomeEntity
from .taphome_sdk import (
    Device,
    DeviceState,
    DigitalOutputDevice,
    DigitalOutputState,
    GenericOutputAdapter,
    GenericOutputState,
    MultiValueSwitchDevice,
    MultiValueSwitchState,
    ValueType,
    enum_from_string,
)


class TapHomeHumidifierConfig(TapHomeEntityConfig):
    """Configuration for a TapHome humidifier device."""

    def __init__(self, device_config: dict) -> None:
        """Store config and extract humidity limits."""
        super().__init__(device_config)
        self.switch_id: int | None = self.get_optional("switch_id", None)
        self.action_id: int | None = self.get_optional("action_id", None)
        self.mode_id: int | None = self.get_optional("mode_id", None)
        self.humidity_sensor_id: int | None = self.get_optional(
            "humidity_sensor_id", None
        )
        self.min_humidity: int = self.get_optional("min_humidity", 0)
        self.max_humidity: int = self.get_optional("max_humidity", 100)
        self.device_class: HumidifierDeviceClass | None = self.get_optional(
            "device_class", None
        )


class TapHomeHumidifier(TapHomeEntity, HumidifierEntity):
    """Representation of a demo humidifier device."""

    _switch_device: DigitalOutputDevice | None = None

    def __init__(
        self,
        config: AddEntryRequest[TapHomeHumidifierConfig],
    ) -> None:
        """Initialize TapHome humidifier entity."""
        self._attr_supported_features = HumidifierEntityFeature(0)
        self._attr_min_humidity = config.entity.min_humidity
        self._attr_max_humidity = config.entity.max_humidity
        self._attr_device_class = config.entity.device_class

        self._humidifier_device = config.hub.get_generic_output_capable_device(
            config.entity.id
        )

        if config.entity.switch_id:
            self._switch_device = config.hub.get_typed_device(
                config.entity.switch_id, DigitalOutputDevice
            )
            self._switch_device.state.changed += self._switch_change
            self._schedule_update_when_changed(self._switch_device)

        if config.entity.humidity_sensor_id:
            self._humidity_sensor = config.hub.get_typed_device(
                config.entity.humidity_sensor_id, Device
            )
            self._humidity_sensor.state.changed += self._on_humidity_change
            self._schedule_update_when_changed(self._humidity_sensor)

        if config.entity.action_id:
            self._action_device = config.hub.get_typed_device(
                config.entity.action_id, MultiValueSwitchDevice
            )
            self._action_device.state.changed += self._on_action_change
            self._schedule_update_when_changed(self._action_device)

        if config.entity.mode_id:
            self._mode_device = config.hub.get_typed_device(
                config.entity.mode_id, MultiValueSwitchDevice
            )
            self._attr_supported_features |= HumidifierEntityFeature.MODES
            self._attr_available_modes = self._mode_device.options
            self._mode_device.state.changed += self._on_mode_change
            self._schedule_update_when_changed(self._mode_device)

        self._humidifier_generic_output = GenericOutputAdapter(self._humidifier_device)
        self._humidifier_generic_output.state_changed += (
            self._on_humidifier_state_change
        )

        super().__init__(config, self._humidifier_device, HUMIDIFIER_DOMAIN)

    def _on_humidity_change(
        self, _: DeviceState | None, current_state: DeviceState
    ) -> None:
        """Handle humidity sensor state change event."""
        self._attr_current_humidity = self.convert_th_percentage_to_ha(
            current_state.get_device_value(ValueType.HUMIDITY)
        )

    def _switch_change(
        self, _: DigitalOutputState | None, current_state: DigitalOutputState
    ) -> None:
        self._attr_is_on = current_state.is_on

    def _on_humidifier_state_change(
        self, _: GenericOutputState | None, current_state: GenericOutputState
    ) -> None:
        """Handle humidifier state change event."""
        if self._switch_device is None:
            self._attr_is_on = current_state.is_on
        self._attr_target_humidity = self.convert_th_percentage_to_ha(
            current_state.output_value
        )

    def _on_action_change(
        self,
        _: MultiValueSwitchState | None,
        current_state: MultiValueSwitchState,
    ) -> None:
        self._attr_action = (
            None
            if self._action_device.selected_option is None
            else enum_from_string(HumidifierAction, self._action_device.selected_option)
        )

    def _on_mode_change(
        self,
        _: MultiValueSwitchState | None,
        current_state: MultiValueSwitchState,
    ) -> None:
        self._attr_mode = self._mode_device.selected_option

    async def async_turn_on(self, **kwargs: Any) -> None:
        """Turn the device on."""
        if self._switch_device is not None:
            await self._switch_device.async_turn_on()
        else:
            await self._humidifier_generic_output.async_turn_on()

    async def async_turn_off(self, **kwargs: Any) -> None:
        """Turn the device off."""
        if self._switch_device is None:
            await self._humidifier_generic_output.async_turn_off()
        else:
            await self._switch_device.async_turn_off()

    async def async_set_humidity(self, humidity: int) -> None:
        """Set new humidity level."""
        if self._switch_device is not None:
            await self._switch_device.async_turn_on()
        await self._humidifier_generic_output.async_set_output_value(
            self.convert_ha_percentage_to_th(humidity)
        )

    async def async_set_mode(self, mode):
        """Set new target preset mode."""
        if self._mode_device is not None:
            await self._mode_device.async_select_option(mode)


def setup_platform(
    hass: HomeAssistant,
    config: ConfigType,
    add_entities: AddEntitiesCallback,
    discovery_info: DiscoveryInfoType | None = None,
) -> None:
    """Set up the humidifier platform."""
    add_taphome_entities(hass, add_entities, CONF_HUMIDIFIER, TapHomeHumidifier)
