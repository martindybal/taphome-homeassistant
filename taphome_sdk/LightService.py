from .ValueChangeResult import ValueChangeResult
from .ValueType import ValueType
from .SwitchState import SwitchState
from .TapHomeHttpClientFactory import TapHomeHttpClientFactory


class LightService:
    def __init__(self, tapHomeHttpClient: TapHomeHttpClientFactory._TapHomeHttpClient):
        self.tapHomeHttpClient = tapHomeHttpClient

    async def async_get_light_state(self, deviceId: int):

        lightValues = (
            await self.tapHomeHttpClient.async_api_get(f"getDeviceValue/{deviceId}")
        )["values"]

        state = {
            ValueType.SwitchState: SwitchState(
                self.get_light_value(lightValues, ValueType.SwitchState)
            )
        }
        return state

    def get_light_value(self, lightValues: dict, vylueType: ValueType):
        return next(
            lightValue
            for lightValue in lightValues
            if lightValue["valueTypeId"] == vylueType.value
        )["value"]

    def async_turn_on_light(self, lightId: int) -> ValueChangeResult:
        return self.__async_set_light_state(lightId, SwitchState.ON)

    def async_turn_off_light(self, lightId: int) -> ValueChangeResult:
        return self.__async_set_light_state(lightId, SwitchState.OFF)

    async def __async_set_light_state(
        self, lightId: int, state: SwitchState
    ) -> ValueChangeResult:
        try:
            requestBody = {
                "deviceId": lightId,
                "values": [
                    {
                        "valueTypeId": ValueType.SwitchState.value,
                        "value": state.value,
                    }
                ],
            }
            json = await self.tapHomeHttpClient.async_api_post(
                "setDeviceValue", requestBody
            )
            result = json["valuesChanged"][0]["result"]
            return ValueChangeResult.from_string(result)
        except:
            return ValueChangeResult.FAILED