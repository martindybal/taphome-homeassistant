"""Repair flows for the TapHome integration."""

from __future__ import annotations

from typing import Any

import voluptuous as vol

from homeassistant import data_entry_flow
from homeassistant.components.repairs import RepairsFlow
from homeassistant.config_entries import ConfigEntry, ConfigEntryState
from homeassistant.core import HomeAssistant
from homeassistant.helpers.selector import (
    BooleanSelector,
    SelectSelector,
    SelectSelectorConfig,
    SelectSelectorMode,
)

from .config_flow import apply_device_options, build_device_options_schema
from .const import CONF_KNOWN_DEVICE_IDS
from .platform_descriptors import (
    PLATFORM_DESCRIPTORS_BY_KEY,
    device_config_id,
    platforms_for_device,
)
from .subentry import (
    build_device_subentry,
    device_subentry_unique_id,
    iter_device_subentries,
)


class NewDeviceRepairFlow(RepairsFlow):
    """Guide the user through adding a newly discovered TapHome device."""

    def __init__(self, config_entry_id: str, device_id: int) -> None:
        """Store the config entry and device the issue was raised for."""
        self._config_entry_id = config_entry_id
        self._device_id = device_id
        self._platform: str | None = None

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> data_entry_flow.FlowResult:
        """Handle the first step of the fix flow."""
        return await self.async_step_confirm()

    async def async_step_confirm(
        self, user_input: dict[str, Any] | None = None
    ) -> data_entry_flow.FlowResult:
        """Pick the platform to add the device as, or ignore it for good."""
        entry = self._entry()
        if entry is None or entry.state is not ConfigEntryState.LOADED:
            return self.async_abort(reason="entry_not_loaded")

        device = entry.runtime_data.hub.devices.get(self._device_id)
        if device is None:
            return self.async_abort(reason="device_gone")

        platforms = platforms_for_device(device)
        errors: dict[str, str] = {}

        if user_input is not None:
            if user_input.get("ignore"):
                self._mark_known(entry)
                return self.async_create_entry(title="", data={})
            platform = user_input.get("platform")
            if platform in platforms:
                self._platform = platform
                descriptor = PLATFORM_DESCRIPTORS_BY_KEY[platform]
                # Sensors auto-detect their options; add them without a form.
                if not descriptor.fields or descriptor.advanced:
                    self._add_device(entry, platform, {"id": self._device_id})
                    return self.async_create_entry(title="", data={})
                return await self.async_step_options()
            errors["base"] = "select_platform_or_ignore"

        return self.async_show_form(
            step_id="confirm",
            data_schema=vol.Schema(
                {
                    vol.Optional("platform"): SelectSelector(
                        SelectSelectorConfig(
                            options=platforms,
                            mode=SelectSelectorMode.DROPDOWN,
                            translation_key="platform",
                        )
                    ),
                    vol.Optional("ignore", default=False): BooleanSelector(),
                }
            ),
            errors=errors,
            description_placeholders={"device": self._device_label(self._device_id)},
        )

    async def async_step_options(
        self, user_input: dict[str, Any] | None = None
    ) -> data_entry_flow.FlowResult:
        """Configure the per-device options before adding the device."""
        entry = self._entry()
        if entry is None or entry.state is not ConfigEntryState.LOADED:
            return self.async_abort(reason="entry_not_loaded")
        if self._platform is None:
            return await self.async_step_confirm()
        if self._device_id not in entry.runtime_data.hub.devices:
            return self.async_abort(reason="device_gone")

        descriptor = PLATFORM_DESCRIPTORS_BY_KEY[self._platform]
        errors: dict[str, str] = {}

        if user_input is not None:
            new_config = apply_device_options(
                descriptor, {"id": self._device_id}, user_input, errors
            )
            if not errors:
                self._add_device(entry, self._platform, new_config)
                return self.async_create_entry(title="", data={})

        schema, suggested = build_device_options_schema(
            descriptor,
            {"id": self._device_id},
            entry.runtime_data.hub.devices,
            self._device_label,
        )
        return self.async_show_form(
            step_id="options",
            data_schema=self.add_suggested_values_to_schema(
                schema, user_input or suggested
            ),
            errors=errors,
            description_placeholders={"device": self._device_label(self._device_id)},
        )

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
        self.hass.config_entries.async_update_entry(
            entry, data=self._data_with_known(entry)
        )

    def _add_device(
        self, entry: ConfigEntry, platform: str, device_config: dict
    ) -> None:
        """Add the device as a subentry and mark it as known."""
        device_id = device_config_id(device_config)
        unique_id = device_subentry_unique_id(platform, device_id)
        if all(
            subentry.unique_id != unique_id
            for subentry in iter_device_subentries(entry)
        ):
            self.hass.config_entries.async_add_subentry(
                entry,
                build_device_subentry(
                    platform, device_config, self._device_label(device_id)
                ),
            )
        self.hass.config_entries.async_update_entry(
            entry, data=self._data_with_known(entry)
        )

    def _data_with_known(self, entry: ConfigEntry) -> dict[str, Any]:
        """Return the entry data with this device added to the known ids."""
        known = {int(value) for value in entry.data.get(CONF_KNOWN_DEVICE_IDS, [])}
        known.add(self._device_id)
        return {**entry.data, CONF_KNOWN_DEVICE_IDS: sorted(known)}


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
