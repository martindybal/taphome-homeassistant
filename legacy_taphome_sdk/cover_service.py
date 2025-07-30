"""Control covers such as blinds within the TapHome system."""

import logging

from .device import Device
from .taphome_api_service import TapHomeApiService
from .taphome_device_state import TapHomeState
from .value_type import ValueType

_LOGGER = logging.getLogger(__name__)


class CoverState(TapHomeState):
    """Represent the current state of a cover."""

    def __init__(
        self,
        switch_values: dict,
    ) -> None:
        """Create a new instance from raw ``switch_values``."""
        super().__init__(switch_values)
        self.blinds_level = self.get_device_value(ValueType.BLINDS_LEVEL)
        self.blinds_slope = self.get_device_value(ValueType.BLINDS_SLOPE)
        self.blinds_is_moving = self.get_device_bool_value(ValueType.BLINDS_IS_MOVING)


class CoverService:
    """Service for operating TapHome covers."""

    def __init__(self, taphome_api_service: TapHomeApiService) -> None:
        """Initialize with the given TapHome API service."""
        self.taphome_api_service = taphome_api_service

    async def async_get_state(self, device: Device) -> CoverState | None:
        """Return the current state of ``device``."""
        try:
            cover_values = await self.taphome_api_service.async_get_device_values(
                device.id
            )

            return CoverState(cover_values)
        except Exception:
            _LOGGER.exception(
                "TapHome async_get_state for device %s failed",
                device.id,
            )
            return None

    async def async_set_level(self, device: Device, position, tilt=None) -> None:
        """Move the cover to ``position`` and optionally set ``tilt``."""
        values = [
            self.taphome_api_service.create_device_value(
                ValueType.BLINDS_LEVEL, position
            )
        ]

        if tilt is not None:
            values.append(
                self.taphome_api_service.create_device_value(
                    ValueType.BLINDS_SLOPE, tilt
                )
            )

        await self.taphome_api_service.async_set_device_values(device.id, values)

    async def async_set_slope(self, device: Device, tilt) -> None:
        """Adjust the tilt of the cover to ``tilt``."""
        values = [
            self.taphome_api_service.create_device_value(ValueType.BLINDS_SLOPE, tilt)
        ]

        await self.taphome_api_service.async_set_device_values(device.id, values)
