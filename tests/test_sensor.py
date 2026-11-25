"""Tests for the TapHome sensor platform."""

from taphome_sdk import ValueType

from homeassistant.core import HomeAssistant

from tests_common import make_config_entry, setup_integration

ENTITY_ID = "sensor.outside_temperature"


async def test_sensor_reports_variable_value(hass: HomeAssistant, mock_hub) -> None:
    """A TapHome variable is exposed with its numeric value."""
    await setup_integration(hass, make_config_entry())

    assert hass.states.get(ENTITY_ID).state == "23.4"


async def test_sensor_push_update(hass: HomeAssistant, mock_hub) -> None:
    """A pushed variable change updates the sensor state."""
    await setup_integration(hass, make_config_entry())

    mock_hub.devices[5].state.apply_changes({ValueType.VARIABLE_STATE: 19.1})
    await hass.async_block_till_done()

    assert hass.states.get(ENTITY_ID).state == "19.1"
