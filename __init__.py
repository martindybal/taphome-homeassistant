"""TapHome integration."""
from .taphome_sdk import *
from .TapHomeClimateController import (
    TapHomeClimateController,
    TapHomeClimateControllerFactory,
)
from homeassistant.helpers.discovery import async_load_platform
import voluptuous
import typing
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
    for coreConfig in config[DOMAIN][TAPHOME_CORES]:
        token = coreConfig[CONF_TOKEN]
        tapHomeHttpClientFactory = TapHomeHttpClientFactory()
        tapHomeHttpClient = tapHomeHttpClientFactory.create(token)
        tapHomeApiService = TapHomeApiService(tapHomeHttpClient)

        devices = await tapHomeApiService.async_discovery_devices()

        platforms = [
            {
                "config": CONF_LIGHTS,
                "platform": "light",
                "map_devices": map_devices_by_ids,
            },
            {
                "config": CONF_COVERS,
                "platform": "cover",
                "map_devices": map_devices_by_ids,
            },
            {
                "config": CONF_CLIMATES,
                "platform": "climate",
                "map_devices": create_climates,
            },
            {
                "config": CONF_SWITCHES,
                "platform": "switch",
                "map_devices": map_devices_by_ids,
            },
            {
                "config": CONF_SENSORS,
                "platform": "sensor",
                "map_devices": map_devices_by_ids,
            },
            {
                "config": CONF_BINARY_SENSORS,
                "platform": "binary_sensor",
                "map_devices": map_devices_by_ids,
            },
        ]

        for platform in platforms:
            platformConfig = coreConfig[platform["config"]]
            if platformConfig:
                map_devices = platform["map_devices"]
                platformDevices = map_devices(
                    devices, platformConfig, tapHomeApiService
                )
                platformConfig = create_platform_config(
                    tapHomeApiService, platformDevices
                )

                hass.async_create_task(
                    async_load_platform(
                        hass, platform["platform"], DOMAIN, platformConfig, config
                    )
                )

    return True


def map_devices_by_ids(
    devices: typing.List[Device],
    platformConfig: list,
    tapHomeApiService: TapHomeApiService,
):
    return filter_devices_by_ids(devices, platformConfig)


def create_climates(
    devices: typing.List[Device],
    climateConfig: list,
    tapHomeApiService: TapHomeApiService,
):
    if all(isinstance(climate, int) for climate in climateConfig):
        return list(
            map(
                lambda thermostatId: TapHomeClimateDevice.create(devices, tapHomeApiService, thermostatId),
                climateConfig,
            )
        )

    return list(
        map(
            lambda climate: TapHomeClimateDevice.create(
                devices,
                tapHomeApiService,
                climate["thermostat"],
                climate.get("mode", None),
                climate.get("heat", None),
                climate.get("cool", None),
            ),
            climateConfig,
        )
    )


def filter_devices_by_ids(devices: typing.List[Device], deviceIds: typing.List[int]):
    return list(
        map(
            lambda deviceId: filter_devices_by_id(devices, deviceId),
            deviceIds,
        )
    )


def filter_devices_by_id(devices: typing.List[Device], deviceId: int):
    return next(device for device in devices if device.deviceId == deviceId)


def create_platform_config(tapHomeApiService: TapHomeApiService, devices: list):
    platformConfig = dict()
    platformConfig[TAPHOME_API_SERVICE] = tapHomeApiService
    platformConfig[TAPHOME_DEVICES] = devices
    return platformConfig


class TapHomeClimateDevice:
    def __init__(
        self,
        thermostat: Device,
        controller: TapHomeClimateController,
    ):
        self.thermostat = thermostat
        self.controller = controller

    def create(
        devices: typing.List[Device],
        tapHomeApiService: TapHomeApiService,
        thermostat_id: int,
        mode_id: typing.Optional[int] = None,
        heat_id: typing.Optional[int] = None,
        cool_id: typing.Optional[int] = None,
    ) -> TapHomeClimateController:
        thermostat = filter_devices_by_id(devices, thermostat_id)
        controller = TapHomeClimateControllerFactory.create(
            devices, tapHomeApiService, mode_id, heat_id, cool_id
        )

        return TapHomeClimateDevice(thermostat, controller)
