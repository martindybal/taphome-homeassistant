"""Tests for the TapHome light platform."""

from taphome_sdk import ValueType

from homeassistant.components.light import (
    ATTR_BRIGHTNESS,
    DOMAIN as LIGHT_DOMAIN,
    SERVICE_TURN_OFF,
    SERVICE_TURN_ON,
)
from homeassistant.const import ATTR_ENTITY_ID, STATE_OFF, STATE_ON
from homeassistant.core import HomeAssistant

from tests_common import make_config_entry, setup_integration

ENTITY_ID = "light.kitchen_light"


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
