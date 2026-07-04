"""Config flow for the TapHome integration."""

from __future__ import annotations

import logging
from typing import Any

import aiohttp
import voluptuous as vol

from homeassistant.config_entries import SOURCE_IMPORT, ConfigFlow, ConfigFlowResult
from homeassistant.const import CONF_ID, CONF_TOKEN, CONF_WEBHOOK_ID
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.selector import (
    TextSelector,
    TextSelectorConfig,
    TextSelectorType,
)

from .const import (
    CONF_API_URL,
    CONF_CLIMATES,
    CONF_ENABLED_ATTRIBUTES,
    CONF_IP,
    CONF_LABELS,
    CONF_ZONES,
    DEFAULT_CLOUD_API_URL,
    DEVICE_CONFIG_KEYS,
    DOMAIN,
    USE_DESCRIPTION_AS_ENTITY_ID,
    USE_DESCRIPTION_AS_NAME,
)
from .taphome_sdk import Location, TapHomeApi, TapHomeAuthError

_LOGGER = logging.getLogger(__name__)

YAML_UNIQUE_ID_PREFIX = "yaml_"

USER_SCHEMA = vol.Schema(
    {
        vol.Optional(CONF_IP): TextSelector(),
        vol.Optional(CONF_API_URL): TextSelector(
            TextSelectorConfig(type=TextSelectorType.URL)
        ),
        vol.Required(CONF_TOKEN): TextSelector(
            TextSelectorConfig(type=TextSelectorType.PASSWORD)
        ),
    }
)

REAUTH_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_TOKEN): TextSelector(
            TextSelectorConfig(type=TextSelectorType.PASSWORD)
        ),
    }
)

# Deprecated climate keys and their current equivalents. Applied in order,
# mirroring TapHomeClimateConfig._backwards_compatibility.
_CLIMATE_LEGACY_RENAMES = (
    ("thermostat", "id"),
    ("heat", "heating_switch_id"),
    ("cool", "cooling_switch_id"),
    ("mode", "heating_cooling_mode_id"),
    ("heating_cooling_mode_id", "hvac_mode_id"),
)


class CannotConnectError(HomeAssistantError):
    """The TapHome core could not be reached."""


def resolve_api_url(ip: str | None, api_url: str | None) -> str:
    """Resolve the API URL from the ip/api_url options."""
    if api_url:
        return api_url
    if ip:
        return f"http://{ip}/api/TapHomeApi/v1"
    return DEFAULT_CLOUD_API_URL


async def _async_get_location(api_url: str, token: str) -> Location:
    """Validate the connection by requesting the core location."""
    api = TapHomeApi(api_url, token)
    try:
        location = await api.async_get_location()
    except TapHomeAuthError:
        raise
    except (aiohttp.ClientError, TimeoutError, ValueError) as error:
        raise CannotConnectError from error

    if location is None:
        raise CannotConnectError
    return location


def _normalize_device_config(config_key: str, device_config: Any) -> dict:
    """Normalize a YAML device entry to the dict shape stored in options."""
    if isinstance(device_config, int):
        return {"id": device_config}

    device_config = dict(device_config)
    if config_key != CONF_CLIMATES:
        return device_config

    for legacy_key, current_key in _CLIMATE_LEGACY_RENAMES:
        if legacy_key in device_config:
            device_config[current_key] = device_config.pop(legacy_key)

    if "heating_switch_id" in device_config:
        device_config["hvac_switch_id"] = device_config.pop("heating_switch_id")
        device_config["hvac_mode"] = "heat"
    if "cooling_switch_id" in device_config:
        device_config["hvac_switch_id"] = device_config.pop("cooling_switch_id")
        device_config["hvac_mode"] = "cool"
    if "hvac_mode" in device_config:
        device_config["hvac_mode"] = str(device_config["hvac_mode"])
    if "range_high_thermostat_id" in device_config:
        device_config["id"] = device_config["range_high_thermostat_id"]

    return device_config


def _yaml_core_to_options(core_config: dict) -> dict:
    """Convert a YAML core configuration to config entry options."""
    options: dict[str, Any] = {}

    for key in (
        CONF_WEBHOOK_ID,
        USE_DESCRIPTION_AS_ENTITY_ID,
        USE_DESCRIPTION_AS_NAME,
        CONF_ZONES,
        CONF_LABELS,
    ):
        if core_config.get(key) is not None:
            options[key] = core_config[key]

    if CONF_ENABLED_ATTRIBUTES in core_config:
        options[CONF_ENABLED_ATTRIBUTES] = list(core_config[CONF_ENABLED_ATTRIBUTES])

    for config_key in DEVICE_CONFIG_KEYS:
        devices = core_config.get(config_key) or []
        if devices:
            options[config_key] = [
                _normalize_device_config(config_key, device) for device in devices
            ]

    return options


