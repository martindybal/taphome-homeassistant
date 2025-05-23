import logging
from typing import Dict, List, Optional

import voluptuous as vol
from homeassistant import config_entries
from homeassistant.const import (
    CONF_TOKEN,
)

from .const import (
    CONF_API_URL,
    CONF_BINARY_SENSORS,
    CONF_BUTTONS,
    CONF_CLIMATES,
    CONF_COVERS,
    CONF_LIGHTS,
    CONF_MULTIVALUE_SWITCHES,
    CONF_SENSORS,
    CONF_SWITCHES,
    CONF_CORES,
    TAPHOME_PLATFORM,
)
from .taphome_sdk import TapHomeApiService, TapHomeHttpClientFactory, ValueType
from .taphome_sdk.device import Device

_LOGGER = logging.getLogger(__name__)

DEFAULT_API_URL = "https://api.taphome.com/api/TapHomeApi/v1"


TYPE_LIGHT = "light"
TYPE_SWITCH = "switch"
TYPE_COVER = "cover"
TYPE_CLIMATE = "climate"
TYPE_SENSOR = "sensor"
TYPE_BINARY_SENSOR = "binary_sensor"
TYPE_BUTTON = "button"
TYPE_MULTIVALUE_SWITCH = "multivalue_switch"

DEVICE_TYPES = {
    TYPE_LIGHT: "Light",
    TYPE_SWITCH: "Switch",
    TYPE_COVER: "Cover",
    TYPE_CLIMATE: "Climate",
    TYPE_SENSOR: "Sensor",
    TYPE_BINARY_SENSOR: "Binary sensor",
    TYPE_BUTTON: "Button",
    TYPE_MULTIVALUE_SWITCH: "Multivalue switch",
    "ignore": "Ignore",
}

TYPE_TO_CONF = {
    TYPE_LIGHT: CONF_LIGHTS,
    TYPE_SWITCH: CONF_SWITCHES,
    TYPE_COVER: CONF_COVERS,
    TYPE_CLIMATE: CONF_CLIMATES,
    TYPE_SENSOR: CONF_SENSORS,
    TYPE_BINARY_SENSOR: CONF_BINARY_SENSORS,
    TYPE_BUTTON: CONF_BUTTONS,
    TYPE_MULTIVALUE_SWITCH: CONF_MULTIVALUE_SWITCHES,
}


class TapHomeConfigFlow(config_entries.ConfigFlow, domain=TAPHOME_PLATFORM):
    VERSION = 1

    def __init__(self) -> None:
        self._token: Optional[str] = None
        self._api_url: str = DEFAULT_API_URL
        self._api_service: Optional[TapHomeApiService] = None
        self._devices: List[Device] = []
        self._index: int = 0
        self._device_map: Dict[str, List[int]] = {}

    async def async_step_user(self, user_input=None):
        if user_input is None:
            return self.async_show_form(
                step_id="user",
                data_schema=vol.Schema(
                    {
                        vol.Required(CONF_TOKEN): str,
                        vol.Optional(CONF_API_URL, default=DEFAULT_API_URL): str,
                    }
                ),
            )

        self._token = user_input[CONF_TOKEN]
        self._api_url = user_input.get(CONF_API_URL, DEFAULT_API_URL)

        try:
            http_client = TapHomeHttpClientFactory().create(self._api_url, self._token)
            self._api_service = TapHomeApiService(http_client)
            self._devices = await self._api_service.async_discovery_devices()
        except Exception as exc:  # pragma: no cover - network error handling
            _LOGGER.error("TapHome discovery failed: %s", exc)
            return self.async_show_form(
                step_id="user",
                data_schema=vol.Schema(
                    {
                        vol.Required(CONF_TOKEN, default=self._token): str,
                        vol.Optional(CONF_API_URL, default=self._api_url): str,
                    }
                ),
                errors={"base": "cannot_connect"},
            )

        if not self._devices:
            return self.async_abort(reason="no_devices")

        self._index = 0
        self._device_map = {}
        return await self.async_step_device()

    async def async_step_device(self, user_input=None):
        if user_input is not None:
            device = self._devices[self._index]
            entity_type = user_input["type"]
            if entity_type != "ignore":
                self._device_map.setdefault(entity_type, []).append(device.id)
            self._index += 1

        if self._index < len(self._devices):
            device = self._devices[self._index]
            suggested = self._suggest_device_types(device)
            default = suggested[0] if len(suggested) == 1 else "ignore"
            options = {k: DEVICE_TYPES[k] for k in DEVICE_TYPES}
            return self.async_show_form(
                step_id="device",
                description_placeholders={
                    "device": f"{device.name} ({device.description})"
                },
                data_schema=vol.Schema(
                    {vol.Required("type", default=default): vol.In(options)}
                ),
            )

        return self._create_entry()

    def _create_entry(self):
        data = {
            CONF_TOKEN: self._token,
            CONF_API_URL: self._api_url,
        }
        for conf in TYPE_TO_CONF.values():
            data[conf] = []
        for entity_type, ids in self._device_map.items():
            conf_key = TYPE_TO_CONF.get(entity_type)
            if conf_key:
                data[conf_key] = ids
        return self.async_create_entry(title="TapHome", data=data)

    def _suggest_device_types(self, device: Device) -> List[str]:
        sv = device.supports_value
        types: List[str] = []
        if sv(ValueType.SwitchState):
            if sv(ValueType.AnalogOutputValue) or sv(ValueType.HueBrightness):
                types.append(TYPE_LIGHT)
            elif sv(ValueType.MultiValueSwitchState):
                types.append(TYPE_MULTIVALUE_SWITCH)
            else:
                types.extend([TYPE_LIGHT, TYPE_SWITCH])
        if sv(ValueType.BlindsLevel):
            types.append(TYPE_COVER)
        if sv(ValueType.TemperatureSetPoint):
            types.append(TYPE_CLIMATE)
        if (
            (sv(ValueType.Humidity) and not sv(ValueType.TemperatureSetPoint))
            or (sv(ValueType.RealTemperature) and not sv(ValueType.TemperatureSetPoint))
            or sv(ValueType.ElectricityDemand)
            or sv(ValueType.ElectricityConsumption)
            or sv(ValueType.Co2)
            or sv(ValueType.SensorBrightness)
            or sv(ValueType.WindSpeed)
            or sv(ValueType.AnalogInputValue)
            or sv(ValueType.TotalImpulseCount)
            or sv(ValueType.CurrentHourImpulseCount)
            or sv(ValueType.LastMeasuredFrequency)
            or sv(ValueType.VariableState)
        ):
            types.append(TYPE_SENSOR)
        if sv(ValueType.Motion) or sv(ValueType.ReedContact) or sv(ValueType.VariableState):
            types.append(TYPE_BINARY_SENSOR)
        if sv(ValueType.ButtonPressed):
            types.append(TYPE_BUTTON)
        # remove duplicates
        return list(dict.fromkeys(types))
