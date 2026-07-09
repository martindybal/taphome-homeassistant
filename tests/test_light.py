"""Tests for the TapHome light platform."""

from taphome_sdk import ValueType

from homeassistant.components.light import (
    ATTR_BRIGHTNESS,
    ATTR_COLOR_MODE,
    ATTR_COLOR_TEMP_KELVIN,
    ATTR_EFFECT,
    ATTR_EFFECT_LIST,
    ATTR_HS_COLOR,
    DOMAIN as LIGHT_DOMAIN,
    SERVICE_TURN_OFF,
    SERVICE_TURN_ON,
    ColorMode,
)
from homeassistant.const import ATTR_ENTITY_ID, STATE_OFF, STATE_ON
from homeassistant.core import HomeAssistant

from tests_common import make_config_entry, make_device, setup_integration

ENTITY_ID = "light.kitchen_light"

RGB_LIGHT = {
    "deviceId": 60,
    "type": "RgbLight",
    "name": "Living Room Strip",
    "description": "LED strip",
    "supportedValues": [
        {"valueTypeId": ValueType.SWITCH_STATE.value, "readOnly": False},
        {"valueTypeId": ValueType.HUE_BRIGHTNESS.value, "readOnly": False},
        {
            "valueTypeId": ValueType.HUE_BRIGHTNESS_DESIRED_VALUE.value,
            "readOnly": False,
        },
        {"valueTypeId": ValueType.HUE_DEGREES.value, "readOnly": False},
        {"valueTypeId": ValueType.SATURATION.value, "readOnly": False},
        {
            "valueTypeId": ValueType.CORRELATED_COLOR_TEMPERATURE.value,
            "readOnly": False,
            "minValue": 2000,
            "maxValue": 6500,
        },
    ],
    "values": {
        ValueType.SWITCH_STATE: 0.0,
        ValueType.HUE_BRIGHTNESS: 0.0,
        ValueType.HUE_DEGREES: 0.0,
        ValueType.SATURATION: 0.0,
    },
}

DUAL_WHITE_LIGHT = {
    "deviceId": 61,
    "type": "DualWhiteLight",
    "name": "Kitchen Panel",
    "description": "Tunable white panel",
    "supportedValues": [
        {"valueTypeId": ValueType.SWITCH_STATE.value, "readOnly": False},
        {"valueTypeId": ValueType.HUE_BRIGHTNESS.value, "readOnly": False},
        {
            "valueTypeId": ValueType.HUE_BRIGHTNESS_DESIRED_VALUE.value,
            "readOnly": False,
        },
        {
            "valueTypeId": ValueType.CORRELATED_COLOR_TEMPERATURE.value,
            "readOnly": False,
            "minValue": 2700,
            "maxValue": 6000,
        },
    ],
    "values": {
        ValueType.SWITCH_STATE: 0.0,
        ValueType.HUE_BRIGHTNESS: 0.0,
    },
}


async def test_light_turn_on_with_brightness(hass: HomeAssistant, mock_hub) -> None:
    """Turning the light on sends the scaled brightness to the core."""
    await setup_integration(hass, make_config_entry())
    assert hass.states.get(ENTITY_ID).state == STATE_OFF

    await hass.services.async_call(
        LIGHT_DOMAIN,
        SERVICE_TURN_ON,
        {ATTR_ENTITY_ID: ENTITY_ID, ATTR_BRIGHTNESS: 128},
        blocking=True,
    )
    await hass.async_block_till_done()

    # HA brightness 128 of 255 becomes a 0..1 output value on the TapHome API.
    assert (
        1,
        {ValueType.SWITCH_STATE: 1, ValueType.ANALOG_OUTPUT_DESIRED_VALUE: 0.5},
    ) in mock_hub.api.set_calls

    state = hass.states.get(ENTITY_ID)
    assert state.state == STATE_ON
    assert state.attributes[ATTR_BRIGHTNESS] == 128


async def test_light_turn_off(hass: HomeAssistant, mock_hub) -> None:
    """Turning the light off resets the switch state."""
    await setup_integration(hass, make_config_entry())
    await hass.services.async_call(
        LIGHT_DOMAIN,
        SERVICE_TURN_ON,
        {ATTR_ENTITY_ID: ENTITY_ID},
        blocking=True,
    )

    await hass.services.async_call(
        LIGHT_DOMAIN,
        SERVICE_TURN_OFF,
        {ATTR_ENTITY_ID: ENTITY_ID},
        blocking=True,
    )
    await hass.async_block_till_done()

    assert (1, {ValueType.SWITCH_STATE: 0}) in mock_hub.api.set_calls
    assert hass.states.get(ENTITY_ID).state == STATE_OFF


async def test_light_push_update(hass: HomeAssistant, mock_hub) -> None:
    """A state pushed by the core updates the entity without polling."""
    await setup_integration(hass, make_config_entry())

    mock_hub.devices[1].state.apply_changes(
        {
            ValueType.SWITCH_STATE: 1,
            ValueType.ANALOG_OUTPUT_VALUE: 1.0,
        }
    )
    await hass.async_block_till_done()

    state = hass.states.get(ENTITY_ID)
    assert state.state == STATE_ON
    assert state.attributes[ATTR_BRIGHTNESS] == 255


