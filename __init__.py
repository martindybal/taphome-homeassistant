"""TapHome integration."""

# sdk_locator must be imported before anything imports taphome_sdk, which
# breaks the usual import ordering on purpose.
# pylint: disable=wrong-import-order

from . import sdk_locator  # noqa: F401

from dataclasses import dataclass
import logging

from aiohttp.web import Request
import voluptuous as vol

from homeassistant.components.binary_sensor import DOMAIN as BINARY_SENSOR_DOMAIN
from homeassistant.components.button import DOMAIN as BUTTON_DOMAIN
from homeassistant.components.climate import DOMAIN as CLIMATE_DOMAIN
from homeassistant.components.cover import DOMAIN as COVER_DOMAIN
from homeassistant.components.event import DOMAIN as EVENT_DOMAIN
from homeassistant.components.fan import DOMAIN as FAN_DOMAIN
from homeassistant.components.humidifier import DOMAIN as HUMIDIFIER_DOMAIN
from homeassistant.components.light import DOMAIN as LIGHT_DOMAIN
from homeassistant.components.number import DOMAIN as NUMBER_DOMAIN
from homeassistant.components.select import DOMAIN as SELECT_DOMAIN
from homeassistant.components.sensor import DOMAIN as SENSOR_DOMAIN
from homeassistant.components.switch import DOMAIN as SWITCH_DOMAIN
from homeassistant.components.time import DOMAIN as TIME_DOMAIN
from homeassistant.components.valve import DOMAIN as VALVE_DOMAIN
from homeassistant.components.webhook import (
    async_register as async_register_webhook,
    async_unregister as async_unregister_webhook,
)
from homeassistant.config_entries import SOURCE_IMPORT, ConfigEntryState
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
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryAuthFailed, ConfigEntryNotReady
from homeassistant.helpers import (
    config_validation as cv,
    device_registry as dr,
    entity_registry as er,
    issue_registry as ir,
)
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.typing import ConfigType

from .binary_sensor import BinarySensorEntityConfig
from .button import TapHomeButtonConfig
from .climate import TapHomeClimateConfig
from .const import (
    AVAILABLE_ATTRIBUTES,
    CONF_API_URL,
    CONF_BUTTONS,
    CONF_CLIMATES,
    CONF_CORES,
    CONF_ENABLED_ATTRIBUTES,
    CONF_FAN,
    CONF_HUMIDIFIER,
    CONF_IP,
    CONF_KNOWN_DEVICE_IDS,
    CONF_LABELS,
    CONF_LANGUAGE,
    CONF_MULTIVALUE_SWITCHES,
    CONF_NUMBERS,
    CONF_TIMES,
    CONF_UPDATE_INTERVAL,
    CONF_VALVE,
    CONF_ZONES,
    DOMAIN,
    PLATFORMS,
    TAPHOME_PLATFORM,
    USE_DESCRIPTION_AS_ENTITY_ID,
    USE_DESCRIPTION_AS_NAME,
)
from .cover import TapHomeCoverConfig
from .fan import TapHomeFanConfig
from .entity import hub_device_id
from .humidifier import TapHomeHumidifierConfig
from .light import TapHomeLightConfig
from .platform_descriptors import device_config_id
from .sensor import TapHomeSensorConfig
from .switch import TapHomeSwitchConfig
from .taphome_config_entry import (
    AddEntryRequest,
    NameMapping,
    TapHomeCoreConfig,
    TapHomeEntityConfig,
)
from .subentry import (
    build_device_subentry,
    device_config_from_subentry,
    iter_device_subentries,
    subentry_platform,
)
from .taphome_data import TapHomeConfigEntry, TapHomeRuntimeData
from .taphome_issue_registry import TapHomeIssueRegistry
from taphome_sdk import (
    HubConnectionState,
    TapHomeAuthError,
    TapHomeError,
    TapHomeHub,
    TapHomeHubFactory,
)
from .translations import Issues
from .valve import TapHomeValveConfig

