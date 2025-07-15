"""Service methods for controlling valve devices."""

from .device import Device
from .percentage_service import PercentageService, PercentageState
from .taphome_api_service import TapHomeApiService


class ValveState(PercentageState):
    """State representation for a valve."""


class ValveService:
    """Service for valve operations such as opening and closing."""

    def __init__(self, taphome_api_service: TapHomeApiService):
        """Initialize with the TapHome API service."""
        self.taphome_api_service = taphome_api_service
        self.percentage_service = PercentageService(taphome_api_service)
        self.taphome_api_service = taphome_api_service

    async def async_get_state(self, device: Device) -> ValveState:
        """Return ``ValveState`` for ``device``."""
        valve_values = await self.taphome_api_service.async_get_device_values(device.id)
        return ValveState(valve_values)

    def support_set_position(self, device: Device) -> None:
        """Return whether the valve supports setting a position."""
        return self.percentage_service.support_set_position(device)

    def async_turn_on(self, device: Device) -> None:
        """Open the valve."""
        return self.percentage_service.async_turn_on(device)

    def async_turn_off(self, device: Device) -> None:
        """Close the valve."""
        return self.percentage_service.async_turn_off(device)

    def async_set_percentage(self, device: Device, percentage=None) -> None:
        """Set valve opening to ``percentage``."""
        return self.percentage_service.async_set_percentage(device, percentage)
