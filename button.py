"""TapHome button integration."""

from collections.abc import Iterator

from homeassistant.components.button import (
    DOMAIN as BUTTON_DOMAIN,
    ButtonDeviceClass,
    ButtonEntity,
)
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback, ConfigType
from homeassistant.helpers.typing import DiscoveryInfoType

from .add_entry_request import add_taphome_entities
from .const import CONF_BUTTONS
from .taphome_entity import (
    TapHomeConfigEntry,
    TapHomeCoreConfigEntry,
    TapHomeDataUpdateCoordinator,
    TapHomeEntity,
)
from .legacy_taphome_sdk import ButtonAction, ButtonService, TapHomeState
from .legacy_taphome_sdk.helpers import Helpers


class ButtonConfigEntry(TapHomeConfigEntry):
    """Configuration options for TapHome buttons."""

    def __init__(self, device_config: dict) -> None:
        """Initialize button config entry."""
        super().__init__(device_config)

        config_actions = self.get_optional("actions", None)
        if config_actions is None:
            self._actions = [ButtonAction.PRESS]
        else:
            self._actions: list[ButtonAction] = []
            for config_action in config_actions:
                action = Helpers.enum_from_string(ButtonAction, config_action)
                self._actions.append(action)

        self._device_class: ButtonDeviceClass | None = self.get_optional(
            "device_class", None
        )

    @property
    def actions(self):
        """Return list of supported button actions."""
        return self._actions

    @property
    def device_class(self):
        """Return Home Assistant button device class if configured."""
        return self._device_class


class TapHomeButton(TapHomeEntity[TapHomeState], ButtonEntity):
    """Representation of an button."""

    def __init__(
        self,
        hass: HomeAssistant,
        core_config: TapHomeCoreConfigEntry,
        config_entry: ButtonConfigEntry,
        action: ButtonAction,
        coordinator: TapHomeDataUpdateCoordinator,
        button_service: ButtonService,
    ) -> None:
        """Initialize TapHome button entity."""
        super().__init__(
            hass,
            core_config,
            config_entry,
            f"{BUTTON_DOMAIN}.{action.name.replace('_', '')}",
            coordinator,
            TapHomeState,
        )

        self._button_service = button_service
        self._action = action
        self._attr_device_class = config_entry.device_class

    def _update_available(self):
        self._attr_available = self.taphome_device is not None

    async def async_press(self) -> None:
        """Send press command to the TapHome device."""
        await self._button_service.async_press(self.taphome_device, self._action)


def _create_button_entities(
    hass: HomeAssistant,
    core_config: TapHomeCoreConfigEntry,
    config_entry: ButtonConfigEntry,
    coordinator: TapHomeDataUpdateCoordinator,
    button_service: ButtonService,
) -> Iterator[TapHomeButton]:
    """Create TapHome button entities."""
    for action in config_entry.actions:
        yield TapHomeButton(
            hass,
            core_config,
            config_entry,
            action,
            coordinator,
            button_service,
        )


def setup_platform(
    hass: HomeAssistant,
    config: ConfigType,
    add_entities: AddEntitiesCallback,
    discovery_info: DiscoveryInfoType | None = None,
) -> None:
    """Set up the button platform."""
    add_taphome_entities(
        hass, add_entities, CONF_BUTTONS, ButtonService, _create_button_entities
    )
