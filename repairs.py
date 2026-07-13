"""Repair flows for the TapHome integration."""

from __future__ import annotations

from typing import Any

from homeassistant import data_entry_flow
from homeassistant.components.repairs import RepairsFlow
from homeassistant.config_entries import ConfigEntry, ConfigEntryState
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import AbortFlow

from .config_flow import DEVICE_ARCHETYPES, _TapHomeDeviceArchetypeFlow
from .const import CONF_KNOWN_DEVICE_IDS
from .subentry import (
    config_subentry_from_data,
    iter_device_subentries,
)
from .taphome_data import TapHomeConfigEntry


class NewDeviceRepairFlow(
    _TapHomeDeviceArchetypeFlow[data_entry_flow.FlowResult], RepairsFlow
):
    """Guide the user through adding a newly discovered TapHome device.

    The device is fixed (the one the issue was raised for); the flow offers the
    same device-type menu as "Add device", filtered to the types this device
    can be exposed as, then reuses the shared archetype steps to build the
    subentry. Picking nothing and confirming "ignore" silences the issue.
    """

    def __init__(self, config_entry_id: str, device_id: int) -> None:
        """Store the config entry and device the issue was raised for."""
        self._config_entry_id = config_entry_id
        self._device_id = device_id
        self._archetype_fixed_device_id = device_id

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> data_entry_flow.FlowResult:
        """Handle the first step of the fix flow."""
        return await self.async_step_menu()

    async def async_step_menu(
        self, user_input: dict[str, Any] | None = None
    ) -> data_entry_flow.FlowResult:
        """Offer the device types this device can be exposed as, or ignore it."""
        entry = self._entry()
        if entry is None or entry.state is not ConfigEntryState.LOADED:
            return self.async_abort(reason="entry_not_loaded")
        if self._device_id not in entry.runtime_data.hub.devices:
            return self.async_abort(reason="device_gone")

        archetype_keys = [
            archetype.key
            for archetype in DEVICE_ARCHETYPES
            if self._archetype_addable_devices(archetype)
        ]
        return self.async_show_menu(
            step_id="menu",
            menu_options=[*archetype_keys, "ignore"],
            description_placeholders={"device": self._device_label(self._device_id)},
        )

    async def async_step_ignore(
        self, user_input: dict[str, Any] | None = None
    ) -> data_entry_flow.FlowResult:
        """Mark the device known so it is never reported as new again."""
        entry = self._entry()
        if entry is None:
            return self.async_abort(reason="entry_not_loaded")
        self._mark_known(entry)
        return self.async_create_entry(title="", data={})

    @property
    def _archetype_entry(self) -> TapHomeConfigEntry:
        """Return the config entry the issue was raised for."""
        entry = self._entry()
        if entry is None:
            raise AbortFlow("entry_not_loaded")
        return entry

    def _archetype_finish(self, payloads: list[Any]) -> data_entry_flow.FlowResult:
        """Add the collected subentries and mark the device known."""
        entry = self._archetype_entry
        existing = {
            subentry.unique_id for subentry in iter_device_subentries(entry)
        }
        for payload in payloads:
            if payload["unique_id"] in existing:
                continue
            self.hass.config_entries.async_add_subentry(
                entry, config_subentry_from_data(payload)
            )
        self._mark_known(entry)
        return self.async_create_entry(title="", data={})

    def _entry(self) -> ConfigEntry | None:
        """Return the config entry the issue was raised for."""
        return self.hass.config_entries.async_get_entry(self._config_entry_id)

    def _device_label(self, device_id: int) -> str:
        """Return a human readable label of a TapHome device."""
        entry = self._entry()
        device = (
            entry.runtime_data.hub.devices.get(device_id)
            if entry is not None and entry.state is ConfigEntryState.LOADED
            else None
        )
        if device is None:
            return f"({device_id})"
        return f"{device.name} ({device_id})"

    def _mark_known(self, entry: ConfigEntry) -> None:
        """Persist the device as known so it is never reported as new again."""
        known = {int(value) for value in entry.data.get(CONF_KNOWN_DEVICE_IDS, [])}
        known.add(self._device_id)
        self.hass.config_entries.async_update_entry(
            entry, data={**entry.data, CONF_KNOWN_DEVICE_IDS: sorted(known)}
        )


async def async_create_fix_flow(
    hass: HomeAssistant,
    issue_id: str,
    data: dict[str, str | int | float | None] | None,
) -> RepairsFlow:
    """Create the repair flow for a TapHome issue."""
    data = data or {}
    return NewDeviceRepairFlow(
        str(data["config_entry_id"]),
        int(data["device_id"]),  # type: ignore[arg-type]
    )
