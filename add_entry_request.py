"""Helper object used during entity creation."""

from collections.abc import Callable, Iterable
from dataclasses import dataclass
from typing import Generic, TypeVar

from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import TAPHOME_PLATFORM
from .coordinator import TapHomeDataUpdateCoordinator
from .taphome_core_config_entry import TapHomeCoreConfigEntry
from .taphome_entity import TapHomeConfigEntry, TapHomeEntity
from .taphome_sdk import TapHomeApiService

ConfigEntryT = TypeVar("ConfigEntryT", bound="TapHomeConfigEntry")


@dataclass(slots=True)
class AddEntryRequest(Generic[ConfigEntryT]):
    """Store parameters required for entity creation."""

    core_config: TapHomeCoreConfigEntry
    config_entry: ConfigEntryT
    taphome_device_id: int
    coordinator: TapHomeDataUpdateCoordinator
    taphome_api_service: TapHomeApiService


TapHomeServiceT = TypeVar("TapHomeServiceT")
TapHomeEntityT = TypeVar("TapHomeEntityT", bound="TapHomeEntity")


def add_taphome_entities(
    hass: HomeAssistant,
    add_entities: AddEntitiesCallback,
    configuration_section_name: str,
    taphome_service_factory: Callable[[TapHomeApiService], TapHomeServiceT],
    taphome_entities_factory: Callable[
        [
            HomeAssistant,
            TapHomeCoreConfigEntry,
            ConfigEntryT,
            TapHomeDataUpdateCoordinator,
            TapHomeServiceT,
        ],
        TapHomeEntityT | Iterable[TapHomeEntityT],
    ],
) -> None:
    """Set up the switch platform."""
    entities_configuration: list[AddEntryRequest[ConfigEntryT]] = hass.data[
        TAPHOME_PLATFORM
    ][configuration_section_name]

    all_entities = []
    for entity_configuration in entities_configuration:
        entry_entities = taphome_entities_factory(
            hass,
            entity_configuration.core_config,
            entity_configuration.config_entry,
            entity_configuration.coordinator,
            taphome_service_factory(entity_configuration.taphome_api_service),
        )

        if not isinstance(entry_entities, Iterable):
            entry_entities = [entry_entities]

        all_entities.extend(entry_entities)

    add_entities(all_entities)
