"""Constants used by the TapHome integration."""

TAPHOME_PLATFORM = "taphome"

TAPHOME_API_SERVICE = f"{TAPHOME_PLATFORM}_TapHomeApiService"
TAPHOME_COORDINATOR = f"{TAPHOME_PLATFORM}_Coordinator"
TAPHOME_DEVICES = f"{TAPHOME_PLATFORM}_Devices"
TAPHOME_LANGUAGE = f"{TAPHOME_PLATFORM}_language"
CONF_CORES = "cores"
CONF_LANGUAGE = "language"
CONF_API_URL = "api_url"
CONF_UPDATE_INTERVAL = "update_interval"
CONF_CLIMATES = "climates"
CONF_FAN = "fans"
CONF_HUMIDIFIER = "humidifiers"
CONF_VALVE = "valves"
CONF_MULTIVALUE_SWITCHES = "multivalue_switches"
CONF_BUTTONS = "buttons"
CONF_TIMES = "times"
USE_DESCRIPTION_AS_ENTITY_ID = "use_description_as_entity_id"
USE_DESCRIPTION_AS_NAME = "use_description_as_name"
USE_ZONES_AS_AREAS = "use_zones_as_areas"
USE_CATEGORIES_AS_LABELS = "use_categories_as_labels"
CONF_ENABLED_ATTRIBUTES = "enabled_attributes"

# Attributes that can be exposed per entity
AVAILABLE_ATTRIBUTES = [
    "taphome_id",
    "taphome_name",
    "taphome_description",
    "taphome_category",
    "taphome_zone",
    "taphome_operation_mode",
]
