"""Provide support for handling button presses on TapHome devices."""

from enum import Enum
import logging

from .device import Device
from .taphome_api_service import TapHomeApiService
from .value_type import ValueType

_LOGGER = logging.getLogger(__name__)


class ButtonAction(Enum):
    """Enumeration of available button press actions."""

    Press = 1
    LongPress = 2
    DoublePress = 3
    TripplePress = 4


class ButtonService:
    """Send button press commands to a TapHome device."""

    def __init__(self, taphome_api_service: TapHomeApiService):
        """Initialize the service with the TapHome API instance."""
        self.taphome_api_service = taphome_api_service

    async def async_press(
        self, device: Device, action: ButtonAction = ButtonAction.Press
    ) -> None:
        """Trigger the desired button ``action`` on ``device``."""
        values = [
            self.taphome_api_service.create_device_value(
                ValueType.ButtonPressed, action.value
            )
        ]

        await self.taphome_api_service.async_set_device_values(device.id, values)
