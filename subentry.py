"""Config subentry model for exposed TapHome devices.

Every exposed TapHome device is one config subentry of type
``SUBENTRY_TYPE_DEVICE``; its ``data`` is the device-config dict plus a
``SUBENTRY_DATA_PLATFORM`` key naming the platform bucket it is exposed on.
These helpers keep that shape and its unique-id format in a single place so the
setup wizard, options flow, subentry flow, migration and repairs all agree.
"""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from types import MappingProxyType
from typing import Any

from homeassistant.config_entries import (
    ConfigEntry,
    ConfigSubentry,
    ConfigSubentryData,
)

from .const import SUBENTRY_DATA_PLATFORM, SUBENTRY_TYPE_DEVICE
from .platform_descriptors import device_config_id


def device_subentry_unique_id(platform: str, device_id: int) -> str:
    """Return the stable unique id of a device exposed on one platform."""
    return f"{platform}:{device_id}"


def device_subentry_payload(platform: str, device_config: Mapping[str, Any]) -> dict:
    """Return the subentry ``data`` for one device/platform pair."""
    return {SUBENTRY_DATA_PLATFORM: platform, **device_config}


def build_device_subentry_data(
    platform: str, device_config: Mapping[str, Any], title: str
) -> ConfigSubentryData:
    """Build the subentry payload for one device exposed on one platform."""
    return ConfigSubentryData(
        data=device_subentry_payload(platform, device_config),
        subentry_type=SUBENTRY_TYPE_DEVICE,
        title=title,
        unique_id=device_subentry_unique_id(platform, device_config_id(device_config)),
    )


def config_subentry_from_data(data: ConfigSubentryData) -> ConfigSubentry:
    """Materialize subentry data into a ``ConfigSubentry`` with a fresh id."""
    return ConfigSubentry(
        data=MappingProxyType(dict(data["data"])),
        subentry_type=data["subentry_type"],
        title=data["title"],
        unique_id=data["unique_id"],
    )


def build_device_subentry(
    platform: str, device_config: Mapping[str, Any], title: str
) -> ConfigSubentry:
    """Build a ``ConfigSubentry`` for one device exposed on one platform."""
    return config_subentry_from_data(
        build_device_subentry_data(platform, device_config, title)
    )


def iter_device_subentries(entry: ConfigEntry) -> Iterable[ConfigSubentry]:
    """Yield the entry's device subentries."""
    return (
        subentry
        for subentry in entry.subentries.values()
        if subentry.subentry_type == SUBENTRY_TYPE_DEVICE
    )


def subentry_platform(data: Mapping[str, Any]) -> str | None:
    """Return the platform a device subentry is exposed on."""
    return data.get(SUBENTRY_DATA_PLATFORM)


def device_config_from_subentry(data: Mapping[str, Any]) -> dict[str, Any]:
    """Return the device config of a subentry, without the platform key."""
    return {
        key: value for key, value in data.items() if key != SUBENTRY_DATA_PLATFORM
    }
