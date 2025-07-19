"""Provide support for handling button presses on TapHome devices."""

import logging
from enum import Enum

from .device import Device
from .taphome_api_service import TapHomeApiService
from .value_type import ValueType

_LOGGER = logging.getLogger(__name__)


class ButtonAction(Enum):
    """Enumeration of available button press actions."""

    PRESS = 1
    LONG_PRESS = 2
    DOUBLE_PRESS = 3
    TRIPPLE_PRESS = 4


class ButtonService:
    """Send button press commands to a TapHome device."""

    def __init__(self, taphome_api_service: TapHomeApiService):
        """Initialize the service with the TapHome API instance."""
        self.taphome_api_service = taphome_api_service

    async def async_press(
        self, device: Device, action: ButtonAction = ButtonAction.PRESS
    ) -> None:
        """Trigger the desired button ``action`` on ``device``."""
        values = [
            self.taphome_api_service.create_device_value(
                ValueType.BUTTON_PRESSED, action.value
            )
        ]

        await self.taphome_api_service.async_set_device_values(device.id, values)
