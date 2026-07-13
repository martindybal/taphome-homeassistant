"""Tests for the TapHome cover platform."""

from taphome_sdk import ValueType

from homeassistant.components.cover import (
    ATTR_CURRENT_POSITION,
    ATTR_CURRENT_TILT_POSITION,
    ATTR_POSITION,
    ATTR_TILT_POSITION,
    DOMAIN as COVER_DOMAIN,
    SERVICE_CLOSE_COVER,
    SERVICE_CLOSE_COVER_TILT,
    SERVICE_OPEN_COVER,
    SERVICE_OPEN_COVER_TILT,
    SERVICE_SET_COVER_POSITION,
    SERVICE_SET_COVER_TILT_POSITION,
    CoverState,
)
from homeassistant.const import ATTR_ENTITY_ID
from homeassistant.core import HomeAssistant

from tests_common import make_config_entry, make_device, setup_integration

ENTITY_ID = "cover.bedroom_blinds"

TILT_BLINDS = {
    "deviceId": 66,
    "type": "Blinds",
    "name": "Office Blinds",
    "description": "Blinds with tilt",
    "supportedValues": [
        {"valueTypeId": ValueType.BLINDS_LEVEL.value, "readOnly": False},
        {"valueTypeId": ValueType.BLINDS_IS_MOVING.value, "readOnly": True},
        {"valueTypeId": ValueType.BLINDS_SLOPE.value, "readOnly": False},
    ],
    "values": {
        ValueType.BLINDS_LEVEL: 0.0,
        ValueType.BLINDS_IS_MOVING: 0.0,
        ValueType.BLINDS_SLOPE: 0.0,
    },
}


async def test_cover_reports_position(hass: HomeAssistant, mock_hub) -> None:
    """TapHome blinds level 0 is a fully open cover in Home Assistant."""
    await setup_integration(hass, make_config_entry({"covers": [{"id": 4}]}))

    state = hass.states.get(ENTITY_ID)
    assert state.state == CoverState.OPEN
    assert state.attributes[ATTR_CURRENT_POSITION] == 100


async def test_cover_set_position(hass: HomeAssistant, mock_hub) -> None:
    """Setting the position sends the inverted 0..1 level to the core."""
    await setup_integration(hass, make_config_entry({"covers": [{"id": 4}]}))

    await hass.services.async_call(
        COVER_DOMAIN,
        SERVICE_SET_COVER_POSITION,
        {ATTR_ENTITY_ID: ENTITY_ID, ATTR_POSITION: 30},
        blocking=True,
    )
    await hass.async_block_till_done()

    # HA position 30 % open = TapHome blinds level 0.7 closed.
    assert any(
        call[0] == 4 and call[1].get(ValueType.BLINDS_LEVEL) == 0.7
        for call in mock_hub.api.set_calls
    )
    assert hass.states.get(ENTITY_ID).attributes[ATTR_CURRENT_POSITION] == 30


async def test_cover_open_and_unknown_position(
    hass: HomeAssistant, mock_hub, freezer
) -> None:
    """Opening writes level 0; an unreported position clears the state."""
    await setup_integration(hass, make_config_entry({"covers": [{"id": 4}]}))

    await hass.services.async_call(
        COVER_DOMAIN,
        SERVICE_OPEN_COVER,
        {ATTR_ENTITY_ID: ENTITY_ID},
        blocking=True,
    )
    await hass.async_block_till_done()
    assert any(
        call[0] == 4 and call[1].get(ValueType.BLINDS_LEVEL) == 0
        for call in mock_hub.api.set_calls
    )

    # After the movement window, the core reporting "NaN" means the
    # position is unknown and the cover reports no state at all.
    freezer.tick(4)
    mock_hub.devices[4].state.apply_changes(
        {ValueType.BLINDS_LEVEL: "NaN"}, force=True
    )
    await hass.async_block_till_done()
    state = hass.states.get(ENTITY_ID)
    assert ATTR_CURRENT_POSITION not in state.attributes


async def test_cover_tilt(hass: HomeAssistant, mock_hub) -> None:
    """Tilt services send the inverted slope to the core."""
    make_device(mock_hub, TILT_BLINDS)
    await setup_integration(hass, make_config_entry({"covers": [{"id": 66}]}))

    entity_id = "cover.office_blinds"
    assert hass.states.get(entity_id).attributes[ATTR_CURRENT_TILT_POSITION] == 100

    await hass.services.async_call(
        COVER_DOMAIN,
        SERVICE_SET_COVER_TILT_POSITION,
        {ATTR_ENTITY_ID: entity_id, ATTR_TILT_POSITION: 30},
        blocking=True,
    )
    await hass.async_block_till_done()
    # HA tilt 30 % open = TapHome slope 0.7.
    assert any(
        call[0] == 66 and call[1].get(ValueType.BLINDS_SLOPE) == 0.7
        for call in mock_hub.api.set_calls
    )
    assert (
        hass.states.get(entity_id).attributes[ATTR_CURRENT_TILT_POSITION] == 30
    )

    await hass.services.async_call(
        COVER_DOMAIN,
        SERVICE_OPEN_COVER_TILT,
        {ATTR_ENTITY_ID: entity_id},
        blocking=True,
    )
    await hass.async_block_till_done()
    assert any(
        call[0] == 66 and call[1].get(ValueType.BLINDS_SLOPE) == 0
        for call in mock_hub.api.set_calls
    )

    await hass.services.async_call(
        COVER_DOMAIN,
        SERVICE_CLOSE_COVER_TILT,
        {ATTR_ENTITY_ID: entity_id},
        blocking=True,
    )
    await hass.async_block_till_done()
    assert any(
        call[0] == 66 and call[1].get(ValueType.BLINDS_SLOPE) == 1
        for call in mock_hub.api.set_calls
    )


async def test_cover_close(hass: HomeAssistant, mock_hub, freezer) -> None:
    """Closing the cover drives the blinds level to 1."""
    await setup_integration(hass, make_config_entry({"covers": [{"id": 4}]}))

    await hass.services.async_call(
        COVER_DOMAIN,
        SERVICE_CLOSE_COVER,
        {ATTR_ENTITY_ID: ENTITY_ID},
        blocking=True,
    )
    await hass.async_block_till_done()

    assert any(
        call[0] == 4 and call[1].get(ValueType.BLINDS_LEVEL) == 1
        for call in mock_hub.api.set_calls
    )
    # Right after the command the device reports pending movement.
    assert hass.states.get(ENTITY_ID).state == CoverState.CLOSING

    # Once the movement window passes and the core confirms the blinds
    # stopped, the cover reports closed.
    freezer.tick(4)
    mock_hub.devices[4].state.apply_changes(
        {ValueType.BLINDS_LEVEL: 1, ValueType.BLINDS_IS_MOVING: 0}, force=True
    )
    await hass.async_block_till_done()
    assert hass.states.get(ENTITY_ID).state == CoverState.CLOSED
