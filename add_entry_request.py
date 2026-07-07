"""Helper object used during entity creation."""

from collections.abc import Callable, Iterable
from typing import TypeVar

from taphome_sdk import DeviceNotExposedError, DeviceTypeError

from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .entity import TapHomeEntity
from .taphome_config_entry import AddEntryRequest, TapHomeEntityConfigT
from .taphome_data import TapHomeConfigEntry
from .taphome_issue_registry import TapHomeIssueRegistry

TapHomeEntityT = TypeVar("TapHomeEntityT", bound=TapHomeEntity)


def add_taphome_entities(
    entry: TapHomeConfigEntry,
    add_entities: AddEntitiesCallback | Callable[[Iterable[TapHomeEntityT]], None],
    platform_domain: str,
    taphome_entities_factory: Callable[
        [AddEntryRequest[TapHomeEntityConfigT]],
        TapHomeEntityT | Iterable[TapHomeEntityT],
    ],
) -> None:
    """Create entities for one platform from the entry's stored requests."""
    entities_configuration: list[AddEntryRequest[TapHomeEntityConfigT]] = (
        entry.runtime_data.add_entry_requests[platform_domain]
    )

    all_entities: list[TapHomeEntityT] = []
    for configuration in entities_configuration:
        try:
            entry_entities = taphome_entities_factory(configuration)

            if not isinstance(entry_entities, Iterable):
                entry_entities = [entry_entities]

        except DeviceNotExposedError:
            taphome_issue_registry = TapHomeIssueRegistry(
                configuration.hass, configuration.core.id
            )
            taphome_issue_registry.create_device_not_exposed_issue(
                configuration.entity.id
            )
            continue
        except DeviceTypeError as err:
            taphome_issue_registry = TapHomeIssueRegistry(
                configuration.hass, configuration.core.id
            )
            taphome_issue_registry.create_device_type_mismatch_issue(
                configuration.entity.id,
                err.device_type,
                err.expected_device_types,
                err.supported_values,
            )
            continue

        all_entities.extend(entry_entities)

    add_entities(all_entities)
