import aiohttp


class TapHomeHttpClientFactory:
    class _TapHomeHttpClient:
        def __init__(self, token: str):
            self.apiUrl = "https://cloudapi.taphome.com/api/CloudApi/v1"
            self.token = token

        async def async_api_get(self, endpoint: str):
            async with aiohttp.ClientSession() as session:
                requestUrl = self.__get_request_url(endpoint)
                headers = self.__get_authorization_header()
                async with session.get(requestUrl, headers=headers) as response:
                    return await response.json()

        async def async_api_post(self, endpoint: str, body):
            async with aiohttp.ClientSession() as session:
                requestUrl = self.__get_request_url(endpoint)
                headers = self.__get_authorization_header()
                async with session.post(
                    requestUrl, headers=headers, json=body
                ) as response:
                    return await response.json()

        def __get_request_url(self, endpoint: str):
            return f"{self.apiUrl}/{endpoint}"

        def __get_authorization_header(self):
            return {"Authorization": f"TapHome {self.token}"}

    def create(self, token: str):
        return TapHomeHttpClientFactory._TapHomeHttpClient(token)


class TapHome:
    from enum import Enum

    class ValueChangeResult(Enum):
        CHANGED = 1
        NOT_CHANGED = 2
        FAILED = 3

        @staticmethod
        def from_string(value: str):
            return {
                "CHANGED": TapHome.ValueChangeResult.CHANGED,
                "NOT_CHANGED": TapHome.ValueChangeResult.NOT_CHANGED,
                "NOTCHANGED": TapHome.ValueChangeResult.NOT_CHANGED,
                "FAILED": TapHome.ValueChangeResult.FAILED,
            }[value.upper()]

    class SwitchState(Enum):
        OFF = 0
        ON = 1

    class ValueType(Enum):
        SwitchState = 48

    def __init__(self, tapHomeHttpClient: TapHomeHttpClientFactory._TapHomeHttpClient):
        self.tapHomeHttpClient = tapHomeHttpClient

    async def async_discovery_devices(self):
        json = await self.tapHomeHttpClient.async_api_get("discovery")
        return json

    async def async_get_device_value(self, deviceId: int):
        json = await self.tapHomeHttpClient.async_api_get(f"getDeviceValue/{deviceId}")
        return json

    def async_turn_on_light(self, lightId: int) -> ValueChangeResult:
        return self.__async_set_light_state(lightId, TapHome.SwitchState.ON)

    def async_turn_off_light(self, lightId: int) -> ValueChangeResult:
        return self.__async_set_light_state(lightId, TapHome.SwitchState.OFF)

    async def __async_set_light_state(
        self, lightId: int, state: SwitchState
    ) -> ValueChangeResult:
        try:
            requestBody = {
                "deviceId": lightId,
                "values": [
                    {
                        "valueTypeId": TapHome.ValueType.SwitchState.value,
                        "value": state.value,
                    }
                ],
            }
            json = await self.tapHomeHttpClient.async_api_post(
                "setDeviceValue", requestBody
            )
            result = json["valuesChanged"][0]["result"]
            return TapHome.ValueChangeResult.from_string(result)
        except:
            print(json)
            return TapHome.ValueChangeResult.FAILED