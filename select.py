"""TapHome light integration."""

from homeassistant.components.select import DOMAIN as SELECT_DOMAIN, SelectEntity
from homeassistant.core import HomeAssistant

from .add_entry_request import AddEntryRequest
from .const import CONF_MULTIVALUE_SWITCHES, TAPHOME_PLATFORM
from .coordinator import TapHomeDataUpdateCoordinator, UpdateTapHomeState
from .taphome_entity import TapHomeConfigEntry, TapHomeCoreConfigEntry, TapHomeEntity
from .taphome_sdk import MultiValueSwitchService, MultiValueSwitchState, ValueType


class TapHomeSelectOption:
    def __init__(self, value: int, text: str) -> None:
        self._value = value
        self._text = text

    @property
    def value(self):
        return self._value

    @property
    def text(self):
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
    ):
        super().__init__(
            hass,
            core_config,
            config_entry,
            SELECT_DOMAIN,
            coordinator,
            MultiValueSwitchState,
        )
        self.multi_value_switch_service = multi_value_switch_service
        # this should be load from TapHome or config. TapHome don't provide such information but they promissed it to me

    @property
    def taphome_options(self) -> list[TapHomeSelectOption]:
        if self.taphome_device is not None:
            allowed_values = self.taphome_device.supported_values[
                ValueType.MultiValueSwitchState
            ].allowed_values
            return [
                TapHomeSelectOption(value["value"], value["name"])
                for value in filter(lambda value: value["isEnabled"], allowed_values)
            ]
        return None

    @property
    def options(self) -> list[str]:
        if self.taphome_device is not None:
            return [option.text for option in self.taphome_options]
        return None

    @property
    def current_option(self) -> str:
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
        return next(option for option in self.taphome_options if option.value == value)

    def get_opinion_by_text(self, text: str) -> TapHomeSelectOption:
        return next(option for option in self.taphome_options if option.text == text)


def setup_platform(
    hass: HomeAssistant,
    config,
    add_entities,
    discovery_info=None,
) -> None:
    """Set up the select platform."""
    add_entry_requests: list[AddEntryRequest] = hass.data[TAPHOME_PLATFORM][
        CONF_MULTIVALUE_SWITCHES
    ]
    selects = []
    for add_entry_request in add_entry_requests:
        select_service = MultiValueSwitchService(add_entry_request.taphome_api_service)
        select = TapHomeSelect(
            hass,
            add_entry_request.core_config,
            add_entry_request.config_entry,
            add_entry_request.coordinator,
            select_service,
        )
        selects.append(select)

    add_entities(selects)
