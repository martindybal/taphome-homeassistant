"""TapHome integration."""

import logging
import typing
from dataclasses import dataclass, field

import voluptuous as vol
from homeassistant.components.binary_sensor import \
    DOMAIN as BINARY_SENSOR_DOMAIN
from homeassistant.components.button import DOMAIN as BUTTON_DOMAIN
from homeassistant.components.climate import DOMAIN as CLIMATE_DOMAIN
from homeassistant.components.cover import DOMAIN as COVER_DOMAIN
from homeassistant.components.fan import DOMAIN as FAN_DOMAIN
from homeassistant.components.humidifier import DOMAIN as HUMIDIFIER_DOMAIN
from homeassistant.components.light import DOMAIN as LIGHT_DOMAIN
from homeassistant.components.select import DOMAIN as SELECT_DOMAIN
from homeassistant.components.sensor import DOMAIN as SENSOR_DOMAIN
from homeassistant.components.switch import DOMAIN as SWITCH_DOMAIN
from homeassistant.components.time import DOMAIN as TIME_DOMAIN
from homeassistant.components.valve import DOMAIN as VALVE_DOMAIN
from homeassistant.components.webhook import \
    async_register as async_register_webhook
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import (CONF_BINARY_SENSORS, CONF_COVERS, CONF_ID,
                                 CONF_LIGHTS, CONF_SENSORS, CONF_SWITCHES,
                                 CONF_TOKEN, CONF_WEBHOOK_ID)
from homeassistant.core import HomeAssistant
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers.discovery import load_platform

from .add_entry_request import AddEntryRequest
from .binary_sensor import BinarySensorConfigEntry
from .button import ButtonConfigEntry
from .climate import ClimateConfigEntry
from .const import (CONF_API_URL, CONF_BUTTONS, CONF_CLIMATES, CONF_CORES,
                    CONF_FAN, CONF_HUMIDIFIER, CONF_LANGUAGE,
                    CONF_MULTIVALUE_SWITCHES, CONF_TIMES, CONF_UPDATE_INTERVAL,
                    CONF_VALVE, TAPHOME_PLATFORM, USE_DESCRIPTION_AS_ENTITY_ID,
                    USE_DESCRIPTION_AS_NAME)
from .coordinator import TapHomeDataUpdateCoordinator
from .cover import CoverConfigEntry
from .humidifier import HumidifierConfigEntry
from .sensor import SensorConfigEntry
from .switch import SwitchConfigEntry
from .taphome_core_config_entry import TapHomeCoreConfigEntry
from .taphome_entity import TapHomeConfigEntry
from .taphome_sdk import TapHomeApiService, TapHomeHttpClientFactory
from .valve import ValveConfigEntry

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
                            vol.Optional(CONF_API_URL): cv.string,
                            vol.Optional(CONF_WEBHOOK_ID): cv.string,
                            vol.Optional(CONF_UPDATE_INTERVAL): cv.positive_float,
                            vol.Optional(USE_DESCRIPTION_AS_ENTITY_ID): cv.boolean,
                            vol.Optional(USE_DESCRIPTION_AS_NAME): cv.boolean,
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


async def async_setup(hass: HomeAssistant, config: ConfigEntry) -> bool:
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
            BINARY_SENSOR_DOMAIN, CONF_BINARY_SENSORS, BinarySensorConfigEntry
        ),
        DomainDefinition(BUTTON_DOMAIN, CONF_BUTTONS, ButtonConfigEntry),
        DomainDefinition(CLIMATE_DOMAIN, CONF_CLIMATES, ClimateConfigEntry),
        DomainDefinition(COVER_DOMAIN, CONF_COVERS, CoverConfigEntry),
        DomainDefinition(LIGHT_DOMAIN, CONF_LIGHTS, TapHomeConfigEntry),
        DomainDefinition(FAN_DOMAIN, CONF_FAN, TapHomeConfigEntry),
        DomainDefinition(VALVE_DOMAIN, CONF_VALVE, ValveConfigEntry),
        DomainDefinition(HUMIDIFIER_DOMAIN, CONF_HUMIDIFIER, HumidifierConfigEntry),
        DomainDefinition(SELECT_DOMAIN, CONF_MULTIVALUE_SWITCHES, TapHomeConfigEntry),
        DomainDefinition(SENSOR_DOMAIN, CONF_SENSORS, SensorConfigEntry),
        DomainDefinition(SWITCH_DOMAIN, CONF_SWITCHES, SwitchConfigEntry),
        DomainDefinition(TIME_DOMAIN, CONF_TIMES, TapHomeConfigEntry),
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


