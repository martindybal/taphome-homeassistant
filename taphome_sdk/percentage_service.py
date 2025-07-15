"""Generic percentage based services for various TapHome devices."""

from .device import Device
from .switch_service import SwitchService
from .switch_states import SwitchStates
from .taphome_api_service import TapHomeApiService
from .taphome_device_state import TapHomeState
from .value_type import ValueType


class PercentageState(TapHomeState):
    """Base state describing percentage capable devices."""

    def __init__(
        self,
        percentage_values: dict,
    ):
        """Create state from ``percentage_values`` dict."""
        super().__init__(percentage_values)
        if self.get_device_value(ValueType.AnalogOutputValue) is not None:
            self.create_analog_state()
        elif self.get_device_value(ValueType.BlindsLevel) is not None:
            self.create_blind_state()
        elif self.get_device_value(ValueType.SwitchState) is not None:
            self.create_switch_state()

    def create_analog_state(self) -> None:
        """Initialize analog output related attributes."""
        self.percentage = self.get_device_value(ValueType.AnalogOutputValue)
        self.switch_state = SwitchStates(self.get_device_value(ValueType.SwitchState))

    def create_blind_state(self) -> None:
        """Initialize blind related attributes."""
        self.percentage = self.get_device_value(ValueType.BlindsLevel)
        switch_state = self.percentage != 0
        self.switch_state = SwitchStates(switch_state)

    def create_switch_state(self) -> None:
        """Initialize switch related attributes."""
        self.switch_state = SwitchStates(self.get_device_value(ValueType.SwitchState))
        self.percentage = 1 if self.switch_state == SwitchStates.ON else 0


class PercentageService:
    """Common service logic for percentage capable devices."""

    def __init__(self, taphome_api_service: TapHomeApiService):
        """Initialize with the API service and helper services."""
        self.taphome_api_service = taphome_api_service
        self.analog_percentage_service = AnalogPercentageService(taphome_api_service)
        self.blind_percentage_service = BlindPercentageService(taphome_api_service)
        self.switch_percentage_service = SwitchPercentageService(taphome_api_service)

    async def async_get_state(self, device: Device) -> PercentageState:
        """Return ``PercentageState`` for ``device``."""
        percentage_values = await self.taphome_api_service.async_get_device_values(
            device.id
        )
        return PercentageState(percentage_values)

    def support_set_position(self, device: Device) -> None:
        """Return helper's ``support_set_position`` implementation."""
        percentage_service = self._get_percentage_service(device)
        return percentage_service.support_set_position

    def async_turn_on(self, device: Device) -> None:
        """Turn ``device`` on using underlying helper."""
        percentage_service = self._get_percentage_service(device)
        return percentage_service.async_turn_on(device)

    def async_turn_off(self, device: Device) -> None:
        """Turn ``device`` off using underlying helper."""
        percentage_service = self._get_percentage_service(device)
        return percentage_service.async_turn_off(device)

    def async_set_percentage(self, device: Device, percentage=None) -> None:
        """Set ``device`` to ``percentage`` using helper service."""
        percentage_service = self._get_percentage_service(device)
        return percentage_service.async_set_percentage(device, percentage)

    def _get_percentage_service(self, device: Device) -> None:
        """Select helper service based on ``device`` capabilities."""
        if device.supports_value(ValueType.AnalogOutputDesiredValue):
            return self.analog_percentage_service
        if device.supports_value(ValueType.BlindsLevel):
            return self.blind_percentage_service
        if device.supports_value(ValueType.SwitchState):
            return self.switch_percentage_service
        return None


class AnalogPercentageService:
    """Handle percentage devices controlled via analog values."""

    def __init__(self, taphome_api_service: TapHomeApiService):
        """Initialize with TapHome API service."""
        self.taphome_api_service = taphome_api_service

    @property
    def support_set_position(self):
        """Return ``True`` as analog devices support positioning."""
        return True

    def async_turn_on(self, device: Device) -> None:
        """Turn ``device`` on."""
        values = [
            self.taphome_api_service.create_device_value(
                ValueType.SwitchState, SwitchStates.ON.value
            )
        ]
        return self.taphome_api_service.async_set_device_values(device.id, values)

    def async_turn_off(self, device: Device) -> None:
        """Turn ``device`` off."""
        values = [
            self.taphome_api_service.create_device_value(
                ValueType.SwitchState, SwitchStates.OFF.value
            )
        ]
        return self.taphome_api_service.async_set_device_values(device.id, values)

    def async_set_percentage(self, device: Device, percentage=None) -> None:
        """Set ``device`` to ``percentage``."""
        if percentage == 0:
            return self.async_turn_off(device)
        values = [
            self.taphome_api_service.create_device_value(
                ValueType.SwitchState, SwitchStates.ON.value
            ),
            self.taphome_api_service.create_device_value(
                ValueType.AnalogOutputDesiredValue, percentage
            ),
        ]

        return self.taphome_api_service.async_set_device_values(device.id, values)


class BlindPercentageService:
    """Handle percentage for blind type devices."""

    def __init__(self, taphome_api_service: TapHomeApiService):
        """Initialize with TapHome API service."""
        self.taphome_api_service = taphome_api_service

    @property
    def support_set_position(self):
        """Return ``True`` since blinds support positioning."""
        return True

    def async_turn_on(self, device: Device) -> None:
        """Open blinds fully."""
        return self.async_set_percentage(device, 1)

    def async_turn_off(self, device: Device) -> None:
        """Close blinds."""
        return self.async_set_percentage(device, 0)

    def async_set_percentage(self, device: Device, percentage=None) -> None:
        """Set blind position to ``percentage``."""
        values = [
            self.taphome_api_service.create_device_value(
                ValueType.BlindsLevel, percentage
            ),
        ]

        return self.taphome_api_service.async_set_device_values(device.id, values)


class SwitchPercentageService:
    """Handle percentage for on/off style switches."""

    def __init__(self, taphome_api_service: TapHomeApiService):
        """Initialize service with TapHome API."""
        self.switch_service = SwitchService(taphome_api_service)

    @property
    def support_set_position(self):
        """Return ``False`` as switches don't support positioning."""
        return False

    def async_turn_on(self, device: Device) -> None:
        """Turn ``device`` on."""
        return self.switch_service.async_turn(SwitchStates.ON, device)

    def async_turn_off(self, device: Device) -> None:
        """Turn ``device`` off."""
        return self.switch_service.async_turn(SwitchStates.OFF, device)

    def async_set_percentage(self, device: Device, percentage=None) -> None:
        """Change switch state based on ``percentage`` value."""
        if percentage == 0:
            return self.async_turn_off(device)
        return self.async_turn_on(device)
