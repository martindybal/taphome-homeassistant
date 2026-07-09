"""Tests for the TapHome valve platform."""

from taphome_sdk import ValueType

from homeassistant.components.valve import (
    ATTR_CURRENT_POSITION,
    ATTR_POSITION,
    DOMAIN as VALVE_DOMAIN,
    SERVICE_CLOSE_VALVE,
    SERVICE_OPEN_VALVE,
    SERVICE_SET_VALVE_POSITION,
    ValveState,
)
from homeassistant.const import ATTR_ENTITY_ID
from homeassistant.core import HomeAssistant

from tests_common import make_config_entry, make_device, setup_integration

VALVE_DEFINITION = {
    "deviceId": 33,
    "type": "Valve",
    "name": "Water Valve",
    "description": "Main water valve",
    "supportedValues": [
        {"valueTypeId": ValueType.ANALOG_OUTPUT_VALUE.value, "readOnly": False},
        {
            "valueTypeId": ValueType.ANALOG_OUTPUT_DESIRED_VALUE.value,
            "readOnly": False,
        },
        {"valueTypeId": ValueType.SWITCH_STATE.value, "readOnly": False},
    ],
    "values": {
        ValueType.ANALOG_OUTPUT_VALUE: 0.0,
        ValueType.ANALOG_OUTPUT_DESIRED_VALUE: 0.0,
        ValueType.SWITCH_STATE: 0.0,
    },
}

ENTITY_ID = "valve.water_valve"

DIGITAL_VALVE = {
    "deviceId": 36,
    "type": "Valve",
    "name": "Garden Valve",
    "description": "On/off irrigation valve",
    "supportedValues": [
        {"valueTypeId": ValueType.SWITCH_STATE.value, "readOnly": False},
    ],
    "values": {ValueType.SWITCH_STATE: 0.0},
}

BIDIRECTIONAL_VALVE = {
    "deviceId": 37,
    "type": "Valve",
    "name": "Main Valve",
    "description": "Motorized valve",
    "supportedValues": [
        {"valueTypeId": ValueType.BLINDS_LEVEL.value, "readOnly": False},
        {"valueTypeId": ValueType.BLINDS_IS_MOVING.value, "readOnly": True},
    ],
    "values": {
        ValueType.BLINDS_LEVEL: 0.0,
        ValueType.BLINDS_IS_MOVING: 0.0,
    },
}


async def test_valve_set_position(hass: HomeAssistant, mock_hub) -> None:
    """Setting the position writes the scaled output value."""
    make_device(mock_hub, VALVE_DEFINITION)
    await setup_integration(hass, make_config_entry({"valves": [{"id": 33}]}))
    assert hass.states.get(ENTITY_ID).state == ValveState.CLOSED

    await hass.services.async_call(
        VALVE_DOMAIN,
        SERVICE_SET_VALVE_POSITION,
        {ATTR_ENTITY_ID: ENTITY_ID, ATTR_POSITION: 50},
        blocking=True,
    )
    await hass.async_block_till_done()

    assert (
        33,
        {ValueType.SWITCH_STATE: 1, ValueType.ANALOG_OUTPUT_DESIRED_VALUE: 0.5},
    ) in mock_hub.api.set_calls
    state = hass.states.get(ENTITY_ID)
    assert state.state == ValveState.OPEN
    assert state.attributes[ATTR_CURRENT_POSITION] == 50


async def test_digital_valve_open_close(hass: HomeAssistant, mock_hub) -> None:
    """A plain on/off valve opens and closes through the switch state."""
    make_device(mock_hub, DIGITAL_VALVE)
    await setup_integration(hass, make_config_entry({"valves": [{"id": 36}]}))

    entity_id = "valve.garden_valve"
    assert hass.states.get(entity_id).state == ValveState.CLOSED

    await hass.services.async_call(
        VALVE_DOMAIN,
        SERVICE_OPEN_VALVE,
        {ATTR_ENTITY_ID: entity_id},
        blocking=True,
    )
    await hass.async_block_till_done()
    assert (36, {ValueType.SWITCH_STATE: 1}) in mock_hub.api.set_calls

    await hass.services.async_call(
        VALVE_DOMAIN,
        SERVICE_CLOSE_VALVE,
        {ATTR_ENTITY_ID: entity_id},
        blocking=True,
    )
    await hass.async_block_till_done()
    assert (36, {ValueType.SWITCH_STATE: 0}) in mock_hub.api.set_calls


async def test_bidirectional_valve_reports_movement(
    hass: HomeAssistant, mock_hub
) -> None:
    """A motorized valve maps the TapHome position state to open/closed."""
    make_device(mock_hub, BIDIRECTIONAL_VALVE)
    await setup_integration(hass, make_config_entry({"valves": [{"id": 37}]}))

    entity_id = "valve.main_valve"
    assert hass.states.get(entity_id).state == ValveState.CLOSED

    mock_hub.devices[37].state.apply_changes(
        {ValueType.BLINDS_LEVEL: 1.0, ValueType.BLINDS_IS_MOVING: 0.0}
    )
    await hass.async_block_till_done()

    state = hass.states.get(entity_id)
    assert state.state == ValveState.OPEN
    assert state.attributes[ATTR_CURRENT_POSITION] == 100


async def test_valve_open_close(hass: HomeAssistant, mock_hub) -> None:
    """Open and close translate to full and zero position writes.

    The entity reports its position, so Home Assistant maps the open and
    close services to position 100 and 0.
    """
    make_device(mock_hub, VALVE_DEFINITION)
    await setup_integration(hass, make_config_entry({"valves": [{"id": 33}]}))

    await hass.services.async_call(
        VALVE_DOMAIN,
        SERVICE_OPEN_VALVE,
        {ATTR_ENTITY_ID: ENTITY_ID},
        blocking=True,
    )
    await hass.async_block_till_done()
    assert (
        33,
        {ValueType.SWITCH_STATE: 1, ValueType.ANALOG_OUTPUT_DESIRED_VALUE: 1},
    ) in mock_hub.api.set_calls
    assert hass.states.get(ENTITY_ID).state == ValveState.OPEN

    await hass.services.async_call(
        VALVE_DOMAIN,
        SERVICE_CLOSE_VALVE,
        {ATTR_ENTITY_ID: ENTITY_ID},
        blocking=True,
    )
    await hass.async_block_till_done()
    assert (
        33,
        {ValueType.SWITCH_STATE: 1, ValueType.ANALOG_OUTPUT_DESIRED_VALUE: 0},
    ) in mock_hub.api.set_calls
    assert hass.states.get(ENTITY_ID).state == ValveState.CLOSED
