"""Tests for the TapHome event platform."""

from taphome_sdk import ValueType

from homeassistant.const import STATE_UNKNOWN
from homeassistant.core import HomeAssistant

from tests_common import make_config_entry, make_device, setup_integration

BUTTON_DEFINITION = {
    "deviceId": 30,
    "type": "PushButton",
    "name": "Wall Button",
    "description": "Button by the door",
    "supportedValues": [
        {"valueTypeId": ValueType.BUTTON_PRESSED.value, "readOnly": False},
    ],
    "values": {ValueType.BUTTON_PRESSED: 0.0},
}

ENTITY_ID = "event.wall_button"


async def test_event_exposes_all_actions(hass: HomeAssistant, mock_hub) -> None:
    """A button device creates an event entity listing every action."""
    make_device(mock_hub, BUTTON_DEFINITION)
    await setup_integration(hass, make_config_entry({"buttons": [{"id": 30}]}))

    state = hass.states.get(ENTITY_ID)
    assert state is not None
    assert state.state == STATE_UNKNOWN
    assert "press" in state.attributes["event_types"]
    assert "long_press" in state.attributes["event_types"]


async def test_event_fires_on_button_click(hass: HomeAssistant, mock_hub) -> None:
    """A pushed button press shows up as the entity's last event."""
    make_device(mock_hub, BUTTON_DEFINITION)
    await setup_integration(hass, make_config_entry({"buttons": [{"id": 30}]}))

    mock_hub.devices[30].state.apply_changes({ValueType.BUTTON_PRESSED: 1.0})
    await hass.async_block_till_done()

    state = hass.states.get(ENTITY_ID)
    assert state.state != STATE_UNKNOWN
    assert state.attributes["event_type"] == "press"
