"""Constants used by the TapHome integration."""

from homeassistant.const import (
    CONF_BINARY_SENSORS,
    CONF_COVERS,
    CONF_LIGHTS,
    CONF_SENSORS,
    CONF_SWITCHES,
    Platform,
)

TAPHOME_PLATFORM = "taphome"
DOMAIN = TAPHOME_PLATFORM

PLATFORMS: list[Platform] = [
    Platform.BINARY_SENSOR,
    Platform.BUTTON,
    Platform.CLIMATE,
    Platform.COVER,
    Platform.EVENT,
    Platform.FAN,
    Platform.HUMIDIFIER,
    Platform.LIGHT,
    Platform.SELECT,
    Platform.SENSOR,
    Platform.SWITCH,
    Platform.TIME,
    Platform.VALVE,
]

TAPHOME_API_SERVICE = f"{TAPHOME_PLATFORM}_TapHomeApiService"
TAPHOME_COORDINATOR = f"{TAPHOME_PLATFORM}_Coordinator"
TAPHOME_DEVICES = f"{TAPHOME_PLATFORM}_Devices"
TAPHOME_LANGUAGE = f"{TAPHOME_PLATFORM}_language"
CONF_CORES = "cores"
CONF_LANGUAGE = "language"
CONF_IP = "ip"
CONF_API_URL = "api_url"
CONF_UPDATE_INTERVAL = "update_interval"
CONF_CLIMATES = "climates"
CONF_FAN = "fans"
CONF_HUMIDIFIER = "humidifiers"
CONF_VALVE = "valves"
CONF_MULTIVALUE_SWITCHES = "multivalue_switches"
CONF_BUTTONS = "buttons"
CONF_NUMBERS = "numbers"
CONF_TIMES = "times"
USE_DESCRIPTION_AS_ENTITY_ID = "use_description_as_entity_id"
USE_DESCRIPTION_AS_NAME = "use_description_as_name"
CONF_ZONES = "zones"
CONF_LABELS = "labels"
CONF_ENABLED_ATTRIBUTES = "enabled_attributes"

# Baseline of device ids already known at setup, stored in the config entry
# data. Devices exposed later that are not in this set are reported as new.
CONF_KNOWN_DEVICE_IDS = "known_device_ids"

# Configuration keys holding per-platform device lists
DEVICE_CONFIG_KEYS = [
    CONF_LIGHTS,
    CONF_BUTTONS,
    CONF_COVERS,
    CONF_CLIMATES,
    CONF_FAN,
    CONF_HUMIDIFIER,
    CONF_MULTIVALUE_SWITCHES,
    CONF_SWITCHES,
    CONF_SENSORS,
    CONF_BINARY_SENSORS,
    CONF_VALVE,
    CONF_TIMES,
]

DEFAULT_CLOUD_API_URL = "https://api.taphome.com/api/TapHomeApi/v1"

# Attributes that can be exposed per entity
AVAILABLE_ATTRIBUTES = [
    "taphome_id",
    "taphome_name",
    "taphome_description",
    "taphome_category",
    "taphome_zone",
    "taphome_operation_mode",
]
