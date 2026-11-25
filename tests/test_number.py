"""Tests for the TapHome number platform."""

from taphome_sdk import ValueType

from homeassistant.components.number import (
    ATTR_MAX,
    ATTR_MIN,
    ATTR_STEP,
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

# A variable whose TapHome metadata reports no min/max range (common for
# free-form variables): Home Assistant must not impose a made-up range.
UNBOUNDED_NUMBER_DEFINITION = {
    "deviceId": 35,
    "type": "Variable",
    "name": "Setpoint",
    "description": "Free variable",
    "supportedValues": [
        {
            "valueTypeId": ValueType.VARIABLE_STATE.value,
            "readOnly": False,
        },
    ],
    "values": {ValueType.VARIABLE_STATE: 120.0},
}

ENTITY_ID = "number.water_limit"
UNBOUNDED_ENTITY_ID = "number.setpoint"


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


async def test_number_without_reported_range_uses_ha_defaults(
    hass: HomeAssistant, mock_hub
) -> None:
    """No TapHome range and no override leaves HA's own number defaults."""
    make_device(mock_hub, UNBOUNDED_NUMBER_DEFINITION)
    await setup_integration(hass, make_config_entry({"numbers": [{"id": 35}]}))

    state = hass.states.get(UNBOUNDED_ENTITY_ID)
    # The current value is shown as-is even though it exceeds the default max.
    assert state.state == "120.0"
    assert state.attributes[ATTR_MIN] == 0
    assert state.attributes[ATTR_MAX] == 100


async def test_number_config_override_sets_limits(
    hass: HomeAssistant, mock_hub
) -> None:
    """Configured min/max/step apply when TapHome reports no range."""
    make_device(mock_hub, UNBOUNDED_NUMBER_DEFINITION)
    await setup_integration(
        hass,
        make_config_entry(
            {"numbers": [{"id": 35, "min_value": -50, "max_value": 250, "step": 5}]}
        ),
    )

    state = hass.states.get(UNBOUNDED_ENTITY_ID)
    assert state.attributes[ATTR_MIN] == -50
    assert state.attributes[ATTR_MAX] == 250
    assert state.attributes[ATTR_STEP] == 5

    await hass.services.async_call(
        NUMBER_DOMAIN,
        SERVICE_SET_VALUE,
        {ATTR_ENTITY_ID: UNBOUNDED_ENTITY_ID, ATTR_VALUE: 200},
        blocking=True,
    )
    await hass.async_block_till_done()

    assert (35, {ValueType.VARIABLE_STATE: 200}) in mock_hub.api.set_calls
    assert hass.states.get(UNBOUNDED_ENTITY_ID).state == "200.0"


async def test_number_config_override_beats_reported_range(
    hass: HomeAssistant, mock_hub
) -> None:
    """A configured limit wins over the range TapHome reports."""
    make_device(mock_hub, NUMBER_DEFINITION)
    await setup_integration(
        hass, make_config_entry({"numbers": [{"id": 34, "max_value": 500}]})
    )

    state = hass.states.get(ENTITY_ID)
    # min stays the TapHome-reported 0; only the overridden max changes.
    assert state.attributes[ATTR_MIN] == 0
    assert state.attributes[ATTR_MAX] == 500


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
