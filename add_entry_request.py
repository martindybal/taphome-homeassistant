from .coordinator import TapHomeDataUpdateCoordinator
from .taphome_core_config_entry import TapHomeCoreConfigEntry
from .taphome_entity import TapHomeConfigEntry
from .taphome_sdk import *


class AddEntryRequest:
    def __init__(
        self,
        core_config: TapHomeCoreConfigEntry,
        config_entry: TapHomeConfigEntry,
        taphome_device_id: int,
        coordinator: TapHomeDataUpdateCoordinator,
        tapHome_api_service: TapHomeApiService,
    ):
        self._core_config = core_config
        self._config_entry = config_entry
        self._taphome_device_id = taphome_device_id
        self._coordinator = coordinator
        self._tapHome_api_service = tapHome_api_service

    @property
    def core_config(self):
        return self._core_config

    @property
    def config_entry(self):
        return self._config_entry

    @property
    def coordinator(self):
        return self._coordinator

    @property
    def tapHome_api_service(self):
        return self._tapHome_api_service
