"""Diagnostics support for the TapHome integration."""

from __future__ import annotations

from typing import Any

from taphome_sdk import Device

from homeassistant.components.diagnostics import async_redact_data
from homeassistant.const import CONF_ID, CONF_TOKEN, CONF_WEBHOOK_ID
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceEntry

from .const import DOMAIN
from .entity import hub_device_id
from .taphome_data import TapHomeConfigEntry

TO_REDACT = {CONF_TOKEN, CONF_WEBHOOK_ID}


def _device_diagnostics(device: Device) -> dict[str, Any]:
    """Return the diagnostics of a single TapHome device."""
    state = device.state
    return {
        "id": device.id,
        "name": device.name,
        "description": device.description,
        "device_type": device.device_type,
        "usage": device.usage,
        "zone": device.zone,
        "category": device.category,
        "operation_mode": (
            state.operation_mode.name if state.operation_mode is not None else None
        ),
        "values": {
            value_type.name: state.get_device_value(value_type)
            for value_type in device.supported_values
        },
    }


async def async_get_config_entry_diagnostics(
    hass: HomeAssistant, entry: TapHomeConfigEntry
) -> dict[str, Any]:
    """Return diagnostics for the Core and all its devices."""
    hub = entry.runtime_data.hub
    location = hub.location
    return {
        "entry": {
            "data": async_redact_data(dict(entry.data), TO_REDACT),
            "options": async_redact_data(dict(entry.options), TO_REDACT),
        },
        "core": {
            "location_id": location.location_id if location else None,
            "location_name": location.location_name if location else None,
            "api_version": location.taphome_api_version if location else None,
            "connection_state": hub.connection_state.value.name,
            "device_count": len(hub.devices),
        },
        "devices": [_device_diagnostics(device) for device in hub.devices.values()],
    }


async def async_get_device_diagnostics(
    hass: HomeAssistant, entry: TapHomeConfigEntry, device: DeviceEntry
) -> dict[str, Any]:
    """Return diagnostics for a single device page."""
    hub = entry.runtime_data.hub
    prefix = f"{hub_device_id(hub.location, entry.data.get(CONF_ID))}_"
    devices: list[dict[str, Any]] = []
    for domain, identifier in device.identifiers:
        if domain != DOMAIN:
            continue
        suffix = identifier.removeprefix(prefix)
        if suffix != identifier and suffix.isdigit():
            taphome_device = hub.devices.get(int(suffix))
            if taphome_device is not None:
                devices.append(_device_diagnostics(taphome_device))
    return {"devices": devices}
