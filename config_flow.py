"""Config flow for the TapHome integration."""

from __future__ import annotations

from collections.abc import Callable
from copy import deepcopy
from dataclasses import dataclass
import logging
from typing import Any

import aiohttp
from aiohttp import ClientSession
import voluptuous as vol

from homeassistant.config_entries import (
    SOURCE_IMPORT,
    ConfigEntry,
    ConfigEntryBaseFlow,
    ConfigEntryState,
    ConfigFlow,
    ConfigFlowResult,
    ConfigSubentry,
    ConfigSubentryData,
    ConfigSubentryFlow,
    OptionsFlow,
    SubentryFlowResult,
)
from homeassistant.const import (
    CONF_BINARY_SENSORS,
    CONF_COVERS,
    CONF_ID,
    CONF_LIGHTS,
    CONF_SENSORS,
    CONF_SWITCHES,
    CONF_TOKEN,
    CONF_WEBHOOK_ID,
)
from homeassistant.core import callback
from homeassistant.data_entry_flow import section
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers import (
    area_registry as ar,
    device_registry as dr,
    entity_registry as er,
    label_registry as lr,
)
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.selector import (
    AreaSelector,
    BooleanSelector,
    DeviceFilterSelectorConfig,
    EntityFilterSelectorConfig,
    LabelSelector,
    NumberSelector,
    NumberSelectorConfig,
    NumberSelectorMode,
    SelectOptionDict,
    SelectSelector,
    SelectSelectorConfig,
    SelectSelectorMode,
    TargetSelector,
    TargetSelectorConfig,
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

from .binary_sensor import KNOWN_BINARY_SENSOR_TYPES
from .const import (
    AVAILABLE_ATTRIBUTES,
    CONF_API_URL,
    CONF_BUTTONS,
    CONF_CLIMATES,
    CONF_ENABLED_ATTRIBUTES,
    CONF_FAN,
    CONF_HUMIDIFIER,
    CONF_IP,
    CONF_LABELS,
    CONF_MULTIVALUE_SWITCHES,
    CONF_NUMBERS,
    CONF_TIMES,
    CONF_VALVE,
    CONF_ZONES,
    DEFAULT_CLOUD_API_URL,
    DEVICE_CONFIG_KEYS,
    DOMAIN,
    SUBENTRY_TYPE_DEVICE,
    USE_DESCRIPTION_AS_ENTITY_ID,
    USE_DESCRIPTION_AS_NAME,
)
from .platform_descriptors import (
    PLATFORM_DESCRIPTORS,
    PLATFORM_DESCRIPTORS_BY_KEY,
    FieldKind,
    OptionField,
    PlatformDescriptor,
    device_config_id,
)
from .sensor import KNOWN_SENSOR_TYPES
from .subentry import (
    build_device_subentry_data,
    config_subentry_from_data,
    device_config_from_subentry,
    device_subentry_payload,
    device_subentry_unique_id,
    iter_device_subentries,
    subentry_platform,
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


@dataclass(slots=True, frozen=True)
class DeviceArchetype:
    """One user-facing device type offered by the subentry add menu.

    An archetype is an add-time template: it picks the platform bucket and the
    subset of option fields that type needs. It is not persisted — reconfigure
    always offers every field, so a device can be converted between archetypes.
    """

    key: str
    config_key: str
    fields: tuple[str, ...] = ()
    # Per-value platforms (sensor/binary sensor) pick a device first and then
    # the device values to expose; each value becomes its own subentry.
    values: bool = False
    # The range thermostat has no main device picker: its two thermostat
    # fields are required and the high thermostat becomes the device id.
    range_thermostat: bool = False


DEVICE_ARCHETYPES: tuple[DeviceArchetype, ...] = (
    DeviceArchetype("light", CONF_LIGHTS, ("effect_id",)),
    DeviceArchetype("switch", CONF_SWITCHES, ("device_class",)),
    DeviceArchetype("cover", CONF_COVERS, ("device_class", "close_threshold")),
    DeviceArchetype("thermostat", CONF_CLIMATES),
    DeviceArchetype(
        "thermostat_controlled",
        CONF_CLIMATES,
        ("hvac_switch_id", "hvac_mode", "hvac_mode_id", "hvac_action_id"),
    ),
    DeviceArchetype(
        "thermostat_range",
        CONF_CLIMATES,
        ("range_high_thermostat_id", "range_low_thermostat_id"),
        range_thermostat=True,
    ),
    DeviceArchetype("sensor", CONF_SENSORS, values=True),
    DeviceArchetype("binary_sensor", CONF_BINARY_SENSORS, values=True),
    DeviceArchetype("fan", CONF_FAN, ("preset_mode_id",)),
    DeviceArchetype("humidifier", CONF_HUMIDIFIER, ("device_class",)),
    DeviceArchetype("valve", CONF_VALVE, ("device_class",)),
    DeviceArchetype("button", CONF_BUTTONS, ("actions", "device_class")),
    DeviceArchetype("select", CONF_MULTIVALUE_SWITCHES),
    DeviceArchetype("number", CONF_NUMBERS),
    DeviceArchetype("time", CONF_TIMES),
)

DEVICE_ARCHETYPES_BY_KEY: dict[str, DeviceArchetype] = {
    archetype.key: archetype for archetype in DEVICE_ARCHETYPES
}

_KNOWN_VALUE_TYPES_BY_KEY: dict[str, tuple[ValueType, ...]] = {
    CONF_SENSORS: tuple(known.value_type for known in KNOWN_SENSOR_TYPES),
    CONF_BINARY_SENSORS: tuple(
        known.value_type for known in KNOWN_BINARY_SENSOR_TYPES
    ),
}


def _value_type_label(value_type: ValueType) -> str:
    """Return the human readable label of a device value type."""
    return value_type.name.replace("_", " ").lower()


def _target_ids(target: dict[str, Any], key: str) -> list[str]:
    """Return one target field normalized to a list of ids."""
    value = target.get(key) or []
    return [value] if isinstance(value, str) else list(value)


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

    return options


def _yaml_device_subentries(
    core_config: dict, devices: dict[int, Device]
) -> list[ConfigSubentryData]:
    """Build one device subentry per device in a YAML core configuration."""
    subentries: list[ConfigSubentryData] = []
    for config_key in DEVICE_CONFIG_KEYS:
        for device in core_config.get(config_key) or []:
            device_config = _normalize_device_config(config_key, device)
            device_id = device_config_id(device_config)
            subentries.append(
                build_device_subentry_data(
                    config_key,
                    device_config,
                    _yaml_subentry_title(device_id, devices.get(device_id)),
                )
            )
    return subentries


def _yaml_subentry_title(device_id: int, device: Device | None) -> str:
    """Title an imported subentry with the API id, description, zone, category."""
    title = f"TapHome api device {device_id}"
    if device is None:
        return title
    details = ", ".join(
        part
        for part in (device.description or device.name, device.zone, device.category)
        if part
    )
    return f"{title} - {details}" if details else title


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
        number_config = NumberSelectorConfig(
            step=option_field.step
            or (1 if option_field.kind == FieldKind.NUMBER_INT else 0.1),
            mode=NumberSelectorMode.BOX,
        )
        if option_field.min_value is not None:
            number_config["min"] = option_field.min_value
        if option_field.max_value is not None:
            number_config["max"] = option_field.max_value
        return NumberSelector(number_config)
    return TextSelector()


def _suggested_field_value(option_field: OptionField, value: Any) -> Any:
    """Convert a stored option value to the form's suggested value."""
    if option_field.kind in (
        FieldKind.DEVICE_ID,
        FieldKind.VALUE_TYPE,
        FieldKind.ENUM,
    ):
        return str(value)
    if option_field.kind == FieldKind.MULTI_ENUM:
        return [str(item) for item in value]
    return value


def _build_fields_schema(
    fields: tuple[OptionField, ...],
    device_config: dict,
    devices: dict[int, Device],
    device_label: Callable[[int], str],
) -> tuple[dict[Any, Any], dict[str, Any]]:
    """Build the schema dict and suggested values for the given fields."""
    schema_dict: dict[Any, Any] = {}
    suggested_values: dict[str, Any] = {}
    for option_field in fields:
        schema_dict[vol.Optional(option_field.key)] = build_field_selector(
            option_field, devices, device_label
        )
        value = device_config.get(option_field.key)
        if value is not None:
            suggested_values[option_field.key] = _suggested_field_value(
                option_field, value
            )
    return schema_dict, suggested_values


def build_device_options_schema(
    descriptor: PlatformDescriptor,
    device_config: dict,
    devices: dict[int, Device],
    device_label: Callable[[int], str],
) -> tuple[vol.Schema, dict[str, Any]]:
    """Build the per-device options form and its suggested values."""
    schema_dict, suggested_values = _build_fields_schema(
        descriptor.fields, device_config, devices, device_label
    )
    return vol.Schema(schema_dict), suggested_values


ADVANCED_OPTIONS_SECTION = "advanced_options"


def build_device_options_schema_split(
    descriptor: PlatformDescriptor,
    device_config: dict,
    devices: dict[int, Device],
    device_label: Callable[[int], str],
) -> tuple[vol.Schema, dict[str, Any]]:
    """Build the options form with the advanced fields in a collapsed section.

    Reconfigure always offers every field so a device can be converted between
    archetypes (e.g. a simple thermostat into a controlled one), but the
    advanced fields stay out of the way.
    """
    basic = tuple(field for field in descriptor.fields if not field.advanced)
    advanced = tuple(field for field in descriptor.fields if field.advanced)

    schema_dict, suggested_values = _build_fields_schema(
        basic, device_config, devices, device_label
    )
    if advanced:
        advanced_dict, advanced_suggested = _build_fields_schema(
            advanced, device_config, devices, device_label
        )
        schema_dict[vol.Optional(ADVANCED_OPTIONS_SECTION)] = section(
            vol.Schema(advanced_dict), {"collapsed": True}
        )
        if advanced_suggested:
            suggested_values[ADVANCED_OPTIONS_SECTION] = advanced_suggested
    return vol.Schema(schema_dict), suggested_values


def flatten_advanced_options(user_input: dict[str, Any]) -> dict[str, Any]:
    """Merge a submitted advanced section back into a flat field mapping."""
    flat = {
        key: value
        for key, value in user_input.items()
        if key != ADVANCED_OPTIONS_SECTION
    }
    flat.update(user_input.get(ADVANCED_OPTIONS_SECTION) or {})
    return flat


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
        if value is None or value in ("", []):
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


class _TapHomeDeviceArchetypeFlow:
    """Archetype add steps shared by the subentry flow and the options flow.

    Adding starts from a menu of user-facing device types (archetypes); each
    type asks only for what it needs. Subclasses provide the parent entry and
    how the collected subentry payloads are persisted, so the exact same steps
    back both the integration page's "Add device" and the Configure dialog.
    """

    _archetype: DeviceArchetype | None = None
    _archetype_device_id: int | None = None

    # Members provided by the hosting data-entry FlowHandler.
    async_show_form: Callable[..., Any]
    async_show_menu: Callable[..., Any]
    async_abort: Callable[..., Any]
    add_suggested_values_to_schema: Callable[..., Any]

    @property
    def _archetype_entry(self) -> ConfigEntry:
        """Return the config entry devices are added to."""
        raise NotImplementedError

    def _archetype_finish(self, payloads: list[ConfigSubentryData]) -> Any:
        """Persist the collected device subentries and end the flow."""
        raise NotImplementedError

    @property
    def _archetype_devices(self) -> dict[int, Device]:
        """Return the devices discovered by the loaded core."""
        return self._archetype_entry.runtime_data.hub.devices

    def _archetype_device_label(self, device: Device) -> str:
        """Return a human readable label of a TapHome device."""
        location = " · ".join(part for part in (device.zone, device.category) if part)
        label = f"{device.name} ({device.id})"
        return f"{label} — {location}" if location else label

    def _archetype_helper_label(self, device_id: int) -> str:
        """Label a device referenced from another device's option field."""
        device = self._archetype_devices.get(device_id)
        if device is None:
            return f"Unknown device ({device_id})"
        return self._archetype_device_label(device)

    def _archetype_value_title(self, device: Device, value: int) -> str:
        """Return the subentry title of one exposed device value."""
        return f"{device.name} — {_value_type_label(ValueType(value))}"

    def _archetype_unique_ids(self) -> set[str]:
        """Return the unique ids of the configured device subentries."""
        return {
            subentry.unique_id
            for subentry in iter_device_subentries(self._archetype_entry)
            if subentry.unique_id
        }

    def _archetype_configured_pairs(self) -> set[tuple[str, int]]:
        """Return the (platform, device id) pairs already exposed."""
        pairs: set[tuple[str, int]] = set()
        for subentry in iter_device_subentries(self._archetype_entry):
            platform = subentry_platform(subentry.data)
            device_id = subentry.data.get("id")
            if isinstance(platform, str) and isinstance(device_id, int):
                pairs.add((platform, device_id))
        return pairs

    def _archetype_device_level_pairs(self) -> set[tuple[str, int]]:
        """Return pairs exposed without a value (legacy auto-detect-all)."""
        pairs: set[tuple[str, int]] = set()
        for subentry in iter_device_subentries(self._archetype_entry):
            if "value" in subentry.data:
                continue
            platform = subentry_platform(subentry.data)
            device_id = subentry.data.get("id")
            if isinstance(platform, str) and isinstance(device_id, int):
                pairs.add((platform, device_id))
        return pairs

    def _archetype_available_values(
        self, archetype: DeviceArchetype, device: Device
    ) -> list[ValueType]:
        """Return the device values not yet exposed on the archetype's platform."""
        if (archetype.config_key, device.id) in self._archetype_device_level_pairs():
            # A legacy subentry already auto-exposes every known value.
            return []
        unique_ids = self._archetype_unique_ids()
        return [
            value_type
            for value_type in _KNOWN_VALUE_TYPES_BY_KEY[archetype.config_key]
            if device.supports_value(value_type)
            and device_subentry_unique_id(
                archetype.config_key, device.id, value_type.value
            )
            not in unique_ids
        ]

    def _archetype_addable_devices(self, archetype: DeviceArchetype) -> list[Device]:
        """Return the devices the archetype can still be added for."""
        descriptor = PLATFORM_DESCRIPTORS_BY_KEY[archetype.config_key]
        candidates = [
            device
            for device in self._archetype_devices.values()
            if _device_qualifies(device, descriptor)
        ]
        if archetype.values:
            return [
                device
                for device in candidates
                if self._archetype_available_values(archetype, device)
            ]
        configured = self._archetype_configured_pairs()
        return [
            device
            for device in candidates
            if (archetype.config_key, device.id) not in configured
        ]

    def _async_show_archetype_menu(self, step_id: str) -> Any:
        """Show the menu of device types."""
        return self.async_show_menu(
            step_id=step_id,
            menu_options=[archetype.key for archetype in DEVICE_ARCHETYPES],
        )

    # One step per archetype so each gets its own translated title and form.
    async def async_step_light(self, user_input=None) -> Any:
        """Add a light."""
        return await self._async_archetype_step("light", user_input)

    async def async_step_switch(self, user_input=None) -> Any:
        """Add a switch."""
        return await self._async_archetype_step("switch", user_input)

    async def async_step_cover(self, user_input=None) -> Any:
        """Add a cover."""
        return await self._async_archetype_step("cover", user_input)

    async def async_step_thermostat(self, user_input=None) -> Any:
        """Add a simple thermostat."""
        return await self._async_archetype_step("thermostat", user_input)

    async def async_step_thermostat_controlled(self, user_input=None) -> Any:
        """Add a thermostat that drives a switch or mode."""
        return await self._async_archetype_step("thermostat_controlled", user_input)

    async def async_step_thermostat_range(self, user_input=None) -> Any:
        """Add a range thermostat."""
        return await self._async_archetype_step("thermostat_range", user_input)

    async def async_step_sensor(self, user_input=None) -> Any:
        """Add sensor values of a device."""
        return await self._async_archetype_step("sensor", user_input)

    async def async_step_binary_sensor(self, user_input=None) -> Any:
        """Add binary sensor values of a device."""
        return await self._async_archetype_step("binary_sensor", user_input)

    async def async_step_fan(self, user_input=None) -> Any:
        """Add a fan."""
        return await self._async_archetype_step("fan", user_input)

    async def async_step_humidifier(self, user_input=None) -> Any:
        """Add a humidifier."""
        return await self._async_archetype_step("humidifier", user_input)

    async def async_step_valve(self, user_input=None) -> Any:
        """Add a valve."""
        return await self._async_archetype_step("valve", user_input)

    async def async_step_button(self, user_input=None) -> Any:
        """Add a button."""
        return await self._async_archetype_step("button", user_input)

    async def async_step_select(self, user_input=None) -> Any:
        """Add a select."""
        return await self._async_archetype_step("select", user_input)

    async def async_step_number(self, user_input=None) -> Any:
        """Add a number."""
        return await self._async_archetype_step("number", user_input)

    async def async_step_time(self, user_input=None) -> Any:
        """Add a time."""
        return await self._async_archetype_step("time", user_input)

    async def async_step_sensor_values(self, user_input=None) -> Any:
        """Pick the sensor values to expose."""
        return await self._async_values_step(user_input)

    async def async_step_binary_sensor_values(self, user_input=None) -> Any:
        """Pick the binary sensor values to expose."""
        return await self._async_values_step(user_input)

    async def _async_archetype_step(
        self, key: str, user_input: dict[str, Any] | None
    ) -> Any:
        """Show one archetype's add form: device picker plus its fields."""
        if self._archetype_entry.state is not ConfigEntryState.LOADED:
            return self.async_abort(reason="entry_not_loaded")
        archetype = DEVICE_ARCHETYPES_BY_KEY[key]
        self._archetype = archetype
        if archetype.range_thermostat:
            return await self._async_range_thermostat_step(user_input)

        descriptor = PLATFORM_DESCRIPTORS_BY_KEY[archetype.config_key]
        devices = self._archetype_addable_devices(archetype)
        if not devices:
            return self.async_abort(reason="no_devices_available")

        errors: dict[str, str] = {}
        if user_input is not None:
            self._archetype_device_id = int(user_input["device"])
            if archetype.values:
                return await self._async_next_values_step()
            field_errors: dict[str, str] = {}
            device_config = apply_device_options(
                descriptor, {"id": self._archetype_device_id}, user_input, field_errors
            )
            if field_errors:
                errors["base"] = "invalid_device_id"
            elif error := self._validate_archetype(archetype, device_config):
                errors["base"] = error
            else:
                return self._create_archetype_subentry(device_config)

        options = [
            SelectOptionDict(
                value=str(device.id), label=self._archetype_device_label(device)
            )
            for device in devices
        ]
        options.sort(key=lambda option: option["label"].casefold())
        schema_dict: dict[Any, Any] = {
            vol.Required("device"): SelectSelector(
                SelectSelectorConfig(options=options, mode=SelectSelectorMode.DROPDOWN)
            )
        }
        field_defs = tuple(
            field for field in descriptor.fields if field.key in archetype.fields
        )
        fields_schema, _ = _build_fields_schema(
            field_defs, {}, self._archetype_devices, self._archetype_helper_label
        )
        schema_dict.update(fields_schema)
        schema = vol.Schema(schema_dict)
        if user_input:
            schema = self.add_suggested_values_to_schema(schema, user_input)
        return self.async_show_form(step_id=key, data_schema=schema, errors=errors)

    @staticmethod
    def _validate_archetype(
        archetype: DeviceArchetype, device_config: dict
    ) -> str | None:
        """Validate archetype-specific field combinations."""
        if archetype.key != "thermostat_controlled":
            return None
        # Mirrors the accepted combinations of climate.create_hvac_controller;
        # the empty combination is the plain thermostat archetype.
        switch = device_config.get("hvac_switch_id")
        mode = device_config.get("hvac_mode")
        mode_id = device_config.get("hvac_mode_id")
        valid = (
            (switch and mode and not mode_id)
            or (switch and mode_id and not mode)
            or (mode_id and not switch and not mode)
        )
        return None if valid else "invalid_hvac_config"

    async def _async_range_thermostat_step(
        self, user_input: dict[str, Any] | None
    ) -> Any:
        """Add a range thermostat from its high and low thermostats."""
        archetype = self._archetype
        assert archetype is not None
        descriptor = PLATFORM_DESCRIPTORS_BY_KEY[archetype.config_key]

        errors: dict[str, str] = {}
        if user_input is not None:
            field_errors: dict[str, str] = {}
            device_config = apply_device_options(
                descriptor, {}, user_input, field_errors
            )
            high = device_config.get("range_high_thermostat_id")
            low = device_config.get("range_low_thermostat_id")
            if field_errors:
                errors["base"] = "invalid_device_id"
            elif not high or not low:
                errors["base"] = "range_thermostats_required"
            elif (archetype.config_key, high) in self._archetype_configured_pairs():
                errors["base"] = "already_configured"
            else:
                device_config["id"] = high
                return self._create_archetype_subentry(device_config)

        field_defs = tuple(
            field for field in descriptor.fields if field.key in archetype.fields
        )
        fields_schema, _ = _build_fields_schema(
            field_defs, {}, self._archetype_devices, self._archetype_helper_label
        )
        schema = vol.Schema(fields_schema)
        if user_input:
            schema = self.add_suggested_values_to_schema(schema, user_input)
        return self.async_show_form(
            step_id="thermostat_range", data_schema=schema, errors=errors
        )

    async def _async_next_values_step(self) -> Any:
        """Continue to the value selection of the picked device."""
        assert self._archetype is not None
        if self._archetype.config_key == CONF_SENSORS:
            return await self.async_step_sensor_values()
        return await self.async_step_binary_sensor_values()

    async def _async_values_step(self, user_input: dict[str, Any] | None) -> Any:
        """Pick the device values to expose; each becomes its own subentry."""
        archetype = self._archetype
        assert archetype is not None and self._archetype_device_id is not None
        device = self._archetype_devices.get(self._archetype_device_id)
        if device is None:
            return self.async_abort(reason="no_devices_available")
        available = self._archetype_available_values(archetype, device)
        if not available:
            return self.async_abort(reason="no_devices_available")

        errors: dict[str, str] = {}
        if user_input is not None:
            selected = [int(value) for value in user_input.get("values", [])]
            if not selected:
                errors["base"] = "no_values_selected"
            else:
                return self._archetype_finish(
                    [
                        build_device_subentry_data(
                            archetype.config_key,
                            {"id": device.id, "value": value},
                            self._archetype_value_title(device, value),
                        )
                        for value in selected
                    ]
                )

        options = [
            SelectOptionDict(
                value=str(value_type.value), label=_value_type_label(value_type)
            )
            for value_type in available
        ]
        options.sort(key=lambda option: option["label"])
        schema = vol.Schema(
            {
                vol.Required(
                    "values", default=[option["value"] for option in options]
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
            step_id=f"{archetype.key}_values",
            data_schema=schema,
            errors=errors,
            description_placeholders={"device": self._archetype_device_label(device)},
        )

    def _create_archetype_subentry(self, device_config: dict) -> Any:
        """Persist the collected device configuration as a subentry."""
        archetype = self._archetype
        assert archetype is not None
        device = self._archetype_devices.get(device_config["id"])
        if device is not None and "value" in device_config:
            title = self._archetype_value_title(device, device_config["value"])
        elif device is not None:
            title = self._archetype_device_label(device)
        else:
            title = f"TapHome device {device_config['id']}"
        return self._archetype_finish(
            [build_device_subentry_data(archetype.config_key, device_config, title)]
        )


class _TapHomeSetupFlow(ConfigEntryBaseFlow):
    """Shared zone, label and device setup steps for config and options flows.

    Mixed into ConfigFlow/OptionsFlow subclasses. ``config_entry`` is only
    touched by the options-flow steps, where OptionsFlow provides it.
    """

    config_entry: ConfigEntry

    _options: dict[str, Any]
    _setup_wizard: bool = False

    def __init__(self) -> None:
        """Initialize the shared setup flow state."""
        super().__init__()
        self._options = {}
        self._pending_device_ids: list[int] = []
        self._pending_pairs: list[tuple[int, str]] = []
        self._pending_subentries: list[ConfigSubentryData] = []
        self._selected_subentry_ids: list[str] = []

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

        # "Add device" opens the same archetype flow as the integration
        # page's native Add device button — one unified add experience.
        return self.async_show_menu(
            step_id="init",
            menu_options=[
                "core_settings",
                "add_device",
                "edit_device",
                "remove_device",
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
            # The selector limits the values to the known device ids.
            device_ids = [int(value) for value in user_input.get("devices", [])]
            if not device_ids:
                errors["base"] = "no_devices_selected"
            else:
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
            field_schema, _ = self._build_device_options_schema(
                descriptor, {"id": device_id}
            )
            section_key = self._pair_section_key(device_id, config_key)
            schema_dict[vol.Optional(section_key)] = section(
                field_schema, {"collapsed": descriptor.advanced}
            )

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
        """Build a device subentry for each pending device/platform pair.

        Returns the form errors; an empty mapping means everything was applied
        and the resulting subentries are stored in ``self._pending_subentries``.
        """
        errors: dict[str, str] = {}
        configured = self._configured_pairs()
        subentries: list[ConfigSubentryData] = []
        for device_id, config_key in self._pending_pairs:
            if (config_key, device_id) in configured:
                continue
            descriptor = PLATFORM_DESCRIPTORS_BY_KEY[config_key]
            section_input = (
                user_input.get(self._pair_section_key(device_id, config_key)) or {}
            )
            field_errors: dict[str, str] = {}
            device_config = self._apply_device_options(
                descriptor, {"id": device_id}, section_input, field_errors
            )
            if field_errors:
                errors["base"] = "invalid_device_id"
            subentries.append(self._device_subentry_data(config_key, device_config))
            configured.add((config_key, device_id))
        if errors:
            return errors
        self._pending_subentries = subentries
        return {}

    def _device_subentry_data(
        self, config_key: str, device_config: dict
    ) -> ConfigSubentryData:
        """Build the subentry payload for one exposed device."""
        title = self._device_label(device_config_id(device_config))
        return build_device_subentry_data(config_key, device_config, title)

    def _async_save_options(self) -> ConfigFlowResult:
        """Store the edited options; the update listener reloads the entry."""
        return self.async_create_entry(title="", data=self._options)

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

    def _device_subentries(self) -> list[dict]:
        """Return the data of the configured device subentries.

        Overridden by the options flow, which reads the loaded entry. The setup
        wizard has no entry yet, so nothing is configured while it runs.
        """
        return []

    def _configured_pairs(self) -> set[tuple[str, int]]:
        """Return the (platform, device id) pairs already exposed."""
        pairs: set[tuple[str, int]] = set()
        for data in self._device_subentries():
            platform = subentry_platform(data)
            if platform is not None and "id" in data:
                pairs.add((platform, device_config_id(data)))
        return pairs

    def _configured_device_ids(self) -> set[int]:
        """Return the ids of all devices exposed by a subentry."""
        return {
            device_config_id(data)
            for data in self._device_subentries()
            if "id" in data
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
                if item.get("ignore"):
                    new_mapping[name] = {"ignore": True}
                elif isinstance(target, str) and target:
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
            ignored = isinstance(mapped, dict) and bool(mapped.get("ignore"))
            schema_dict[vol.Required(name)] = section(
                vol.Schema(
                    {
                        vol.Optional(
                            field_key,
                            description={"suggested_value": suggested},
                        ): target_selector,
                        vol.Optional(
                            "ignore", default=ignored
                        ): BooleanSelector(),
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

    def _apply_device_options(
        self,
        descriptor: PlatformDescriptor,
        device_config: dict,
        user_input: dict[str, Any],
        errors: dict[str, str],
    ) -> dict:
        """Merge submitted per-device options into the stored device config."""
        return apply_device_options(descriptor, device_config, user_input, errors)


class TapHomeOptionsFlow(_TapHomeDeviceArchetypeFlow, _TapHomeSetupFlow, OptionsFlow):
    """Handle the TapHome options flow."""

    @property
    def _hub(self) -> TapHomeHub:
        """Return the live hub of the loaded config entry."""
        return self.config_entry.runtime_data.hub

    @property
    def _devices(self) -> dict[int, Device]:
        """Return the devices discovered by the loaded core."""
        return self._hub.devices

    def _device_subentries(self) -> list[dict]:
        """Return the data of the loaded entry's device subentries."""
        return [
            dict(subentry.data)
            for subentry in iter_device_subentries(self.config_entry)
        ]

    async def _async_commit(self, completed: str) -> ConfigFlowResult:
        """Persist the completed section; the update listener reloads the entry."""
        return self._async_save_options()

    @property
    def _archetype_entry(self) -> ConfigEntry:
        """Return the config entry devices are added to."""
        return self.config_entry

    def _archetype_finish(
        self, payloads: list[ConfigSubentryData]
    ) -> ConfigFlowResult:
        """Add every collected subentry and end the options flow."""
        for payload in payloads:
            self.hass.config_entries.async_add_subentry(
                self.config_entry, config_subentry_from_data(payload)
            )
        return self.async_abort(reason="device_added")

    async def async_step_add_device(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Choose the type of device to add — the same flow as Add device."""
        return self._async_show_archetype_menu("add_device")

    async def async_step_edit_device(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Find a configured device to edit by device or entity."""
        return await self._async_pick_device_step("edit_device", user_input)

    async def async_step_remove_device(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Find a configured device to remove by device or entity."""
        return await self._async_pick_device_step("remove_device", user_input)

    async def _async_pick_device_step(
        self, step_id: str, user_input: dict[str, Any] | None
    ) -> ConfigFlowResult:
        """Resolve a picked target to its device subentries.

        The same target picker as in automations: the user can pick entities,
        devices, areas or labels — whichever they know. Purely a findability
        feature; the follow-up steps use the same subentry mechanics as the
        device page.
        """
        errors: dict[str, str] = {}
        if user_input is not None:
            subentries = self._resolve_target_selection(
                user_input.get("target") or {}, errors
            )
            if not errors:
                self._selected_subentry_ids = [
                    subentry.subentry_id for subentry in subentries
                ]
                if step_id == "remove_device":
                    return await self.async_step_remove_device_confirm()
                if len(subentries) == 1:
                    return await self.async_step_edit_device_form()
                return await self.async_step_edit_device_pick()

        schema = vol.Schema(
            {
                vol.Required("target"): TargetSelector(
                    TargetSelectorConfig(
                        entity=[EntityFilterSelectorConfig(integration=DOMAIN)],
                        device=[DeviceFilterSelectorConfig(integration=DOMAIN)],
                    )
                ),
            }
        )
        if user_input:
            schema = self.add_suggested_values_to_schema(schema, user_input)
        return self.async_show_form(
            step_id=step_id, data_schema=schema, errors=errors, last_step=False
        )

    def _resolve_target_selection(
        self, target: dict[str, Any], errors: dict[str, str]
    ) -> list[ConfigSubentry]:
        """Return the device subentries behind a picked target.

        Areas, floors and labels fan out to this entry's devices and entities
        in them; entities resolve through their subentry, devices through their
        subentry links.
        """
        entry = self.config_entry
        entity_registry = er.async_get(self.hass)
        device_registry = dr.async_get(self.hass)

        entity_ids = _target_ids(target, "entity_id")
        device_ids = _target_ids(target, "device_id")
        area_ids = _target_ids(target, "area_id")
        label_ids = _target_ids(target, "label_id")

        if not (entity_ids or device_ids or area_ids or label_ids
                or _target_ids(target, "floor_id")):
            errors["base"] = "select_target"
            return []

        for floor_id in _target_ids(target, "floor_id"):
            area_ids.extend(
                area.id
                for area in ar.async_get(self.hass).async_list_areas()
                if area.floor_id == floor_id
            )
        for area_id in area_ids:
            device_ids.extend(
                device.id
                for device in dr.async_entries_for_area(device_registry, area_id)
            )
            entity_ids.extend(
                registry_entry.entity_id
                for registry_entry in er.async_entries_for_area(
                    entity_registry, area_id
                )
            )
        for label_id in label_ids:
            device_ids.extend(
                device.id
                for device in dr.async_entries_for_label(device_registry, label_id)
            )
            entity_ids.extend(
                registry_entry.entity_id
                for registry_entry in er.async_entries_for_label(
                    entity_registry, label_id
                )
            )

        subentry_ids: list[str] = []
        for entity_id in entity_ids:
            registry_entry = entity_registry.async_get(entity_id)
            if (
                registry_entry is not None
                and registry_entry.config_entry_id == entry.entry_id
                and registry_entry.config_subentry_id is not None
            ):
                subentry_ids.append(registry_entry.config_subentry_id)
        for device_id in device_ids:
            device = device_registry.async_get(device_id)
            if device is not None:
                subentry_ids.extend(
                    sorted(
                        subentry_id
                        for subentry_id in device.config_entries_subentries.get(
                            entry.entry_id, set()
                        )
                        if subentry_id is not None
                    )
                )

        subentries = [
            entry.subentries[subentry_id]
            for subentry_id in dict.fromkeys(subentry_ids)
            if subentry_id in entry.subentries
        ]
        if not subentries:
            errors["base"] = "no_device_config"
        return subentries

    def _selected_subentries(self) -> list[ConfigSubentry]:
        """Return the still existing subentries of the current selection."""
        entry = self.config_entry
        return [
            entry.subentries[subentry_id]
            for subentry_id in self._selected_subentry_ids
            if subentry_id in entry.subentries
        ]

    async def async_step_edit_device_pick(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Pick which of the device's configurations to edit."""
        subentries = self._selected_subentries()
        if not subentries:
            return self.async_abort(reason="no_device_config")

        if user_input is not None:
            self._selected_subentry_ids = [user_input["config"]]
            return await self.async_step_edit_device_form()

        options = [
            SelectOptionDict(value=subentry.subentry_id, label=subentry.title)
            for subentry in subentries
        ]
        return self.async_show_form(
            step_id="edit_device_pick",
            data_schema=vol.Schema(
                {
                    vol.Required("config"): SelectSelector(
                        SelectSelectorConfig(
                            options=options, mode=SelectSelectorMode.DROPDOWN
                        )
                    )
                }
            ),
            last_step=False,
        )

    async def async_step_edit_device_form(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Edit the picked device configuration (same form as reconfigure)."""
        subentries = self._selected_subentries()
        if not subentries:
            return self.async_abort(reason="no_device_config")
        subentry = subentries[0]
        config_key = subentry_platform(subentry.data)
        descriptor = PLATFORM_DESCRIPTORS_BY_KEY.get(config_key)
        if descriptor is None:
            return self.async_abort(reason="unknown_subentry")
        device_config = device_config_from_subentry(subentry.data)

        errors: dict[str, str] = {}
        if user_input is not None:
            field_errors: dict[str, str] = {}
            new_config = apply_device_options(
                descriptor,
                device_config,
                flatten_advanced_options(user_input),
                field_errors,
            )
            if field_errors:
                errors["base"] = "invalid_device_id"
            else:
                self.hass.config_entries.async_update_subentry(
                    self.config_entry,
                    subentry,
                    data=device_subentry_payload(config_key, new_config),
                )
                return self.async_abort(reason="reconfigure_successful")

        schema, suggested = build_device_options_schema_split(
            descriptor, device_config, self._devices, self._device_label
        )
        return self.async_show_form(
            step_id="edit_device_form",
            data_schema=self.add_suggested_values_to_schema(
                schema, user_input or suggested
            ),
            errors=errors,
            description_placeholders={"device": subentry.title},
        )

    async def async_step_remove_device_confirm(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Review the resolved devices, untick any to keep, remove the rest."""
        subentries = self._selected_subentries()
        if not subentries:
            return self.async_abort(reason="no_device_config")

        errors: dict[str, str] = {}
        if user_input is not None:
            checked = {int(value) for value in user_input.get("devices", [])}
            if not checked:
                errors["base"] = "no_devices_selected"
            else:
                for subentry in subentries:
                    if subentry.data.get("id") in checked:
                        self.hass.config_entries.async_remove_subentry(
                            self.config_entry, subentry.subentry_id
                        )
                return self.async_abort(reason="device_removed")

        device_ids = sorted(
            {
                device_id
                for subentry in subentries
                if isinstance(device_id := subentry.data.get("id"), int)
            }
        )
        options = [
            SelectOptionDict(value=str(device_id), label=self._device_label(device_id))
            for device_id in device_ids
        ]
        options.sort(key=lambda option: option["label"].casefold())
        return self.async_show_form(
            step_id="remove_device_confirm",
            data_schema=vol.Schema(
                {
                    vol.Required(
                        "devices", default=[option["value"] for option in options]
                    ): SelectSelector(
                        SelectSelectorConfig(
                            options=options,
                            multiple=True,
                            mode=SelectSelectorMode.LIST,
                        )
                    )
                }
            ),
            errors=errors,
        )


class TapHomeConfigFlow(_TapHomeSetupFlow, ConfigFlow, domain=DOMAIN):
    """Handle the TapHome config flow."""

    VERSION = 1
    MINOR_VERSION = 2

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

    @classmethod
    @callback
    def async_get_supported_subentry_types(
        cls, config_entry: ConfigEntry
    ) -> dict[str, type[ConfigSubentryFlow]]:
        """Return the subentry types this integration supports."""
        return {SUBENTRY_TYPE_DEVICE: TapHomeDeviceSubentryFlowHandler}

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
        # pylint mis-resolves the ConfigFlow.async_create_entry override.
        return self.async_create_entry(  # pylint: disable=unexpected-keyword-arg
            title=self._wizard_title,
            data=self._wizard_data,
            options=self._options,
            subentries=self._pending_subentries,
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
        devices: dict[int, Device] = {}
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
            try:
                # Best effort: device metadata makes the subentry titles
                # human readable (description, zone, category).
                devices = await _async_load_devices(
                    async_get_clientsession(self.hass), api_url, token
                )
            except (TapHomeAuthError, CannotConnectError):
                devices = {}

        await self.async_set_unique_id(unique_id)
        self._abort_if_unique_id_configured()

        # pylint mis-resolves the ConfigFlow.async_create_entry override.
        return self.async_create_entry(  # pylint: disable=unexpected-keyword-arg
            title=title,
            data={
                CONF_TOKEN: token,
                CONF_API_URL: api_url,
                CONF_ID: core_id,
            },
            options=_yaml_core_to_options(import_data),
            subentries=_yaml_device_subentries(import_data, devices),
        )




class TapHomeDeviceSubentryFlowHandler(_TapHomeDeviceArchetypeFlow, ConfigSubentryFlow):
    """Add, edit and remove a single exposed TapHome device.

    The archetype add steps come from the shared mixin; the device page's Edit
    offers every option (advanced ones collapsed) and Delete removes the
    subentry. Every subentry mutation fires the entry's reload listener.
    """

    @property
    def _archetype_entry(self) -> ConfigEntry:
        """Return the parent config entry."""
        return self._get_entry()

    def _archetype_finish(
        self, payloads: list[ConfigSubentryData]
    ) -> SubentryFlowResult:
        """Add all but the last subentry directly; the last ends the flow."""
        for payload in payloads[:-1]:
            self.hass.config_entries.async_add_subentry(
                self._archetype_entry, config_subentry_from_data(payload)
            )
        last = payloads[-1]
        return self.async_create_entry(
            title=last["title"], data=last["data"], unique_id=last["unique_id"]
        )

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> SubentryFlowResult:
        """Choose the type of device to add."""
        if self._archetype_entry.state is not ConfigEntryState.LOADED:
            return self.async_abort(reason="entry_not_loaded")
        return self._async_show_archetype_menu("user")

    async def async_step_reconfigure(
        self, user_input: dict[str, Any] | None = None
    ) -> SubentryFlowResult:
        """Edit the options of an already exposed device."""
        if self._archetype_entry.state is not ConfigEntryState.LOADED:
            return self.async_abort(reason="entry_not_loaded")

        subentry = self._get_reconfigure_subentry()
        config_key = subentry_platform(subentry.data)
        descriptor = PLATFORM_DESCRIPTORS_BY_KEY.get(config_key)
        if descriptor is None:
            return self.async_abort(reason="unknown_subentry")
        device_config = device_config_from_subentry(subentry.data)

        errors: dict[str, str] = {}
        if user_input is not None:
            field_errors: dict[str, str] = {}
            new_config = apply_device_options(
                descriptor,
                device_config,
                flatten_advanced_options(user_input),
                field_errors,
            )
            if field_errors:
                errors["base"] = "invalid_device_id"
            else:
                return self.async_update_and_abort(
                    self._archetype_entry,
                    subentry,
                    data=device_subentry_payload(config_key, new_config),
                )

        schema, suggested = build_device_options_schema_split(
            descriptor,
            device_config,
            self._archetype_devices,
            self._archetype_helper_label,
        )
        return self.async_show_form(
            step_id="reconfigure",
            data_schema=self.add_suggested_values_to_schema(
                schema, user_input or suggested
            ),
            errors=errors,
        )
