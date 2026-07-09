"""Configuration entry for a TapHome core."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TypeVar

from taphome_sdk import TapHomeHub, get_optional, get_required

from homeassistant.core import HomeAssistant


@dataclass(slots=True, frozen=True)
class NameMapping:
    """Define the name-to-target mapping and ignored names (immutable).

    A target is either an area/label id (stored by the options flow) or a
    plain name (imported from YAML). Unmapped names fall back to themselves;
    ignored names get no assignment at all.
    """

    renames: frozenset[tuple[str, str]]
    ignored: frozenset[str]

    @staticmethod
    def from_dict(data: dict | None) -> NameMapping:
        """Create a NameMapping from a dictionary."""
        renames: dict[str, str] = {}
        ignored: set[str] = set()
        for source, target in (data or {}).items():
            if isinstance(target, dict) and target.get("ignore"):
                ignored.add(source)
            elif isinstance(target, str):
                renames[source] = target
        return NameMapping(frozenset(renames.items()), frozenset(ignored))

    def is_ignored(self, original: str) -> bool:
        """Return True when the original name must not be assigned at all."""
        return original in self.ignored

    def map(self, original: str) -> str:
        """Return the configured target, or the original name itself."""
        for source, target in self.renames:
            if source == original:
                return target
        return original


@dataclass(slots=True, frozen=True)
class TapHomeCoreConfig:
    """Holds configuration options for a TapHome core instance."""

    id: str | None
    # The per-core segment embedded in entity unique ids (the location id for
    # cores added after this was introduced, the YAML id for imported cores,
    # None for older UI cores). ``id`` stays for display and hub identity.
    unique_id_segment: str | None
    zone_mapping: NameMapping
    label_mapping: NameMapping
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
class AddEntryRequest[ConfigT: TapHomeEntityConfig]:
    """Store parameters required for entity creation."""

    hass: HomeAssistant
    core: TapHomeCoreConfig
    entity: ConfigT
    hub: TapHomeHub
