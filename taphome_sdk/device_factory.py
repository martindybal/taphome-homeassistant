"""Factory for creating TapHome devices."""

import logging

from .device import Device, DeviceMetadata, DeviceState, ValueType
from .device_analog_output import AnalogOutputDevice, AnalogOutputState
from .device_bidirectional import BidirectionalDevice, BidirectionalDeviceState
from .device_button import ButtonDevice, ButtonState
from .device_digital_output import DigitalOutputDevice, DigitalOutputState
from .device_light import (
    DualWhiteLightDevice,
    DualWhiteLightState,
    RGBLightDevice,
    RGBLightState,
)
from .device_multivalue_switch import MultiValueSwitchDevice, MultiValueSwitchState
from .device_thermostat import ThermostatDevice, ThermostatState
from .device_variable import (
    SessionDurationVariableDevice,
    SessionDurationVariableState,
    VariableDevice,
    VariableState,
)
from .observable import ObservableValue
from .taphome_api import ApiConnectionType, TapHomeApi

_LOGGER = logging.getLogger(__name__)


class DeviceFactory:
    """Factory for creating TapHome devices."""

    @staticmethod
    def create_device(
        api: TapHomeApi,
        connection_type: ObservableValue[ApiConnectionType],
        metadata: DeviceMetadata,
        device_values: dict[ValueType, float],
    ) -> Device | None:
        """Create a Device."""

        if metadata.supports_value(ValueType.BLINDS_LEVEL):
            return BidirectionalDevice.create(
                api=api,
                connection_type=connection_type,
                metadata=metadata,
                device_values=device_values,
                state_type=BidirectionalDeviceState,
            )

        if metadata.supports_values(ValueType.TEMPERATURE_SET_POINT):
            return ThermostatDevice.create(
                api=api,
                connection_type=connection_type,
                metadata=metadata,
                device_values=device_values,
                state_type=ThermostatState,
            )

        if metadata.supports_values(
            ValueType.ANALOG_OUTPUT_VALUE, ValueType.ANALOG_OUTPUT_DESIRED_VALUE
        ):
            return AnalogOutputDevice.create(
                api=api,
                connection_type=connection_type,
                metadata=metadata,
                device_values=device_values,
                state_type=AnalogOutputState,
            )

        if metadata.supports_values(
            ValueType.HUE_BRIGHTNESS, ValueType.HUE_DEGREES, ValueType.SATURATION
        ):
            return RGBLightDevice.create(
                api=api,
                connection_type=connection_type,
                metadata=metadata,
                device_values=device_values,
                state_type=RGBLightState,
            )

        if metadata.supports_values(
            ValueType.HUE_BRIGHTNESS, ValueType.CORRELATED_COLOR_TEMPERATURE
        ):
            return DualWhiteLightDevice.create(
                api=api,
                connection_type=connection_type,
                metadata=metadata,
                device_values=device_values,
                state_type=DualWhiteLightState,
            )

        if metadata.supports_values(
            ValueType.MULTI_VALUE_SWITCH_STATE,
            ValueType.MULTI_VALUE_SWITCH_DESIRED_STATE,
        ):
            return MultiValueSwitchDevice.create(
                api=api,
                connection_type=connection_type,
                metadata=metadata,
                device_values=device_values,
                state_type=MultiValueSwitchState,
            )

        if metadata.supports_value(ValueType.SWITCH_STATE):
            return DigitalOutputDevice.create(
                api=api,
                connection_type=connection_type,
                metadata=metadata,
                device_values=device_values,
                state_type=DigitalOutputState,
            )

        if metadata.supports_values(
            ValueType.VARIABLE_STATE, ValueType.SESSION_DURATION
        ):
            return SessionDurationVariableDevice.create(
                api=api,
                connection_type=connection_type,
                metadata=metadata,
                device_values=device_values,
                state_type=SessionDurationVariableState,
            )

        if metadata.supports_value(ValueType.VARIABLE_STATE):
            return VariableDevice.create(
                api=api,
                connection_type=connection_type,
                metadata=metadata,
                device_values=device_values,
                state_type=VariableState,
            )

        if metadata.supports_values(ValueType.BUTTON_PRESSED):
            return ButtonDevice.create(
                api=api,
                connection_type=connection_type,
                metadata=metadata,
                device_values=device_values,
                state_type=ButtonState,
            )

        return Device.create(
            api=api,
            connection_type=connection_type,
            metadata=metadata,
            device_values=device_values,
            state_type=DeviceState,
        )
