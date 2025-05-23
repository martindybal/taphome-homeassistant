from .device import Device
from .percentage_service import PercentageService, PercentageState
from .taphome_api_service import TapHomeApiService


class ValveState(PercentageState):
    """Valve state."""


class ValveService:
    def __init__(self, taphome_api_service: TapHomeApiService):
        self.taphome_api_service = taphome_api_service
        self.percentage_service = PercentageService(taphome_api_service)
        self.taphome_api_service = taphome_api_service

    async def async_get_state(self, device: Device) -> ValveState:
        valve_values = await self.taphome_api_service.async_get_device_values(
            device.id
        )
        return ValveState(valve_values)

    def support_set_position(self, device: Device) -> None:
        return self.percentage_service.support_set_position(device)

    def async_turn_on(self, device: Device) -> None:
        return self.percentage_service.async_turn_on(device)

    def async_turn_off(self, device: Device) -> None:
        return self.percentage_service.async_turn_off(device)

    def async_set_percentage(self, device: Device, percentage=None) -> None:
        return self.percentage_service.async_set_percentage(device, percentage)