_LOGGER = logging.getLogger(__name__)


@dataclass(slots=True, frozen=True)
class DomainDefinition:
    """Bind a Home Assistant platform domain to its TapHome configuration."""

    name: str
    config_key: str
    config_entry_type: type


DOMAIN_DEFINITIONS: tuple[DomainDefinition, ...] = (
    DomainDefinition(BINARY_SENSOR_DOMAIN, CONF_BINARY_SENSORS, BinarySensorEntityConfig),
    DomainDefinition(BUTTON_DOMAIN, CONF_BUTTONS, TapHomeButtonConfig),
    DomainDefinition(EVENT_DOMAIN, CONF_BUTTONS, TapHomeButtonConfig),
    DomainDefinition(CLIMATE_DOMAIN, CONF_CLIMATES, TapHomeClimateConfig),
    DomainDefinition(COVER_DOMAIN, CONF_COVERS, TapHomeCoverConfig),
    DomainDefinition(LIGHT_DOMAIN, CONF_LIGHTS, TapHomeLightConfig),
    DomainDefinition(FAN_DOMAIN, CONF_FAN, TapHomeFanConfig),
    DomainDefinition(VALVE_DOMAIN, CONF_VALVE, TapHomeValveConfig),
    DomainDefinition(HUMIDIFIER_DOMAIN, CONF_HUMIDIFIER, TapHomeHumidifierConfig),
    DomainDefinition(SELECT_DOMAIN, CONF_MULTIVALUE_SWITCHES, TapHomeEntityConfig),
    DomainDefinition(SENSOR_DOMAIN, CONF_SENSORS, TapHomeSensorConfig),
    DomainDefinition(SWITCH_DOMAIN, CONF_SWITCHES, TapHomeSwitchConfig),
    DomainDefinition(TIME_DOMAIN, CONF_TIMES, TapHomeEntityConfig),
    DomainDefinition(NUMBER_DOMAIN, CONF_NUMBERS, TapHomeEntityConfig),
)


CONFIG_SCHEMA = vol.Schema(
    {
        TAPHOME_PLATFORM: vol.Schema(
            {
                vol.Optional(CONF_LANGUAGE): cv.string,
                CONF_CORES: [
                    vol.All(
                        cv.has_at_least_one_key(
                            CONF_LIGHTS,
                            CONF_BUTTONS,
                            CONF_COVERS,
                            CONF_CLIMATES,
                            CONF_FAN,
                            CONF_HUMIDIFIER,
                            CONF_MULTIVALUE_SWITCHES,
                            CONF_VALVE,
                            CONF_SWITCHES,
                            CONF_SENSORS,
                            CONF_BINARY_SENSORS,
                            CONF_NUMBERS,
                            CONF_TIMES,
                        ),
                        {
                            vol.Required(CONF_TOKEN): cv.string,
                            vol.Optional(CONF_ID): cv.string,
                            vol.Optional(CONF_IP): cv.string,
                            vol.Optional(CONF_API_URL): cv.string,
                            vol.Optional(CONF_WEBHOOK_ID): cv.string,
                            vol.Optional(CONF_UPDATE_INTERVAL): cv.positive_float,
                            vol.Optional(USE_DESCRIPTION_AS_ENTITY_ID): cv.boolean,
                            vol.Optional(USE_DESCRIPTION_AS_NAME): cv.boolean,
                            vol.Optional(CONF_ZONES): vol.Any(
                                None,
                                {
                                    str: vol.Any(
                                        str, {vol.Required("ignore"): cv.boolean}
                                    )
                                },
                            ),
                            vol.Optional(CONF_LABELS): vol.Any(
                                None,
                                {
                                    str: vol.Any(
                                        str, {vol.Required("ignore"): cv.boolean}
                                    )
                                },
                            ),
                            vol.Optional(
                                CONF_ENABLED_ATTRIBUTES, default=AVAILABLE_ATTRIBUTES
                            ): cv.ensure_list,
                            vol.Optional(CONF_LIGHTS, default=[]): cv.ensure_list,
                            vol.Optional(CONF_BUTTONS, default=[]): cv.ensure_list,
                            vol.Optional(CONF_COVERS, default=[]): cv.ensure_list,
                            vol.Optional(CONF_CLIMATES, default=[]): cv.ensure_list,
                            vol.Optional(CONF_FAN, default=[]): cv.ensure_list,
                            vol.Optional(CONF_HUMIDIFIER, default=[]): cv.ensure_list,
                            vol.Optional(
                                CONF_MULTIVALUE_SWITCHES, default=[]
                            ): cv.ensure_list,
                            vol.Optional(CONF_SWITCHES, default=[]): cv.ensure_list,
                            vol.Optional(CONF_SENSORS, default=[]): cv.ensure_list,
                            vol.Optional(
                                CONF_BINARY_SENSORS, default=[]
                            ): cv.ensure_list,
                            vol.Optional(CONF_VALVE, default=[]): cv.ensure_list,
                            vol.Optional(CONF_NUMBERS, default=[]): cv.ensure_list,
                            vol.Optional(CONF_TIMES, default=[]): cv.ensure_list,
                        },
                    )
                ],
            }
        )
    },
    extra=vol.ALLOW_EXTRA,
)


