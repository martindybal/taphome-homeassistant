class Location:
    def __init__(self, locationId: str, locationName: str):
        self._locationId = locationId
        self._locationName = locationName

    @staticmethod
    def create(location: dict):
        locationId = location["locationId"]
        locationName = location["locationName"]

        return Location(locationId, locationName)

    @property
    def locationId(self):
        return self._locationId

    @property
    def locationName(self):
        return self._locationName
