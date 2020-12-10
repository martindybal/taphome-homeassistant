"""TapHome integration."""

from .taphome_sdk import *
from homeassistant.helpers.discovery import async_load_platform
import voluptuous as voluptuous
import homeassistant.helpers.config_validation as config_validation

from homeassistant.const import CONF_TOKEN, CONF_LIGHTS

DOMAIN = "taphome"
TAPHOME = f"{DOMAIN}_TapHome"

CONFIG_SCHEMA = voluptuous.Schema(
    {
        DOMAIN: voluptuous.Schema(
            voluptuous.All(
                config_validation.has_at_least_one_key(CONF_LIGHTS),
                {
                    voluptuous.Required(CONF_TOKEN): config_validation.string,
                    voluptuous.Optional(CONF_LIGHTS, default=[]): config_validation.ensure_list,
                },
            )
        )
    },
    extra=voluptuous.ALLOW_EXTRA,
)


async def async_setup(hass, config):

    token = config[DOMAIN][CONF_TOKEN]
    lights = config[DOMAIN][CONF_LIGHTS]

    tapHomeHttpClientFactory = TapHomeHttpClientFactory()
    tapHomeHttpClient = tapHomeHttpClientFactory.create(token)
    tapHome = TapHome(tapHomeHttpClient)
    hass.data[TAPHOME] = tapHome

    if lights:
        hass.async_create_task(
            async_load_platform(
                hass, "light", DOMAIN, lights, config
            )
        )

    return True