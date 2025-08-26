"""Configuration entry for a TapHome core."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Generic, TypeVar

from homeassistant.core import HomeAssistant

from .taphome_sdk import TapHomeHub, get_optional, get_required


@dataclass(slots=True, frozen=True)
class NameMapping:
    """Define name mapping and ignored names (immutable/hashable)."""

    renames: frozenset[tuple[str, str]]
    ignored: frozenset[str]

    @staticmethod
    def from_dict(data: dict | None) -> NameMapping:
        """Create a NameMapping from a dictionary."""
        renames: dict[str, str] = {}
        ignored: set[str] = set()
        if data is not None:
            for source, target in data.items():
                if isinstance(target, dict) and target.get("ignore"):
                    ignored.add(source)
                elif isinstance(target, str):
                    renames[source] = target
        return NameMapping(frozenset(renames.items()), frozenset(ignored))

    def is_ignored(self, original: str) -> bool:
        """Check if the original name is ignored."""
        return original in self.ignored

    def map(self, original: str) -> str:
        """Map original name to preferred name."""
        for k, v in self.renames:
            if k == original:
                return v
        return original


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
