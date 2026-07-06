"""Tests for the TapHome options flow (the Configure dialog)."""

from homeassistant.const import CONF_TOKEN, CONF_WEBHOOK_ID
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResultType

from custom_components.taphome.const import CONF_IP
from tests_common import TEST_TOKEN, make_config_entry, setup_integration


async def _start_options_flow(hass: HomeAssistant, entry):
    result = await hass.config_entries.options.async_init(entry.entry_id)
    assert result["type"] is FlowResultType.MENU
    return result


async def test_options_menu_requires_loaded_entry(
    hass: HomeAssistant, mock_hub
) -> None:
    """The options flow only works while the entry is loaded."""
    entry = make_config_entry()
    entry.add_to_hass(hass)

    result = await hass.config_entries.options.async_init(entry.entry_id)

    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "entry_not_loaded"


async def test_options_core_settings_updates_webhook(
    hass: HomeAssistant, mock_hub
) -> None:
    """Changing the webhook id in core settings is stored in the options."""
    entry = make_config_entry()
    await setup_integration(hass, entry)

    result = await _start_options_flow(hass, entry)
    result = await hass.config_entries.options.async_configure(
        result["flow_id"], {"next_step_id": "core_settings"}
    )
    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "core_settings"

    result = await hass.config_entries.options.async_configure(
        result["flow_id"],
        {
            CONF_TOKEN: TEST_TOKEN,
            CONF_IP: "10.0.0.5",
            CONF_WEBHOOK_ID: "taphome-hook",
        },
    )
    await hass.async_block_till_done()

    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert entry.options[CONF_WEBHOOK_ID] == "taphome-hook"


async def test_options_add_device(hass: HomeAssistant, mock_hub) -> None:
    """A not yet configured device can be added from the options menu."""
    entry = make_config_entry({"switches": []})
    await setup_integration(hass, entry)

    result = await _start_options_flow(hass, entry)
    result = await hass.config_entries.options.async_configure(
        result["flow_id"], {"next_step_id": "add_devices"}
    )
    assert result["step_id"] == "add_devices"

    result = await hass.config_entries.options.async_configure(
        result["flow_id"], {"devices": ["2"]}
    )
    assert result["step_id"] == "add_devices_platform"

    result = await hass.config_entries.options.async_configure(
        result["flow_id"], {"Garden Socket (2)": {"domains": ["switches"]}}
    )
    assert result["step_id"] == "add_devices_options"

    result = await hass.config_entries.options.async_configure(result["flow_id"], {})
    await hass.async_block_till_done()

    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert entry.options["switches"] == [{"id": 2}]
    assert hass.states.get("switch.garden_socket") is not None


async def test_options_remove_device(hass: HomeAssistant, mock_hub) -> None:
    """Removing a configured device drops its options and its entity."""
    entry = make_config_entry()
    await setup_integration(hass, entry)
    assert hass.states.get("switch.garden_socket") is not None

    result = await _start_options_flow(hass, entry)
    result = await hass.config_entries.options.async_configure(
        result["flow_id"], {"next_step_id": "remove_devices"}
    )
    assert result["step_id"] == "remove_devices"

    result = await hass.config_entries.options.async_configure(
        result["flow_id"], {"devices": ["switch.garden_socket"]}
    )
    await hass.async_block_till_done()

    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert not entry.options.get("switches")
    assert hass.states.get("switch.garden_socket") is None
