from .Device import Device
from .ValueChangeResult import ValueChangeResult
from .ValueType import ValueType
from .SwitchStates import SwitchStates
from .TapHomeApiService import TapHomeApiService
from .DeviceServiceHelper import __DeviceServiceHelper as DeviceServiceHelper


class LightState:
    def __init__(
        self,
        switch_state: SwitchStates,
        brightness: float,
        hue: float,
        saturation: float,
    ):
        self._switch_state = switch_state
        self._brightness = brightness
        self._hue = hue
        self._saturation = saturation

    @property
    def switch_state(self):
        return self._switch_state

    @property
    def brightness(self):
        return self._brightness

    @property
    def hue(self):
        return self._hue

    @property
    def saturation(self):
        return self._saturation


class LightService:
    def __init__(self, tapHomeApiService: TapHomeApiService):
        self.tapHomeApiService = tapHomeApiService

    async def async_get_light_state(self, device: Device):
        lightValues = await self.tapHomeApiService.async_get_device_values(
            device.deviceId
        )
        switch_state = SwitchStates(
            DeviceServiceHelper.get_device_value(lightValues, ValueType.SwitchState)
        )

        brightness = None
        if ValueType.AnalogOutputValue in device.supportedValues:
            brightness = DeviceServiceHelper.get_device_value(
                lightValues, ValueType.AnalogOutputValue
            )
        else:
            brightness = DeviceServiceHelper.get_device_value(
                lightValues, ValueType.HueBrightness
            )

        hue = DeviceServiceHelper.get_device_value(lightValues, ValueType.HueDegrees)
        saturation = DeviceServiceHelper.get_device_value(
            lightValues, ValueType.Saturation
        )

        return LightState(switch_state, brightness, hue, saturation)

    def async_turn_on_light(
        self, device: Device, brightness=None, hue=None, saturation=None
    ) -> ValueChangeResult:
        values = [
            self.tapHomeApiService.create_device_value(
                ValueType.SwitchState, SwitchStates.ON.value
            )
        ]

        if brightness is not None:
            if ValueType.AnalogOutputValue in device.supportedValues:
                values.append(
                    self.tapHomeApiService.create_device_value(
                        ValueType.AnalogOutputValue, brightness
                    )
                )
            else:
                values.append(
                    self.tapHomeApiService.create_device_value(
                        ValueType.HueBrightness, brightness
                    )
                )

        if hue is not None:
            values.append(
                self.tapHomeApiService.create_device_value(ValueType.HueDegrees, hue)
            )

        if saturation is not None:
            values.append(
                self.tapHomeApiService.create_device_value(
                    ValueType.Saturation, saturation
                )
            )

        return self.tapHomeApiService.async_set_device_values(device.deviceId, values)

    def async_turn_off_light(self, device: Device) -> ValueChangeResult:
        values = [
            self.tapHomeApiService.create_device_value(
                ValueType.SwitchState, SwitchStates.OFF.value
            )
        ]
        return self.tapHomeApiService.async_set_device_values(device.deviceId, values)