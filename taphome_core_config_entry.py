"""Configuration entry for a TapHome core."""


class TapHomeCoreConfigEntry:
    """Holds configuration options for a TapHome core instance."""

    def __init__(
        self, id: str, use_description_as_entity_id: bool, use_description_as_name: bool
    ) -> None:
        """Initialize core configuration with provided options."""
        self._id = id
        self._use_description_as_entity_id = use_description_as_entity_id
        self._use_description_as_name = use_description_as_name

    @property
    def id(self):
        """Return the identifier of the TapHome core."""
        return self._id

    @property
    def use_description_as_entity_id(self):
        """Return ``True`` if device description should be used as entity_id."""
        return self._use_description_as_entity_id

    @property
    def use_description_as_name(self):
        """Return ``True`` if device description should be used as entity name."""
        return self._use_description_as_name
