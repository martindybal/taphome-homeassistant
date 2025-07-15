"""Control humidifiers managed by TapHome."""

from .device import Device
from .percentage_service import PercentageService, PercentageState
from .taphome_api_service import TapHomeApiService


class HumidifierState(PercentageState):
    """State representation for a humidifier device."""


class HumidifierService:
    """Service methods to operate TapHome humidifiers."""

    def __init__(self, taphome_api_service: TapHomeApiService):
        """Initialize with the TapHome API service."""
        self.taphome_api_service = taphome_api_service
        self.percentage_service = PercentageService(taphome_api_service)
        self.taphome_api_service = taphome_api_service

    async def async_get_state(self, device: Device) -> HumidifierState:
        """Return ``HumidifierState`` for ``device``."""
        humidifier_values = await self.taphome_api_service.async_get_device_values(
            device.id
        )
        return HumidifierState(humidifier_values)

    def async_turn_on(self, device: Device) -> None:
        """Turn ``device`` on."""
        return self.percentage_service.async_turn_on(device)

    def async_turn_off(self, device: Device) -> None:
        """Turn ``device`` off."""
        return self.percentage_service.async_turn_off(device)

    def async_set_humidity(self, device: Device, humidity=None) -> None:
        """Set desired humidity ``percentage`` on ``device``."""
        return self.percentage_service.async_set_percentage(device, humidity)
