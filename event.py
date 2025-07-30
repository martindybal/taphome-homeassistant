"""TapHome event integration."""

import logging

from homeassistant.components.event import (
    DOMAIN as EVENT_DOMAIN,
    EventDeviceClass,
    EventEntity,
)
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback, ConfigType
from homeassistant.helpers.typing import DiscoveryInfoType

from .add_entry_request import add_taphome_entities
from .button import TapHomeButtonConfig
from .const import CONF_BUTTONS
from .taphome_config_entry import AddEntryRequest
from .taphome_entity import TapHomeEntity
from .taphome_sdk import ButtonAction, ButtonDevice

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
        event_type = action.name.lower()
        self._trigger_event(event_type)
        self.async_write_ha_state()


def setup_platform(
    hass: HomeAssistant,
    config: ConfigType,
    add_entities: AddEntitiesCallback,
    discovery_info: DiscoveryInfoType | None = None,
) -> None:
    """Set up the event platform."""
    add_taphome_entities(hass, add_entities, CONF_BUTTONS, TapHomeButtonEvent)
