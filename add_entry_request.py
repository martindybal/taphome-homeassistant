"""Helper object used during entity creation."""

from .coordinator import TapHomeDataUpdateCoordinator
from .taphome_core_config_entry import TapHomeCoreConfigEntry
from .taphome_entity import TapHomeConfigEntry
from .taphome_sdk import TapHomeApiService


class AddEntryRequest:
    """Store parameters needed for creating an entity."""

    def __init__(
        self,
        core_config: TapHomeCoreConfigEntry,
        config_entry: TapHomeConfigEntry,
        taphome_device_id: int,
        coordinator: TapHomeDataUpdateCoordinator,
        taphome_api_service: TapHomeApiService,
    ) -> None:
        """Initialize request data for entity creation."""
        self._core_config = core_config
        self._config_entry = config_entry
        self._taphome_device_id = taphome_device_id
        self._coordinator = coordinator
        self._taphome_api_service = taphome_api_service

    @property
    def core_config(self):
        """Return TapHome core configuration."""
        return self._core_config

    @property
    def config_entry(self):
        """Return the configuration entry used for entity creation."""
        return self._config_entry

    @property
    def coordinator(self):
        """Return the coordinator responsible for data updates."""
        return self._coordinator

    @property
    def taphome_api_service(self):
        """Return the TapHome API service instance."""
        return self._taphome_api_service
