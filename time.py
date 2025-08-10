"""TapHome time integration."""

from datetime import time
import logging

from homeassistant.components.time import DOMAIN as TIME_DOMAIN, TimeEntity
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import (
    AddEntitiesCallback,
    ConfigType,
    DiscoveryInfoType,
)

from .add_entry_request import add_taphome_entities
from .const import CONF_TIMES
from .taphome_config_entry import AddEntryRequest, TapHomeEntityConfig
from .taphome_entity import TapHomeEntity
from .taphome_sdk import SessionDurationVariableDevice, SessionDurationVariableState

_LOGGER = logging.getLogger(__name__)


class TapHomeTime(TapHomeEntity, TimeEntity):
    """Representation of an time."""

    def __init__(self, config: AddEntryRequest[TapHomeEntityConfig]) -> None:
        """Initialize TapHome time entity."""

        self._variable = config.hub.get_typed_device(
            config.entity.id, SessionDurationVariableDevice
        )
        self._variable.state.changed += self._on_variable_state_change

        super().__init__(config, self._variable, TIME_DOMAIN)

    def _on_variable_state_change(
        self,
        _: SessionDurationVariableState | None,
        current_state: SessionDurationVariableState,
    ) -> None:
        self._attr_native_value = current_state.to_time()

    async def async_set_value(self, value: time) -> None:
        """Persist new time value on the device."""
        await self._variable.async_set_time(value)


def setup_platform(
    hass: HomeAssistant,
    _config: ConfigType,
    add_entities: AddEntitiesCallback,
    _discovery_info: DiscoveryInfoType | None = None,
) -> None:
    """Set up the switch platform."""
    add_taphome_entities(hass, add_entities, CONF_TIMES, TapHomeTime)
