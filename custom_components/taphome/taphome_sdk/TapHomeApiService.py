import logging
from .Device import Device
from .TapHomeHttpClientFactory import TapHomeHttpClientFactory
from .ValueChangeResult import ValueChangeResult
from .ValueType import ValueType


_LOGGER = logging.getLogger(__name__)


class TapHomeApiService:
    def __init__(self, tapHomeHttpClient: TapHomeHttpClientFactory._TapHomeHttpClient):
        self.tapHomeHttpClient = tapHomeHttpClient

    async def async_discovery_devices(self):
        json = await self.tapHomeHttpClient.async_api_get("discovery")
        try:
            devices = list(map(lambda device: Device.create(device), json["devices"]))
            return devices
        except Exception:
            _LOGGER.exception(f"async_discovery_devices fails \n {json}")

    async def async_get_device_values(self, deviceId: int):
        deviceInfo = None
        try:
            deviceInfo = await self.tapHomeHttpClient.async_api_get(
                f"getDeviceValue/{deviceId}"
            )
            return deviceInfo["values"]
        except Exception:
            _LOGGER.exception(
                f"async_get_device_values for {deviceId} fails \n {deviceInfo}"
            )

    async def async_set_device_values(
        self, deviceId: int, values: list
    ) -> ValueChangeResult:
        json = None
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
        except Exception:
            _LOGGER.exception(f"async_get_device_values for {deviceId} fails \n {json}")
            return ValueChangeResult.FAILED

    def create_device_value(self, valueType: ValueType, value):
        return {
            "valueTypeId": valueType.value,
            "value": value,
        }
