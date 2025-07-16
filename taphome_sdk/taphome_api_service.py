"""Wrapper for the TapHome HTTP API."""

import logging

from .device import Device
from .location import Location
from .taphome_http_client_factory import TapHomeHttpClientFactory
from .value_change_result import ValueChangeResult
from .value_type import ValueType

_LOGGER = logging.getLogger(__name__)


class TapHomeApiValueFailChangedException(Exception):
    """Raised when a value change was not applied by TapHome."""

    def __init__(self, device_id: int, values: list):
        """Store failing ``device_id`` and ``values`` in the message."""
        self.message = f"Values {values} failed to change for device {device_id}"
        super().__init__(self.message)


class TapHomeApiService:
    """Provide high level API methods used by integration services."""

    def __init__(
        self, taphome_api_service: TapHomeHttpClientFactory._TapHomeHttpClient
    ):
        """Initialize with the underlying HTTP client."""
        self.taphome_api_service = taphome_api_service

    async def async_discovery_devices(self) -> list[Device] | None:
        """Return devices discovered on the TapHome network."""
        json = {}
        try:
            json = await self.taphome_api_service.async_api_get("discovery")
            return self._map_devices(json)

        except Exception:
            _LOGGER.exception(
                "TapHome request async_discovery_devices failed: %s", json
            )
            return None

    def _map_devices(self, json) -> list[Device]:
        """Convert discovery JSON into a list of ``Device`` objects."""
        devices = []
        for device in json["devices"]:
            try:
                devices.append(Device.create(device))
            except Exception:
                _LOGGER.exception(
                    "TapHome Device.create failed \n %s \n %s", device, json
                )
        return devices

    async def async_get_location(self):
        """Fetch the configured TapHome location."""
        json = {}
        try:
            json = await self.taphome_api_service.async_api_get("location")
            return Location.create(json)
        except Exception:
            _LOGGER.exception("TapHome request async_get_location failed: %s", json)

    async def async_get_all_devices_values(self) -> dict | None:
        """Return current values for all devices."""
        device_info = None
        try:
            return await self.taphome_api_service.async_api_get("getAllDevicesValues")
        except Exception:
            _LOGGER.exception(
                "TapHome request async_get_all_devices_values failed: %s", device_info
            )
            return None

    async def async_get_device_values(self, device_id: int) -> dict:
        """Return all values for the given ``device_id``."""
        device_info = None
        try:
            device_info = await self.taphome_api_service.async_api_get(
                f"getDeviceValue/{device_id}"
            )
            return device_info["values"]
        except Exception:
            _LOGGER.exception(
                "TapHome request async_get_device_values failed: %s", device_info
            )
            return {}

    async def async_set_device_value(
        self, device_id: int, value_type: ValueType, value
    ) -> None:
        """Set a single ``value_type`` on ``device_id``."""
        return await self.async_set_device_values(
            device_id,
            [self.create_device_value(value_type, value)],
        )

    async def async_set_device_values(self, device_id: int, values: list) -> None:
        """Set multiple values on ``device_id`` atomically."""
        json = None
        was_values_changed = False

        try:
            request_body = {
                "deviceId": device_id,
                "values": values,
            }
            json = await self.taphome_api_service.async_api_post(
                "setDeviceValue", request_body
            )
            results = json["valuesChanged"]

            if not any(
                result
                for result in results
                if result["result"] == ValueChangeResult.FAILED
            ):
                was_values_changed = True
        except Exception:
            _LOGGER.exception(
                "TapHome async_set_device_values for %s fails %s", device_id, json
            )

        if not was_values_changed:
            raise TapHomeApiValueFailChangedException(device_id, values)

    def create_device_value(self, value_type: ValueType, value) -> dict:
        """Return dictionary for setting ``value_type`` to ``value``."""
        return {
            "ValueTypeId": value_type.value,
            "Value": value,
        }
