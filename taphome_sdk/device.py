"""Models TapHome devices and supported value types."""

from __future__ import annotations

from dataclasses import dataclass, field
import logging
from typing import Generic, Self, TypeVar, cast

from .helpers import EnumT
from .observable import Event, ObservableValue
from .operation_mode import OperationMode
from .taphome_api import (
    ApiConnectionType,
    DeviceMetadata,
    SetDeviceValueResponse,
    TapHomeApi,
    ValueChangeFailedException,
    ValueChangeResult,
)
from .value_type import ValueType

_LOGGER = logging.getLogger(__name__)


@dataclass(slots=True)
class DeviceState:
    """Protocol for classes that can be created from dict."""

    _device_values: dict[ValueType, float]
    operation_mode: OperationMode | None = None
    _changed: Event[Self | None, Self] = field(default_factory=Event[Self | None, Self])

    @property
    def changed(self) -> Event[Self | None, Self]:
        """Return the event that is triggered when the state changes."""
        return self._changed

    @changed.setter
    def changed(
        self,
        value: Event[Self | None, Self],
    ) -> None:
        self._changed = value

    def __post_init__(self) -> None:
        """Initialize the device state."""
        self.apply_changes(self._device_values, False, True)

    @classmethod
    def from_dict(cls, data: dict[ValueType, float]) -> Self:
        """Instantiate ``DeviceState`` from a dictionary."""
        return cls(_device_values=data)

    def apply_changes(
        self, values: dict[ValueType, float], force: bool = False, initial: bool = False
    ) -> None:
        """Apply changes to the device state based on provided values."""
        updated = self.should_update(values)
        if initial or updated or force:
            old_state = None if initial else self.clone()
            self._device_values.update(values)
            self.device_values_changed(initial)
            self.operation_mode = self.get_device_enum_value(
                OperationMode, ValueType.OPERATION_MODE
            )
            self._changed(cast(Self | None, old_state), cast(Self, self))

    def should_update(self, values):
        """Check if the device state should be updated."""
        return self._device_values != values

    def clone(self) -> Self:
        """Return a copy of the current state."""
        return self.from_dict(self._device_values)

    def device_values_changed(self, initial: bool) -> None:
        """Update state attributes when device values change."""

    def get_device_enum_value(
        self, enum_type: type[EnumT], value_type: ValueType, supress_warning=False
    ) -> EnumT | None:
        """Return enum value for ``value_type`` or None."""
        value = self.get_device_value(value_type)
        try:
            return enum_type(value)
        except (ValueError, TypeError):
            if not supress_warning:
                _LOGGER.warning(
                    "Failed to create enum %s with value %s",
                    enum_type.__name__,
                    value,
                )
            return None

    def get_device_bool_value(self, value_type: ValueType) -> bool | None:
        """Return True if ``value_type`` is 1, False if 0, None if not available."""
        return self.get_device_value(value_type) == 1

    def get_device_int_value(self, value_type: ValueType) -> int | None:
        """Return integer representation of ``value_type`` or None."""
        value = self.get_device_value(value_type)
        try:
            if value is None:
                return None
            return int(value)
        except (TypeError, ValueError):
            return None

    def get_device_value(self, value_type: ValueType) -> float | None:
        """Return value for ``value_type`` if available."""
        value = self._device_values.get(value_type)
        return value if value != "NaN" else None


StateT = TypeVar("StateT", bound=DeviceState)


@dataclass(slots=True)
class Device(DeviceMetadata, Generic[StateT]):
    """Representation of a TapHome device with its metadata and values."""

    _api: TapHomeApi
    _connection_type: ObservableValue[ApiConnectionType]
    _state: StateT

    @property
    def state(self) -> StateT:
        """Return the current state of the device."""
        return self._state

    @classmethod
    def create(
        cls,
        api: TapHomeApi,
        connection_type: ObservableValue[ApiConnectionType],
        metadata: DeviceMetadata,
        device_values: dict[ValueType, float],
        state_type: type[StateT],
    ) -> Self:
        """Create Device."""
        return cls(
            _api=api,
            _connection_type=connection_type,
            id=metadata.id,
            device_type=metadata.device_type,
            usage=metadata.usage,
            name=metadata.name,
            description=metadata.description,
            zone=metadata.zone,
            category=metadata.category,
            supported_values=metadata.supported_values,
            _state=state_type.from_dict(device_values),
        )

    async def async_set_device_value(
        self, value_type: ValueType, value: float | None
    ) -> None:
        """Set a single ``value_type`` on ``device_id``."""
        return await self.async_set_device_values(
            {value_type: value},
        )

    async def async_set_device_values(
        self, values: dict[ValueType, float | None]
    ) -> None:
        """Set multiple values on ``device_id`` atomically."""
        values_without_none = {k: v for k, v in values.items() if v is not None}
        result = await self._api.async_set_device_values(self.id, values_without_none)
        if result is None:
            _LOGGER.error("Failed to set device values for %s", self.id)
            return
        if not self.was_values_changed(result):
            await self._async_reload_values(True)
            raise ValueChangeFailedException(result.device_id, result.values_changed)

        if self._connection_type.value != ApiConnectionType.LOCAL_PUSH:
            await self._async_reload_values()

    def was_values_changed(self, result: SetDeviceValueResponse) -> bool:
        """Ensure that values were changed successfully."""
        if result is None or any(
            value_changed == ValueChangeResult.FAILED
            for value_changed in result.values_changed.values()
        ):
            return False
        return True

    async def _async_reload_values(self, force: bool = False) -> None:
        device_values = await self._api.async_get_device_values(self.id)
        if device_values is not None:
            self.state.apply_changes(device_values.values, force)
