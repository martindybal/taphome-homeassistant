"""TapHome humidifier integration."""
from __future__ import annotations

from typing import Any, Optional

from homeassistant.components.humidifier import (
    DOMAIN,
    HumidifierDeviceClass,
    HumidifierEntity,
)
from homeassistant.components.humidifier.const import HumidifierAction
from homeassistant.core import HomeAssistant

from .add_entry_request import AddEntryRequest
from .const import CONF_HUMIDIFIER, TAPHOME_PLATFORM
from .coordinator import *
from .taphome_entity import *
from .taphome_sdk import *


class HumidifierConfigEntry(TapHomeConfigEntry):
    def __init__(self, device_config: dict):
        super().__init__(device_config)

        self.min_humidity = self.get_optional("min_humidity", None)
        self.max_humidity = self.get_optional("max_humidity", None)


# Je potřeba dořešit
# - On off pomocí přepínače -> v configu bude switch id
# - Čtení current humidity z jiného senzoru -> config id
class TapHomeHumidifier(TapHomeEntity[HumidifierState], HumidifierEntity):
    """Representation of a demo humidifier device."""

    def __init__(
        self,
        hass: HomeAssistant,
        core_config: TapHomeCoreConfigEntry,
        config_entry: HumidifierConfigEntry,
        coordinator: TapHomeDataUpdateCoordinator,
        humidifier_service: HumidifierService,
    ):
        super().__init__(
            hass, core_config, config_entry, DOMAIN, coordinator, HumidifierState
        )
        self.config = config_entry
        self._attr_action = HumidifierAction.HUMIDIFYING
        self.humidifier_service = humidifier_service
        # self._attr_device_class = HumidifierDeviceClass.HUMIDIFIER

    @property
    def is_on(self):
        """Returns if the device is on or not."""
        if not self.taphome_state is None:
            return self.taphome_state.switch_state == SwitchStates.ON

    @property
    def target_humidity(self) -> int | None:
        """Returns if the device is on or not."""
        if not self.taphome_state is None:
            return TapHomeEntity.convert_taphome_percentage_to_ha(
                self.taphome_state.humidity
            )

    @property
    def current_humidity(self) -> int | None:
        """Returns if the device is on or not."""
        if not self.taphome_state is None:
            return TapHomeEntity.convert_taphome_percentage_to_ha(
                self.taphome_state.humidity
            )

    @property
    def min_humidity(self) -> int | None:
        """Returns if the device is on or not."""

        if self.config.min_humidity is not None:
            return self.config.min_humidity

        if not self.taphome_device is None:
            return TapHomeEntity.convert_taphome_percentage_to_ha(
                self.taphome_device.supported_values[
                    ValueType.AnalogOutputDesiredValue
                ].min_value
            )

    @property
    def max_humidity(self) -> int | None:
        """Returns if the device is on or not."""
        if self.config.max_humidity is not None:
            return self.config.max_humidity

        if not self.taphome_device is None:
            return TapHomeEntity.convert_taphome_percentage_to_ha(
                self.taphome_device.supported_values[
                    ValueType.AnalogOutputDesiredValue
                ].max_value
            )

    async def async_turn_on(self, **kwargs: Any) -> None:
        """Turn the device on."""
        async with UpdateTapHomeState(self) as state:
            await self.humidifier_service.async_turn_on(self.taphome_device)
            state.switch_state = SwitchStates.ON

    async def async_turn_off(self, **kwargs: Any) -> None:
        """Turn the device off."""
        async with UpdateTapHomeState(self) as state:
            await self.humidifier_service.async_turn_off(self.taphome_device)
            state.switch_state = SwitchStates.OFF

    async def async_set_humidity(self, humidity: int) -> None:
        """Set new humidity level."""

        if self.min_humidity == humidity:
            self.async_turn_off()
        else:
            humidity = TapHomeEntity.convert_ha_percentage_to_taphome(humidity)

            async with UpdateTapHomeState(self) as state:
                await self.humidifier_service.async_set_humidity(
                    self.taphome_device, humidity
                )

                if humidity is not None:
                    state.humidity = humidity


def setup_platform(
    hass: HomeAssistant,
    config,
    add_entities,
    discovery_info=None,
) -> None:
    """Set up the fan platform."""
    add_entry_requests: typing.List[AddEntryRequest] = hass.data[TAPHOME_PLATFORM][
        CONF_HUMIDIFIER
    ]
    humidifiers = []
    for add_entry_request in add_entry_requests:
        humidifier_service = HumidifierService(add_entry_request.tapHome_api_service)
        humidifier = TapHomeHumidifier(
            hass,
            add_entry_request.core_config,
            add_entry_request.config_entry,
            add_entry_request.coordinator,
            humidifier_service,
        )
        humidifiers.append(humidifier)

    add_entities(humidifiers)
