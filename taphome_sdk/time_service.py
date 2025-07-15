"""Time based device support for TapHome."""

import logging

from .device import Device
from .taphome_api_service import TapHomeApiService
from .taphome_device_state import TapHomeState
from .value_type import ValueType

_LOGGER = logging.getLogger(__name__)


class TimeState(TapHomeState):
    """State representation for a time device."""

    def __init__(
        self,
        switch_values: dict,
    ):
        """Create state from ``switch_values``."""
        super().__init__(switch_values)
        self.total_seconds = self.get_device_value(ValueType.SessionDuration)


class TimeService:
    """Service for devices exposing a time value."""

    def __init__(self, taphome_api_service: TapHomeApiService):
        """Initialize with the TapHome API service."""
        self.taphome_api_service = taphome_api_service

    async def async_get_state(self, device: Device):
        """Return ``TimeState`` for ``device`` if available."""
        try:
            time_values = await self.taphome_api_service.async_get_device_values(
                device.id
            )

            if time_values is None:
                return None

            return TimeState(time_values)
        except Exception:
            _LOGGER.exception("TapHome async_get_state for %s failed", device.id)
            return None

    def async_set_value(self, total_seconds: int, device: Device) -> None:
        """Set time in seconds on ``device``."""
        values = [
            self.taphome_api_service.create_device_value(
                # Be care here. Only variable state can be changed. Value conversions are readonly.
                ValueType.VariableState,
                total_seconds,
            )
        ]

        return self.taphome_api_service.async_set_device_values(device.id, values)
