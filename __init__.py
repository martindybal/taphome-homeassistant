"""TapHome integration."""

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
from homeassistant.config_entries import SOURCE_IMPORT
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
from homeassistant.helpers import config_validation as cv, issue_registry as ir
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
from .humidifier import TapHomeHumidifierConfig
from .light import TapHomeLightConfig
from .sensor import TapHomeSensorConfig
from .switch import TapHomeSwitchConfig
from .taphome_config_entry import (
    AddEntryRequest,
    NameMapping,
    TapHomeCoreConfig,
    TapHomeEntityConfig,
)
from .taphome_data import TapHomeConfigEntry, TapHomeRuntimeData
from .taphome_issue_registry import TapHomeIssueRegistry
from .taphome_sdk import (
    HubConnectionState,
    TapHomeAuthError,
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
        ) (Add config flow and convert setup to config entries)

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
                "/blob/production/configuration.md"
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

    def hub_connection_state_changed(
        _: HubConnectionState, state: HubConnectionState
    ) -> None:
        """Handle changes in hub connection state."""
        if state == HubConnectionState.CONNECTED:
            taphome_issue_registry.try_delete_core_unavailable_issue()
        else:
            taphome_issue_registry.create_core_unavailable_issue()

    hub.connection_state.changed += hub_connection_state_changed

    _register_webhook(hass, entry, hub, core_config)

    add_entry_requests = {
        domain.name: _map_add_entry_requests(
            hass,
            core_config,
            _map_config_entries(
                domain.config_entry_type, entry.options.get(domain.config_key, [])
            ),
            hub,
        )
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


async def async_migrate_entry(hass: HomeAssistant, entry: TapHomeConfigEntry) -> bool:
    """Migrate old config entries to the current version."""
    return True


async def _async_update_listener(hass: HomeAssistant, entry: TapHomeConfigEntry) -> None:
    """Reload the config entry when its options change."""
    await hass.config_entries.async_reload(entry.entry_id)


def _build_core_config(entry: TapHomeConfigEntry) -> TapHomeCoreConfig:
    """Build the immutable core configuration from a config entry."""
    options = entry.options
    zone_mapping = (
        NameMapping.from_dict(options.get(CONF_ZONES))
        if CONF_ZONES in options
        else None
    )
    label_mapping = (
        NameMapping.from_dict(options.get(CONF_LABELS))
        if CONF_LABELS in options
        else None
    )

    return TapHomeCoreConfig(
        entry.data.get(CONF_ID),
        options.get(USE_DESCRIPTION_AS_ENTITY_ID, False),
        options.get(USE_DESCRIPTION_AS_NAME, False),
        zone_mapping,
        label_mapping,
        tuple(options.get(CONF_ENABLED_ATTRIBUTES, AVAILABLE_ATTRIBUTES)),
    )


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
        await hub.async_handle_webhook(request)

    async_register_webhook(
        hass, TAPHOME_PLATFORM, webhook_name, webhook_id, async_handle_webhook
    )
    entry.async_on_unload(lambda: async_unregister_webhook(hass, webhook_id))


def _map_config_entries(
    config_entry_factory, platform_config: list
) -> list[TapHomeEntityConfig]:
    return list(map(config_entry_factory, platform_config))


def _map_add_entry_requests(
    hass: HomeAssistant,
    core_config_entry: TapHomeCoreConfig,
    config_entries: list[TapHomeEntityConfig],
    hub: TapHomeHub,
) -> list[AddEntryRequest]:
    return [
        AddEntryRequest(hass, core_config_entry, config_entry, hub)
        for config_entry in config_entries
    ]
