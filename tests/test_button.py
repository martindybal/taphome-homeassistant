"""Tests for the TapHome button platform."""

from taphome_sdk import ValueType

from homeassistant.components.button import DOMAIN as BUTTON_DOMAIN, SERVICE_PRESS
from homeassistant.const import ATTR_ENTITY_ID
from homeassistant.core import HomeAssistant
from homeassistant.helpers import entity_registry as er

from custom_components.taphome.const import DOMAIN
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

ENTITY_ID = "button.wall_button"


async def test_button_press(hass: HomeAssistant, mock_hub) -> None:
    """Pressing the button entity sends the press action to the core."""
    make_device(mock_hub, BUTTON_DEFINITION)
    await setup_integration(hass, make_config_entry({"buttons": [{"id": 30}]}))

    assert hass.states.get(ENTITY_ID) is not None

    await hass.services.async_call(
        BUTTON_DOMAIN,
        SERVICE_PRESS,
        {ATTR_ENTITY_ID: ENTITY_ID},
        blocking=True,
    )
    await hass.async_block_till_done()

    assert (30, {ValueType.BUTTON_PRESSED: 1}) in mock_hub.api.set_calls


async def test_button_configured_actions(hass: HomeAssistant, mock_hub) -> None:
    """Each configured action becomes its own button entity."""
    make_device(mock_hub, BUTTON_DEFINITION)
    await setup_integration(
        hass,
        make_config_entry(
            {"buttons": [{"id": 30, "actions": ["press", "long_press"]}]}
        ),
    )

    entity_registry = er.async_get(hass)
    press = entity_registry.async_get_entity_id(
        "button", DOMAIN, "taphome.button.press.30"
    )
    long_press = entity_registry.async_get_entity_id(
        "button", DOMAIN, "taphome.button.longpress.30"
    )
    assert press is not None
    assert long_press is not None

    await hass.services.async_call(
        BUTTON_DOMAIN,
        SERVICE_PRESS,
        {ATTR_ENTITY_ID: long_press},
        blocking=True,
    )
    await hass.async_block_till_done()

    assert (30, {ValueType.BUTTON_PRESSED: 2}) in mock_hub.api.set_calls
