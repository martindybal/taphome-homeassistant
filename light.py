"""TapHome light integration."""
from .taphome_sdk import *

import logging
import voluptuous
import homeassistant.helpers.config_validation as config_validation

# Import the device class from the component that you want to support
from homeassistant.components.light import PLATFORM_SCHEMA, LightEntity
from homeassistant.const import CONF_TOKEN, CONF_LIGHTS

_LOGGER = logging.getLogger(__name__)

# Validation of the user's configuration
PLATFORM_SCHEMA = PLATFORM_SCHEMA.extend(
    {
        voluptuous.Required(CONF_TOKEN): config_validation.string,
        voluptuous.Required(CONF_LIGHTS): config_validation.ensure_list,
    }
)


async def async_setup_platform(hass, config, async_add_entities, discovery_info=None):
    token = config[CONF_TOKEN]
    lightIds = config[CONF_LIGHTS]

    tapHomeHttpClientFactory = TapHomeHttpClientFactory()
    tapHomeHttpClient = tapHomeHttpClientFactory.create(token)
    tapHome = TapHome(tapHomeHttpClient)

    devices = (await tapHome.async_discovery_devices())["devices"]

    lights = []
    for lightId in lightIds:
        light = next(device for device in devices if device["deviceId"] == lightId)
        lightValues = (await tapHome.async_get_device_value(lightId))["values"]
        isLightOn = (
            next(
                lightValue
                for lightValue in lightValues
                if lightValue["valueTypeId"] == TapHome.ValueType.SwitchState.value
            )["value"]
            == 1
        )

        lights.append(
            # TODO False should be change and load from TapHome
            SimpleTapHomeLight(
                tapHome, light["deviceId"], "TapHome - " + light["name"], isLightOn
            )
        )

    async_add_entities(lights)


class SimpleTapHomeLight(LightEntity):
    """Representation of an Light without brightness or color setting."""

    def __init__(self, tapHome: TapHome, deviceId: int, name: str, is_on: bool):
        self._tapHome = tapHome
        self._name = name
        self._deviceId = deviceId
        self._is_on = is_on

    @property
    def name(self):
        """Return the name of the light."""
        return self._name

    @property
    def is_on(self):
        """Returns if the light entity is on or not."""
        return self._is_on

    async def async_turn_on(self, **kwargs):
        """Turn device on."""
        print(f"Turn {self._name} on.")
        print(kwargs)
        result = await self._tapHome.async_turn_on_light(self._deviceId)
        self._is_on = result == TapHome.ValueChangeResult.CHANGED
        print(f"Turn {self._name} on.")

    async def async_turn_off(self):
        """Turn device off."""
        print(f"Turn {self._name} off.")
        result = await self._tapHome.async_turn_off_light(self._deviceId)
        self._is_on = not result == TapHome.ValueChangeResult.CHANGED
        print(f"Turn {self._name} on.")