async def async_setup(hass: HomeAssistant, config: ConfigType) -> bool:
    """Import legacy YAML configuration into config entries."""
    if TAPHOME_PLATFORM not in config:
        return True

    yaml_config = config[TAPHOME_PLATFORM]
    cores = yaml_config.get(CONF_CORES, [])

    if len(cores) > 1:
        for core_config in cores:
            if CONF_ID not in core_config:
                _LOGGER.error(
                    "You have to specify an 'id' if you are using multiple cores"
                )
                return False

    for core_config in cores:
        hass.async_create_task(
            hass.config_entries.flow.async_init(
                DOMAIN, context={"source": SOURCE_IMPORT}, data=core_config
            )
        )

    if cores:
        ir.async_create_issue(
            hass,
            DOMAIN,
            Issues.YAML_DEPRECATED,
            is_fixable=False,
            severity=ir.IssueSeverity.WARNING,
            translation_key=Issues.YAML_DEPRECATED,
            learn_more_url=(
                "https://github.com/martindybal/taphome-homeassistant"
                "/blob/production/docs/user-guide.md#migrating-from-yaml"
            ),
        )

    return True


async def async_setup_entry(hass: HomeAssistant, entry: TapHomeConfigEntry) -> bool:
    """Set up a TapHome core from a config entry."""
    core_config = _build_core_config(entry)
    taphome_issue_registry = TapHomeIssueRegistry(hass, core_config.id)

    try:
        hub = await TapHomeHubFactory.async_connect(
            entry.data[CONF_API_URL],
            entry.data[CONF_TOKEN],
            async_get_clientsession(hass),
        )
    except TapHomeAuthError as error:
        raise ConfigEntryAuthFailed(
            "TapHome API rejected the configured token"
        ) from error
    except Exception as error:
        raise ConfigEntryNotReady(
            f"Failed to connect to TapHome core: {error}"
        ) from error

    if hub.connection_state.value != HubConnectionState.CONNECTED:
        hub.disconnect()
        raise ConfigEntryNotReady("TapHome hub is not connected")

    unavailable_logged = False

    def hub_connection_state_changed(
        _: HubConnectionState, state: HubConnectionState
    ) -> None:
        """Handle changes in hub connection state."""
        nonlocal unavailable_logged
        if state == HubConnectionState.CONNECTED:
            if unavailable_logged:
                _LOGGER.info("Connection to the TapHome Core re-established")
                unavailable_logged = False
            taphome_issue_registry.try_delete_core_unavailable_issue()
        else:
            if not unavailable_logged:
                _LOGGER.info(
                    "Connection to the TapHome Core lost;"
                    " entities are unavailable until it recovers"
                )
                unavailable_logged = True
            if state == HubConnectionState.AUTH_FAILED:
                # The token stopped working at runtime; reauth prompts for a
                # new one instead of reporting the Core as unreachable.
                entry.async_start_reauth(hass)
            else:
                taphome_issue_registry.create_core_unavailable_issue()

    hub.connection_state.changed += hub_connection_state_changed

    _register_hub_device(hass, entry, hub)
    _register_webhook(hass, entry, hub, core_config)
    _async_remove_stale_entities(hass, entry)
    _async_detect_new_devices(
        hass, entry, hub, taphome_issue_registry, set(hub.devices)
    )
    _subscribe_new_device_detection(hass, entry, hub, taphome_issue_registry)

    add_entry_requests = {
        domain.name: _map_subentry_requests(hass, core_config, entry, domain, hub)
        for domain in DOMAIN_DEFINITIONS
    }

    entry.runtime_data = TapHomeRuntimeData(
        hub, core_config, add_entry_requests, hub_connection_state_changed
    )

    entry.async_on_unload(entry.add_update_listener(_async_update_listener))

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    return True


