"""Tests for the TapHome select platform (multi-value switches)."""

from taphome_sdk import ValueType

from homeassistant.components.select import (
    ATTR_OPTION,
    ATTR_OPTIONS,
    DOMAIN as SELECT_DOMAIN,
    SERVICE_SELECT_OPTION,
)
from homeassistant.const import ATTR_ENTITY_ID
from homeassistant.core import HomeAssistant

from tests_common import make_config_entry, setup_integration

ENTITY_ID = "select.scene_switch"


async def test_select_exposes_options(hass: HomeAssistant, mock_hub) -> None:
    """The multi-value switch options become select options."""
    await setup_integration(
        hass, make_config_entry({"multivalue_switches": [{"id": 6}]})
    )

    state = hass.states.get(ENTITY_ID)
    assert state.state == "Off"
    assert state.attributes[ATTR_OPTIONS] == ["Off", "Party", "Relax"]


async def test_select_option(hass: HomeAssistant, mock_hub) -> None:
    """Selecting an option writes its value to the core."""
    await setup_integration(
        hass, make_config_entry({"multivalue_switches": [{"id": 6}]})
    )

    await hass.services.async_call(
        SELECT_DOMAIN,
        SERVICE_SELECT_OPTION,
        {ATTR_ENTITY_ID: ENTITY_ID, ATTR_OPTION: "Party"},
        blocking=True,
    )
    await hass.async_block_till_done()

    assert any(
        call[0] == 6 and call[1].get(ValueType.MULTI_VALUE_SWITCH_STATE) == 1
        for call in mock_hub.api.set_calls
    )
    assert hass.states.get(ENTITY_ID).state == "Party"
