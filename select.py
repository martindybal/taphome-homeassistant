"""TapHome light integration."""

from homeassistant.components.select import DOMAIN as SELECT_DOMAIN, SelectEntity
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import (
    AddEntitiesCallback,
    ConfigType,
    DiscoveryInfoType,
)

from .add_entry_request import add_taphome_entities
from .const import CONF_MULTIVALUE_SWITCHES
from .taphome_config_entry import AddEntryRequest, TapHomeEntityConfig
from .taphome_entity import TapHomeEntity
from .taphome_sdk import MultiValueSwitchDevice, MultiValueSwitchState


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
        self._multi_value_switch.state.changed += (
            self._on__multi_value_switch_state_change
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


def setup_platform(
    hass: HomeAssistant,
    config: ConfigType,
    add_entities: AddEntitiesCallback,
    discovery_info: DiscoveryInfoType | None = None,
) -> None:
    """Set up the switch platform."""
    add_taphome_entities(hass, add_entities, CONF_MULTIVALUE_SWITCHES, TapHomeSelect)
