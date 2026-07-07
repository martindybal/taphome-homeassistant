"""TapHome light integration."""

from taphome_sdk import MultiValueSwitchDevice, MultiValueSwitchState

from homeassistant.components.select import DOMAIN as SELECT_DOMAIN, SelectEntity
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .add_entry_request import add_taphome_entities
from .entity import TapHomeEntity
from .taphome_config_entry import AddEntryRequest, TapHomeEntityConfig
from .taphome_data import TapHomeConfigEntry


class TapHomeSelect(TapHomeEntity, SelectEntity):
    """Representation of an select."""

    def __init__(
        self,
        config: AddEntryRequest[TapHomeEntityConfig],
    ) -> None:
        """Initialize TapHome select entity."""

        self._multi_value_switch = config.hub.get_typed_device(
            config.entity.id, MultiValueSwitchDevice
        )
        self._subscribe(
            self._multi_value_switch.state.changed,
            self._on__multi_value_switch_state_change,
        )

        self._attr_options = self._multi_value_switch.options

        super().__init__(config, self._multi_value_switch, SELECT_DOMAIN)

    def _on__multi_value_switch_state_change(
        self,
        _: MultiValueSwitchState | None,
        current_state: MultiValueSwitchState,
    ) -> None:
        self._attr_current_option = self._multi_value_switch.selected_option

    async def async_select_option(self, option: str) -> None:
        """Change the selected option."""
        await self._multi_value_switch.async_select_option(option)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: TapHomeConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up TapHome selects from a config entry."""
    add_taphome_entities(entry, async_add_entities, SELECT_DOMAIN, TapHomeSelect)
