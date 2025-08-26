"""Helper object used during entity creation."""

from collections.abc import Callable, Iterable
from typing import TypeVar

from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import TAPHOME_PLATFORM
from .taphome_config_entry import AddEntryRequest, TapHomeEntityConfigT
from .taphome_entity import TapHomeEntity
from .taphome_issue_registry import TapHomeIssueRegistry
from .taphome_sdk import DeviceNotExposedError

TapHomeEntityT = TypeVar("TapHomeEntityT", bound=TapHomeEntity)


def add_taphome_entities(
    hass: HomeAssistant,
    add_entities: AddEntitiesCallback,
    configuration_section_name: str,
    taphome_entities_factory: Callable[
        [AddEntryRequest[TapHomeEntityConfigT]],
        TapHomeEntityT | Iterable[TapHomeEntityT],
    ],
) -> None:
    """Set up the switch platform."""
    entities_configuration: list[AddEntryRequest[TapHomeEntityConfigT]] = hass.data[
        TAPHOME_PLATFORM
    ][configuration_section_name]

    all_entities = []
    for configuration in entities_configuration:
        try:
            entry_entities = taphome_entities_factory(configuration)

            if not isinstance(entry_entities, Iterable):
                entry_entities = [entry_entities]

        except DeviceNotExposedError:
            taphome_issue_registry = TapHomeIssueRegistry(hass, configuration.core.id)
            taphome_issue_registry.create_device_not_exposed_issue(
                configuration.entity.id
            )
            continue

        all_entities.extend(entry_entities)

    add_entities(all_entities)