async def async_unload_entry(hass: HomeAssistant, entry: TapHomeConfigEntry) -> bool:
    """Unload a TapHome config entry."""
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unload_ok:
        runtime_data = entry.runtime_data
        runtime_data.hub.connection_state.changed -= (
            runtime_data.connection_state_handler
        )
        runtime_data.hub.disconnect()
    return unload_ok


async def async_migrate_entry(
    hass: HomeAssistant, entry: TapHomeConfigEntry
) -> bool:
    """Migrate old config entries to the current version."""
    if entry.version == 1 and entry.minor_version < 2:
        _migrate_devices_to_subentries(hass, entry)
    return True


def _migrate_devices_to_subentries(
    hass: HomeAssistant, entry: TapHomeConfigEntry
) -> None:
    """Move per-platform device option lists into one subentry per device.

    Each ``options[<config_key>]`` device becomes a ``device`` subentry; the
    existing entities and their device are re-homed to it (keeping their unique
    ids, so history is preserved) and the device lists are dropped from options.
    """
    from .config_flow import _normalize_device_config  # noqa: PLC0415

    entity_registry = er.async_get(hass)
    device_registry = dr.async_get(hass)
    domain_to_key = {
        definition.name: definition.config_key for definition in DOMAIN_DEFINITIONS
    }
    device_config_keys = list(
        dict.fromkeys(definition.config_key for definition in DOMAIN_DEFINITIONS)
    )

    entities = er.async_entries_for_config_entry(entity_registry, entry.entry_id)
    name_by_device: dict[tuple[str, int], str] = {}
    name_by_unique_id: dict[str, str] = {}
    for registry_entry in entities:
        device = (
            device_registry.async_get(registry_entry.device_id)
            if registry_entry.device_id
            else None
        )
        if device is None or not device.name:
            continue
        config_key = domain_to_key.get(registry_entry.domain)
        device_id = _parse_device_id_from_unique_id(registry_entry.unique_id)
        if config_key is not None and device_id is not None:
            name_by_device.setdefault((config_key, device_id), device.name)
        name_by_unique_id.setdefault(registry_entry.unique_id, device.name)

    new_options = dict(entry.options)
    subentry_by_device: dict[tuple[str, int], str] = {}
    subentry_by_unique_id: dict[str, str] = {}
    for config_key in device_config_keys:
        for raw_config in new_options.pop(config_key, None) or []:
            device_config = _normalize_device_config(config_key, raw_config)
            device_id = device_config_id(device_config)
            custom_unique_id = device_config.get("unique_id")
            title = name_by_device.get((config_key, device_id))
            if title is None and isinstance(custom_unique_id, str):
                title = name_by_unique_id.get(custom_unique_id)
            subentry = build_device_subentry(
                config_key, device_config, title or f"TapHome device {device_id}"
            )
            hass.config_entries.async_add_subentry(entry, subentry)
            subentry_by_device[(config_key, device_id)] = subentry.subentry_id
            if isinstance(custom_unique_id, str):
                subentry_by_unique_id[custom_unique_id] = subentry.subentry_id

    subentries_by_ha_device: dict[str, set[str]] = {}
    for registry_entry in entities:
        subentry_id = subentry_by_unique_id.get(registry_entry.unique_id)
        if subentry_id is None:
            config_key = domain_to_key.get(registry_entry.domain)
            device_id = _parse_device_id_from_unique_id(registry_entry.unique_id)
            if config_key is not None and device_id is not None:
                subentry_id = subentry_by_device.get((config_key, device_id))
        if subentry_id is None:
            continue
        entity_registry.async_update_entity(
            registry_entry.entity_id, config_subentry_id=subentry_id
        )
        if registry_entry.device_id:
            subentries_by_ha_device.setdefault(registry_entry.device_id, set()).add(
                subentry_id
            )

    for ha_device_id, subentry_ids in subentries_by_ha_device.items():
        for subentry_id in subentry_ids:
            device_registry.async_update_device(
                ha_device_id,
                add_config_entry_id=entry.entry_id,
                add_config_subentry_id=subentry_id,
            )
        # Drop the bare (no-subentry) link so the device belongs to its subentry.
        device_registry.async_update_device(
            ha_device_id,
            remove_config_entry_id=entry.entry_id,
            remove_config_subentry_id=None,
        )

    hass.config_entries.async_update_entry(
        entry, options=new_options, minor_version=2
    )


