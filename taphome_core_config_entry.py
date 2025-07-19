"""Configuration entry for a TapHome core."""

from dataclasses import dataclass


@dataclass(slots=True, frozen=True)
class TapHomeCoreConfigEntry:
    """Holds configuration options for a TapHome core instance."""

    core_id: str
    use_description_as_entity_id: bool
    use_description_as_name: bool

    @property
    def id(self) -> str:
        """Return the identifier of the TapHome core."""
        return self.core_id
