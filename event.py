"""TapHome event integration."""

import logging

from taphome_sdk import ButtonAction, ButtonDevice

from homeassistant.components.event import (
    DOMAIN as EVENT_DOMAIN,
    EventDeviceClass,
    EventEntity,
)
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .add_entry_request import add_taphome_entities
from .button import TapHomeButtonConfig
from .entity import TapHomeEntity
from .taphome_config_entry import AddEntryRequest
from .taphome_data import TapHomeConfigEntry

_LOGGER = logging.getLogger(__name__)


class TapHomeButtonEvent(TapHomeEntity, EventEntity):
    """Representation of a TapHome button event entity."""

    def __init__(self, config: AddEntryRequest[TapHomeButtonConfig]) -> None:
        """Initialize the TapHome button event entity."""
        self._button = config.hub.get_typed_device(config.entity.id, ButtonDevice)
        self._attr_device_class = EventDeviceClass.BUTTON
        self._attr_event_types = [action.name.lower() for action in ButtonAction]
        self._button.clicked += self._on_button_clicked
        super().__init__(config, self._button, EVENT_DOMAIN)

    def _on_button_clicked(self, action: ButtonAction) -> None:
        """Handle button click event."""
        if self.hass is not None:
            event_type = action.name.lower()
            self._trigger_event(event_type)
            self.async_write_ha_state()


async def async_setup_entry(
    hass: HomeAssistant,
    entry: TapHomeConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up TapHome button events from a config entry."""
    add_taphome_entities(entry, async_add_entities, EVENT_DOMAIN, TapHomeButtonEvent)
