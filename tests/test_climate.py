"""Tests for the TapHome climate platform."""

from taphome_sdk import ValueType

from homeassistant.components.climate import (
    ATTR_CURRENT_TEMPERATURE,
    ATTR_TEMPERATURE,
    DOMAIN as CLIMATE_DOMAIN,
    SERVICE_SET_TEMPERATURE,
)
from homeassistant.const import ATTR_ENTITY_ID
from homeassistant.core import HomeAssistant

from tests_common import make_config_entry, setup_integration

ENTITY_ID = "climate.living_room_thermostat"


async def test_climate_reports_temperatures(hass: HomeAssistant, mock_hub) -> None:
    """The thermostat exposes current and target temperature."""
    await setup_integration(hass, make_config_entry({"climates": [{"id": 3}]}))

    state = hass.states.get(ENTITY_ID)
    assert state.attributes[ATTR_CURRENT_TEMPERATURE] == 21.3
    assert state.attributes[ATTR_TEMPERATURE] == 22.0


async def test_climate_set_temperature(hass: HomeAssistant, mock_hub) -> None:
    """Setting the target temperature writes the set point to the core."""
    await setup_integration(hass, make_config_entry({"climates": [{"id": 3}]}))

    await hass.services.async_call(
        CLIMATE_DOMAIN,
        SERVICE_SET_TEMPERATURE,
        {ATTR_ENTITY_ID: ENTITY_ID, ATTR_TEMPERATURE: 23.5},
        blocking=True,
    )
    await hass.async_block_till_done()

    assert any(
        call[0] == 3 and call[1].get(ValueType.TEMPERATURE_SET_POINT) == 23.5
        for call in mock_hub.api.set_calls
    )
    assert hass.states.get(ENTITY_ID).attributes[ATTR_TEMPERATURE] == 23.5


async def test_climate_push_update(hass: HomeAssistant, mock_hub) -> None:
    """A pushed temperature change updates the entity."""
    await setup_integration(hass, make_config_entry({"climates": [{"id": 3}]}))

    mock_hub.devices[3].state.apply_changes({ValueType.REAL_TEMPERATURE: 19.8})
    await hass.async_block_till_done()

    state = hass.states.get(ENTITY_ID)
    assert state.attributes[ATTR_CURRENT_TEMPERATURE] == 19.8
