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
    add_entry_requests: dict[str, list[AddEntryRequest]]
    connection_state_handler: Callable[[HubConnectionState, HubConnectionState], None]


type TapHomeConfigEntry = ConfigEntry[TapHomeRuntimeData]
