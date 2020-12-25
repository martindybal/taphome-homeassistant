from .Device import Device
from .TapHomeHttpClientFactory import TapHomeHttpClientFactory
from .ValueChangeResult import ValueChangeResult
from .ValueType import ValueType
from .SwitchStates import SwitchStates

import sys


class TapHomeApiService:
    def __init__(self, tapHomeHttpClient: TapHomeHttpClientFactory._TapHomeHttpClient):
        self.tapHomeHttpClient = tapHomeHttpClient

    async def async_discovery_devices(self):
        json = await self.tapHomeHttpClient.async_api_get("discovery")
        devices = list(map(lambda device: Device.create(device), json["devices"]))

        return devices

    async def async_get_device_values(self, deviceId: int):
        deviceInfo = await self.tapHomeHttpClient.async_api_get(
            f"getDeviceValue/{deviceId}"
        )
        return deviceInfo["values"]

    async def async_set_device_values(
        self, deviceId: int, values: list
    ) -> ValueChangeResult:
        try:
            requestBody = {
                "deviceId": deviceId,
                "values": values,
            }
            json = await self.tapHomeHttpClient.async_api_post(
                "setDeviceValue", requestBody
            )
            results = json["valuesChanged"]

            return (
                ValueChangeResult.FAILED
                if any(
                    (
                        result
                        for result in results
                        if result["result"] == ValueChangeResult.FAILED
                    )
                )
                else ValueChangeResult.CHANGED
            )
        except:
            return ValueChangeResult.FAILED

    def create_device_value(self, valueType: ValueType, value):
        return {
            "valueTypeId": valueType.value,
            "value": value,
        }
