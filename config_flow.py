"""Config flow for the TapHome integration."""

from __future__ import annotations

from collections.abc import Callable
from copy import deepcopy
import logging
from typing import Any

import aiohttp
from aiohttp import ClientSession
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
from homeassistant.data_entry_flow import section
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers import (
    area_registry as ar,
    entity_registry as er,
    label_registry as lr,
)
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.selector import (
    AreaSelector,
    BooleanSelector,
    EntitySelector,
    EntitySelectorConfig,
    LabelSelector,
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

from taphome_sdk import (
    Device,
    Location,
    TapHomeApi,
    TapHomeAuthError,
    TapHomeConnectionError,
    TapHomeHub,
    TapHomeHubFactory,
    ValueType,
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

_LOGGER = logging.getLogger(__name__)

YAML_UNIQUE_ID_PREFIX = "yaml_"

CONF_USE_CLOUD = "use_cloud"

DEFAULT_WEBHOOK_ID = "taphome"

CONNECTION_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_TOKEN): TextSelector(
            TextSelectorConfig(type=TextSelectorType.PASSWORD)
        ),
        vol.Optional(CONF_USE_CLOUD, default=False): BooleanSelector(),
        vol.Optional(CONF_IP): TextSelector(),
    }
)

CORE_SCHEMA = CONNECTION_SCHEMA.extend(
    {
        vol.Optional(CONF_ID): TextSelector(),
        vol.Optional(CONF_WEBHOOK_ID): TextSelector(),
        vol.Optional(
            CONF_ENABLED_ATTRIBUTES, default=AVAILABLE_ATTRIBUTES
        ): SelectSelector(
            SelectSelectorConfig(
                options=AVAILABLE_ATTRIBUTES,
                multiple=True,
                mode=SelectSelectorMode.DROPDOWN,
            )
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


def _connection_values_from_api_url(api_url: str) -> dict[str, Any]:
    """Derive the ip/use_cloud form values from a stored API URL."""
    normalized = api_url.rstrip("/")
    if normalized == DEFAULT_CLOUD_API_URL:
        return {CONF_USE_CLOUD: True}
    prefix = "http://"
    suffix = "/api/TapHomeApi/v1"
    if normalized.startswith(prefix) and normalized.endswith(suffix):
        ip = normalized[len(prefix) : -len(suffix)]
        if ip and "/" not in ip:
            return {CONF_IP: ip}
    return {}


def _apply_core_settings(options: dict[str, Any], user_input: dict[str, Any]) -> None:
    """Merge the core settings form fields from user_input into options."""
    if user_input.get(CONF_WEBHOOK_ID):
        options[CONF_WEBHOOK_ID] = user_input[CONF_WEBHOOK_ID].strip()
    else:
        options.pop(CONF_WEBHOOK_ID, None)
    options[CONF_ENABLED_ATTRIBUTES] = user_input.get(
        CONF_ENABLED_ATTRIBUTES, AVAILABLE_ATTRIBUTES
    )


def _core_id_from_input(user_input: dict[str, Any]) -> str | None:
    """Return the optional user-defined core id from the form input."""
    return (user_input.get(CONF_ID) or "").strip() or None


def _is_yaml_fallback_unique_id(unique_id: str | None) -> bool:
    """Return True when the entry still has an import fallback unique id."""
    return unique_id is None or unique_id.startswith(YAML_UNIQUE_ID_PREFIX)


async def _async_validate_connection(
    session: ClientSession, user_input: dict[str, Any], errors: dict[str, str]
) -> tuple[str, Location] | None:
    """Validate the connection form input and return the resolved connection."""
    if user_input.get(CONF_USE_CLOUD, False):
        api_url = DEFAULT_CLOUD_API_URL
    else:
        ip = (user_input.get(CONF_IP) or "").strip()
        if not ip:
            errors["base"] = "ip_required"
            return None
        api_url = f"http://{ip}/api/TapHomeApi/v1"

    try:
        location = await _async_get_location(session, api_url, user_input[CONF_TOKEN])
    except TapHomeAuthError:
        errors["base"] = "invalid_auth"
    except CannotConnectError:
        errors["base"] = "cannot_connect"
    else:
        return api_url, location
    return None


async def _async_get_location(
    session: ClientSession, api_url: str, token: str
) -> Location:
    """Validate the connection by requesting the core location."""
    api = TapHomeApi(api_url, token, session)
    try:
        location = await api.async_get_location()
    except TapHomeAuthError:
        raise
    except (
        TapHomeConnectionError,
        aiohttp.ClientError,
        TimeoutError,
        ValueError,
    ) as error:
        raise CannotConnectError from error

    if location is None:
        raise CannotConnectError
    return location


async def _async_load_devices(
    session: ClientSession, api_url: str, token: str
) -> dict[int, Device]:
    """Connect to the core and return its devices for the setup wizard."""
    try:
        hub = await TapHomeHubFactory.async_connect(api_url, token, session)
    except TapHomeAuthError:
        raise
    except Exception as error:
        raise CannotConnectError from error
    try:
        return dict(hub.devices)
    finally:
        hub.disconnect()


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


def _device_config_id(device_config: dict | int) -> int:
    """Return the TapHome device id of a stored device configuration."""
    if isinstance(device_config, dict):
        return int(device_config["id"])
    return int(device_config)


def _device_qualifies(device: Device, descriptor: PlatformDescriptor) -> bool:
    """Return True when the device can be exposed on the descriptor's platform."""
    return not descriptor.candidate_types or isinstance(
        device, descriptor.candidate_types
    )


def build_field_selector(
    option_field: OptionField,
    devices: dict[int, Device],
    device_label: Callable[[int], str],
) -> Any:
    """Build the selector for one per-device option field."""
    if option_field.kind == FieldKind.DEVICE_ID:
        options = [
            SelectOptionDict(value=str(device.id), label=device_label(device.id))
            for device in devices.values()
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


def build_device_options_schema(
    descriptor: PlatformDescriptor,
    device_config: dict,
    devices: dict[int, Device],
    device_label: Callable[[int], str],
) -> tuple[vol.Schema, dict[str, Any]]:
    """Build the per-device options form and its suggested values."""
    schema_dict: dict[Any, Any] = {}
    suggested_values: dict[str, Any] = {}

    for option_field in descriptor.fields:
        schema_dict[vol.Optional(option_field.key)] = build_field_selector(
            option_field, devices, device_label
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


def apply_device_options(
    descriptor: PlatformDescriptor,
    device_config: dict,
    user_input: dict[str, Any],
    errors: dict[str, str],
) -> dict:
    """Merge submitted per-device options into the stored device config."""
    new_config = dict(device_config)
    # unique_id is a YAML-only option: any imported value is preserved by the
    # copy above and is intentionally not exposed for editing in the UI.

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


class _TapHomeSetupFlow:
    """Shared zone, label and device setup steps for config and options flows.

    Mixed into ConfigFlow/OptionsFlow subclasses, which provide the flow
    members pylint cannot see on the mixin itself.
    """

    # pylint: disable=no-member

    _options: dict[str, Any]
    _setup_wizard: bool = False

    def __init__(self) -> None:
        """Initialize the shared setup flow state."""
        super().__init__()
        self._options = {}
        self._edit_selection: list[str] = []
        self._pending_device_ids: list[int] = []
        self._pending_pairs: list[tuple[int, str]] = []

    @property
    def _devices(self) -> dict[int, Device]:
        """Return the TapHome devices available to the flow."""
        raise NotImplementedError

    async def _async_commit(self, completed: str) -> ConfigFlowResult:
        """Persist the state after completing the given setup section."""
        raise NotImplementedError

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
                "add_devices",
                "edit_devices",
                "remove_devices",
                "zones",
                "labels",
            ],
        )

    async def async_step_core_settings(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Edit the connection and core level settings."""
        errors: dict[str, str] = {}

        if user_input is not None:
            connection = await _async_validate_connection(
                async_get_clientsession(self.hass), user_input, errors
            )
            if connection is not None:
                api_url, location = connection
                if (
                    not _is_yaml_fallback_unique_id(self.config_entry.unique_id)
                    and location.location_id != self.config_entry.unique_id
                ):
                    errors["base"] = "unique_id_mismatch"
                else:
                    self.hass.config_entries.async_update_entry(
                        self.config_entry,
                        data={
                            **self.config_entry.data,
                            CONF_TOKEN: user_input[CONF_TOKEN],
                            CONF_API_URL: api_url,
                            CONF_ID: _core_id_from_input(user_input),
                        },
                    )
                    _apply_core_settings(self._options, user_input)
                    return self._async_save_options()

        suggested_values = user_input or {
            CONF_TOKEN: self.config_entry.data.get(CONF_TOKEN),
            CONF_ID: self.config_entry.data.get(CONF_ID),
            **_connection_values_from_api_url(
                self.config_entry.data.get(CONF_API_URL) or ""
            ),
            CONF_WEBHOOK_ID: self._options.get(CONF_WEBHOOK_ID),
            CONF_ENABLED_ATTRIBUTES: self._options.get(
                CONF_ENABLED_ATTRIBUTES, AVAILABLE_ATTRIBUTES
            ),
        }
        return self.async_show_form(
            step_id="core_settings",
            data_schema=self.add_suggested_values_to_schema(
                CORE_SCHEMA, suggested_values
            ),
            errors=errors,
        )

    async def async_step_zones(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Edit the zone to area mapping."""
        return await self._async_step_name_mapping(
            CONF_ZONES,
            "zones",
            user_input,
            lambda device: device.zone,
            "area",
            AreaSelector(),
            self._resolve_area_id,
        )

    async def async_step_labels(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Edit the category to label mapping."""
        return await self._async_step_name_mapping(
            CONF_LABELS,
            "labels",
            user_input,
            lambda device: device.category,
            "label",
            LabelSelector(),
            self._resolve_label_id,
        )

    async def async_step_add_devices(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Pick the devices that should be added."""
        errors: dict[str, str] = {}
        cleared = bool(user_input and user_input.get("clear_selection"))

        if user_input is not None and not cleared:
            try:
                device_ids = [int(value) for value in user_input.get("devices", [])]
            except ValueError:
                device_ids = []
                errors["base"] = "invalid_device"
            if not errors and not device_ids:
                errors["base"] = "no_devices_selected"
            if not errors and not self._platforms_for_devices(device_ids):
                errors["base"] = "no_common_platform"
            if not errors:
                self._pending_device_ids = device_ids
                return await self.async_step_add_devices_platform()

        options = [
            SelectOptionDict(value=str(device.id), label=self._device_label(device.id))
            for device in self._devices.values()
        ]
        options.sort(key=lambda option: option["label"].casefold())

        configured_ids = self._configured_device_ids()
        unconfigured = [
            option["value"]
            for option in options
            if int(option["value"]) not in configured_ids
        ]

        schema = vol.Schema(
            {
                vol.Optional("devices", default=unconfigured): SelectSelector(
                    SelectSelectorConfig(
                        options=options,
                        multiple=True,
                        mode=SelectSelectorMode.DROPDOWN,
                    )
                ),
                vol.Optional("clear_selection", default=False): BooleanSelector(),
            }
        )
        if cleared:
            # "Deselect all" was submitted: re-show the form with nothing picked.
            schema = self.add_suggested_values_to_schema(
                schema, {"devices": [], "clear_selection": False}
            )
        elif user_input is not None:
            schema = self.add_suggested_values_to_schema(
                schema, {**user_input, "clear_selection": False}
            )

        return self.async_show_form(
            step_id="add_devices",
            data_schema=schema,
            errors=errors,
            last_step=False,
        )

    async def async_step_add_devices_platform(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Pick, per selected device, the platforms it should be added as."""
        devices = [
            device
            for device_id in self._pending_device_ids
            if (device := self._devices.get(device_id)) is not None
        ]
        devices.sort(key=lambda device: self._device_label(device.id).casefold())

        if user_input is not None:
            pairs: list[tuple[int, str]] = []
            for device in devices:
                item = user_input.get(self._device_label(device.id)) or {}
                selected = set(item.get("domains") or [])
                pairs.extend(
                    (device.id, descriptor.config_key)
                    for descriptor in PLATFORM_DESCRIPTORS
                    if descriptor.config_key in selected
                )
            self._pending_pairs = pairs
            if not pairs:
                return await self._async_commit("add_devices")
            return await self.async_step_add_devices_options()

        # Each device is a section holding a domain multiselect. Field labels
        # nested in a section cannot be localized, so the "domains" key shows as
        # is, matching the raw option keys of the next step.
        schema_dict: dict[Any, Any] = {
            vol.Required(self._device_label(device.id)): section(
                vol.Schema(
                    {
                        vol.Optional("domains", default=[]): SelectSelector(
                            SelectSelectorConfig(
                                options=self._platforms_for_device(device.id),
                                multiple=True,
                                mode=SelectSelectorMode.DROPDOWN,
                                translation_key="platform",
                            )
                        )
                    }
                ),
                {"collapsed": False},
            )
            for device in devices
        }

        return self.async_show_form(
            step_id="add_devices_platform",
            data_schema=vol.Schema(schema_dict),
            last_step=False,
        )

    async def async_step_add_devices_options(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Configure the options of each selected device and platform."""
        pairs_with_options = [
            (device_id, config_key)
            for device_id, config_key in self._pending_pairs
            if PLATFORM_DESCRIPTORS_BY_KEY[config_key].fields
        ]

        errors: dict[str, str] = {}
        if user_input is not None:
            errors = self._add_pending_pairs(user_input)
            if not errors:
                return await self._async_commit("add_devices")
        elif not pairs_with_options:
            # No selected device has configurable options; add them directly.
            self._add_pending_pairs({})
            return await self._async_commit("add_devices")

        schema_dict: dict[Any, Any] = {}
        suggested_values: dict[str, Any] = {}
        for device_id, config_key in pairs_with_options:
            descriptor = PLATFORM_DESCRIPTORS_BY_KEY[config_key]
            field_schema, field_suggested = self._build_device_options_schema(
                descriptor, {"id": device_id}
            )
            section_key = self._pair_section_key(device_id, config_key)
            schema_dict[vol.Optional(section_key)] = section(
                field_schema, {"collapsed": descriptor.advanced}
            )
            if field_suggested:
                suggested_values[section_key] = field_suggested

        if user_input is not None:
            suggested_values = user_input

        return self.async_show_form(
            step_id="add_devices_options",
            data_schema=self.add_suggested_values_to_schema(
                vol.Schema(schema_dict), suggested_values
            ),
            errors=errors,
        )

    def _add_pending_pairs(self, user_input: dict[str, Any]) -> dict[str, str]:
        """Add the pending device/platform pairs to the options.

        Returns the form errors; an empty mapping means everything was applied.
        """
        errors: dict[str, str] = {}
        new_configs: dict[str, list[dict]] = {}
        for device_id, config_key in self._pending_pairs:
            descriptor = PLATFORM_DESCRIPTORS_BY_KEY[config_key]
            section_input = (
                user_input.get(self._pair_section_key(device_id, config_key)) or {}
            )
            field_errors: dict[str, str] = {}
            new_config = self._apply_device_options(
                descriptor, {"id": device_id}, section_input, field_errors
            )
            if field_errors:
                errors["base"] = "invalid_device_id"
            new_configs.setdefault(config_key, []).append(new_config)
        if errors:
            return errors
        for config_key, configs in new_configs.items():
            devices = list(self._options.get(config_key) or [])
            existing_ids = {_device_config_id(dc) for dc in devices}
            for config in configs:
                if _device_config_id(config) not in existing_ids:
                    devices.append(config)
                    existing_ids.add(_device_config_id(config))
            self._options[config_key] = devices
        return {}

    async def async_step_edit_devices(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Pick the configured devices that should be edited."""
        entity_map = self._entity_selection_map()
        if not entity_map:
            return self.async_abort(reason="no_devices_configured")

        errors: dict[str, str] = {}
        if user_input is not None:
            entity_ids = user_input.get("devices", [])
            if not entity_ids:
                errors["base"] = "no_devices_selected"
            elif not all(entity_id in entity_map for entity_id in entity_ids):
                errors["base"] = "invalid_device"
            else:
                self._edit_selection = list(
                    dict.fromkeys(entity_map[entity_id] for entity_id in entity_ids)
                )
                return await self.async_step_edit_devices_form()

        return self.async_show_form(
            step_id="edit_devices",
            data_schema=vol.Schema(
                {
                    vol.Optional("devices"): EntitySelector(
                        EntitySelectorConfig(
                            multiple=True,
                            include_entities=sorted(entity_map),
                        )
                    )
                }
            ),
            errors=errors,
            last_step=False,
        )

    async def async_step_remove_devices(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Pick the configured devices that should be removed."""
        entity_map = self._entity_selection_map()
        if not entity_map:
            return self.async_abort(reason="no_devices_configured")

        errors: dict[str, str] = {}
        if user_input is not None:
            entity_ids = user_input.get("devices", [])
            if not entity_ids:
                errors["base"] = "no_devices_selected"
            elif not all(entity_id in entity_map for entity_id in entity_ids):
                errors["base"] = "invalid_device"
            else:
                self._remove_devices(
                    list(
                        dict.fromkeys(entity_map[entity_id] for entity_id in entity_ids)
                    )
                )
                return self._async_save_options()

        return self.async_show_form(
            step_id="remove_devices",
            data_schema=vol.Schema(
                {
                    vol.Optional("devices"): EntitySelector(
                        EntitySelectorConfig(
                            multiple=True,
                            include_entities=sorted(entity_map),
                        )
                    )
                }
            ),
            errors=errors,
        )

    async def async_step_edit_devices_form(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Edit the options of each selected device."""
        entries = self._resolve_edit_selection()
        if not entries:
            return self.async_abort(reason="no_devices_configured")

        errors: dict[str, str] = {}
        if user_input is not None:
            updates: list[tuple[str, int, dict]] = []
            for section_key, config_key, index, descriptor, device_config in entries:
                section_input = user_input.get(section_key) or {}
                field_errors: dict[str, str] = {}
                new_config = self._apply_device_options(
                    descriptor, device_config, section_input, field_errors
                )
                if field_errors:
                    errors["base"] = "invalid_device_id"
                updates.append((config_key, index, new_config))
            if not errors:
                for config_key, index, new_config in updates:
                    self._options[config_key][index] = new_config
                return self._async_save_options()

        schema_dict: dict[Any, Any] = {}
        suggested_values: dict[str, Any] = {}
        for section_key, _config_key, _index, descriptor, device_config in entries:
            field_schema, field_suggested = self._build_device_options_schema(
                descriptor, device_config
            )
            schema_dict[vol.Optional(section_key)] = section(
                field_schema, {"collapsed": descriptor.advanced}
            )
            if field_suggested:
                suggested_values[section_key] = field_suggested

        if user_input is not None:
            suggested_values = user_input

        return self.async_show_form(
            step_id="edit_devices_form",
            data_schema=self.add_suggested_values_to_schema(
                vol.Schema(schema_dict), suggested_values
            ),
            errors=errors,
        )

    def _resolve_edit_selection(
        self,
    ) -> list[tuple[str, str, int, PlatformDescriptor, dict]]:
        """Resolve the edit selection to one form section per selected device."""
        entries: list[tuple[str, str, int, PlatformDescriptor, dict]] = []
        label_counts: dict[str, int] = {}
        for selection in self._edit_selection:
            config_key, index_str = selection.rsplit(":", 1)
            index = int(index_str)
            devices = self._options.get(config_key) or []
            if index >= len(devices):
                continue
            device_config = devices[index]
            if not isinstance(device_config, dict):
                device_config = {"id": device_config}
            base_key = self._pair_section_key(
                _device_config_id(device_config), config_key
            )
            count = label_counts.get(base_key, 0)
            label_counts[base_key] = count + 1
            section_key = base_key if count == 0 else f"{base_key} ({count + 1})"
            entries.append(
                (
                    section_key,
                    config_key,
                    index,
                    PLATFORM_DESCRIPTORS_BY_KEY[config_key],
                    device_config,
                )
            )
        return entries

    def _async_save_options(self) -> ConfigFlowResult:
        """Store the edited options; the update listener reloads the entry."""
        return self.async_create_entry(title="", data=self._options)

    def _entity_selection_map(self) -> dict[str, str]:
        """Map this entry's entity ids to their 'config_key:index' selection.

        Edit and remove operate on configured devices, whose Home Assistant
        entities already exist. Picking an entity is resolved back to its device
        configuration through the entity registry (custom unique id or the device
        id encoded in the generated unique id).
        """
        from . import (  # noqa: PLC0415
            DOMAIN_DEFINITIONS,
            _parse_device_id_from_unique_id,
        )

        domain_to_key = {
            definition.name: definition.config_key for definition in DOMAIN_DEFINITIONS
        }
        index_by_device: dict[tuple[str, int], int] = {}
        selection_by_unique_id: dict[str, str] = {}
        for descriptor in PLATFORM_DESCRIPTORS:
            for index, device_config in enumerate(
                self._options.get(descriptor.config_key) or []
            ):
                device_id = _device_config_id(device_config)
                index_by_device[(descriptor.config_key, device_id)] = index
                if isinstance(device_config, dict) and device_config.get("unique_id"):
                    selection_by_unique_id[device_config["unique_id"]] = (
                        f"{descriptor.config_key}:{index}"
                    )

        registry = er.async_get(self.hass)
        selections: dict[str, str] = {}
        for entry in er.async_entries_for_config_entry(
            registry, self.config_entry.entry_id
        ):
            selection = selection_by_unique_id.get(entry.unique_id)
            if selection is None:
                config_key = domain_to_key.get(entry.domain)
                if config_key is None:
                    continue
                device_id = _parse_device_id_from_unique_id(entry.unique_id)
                if device_id is None:
                    continue
                index = index_by_device.get((config_key, device_id))
                if index is None:
                    continue
                selection = f"{config_key}:{index}"
            selections[entry.entity_id] = selection
        return selections

    def _remove_devices(self, selections: list[str]) -> None:
        """Remove the selected config_key:index entries from the options."""
        indexes_by_platform: dict[str, list[int]] = {}
        for selection in selections:
            config_key, index = selection.rsplit(":", 1)
            indexes_by_platform.setdefault(config_key, []).append(int(index))
        for config_key, indexes in indexes_by_platform.items():
            devices = self._options[config_key]
            for index in sorted(indexes, reverse=True):
                devices.pop(index)
            if not devices:
                self._options.pop(config_key, None)

    def _platforms_for_devices(self, device_ids: list[int]) -> list[str]:
        """Return the platforms at least one of the given devices qualifies for."""
        devices = [
            device
            for device_id in device_ids
            if (device := self._devices.get(device_id)) is not None
        ]
        if not devices:
            return []
        return [
            descriptor.config_key
            for descriptor in PLATFORM_DESCRIPTORS
            if any(_device_qualifies(device, descriptor) for device in devices)
        ]

    def _platforms_for_device(self, device_id: int) -> list[str]:
        """Return the platforms a single device qualifies for."""
        device = self._devices.get(device_id)
        if device is None:
            return []
        return [
            descriptor.config_key
            for descriptor in PLATFORM_DESCRIPTORS
            if _device_qualifies(device, descriptor)
        ]

    def _pair_section_key(self, device_id: int, config_key: str) -> str:
        """Return the form section key for one device and platform pair."""
        return f"{self._device_label(device_id)} · {config_key}"

    def _device_label(self, device_id: int) -> str:
        """Return a human readable label of a TapHome device."""
        device = self._devices.get(device_id)
        if device is None:
            return f"Unknown device ({device_id})"
        label = f"{device.name} ({device_id})"
        location = self._device_location(device)
        return f"{label} — {location}" if location else label

    def _device_location(self, device: Device) -> str | None:
        """Describe where a device lives: its area, or its zone and category."""
        if device.id in self._configured_device_ids():
            return self._area_name(device.zone)
        return (
            " · ".join(part for part in (device.zone, device.category) if part) or None
        )

    def _configured_device_ids(self) -> set[int]:
        """Return the ids of all devices present in any platform list."""
        return {
            _device_config_id(device_config)
            for descriptor in PLATFORM_DESCRIPTORS
            for device_config in self._options.get(descriptor.config_key) or []
        }

    def _area_name(self, zone: str | None) -> str | None:
        """Return the Home Assistant area name a TapHome zone maps to."""
        if not zone:
            return None
        mapped = (self._options.get(CONF_ZONES) or {}).get(zone)
        if isinstance(mapped, str):
            registry = ar.async_get(self.hass)
            area = registry.async_get_area(mapped) or registry.async_get_area_by_name(
                mapped
            )
            return area.name if area else mapped
        return zone

    def _resolve_area_id(self, mapped: str) -> str | None:
        """Resolve a stored area id or legacy name to an existing area id."""
        registry = ar.async_get(self.hass)
        if registry.async_get_area(mapped) is not None:
            return mapped
        area = registry.async_get_area_by_name(mapped)
        return area.id if area else None

    def _resolve_label_id(self, mapped: str) -> str | None:
        """Resolve a stored label id or legacy name to an existing label id."""
        registry = lr.async_get(self.hass)
        if registry.async_get_label(mapped) is not None:
            return mapped
        label = registry.async_get_label_by_name(mapped)
        return label.label_id if label else None

    async def _async_step_name_mapping(
        self,
        option_key: str,
        step_id: str,
        user_input: dict[str, Any] | None,
        get_name: Callable[[Device], str | None],
        field_key: str,
        target_selector: Any,
        resolve_target: Callable[[str], str | None],
    ) -> ConfigFlowResult:
        """Edit a zone or label mapping: each name maps to an area/label or nothing."""
        mapping = self._options.get(option_key) or {}
        discovered = {
            name for device in self._devices.values() if (name := get_name(device))
        }
        names = sorted(discovered | set(mapping), key=str.casefold)

        if user_input is not None:
            new_mapping: dict[str, Any] = {}
            for name in names:
                item = user_input.get(name) or {}
                target = item.get(field_key)
                if isinstance(target, str) and target:
                    new_mapping[name] = target
            if new_mapping:
                self._options[option_key] = new_mapping
            else:
                self._options.pop(option_key, None)
            return await self._async_commit(step_id)

        schema_dict: dict[Any, Any] = {}
        for name in names:
            mapped = mapping.get(name)
            suggested = resolve_target(mapped) if isinstance(mapped, str) else None
            schema_dict[vol.Required(name)] = section(
                vol.Schema(
                    {
                        vol.Optional(
                            field_key,
                            description={"suggested_value": suggested},
                        ): target_selector,
                    }
                ),
                {"collapsed": False},
            )

        return self.async_show_form(
            step_id=step_id,
            data_schema=vol.Schema(schema_dict),
            last_step=not self._setup_wizard,
        )

    def _build_device_options_schema(
        self, descriptor: PlatformDescriptor, device_config: dict
    ) -> tuple[vol.Schema, dict[str, Any]]:
        """Build the per-device options form and its suggested values."""
        return build_device_options_schema(
            descriptor, device_config, self._devices, self._device_label
        )

    def _build_field_selector(self, option_field: OptionField) -> Any:
        """Build the selector for one per-device option field."""
        return build_field_selector(option_field, self._devices, self._device_label)

    def _apply_device_options(
        self,
        descriptor: PlatformDescriptor,
        device_config: dict,
        user_input: dict[str, Any],
        errors: dict[str, str],
    ) -> dict:
        """Merge submitted per-device options into the stored device config."""
        return apply_device_options(descriptor, device_config, user_input, errors)


class TapHomeOptionsFlow(_TapHomeSetupFlow, OptionsFlow):
    """Handle the TapHome options flow."""

    @property
    def _hub(self) -> TapHomeHub:
        """Return the live hub of the loaded config entry."""
        return self.config_entry.runtime_data.hub

    @property
    def _devices(self) -> dict[int, Device]:
        """Return the devices discovered by the loaded core."""
        return self._hub.devices

    async def _async_commit(self, completed: str) -> ConfigFlowResult:
        """Save the edited options; the update listener reloads the entry."""
        return self._async_save_options()


class TapHomeConfigFlow(_TapHomeSetupFlow, ConfigFlow, domain=DOMAIN):
    """Handle the TapHome config flow."""

    VERSION = 1
    MINOR_VERSION = 1

    def __init__(self) -> None:
        """Initialize the config flow state."""
        super().__init__()
        self._wizard_devices: dict[int, Device] = {}
        self._wizard_data: dict[str, Any] = {}
        self._wizard_title = ""

    @staticmethod
    @callback
    def async_get_options_flow(config_entry: ConfigEntry) -> TapHomeOptionsFlow:
        """Create the options flow handler."""
        return TapHomeOptionsFlow()

    @property
    def _devices(self) -> dict[int, Device]:
        """Return the devices discovered while adding the core."""
        return self._wizard_devices

    async def _async_commit(self, completed: str) -> ConfigFlowResult:
        """Advance the initial setup wizard after a section is completed."""
        if completed == "zones":
            return await self._async_wizard_labels()
        if completed == "labels":
            return await self.async_step_add_devices()
        return self._async_create_wizard_entry()

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Handle the initial step started by the user."""
        errors: dict[str, str] = {}

        if user_input is not None:
            connection = await _async_validate_connection(
                async_get_clientsession(self.hass), user_input, errors
            )
            if connection is not None:
                api_url, location = connection
                await self.async_set_unique_id(location.location_id)
                self._abort_if_unique_id_configured()
                try:
                    self._wizard_devices = await _async_load_devices(
                        async_get_clientsession(self.hass),
                        api_url,
                        user_input[CONF_TOKEN],
                    )
                except TapHomeAuthError:
                    errors["base"] = "invalid_auth"
                except CannotConnectError:
                    errors["base"] = "cannot_connect"
                else:
                    self._wizard_data = {
                        CONF_TOKEN: user_input[CONF_TOKEN],
                        CONF_API_URL: api_url,
                        CONF_ID: _core_id_from_input(user_input),
                    }
                    self._wizard_title = location.location_name
                    self._options = {}
                    _apply_core_settings(self._options, user_input)
                    return await self._async_start_wizard()

        suggested_values = user_input or {
            CONF_WEBHOOK_ID: DEFAULT_WEBHOOK_ID,
        }
        return self.async_show_form(
            step_id="user",
            data_schema=self.add_suggested_values_to_schema(
                CORE_SCHEMA, suggested_values
            ),
            errors=errors,
        )

    async def _async_start_wizard(self) -> ConfigFlowResult:
        """Start the guided setup once the connection is confirmed."""
        self._setup_wizard = True
        if not self._devices:
            return self._async_create_wizard_entry()
        return await self._async_wizard_zones()

    async def _async_wizard_zones(self) -> ConfigFlowResult:
        """Show the zones step, or skip it when the core exposes no zones."""
        if any(device.zone for device in self._devices.values()):
            return await self.async_step_zones()
        return await self._async_wizard_labels()

    async def _async_wizard_labels(self) -> ConfigFlowResult:
        """Show the labels step, or skip it when the core exposes no categories."""
        if any(device.category for device in self._devices.values()):
            return await self.async_step_labels()
        return await self.async_step_add_devices()

    def _async_create_wizard_entry(self) -> ConfigFlowResult:
        """Create the config entry with the options gathered in the wizard."""
        return self.async_create_entry(
            title=self._wizard_title,
            data=self._wizard_data,
            options=self._options,
        )

    async def async_step_reconfigure(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Handle reconfiguration of the connection and core settings."""
        entry = self._get_reconfigure_entry()
        errors: dict[str, str] = {}

        if user_input is not None:
            connection = await _async_validate_connection(
                async_get_clientsession(self.hass), user_input, errors
            )
            if connection is not None:
                api_url, location = connection
                await self.async_set_unique_id(location.location_id)
                if not _is_yaml_fallback_unique_id(entry.unique_id):
                    self._abort_if_unique_id_mismatch(reason="unique_id_mismatch")
                new_options = dict(entry.options)
                _apply_core_settings(new_options, user_input)
                return self.async_update_reload_and_abort(
                    entry,
                    unique_id=location.location_id,
                    data_updates={
                        CONF_TOKEN: user_input[CONF_TOKEN],
                        CONF_API_URL: api_url,
                        CONF_ID: _core_id_from_input(user_input),
                    },
                    options=new_options,
                )

        suggested_values = user_input or {
            CONF_TOKEN: entry.data.get(CONF_TOKEN),
            CONF_ID: entry.data.get(CONF_ID),
            **_connection_values_from_api_url(entry.data.get(CONF_API_URL) or ""),
            CONF_WEBHOOK_ID: entry.options.get(CONF_WEBHOOK_ID),
            CONF_ENABLED_ATTRIBUTES: entry.options.get(
                CONF_ENABLED_ATTRIBUTES, AVAILABLE_ATTRIBUTES
            ),
        }
        return self.async_show_form(
            step_id="reconfigure",
            data_schema=self.add_suggested_values_to_schema(
                CORE_SCHEMA, suggested_values
            ),
            errors=errors,
        )

    async def async_step_reauth(self, entry_data: dict[str, Any]) -> ConfigFlowResult:
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
                location = await _async_get_location(
                    async_get_clientsession(self.hass),
                    entry.data[CONF_API_URL],
                    token,
                )
            except TapHomeAuthError:
                errors["base"] = "invalid_auth"
            except CannotConnectError:
                errors["base"] = "cannot_connect"
            else:
                await self.async_set_unique_id(location.location_id)
                if not _is_yaml_fallback_unique_id(entry.unique_id):
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
            location = await _async_get_location(
                async_get_clientsession(self.hass), api_url, token
            )
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
