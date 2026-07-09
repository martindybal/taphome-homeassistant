"""Tests for the TapHome humidifier platform."""

from taphome_sdk import ValueType

from homeassistant.components.humidifier import (
    ATTR_HUMIDITY,
    DOMAIN as HUMIDIFIER_DOMAIN,
    SERVICE_SET_HUMIDITY,
)
from homeassistant.const import (
    ATTR_ENTITY_ID,
    SERVICE_TURN_OFF,
    SERVICE_TURN_ON,
    STATE_OFF,
    STATE_ON,
)
from homeassistant.core import HomeAssistant

from tests_common import make_config_entry, make_device, setup_integration

HUMIDIFIER_DEFINITION = {
    "deviceId": 32,
    "type": "Humidifier",
    "name": "Bedroom Humidifier",
    "description": "Humidifier in the bedroom",
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

ENTITY_ID = "humidifier.bedroom_humidifier"

HUMIDIFIER_SWITCH = {
    "deviceId": 65,
    "type": "PowerOutlet",
    "name": "Humidifier Switch",
    "description": "Relay of the humidifier",
    "supportedValues": [
        {"valueTypeId": ValueType.SWITCH_STATE.value, "readOnly": False},
    ],
    "values": {ValueType.SWITCH_STATE: 0.0},
}

HUMIDITY_SENSOR = {
    "deviceId": 63,
    "type": "Sensor",
    "name": "Bedroom Sensor",
    "description": "Humidity sensor",
    "supportedValues": [
        {"valueTypeId": ValueType.HUMIDITY.value, "readOnly": True},
    ],
    "values": {ValueType.HUMIDITY: 0.45},
}

ACTION_SWITCH = {
    "deviceId": 64,
    "type": "MultiValueSwitch",
    "name": "Humidifier Action",
    "description": "Reported humidifier action",
    "supportedValues": [
        {
            "valueTypeId": ValueType.MULTI_VALUE_SWITCH_STATE.value,
            "readOnly": False,
            "enumeratedValues": [
                {"value": 0, "name": "Off", "isEnabled": True},
                {"value": 1, "name": "Idle", "isEnabled": True},
                {"value": 2, "name": "Humidifying", "isEnabled": True},
            ],
        },
        {
            "valueTypeId": ValueType.MULTI_VALUE_SWITCH_DESIRED_STATE.value,
            "readOnly": False,
        },
    ],
    "values": {
        ValueType.MULTI_VALUE_SWITCH_STATE: 0.0,
        ValueType.MULTI_VALUE_SWITCH_DESIRED_STATE: 0.0,
    },
}


async def test_humidifier_turn_on_off(hass: HomeAssistant, mock_hub) -> None:
    """The humidifier services drive the TapHome output device."""
    make_device(mock_hub, HUMIDIFIER_DEFINITION)
    await setup_integration(hass, make_config_entry({"humidifiers": [{"id": 32}]}))
    assert hass.states.get(ENTITY_ID).state == STATE_OFF

    await hass.services.async_call(
        HUMIDIFIER_DOMAIN,
        SERVICE_TURN_ON,
        {ATTR_ENTITY_ID: ENTITY_ID},
        blocking=True,
    )
    await hass.async_block_till_done()
    assert (32, {ValueType.SWITCH_STATE: 1}) in mock_hub.api.set_calls
    assert hass.states.get(ENTITY_ID).state == STATE_ON

    await hass.services.async_call(
        HUMIDIFIER_DOMAIN,
        SERVICE_TURN_OFF,
        {ATTR_ENTITY_ID: ENTITY_ID},
        blocking=True,
    )
    await hass.async_block_till_done()
    assert (32, {ValueType.SWITCH_STATE: 0}) in mock_hub.api.set_calls
    assert hass.states.get(ENTITY_ID).state == STATE_OFF


async def test_humidifier_set_humidity(hass: HomeAssistant, mock_hub) -> None:
    """Setting the target humidity writes the scaled output value."""
    make_device(mock_hub, HUMIDIFIER_DEFINITION)
    await setup_integration(hass, make_config_entry({"humidifiers": [{"id": 32}]}))

    await hass.services.async_call(
        HUMIDIFIER_DOMAIN,
        SERVICE_SET_HUMIDITY,
        {ATTR_ENTITY_ID: ENTITY_ID, ATTR_HUMIDITY: 60},
        blocking=True,
    )
    await hass.async_block_till_done()

    assert (
        32,
        {ValueType.SWITCH_STATE: 1, ValueType.ANALOG_OUTPUT_DESIRED_VALUE: 0.6},
    ) in mock_hub.api.set_calls
    state = hass.states.get(ENTITY_ID)
    assert state.attributes[ATTR_HUMIDITY] == 60


async def test_humidifier_with_helper_devices(hass: HomeAssistant, mock_hub) -> None:
    """Switch, humidity sensor, action and mode devices feed the entity."""
    make_device(mock_hub, HUMIDIFIER_DEFINITION)
    make_device(mock_hub, HUMIDIFIER_SWITCH)
    make_device(mock_hub, HUMIDITY_SENSOR)
    make_device(mock_hub, ACTION_SWITCH)
    await setup_integration(
        hass,
        make_config_entry(
            {
                "humidifiers": [
                    {
                        "id": 32,
                        "switch_id": 65,
                        "humidity_sensor_id": 63,
                        "action_id": 64,
                        "mode_id": 6,
                        "min_humidity": 30,
                        "max_humidity": 70,
                    }
                ]
            }
        ),
    )

    state = hass.states.get(ENTITY_ID)
    assert state.state == STATE_OFF
    assert state.attributes["current_humidity"] == 45
    assert state.attributes["available_modes"] == ["Off", "Party", "Relax"]
    assert state.attributes["min_humidity"] == 30
    assert state.attributes["max_humidity"] == 70

    # On/off drives the dedicated switch device, not the output.
    await hass.services.async_call(
        HUMIDIFIER_DOMAIN,
        SERVICE_TURN_ON,
        {ATTR_ENTITY_ID: ENTITY_ID},
        blocking=True,
    )
    await hass.async_block_till_done()
    assert (65, {ValueType.SWITCH_STATE: 1}) in mock_hub.api.set_calls
    assert hass.states.get(ENTITY_ID).state == STATE_ON

    # Setting the humidity keeps the switch on and writes the output value.
    await hass.services.async_call(
        HUMIDIFIER_DOMAIN,
        SERVICE_SET_HUMIDITY,
        {ATTR_ENTITY_ID: ENTITY_ID, ATTR_HUMIDITY: 50},
        blocking=True,
    )
    await hass.async_block_till_done()
    assert (
        32,
        {ValueType.SWITCH_STATE: 1, ValueType.ANALOG_OUTPUT_DESIRED_VALUE: 0.5},
    ) in mock_hub.api.set_calls

    await hass.services.async_call(
        HUMIDIFIER_DOMAIN,
        "set_mode",
        {ATTR_ENTITY_ID: ENTITY_ID, "mode": "Relax"},
        blocking=True,
    )
    await hass.async_block_till_done()
    assert any(
        call[0] == 6 and call[1].get(ValueType.MULTI_VALUE_SWITCH_STATE) == 2
        for call in mock_hub.api.set_calls
    )
    assert hass.states.get(ENTITY_ID).attributes["mode"] == "Relax"

    # The action device reports what the humidifier is doing.
    mock_hub.devices[64].state.apply_changes(
        {ValueType.MULTI_VALUE_SWITCH_STATE: 2.0}
    )
    await hass.async_block_till_done()
    assert hass.states.get(ENTITY_ID).attributes["action"] == "humidifying"

    await hass.services.async_call(
        HUMIDIFIER_DOMAIN,
        SERVICE_TURN_OFF,
        {ATTR_ENTITY_ID: ENTITY_ID},
        blocking=True,
    )
    await hass.async_block_till_done()
    assert (65, {ValueType.SWITCH_STATE: 0}) in mock_hub.api.set_calls
    assert hass.states.get(ENTITY_ID).state == STATE_OFF
