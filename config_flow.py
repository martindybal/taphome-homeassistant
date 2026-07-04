"""Config flow for the TapHome integration."""

from __future__ import annotations

from collections.abc import Callable
from copy import deepcopy
import logging
from typing import Any

import aiohttp
import voluptuous as vol

from homeassistant.config_entries import (
    SOURCE_IMPORT,
    ConfigEntry,
    ConfigEntryState,
    ConfigFlow,
    ConfigFlowResult,
    OptionsFlow,
)
from homeassistant.const import CONF_ID, CONF_TOKEN, CONF_WEBHOOK_ID
from homeassistant.core import callback
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.selector import (
    BooleanSelector,
    NumberSelector,
    NumberSelectorConfig,
    NumberSelectorMode,
    SelectOptionDict,
    SelectSelector,
    SelectSelectorConfig,
    SelectSelectorMode,
    TextSelector,
    TextSelectorConfig,
    TextSelectorType,
)

from .const import (
    AVAILABLE_ATTRIBUTES,
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
from .platform_descriptors import (
    PLATFORM_DESCRIPTORS,
    PLATFORM_DESCRIPTORS_BY_KEY,
    FieldKind,
    OptionField,
    PlatformDescriptor,
)
from .taphome_sdk import (
    Device,
    Location,
    TapHomeApi,
    TapHomeAuthError,
    TapHomeHub,
    ValueType,
)

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

    @staticmethod
    @callback
    def async_get_options_flow(config_entry: ConfigEntry) -> TapHomeOptionsFlow:
        """Create the options flow handler."""
        return TapHomeOptionsFlow()

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


def _device_config_id(device_config: dict | int) -> int:
    """Return the TapHome device id of a stored device configuration."""
    if isinstance(device_config, dict):
        return int(device_config["id"])
    return int(device_config)


class TapHomeOptionsFlow(OptionsFlow):
    """Handle the TapHome options flow."""

    def __init__(self) -> None:
        """Initialize the options flow state."""
        self._options: dict[str, Any] = {}
        self._config_key: str | None = None
        self._device_index: int | None = None

    @property
    def _hub(self) -> TapHomeHub:
        """Return the live hub of the loaded config entry."""
        return self.config_entry.runtime_data.hub

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Show the options menu."""
        if self.config_entry.state is not ConfigEntryState.LOADED:
            return self.async_abort(reason="entry_not_loaded")
        if not self._options:
            self._options = deepcopy(dict(self.config_entry.options))

        return self.async_show_menu(
            step_id="init",
            menu_options=[
                "core_settings",
                "zones",
                "labels",
                "select_devices",
                "device_options",
            ],
        )

    async def async_step_core_settings(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Edit core level settings."""
        if user_input is not None:
            if user_input.get(CONF_WEBHOOK_ID):
                self._options[CONF_WEBHOOK_ID] = user_input[CONF_WEBHOOK_ID].strip()
            else:
                self._options.pop(CONF_WEBHOOK_ID, None)
            self._options[USE_DESCRIPTION_AS_ENTITY_ID] = user_input.get(
                USE_DESCRIPTION_AS_ENTITY_ID, False
            )
            self._options[USE_DESCRIPTION_AS_NAME] = user_input.get(
                USE_DESCRIPTION_AS_NAME, False
            )
            self._options[CONF_ENABLED_ATTRIBUTES] = user_input.get(
                CONF_ENABLED_ATTRIBUTES, []
            )
            return self._async_save_options()

        schema = vol.Schema(
            {
                vol.Optional(CONF_WEBHOOK_ID): TextSelector(),
                vol.Optional(
                    USE_DESCRIPTION_AS_ENTITY_ID,
                    default=self._options.get(USE_DESCRIPTION_AS_ENTITY_ID, False),
                ): BooleanSelector(),
                vol.Optional(
                    USE_DESCRIPTION_AS_NAME,
                    default=self._options.get(USE_DESCRIPTION_AS_NAME, False),
                ): BooleanSelector(),
                vol.Optional(
                    CONF_ENABLED_ATTRIBUTES,
                    default=self._options.get(
                        CONF_ENABLED_ATTRIBUTES, AVAILABLE_ATTRIBUTES
                    ),
                ): SelectSelector(
                    SelectSelectorConfig(
                        options=AVAILABLE_ATTRIBUTES,
                        multiple=True,
                        mode=SelectSelectorMode.DROPDOWN,
                    )
                ),
            }
        )
        return self.async_show_form(
            step_id="core_settings",
            data_schema=self.add_suggested_values_to_schema(
                schema, {CONF_WEBHOOK_ID: self._options.get(CONF_WEBHOOK_ID)}
            ),
        )

    async def async_step_zones(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Edit the zone to area mapping."""
        return await self._async_step_name_mapping(
            CONF_ZONES, "zones", user_input, lambda device: device.zone
        )

    async def async_step_labels(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Edit the category to label mapping."""
        return await self._async_step_name_mapping(
            CONF_LABELS, "labels", user_input, lambda device: device.category
        )

    async def async_step_select_devices(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Pick the platform whose devices should be selected."""
        if user_input is not None:
            self._config_key = user_input["platform"]
            return await self.async_step_select_devices_pick()

        return self.async_show_form(
            step_id="select_devices",
            data_schema=vol.Schema(
                {
                    vol.Required("platform"): SelectSelector(
                        SelectSelectorConfig(
                            options=[
                                descriptor.config_key
                                for descriptor in PLATFORM_DESCRIPTORS
                            ],
                            mode=SelectSelectorMode.DROPDOWN,
                            translation_key="platform",
                        )
                    )
                }
            ),
        )

    async def async_step_select_devices_pick(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Select the devices exposed on the chosen platform."""
        descriptor = PLATFORM_DESCRIPTORS_BY_KEY[self._config_key]
        configured = {
            _device_config_id(device_config): device_config
            for device_config in self._options.get(self._config_key) or []
        }

        if user_input is not None:
            selected_ids = [int(value) for value in user_input.get("devices", [])]
            new_devices = [
                configured.get(device_id, {"id": device_id})
                for device_id in selected_ids
            ]
            if new_devices:
                self._options[self._config_key] = new_devices
            else:
                self._options.pop(self._config_key, None)
            return self._async_save_options()

        candidates = self._candidate_devices(descriptor)
        options = [
            SelectOptionDict(value=str(device.id), label=self._device_label(device.id))
            for device in candidates
        ]
        known_ids = {device.id for device in candidates}
        options.extend(
            SelectOptionDict(
                value=str(device_id), label=self._device_label(device_id)
            )
            for device_id in configured
            if device_id not in known_ids
        )
        options.sort(key=lambda option: option["label"].casefold())

        schema = vol.Schema(
            {
                vol.Optional(
                    "devices", default=[str(device_id) for device_id in configured]
                ): SelectSelector(
                    SelectSelectorConfig(
                        options=options,
                        multiple=True,
                        mode=SelectSelectorMode.DROPDOWN,
                    )
                )
            }
        )
        return self.async_show_form(
            step_id="select_devices_pick",
            data_schema=schema,
            description_placeholders={"platform": self._config_key},
        )

    async def async_step_device_options(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Pick the platform whose device options should be edited."""
        platforms = [
            descriptor.config_key
            for descriptor in PLATFORM_DESCRIPTORS
            if self._options.get(descriptor.config_key)
        ]
        if not platforms:
            return self.async_abort(reason="no_devices_configured")

        if user_input is not None:
            self._config_key = user_input["platform"]
            return await self.async_step_device_options_pick()

        return self.async_show_form(
            step_id="device_options",
            data_schema=vol.Schema(
                {
                    vol.Required("platform"): SelectSelector(
                        SelectSelectorConfig(
                            options=platforms,
                            mode=SelectSelectorMode.DROPDOWN,
                            translation_key="platform",
                        )
                    )
                }
            ),
        )

    async def async_step_device_options_pick(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Pick the configured device to edit."""
        devices = self._options.get(self._config_key) or []

        if user_input is not None:
            self._device_index = int(user_input["device"])
            return await self.async_step_device_options_form()

        options = [
            SelectOptionDict(
                value=str(index),
                label=self._device_label(_device_config_id(device_config)),
            )
            for index, device_config in enumerate(devices)
        ]
        return self.async_show_form(
            step_id="device_options_pick",
            data_schema=vol.Schema(
                {
                    vol.Required("device"): SelectSelector(
                        SelectSelectorConfig(
                            options=options, mode=SelectSelectorMode.DROPDOWN
                        )
                    )
                }
            ),
            description_placeholders={"platform": self._config_key},
        )

    async def async_step_device_options_form(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Edit the options of one configured device."""
        descriptor = PLATFORM_DESCRIPTORS_BY_KEY[self._config_key]
        devices = self._options[self._config_key]
        device_config = devices[self._device_index]
        if not isinstance(device_config, dict):
            device_config = {"id": device_config}
        errors: dict[str, str] = {}

        if user_input is not None:
            new_config = self._apply_device_options(
                descriptor, device_config, user_input, errors
            )
            if not errors:
                devices[self._device_index] = new_config
                return self._async_save_options()

        schema, suggested_values = self._build_device_options_schema(
            descriptor, device_config
        )
        return self.async_show_form(
            step_id="device_options_form",
            data_schema=self.add_suggested_values_to_schema(schema, suggested_values),
            errors=errors,
            description_placeholders={
                "device": self._device_label(_device_config_id(device_config))
            },
        )

    def _async_save_options(self) -> ConfigFlowResult:
        """Store the edited options; the update listener reloads the entry."""
        return self.async_create_entry(title="", data=self._options)

    def _candidate_devices(self, descriptor: PlatformDescriptor) -> list[Device]:
        """Return the exposed devices that qualify for the platform."""
        return [
            device
            for device in self._hub.devices.values()
            if not descriptor.candidate_types
            or isinstance(device, descriptor.candidate_types)
        ]

    def _device_label(self, device_id: int) -> str:
        """Return a human readable label of a TapHome device."""
        device = self._hub.devices.get(device_id)
        if device is None:
            return f"Unknown device ({device_id})"
        return f"{device.name} ({device_id})"

    async def _async_step_name_mapping(
        self,
        option_key: str,
        step_id: str,
        user_input: dict[str, Any] | None,
        get_name: Callable[[Device], str | None],
    ) -> ConfigFlowResult:
        """Edit a zone or label mapping with rename and ignore support."""
        mapping = self._options.get(option_key) or {}
        discovered = {
            name for device in self._hub.devices.values() if (name := get_name(device))
        }
        names = sorted(discovered | set(mapping), key=str.casefold)

        if user_input is not None:
            ignored = set(user_input.get("ignored_names", []))
            new_mapping: dict[str, Any] = {}
            for name in names:
                if name in ignored:
                    new_mapping[name] = {"ignore": True}
                    continue
                target = (user_input.get(name) or "").strip()
                if target and target != name:
                    new_mapping[name] = target
            if new_mapping:
                self._options[option_key] = new_mapping
            else:
                self._options.pop(option_key, None)
            return self._async_save_options()

        currently_ignored = [
            name
            for name in names
            if isinstance(mapping.get(name), dict) and mapping[name].get("ignore")
        ]
        schema_dict: dict[Any, Any] = {
            vol.Optional("ignored_names", default=currently_ignored): SelectSelector(
                SelectSelectorConfig(
                    options=names,
                    multiple=True,
                    mode=SelectSelectorMode.DROPDOWN,
                )
            )
        }
        suggested_values: dict[str, Any] = {}
        for name in names:
            schema_dict[vol.Optional(name)] = TextSelector()
            if isinstance(mapping.get(name), str):
                suggested_values[name] = mapping[name]

        return self.async_show_form(
            step_id=step_id,
            data_schema=self.add_suggested_values_to_schema(
                vol.Schema(schema_dict), suggested_values
            ),
        )

    def _build_device_options_schema(
        self, descriptor: PlatformDescriptor, device_config: dict
    ) -> tuple[vol.Schema, dict[str, Any]]:
        """Build the per-device options form and its suggested values."""
        schema_dict: dict[Any, Any] = {vol.Optional("unique_id"): TextSelector()}
        suggested_values: dict[str, Any] = {}
        if device_config.get("unique_id"):
            suggested_values["unique_id"] = device_config["unique_id"]

        for option_field in descriptor.fields:
            schema_dict[vol.Optional(option_field.key)] = self._build_field_selector(
                option_field
            )
            value = device_config.get(option_field.key)
            if value is None:
                continue
            if option_field.kind in (FieldKind.DEVICE_ID, FieldKind.VALUE_TYPE):
                suggested_values[option_field.key] = str(value)
            elif option_field.kind == FieldKind.MULTI_ENUM:
                suggested_values[option_field.key] = [str(item) for item in value]
            elif option_field.kind == FieldKind.ENUM:
                suggested_values[option_field.key] = str(value)
            else:
                suggested_values[option_field.key] = value

        return vol.Schema(schema_dict), suggested_values

    def _build_field_selector(self, option_field: OptionField) -> Any:
        """Build the selector for one per-device option field."""
        if option_field.kind == FieldKind.DEVICE_ID:
            options = [
                SelectOptionDict(
                    value=str(device.id), label=self._device_label(device.id)
                )
                for device in self._hub.devices.values()
                if not option_field.device_types
                or isinstance(device, option_field.device_types)
            ]
            options.sort(key=lambda option: option["label"].casefold())
            return SelectSelector(
                SelectSelectorConfig(
                    options=options,
                    mode=SelectSelectorMode.DROPDOWN,
                    custom_value=True,
                )
            )
        if option_field.kind == FieldKind.VALUE_TYPE:
            options = [
                SelectOptionDict(
                    value=str(value_type.value),
                    label=value_type.name.replace("_", " ").lower(),
                )
                for value_type in ValueType
            ]
            options.sort(key=lambda option: option["label"])
            return SelectSelector(
                SelectSelectorConfig(options=options, mode=SelectSelectorMode.DROPDOWN)
            )
        if option_field.kind in (FieldKind.ENUM, FieldKind.MULTI_ENUM):
            return SelectSelector(
                SelectSelectorConfig(
                    options=sorted(option_field.options),
                    multiple=option_field.kind == FieldKind.MULTI_ENUM,
                    mode=SelectSelectorMode.DROPDOWN,
                )
            )
        if option_field.kind in (FieldKind.NUMBER_INT, FieldKind.NUMBER_FLOAT):
            return NumberSelector(
                NumberSelectorConfig(
                    min=option_field.min_value,
                    max=option_field.max_value,
                    step=option_field.step
                    or (1 if option_field.kind == FieldKind.NUMBER_INT else 0.1),
                    mode=NumberSelectorMode.BOX,
                )
            )
        return TextSelector()

    def _apply_device_options(
        self,
        descriptor: PlatformDescriptor,
        device_config: dict,
        user_input: dict[str, Any],
        errors: dict[str, str],
    ) -> dict:
        """Merge submitted per-device options into the stored device config."""
        new_config = dict(device_config)

        unique_id = (user_input.get("unique_id") or "").strip()
        if unique_id:
            new_config["unique_id"] = unique_id
        else:
            new_config.pop("unique_id", None)

        for option_field in descriptor.fields:
            value = user_input.get(option_field.key)
            if value in (None, "", []):
                new_config.pop(option_field.key, None)
                continue
            if option_field.kind in (FieldKind.DEVICE_ID, FieldKind.VALUE_TYPE):
                try:
                    new_config[option_field.key] = int(value)
                except (TypeError, ValueError):
                    errors[option_field.key] = "invalid_device_id"
            elif option_field.kind == FieldKind.NUMBER_INT:
                new_config[option_field.key] = int(value)
            elif option_field.kind == FieldKind.NUMBER_FLOAT:
                new_config[option_field.key] = float(value)
            elif option_field.kind == FieldKind.MULTI_ENUM:
                new_config[option_field.key] = list(value)
            else:
                new_config[option_field.key] = value

        return new_config
