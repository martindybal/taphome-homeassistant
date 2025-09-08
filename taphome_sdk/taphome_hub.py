"""TapHome Hub handles communication with TapHome Core."""

from asyncio import Task
from datetime import UTC, datetime, timedelta
from enum import Enum
import logging
from typing import NoReturn, TypeVar, cast

from aiohttp.web import Request

from .device import Device
from .device_analog_output import AnalogOutputDevice
from .device_bidirectional import BidirectionalDevice
from .device_digital_output import DigitalOutputDevice
from .device_factory import DeviceFactory
from .device_generic_output_adapter import OutputCapableDevice
from .helpers import set_interval_async
from .observable import ObservableValue
from .taphome_api import (
    DevicesValuesResponse,
    ApiConnectionType,
    DeviceValues,
    Location,
    TapHomeApi,
)

_LOGGER = logging.getLogger(__name__)


class HubConnectionState(Enum):
    """Enum representing the hub connection state."""

    DISCONNECTED = "disconnected"
    CONNECTED = "connected"
    FAILED = "failed"


DeviceT = TypeVar("DeviceT", bound=Device)


class DeviceNotExposedError(Exception):
    """Device is not exposed to TapHome API."""

    def __init__(self, device_id: int) -> None:
        """Initialize the exception with the device ID."""
        self.device_id = device_id
        super().__init__(
            f"Device with ID {device_id} has not been exposed in the TapHome API"
        )


class DeviceTypeError(Exception):
    """Unexpected device type returned for a TapHome device."""

    def __init__(
        self,
        device_id: int,
        device_class_name: str,
        device_type: str,
        supported_values: str,
        expected_device_types: str,
    ) -> None:
        """Initialize the exception with the device ID and types."""
        msg = (
            f"Device with ID {device_id} is type {device_class_name} "
            f"(device_type={device_type}, "
            f"supported_values=[{supported_values}]) not one of: {expected_device_types}"
        )
        super().__init__(msg)
        self.device_id = device_id
        self.device_type = device_type
        self.supported_values = supported_values
        self.expected_device_types = expected_device_types


class TapHomeHub:
    """TapHome Hub connection class."""

    location: Location | None = None
    last_update_success_time: ObservableValue[datetime | None]
    connection_type: ObservableValue[ApiConnectionType]
    connection_state: ObservableValue[HubConnectionState]

    def __init__(
        self,
        api_url: str,
        token: str,
    ) -> None:
        """Initialize the TapHome Hub with an API instance."""
        self.api = TapHomeApi(api_url, token)
        self.last_update_success_time = ObservableValue(None)
        self.connection_state = ObservableValue(HubConnectionState.DISCONNECTED)
        connection_type = (
            ApiConnectionType.CLOUD
            if "taphome.com" in api_url
            else ApiConnectionType.LOCAL
        )
        self.connection_type = ObservableValue(connection_type)

        self.devices: dict[int, Device] = {}
        self.periodic_refresh_task: Task | None = None

    def get_generic_output_capable_device(self, device_id: int) -> OutputCapableDevice:
        """Get a digital output device by its ID."""
        device = self.get_typed_device(
            device_id,
            DigitalOutputDevice,
            AnalogOutputDevice,
            BidirectionalDevice,
        )

        return cast(OutputCapableDevice, device)

    def get_typed_device(self, device_id: int, *device_types: type[DeviceT]) -> DeviceT:
        """Get a device by its ID and ensure it is of the specified type(s)."""
        device = self.devices.get(device_id)

        if device is None:
            raise DeviceNotExposedError(device_id)

        if not isinstance(device, device_types):
            device_class_name = device.__class__.__name__
            expected_device_types = ", ".join(t.__name__ for t in device_types)
            supported_values = ", ".join(
                value_type.name for value_type in device.supported_values
            )
            raise DeviceTypeError(
                device_id,
                device_class_name,
                device.device_type,
                supported_values,
                expected_device_types,
            )

        return device

    async def async_connect(self) -> None:
        """Connect to the TapHome API."""

        try:
            self.location = await self.api.async_get_location()
            discovery = await self.api.async_discovery_devices()
            values = await self.api.async_get_all_devices_values()

            if self.location is None or discovery is None or values is None:
                self._empty_response()

            for metadata in discovery.devices.values():
                device_values = values.devices[metadata.id]
                device = DeviceFactory.create_device(
                    self.api, self.connection_type, metadata, device_values.values
                )
                if device is not None:
                    self.devices[metadata.id] = device

            self._schedule_periodic_refresh()
            self.connection_type.changed += (
                lambda _, __: self._schedule_periodic_refresh()
            )
            self.connection_state.value = HubConnectionState.CONNECTED

        except Exception as e:
            _LOGGER.error("Failed to connect to TapHome API: %s", e)
            raise

    async def async_handle_webhook(self, request: Request) -> None:
        """Handle incoming webhook requests."""
        self.connection_type.value = ApiConnectionType.LOCAL_PUSH
        if self.connection_state.value == HubConnectionState.CONNECTED:
            json = await request.json()
            changed_values = DevicesValuesResponse.from_dict(json)
            self._update_devices_values(changed_values.devices)
        else:
            await self._async_update_all_devices_values()

    def _schedule_periodic_refresh(self) -> None:
        if self.periodic_refresh_task is not None:
            self.periodic_refresh_task.cancel()

        self.periodic_refresh_task = set_interval_async(
            self._async_update_all_devices_values, self._update_interval
        )

    @property
    def _update_interval(self) -> timedelta:
        if self.connection_type.value == ApiConnectionType.LOCAL_PUSH:
            return timedelta(seconds=60)
        if self.connection_type.value == ApiConnectionType.LOCAL:
            return timedelta(seconds=2)
        return timedelta(seconds=20)

    async def _async_update_all_devices_values(
        self,
    ) -> None:
        try:
            values = await self.api.async_get_all_devices_values()
            if values is None:
                self._empty_response()

            self._update_devices_values(values.devices)
            self.connection_state.value = HubConnectionState.CONNECTED
        except Exception:
            _LOGGER.exception(
                "Failed to update TapHome data. Last successful update: %s",
                self.last_update_success_time.value,
            )
            self.connection_state.value = HubConnectionState.FAILED

    def _empty_response(self) -> NoReturn:
        raise ValueError(
            "Empty response from TapHome API. "
            "This may indicate a network issue, invalid API credentials, "
            "or a problem with the TapHome server. "
            "Please check your connection and try again."
        )

    def _update_devices_values(self, values: dict[int, DeviceValues]):
        for device_id, device_values in values.items():
            device = self.devices.get(device_id)
            if device is not None and device_values is not None:
                device.state.apply_changes(device_values.values)

        self.last_update_success_time.value = datetime.now(UTC)


class TapHomeHubFactory:
    """Factory for creating TapHome hub connections."""

    @staticmethod
    async def async_connect(api_url: str, token: str) -> TapHomeHub:
        """Connect to TapHome and return an instance of TapHomeHub."""
        hub = TapHomeHub(api_url, token)

        if hub.connection_type.value == ApiConnectionType.CLOUD:
            _LOGGER.warning(
                "Connecting to TapHome Cloud API. "
                "This may be slow and is not recommended for production use"
            )
        await hub.async_connect()
        return hub
