"""TapHome integration."""
from .add_entry_request import AddEntryRequest
from .switch import SwitchConfigEntry
from .taphome_entity import TapHomeConfigEntry
from .taphome_sdk import *
from .const import *

from .TapHomeClimateController import (
    TapHomeClimateController,
    TapHomeClimateControllerFactory,
)
from .coordinator import TapHomeDataUpdateCoordinator
from homeassistant.helpers.discovery import load_platform
import voluptuous
import typing
import homeassistant.helpers.config_validation as config_validation

from homeassistant.core import HomeAssistant
from homeassistant.config_entries import ConfigEntry


from homeassistant.components.switch import DOMAIN as SWITCH_DOMAIN
from homeassistant.components.light import DOMAIN as LIGHT_DOMAIN

# from homeassistant.exceptions import ConfigEntryAuthFailed

from homeassistant.const import (
    CONF_TOKEN,
    CONF_LIGHTS,
    CONF_COVERS,
    CONF_SWITCHES,
    CONF_SENSORS,
    CONF_BINARY_SENSORS,
)

CONFIG_SCHEMA = voluptuous.Schema(
    {
        DOMAIN: voluptuous.Schema(
            {
                voluptuous.Optional(
                    CONF_LANGUAGE, default="en"
                ): config_validation.string,
                CONF_CORES: [
                    voluptuous.All(
                        config_validation.has_at_least_one_key(
                            CONF_LIGHTS,
                            CONF_COVERS,
                            CONF_CLIMATES,
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
    for core_config in config[DOMAIN][CONF_CORES]:
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

        platforms = [
            {
                "domain": SWITCH_DOMAIN,
                "config_key": CONF_SWITCHES,
                "config_entry": SwitchConfigEntry,
            },
            {
                "domain": LIGHT_DOMAIN,
                "config_key": CONF_LIGHTS,
                "config_entry": TapHomeConfigEntry,
            },
        ]
        hass.data[DOMAIN] = {}
        for platform in platforms:
            platform_config = core_config[platform["config_key"]]
            config_entries = map_config_entries(
                platform["config_entry"], platform_config
            )

            add_entry_requests = map_add_entry_requests(
                config_entries, coordinator, tapHome_api_service
            )

            hass.data[DOMAIN][platform["config_key"]] = add_entry_requests

            load_platform(
                hass,
                platform["domain"],
                DOMAIN,
                {},
                config,
            )

        hass.async_create_task(coordinator.async_refresh())
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