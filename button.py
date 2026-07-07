"""TapHome button integration."""

from collections.abc import Iterator

from taphome_sdk import ButtonAction, ButtonDevice, enum_from_string_required

from homeassistant.components.button import (
    DOMAIN as BUTTON_DOMAIN,
    ButtonDeviceClass,
    ButtonEntity,
)
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .add_entry_request import add_taphome_entities
from .entity import TapHomeEntity
from .taphome_config_entry import AddEntryRequest, TapHomeEntityConfig
from .taphome_data import TapHomeConfigEntry


class TapHomeButtonConfig(TapHomeEntityConfig):
    """Configuration options for TapHome buttons."""

    def __init__(self, device_config: dict) -> None:
        """Initialize button config entry."""
        super().__init__(device_config)

        self.device_class: ButtonDeviceClass | None = self.get_optional(
            "device_class", None
        )

        config_actions = self.get_optional("actions", None)
        if config_actions is None:
            self.actions = [ButtonAction.PRESS]
        else:
            self.actions: list[ButtonAction] = []
            for config_action in config_actions:
                action = enum_from_string_required(ButtonAction, config_action)
                self.actions.append(action)


class TapHomeButton(TapHomeEntity, ButtonEntity):
    """Representation of an button."""

    def __init__(
        self,
        config: AddEntryRequest[TapHomeButtonConfig],
        action: ButtonAction,
    ) -> None:
        """Initialize TapHome button entity."""

        self._button = config.hub.get_typed_device(config.entity.id, ButtonDevice)
        self._attr_device_class = config.entity.device_class
        self._action = action

        super().__init__(
            config, self._button, BUTTON_DOMAIN, action.name.replace("_", "")
        )
        self._add_state_attributes(
            "taphome_button_action",
            action,
            lambda value: value.name.replace("_", " ").lower(),
        )

    async def async_press(self) -> None:
        """Send press command to the TapHome device."""
        await self._button.async_press(self._action)


def _create_button_entities(
    config: AddEntryRequest[TapHomeButtonConfig],
) -> Iterator[TapHomeButton]:
    """Create TapHome button entities."""
    for action in config.entity.actions:
        yield TapHomeButton(
            config,
            action,
        )


async def async_setup_entry(
    hass: HomeAssistant,
    entry: TapHomeConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up TapHome buttons from a config entry."""
    add_taphome_entities(
        entry, async_add_entities, BUTTON_DOMAIN, _create_button_entities
    )
