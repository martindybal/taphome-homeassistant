import logging

from .device import Device
from .taphome_api_service import TapHomeApiService
from .value_type import ValueType
from enum import Enum

_LOGGER = logging.getLogger(__name__)


class ButtonAction(Enum):
    Press = 1
    LongPress = 2
    DoublePress = 3
    TripplePress = 4


class ButtonService:
    def __init__(self, taphome_api_service: TapHomeApiService):
        self.taphome_api_service = taphome_api_service

    def async_press(
        self, device: Device, action: ButtonAction = ButtonAction.Press
    ) -> None:
        values = [
            self.taphome_api_service.create_device_value(
                ValueType.ButtonPressed, action.value
            )
        ]

        return self.taphome_api_service.async_set_device_values(device.id, values)