class TapHomeConfigFlow(ConfigFlow, domain=DOMAIN):
    """Handle the TapHome config flow."""

    VERSION = 1
    MINOR_VERSION = 1

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Handle the initial step started by the user."""
        errors: dict[str, str] = {}

        if user_input is not None:
            connection = await self._async_validate_connection(user_input, errors)
            if connection is not None:
                api_url, location = connection
                await self.async_set_unique_id(location.location_id)
                self._abort_if_unique_id_configured()
                return self.async_create_entry(
                    title=location.location_name,
                    data={
                        CONF_TOKEN: user_input[CONF_TOKEN],
                        CONF_API_URL: api_url,
                        CONF_ID: location.location_id,
                    },
                )

        return self.async_show_form(
            step_id="user",
            data_schema=self.add_suggested_values_to_schema(USER_SCHEMA, user_input),
            errors=errors,
        )

    async def async_step_reconfigure(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Handle reconfiguration of the connection settings."""
        entry = self._get_reconfigure_entry()
        errors: dict[str, str] = {}

        if user_input is not None:
            connection = await self._async_validate_connection(user_input, errors)
            if connection is not None:
                api_url, location = connection
                await self.async_set_unique_id(location.location_id)
                if not self._is_yaml_fallback_unique_id(entry.unique_id):
                    self._abort_if_unique_id_mismatch(reason="unique_id_mismatch")
                return self.async_update_reload_and_abort(
                    entry,
                    unique_id=location.location_id,
                    data_updates={
                        CONF_TOKEN: user_input[CONF_TOKEN],
                        CONF_API_URL: api_url,
                    },
                )

        suggested_values = user_input or {
            CONF_API_URL: entry.data.get(CONF_API_URL),
            CONF_TOKEN: entry.data.get(CONF_TOKEN),
        }
        return self.async_show_form(
            step_id="reconfigure",
            data_schema=self.add_suggested_values_to_schema(
                USER_SCHEMA, suggested_values
            ),
            errors=errors,
        )

    async def async_step_reauth(
        self, entry_data: dict[str, Any]
    ) -> ConfigFlowResult:
        """Handle reauthentication when the token is rejected."""
        return await self.async_step_reauth_confirm()

    async def async_step_reauth_confirm(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Ask for a new token and validate it."""
        entry = self._get_reauth_entry()
        errors: dict[str, str] = {}

        if user_input is not None:
            token = user_input[CONF_TOKEN]
            try:
                location = await _async_get_location(entry.data[CONF_API_URL], token)
            except TapHomeAuthError:
                errors["base"] = "invalid_auth"
            except CannotConnectError:
                errors["base"] = "cannot_connect"
            else:
                await self.async_set_unique_id(location.location_id)
                if not self._is_yaml_fallback_unique_id(entry.unique_id):
                    self._abort_if_unique_id_mismatch(reason="unique_id_mismatch")
                return self.async_update_reload_and_abort(
                    entry,
                    unique_id=location.location_id,
                    data_updates={CONF_TOKEN: token},
                )

        return self.async_show_form(
            step_id="reauth_confirm",
            data_schema=REAUTH_SCHEMA,
            description_placeholders={"name": entry.title},
            errors=errors,
        )

    async def async_step_import(self, import_data: dict) -> ConfigFlowResult:
        """Import one core from the legacy YAML configuration."""
        token = import_data[CONF_TOKEN]
        core_id = import_data.get(CONF_ID)
        api_url = resolve_api_url(
            import_data.get(CONF_IP), import_data.get(CONF_API_URL)
        )

        for entry in self._async_current_entries(include_ignore=True):
            if entry.source == SOURCE_IMPORT and entry.data.get(CONF_ID) == core_id:
                return self.async_abort(reason="already_configured")

        title = core_id or "TapHome"
        try:
            location = await _async_get_location(api_url, token)
        except (TapHomeAuthError, CannotConnectError) as error:
            # Keep the configuration even when the core is unreachable during
            # startup. Entry setup retries and reauth guides the user when
            # the token is invalid.
            _LOGGER.warning(
                "Importing TapHome core %s without validation: %s", title, error
            )
            unique_id = f"{YAML_UNIQUE_ID_PREFIX}{core_id or 'default'}"
        else:
            unique_id = location.location_id
            title = location.location_name

        await self.async_set_unique_id(unique_id)
        self._abort_if_unique_id_configured()

        return self.async_create_entry(
            title=title,
            data={
                CONF_TOKEN: token,
                CONF_API_URL: api_url,
                CONF_ID: core_id,
            },
            options=_yaml_core_to_options(import_data),
        )

    async def _async_validate_connection(
        self, user_input: dict[str, Any], errors: dict[str, str]
    ) -> tuple[str, Location] | None:
        """Validate the user form input and return the resolved connection."""
        ip = user_input.get(CONF_IP)
        api_url = user_input.get(CONF_API_URL)

        if ip and api_url:
            errors["base"] = "ip_and_api_url_set"
            return None

        resolved_api_url = resolve_api_url(ip, api_url)
        try:
            location = await _async_get_location(
                resolved_api_url, user_input[CONF_TOKEN]
            )
        except TapHomeAuthError:
            errors["base"] = "invalid_auth"
        except CannotConnectError:
            errors["base"] = "cannot_connect"
        else:
            return resolved_api_url, location
        return None

    @staticmethod
    def _is_yaml_fallback_unique_id(unique_id: str | None) -> bool:
        """Return True when the entry still has an import fallback unique id."""
        return unique_id is None or unique_id.startswith(YAML_UNIQUE_ID_PREFIX)
