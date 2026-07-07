"""Tests for the TapHome binary sensor platform."""

from homeassistant.core import HomeAssistant
from homeassistant.helpers import device_registry as dr, entity_registry as er

from custom_components.taphome.const import DOMAIN
from tests_common import (
    TEST_LOCATION_ID,
    device_subentry,
    make_config_entry,
    setup_integration,
)


async def test_binary_sensor_device_under_subentry_plus_is_alive(
    hass: HomeAssistant, mock_hub
) -> None:
    """A configured binary sensor is added under its subentry; is-alive is not.

    Regression: the platform must add per-device binary sensors through the
    subentry-aware callback while the core-level is-alive sensor belongs to the
    entry itself.
    """
    entry = make_config_entry({"binary_sensors": [{"id": 5}]})
    await setup_integration(hass, entry)

    entity_registry = er.async_get(hass)
    device = dr.async_get(hass).async_get_device({(DOMAIN, f"{TEST_LOCATION_ID}_5")})
    assert device is not None

    binary_sensors = [
        registry_entry
        for registry_entry in er.async_entries_for_device(entity_registry, device.id)
        if registry_entry.domain == "binary_sensor"
    ]
    assert len(binary_sensors) == 1
    subentry = device_subentry(entry, "binary_sensors", 5)
    assert binary_sensors[0].config_subentry_id == subentry.subentry_id

    # The core-level "is alive" sensor exists and belongs to the entry, not a subentry.
    is_alive = entity_registry.async_get("binary_sensor.taphome_is_alive_sensor")
    assert is_alive is not None
    assert is_alive.config_subentry_id is None
