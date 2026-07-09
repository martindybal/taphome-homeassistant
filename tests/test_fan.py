"""Tests for the TapHome fan platform."""

from taphome_sdk import ValueType

from homeassistant.components.fan import (
    ATTR_PERCENTAGE,
    ATTR_PRESET_MODE,
    DOMAIN as FAN_DOMAIN,
    SERVICE_SET_PERCENTAGE,
    SERVICE_SET_PRESET_MODE,
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

FAN_DEFINITION = {
    "deviceId": 31,
    "type": "Ventilation",
    "name": "Ceiling Fan",
    "description": "Fan in the bathroom",
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

ENTITY_ID = "fan.ceiling_fan"


async def test_fan_turn_on_off(hass: HomeAssistant, mock_hub) -> None:
    """The fan services drive the TapHome output device."""
    make_device(mock_hub, FAN_DEFINITION)
    await setup_integration(hass, make_config_entry({"fans": [{"id": 31}]}))
    assert hass.states.get(ENTITY_ID).state == STATE_OFF

    await hass.services.async_call(
        FAN_DOMAIN,
        SERVICE_TURN_ON,
        {ATTR_ENTITY_ID: ENTITY_ID},
        blocking=True,
    )
    await hass.async_block_till_done()
    assert (31, {ValueType.SWITCH_STATE: 1}) in mock_hub.api.set_calls
    assert hass.states.get(ENTITY_ID).state == STATE_ON

    await hass.services.async_call(
        FAN_DOMAIN,
        SERVICE_TURN_OFF,
        {ATTR_ENTITY_ID: ENTITY_ID},
        blocking=True,
    )
    await hass.async_block_till_done()
    assert (31, {ValueType.SWITCH_STATE: 0}) in mock_hub.api.set_calls
    assert hass.states.get(ENTITY_ID).state == STATE_OFF


async def test_fan_set_percentage(hass: HomeAssistant, mock_hub) -> None:
    """Setting the speed writes the scaled output value."""
    make_device(mock_hub, FAN_DEFINITION)
    await setup_integration(hass, make_config_entry({"fans": [{"id": 31}]}))

    await hass.services.async_call(
        FAN_DOMAIN,
        SERVICE_SET_PERCENTAGE,
        {ATTR_ENTITY_ID: ENTITY_ID, ATTR_PERCENTAGE: 50},
        blocking=True,
    )
    await hass.async_block_till_done()

    assert (
        31,
        {ValueType.SWITCH_STATE: 1, ValueType.ANALOG_OUTPUT_DESIRED_VALUE: 0.5},
    ) in mock_hub.api.set_calls
    state = hass.states.get(ENTITY_ID)
    assert state.attributes[ATTR_PERCENTAGE] == 50


async def test_fan_turn_on_with_percentage_and_preset(
    hass: HomeAssistant, mock_hub
) -> None:
    """Turning on with a percentage and preset applies both."""
    make_device(mock_hub, FAN_DEFINITION)
    await setup_integration(
        hass, make_config_entry({"fans": [{"id": 31, "preset_mode_id": 6}]})
    )

    await hass.services.async_call(
        FAN_DOMAIN,
        SERVICE_TURN_ON,
        {ATTR_ENTITY_ID: ENTITY_ID, ATTR_PERCENTAGE: 40, ATTR_PRESET_MODE: "Party"},
        blocking=True,
    )
    await hass.async_block_till_done()

    assert (
        31,
        {ValueType.SWITCH_STATE: 1, ValueType.ANALOG_OUTPUT_DESIRED_VALUE: 0.4},
    ) in mock_hub.api.set_calls
    assert any(
        call[0] == 6 and call[1].get(ValueType.MULTI_VALUE_SWITCH_STATE) == 1
        for call in mock_hub.api.set_calls
    )


async def test_fan_preset_mode(hass: HomeAssistant, mock_hub) -> None:
    """A preset-mode multi-value switch drives the fan preset."""
    make_device(mock_hub, FAN_DEFINITION)
    await setup_integration(
        hass, make_config_entry({"fans": [{"id": 31, "preset_mode_id": 6}]})
    )

    state = hass.states.get(ENTITY_ID)
    assert state.attributes["preset_modes"] == ["Off", "Party", "Relax"]

    await hass.services.async_call(
        FAN_DOMAIN,
        SERVICE_SET_PRESET_MODE,
        {ATTR_ENTITY_ID: ENTITY_ID, ATTR_PRESET_MODE: "Relax"},
        blocking=True,
    )
    await hass.async_block_till_done()

    assert any(
        call[0] == 6 and call[1].get(ValueType.MULTI_VALUE_SWITCH_STATE) == 2
        for call in mock_hub.api.set_calls
    )
    assert hass.states.get(ENTITY_ID).attributes[ATTR_PRESET_MODE] == "Relax"
