"""TapHome integration."""
import asyncio
import logging
import typing

from async_timeout import timeout
import voluptuous

from homeassistant.components.binary_sensor import DOMAIN as BINARY_SENSOR_DOMAIN
from homeassistant.components.button import DOMAIN as BUTTON_DOMAIN
from homeassistant.components.climate import DOMAIN as CLIMATE_DOMAIN
from homeassistant.components.cover import DOMAIN as COVER_DOMAIN
from homeassistant.components.fan import DOMAIN as FAN_DOMAIN
from homeassistant.components.humidifier import DOMAIN as HUMIDIFIER_DOMAIN
from homeassistant.components.light import DOMAIN as LIGHT_DOMAIN
from homeassistant.components.select import DOMAIN as SELECT_DOMAIN
from homeassistant.components.sensor import DOMAIN as SENSOR_DOMAIN
from homeassistant.components.switch import DOMAIN as SWITCH_DOMAIN
from homeassistant.components.valve import DOMAIN as VALVE_DOMAIN
from homeassistant.config_entries import ConfigEntry
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
import homeassistant.helpers.config_validation as config_validation
from homeassistant.helpers.discovery import load_platform

from .add_entry_request import AddEntryRequest
from .binary_sensor import BinarySensorConfigEntry
from .button import ButtonConfigEntry
from .climate import ClimateConfigEntry
from .const import *
from .coordinator import TapHomeDataUpdateCoordinator
from .cover import CoverConfigEntry
from .humidifier import HumidifierConfigEntry
from .sensor import SensorConfigEntry
from .switch import SwitchConfigEntry
from .taphome_core_config_entry import TapHomeCoreConfigEntry
from .taphome_entity import TapHomeConfigEntry
from .taphome_sdk import *

_LOGGER = logging.getLogger(__name__)

# "domain": BINARY_SENSOR_DOMAIN,
# "config_key": CONF_BINARY_SENSORS,
# "config_entry": BinarySensorConfigEntry,


class DomainDefinition:
    def __init__(
        self,
        name: str,
        config_key: str,
        config_entry_type,
    ):
        self.name = name
        self.config_key = config_key
        self.config_entry_type = config_entry_type
        self.add_entry_requests = []


CONFIG_SCHEMA = voluptuous.Schema(
    {
        TAPHOME_PLATFORM: voluptuous.Schema(
            {
                voluptuous.Optional(CONF_LANGUAGE): config_validation.string,
                CONF_CORES: [
                    voluptuous.All(
                        config_validation.has_at_least_one_key(
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
                        ),
                        {
                            voluptuous.Required(CONF_TOKEN): config_validation.string,
                            voluptuous.Optional(CONF_ID): config_validation.string,
                            voluptuous.Optional(CONF_API_URL): config_validation.string,
                            voluptuous.Optional(
                                CONF_WEBHOOK_ID
                            ): config_validation.string,
                            voluptuous.Optional(
                                CONF_UPDATE_INTERVAL
                            ): config_validation.positive_float,
                            voluptuous.Optional(
                                USE_DESCRIPTION_AS_ENTITY_ID
                            ): config_validation.boolean,
                            voluptuous.Optional(
                                USE_DESCRIPTION_AS_NAME
                            ): config_validation.boolean,
                            voluptuous.Optional(
                                CONF_LIGHTS, default=[]
                            ): config_validation.ensure_list,
                            voluptuous.Optional(
                                CONF_BUTTONS, default=[]
                            ): config_validation.ensure_list,
                            voluptuous.Optional(
                                CONF_COVERS, default=[]
                            ): config_validation.ensure_list,
                            voluptuous.Optional(
                                CONF_CLIMATES, default=[]
                            ): config_validation.ensure_list,
                            voluptuous.Optional(
                                CONF_FAN, default=[]
                            ): config_validation.ensure_list,
                            voluptuous.Optional(
                                CONF_HUMIDIFIER, default=[]
                            ): config_validation.ensure_list,
                            voluptuous.Optional(
                                CONF_MULTIVALUE_SWITCHES, default=[]
                            ): config_validation.ensure_list,
                            voluptuous.Optional(
                                CONF_SWITCHES, default=[]
                            ): config_validation.ensure_list,
                            voluptuous.Optional(
                                CONF_SENSORS, default=[]
                            ): config_validation.ensure_list,
                            voluptuous.Optional(
                                CONF_BINARY_SENSORS, default=[]
                            ): config_validation.ensure_list,
                            voluptuous.Optional(
                                CONF_VALVE, default=[]
                            ): config_validation.ensure_list,
                        },
                    )
                ],
            }
        )
    },
    extra=voluptuous.ALLOW_EXTRA,
)


