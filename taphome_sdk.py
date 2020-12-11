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
        SensorBrightness = 2
        DeviceStatus = 7
        BlindsSlope = 10
        ButtonHeldState = 38
        HueDegrees = 40
        Saturation = 41
        AnalogOutputValue = 42
        BlindsLevel = 46
        SwitchState = 48
        MultiValueSwitchState = 49
        ButtonPressed = 52
        AnalogOutputDesiredValue = 67
        MultiValueSwitchDesiredState = 71
        HueBrightness = 65
        BlindsIsMoving = 66
        HueBrightnessDesiredValue = 68

    class TapHomeDevice:
        def __init__(
            self,
            deviceId: int,
            name: str,
            description: str,
            type: str,
            supportedValues: list,
        ):
            self._deviceId = deviceId
            self._name = name
            self._description = description
            self._type = type
            self._supportedValues = supportedValues

        @staticmethod
        def create(device: dict):
            deviceId = device["deviceId"]
            name = device["name"]
            description = device["description"]
            type = device["type"]
            supportedValues = list(
                map(
                    lambda supportedValue: TapHome.ValueType(
                        supportedValue["valueTypeId"]
                    ),
                    device["supportedValues"],
                )
            )

            return TapHome.TapHomeDevice(
                deviceId, name, description, type, supportedValues
            )

        @property
        def deviceId(self):
            return self._deviceId

        @property
        def name(self):
            return self._name

        @property
        def description(self):
            return self._description

        @property
        def type(self):
            return self._type

        @property
        def supportedValues(self):
            return self._supportedValues

    def __init__(self, tapHomeHttpClient: TapHomeHttpClientFactory._TapHomeHttpClient):
        self.tapHomeHttpClient = tapHomeHttpClient

    async def async_discovery_devices(self):
        json = await self.tapHomeHttpClient.async_api_get("discovery")
        devices = list(
            map(lambda device: TapHome.TapHomeDevice.create(device), json["devices"])
        )

        return devices

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
            return TapHome.ValueChangeResult.FAILED