"""TapHome time integration."""

from datetime import time
import logging
from typing import override

from taphome_sdk import SessionDurationVariableDevice, SessionDurationVariableState

from homeassistant.components.time import DOMAIN as TIME_DOMAIN, TimeEntity
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .add_entry_request import add_taphome_entities
from .entity import TapHomeEntity
from .taphome_config_entry import AddEntryRequest, TapHomeEntityConfig
from .taphome_data import TapHomeConfigEntry

_LOGGER = logging.getLogger(__name__)


class TapHomeTime(TapHomeEntity, TimeEntity):
    """Representation of an time."""

    def __init__(self, config: AddEntryRequest[TapHomeEntityConfig]) -> None:
        """Initialize TapHome time entity."""

        self._variable = config.hub.get_typed_device(
            config.entity.id, SessionDurationVariableDevice
        )
        self._subscribe(self._variable.state.changed, self._on_variable_state_change)

        super().__init__(config, self._variable, TIME_DOMAIN)

    def _on_variable_state_change(
        self,
        _: SessionDurationVariableState | None,
        current_state: SessionDurationVariableState,
    ) -> None:
        self._attr_native_value = current_state.to_time()

    @override
    async def async_set_value(self, value: time) -> None:
        """Persist new time value on the device."""
        await self._variable.async_set_time(value)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: TapHomeConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up TapHome times from a config entry."""
    add_taphome_entities(entry, async_add_entities, TIME_DOMAIN, TapHomeTime)
