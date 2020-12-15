"""TapHome integration."""

from .taphome_sdk import *
from homeassistant.helpers.discovery import async_load_platform
import voluptuous
import homeassistant.helpers.config_validation as config_validation
from homeassistant.const import CONF_TOKEN, CONF_LIGHTS, CONF_COVERS

DOMAIN = "taphome"
TAPHOME_API_SERVICE = f"{DOMAIN}_TapHomeApiService"
TAPHOME_DEVICES = f"{DOMAIN}_Devices"

CONFIG_SCHEMA = voluptuous.Schema(
    {
        DOMAIN: voluptuous.Schema(
            [
                voluptuous.All(
                    config_validation.has_at_least_one_key(CONF_LIGHTS, CONF_COVERS),
                    {
                        voluptuous.Required(CONF_TOKEN): config_validation.string,
                        voluptuous.Optional(
                            CONF_LIGHTS, default=[]
                        ): config_validation.ensure_list,
                        voluptuous.Optional(
                            CONF_COVERS, default=[]
                        ): config_validation.ensure_list,
                    },
                )
            ]
        )
    },
    extra=voluptuous.ALLOW_EXTRA,
)


async def async_setup(hass, config):
    for coreConfig in config[DOMAIN]:
        token = coreConfig[CONF_TOKEN]
        tapHomeHttpClientFactory = TapHomeHttpClientFactory()
        tapHomeHttpClient = tapHomeHttpClientFactory.create(token)
        tapHomeApiService = TapHomeApiService(tapHomeHttpClient)
        hass.data[TAPHOME_API_SERVICE] = tapHomeApiService

        devices = await tapHomeApiService.async_discovery_devices()

        lightIds = coreConfig[CONF_LIGHTS]
        if lightIds:
            platformConfig = dict()
            platformConfig[TAPHOME_DEVICES] = filter_devices_by_ids(devices, lightIds)
            platformConfig[TAPHOME_API_SERVICE] = tapHomeApiService

            hass.async_create_task(
                async_load_platform(hass, "light", DOMAIN, platformConfig, config)
            )

        coverIds = coreConfig[CONF_COVERS]
        if coverIds:
            platformConfig = dict()
            platformConfig[TAPHOME_DEVICES] = filter_devices_by_ids(devices, coverIds)
            platformConfig[TAPHOME_API_SERVICE] = tapHomeApiService

            hass.async_create_task(
                async_load_platform(hass, "cover", DOMAIN, platformConfig, config)
            )

    return True


def filter_devices_by_ids(devices: list, deviceIds: list):
    return list(
        map(
            lambda deviceId: next(
                device for device in devices if device.deviceId == deviceId
            ),
            deviceIds,
        )
    )
