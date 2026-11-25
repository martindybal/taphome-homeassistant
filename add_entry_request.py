"""Helper object used during entity creation."""

from collections.abc import Callable, Iterable
from typing import Any, TypeVar, cast

from taphome_sdk import DeviceNotExposedError, DeviceTypeError

from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from .entity import TapHomeEntity
from .taphome_config_entry import AddEntryRequest, TapHomeEntityConfigT
from .taphome_data import TapHomeConfigEntry
from .taphome_issue_registry import TapHomeIssueRegistry

TapHomeEntityT = TypeVar("TapHomeEntityT", bound=TapHomeEntity[Any, Any])


def add_taphome_entities(
    entry: TapHomeConfigEntry,
    add_entities: AddConfigEntryEntitiesCallback,
    platform_domain: str,
    taphome_entities_factory: Callable[
        [AddEntryRequest[TapHomeEntityConfigT]],
        TapHomeEntityT | Iterable[TapHomeEntityT],
    ],
) -> None:
    """Create entities for one platform from the entry's stored requests.

    Requests are grouped by their device's config subentry so each batch is
    added under the right ``config_subentry_id`` (which ties the entities and
    their device to that subentry).
    """
    # Storage keeps the requests under the ``TapHomeEntityConfig`` base type; for
    # a given platform every request in the bucket carries this factory's own
    # config subtype, so narrowing to it is safe.
    requests: list[tuple[str, AddEntryRequest[TapHomeEntityConfigT]]] = cast(
        "list[tuple[str, AddEntryRequest[TapHomeEntityConfigT]]]",
        entry.runtime_data.add_entry_requests[platform_domain],
    )

    for subentry_id, configuration in requests:
        try:
            entry_entities = taphome_entities_factory(configuration)

            if not isinstance(entry_entities, Iterable):
                entry_entities = [entry_entities]

        except DeviceNotExposedError:
            taphome_issue_registry = TapHomeIssueRegistry(
                configuration.hass, configuration.core.id, configuration.core.entry_id
            )
            taphome_issue_registry.create_device_not_exposed_issue(
                configuration.entity.id
            )
            continue
        except DeviceTypeError as err:
            taphome_issue_registry = TapHomeIssueRegistry(
                configuration.hass, configuration.core.id, configuration.core.entry_id
            )
            taphome_issue_registry.create_device_type_mismatch_issue(
                configuration.entity.id,
                err.device_type,
                err.expected_device_types,
                err.supported_values,
            )
            continue

        add_entities(list(entry_entities), config_subentry_id=subentry_id)
