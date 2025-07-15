"""Model for a TapHome location."""


class Location:
    """Represent a physical location in TapHome."""

    def __init__(self, location_id: str, location_name: str):
        """Create a new location from its id and name."""
        self._location_id = location_id
        self._location_name = location_name

    @staticmethod
    def create(location: dict):
        """Instantiate ``Location`` from a dictionary."""
        location_id = location["locationId"]
        location_name = location["locationName"]

        return Location(location_id, location_name)

    @property
    def location_id(self):
        """Return the unique identifier of the location."""
        return self._location_id

    @property
    def location_name(self):
        """Return the human readable name of the location."""
        return self._location_name