async def test_onoff_light(hass: HomeAssistant, mock_hub) -> None:
    """A digital output exposed as light supports plain on/off."""
    await setup_integration(hass, make_config_entry({"lights": [{"id": 2}]}))

    entity_id = "light.garden_socket"
    state = hass.states.get(entity_id)
    assert state.attributes["supported_color_modes"] == [ColorMode.ONOFF]

    await hass.services.async_call(
        LIGHT_DOMAIN,
        SERVICE_TURN_ON,
        {ATTR_ENTITY_ID: entity_id},
        blocking=True,
    )
    await hass.async_block_till_done()
    assert (2, {ValueType.SWITCH_STATE: 1}) in mock_hub.api.set_calls
    assert hass.states.get(entity_id).state == STATE_ON


async def test_rgb_light_turn_on_with_color(hass: HomeAssistant, mock_hub) -> None:
    """Turning an RGB light on writes hue, saturation and brightness."""
    make_device(mock_hub, RGB_LIGHT)
    await setup_integration(hass, make_config_entry({"lights": [{"id": 60}]}))

    await hass.services.async_call(
        LIGHT_DOMAIN,
        SERVICE_TURN_ON,
        {
            ATTR_ENTITY_ID: "light.living_room_strip",
            ATTR_BRIGHTNESS: 255,
            ATTR_HS_COLOR: (30, 50),
        },
        blocking=True,
    )
    await hass.async_block_till_done()

    assert (
        60,
        {
            ValueType.SWITCH_STATE: 1,
            ValueType.HUE_BRIGHTNESS_DESIRED_VALUE: 1.0,
            ValueType.HUE_DEGREES: 30,
            ValueType.SATURATION: 0.5,
        },
    ) in mock_hub.api.set_calls

    state = hass.states.get("light.living_room_strip")
    assert state.state == STATE_ON
    assert state.attributes[ATTR_BRIGHTNESS] == 255
    assert state.attributes[ATTR_HS_COLOR] == (30, 50)
    assert state.attributes[ATTR_COLOR_MODE] == ColorMode.HS


async def test_dual_white_light_color_temperature(
    hass: HomeAssistant, mock_hub
) -> None:
    """A tunable white light exposes and writes the color temperature."""
    make_device(mock_hub, DUAL_WHITE_LIGHT)
    await setup_integration(hass, make_config_entry({"lights": [{"id": 61}]}))

    state = hass.states.get("light.kitchen_panel")
    assert state.attributes["min_color_temp_kelvin"] == 2700
    assert state.attributes["max_color_temp_kelvin"] == 6000

    await hass.services.async_call(
        LIGHT_DOMAIN,
        SERVICE_TURN_ON,
        {
            ATTR_ENTITY_ID: "light.kitchen_panel",
            ATTR_BRIGHTNESS: 128,
            ATTR_COLOR_TEMP_KELVIN: 3000,
        },
        blocking=True,
    )
    await hass.async_block_till_done()

    assert (
        61,
        {
            ValueType.SWITCH_STATE: 1,
            ValueType.HUE_BRIGHTNESS_DESIRED_VALUE: 0.5,
            ValueType.CORRELATED_COLOR_TEMPERATURE: 3000,
        },
    ) in mock_hub.api.set_calls

    state = hass.states.get("light.kitchen_panel")
    assert state.state == STATE_ON
    assert state.attributes[ATTR_COLOR_TEMP_KELVIN] == 3000
    assert state.attributes[ATTR_COLOR_MODE] == ColorMode.COLOR_TEMP


async def test_light_effect_from_multivalue_switch(
    hass: HomeAssistant, mock_hub
) -> None:
    """A configured effect device exposes its options as light effects."""
    await setup_integration(
        hass, make_config_entry({"lights": [{"id": 1, "effect_id": 6}]})
    )

    state = hass.states.get(ENTITY_ID)
    assert state.attributes[ATTR_EFFECT_LIST] == ["Off", "Party", "Relax"]

    # Effect is only reported while the light is on.
    mock_hub.devices[1].state.apply_changes(
        {ValueType.SWITCH_STATE: 1, ValueType.ANALOG_OUTPUT_VALUE: 1.0}
    )
    mock_hub.devices[6].state.apply_changes(
        {ValueType.MULTI_VALUE_SWITCH_STATE: 1.0}
    )
    await hass.async_block_till_done()

    assert hass.states.get(ENTITY_ID).attributes[ATTR_EFFECT] == "Party"


async def test_light_unavailable_when_hub_disconnects(
    hass: HomeAssistant, mock_hub
) -> None:
    """Entities become unavailable when the core connection is lost."""
    from taphome_sdk import HubConnectionState

    await setup_integration(hass, make_config_entry())
    assert hass.states.get(ENTITY_ID).state != "unavailable"

    mock_hub.connection_state.value = HubConnectionState.FAILED
    mock_hub.devices[1].state.apply_changes({ValueType.SWITCH_STATE: 0}, force=True)
    await hass.async_block_till_done()

    assert hass.states.get(ENTITY_ID).state == "unavailable"
