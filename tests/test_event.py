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
        {"valueTypeId": ValueType.BUTTON_HELD_STATE.value, "readOnly": True},
    ],
    "values": {ValueType.BUTTON_PRESSED: 0.0, ValueType.BUTTON_HELD_STATE: 0.0},
}

ENTITY_ID = "event.wall_button"


def _button_push(value_type: ValueType, value: float) -> dict:
    """Return a webhook payload carrying one changed value of the button."""
    return {
        "devices": [
            {
                "deviceId": 30,
                "values": [{"valueTypeId": value_type.value, "value": value}],
            }
        ],
        "timestamp": 2,
    }


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


async def test_long_press_fires_once_despite_held_state_pushes(
    hass: HomeAssistant, mock_hub, freezer
) -> None:
    """Held-state pushes during a long press do not re-fire the event (#211)."""
    make_device(mock_hub, BUTTON_DEFINITION)
    await setup_integration(hass, make_config_entry({"buttons": [{"id": 30}]}))

    await mock_hub.async_handle_webhook(_button_push(ValueType.BUTTON_PRESSED, 2))
    await hass.async_block_till_done()
    long_press = hass.states.get(ENTITY_ID)
    assert long_press.attributes["event_type"] == "long_press"

    # The Core pushes the held state when the hold starts and on release;
    # a re-fired event would carry a later timestamp.
    freezer.tick(1)
    await mock_hub.async_handle_webhook(_button_push(ValueType.BUTTON_HELD_STATE, 1))
    freezer.tick(1)
    await mock_hub.async_handle_webhook(_button_push(ValueType.BUTTON_HELD_STATE, 0))
    await hass.async_block_till_done()

    assert hass.states.get(ENTITY_ID).state == long_press.state


async def test_repeated_gesture_fires_each_time(
    hass: HomeAssistant, mock_hub, freezer
) -> None:
    """The same gesture pushed twice in a row fires twice."""
    make_device(mock_hub, BUTTON_DEFINITION)
    await setup_integration(hass, make_config_entry({"buttons": [{"id": 30}]}))

    await mock_hub.async_handle_webhook(_button_push(ValueType.BUTTON_PRESSED, 2))
    await hass.async_block_till_done()
    first = hass.states.get(ENTITY_ID).state

    freezer.tick(5)
    await mock_hub.async_handle_webhook(_button_push(ValueType.BUTTON_PRESSED, 2))
    await hass.async_block_till_done()

    state = hass.states.get(ENTITY_ID)
    assert state.state != first
    assert state.attributes["event_type"] == "long_press"