async def _async_update_listener(hass: HomeAssistant, entry: TapHomeConfigEntry) -> None:
    """Reload the entry when its options or a device subentry change.

    ``async_schedule_reload`` (over ``async_reload``) is the recommended call: it
    cancels a pending setup retry first, avoiding a race with the reload.
    """
    hass.config_entries.async_schedule_reload(entry.entry_id)


def _build_core_config(entry: TapHomeConfigEntry) -> TapHomeCoreConfig:
    """Build the immutable core configuration from a config entry."""
    options = entry.options
    zone_mapping = NameMapping.from_dict(options.get(CONF_ZONES))
    label_mapping = NameMapping.from_dict(options.get(CONF_LABELS))

    return TapHomeCoreConfig(
        entry.data.get(CONF_ID),
        zone_mapping,
        label_mapping,
        tuple(options.get(CONF_ENABLED_ATTRIBUTES, AVAILABLE_ATTRIBUTES)),
    )


def _parse_device_id_from_unique_id(unique_id: str) -> int | None:
    """Extract the TapHome device id from a generated entity unique id."""
    if not unique_id.startswith("taphome"):
        return None
    try:
        return int(unique_id.rsplit(".", 1)[-1])
    except ValueError:
        return None


def _domains_by_config_key() -> dict[str, list[str]]:
    """Map each platform config key to the domain names sharing it."""
    mapping: dict[str, list[str]] = {}
    for domain in DOMAIN_DEFINITIONS:
        mapping.setdefault(domain.config_key, []).append(domain.name)
    return mapping


