"""Wrapper for the TapHome HTTP API."""

from __future__ import annotations

from collections.abc import Generator
from dataclasses import dataclass
from enum import Enum
import logging
from typing import TypeVar

import aiohttp
from aiohttp import ClientResponse, ClientResponseError

from .helpers import FromDictProtocol
from .value_type import ValueType

_LOGGER = logging.getLogger(__name__)


ResponseT = TypeVar("ResponseT", bound=FromDictProtocol)


class TapHomeAuthError(Exception):
    """Raised when the TapHome API rejects the token (HTTP 401/403)."""

    def __init__(self, status: int) -> None:
        """Store the HTTP status code."""
        self.status = status
        super().__init__(f"TapHome API rejected the token (HTTP {status})")


class ApiConnectionType(Enum):
    """Enum representing the hub connection type."""

    CLOUD = "cloud"
    LOCAL = "local"
    LOCAL_PUSH = "local_push"


@dataclass(slots=True, frozen=True)
class EnumeratedValue:
    """Describe a allowed value for SupportedValue."""

    value: int
    name: str
    is_enabled: bool

    @classmethod
    def from_dict(cls, data: dict) -> EnumeratedValue:
        """Create EnumeratedValue instance from dictionary."""
        return cls(value=data["value"], name=data["name"], is_enabled=data["isEnabled"])


@dataclass(slots=True, frozen=True)
class SupportedValue:
    """Describe a supported value on a TapHome device."""

    value_type: ValueType
    read_only: bool
    allowed_values: list[EnumeratedValue]
    min_value: int | None
    max_value: int | None

    @classmethod
    def from_dict(cls, data: dict) -> SupportedValue:
        """Create SupportedValue instance from dictionary."""
        return cls(
            value_type=ValueType(data["valueTypeId"]),
            read_only=data["readOnly"],
            allowed_values=[
                EnumeratedValue.from_dict(value)
                for value in data.get("enumeratedValues", [])
            ],
            min_value=data.get("minValue"),
            max_value=data.get("maxValue"),
        )


@dataclass(slots=True)
class DeviceMetadata:
    """Representation of a device connected to TapHome."""

    id: int
    device_type: str
    usage: str | None
    name: str
    description: str
    zone: str | None
    category: str | None
    supported_values: dict[ValueType, SupportedValue]

    @classmethod
    def from_dict(cls, data: dict) -> DeviceMetadata:
        """Create Device instance from dictionary."""
        supported_values: dict[ValueType, SupportedValue] = {}
        for supported_value in data["supportedValues"]:
            try:
                supported_value = SupportedValue.from_dict(supported_value)
                supported_values[supported_value.value_type] = supported_value
            except ValueError:
                _LOGGER.warning("%s is not a valid ValueType", supported_value)

        return DeviceMetadata(
            data["deviceId"],
            data["type"],
            data.get("usage"),
            data["name"],
            data["description"],
            data.get("zone"),
            data.get("category"),
            supported_values,
        )

    def supports_value(self, value_type: ValueType) -> bool:
        """Return ``True`` if ``value_type`` is supported by the device."""
        return self.supports_values(value_type)

    def supports_values(self, *value_types: ValueType) -> bool:
        """Return ``True`` if all of the ``value_types`` are supported by the device."""
        return all(value_type in self.supported_values for value_type in value_types)


@dataclass(slots=True, frozen=True)
class DeviceValue:
    """Represents a single device value."""

    value_type: ValueType
    value: float

    @classmethod
    def from_dict(cls, data: dict) -> DeviceValue:
        """Instantiate ``DeviceValue`` from a dictionary."""
        return DeviceValue(
            value_type=ValueType(data["valueTypeId"]), value=data["value"]
        )


@dataclass(slots=True, frozen=True)
class DeviceValues:
    """Represents values for a single device."""

    device_id: int
    values: dict[ValueType, float]
    error_code: int | None
    message: str | None

    @classmethod
    def from_dict(cls, data: dict) -> DeviceValues:
        """Instantiate ``DeviceValues`` from a dictionary."""

        def _map_values(data) -> Generator[tuple[ValueType, float]]:
            for value_data in data["values"]:
                try:
                    device_value = DeviceValue.from_dict(value_data)
                    yield device_value.value_type, device_value.value
                except ValueError:
                    _LOGGER.warning(
                        "%s is not a valid ValueType", value_data["valueTypeId"]
                    )

        return cls(
            device_id=data["deviceId"],
            values=dict(_map_values(data)),
            error_code=data.get("errorCode"),
            message=data.get("message"),
        )


