"""Support for multi-value switch devices."""

import logging

from .device import Device
from .taphome_api_service import TapHomeApiService
from .taphome_device_state import TapHomeState
from .value_change_result import ValueChangeResult
from .value_type import ValueType

_LOGGER = logging.getLogger(__name__)


class MultiValueSwitchState(TapHomeState):
    """State representation for a multi-value switch."""

    def __init__(
        self,
        multi_value_switch_values: dict,
    ):
        """Create state from ``multi_value_switch_values``."""
        super().__init__(multi_value_switch_values)
        self.multi_value_switch_state: int = self.get_device_value(
            ValueType.MultiValueSwitchState
        )


class MultiValueSwitchService:
    """Operate multi-value switches via TapHome."""

    def __init__(self, taphome_api_service: TapHomeApiService):
        """Initialize with the TapHome API service."""
        self.taphome_api_service = taphome_api_service

    async def async_get_state(self, device: Device) -> MultiValueSwitchState:
        """Return ``MultiValueSwitchState`` for ``device``."""
        try:
            multi_value_switch_values = (
                await self.taphome_api_service.async_get_device_values(device.id)
            )
            return MultiValueSwitchState(multi_value_switch_values)
        except Exception:
            _LOGGER.exception("TapHome async_get_state for %s failed", device.id)
            return None

    def async_set_value(self, value: int, device: Device) -> ValueChangeResult:
        """Set ``device`` to ``value`` and return the change result."""
        values = [
            self.taphome_api_service.create_device_value(
                ValueType.MultiValueSwitchState, value
            )
        ]

        return self.taphome_api_service.async_set_device_values(device.id, values)