async def async_setup(hass: HomeAssistant, config: ConfigEntry) -> bool:
    if CONF_LANGUAGE in config[TAPHOME_PLATFORM]:
        _LOGGER.warning(
            "TapHome language setting is not supported any more. You can renema entities as you wish. This options'll be removed in future, please remove it from your config"
        )

    if len(config[TAPHOME_PLATFORM][CONF_CORES]) > 1:
        for core_config in config[TAPHOME_PLATFORM][CONF_CORES]:
            if not CONF_ID in core_config:
                _LOGGER.error(
                    "You have to specify a 'name' if you are using multiple cores."
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
        DomainDefinition(VALVE_DOMAIN, CONF_VALVE, TapHomeConfigEntry),
        DomainDefinition(HUMIDIFIER_DOMAIN, CONF_HUMIDIFIER, HumidifierConfigEntry),
        DomainDefinition(SELECT_DOMAIN, CONF_MULTIVALUE_SWITCHES, TapHomeConfigEntry),
        DomainDefinition(SENSOR_DOMAIN, CONF_SENSORS, SensorConfigEntry),
        DomainDefinition(SWITCH_DOMAIN, CONF_SWITCHES, SwitchConfigEntry),
    ]

    for core_config in config[TAPHOME_PLATFORM][CONF_CORES]:
        token = core_config[CONF_TOKEN]

        core_id = read_from_config_or_default(
            core_config,
            CONF_ID,
            None,
        )

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
            core_config,
            CONF_API_URL,
            "https://cloudapi.taphome.com/api/CloudApi/v1",
        )

        webhook_id = read_from_config_or_default(core_config, CONF_WEBHOOK_ID, None)

        update_interval = read_from_config_or_default(
            core_config,
            CONF_UPDATE_INTERVAL,
            get_update_interval_default_value(api_url, webhook_id),
        )

        tapHome_http_client = TapHomeHttpClientFactory().create(api_url, token)
        tapHome_api_service = TapHomeApiService(tapHome_http_client)
        coordinator = TapHomeDataUpdateCoordinator(
            hass, update_interval, taphome_api_service=tapHome_api_service
        )

        # register webhook handler if webhook_id is specified
        if webhook_id:
            handle_webhook_lambda = lambda hass, webhook_id, request: handle_webhook(
                coordinator, webhook_id
            )

            webhook_name = f"Taphome-{core_id}" if core_id else "Taphome"
            hass.components.webhook.async_register(
                TAPHOME_PLATFORM, webhook_name, webhook_id, handle_webhook_lambda
            )

        try:
            async with timeout(8):
                await coordinator.async_refresh()
                if not coordinator.last_update_success:
                    _LOGGER.warn("TapHome devices was not discovered during startup")
        except asyncio.TimeoutError:
            _LOGGER.warn("TapHome devices was not discovered during startup")
        except NotImplementedError:
            return False

        hass.data[TAPHOME_PLATFORM] = {}
        for domain in domains:
            domain_config = core_config[domain.config_key]
            config_entries = map_config_entries(domain.config_entry_type, domain_config)

            core_add_entry_requests = map_add_entry_requests(
                core_config_entry,
                config_entries,
                coordinator,
                tapHome_api_service,
            )
            domain.add_entry_requests.extend(core_add_entry_requests)

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
    if webhook_id:
        return 600
    if "cloudapi.taphome.com" in api_url:
        return 20
    return 2  # local api


def read_from_config_or_default(config: dict, key: str, default_value) -> typing.Any:
    if key in config:
        return config[key]
    else:
        return default_value


def map_config_entries(
    config_entry, platform_config: typing.List
) -> typing.List[TapHomeConfigEntry]:
    return list(
        map(
            lambda device_config: config_entry(device_config),
            platform_config,
        )
    )


def map_add_entry_requests(
    core_config_entry: TapHomeCoreConfigEntry,
    config_entries: typing.List[TapHomeConfigEntry],
    coordinator: TapHomeDataUpdateCoordinator,
    tapHome_api_service: TapHomeApiService,
) -> typing.List[AddEntryRequest]:
    return list(
        map(
            lambda config_entry: AddEntryRequest(
                core_config_entry,
                config_entry,
                config_entry.id,
                coordinator,
                tapHome_api_service,
            ),
            config_entries,
        )
    )


#
# webhook handler
#


async def handle_webhook(coordinator, webhook_id):
    """Handle incoming webhook - we will trigger an update poll here"""
    _LOGGER.info(f"Taphome webhook triggered - webhook_id: {webhook_id}")

    try:
        # ask for refresh with 8 seconds timeout
        async with timeout(8):
            await coordinator.async_refresh()
            _LOGGER.info("Refresh of taphome finished")
    except asyncio.TimeoutError:
        _LOGGER.warn("Refresh of taphome state failed due to timeout!")
    except NotImplementedError:
        _LOGGER.warn("Not implemented!")
