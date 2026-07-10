"""Tests for importing the legacy YAML configuration."""

from homeassistant.core import HomeAssistant
from homeassistant.helpers import issue_registry as ir
from homeassistant.setup import async_setup_component

from custom_components.taphome.const import CONF_API_URL, DOMAIN
from tests_common import (
    TEST_LOCATION_ID,
    TEST_TOKEN,
    device_subentry_configs,
)


async def test_yaml_import_creates_entry_and_repair_issue(
    hass: HomeAssistant, mock_hub
) -> None:
    """A legacy YAML section is imported into a config entry once."""
    config = {
        DOMAIN: {
            "cores": [
                {
                    "token": TEST_TOKEN,
                    "ip": "10.0.0.5",
                    "lights": [1],
                    "switches": [{"id": 2, "device_class": "outlet"}],
                }
            ]
        }
    }

    assert await async_setup_component(hass, DOMAIN, config)
    await hass.async_block_till_done()

    [entry] = hass.config_entries.async_entries(DOMAIN)
    assert entry.unique_id == TEST_LOCATION_ID
    assert entry.data[CONF_API_URL] == "http://10.0.0.5/api/TapHomeApi/v1"
    assert device_subentry_configs(entry, "lights") == [{"id": 1}]
    assert device_subentry_configs(entry, "switches") == [
        {"id": 2, "device_class": "outlet"}
    ]

    # Subentries are titled after the TapHome device (name and API id).
    from tests_common import device_subentry

    socket = device_subentry(entry, "switches", 2)
    assert socket.title == "Garden Socket (2)"

    issue_registry = ir.async_get(hass)
    assert any(
        issue.domain == DOMAIN and issue.issue_id == "yaml_deprecated"
        for issue in issue_registry.issues.values()
    )

    # A second import of the same core does not create a duplicate entry.
    assert await async_setup_component(hass, DOMAIN, config)
    await hass.async_block_till_done()
    assert len(hass.config_entries.async_entries(DOMAIN)) == 1
