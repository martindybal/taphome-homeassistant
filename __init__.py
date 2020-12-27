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
)

DOMAIN = "taphome"
TAPHOME_API_SERVICE = f"{DOMAIN}_TapHomeApiService"
TAPHOME_DEVICES = f"{DOMAIN}_Devices"
TAPHOME_CORES = "cores"
CONF_CLIMATES = "climates"

CONFIG_SCHEMA = voluptuous.Schema(
    {
        DOMAIN: voluptuous.Schema(
            {
                TAPHOME_CORES: [
                    voluptuous.All(
                        config_validation.has_at_least_one_key(
                            CONF_LIGHTS,
                            CONF_COVERS,
                            CONF_CLIMATES,
                            CONF_SWITCHES,
                            CONF_SENSORS,
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
                        },
                    )
                ]
            }
        )
    },
    extra=voluptuous.ALLOW_EXTRA,
)


async def async_setup(hass, config):
    for coreConfig in config[DOMAIN][TAPHOME_CORES]:
        token = coreConfig[CONF_TOKEN]
        tapHomeHttpClientFactory = TapHomeHttpClientFactory()
        tapHomeHttpClient = tapHomeHttpClientFactory.create(token)
        tapHomeApiService = TapHomeApiService(tapHomeHttpClient)
        hass.data[TAPHOME_API_SERVICE] = tapHomeApiService

        devices = await tapHomeApiService.async_discovery_devices()

        lightIds = coreConfig[CONF_LIGHTS]
        if lightIds:
            lights = filter_devices_by_ids(devices, lightIds)
            platformConfig = create_platform_config(tapHomeApiService, lights)

            hass.async_create_task(
                async_load_platform(hass, "light", DOMAIN, platformConfig, config)
            )

        coverIds = coreConfig[CONF_COVERS]
        if coverIds:
            covers = filter_devices_by_ids(devices, coverIds)
            platformConfig = create_platform_config(tapHomeApiService, covers)

            hass.async_create_task(
                async_load_platform(hass, "cover", DOMAIN, platformConfig, config)
            )

        climateIds = coreConfig[CONF_CLIMATES]
        if climateIds:
            climates = filter_devices_by_ids(devices, climateIds)

            hass.async_create_task(
                async_load_platform(hass, "climate", DOMAIN, climates, config)
            )

        switchIds = coreConfig[CONF_SWITCHES]
        if switchIds:
            switches = filter_devices_by_ids(devices, switchIds)
            platformConfig = create_platform_config(tapHomeApiService, switches)

            hass.async_create_task(
                async_load_platform(hass, "switch", DOMAIN, platformConfig, config)
            )

        sensorIds = coreConfig[CONF_SENSORS]
        if sensorIds:
            sensors = filter_devices_by_ids(devices, sensorIds)
            platformConfig = create_platform_config(tapHomeApiService, sensors)
            hass.async_create_task(
                async_load_platform(hass, "sensor", DOMAIN, platformConfig, config)
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
