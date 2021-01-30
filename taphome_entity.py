from .taphome_sdk import *


class TapHomeEntity:
    def __init__(self, device: Device):
        self._device = device

    @property
    def unique_id(self):
        return f"{self.__class__.__name__}.taphome_{self._device.deviceId}".lower()

    @property
    def name(self):
        return self._device.name