"""Helper object used during entity creation."""

from dataclasses import dataclass
from typing import Generic, TypeVar

from .coordinator import TapHomeDataUpdateCoordinator
from .taphome_core_config_entry import TapHomeCoreConfigEntry
from .taphome_entity import TapHomeConfigEntry
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
