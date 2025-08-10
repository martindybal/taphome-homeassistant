"""Helper functions and protocols for TapHome integration."""

import asyncio
from collections.abc import Awaitable, Callable
from datetime import timedelta
from enum import Enum
from typing import Any, Protocol, TypeVar

EnumT = TypeVar("EnumT", bound=Enum)


def enum_from_string(enum_type: type[EnumT], value: str) -> EnumT:
    """Create a ``EnumT`` from a string."""
    for enum_value in enum_type:
        if enum_value.name.replace("_", "").lower() == value.lower():
            return enum_value
    raise ValueError(f"Unknown enum value: {value}")


def get_required(config: dict[str, Any], key: str):
    """Return value for ``key`` or raise if missing."""
    value = get_optional(config, key, None)
    if value is None:
        raise KeyError(f"Missing required key: {key}")
    return value


def get_optional(config: dict[str, Any], key: str, default):
    """Return value for ``key`` or ``default`` if not present."""
    if isinstance(config, dict):
        if key in config:
            return config[key]
    return default


class FromDictProtocol[ResponseT](Protocol):
    """Protocol for classes that can be created from dict."""

    @classmethod
    def from_dict(cls, data: dict) -> ResponseT:
        """Create an instance of the class from a dictionary."""
        raise NotImplementedError


def set_interval_async(
    func: Callable[..., Awaitable[Any]], interval: timedelta, *args: Any, **kwargs: Any
) -> asyncio.Task:
    """Schedule `func(*args, **kwargs)` every `interval` seconds in asyncio."""

    async def periodic_execute() -> None:
        while True:
            await asyncio.sleep(interval.total_seconds())
            await func(*args, **kwargs)

    return asyncio.create_task(periodic_execute())