@dataclass(slots=True, frozen=True)
class Location:
    """Response from location endpoint."""

    location_id: str
    location_name: str
    taphome_api_version: int
    timestamp: int

    @classmethod
    def from_dict(cls, data: dict) -> Location:
        """Instantiate ``LocationResponse`` from a dictionary."""
        return cls(
            location_id=data["locationId"],
            location_name=data["locationName"],
            taphome_api_version=data["tapHomeApiVersion"],
            timestamp=data["timestamp"],
        )


@dataclass(slots=True, frozen=True)
class DiscoveryResponse:
    """Response from getAllDevicesValues endpoint."""

    devices: dict[int, DeviceMetadata]
    timestamp: int

    @classmethod
    def from_dict(cls, data: dict) -> DiscoveryResponse:
        """Instantiate ``AllDevicesValues`` from a dictionary."""

        def _map_devices(
            data,
        ) -> Generator[tuple[int, DeviceMetadata]]:
            for device in data["devices"]:
                try:
                    device_metadata = DeviceMetadata.from_dict(device)
                    yield device_metadata.id, device_metadata
                except Exception:
                    _LOGGER.exception(
                        "TapHome Device.create failed \n %s \n %s", device, data
                    )

        return DiscoveryResponse(
            devices=dict(_map_devices(data)),
            timestamp=data["timestamp"],
        )


@dataclass(slots=True, frozen=True)
class DevicesValuesResponse:
    """Response from getAllDevicesValues endpoint."""

    devices: dict[int, DeviceValues]
    timestamp: int

    @classmethod
    def from_dict(cls, data: dict) -> DevicesValuesResponse:
        """Instantiate ``AllDevicesValues`` from a dictionary."""
        return DevicesValuesResponse(
            devices={
                device.device_id: device
                for device_data in data["devices"]
                if (device := DeviceValues.from_dict(device_data))
            },
            timestamp=data["timestamp"],
        )


class ValueChangeResult(Enum):
    """Possible outcomes of setting a value via the API."""

    CHANGED = 1
    NOT_CHANGED = 2
    FAILED = 3

    @staticmethod
    def from_string(value: str):
        """Map string ``value`` to the corresponding enum member."""
        value = value.upper()
        if value == "CHANGED":
            return ValueChangeResult.CHANGED
        if value in {"NOT_CHANGED", "NOTCHANGED"}:
            return ValueChangeResult.NOT_CHANGED
        if value in {"FAILED"}:
            return ValueChangeResult.FAILED

        _LOGGER.warning("Unknown ChangeStatus value: %s", value)
        return ValueChangeResult.FAILED


class ValueChangeFailedException(Exception):
    """Raised when a value change was not applied by TapHome."""

    def __init__(
        self, device_id: int, values: dict[ValueType, ValueChangeResult]
    ) -> None:
        """Store failing ``device_id`` and ``values`` in the message."""
        self.message = f"Values {values} failed to change for device {device_id}"
        super().__init__(self.message)


@dataclass(slots=True, frozen=True)
class SetDeviceValueResponse:
    """Response from setDeviceValue endpoint."""

    device_id: int
    values_changed: dict[ValueType, ValueChangeResult]
    timestamp: int

    @classmethod
    def from_dict(cls, data: dict) -> SetDeviceValueResponse:
        """Instantiate ``_SetDeviceValueResponse`` from a dictionary."""
        values_changed = {
            ValueType(result["typeId"]): ValueChangeResult.from_string(result["result"])
            for result in data["valuesChanged"]
        }

        return cls(
            device_id=data["deviceId"],
            values_changed=values_changed,
            timestamp=data["timestamp"],
        )


