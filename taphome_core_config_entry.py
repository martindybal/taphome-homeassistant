"""Configuration entry for a TapHome core."""

from dataclasses import dataclass


@dataclass(slots=True, frozen=True)
class TapHomeCoreConfigEntry:
    """Holds configuration options for a TapHome core instance."""

    id: str
    use_description_as_entity_id: bool
    use_description_as_name: bool
    enabled_attributes: tuple[str, ...]

    def is_attribute_enabled(self, attribute: str) -> bool:
        """Return True if given attribute is enabled."""
        return attribute in self.enabled_attributes
