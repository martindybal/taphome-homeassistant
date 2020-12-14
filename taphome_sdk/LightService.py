from .ValueChangeResult import ValueChangeResult
from .ValueType import ValueType
from .SwitchState import SwitchState
from .TapHomeApiService import TapHomeApiService
from .DeviceServiceHelper import __DeviceServiceHelper as DeviceServiceHelper


class LightState:
    def __init__(
        self, switch_state: SwitchState, brightness: float, hue: int, saturation: int
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

    async def async_get_light_state(self, deviceId: int):
        lightValues = await self.tapHomeApiService.async_get_device_values(deviceId)
        print(lightValues)
        switch_state = SwitchState(
            DeviceServiceHelper.get_device_value(lightValues, ValueType.SwitchState)
        )

        brightness = DeviceServiceHelper.get_device_value(
            lightValues, ValueType.HueBrightness
        )
        hue = DeviceServiceHelper.get_device_value(lightValues, ValueType.HueDegrees)
        saturation = DeviceServiceHelper.get_device_value(
            lightValues, ValueType.Saturation
        )

        return LightState(switch_state, brightness, hue, saturation)

    def async_turn_on_light(
        self, lightId: int, brightness=None, hue=None, saturation=None
    ) -> ValueChangeResult:
        values = [
            self.tapHomeApiService.create_device_value(
                ValueType.SwitchState, SwitchState.ON.value
            )
        ]

        if brightness is not None:
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

        return self.tapHomeApiService.async_set_device_values(lightId, values)

    def async_turn_off_light(self, lightId: int) -> ValueChangeResult:
        values = [
            self.tapHomeApiService.create_device_value(
                ValueType.SwitchState, SwitchState.OFF.value
            )
        ]
        return self.tapHomeApiService.async_set_device_values(lightId, values)