class TapHomeCoreConfigEntry:
    def __init__(
        self, id: str, use_description_as_entity_id: bool, use_description_as_name: bool
    ):
        self._id = id
        self._use_description_as_entity_id = use_description_as_entity_id
        self._use_description_as_name = use_description_as_name

    @property
    def id(self):
        return self._id

    @property
    def use_description_as_entity_id(self):
        return self._use_description_as_entity_id

    @property
    def use_description_as_name(self):
        return self._use_description_as_name
