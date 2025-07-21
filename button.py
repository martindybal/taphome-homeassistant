"""TapHome button integration."""

from .taphome_sdk.helpers import Helpers
from homeassistant.components.button import (
    DOMAIN as BUTTON_DOMAIN,
    ButtonDeviceClass,
    ButtonEntity,
)
from homeassistant.core import HomeAssistant

from .add_entry_request import AddEntryRequest
from .const import CONF_BUTTONS, TAPHOME_PLATFORM
from .taphome_entity import (
    TapHomeConfigEntry,
    TapHomeCoreConfigEntry,
    TapHomeDataUpdateCoordinator,
    TapHomeEntity,
)
from .taphome_sdk import ButtonAction, ButtonService, TapHomeState


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
            f"{BUTTON_DOMAIN}.{action.name}",
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


def setup_platform(
    hass: HomeAssistant,
    config,
    add_entities,
    discovery_info=None,
) -> None:
    """Set up the button platform."""
    add_entry_requests: list[AddEntryRequest] = hass.data[TAPHOME_PLATFORM][
        CONF_BUTTONS
    ]
    buttons = []
    for add_entry_request in add_entry_requests:
        button_service = ButtonService(add_entry_request.taphome_api_service)

        for action in add_entry_request.config_entry.actions:
            button = TapHomeButton(
                hass,
                add_entry_request.core_config,
                add_entry_request.config_entry,
                action,
                add_entry_request.coordinator,
                button_service,
            )
            buttons.append(button)

    add_entities(buttons)
