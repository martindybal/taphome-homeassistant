"""Tests for the TapHome repair flows."""

from taphome_sdk import ValueType

from homeassistant.core import HomeAssistant
from homeassistant.helpers import issue_registry as ir

from custom_components.taphome.const import CONF_KNOWN_DEVICE_IDS, DOMAIN
from custom_components.taphome.repairs import async_create_fix_flow
from tests_common import device_subentry, make_config_entry, make_device


async def _setup_with_new_device(
    hass: HomeAssistant, known: list[int], device_id: int
):
    """Set up an entry whose known baseline omits ``device_id``."""
    entry = make_config_entry()
    entry.add_to_hass(hass)
    hass.config_entries.async_update_entry(
        entry, data={**entry.data, CONF_KNOWN_DEVICE_IDS: known}
    )
    await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()

    registry = ir.async_get(hass)
    issue = next(
        issue
        for issue in registry.issues.values()
        if issue.domain == DOMAIN and issue.issue_id.endswith(f"_{device_id}")
    )
    return entry, issue


async def _start_flow(hass: HomeAssistant, issue):
    """Create the fix flow for the issue."""
    flow = await async_create_fix_flow(hass, issue.issue_id, issue.data)
    flow.hass = hass
    flow.flow_id = "test-flow"
    flow.handler = DOMAIN
    return flow


async def test_menu_lists_only_valid_types(hass: HomeAssistant, mock_hub) -> None:
    """The menu offers the types the device qualifies for, plus ignore."""
    # Device 6 is a multi-value switch (a digital output subtype), so it can be
    # a select and the generic-output types, but not a cover/thermostat/button.
    _, issue = await _setup_with_new_device(hass, [1, 2, 3, 4, 5], 6)
    flow = await _start_flow(hass, issue)

    result = await flow.async_step_init()
    assert result["type"] == "menu"
    assert result["step_id"] == "menu"
    assert "select" in result["menu_options"]
    assert "ignore" in result["menu_options"]
    assert "cover" not in result["menu_options"]
    assert "thermostat" not in result["menu_options"]
    assert "button" not in result["menu_options"]


async def test_add_type_without_options(hass: HomeAssistant, mock_hub) -> None:
    """Picking a fieldless type adds the subentry straight away."""
    entry, issue = await _setup_with_new_device(hass, [1, 2, 3, 4, 5], 6)
    flow = await _start_flow(hass, issue)
    await flow.async_step_init()

    # Selecting the type from the menu routes to its archetype step.
    result = await flow.async_step_select()
    await hass.async_block_till_done()

    assert result["type"] == "create_entry"
    assert device_subentry(entry, "multivalue_switches", 6) is not None
    assert 6 in entry.data[CONF_KNOWN_DEVICE_IDS]
    # The subentry change reloaded the entry and created the select entity.
    assert hass.states.get("select.scene_switch") is not None


async def test_add_type_with_options(hass: HomeAssistant, mock_hub) -> None:
    """A type with fields shows its form (no device picker) before adding."""
    # Device 4 is blinds; expose it as a cover with a device class.
    entry, issue = await _setup_with_new_device(hass, [1, 2, 3, 5, 6], 4)
    flow = await _start_flow(hass, issue)
    await flow.async_step_init()

    result = await flow.async_step_cover()
    assert result["type"] == "form"
    assert result["step_id"] == "cover"
    # The device is fixed, so the form only asks for the cover options.
    assert "device" not in result["data_schema"].schema

    result = await flow.async_step_cover({"device_class": "blind"})
    await hass.async_block_till_done()

    assert result["type"] == "create_entry"
    subentry = device_subentry(entry, "covers", 4)
    assert subentry is not None
    assert subentry.data["device_class"] == "blind"
    assert 4 in entry.data[CONF_KNOWN_DEVICE_IDS]
    assert hass.states.get("cover.bedroom_blinds") is not None


async def test_add_per_value_sensor(hass: HomeAssistant, mock_hub) -> None:
    """A sensor type lets the user pick which values to expose."""
    make_device(
        mock_hub,
        {
            "deviceId": 7,
            "type": "Sensor",
            "name": "Bathroom Sensor",
            "description": "",
            "supportedValues": [
                {"valueTypeId": ValueType.HUMIDITY.value, "readOnly": True}
            ],
            "values": {ValueType.HUMIDITY: 0.5},
        },
    )
    entry, issue = await _setup_with_new_device(hass, [1, 2, 3, 4, 5, 6], 7)
    flow = await _start_flow(hass, issue)
    await flow.async_step_init()

    result = await flow.async_step_sensor()
    assert result["type"] == "form"
    assert result["step_id"] == "sensor_values"

    result = await flow.async_step_sensor_values(
        {"values": [str(ValueType.HUMIDITY.value)]}
    )
    await hass.async_block_till_done()

    assert result["type"] == "create_entry"
    subentry = device_subentry(entry, "sensors", 7)
    assert subentry is not None
    assert subentry.data["value"] == ValueType.HUMIDITY.value
    assert 7 in entry.data[CONF_KNOWN_DEVICE_IDS]


async def test_ignore_marks_known(hass: HomeAssistant, mock_hub) -> None:
    """Ignoring the device only marks it known; nothing is added."""
    entry, issue = await _setup_with_new_device(hass, [1, 2, 3, 4, 5], 6)
    flow = await _start_flow(hass, issue)
    await flow.async_step_init()

    result = await flow.async_step_ignore()
    await hass.async_block_till_done()

    assert result["type"] == "create_entry"
    assert device_subentry(entry, "multivalue_switches", 6) is None
    assert 6 in entry.data[CONF_KNOWN_DEVICE_IDS]


async def test_flow_aborts_when_device_or_entry_gone(
    hass: HomeAssistant, mock_hub
) -> None:
    """The flow aborts when the device disappears or the entry unloads."""
    entry, issue = await _setup_with_new_device(hass, [1, 2, 3, 4, 5], 6)

    flow = await _start_flow(hass, issue)
    mock_hub.devices.pop(6)
    result = await flow.async_step_init()
    assert result["type"] == "abort"
    assert result["reason"] == "device_gone"

    mock_hub.devices[6] = mock_hub.devices[1]
    await hass.config_entries.async_unload(entry.entry_id)
    await hass.async_block_till_done()
    flow = await _start_flow(hass, issue)
    result = await flow.async_step_init()
    assert result["type"] == "abort"
    assert result["reason"] == "entry_not_loaded"