def _async_remove_stale_entities(
    hass: HomeAssistant, entry: TapHomeConfigEntry
) -> None:
    """Remove registry entities whose device is no longer configured."""
    configured_ids: dict[str, set[int]] = {
        domain.name: set() for domain in DOMAIN_DEFINITIONS
    }
    custom_unique_ids: set[str] = set()
    domains_by_key = _domains_by_config_key()
    for subentry in iter_device_subentries(entry):
        data = subentry.data
        platform = subentry_platform(data)
        if platform not in domains_by_key:
            continue
        for name in domains_by_key[platform]:
            configured_ids[name].add(device_config_id(data))
        if data.get("unique_id"):
            custom_unique_ids.add(data["unique_id"])

    entity_registry = er.async_get(hass)
    for registry_entry in er.async_entries_for_config_entry(
        entity_registry, entry.entry_id
    ):
        if registry_entry.unique_id in custom_unique_ids:
            continue
        if registry_entry.domain not in configured_ids:
            continue
        # Custom unique ids do not parse to a device id and are kept above;
        # anything else unparseable is left alone to stay on the safe side.
        device_id = _parse_device_id_from_unique_id(registry_entry.unique_id)
        if device_id is None:
            continue
        if device_id not in configured_ids[registry_entry.domain]:
            entity_registry.async_remove(registry_entry.entity_id)


def _all_configured_device_ids(entry: TapHomeConfigEntry) -> set[int]:
    """Return the ids of every device exposed by a subentry."""
    return {
        device_config_id(subentry.data)
        for subentry in iter_device_subentries(entry)
        if "id" in subentry.data
    }


def _async_detect_new_devices(
    hass: HomeAssistant,
    entry: TapHomeConfigEntry,
    hub: TapHomeHub,
    issue_registry: TapHomeIssueRegistry,
    exposed: set[int],
) -> None:
    """Report devices exposed since the entry was last known about.

    On the first setup the currently exposed devices become the baseline, so
    nothing is reported. Afterwards any device exposed in the API that is not in
    the baseline and not already configured raises a fixable repair issue.
    """
    configured = _all_configured_device_ids(entry)
    known_raw = entry.data.get(CONF_KNOWN_DEVICE_IDS)

    if known_raw is None:
        hass.config_entries.async_update_entry(
            entry,
            data={**entry.data, CONF_KNOWN_DEVICE_IDS: sorted(exposed | configured)},
        )
        return

    known = {int(value) for value in known_raw}
    new_devices = exposed - known - configured
    issue_registry.sync_new_device_issues(entry.entry_id, hub, new_devices)


def _subscribe_new_device_detection(
    hass: HomeAssistant,
    entry: TapHomeConfigEntry,
    hub: TapHomeHub,
    issue_registry: TapHomeIssueRegistry,
) -> None:
    """Report new devices the moment their values arrive (webhook or poll).

    Exposing a device in the TapHome app makes its id show up in the incoming
    values without a matching registered device; the hub surfaces that on
    ``new_device_ids``. Reacting to it fetches the device metadata on demand
    instead of polling discovery on a timer.
    """
    detecting = False

    async def _async_detect() -> None:
        nonlocal detecting
        try:
            exposed = await hub.async_discover_new_devices()
        except TapHomeError as error:
            _LOGGER.debug("Skipping new-device detection: %s", error)
            return
        finally:
            detecting = False
        _async_detect_new_devices(hass, entry, hub, issue_registry, exposed)

    def _on_new_device_ids(
        _: frozenset[int], new_device_ids: frozenset[int]
    ) -> None:
        nonlocal detecting
        # async_discover_new_devices resolves every exposed device at once and
        # clears the resolved ids, re-firing if any remain unknown, so skipping
        # a concurrent run never drops a device.
        if new_device_ids and not detecting:
            detecting = True
            entry.async_create_background_task(
                hass, _async_detect(), "taphome_new_device_detection"
            )

    def _unsubscribe() -> None:
        # Return None: unsubscribe returns the Event, which async_on_unload
        # would otherwise mistake for a coroutine to await.
        hub.new_device_ids.changed.unsubscribe(_on_new_device_ids)

    hub.new_device_ids.changed += _on_new_device_ids
    entry.async_on_unload(_unsubscribe)


