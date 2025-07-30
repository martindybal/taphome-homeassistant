"""Helper for controlling simple on/off switches."""

import logging

from .device import Device
from .switch_states import SwitchStates
from .taphome_api_service import TapHomeApiService
from .taphome_device_state import TapHomeState
from .value_type import ValueType

_LOGGER = logging.getLogger(__name__)


class SwitchState(TapHomeState):
    """State representation for a switch device."""

    def __init__(
        self,
        switch_values: dict,
    ):
        """Create state from ``switch_values``."""
        super().__init__(switch_values)
        self.switch_state = self.get_device_enum_value(
            SwitchStates, ValueType.SWITCH_STATE
        )


class SwitchService:
    """Service for operating simple switches."""

    def __init__(self, taphome_api_service: TapHomeApiService):
        """Initialize with the TapHome API service."""
        self.taphome_api_service = taphome_api_service

    async def async_get_state(self, device: Device):
        """Return ``SwitchState`` for ``device`` if available."""
        try:
            switch_values = await self.taphome_api_service.async_get_device_values(
                device.id
            )

            if switch_values is None:
                return None

            return SwitchState(switch_values)
        except Exception:
            _LOGGER.exception("TapHome async_get_state for %s failed", device.id)
            return None

    async def async_turn(self, switch_state: SwitchStates, device: Device) -> None:
        """Set ``device`` to the provided ``switch_state``."""
        values = [
            self.taphome_api_service.create_device_value(
                ValueType.SWITCH_STATE, switch_state.value
            )
        ]

        await self.taphome_api_service.async_set_device_values(device.id, values)
