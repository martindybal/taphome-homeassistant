"""TapHome button integration."""
import typing
from homeassistant.components.button import DOMAIN, ButtonEntity
from homeassistant.core import HomeAssistant
from .add_entry_request import AddEntryRequest
from .const import TAPHOME_PLATFORM, CONF_BUTTONS
from .taphome_entity import *
from .taphome_sdk import *


class ButtonConfigEntry(TapHomeConfigEntry):
    def __init__(self, device_config: dict):
        super().__init__(device_config)

        action_name = self.get_optional("action", ButtonAction.Press.name)
        for action in ButtonAction:
            if action.name.lower() == action_name.lower():
                self._action = action

        self._device_class = self.get_optional("device_class", None)

    @property
    def action(self):
        return self._action

    @property
    def device_class(self):
        return self._device_class


class TapHomeButton(TapHomeEntity[dict], ButtonEntity):
    """Representation of an button"""

    def __init__(
        self,
        hass: HomeAssistant,
        core_config: TapHomeCoreConfigEntry,
        config_entry: ButtonConfigEntry,
        coordinator: TapHomeDataUpdateCoordinator,
        button_service: ButtonService,
    ):
        super().__init__(hass, core_config, config_entry, DOMAIN, coordinator, dict)

        self._button_service = button_service
        self._action = config_entry.action
        self._device_class = config_entry.device_class

    @property
    def available(self):
        return not self.taphome_device is None

    @property
    def device_class(self):
        """Return the class of this device, from component DEVICE_CLASSES."""
        return self._device_class

    async def async_press(self) -> None:
        await self._button_service.async_press(self.taphome_device, self._action)


def setup_platform(
    hass: HomeAssistant,
    config,
    add_entities,
    discovery_info=None,
) -> None:
    """Set up the button platform."""
    add_entry_requests: typing.List[AddEntryRequest] = hass.data[TAPHOME_PLATFORM][
        CONF_BUTTONS
    ]
    buttons = []
    for add_entry_request in add_entry_requests:
        button_service = ButtonService(add_entry_request.tapHome_api_service)
        button = TapHomeButton(
            hass,
            add_entry_request.core_config,
            add_entry_request.config_entry,
            add_entry_request.coordinator,
            button_service,
        )
        buttons.append(button)

    add_entities(buttons)
