"""Runtime data stored on a TapHome config entry."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass

from homeassistant.config_entries import ConfigEntry

from taphome_sdk import HubConnectionState, TapHomeHub

from .taphome_config_entry import AddEntryRequest, TapHomeCoreConfig


@dataclass(slots=True)
class TapHomeRuntimeData:
    """Objects a loaded TapHome config entry keeps for its lifetime."""

    hub: TapHomeHub
    core_config: TapHomeCoreConfig
    # Per platform domain, the (subentry id, request) pairs to add. Entities are
    # added grouped by subentry so each is tied to its device's config subentry.
    add_entry_requests: dict[str, list[tuple[str, AddEntryRequest]]]
    connection_state_handler: Callable[[HubConnectionState, HubConnectionState], None]


type TapHomeConfigEntry = ConfigEntry[TapHomeRuntimeData]
