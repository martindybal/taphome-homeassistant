class Location:
    def __init__(self, location_id: str, location_name: str):
        self._location_id = location_id
        self._location_name = location_name

    @staticmethod
    def create(location: dict):
        location_id = location["locationId"]
        location_name = location["locationName"]

        return Location(location_id, location_name)

    @property
    def location_id(self):
        return self._location_id

    @property
    def location_name(self):
        return self._location_name
