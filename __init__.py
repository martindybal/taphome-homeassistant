"""TapHome integration."""
import asyncio
import logging
import typing

from async_timeout import timeout
import voluptuous

from homeassistant.components.binary_sensor import DOMAIN as BINARY_SENSOR_DOMAIN
from homeassistant.components.climate import DOMAIN as CLIMATE_DOMAIN
from homeassistant.components.cover import DOMAIN as COVER_DOMAIN
from homeassistant.components.light import DOMAIN as LIGHT_DOMAIN
from homeassistant.components.select import DOMAIN as SELECT_DOMAIN
from homeassistant.components.sensor import DOMAIN as SENSOR_DOMAIN
from homeassistant.components.switch import DOMAIN as SWITCH_DOMAIN
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import (
    CONF_BINARY_SENSORS,
    CONF_COVERS,
    CONF_LIGHTS,
    CONF_SENSORS,
    CONF_SWITCHES,
    CONF_TOKEN,
)
from homeassistant.core import HomeAssistant
import homeassistant.helpers.config_validation as config_validation
from homeassistant.helpers.discovery import load_platform

from .add_entry_request import AddEntryRequest
from .binary_sensor import BinarySensorConfigEntry
from .climate import ClimateConfigEntry
from .const import *
from .coordinator import TapHomeDataUpdateCoordinator
from .cover import CoverConfigEntry
from .sensor import SensorConfigEntry
from .switch import SwitchConfigEntry
from .taphome_entity import TapHomeConfigEntry
from .taphome_sdk import *

_LOGGER = logging.getLogger(__name__)

CONFIG_SCHEMA = voluptuous.Schema(
    {
        TAPHOME_PLATFORM: voluptuous.Schema(
            {
                voluptuous.Optional(CONF_LANGUAGE): config_validation.string,
                CONF_CORES: [
                    voluptuous.All(
                        config_validation.has_at_least_one_key(
                            CONF_LIGHTS,
                            CONF_COVERS,
                            CONF_CLIMATES,
                            CONF_MULTIVALUE_SWITCHES,
                            CONF_SWITCHES,
                            CONF_SENSORS,
                            CONF_BINARY_SENSORS,
                        ),
                        {
                            voluptuous.Required(CONF_TOKEN): config_validation.string,
                            voluptuous.Optional(CONF_API_URL): config_validation.string,
                            voluptuous.Optional(
                                CONF_UPDATE_INTERVAL
                            ): config_validation.positive_float,
                            voluptuous.Optional(
                                CONF_LIGHTS, default=[]
                            ): config_validation.ensure_list,
                            voluptuous.Optional(
                                CONF_COVERS, default=[]
                            ): config_validation.ensure_list,
                            voluptuous.Optional(
                                CONF_CLIMATES, default=[]
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

    for core_config in config[TAPHOME_PLATFORM][CONF_CORES]:
        token = core_config[CONF_TOKEN]

        api_url = read_from_config_or_default(
            core_config,
            CONF_API_URL,
            "https://cloudapi.taphome.com/api/CloudApi/v1",
        )

        update_interval = read_from_config_or_default(
            core_config, CONF_UPDATE_INTERVAL, 10
        )

        tapHome_http_client = TapHomeHttpClientFactory().create(api_url, token)
        tapHome_api_service = TapHomeApiService(tapHome_http_client)
        coordinator = TapHomeDataUpdateCoordinator(
            hass, update_interval, taphome_api_service=tapHome_api_service
        )

        try:
            async with timeout(8):
                await coordinator.async_refresh()
        except asyncio.TimeoutError:
            _LOGGER.warn("TapHome devices was not discovered during startup")
            hass.async_create_task(coordinator.async_refresh())
        except NotImplementedError:
            return False

        domains = [
            {
                "domain": BINARY_SENSOR_DOMAIN,
                "config_key": CONF_BINARY_SENSORS,
                "config_entry": BinarySensorConfigEntry,
            },
            {
                "domain": CLIMATE_DOMAIN,
                "config_key": CONF_CLIMATES,
                "config_entry": ClimateConfigEntry,
            },
            {
                "domain": COVER_DOMAIN,
                "config_key": CONF_COVERS,
                "config_entry": CoverConfigEntry,
            },
            {
                "domain": LIGHT_DOMAIN,
                "config_key": CONF_LIGHTS,
                "config_entry": TapHomeConfigEntry,
            },
            {
                "domain": SELECT_DOMAIN,
                "config_key": CONF_MULTIVALUE_SWITCHES,
                "config_entry": TapHomeConfigEntry,
            },
            {
                "domain": SENSOR_DOMAIN,
                "config_key": CONF_SENSORS,
                "config_entry": SensorConfigEntry,
            },
            {
                "domain": SWITCH_DOMAIN,
                "config_key": CONF_SWITCHES,
                "config_entry": SwitchConfigEntry,
            },
        ]
        hass.data[TAPHOME_PLATFORM] = {}
        for domain in domains:
            domain_config = core_config[domain["config_key"]]
            config_entries = map_config_entries(domain["config_entry"], domain_config)

            add_entry_requests = map_add_entry_requests(
                config_entries, coordinator, tapHome_api_service
            )

            hass.data[TAPHOME_PLATFORM][domain["config_key"]] = add_entry_requests

            load_platform(
                hass,
                domain["domain"],
                TAPHOME_PLATFORM,
                {},
                config,
            )

    return True


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
    config_entries: typing.List[TapHomeConfigEntry],
    coordinator: TapHomeDataUpdateCoordinator,
    tapHome_api_service: TapHomeApiService,
) -> typing.List[AddEntryRequest]:
    return list(
        map(
            lambda config_entry: AddEntryRequest(
                config_entry,
                config_entry.id,
                coordinator,
                tapHome_api_service,
            ),
            config_entries,
        )
    )
