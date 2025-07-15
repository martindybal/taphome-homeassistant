"""Fan device handling for the TapHome integration."""

from .device import Device
from .percentage_service import PercentageService, PercentageState
from .taphome_api_service import TapHomeApiService


class FanState(PercentageState):
    """State representation for a fan device."""


class FanService:
    """Service methods to operate TapHome fans."""

    def __init__(self, taphome_api_service: TapHomeApiService):
        """Initialize with the API service instance."""
        self.taphome_api_service = taphome_api_service
        self.percentage_service = PercentageService(taphome_api_service)
        self.taphome_api_service = taphome_api_service

    async def async_get_state(self, device: Device) -> FanState:
        """Return ``FanState`` for ``device``."""
        fan_values = await self.taphome_api_service.async_get_device_values(device.id)
        return FanState(fan_values)

    def async_turn_on(self, device: Device) -> None:
        """Turn ``device`` on."""
        return self.percentage_service.async_turn_on(device)

    def async_turn_off(self, device: Device) -> None:
        """Turn ``device`` off."""
        return self.percentage_service.async_turn_off(device)

    def async_set_percentage(self, device: Device, percentage=None) -> None:
        """Set fan ``device`` speed to ``percentage``."""
        return self.percentage_service.async_set_percentage(device, percentage)
