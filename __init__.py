"""TapHome integration."""

from dataclasses import dataclass, field
import logging
import typing

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
from homeassistant.components.select import DOMAIN as SELECT_DOMAIN
from homeassistant.components.sensor import DOMAIN as SENSOR_DOMAIN
from homeassistant.components.switch import DOMAIN as SWITCH_DOMAIN
from homeassistant.components.time import DOMAIN as TIME_DOMAIN
from homeassistant.components.valve import DOMAIN as VALVE_DOMAIN
from homeassistant.components.webhook import async_register as async_register_webhook
from homeassistant.config_entries import ConfigType
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
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers.discovery import load_platform

from .binary_sensor import BinarySensorEntityConfig
from .button import TapHomeButtonConfig
from .climate import TapHomeClimateConfig
from .const import (
    AVAILABLE_ATTRIBUTES,
    CONF_API_URL,
    CONF_IP,
    CONF_BUTTONS,
    CONF_CLIMATES,
    CONF_CORES,
    CONF_ENABLED_ATTRIBUTES,
    CONF_FAN,
    CONF_HUMIDIFIER,
    CONF_LABELS,
    CONF_LANGUAGE,
    CONF_MULTIVALUE_SWITCHES,
    CONF_TIMES,
    CONF_UPDATE_INTERVAL,
    CONF_VALVE,
    CONF_ZONES,
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
from .taphome_issue_registry import TapHomeIssueRegistry
from .taphome_sdk import HubConnectionState, TapHomeHub, TapHomeHubFactory
from .valve import TapHomeValveConfig

_LOGGER = logging.getLogger(__name__)

# "domain": BINARY_SENSOR_DOMAIN,
# "config_key": CONF_BINARY_SENSORS,
# "config_entry": BinarySensorConfigEntry,


@dataclass
class DomainDefinition:
    """Configuration holder for a Home Assistant platform domain."""

    name: str
    config_key: str
    config_entry_type: type
    add_entry_requests: list = field(default_factory=list)

    def add_requests(self, requests: list) -> None:
        """Extend stored entry requests."""
        self.add_entry_requests.extend(requests)


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
    """Set up the TapHome integration."""
    if CONF_LANGUAGE in config[TAPHOME_PLATFORM]:
        _LOGGER.error(
            "TapHome language setting is not supported any more. "
            "You can rename entities as you wish. "
            "This option will be removed in future, please remove it from your config"
        )

    if len(config[TAPHOME_PLATFORM][CONF_CORES]) > 1:
        for core_config in config[TAPHOME_PLATFORM][CONF_CORES]:
            if CONF_ID not in core_config:
                _LOGGER.error(
                    "You have to specify a 'name' if you are using multiple cores"
                )
                return False

    domains = [
        DomainDefinition(
            BINARY_SENSOR_DOMAIN, CONF_BINARY_SENSORS, BinarySensorEntityConfig
        ),
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
    ]

    for core_config in config[TAPHOME_PLATFORM][CONF_CORES]:
        if not await _setup_core(hass, core_config, domains):
            return False

    for domain in domains:
        hass.data[TAPHOME_PLATFORM][domain.config_key] = domain.add_entry_requests

        load_platform(
            hass,
            domain.name,
            TAPHOME_PLATFORM,
            {},
            config,
        )

    return True


def _read_from_config_or_default(config: dict, key: str, default_value) -> typing.Any:
    if key in config:
        return config[key]
    return default_value


async def _setup_core(
    hass: HomeAssistant, core_config: dict, domains: list[DomainDefinition]
) -> bool:
    token = core_config[CONF_TOKEN]

    core_id = _read_from_config_or_default(core_config, CONF_ID, None)
    use_description_as_entity_id = _read_from_config_or_default(
        core_config, USE_DESCRIPTION_AS_ENTITY_ID, False
    )
    use_description_as_name = _read_from_config_or_default(
        core_config, USE_DESCRIPTION_AS_NAME, False
    )
    zone_mapping = (
        NameMapping.from_dict(core_config.get(CONF_ZONES))
        if CONF_ZONES in core_config
        else None
    )
    label_mapping = (
        NameMapping.from_dict(core_config.get(CONF_LABELS))
        if CONF_LABELS in core_config
        else None
    )
    enabled_attributes = tuple(
        _read_from_config_or_default(
            core_config, CONF_ENABLED_ATTRIBUTES, AVAILABLE_ATTRIBUTES
        )
    )

    core_config_entry = TapHomeCoreConfig(
        core_id,
        use_description_as_entity_id,
        use_description_as_name,
        zone_mapping,
        label_mapping,
        enabled_attributes,
    )
    ip = _read_from_config_or_default(core_config, CONF_IP, None)
    api_url = _read_from_config_or_default(core_config, CONF_API_URL, None)
    if api_url is None:
        if ip is not None:
            api_url = f"http://{ip}/api/TapHomeApi/v1"
        else:
            api_url = "https://api.taphome.com/api/TapHomeApi/v1"
    webhook_id = _read_from_config_or_default(core_config, CONF_WEBHOOK_ID, None)
    update_interval = _read_from_config_or_default(
        core_config, CONF_UPDATE_INTERVAL, None
    )

    if update_interval is not None:
        _LOGGER.error("Update interval is not supported anymore")

    taphome_issue_registry = TapHomeIssueRegistry(hass, core_id)
    hub: TapHomeHub

    try:
        hub = await TapHomeHubFactory.async_connect(
            api_url,
            token,
        )
        if hub.connection_state.value != HubConnectionState.CONNECTED:
            _LOGGER.error("Failed to connect to TapHome Hub")
            return False

        def hub_connection_state_changed(
            _: HubConnectionState, state: HubConnectionState
        ) -> None:
            """Handle changes in hub connection state."""
            if state == HubConnectionState.CONNECTED:
                taphome_issue_registry.try_delete_core_unavailable_issue()
            else:
                taphome_issue_registry.create_core_unavailable_issue()

        hub.connection_state.changed += hub_connection_state_changed

    except NotImplementedError:
        return False

    if webhook_id:
        webhook_name = f"Taphome-{core_id}" if core_id else "Taphome"

        async def async_handle_webhook(
            _: HomeAssistant, webhook_id: str, request: Request
        ) -> None:
            _LOGGER.info("Taphome webhook triggered - webhook_id: %s", webhook_id)
            await hub.async_handle_webhook(request)

        async_register_webhook(
            hass, TAPHOME_PLATFORM, webhook_name, webhook_id, async_handle_webhook
        )

    hass.data[TAPHOME_PLATFORM] = {}
    for domain in domains:
        domain_config = core_config[domain.config_key]

        config_entries = _map_config_entries(domain.config_entry_type, domain_config)

        core_add_entry_requests = _map_add_entry_requests(
            hass, core_config_entry, config_entries, hub
        )

        domain.add_requests(core_add_entry_requests)

    return True


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
