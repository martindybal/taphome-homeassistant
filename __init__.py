"""TapHome integration."""

from .taphome_sdk import *
from homeassistant.helpers.discovery import async_load_platform
import voluptuous
import homeassistant.helpers.config_validation as config_validation

from homeassistant.const import (
    CONF_TOKEN,
    CONF_LIGHTS,
    CONF_COVERS,
    CONF_SWITCHES,
    CONF_SENSORS,
    CONF_BINARY_SENSORS,
)

DOMAIN = "taphome"
TAPHOME_API_SERVICE = f"{DOMAIN}_TapHomeApiService"
TAPHOME_DEVICES = f"{DOMAIN}_Devices"
TAPHOME_LANGUAGE = f"{DOMAIN}_language"
CONF_CORES = "cores"
CONF_LANGUAGE = "language"
CONF_CLIMATES = "climates"

CONFIG_SCHEMA = voluptuous.Schema(
    {
        DOMAIN: voluptuous.Schema(
            {
                voluptuous.Optional(CONF_LANGUAGE): config_validation.string,
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
                ]
            }
        )
    },
    extra=voluptuous.ALLOW_EXTRA,
)


async def async_setup(hass, config):
    hass.data[TAPHOME_LANGUAGE] = config[DOMAIN][CONF_LANGUAGE]

    for coreConfig in config[DOMAIN][CONF_CORES]:
        token = coreConfig[CONF_TOKEN]
        tapHomeHttpClientFactory = TapHomeHttpClientFactory()
        tapHomeHttpClient = tapHomeHttpClientFactory.create(token)
        tapHomeApiService = TapHomeApiService(tapHomeHttpClient)
        hass.data[TAPHOME_API_SERVICE] = tapHomeApiService

        devices = await tapHomeApiService.async_discovery_devices()

        platforms = [
            {"config": CONF_LIGHTS, "platform": "light"},
            {"config": CONF_COVERS, "platform": "cover"},
            {"config": CONF_CLIMATES, "platform": "climate"},
            {"config": CONF_SWITCHES, "platform": "switch"},
            {"config": CONF_SENSORS, "platform": "sensor"},
            {"config": CONF_BINARY_SENSORS, "platform": "binary_sensor"},
        ]

        for platform in platforms:
            platformDeviceIds = coreConfig[platform["config"]]
            if platformDeviceIds:
                platformDevices = filter_devices_by_ids(devices, platformDeviceIds)
                platformConfig = create_platform_config(
                    tapHomeApiService, platformDevices
                )

                hass.async_create_task(
                    async_load_platform(
                        hass, platform["platform"], DOMAIN, platformConfig, config
                    )
                )

    return True


def create_platform_config(tapHomeApiService: TapHomeApiService, devices: list):
    platformConfig = dict()
    platformConfig[TAPHOME_API_SERVICE] = tapHomeApiService
    platformConfig[TAPHOME_DEVICES] = devices
    return platformConfig


def filter_devices_by_ids(devices: list, deviceIds: list):
    return list(
        map(
            lambda deviceId: next(
                device for device in devices if device.deviceId == deviceId
            ),
            deviceIds,
        )
    )
