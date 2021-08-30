import logging
import typing

from .device import Device
from .location import Location
from .taphome_http_client_factory import TapHomeHttpClientFactory
from .value_change_result import ValueChangeResult
from .value_type import ValueType

_LOGGER = logging.getLogger(__name__)


class TapHomeApiValueFailChangedException(Exception):
    """Exception raised when value fail changed."""

    def __init__(self, device_id: int, values: list):
        self.message = f"Values {values} failed to change for device {device_id}"
        super().__init__(self.message)


class TapHomeApiService:
    def __init__(
        self, taphome_api_service: TapHomeHttpClientFactory._TapHomeHttpClient
    ):
        self.taphome_api_service = taphome_api_service

    async def async_discovery_devices(self) -> typing.List[Device]:
        json = {}
        try:
            json = await self.taphome_api_service.async_api_get("discovery")
            devices = []
            for device in json["devices"]:
                try:
                    devices.append(Device.create(device))
                except Exception:
                    _LOGGER.error(f"TapHome Device.create failed \n {device} \n {json}")
            return devices
        except Exception:
            _LOGGER.error(f"TapHome request async_discovery_devices failed: {json}")

    async def async_get_location(self):
        json = {}
        try:
            json = await self.taphome_api_service.async_api_get("location")
            return Location.create(json)
        except Exception:
            _LOGGER.error(f"TapHome request async_get_location failed: {json}")

    async def async_get_all_devices_values(self) -> dict:
        deviceInfo = None
        try:
            return await self.taphome_api_service.async_api_get("getAllDevicesValues")
        except Exception as ex:
            if hasattr(ex, "status") and ex.status == 501:
                _LOGGER.error(
                    f"TapHome request failed: Request not supported by core! Please update your core to 2021.2 or newer"
                )
                raise
            _LOGGER.error(
                f"TapHome request async_get_all_devices_values failed:{deviceInfo}"
            )
            return None

    async def async_get_device_values(self, device_id: int) -> dict:
        deviceInfo = None
        try:
            deviceInfo = await self.taphome_api_service.async_api_get(
                f"getDeviceValue/{device_id}"
            )
            return deviceInfo["values"]
        except Exception:
            _LOGGER.error(
                f"TapHome request async_get_device_values failed: {deviceInfo}"
            )
            return None

    async def async_set_device_values(self, device_id: int, values: list) -> None:
        json = None
        was_values_changed = False

        try:
            requestBody = {
                "deviceId": device_id,
                "values": values,
            }
            json = await self.taphome_api_service.async_api_post(
                "setDeviceValue", requestBody
            )
            results = json["valuesChanged"]

            if not any(
                result
                for result in results
                if result["result"] == ValueChangeResult.FAILED
            ):
                was_values_changed = True
        except Exception:
            _LOGGER.error(f"async_set_device_values for {device_id} fails {json}")

        if not was_values_changed:
            raise TapHomeApiValueFailChangedException(device_id, values)

    def create_device_value(self, value_type: ValueType, value) -> dict:
        return {
            "ValueTypeId": value_type.value,
            "Value": value,
        }