def _register_hub_device(
    hass: HomeAssistant, entry: TapHomeConfigEntry, hub: TapHomeHub
) -> None:
    """Register the TapHome Core as the hub device."""
    location = hub.location
    location_id = hub_device_id(location, entry.data.get(CONF_ID))
    device_registry = dr.async_get(hass)
    device_registry.async_get_or_create(
        config_entry_id=entry.entry_id,
        identifiers={(DOMAIN, location_id)},
        name=location.location_name if location else entry.title,
        manufacturer="TapHome",
        model="Core",
        configuration_url=_core_configuration_url(entry.data.get(CONF_API_URL, "")),
    )


def _core_configuration_url(api_url: str) -> str | None:
    """Return the Core's local log page, or None for a cloud connection.

    The Core only serves a UI (its local API log) on the local network; the
    cloud API has no such page.
    """
    prefix, suffix = "http://", "/api/TapHomeApi/v1"
    normalized = api_url.rstrip("/")
    if normalized.startswith(prefix) and normalized.endswith(suffix):
        host = normalized[len(prefix) : -len(suffix)]
        if host:
            return f"http://{host}/localapilog"
    return None


async def async_remove_config_entry_device(
    hass: HomeAssistant, entry: TapHomeConfigEntry, device_entry: dr.DeviceEntry
) -> bool:
    """Allow deleting a device the Core no longer provides.

    The Core hub device and devices still exposed by the Core are kept (remove
    those through the device subentry's Delete); a genuinely orphaned device can
    be deleted from its device page.
    """
    if entry.state is not ConfigEntryState.LOADED:
        return True
    hub = entry.runtime_data.hub
    location_id = hub_device_id(hub.location, entry.data.get(CONF_ID))
    prefix = f"{location_id}_"
    for domain, identifier in device_entry.identifiers:
        if domain != DOMAIN:
            continue
        if identifier == location_id:
            return False  # the Core hub device itself
        suffix = identifier.removeprefix(prefix)
        if suffix != identifier and suffix.isdigit() and int(suffix) in hub.devices:
            return False  # still exposed by the Core
    return True


def _register_webhook(
    hass: HomeAssistant,
    entry: TapHomeConfigEntry,
    hub: TapHomeHub,
    core_config: TapHomeCoreConfig,
) -> None:
    """Register the push webhook for the entry when configured."""
    webhook_id = entry.options.get(CONF_WEBHOOK_ID)
    if not webhook_id:
        return

    webhook_name = f"Taphome-{core_config.id}" if core_config.id else "Taphome"

    async def async_handle_webhook(
        _: HomeAssistant, webhook_id: str, request: Request
    ) -> None:
        _LOGGER.info("Taphome webhook triggered - webhook_id: %s", webhook_id)
        try:
            payload = await request.json()
        except ValueError:
            _LOGGER.warning("Ignoring TapHome webhook with an invalid JSON body")
            return
        await hub.async_handle_webhook(payload)

    async_register_webhook(
        hass, TAPHOME_PLATFORM, webhook_name, webhook_id, async_handle_webhook
    )
    entry.async_on_unload(lambda: async_unregister_webhook(hass, webhook_id))


def _map_subentry_requests(
    hass: HomeAssistant,
    core_config: TapHomeCoreConfig,
    entry: TapHomeConfigEntry,
    domain: DomainDefinition,
    hub: TapHomeHub,
) -> list[tuple[str, AddEntryRequest]]:
    """Build the (subentry id, request) pairs for one platform domain.

    Every exposed device is a ``device`` subentry whose ``data`` names the
    platform bucket it belongs to; a subentry feeds one request per domain
    sharing that bucket (e.g. ``buttons`` feeds both button and event).
    """
    requests: list[tuple[str, AddEntryRequest]] = []
    for subentry in iter_device_subentries(entry):
        if subentry_platform(subentry.data) != domain.config_key:
            continue
        entity_config = domain.config_entry_type(
            device_config_from_subentry(subentry.data)
        )
        requests.append(
            (subentry.subentry_id, AddEntryRequest(hass, core_config, entity_config, hub))
        )
    return requests
