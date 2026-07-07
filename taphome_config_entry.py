"""Configuration entry for a TapHome core."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Generic, TypeVar

from homeassistant.core import HomeAssistant

from .taphome_sdk import TapHomeHub, get_optional, get_required


@dataclass(slots=True, frozen=True)
class NameMapping:
    """Define the name-to-target mapping (immutable/hashable)."""

    renames: frozenset[tuple[str, str]]

    @staticmethod
    def from_dict(data: dict | None) -> NameMapping:
        """Create a NameMapping from a dictionary."""
        renames = {
            source: target
            for source, target in (data or {}).items()
            if isinstance(target, str)
        }
        return NameMapping(frozenset(renames.items()))

    def get(self, original: str) -> str | None:
        """Return the configured target for the original name, or None."""
        for source, target in self.renames:
            if source == original:
                return target
        return None


@dataclass(slots=True, frozen=True)
class TapHomeCoreConfig:
    """Holds configuration options for a TapHome core instance."""

    id: str
    use_description_as_entity_id: bool
    use_description_as_name: bool
    zone_mapping: NameMapping | None
    label_mapping: NameMapping | None
    enabled_attributes: tuple[str, ...]

    def is_attribute_enabled(self, attribute: str) -> bool:
        """Return True if given attribute is enabled."""
        return attribute in self.enabled_attributes


class TapHomeEntityConfig:
    """Configuration options for a TapHome entity."""

    def __init__(self, device_config: dict) -> None:
        """Initialize TapHome entity configuration."""
        self._device_config = device_config
        self.id: int = self._get_id()
        self.unique_id: str | None = self.get_optional("unique_id", None)

    def _get_id(self) -> int:
        if isinstance(self._device_config, int):
            return self._device_config
        return int(get_required(self._device_config, "id"))

    def get_required(self, key: str):
        """Return value for ``key`` or raise if missing."""
        return get_required(self._device_config, key)

    def get_optional(self, key: str, default):
        """Return value for ``key`` or ``default`` if not present."""
        return get_optional(self._device_config, key, default)


TapHomeEntityConfigT = TypeVar("TapHomeEntityConfigT", bound=TapHomeEntityConfig)


@dataclass(slots=True, frozen=True)
class AddEntryRequest(Generic[TapHomeEntityConfigT]):
    """Store parameters required for entity creation."""

    hass: HomeAssistant
    core: TapHomeCoreConfig
    entity: TapHomeEntityConfigT
    hub: TapHomeHub
