"""Tests for the TapHome switch platform."""

from taphome_sdk import ValueType

from homeassistant.components.switch import (
    DOMAIN as SWITCH_DOMAIN,
    SERVICE_TURN_OFF,
    SERVICE_TURN_ON,
)
from homeassistant.const import ATTR_ENTITY_ID, STATE_OFF, STATE_ON
from homeassistant.core import HomeAssistant

from tests_common import make_config_entry, setup_integration

ENTITY_ID = "switch.garden_socket"


async def test_switch_turn_on_off(hass: HomeAssistant, mock_hub) -> None:
    """The switch services drive the TapHome digital output."""
    await setup_integration(hass, make_config_entry())
    assert hass.states.get(ENTITY_ID).state == STATE_OFF

    await hass.services.async_call(
        SWITCH_DOMAIN,
        SERVICE_TURN_ON,
        {ATTR_ENTITY_ID: ENTITY_ID},
        blocking=True,
    )
    await hass.async_block_till_done()
    assert (2, {ValueType.SWITCH_STATE: 1}) in mock_hub.api.set_calls
    assert hass.states.get(ENTITY_ID).state == STATE_ON

    await hass.services.async_call(
        SWITCH_DOMAIN,
        SERVICE_TURN_OFF,
        {ATTR_ENTITY_ID: ENTITY_ID},
        blocking=True,
    )
    await hass.async_block_till_done()
    assert (2, {ValueType.SWITCH_STATE: 0}) in mock_hub.api.set_calls
    assert hass.states.get(ENTITY_ID).state == STATE_OFF


async def test_switch_push_update(hass: HomeAssistant, mock_hub) -> None:
    """A webhook style push toggles the switch entity."""
    await setup_integration(hass, make_config_entry())

    mock_hub.devices[2].state.apply_changes({ValueType.SWITCH_STATE: 1})
    await hass.async_block_till_done()

    assert hass.states.get(ENTITY_ID).state == STATE_ON
