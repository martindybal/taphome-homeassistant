"""Tests for the TapHome time platform."""

from datetime import time

from taphome_sdk import ValueType

from homeassistant.components.time import (
    ATTR_TIME,
    DOMAIN as TIME_DOMAIN,
    SERVICE_SET_VALUE,
)
from homeassistant.const import ATTR_ENTITY_ID
from homeassistant.core import HomeAssistant

from tests_common import make_config_entry, make_device, setup_integration

TIME_DEFINITION = {
    "deviceId": 35,
    "type": "Variable",
    "name": "Watering Start",
    "description": "Daily watering start time",
    "supportedValues": [
        {"valueTypeId": ValueType.VARIABLE_STATE.value, "readOnly": False},
        {"valueTypeId": ValueType.SESSION_DURATION.value, "readOnly": False},
    ],
    "values": {
        ValueType.VARIABLE_STATE: 23400.0,
        ValueType.SESSION_DURATION: 23400.0,
    },
}

ENTITY_ID = "time.watering_start"


async def test_time_set_value(hass: HomeAssistant, mock_hub) -> None:
    """Setting the time writes the value as seconds since midnight."""
    make_device(mock_hub, TIME_DEFINITION)
    await setup_integration(hass, make_config_entry({"times": [{"id": 35}]}))

    assert hass.states.get(ENTITY_ID).state == "06:30:00"

    await hass.services.async_call(
        TIME_DOMAIN,
        SERVICE_SET_VALUE,
        {ATTR_ENTITY_ID: ENTITY_ID, ATTR_TIME: time(7, 15)},
        blocking=True,
    )
    await hass.async_block_till_done()

    assert (35, {ValueType.VARIABLE_STATE: 26100}) in mock_hub.api.set_calls


async def test_time_push_update(hass: HomeAssistant, mock_hub) -> None:
    """A pushed duration change updates the entity state."""
    make_device(mock_hub, TIME_DEFINITION)
    await setup_integration(hass, make_config_entry({"times": [{"id": 35}]}))

    mock_hub.devices[35].state.apply_changes(
        {ValueType.VARIABLE_STATE: 3600.0, ValueType.SESSION_DURATION: 3600.0}
    )
    await hass.async_block_till_done()

    assert hass.states.get(ENTITY_ID).state == "01:00:00"
