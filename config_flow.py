import logging
from typing import Any, Dict

import voluptuous as vol

from homeassistant import config_entries

from .const import (
    TAPHOME_PLATFORM,
    CONF_TOKEN,
    CONF_ID,
    CONF_API_URL,
    CONF_LIGHTS,
    CONF_SWITCHES,
    CONF_COVERS,
    CONF_CLIMATES,
    CONF_SENSORS,
    CONF_BINARY_SENSORS,
    CONF_BUTTONS,
    CONF_MULTIVALUE_SWITCHES,
)
from .taphome_sdk import TapHomeApiService, TapHomeHttpClientFactory, ValueType, Device

_LOGGER = logging.getLogger(__name__)

API_URL_DEFAULT = "https://api.taphome.com/api/TapHomeApi/v1"

DOMAIN_OPTIONS = {
    "light": CONF_LIGHTS,
    "switch": CONF_SWITCHES,
    "cover": CONF_COVERS,
    "climate": CONF_CLIMATES,
    "sensor": CONF_SENSORS,
    "binary_sensor": CONF_BINARY_SENSORS,
    "button": CONF_BUTTONS,
    "select": CONF_MULTIVALUE_SWITCHES,
    "ignore": None,
}


class TapHomeConfigFlow(config_entries.ConfigFlow, domain=TAPHOME_PLATFORM):
    """Handle a config flow for TapHome."""

    VERSION = 1

    def __init__(self) -> None:
        self._data: Dict[str, Any] = {}
        self._devices: list[Device] = []

    async def async_step_user(self, user_input: Dict[str, Any] | None = None):
        errors = {}
        if user_input is not None:
            token = user_input[CONF_TOKEN]
            api_url = user_input.get(CONF_API_URL, API_URL_DEFAULT)
            self._data = {
                CONF_TOKEN: token,
                CONF_API_URL: api_url,
            }
            if user_input.get(CONF_ID):
                self._data[CONF_ID] = user_input[CONF_ID]

            try:
                client = TapHomeHttpClientFactory().create(api_url, token)
                service = TapHomeApiService(client)
                self._devices = await service.async_discovery_devices()
            except Exception:  # pragma: no cover - network errors
                _LOGGER.exception("TapHome discovery failed")
                errors["base"] = "cannot_connect"
            else:
                if not self._devices:
                    errors["base"] = "no_devices"
                else:
                    return await self.async_step_devices()

        schema = vol.Schema(
            {
                vol.Required(CONF_TOKEN): str,
                vol.Optional(CONF_ID): str,
                vol.Optional(CONF_API_URL, default=API_URL_DEFAULT): str,
            }
        )
        return self.async_show_form(step_id="user", data_schema=schema, errors=errors)

    async def async_step_devices(self, user_input: Dict[str, Any] | None = None):
        if user_input is not None:
            devices_map: Dict[str, list[int]] = {
                opt: [] for opt in DOMAIN_OPTIONS.values() if opt
            }
            for device in self._devices:
                value = user_input.get(str(device.id))
                if not value or value == "ignore":
                    continue
                conf_key = DOMAIN_OPTIONS[value]
                devices_map[conf_key].append(device.id)
            self._data.update(devices_map)
            return self.async_create_entry(
                title=self._data.get(CONF_ID, "TapHome"), data=self._data
            )

        fields = {}
        for device in self._devices:
            default = self._guess_domain(device) or "ignore"
            fields[vol.Optional(str(device.id), default=default)] = vol.In(
                list(DOMAIN_OPTIONS.keys())
            )
        return self.async_show_form(step_id="devices", data_schema=vol.Schema(fields))

    def _guess_domain(self, device: Device) -> str | None:
        def s(val: ValueType) -> bool:
            return device.supports_value(val)

        if s(ValueType.SwitchState):
            if s(ValueType.AnalogOutputValue) or s(ValueType.HueBrightness):
                return "light"
            if s(ValueType.MultiValueSwitchState):
                return "select"
            return "switch"
        if s(ValueType.BlindsLevel):
            return "cover"
        if s(ValueType.TemperatureSetPoint):
            return "climate"
        sensor_types = [
            ValueType.Humidity,
            ValueType.RealTemperature,
            ValueType.ElectricityDemand,
            ValueType.ElectricityConsumption,
            ValueType.Co2,
            ValueType.SensorBrightness,
            ValueType.WindSpeed,
            ValueType.AnalogInputValue,
            ValueType.TotalImpulseCount,
            ValueType.CurrentHourImpulseCount,
            ValueType.LastMeasuredFrequency,
            ValueType.VariableState,
        ]
        if any(s(t) for t in sensor_types):
            return "sensor"
        if (
            s(ValueType.Motion)
            or s(ValueType.ReedContact)
            or s(ValueType.VariableState)
        ):
            return "binary_sensor"
        if s(ValueType.ButtonPressed):
            return "button"
        return None
