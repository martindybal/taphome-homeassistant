"""Tests for the TapHome repair flows."""

from homeassistant.core import HomeAssistant
from homeassistant.helpers import issue_registry as ir

from custom_components.taphome.const import CONF_KNOWN_DEVICE_IDS, DOMAIN
from custom_components.taphome.repairs import async_create_fix_flow
from tests_common import device_subentry, make_config_entry


async def _setup_with_new_device(hass: HomeAssistant):
    """Set up an entry whose known-device baseline is missing device 6."""
    entry = make_config_entry()
    entry.add_to_hass(hass)
    hass.config_entries.async_update_entry(
        entry, data={**entry.data, CONF_KNOWN_DEVICE_IDS: [1, 2, 3, 4, 5]}
    )
    await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()

    registry = ir.async_get(hass)
    issue = next(
        issue
        for issue in registry.issues.values()
        if issue.domain == DOMAIN and issue.issue_id.endswith("_6")
    )
    return entry, issue


async def _start_flow(hass: HomeAssistant, issue):
    """Create the fix flow for the issue and drive it to the confirm form."""
    flow = await async_create_fix_flow(hass, issue.issue_id, issue.data)
    flow.hass = hass
    flow.flow_id = "test-flow"
    flow.handler = DOMAIN
    result = await flow.async_step_init()
    assert result["type"] == "form"
    assert result["step_id"] == "confirm"
    return flow


async def test_new_device_fix_flow_adds_subentry(
    hass: HomeAssistant, mock_hub
) -> None:
    """Picking a platform adds the device subentry and marks it known."""
    entry, issue = await _setup_with_new_device(hass)
    flow = await _start_flow(hass, issue)

    result = await flow.async_step_confirm({"platform": "multivalue_switches"})
    await hass.async_block_till_done()

    assert result["type"] == "create_entry"
    assert device_subentry(entry, "multivalue_switches", 6) is not None
    assert 6 in entry.data[CONF_KNOWN_DEVICE_IDS]
    # The subentry change reloaded the entry and created the select entity.
    assert hass.states.get("select.scene_switch") is not None


async def test_new_device_fix_flow_ignore(hass: HomeAssistant, mock_hub) -> None:
    """Ignoring the device only marks it known; nothing is added."""
    entry, issue = await _setup_with_new_device(hass)
    flow = await _start_flow(hass, issue)

    result = await flow.async_step_confirm({"ignore": True})
    await hass.async_block_till_done()

    assert result["type"] == "create_entry"
    assert device_subentry(entry, "multivalue_switches", 6) is None
    assert 6 in entry.data[CONF_KNOWN_DEVICE_IDS]


async def test_new_device_fix_flow_requires_choice(
    hass: HomeAssistant, mock_hub
) -> None:
    """Submitting neither a platform nor ignore re-shows the form."""
    _, issue = await _setup_with_new_device(hass)
    flow = await _start_flow(hass, issue)

    result = await flow.async_step_confirm({})

    assert result["type"] == "form"
    assert result["errors"] == {"base": "select_platform_or_ignore"}


async def test_new_device_fix_flow_aborts(hass: HomeAssistant, mock_hub) -> None:
    """The flow aborts when the device disappears or the entry unloads."""
    entry, issue = await _setup_with_new_device(hass)

    # Device gone from the hub → abort.
    flow = await _start_flow(hass, issue)
    mock_hub.devices.pop(6)
    result = await flow.async_step_confirm()
    assert result["type"] == "abort"
    assert result["reason"] == "device_gone"

    # The options step without a picked platform falls back to confirm.
    mock_hub.devices[6] = mock_hub.devices[1]
    flow = await _start_flow(hass, issue)
    result = await flow.async_step_options()
    assert result["type"] == "form"
    assert result["step_id"] == "confirm"

    # Entry not loaded → abort.
    await hass.config_entries.async_unload(entry.entry_id)
    await hass.async_block_till_done()
    result = await flow.async_step_confirm()
    assert result["type"] == "abort"
    assert result["reason"] == "entry_not_loaded"


async def test_new_device_fix_flow_with_options(
    hass: HomeAssistant, mock_hub
) -> None:
    """A platform with options shows the options form before adding."""
    entry, issue = await _setup_with_new_device(hass)
    flow = await _start_flow(hass, issue)

    result = await flow.async_step_confirm({"platform": "switches"})
    assert result["type"] == "form"
    assert result["step_id"] == "options"

    result = await flow.async_step_options({"device_class": "outlet"})
    await hass.async_block_till_done()

    assert result["type"] == "create_entry"
    subentry = device_subentry(entry, "switches", 6)
    assert subentry is not None
    assert subentry.data["device_class"] == "outlet"
    assert 6 in entry.data[CONF_KNOWN_DEVICE_IDS]
