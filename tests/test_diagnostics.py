"""Tests for the TapHome diagnostics."""

from homeassistant.const import CONF_TOKEN
from homeassistant.core import HomeAssistant

from tests_common import make_config_entry, setup_integration


async def test_config_entry_diagnostics(hass: HomeAssistant, mock_hub) -> None:
    """The entry diagnostics redact the token and dump every device."""
    from custom_components.taphome.diagnostics import (
        async_get_config_entry_diagnostics,
    )

    entry = make_config_entry()
    await setup_integration(hass, entry)

    diagnostics = await async_get_config_entry_diagnostics(hass, entry)

    assert diagnostics["entry"]["data"][CONF_TOKEN] == "**REDACTED**"
    assert diagnostics["core"]["location_name"] == "Test Home"
    assert diagnostics["core"]["device_count"] == len(mock_hub.devices)

    socket = next(device for device in diagnostics["devices"] if device["id"] == 2)
    assert socket["name"] == "Garden Socket"
    assert socket["device_type"] == "PowerOutlet"
    assert "SWITCH_STATE" in socket["values"]


async def test_device_diagnostics(hass: HomeAssistant, mock_hub) -> None:
    """The device diagnostics dump only the device of that device page."""
    from homeassistant.helpers import device_registry as dr

    from custom_components.taphome.const import DOMAIN
    from custom_components.taphome.diagnostics import async_get_device_diagnostics
    from tests_common import TEST_LOCATION_ID

    entry = make_config_entry()
    await setup_integration(hass, entry)

    device = dr.async_get(hass).async_get_device({(DOMAIN, f"{TEST_LOCATION_ID}_2")})
    diagnostics = await async_get_device_diagnostics(hass, entry, device)

    assert [device["id"] for device in diagnostics["devices"]] == [2]