class _TapHomeHttpClient:
    """Internal HTTP client wrapper used by the SDK."""

    def __init__(self, api_url: str, token: str) -> None:
        """Initialize the client with ``api_url`` and ``token``."""
        self.api_url = api_url
        self.token = token

    async def async_api_get(
        self,
        response_class: type[ResponseT],
        endpoint: str,
    ) -> ResponseT | None:
        """Perform GET request on ``endpoint`` and return JSON response."""
        async with aiohttp.ClientSession() as session:
            request_url = self._get_request_url(endpoint)
            _LOGGER.debug("TapHome get %s", request_url)
            headers = self._get_authorization_header()

            async with session.get(request_url, headers=headers) as response:
                return await self._get_from_json(
                    response_class, response, f"GET {endpoint}"
                )

    async def async_api_post(
        self, response_class: type[ResponseT], endpoint: str, body: dict
    ) -> ResponseT | None:
        """Perform POST request on ``endpoint`` with ``body``."""
        async with aiohttp.ClientSession() as session:
            request_url = self._get_request_url(endpoint)
            _LOGGER.debug("TapHome post %s", request_url)
            headers = self._get_authorization_header()
            async with session.post(
                request_url, headers=headers, json=body
            ) as response:
                return await self._get_from_json(
                    response_class, response, f"POST {endpoint}"
                )

    async def _get_from_json(
        self, response_class: type[ResponseT], response: ClientResponse, operation: str
    ) -> ResponseT | None:
        json = None
        try:
            json = await self._read_as_json(response)
            return response_class.from_dict(json)
        except TapHomeAuthError:
            raise
        except Exception:
            _LOGGER.debug(
                "Request %s %s\nstatus %s %s\nheaders %s\ntext %s\n",
                response.url,
                response.request_info.headers,
                response.status,
                response.reason,
                response.headers,
                await response.text(),
            )
            _LOGGER.exception("TapHome request %s failed: %s", operation, json)
            return None

    async def _read_as_json(self, response: ClientResponse):
        if response.status == 200:
            return await response.json()

        if response.status in (401, 403):
            raise TapHomeAuthError(response.status)

        message = response.reason if response.reason else "Unexpected response"
        raise ClientResponseError(
            response.request_info,
            response.history,
            status=response.status,
            message=message,
            headers=response.headers,
        )

    def _get_request_url(self, endpoint: str):
        """Construct request URL for ``endpoint``."""
        return f"{self.api_url}/{endpoint}"

    def _get_authorization_header(self):
        """Return authorization header for HTTP requests."""
        return {"Authorization": f"TapHome {self.token}"}


class TapHomeApi:
    """Provide high level API methods used by integration services."""

    def __init__(self, api_url: str, token: str) -> None:
        """Initialize with the underlying HTTP client."""
        self.taphome_http_client = _TapHomeHttpClient(api_url, token)

    async def async_discovery_devices(self) -> DiscoveryResponse | None:
        """Returns the currently exposed devices under 'Exposed devices', 'TapHome API' in TapHome application."""
        return await self.taphome_http_client.async_api_get(
            DiscoveryResponse, "discovery"
        )

    async def async_get_location(self) -> Location | None:
        """Returns Control unit location info."""
        return await self.taphome_http_client.async_api_get(Location, "location")

    async def async_get_device_values(self, device_id: int) -> DeviceValues | None:
        """Gets all current values for ``device_id`` and their types."""
        return await self.taphome_http_client.async_api_get(
            DeviceValues,
            f"getDeviceValue/{device_id}",
        )

    async def async_get_all_devices_values(self) -> DevicesValuesResponse | None:
        """Return current values for all devices."""
        return await self.taphome_http_client.async_api_get(
            DevicesValuesResponse, "getAllDevicesValues"
        )

    async def async_set_device_value(
        self, device_id: int, value_type: ValueType, value: float
    ) -> SetDeviceValueResponse | None:
        """Set a single ``value_type`` on ``device_id``."""
        return await self.async_set_device_values(
            device_id,
            {value_type: value},
        )

    async def async_set_device_values(
        self, device_id: int, values: dict[ValueType, float]
    ) -> SetDeviceValueResponse | None:
        """Set multiple values on ``device_id`` atomically."""
        request_body = {
            "deviceId": device_id,
            "values": [
                {"valueTypeId": value_type.value, "value": value}
                for value_type, value in values.items()
            ],
        }
        return await self.taphome_http_client.async_api_post(
            SetDeviceValueResponse, "setDeviceValue", request_body
        )
