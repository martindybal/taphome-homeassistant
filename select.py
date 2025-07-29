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
from .coordinator import TapHomeDataUpdateCoordinator, UpdateTapHomeState
from .taphome_entity import TapHomeConfigEntry, TapHomeCoreConfigEntry, TapHomeEntity
from .taphome_sdk import MultiValueSwitchService, MultiValueSwitchState, ValueType


class TapHomeSelectOption:
    """Represent a selectable option value."""

    def __init__(self, value: int, text: str) -> None:
        """Store option ``value`` and display ``text``."""
        self._value = value
        self._text = text

    @property
    def value(self):
        """Return raw option value sent to TapHome."""
        return self._value

    @property
    def text(self):
        """Return human readable option value."""
        return self._text


class TapHomeSelect(TapHomeEntity[MultiValueSwitchState], SelectEntity):
    """Representation of an select."""

    def __init__(
        self,
        hass: HomeAssistant,
        core_config: TapHomeCoreConfigEntry,
        config_entry: TapHomeConfigEntry,
        coordinator: TapHomeDataUpdateCoordinator,
        multi_value_switch_service: MultiValueSwitchService,
    ) -> None:
        """Initialize TapHome select entity."""
        super().__init__(
            hass,
            core_config,
            config_entry,
            SELECT_DOMAIN,
            coordinator,
            MultiValueSwitchState,
        )
        self.multi_value_switch_service = multi_value_switch_service

    @property
    def taphome_options(self) -> list[TapHomeSelectOption]:
        """Return list of available options from TapHome."""
        if self.taphome_device is not None:
            allowed_values = self.taphome_device.supported_values[
                ValueType.MULTI_VALUE_SWITCH_STATE
            ].allowed_values
            return [
                TapHomeSelectOption(value.value, value.name)
                for value in filter(lambda value: value.is_enabled, allowed_values)
            ]
        return None

    @property
    def options(self) -> list[str]:
        """Return list of option texts for Home Assistant UI."""
        if self.taphome_device is not None:
            return [option.text for option in self.taphome_options]
        return None

    @property
    def current_option(self) -> str:
        """Return text of the currently selected option."""
        if self.taphome_state is not None:
            return self.get_opinion_by_value(
                self.taphome_state.multi_value_switch_state
            ).text
        return None

    async def async_select_option(self, option: str) -> None:
        """Change the selected option."""
        taphome_option = self.get_opinion_by_text(option)

        async with UpdateTapHomeState(self) as state:
            await self.multi_value_switch_service.async_set_value(
                taphome_option.value, self.taphome_device
            )
            state.multi_value_switch_state = taphome_option.value

    def get_opinion_by_value(self, value: int) -> TapHomeSelectOption:
        """Return option object matching ``value``."""
        return next(option for option in self.taphome_options if option.value == value)

    def get_opinion_by_text(self, text: str) -> TapHomeSelectOption:
        """Return option object matching ``text``."""
        return next(option for option in self.taphome_options if option.text == text)


def setup_platform(
    hass: HomeAssistant,
    config: ConfigType,
    add_entities: AddEntitiesCallback,
    discovery_info: DiscoveryInfoType | None = None,
) -> None:
    """Set up the switch platform."""
    add_taphome_entities(
        hass,
        add_entities,
        CONF_MULTIVALUE_SWITCHES,
        MultiValueSwitchService,
        TapHomeSelect,
    )