def get_update_interval_default_value(api_url: str, webhook_id: str) -> int:
    """Return polling interval in seconds based on API configuration."""
    if webhook_id:
        return 600
    if "cloudapi.taphome.com" in api_url:
        return 20
    return 2  # local api


def read_from_config_or_default(config: dict, key: str, default_value) -> typing.Any:
    """Return ``config[key]`` if available otherwise ``default_value``."""
    if key in config:
        return config[key]
    return default_value


def map_config_entries(config_entry, platform_config: list) -> list[TapHomeConfigEntry]:
    """Instantiate ``config_entry`` objects for each configuration item."""
    return list(map(config_entry, platform_config))


def map_add_entry_requests(
    core_config_entry: TapHomeCoreConfigEntry,
    config_entries: list[TapHomeConfigEntry],
    coordinator: TapHomeDataUpdateCoordinator,
    taphome_api_service: TapHomeApiService,
) -> list[AddEntryRequest]:
    """Create ``AddEntryRequest`` objects for each config entry."""
    return [
        AddEntryRequest(
            core_config_entry,
            config_entry,
            config_entry.id,
            coordinator,
            taphome_api_service,
        )
        for config_entry in config_entries
    ]


async def _setup_core(
    hass: HomeAssistant, core_config: dict, domains: list[DomainDefinition]
) -> bool:
    """Set up TapHome for one core configuration."""
    token = core_config[CONF_TOKEN]

    core_id = read_from_config_or_default(core_config, CONF_ID, None)
    use_description_as_entity_id = read_from_config_or_default(
        core_config, USE_DESCRIPTION_AS_ENTITY_ID, False
    )
    use_description_as_name = read_from_config_or_default(
        core_config, USE_DESCRIPTION_AS_NAME, False
    )

    core_config_entry = TapHomeCoreConfigEntry(
        core_id, use_description_as_entity_id, use_description_as_name
    )

    api_url = read_from_config_or_default(
        core_config, CONF_API_URL, "https://api.taphome.com/api/TapHomeApi/v1"
    )
    webhook_id = read_from_config_or_default(core_config, CONF_WEBHOOK_ID, None)
    update_interval = read_from_config_or_default(
        core_config,
        CONF_UPDATE_INTERVAL,
        get_update_interval_default_value(api_url, webhook_id),
    )

    taphome_http_client = TapHomeHttpClientFactory().create(api_url, token)
    taphome_api_service = TapHomeApiService(taphome_http_client)
    coordinator = TapHomeDataUpdateCoordinator(
        hass, update_interval, taphome_api_service=taphome_api_service
    )

    try:
        await coordinator.async_refresh()
    except NotImplementedError:
        return False

    if webhook_id:
        webhook_name = f"Taphome-{core_id}" if core_id else "Taphome"
        async_register_webhook(
            hass,
            TAPHOME_PLATFORM,
            webhook_name,
            webhook_id,
            coordinator.async_handle_webhook,
        )

    hass.data[TAPHOME_PLATFORM] = {}
    for domain in domains:
        domain_config = core_config[domain.config_key]
        config_entries = map_config_entries(domain.config_entry_type, domain_config)

        core_add_entry_requests = map_add_entry_requests(
            core_config_entry,
            config_entries,
            coordinator,
            taphome_api_service,
        )
        domain.add_requests(core_add_entry_requests)
    return True
