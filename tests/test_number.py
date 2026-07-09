"""Tests for the TapHome number platform."""

from taphome_sdk import ValueType

from homeassistant.components.number import (
    ATTR_MAX,
    ATTR_MIN,
    ATTR_VALUE,
    DOMAIN as NUMBER_DOMAIN,
    SERVICE_SET_VALUE,
)
from homeassistant.const import ATTR_ENTITY_ID
from homeassistant.core import HomeAssistant

from tests_common import make_config_entry, make_device, setup_integration

NUMBER_DEFINITION = {
    "deviceId": 34,
    "type": "Variable",
    "name": "Water Limit",
    "description": "Maximum irrigation volume",
    "supportedValues": [
        {
            "valueTypeId": ValueType.VARIABLE_STATE.value,
            "readOnly": False,
            "minValue": 0,
            "maxValue": 200,
        },
    ],
    "values": {ValueType.VARIABLE_STATE: 40.0},
}

ENTITY_ID = "number.water_limit"


async def test_number_set_value(hass: HomeAssistant, mock_hub) -> None:
    """Setting the number writes the variable and applies its limits."""
    make_device(mock_hub, NUMBER_DEFINITION)
    await setup_integration(hass, make_config_entry({"numbers": [{"id": 34}]}))

    state = hass.states.get(ENTITY_ID)
    assert state.state == "40.0"
    assert state.attributes[ATTR_MIN] == 0
    assert state.attributes[ATTR_MAX] == 200

    await hass.services.async_call(
        NUMBER_DOMAIN,
        SERVICE_SET_VALUE,
        {ATTR_ENTITY_ID: ENTITY_ID, ATTR_VALUE: 55},
        blocking=True,
    )
    await hass.async_block_till_done()

    assert (34, {ValueType.VARIABLE_STATE: 55}) in mock_hub.api.set_calls
    assert hass.states.get(ENTITY_ID).state == "55.0"


async def test_number_read_only_variable_ignores_writes(
    hass: HomeAssistant, mock_hub
) -> None:
    """A read-only variable accepts the service call but writes nothing."""
    await setup_integration(hass, make_config_entry({"numbers": [{"id": 5}]}))

    state = hass.states.get("number.outside_temperature")
    assert state.state == "23.4"

    await hass.services.async_call(
        NUMBER_DOMAIN,
        SERVICE_SET_VALUE,
        {ATTR_ENTITY_ID: "number.outside_temperature", ATTR_VALUE: 30},
        blocking=True,
    )
    await hass.async_block_till_done()

    assert not any(call[0] == 5 for call in mock_hub.api.set_calls)
