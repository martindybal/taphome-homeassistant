"""Tests for the TapHome Configure dialog and device subentry flow."""

from homeassistant.config_entries import SOURCE_USER
from homeassistant.const import CONF_TOKEN, CONF_WEBHOOK_ID
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResultType

from custom_components.taphome.const import CONF_IP
from tests_common import (
    TEST_TOKEN,
    device_subentry,
    device_subentry_configs,
    make_config_entry,
    setup_integration,
)


async def _start_options_flow(hass: HomeAssistant, entry):
    result = await hass.config_entries.options.async_init(entry.entry_id)
    assert result["type"] is FlowResultType.MENU
    return result


async def _reconfigure(hass: HomeAssistant, entry, platform: str, device_id: int):
    """Open the reconfigure flow of one device subentry."""
    subentry = device_subentry(entry, platform, device_id)
    assert subentry is not None
    result = await entry.start_subentry_reconfigure_flow(hass, subentry.subentry_id)
    assert result["step_id"] == "reconfigure"
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
    """The bulk Add devices step stores each picked device as a subentry."""
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
    assert device_subentry(entry, "switches", 2) is not None
    assert hass.states.get("switch.garden_socket") is not None


def _devices_field(data_schema):
    """Return the (default, selector) of the add-devices ``devices`` field."""
    for marker, selector in data_schema.schema.items():
        if getattr(marker, "schema", marker) == "devices":
            return marker.default(), selector
    raise AssertionError("no 'devices' field in the add_devices schema")


async def test_add_devices_skips_helper_referenced_device(
    hass: HomeAssistant, mock_hub
) -> None:
    """A device used only as another device's helper is not preselected."""
    # Garden Socket (2) is not exposed on its own; it is only used as the
    # thermostat's hvac switch. It is in use, so it must not be preselected,
    # while a genuinely unused device (Bedroom Blinds, 4) still is.
    entry = make_config_entry(
        {
            "switches": [],
            "climates": [{"id": 3, "hvac_switch_id": 2, "hvac_mode": "heat"}],
        }
    )
    await setup_integration(hass, entry)

    result = await _start_options_flow(hass, entry)
    result = await hass.config_entries.options.async_configure(
        result["flow_id"], {"next_step_id": "add_devices"}
    )
    assert result["step_id"] == "add_devices"

    default, selector = _devices_field(result["data_schema"])
    # Configured (1, 3, 5) and helper-referenced (2) devices are excluded; a
    # genuinely unused device (4) is still preselected.
    assert "2" not in default
    assert "4" in default
    assert {"1", "3", "5"}.isdisjoint(default)
    # Device 2 remains a selectable option so it can still be added manually.
    options = {option["value"] for option in selector.config["options"]}
    assert "2" in options


async def test_subentry_add_single_device(hass: HomeAssistant, mock_hub) -> None:
    """The device subentry flow adds one device via device → platform → options."""
    entry = make_config_entry()
    await setup_integration(hass, entry)

    result = await hass.config_entries.subentries.async_init(
        (entry.entry_id, "device"), context={"source": SOURCE_USER}
    )
    assert result["step_id"] == "user"

    # Bedroom Blinds (4) is not configured yet; it qualifies for covers plus the
    # generic sensor/binary-sensor platforms, so the platform step is shown.
    result = await hass.config_entries.subentries.async_configure(
        result["flow_id"], {"device": "4"}
    )
    assert result["step_id"] == "platform"

    result = await hass.config_entries.subentries.async_configure(
        result["flow_id"], {"platform": "covers"}
    )
    assert result["step_id"] == "configure"

    result = await hass.config_entries.subentries.async_configure(result["flow_id"], {})
    await hass.async_block_till_done()

    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert device_subentry(entry, "covers", 4) is not None
    assert hass.states.get("cover.bedroom_blinds") is not None


async def test_subentry_remove_device(hass: HomeAssistant, mock_hub) -> None:
    """Removing a device subentry removes its entity from Home Assistant."""
    entry = make_config_entry()
    await setup_integration(hass, entry)
    assert hass.states.get("switch.garden_socket") is not None

    subentry = device_subentry(entry, "switches", 2)
    assert subentry is not None
    hass.config_entries.async_remove_subentry(entry, subentry.subentry_id)
    await hass.async_block_till_done()

    assert device_subentry(entry, "switches", 2) is None
    assert hass.states.get("switch.garden_socket") is None


async def test_options_menu_zones_mapping(hass: HomeAssistant, mock_hub) -> None:
    """The zone mapping can be edited from the options menu."""
    from tests_common import make_device

    from homeassistant.helpers import area_registry as ar
    from taphome_sdk import ValueType

    area = ar.async_get(hass).async_create("Zahrada")
    make_device(
        mock_hub,
        {
            "deviceId": 9,
            "type": "PowerOutlet",
            "name": "Pool Pump",
            "description": "Pump by the pool",
            "zone": "Garden",
            "supportedValues": [
                {"valueTypeId": ValueType.SWITCH_STATE.value, "readOnly": False}
            ],
            "values": {ValueType.SWITCH_STATE: 0.0},
        },
    )
    entry = make_config_entry()
    await setup_integration(hass, entry)

    result = await _start_options_flow(hass, entry)
    result = await hass.config_entries.options.async_configure(
        result["flow_id"], {"next_step_id": "zones"}
    )
    assert result["step_id"] == "zones"

    result = await hass.config_entries.options.async_configure(
        result["flow_id"], {"Garden": {"area": area.id}}
    )
    await hass.async_block_till_done()

    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert entry.options["zones"] == {"Garden": area.id}

    # Clearing the mapping removes the option again.
    result = await _start_options_flow(hass, entry)
    result = await hass.config_entries.options.async_configure(
        result["flow_id"], {"next_step_id": "zones"}
    )
    result = await hass.config_entries.options.async_configure(
        result["flow_id"], {"Garden": {}}
    )
    await hass.async_block_till_done()
    assert "zones" not in entry.options


async def test_subentry_reconfigure_field_kinds(
    hass: HomeAssistant, mock_hub
) -> None:
    """Reconfiguring a device converts every option field kind to its type."""
    entry = make_config_entry(
        {"climates": [{"id": 3}], "lights": [{"id": 1, "effect_id": 6}]}
    )
    await setup_integration(hass, entry)

    result = await _reconfigure(hass, entry, "climates", 3)

    # An invalid device id shows an error and keeps the form open.
    result = await hass.config_entries.subentries.async_configure(
        result["flow_id"], {"hvac_switch_id": "abc"}
    )
    assert result["step_id"] == "reconfigure"
    assert result["errors"] == {"base": "invalid_device_id"}

    result = await hass.config_entries.subentries.async_configure(
        result["flow_id"],
        {
            "hvac_switch_id": "2",
            "hvac_mode": "heat",
            "target_temperature_step": 0.5,
            "min_humidity": 30,
        },
    )
    await hass.async_block_till_done()
    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "reconfigure_successful"
    assert device_subentry_configs(entry, "climates") == [
        {
            "id": 3,
            "hvac_switch_id": 2,
            "hvac_mode": "heat",
            "target_temperature_step": 0.5,
            "min_humidity": 30,
        }
    ]

    # Clearing the effect_id removes it from the light subentry.
    result = await _reconfigure(hass, entry, "lights", 1)
    result = await hass.config_entries.subentries.async_configure(
        result["flow_id"], {"effect_id": ""}
    )
    await hass.async_block_till_done()
    assert device_subentry_configs(entry, "lights") == [{"id": 1}]


async def test_subentry_reconfigure_sensor_value_type(
    hass: HomeAssistant, mock_hub
) -> None:
    """Sensor overrides store the value type and free-text unit."""
    from taphome_sdk import ValueType

    entry = make_config_entry()
    await setup_integration(hass, entry)

    result = await _reconfigure(hass, entry, "sensors", 5)
    result = await hass.config_entries.subentries.async_configure(
        result["flow_id"],
        {
            "value_type": str(ValueType.VARIABLE_STATE.value),
            "unit_of_measurement": "°C",
            "device_class": "temperature",
        },
    )
    await hass.async_block_till_done()

    assert result["type"] is FlowResultType.ABORT
    assert device_subentry_configs(entry, "sensors") == [
        {
            "id": 5,
            "value_type": ValueType.VARIABLE_STATE.value,
            "unit_of_measurement": "°C",
            "device_class": "temperature",
        }
    ]


async def test_subentry_reconfigure_button_multi_enum(
    hass: HomeAssistant, mock_hub
) -> None:
    """Multi-select options render their stored values and save as lists."""
    from tests_common import make_device

    from taphome_sdk import ValueType

    make_device(
        mock_hub,
        {
            "deviceId": 8,
            "type": "WallButton",
            "name": "Hall Button",
            "description": "Button in the hall",
            "supportedValues": [
                {"valueTypeId": ValueType.BUTTON_PRESSED.value, "readOnly": True}
            ],
            "values": {ValueType.BUTTON_PRESSED: 0.0},
        },
    )
    entry = make_config_entry(
        {"buttons": [{"id": 8, "actions": ["press"], "device_class": "identify"}]}
    )
    await setup_integration(hass, entry)

    result = await _reconfigure(hass, entry, "buttons", 8)
    result = await hass.config_entries.subentries.async_configure(
        result["flow_id"], {"actions": ["press", "long_press"]}
    )
    await hass.async_block_till_done()

    assert result["type"] is FlowResultType.ABORT
    assert device_subentry_configs(entry, "buttons") == [
        {"id": 8, "actions": ["press", "long_press"]}
    ]


async def test_subentry_reconfigure_legacy_int_config(
    hass: HomeAssistant, mock_hub
) -> None:
    """A device stored as a bare id (YAML legacy) can still be reconfigured."""
    entry = make_config_entry({"switches": [2]})
    await setup_integration(hass, entry)

    result = await _reconfigure(hass, entry, "switches", 2)
    result = await hass.config_entries.subentries.async_configure(
        result["flow_id"], {"device_class": "outlet"}
    )
    await hass.async_block_till_done()

    assert result["type"] is FlowResultType.ABORT
    assert device_subentry_configs(entry, "switches") == [
        {"id": 2, "device_class": "outlet"}
    ]


async def test_options_core_settings_rejects_other_core(
    hass: HomeAssistant, mock_hub
) -> None:
    """Core settings refuse a connection that points to a different core."""
    from dataclasses import replace

    from tests_common import TEST_LOCATION, TEST_TOKEN

    entry = make_config_entry()
    await setup_integration(hass, entry)

    result = await _start_options_flow(hass, entry)
    result = await hass.config_entries.options.async_configure(
        result["flow_id"], {"next_step_id": "core_settings"}
    )

    mock_hub.mock_get_location.return_value = replace(
        TEST_LOCATION, location_id="other-location"
    )
    result = await hass.config_entries.options.async_configure(
        result["flow_id"], {CONF_TOKEN: TEST_TOKEN, CONF_IP: "10.0.0.5"}
    )
    assert result["type"] is FlowResultType.FORM
    assert result["errors"] == {"base": "unique_id_mismatch"}


async def test_options_mapping_renders_legacy_values(
    hass: HomeAssistant, mock_hub
) -> None:
    """Stored area/label names and unknown ids resolve when rendering."""
    from tests_common import make_device

    from homeassistant.helpers import area_registry as ar, label_registry as lr
    from taphome_sdk import ValueType

    ar.async_get(hass).async_create("Zahrada")
    make_device(
        mock_hub,
        {
            "deviceId": 9,
            "type": "PowerOutlet",
            "name": "Pool Pump",
            "description": "Pump by the pool",
            "zone": "Garden",
            "category": "Lights",
            "supportedValues": [
                {"valueTypeId": ValueType.SWITCH_STATE.value, "readOnly": False}
            ],
            "values": {ValueType.SWITCH_STATE: 0.0},
        },
    )
    label = lr.async_get(hass).async_create("Rolety")
    entry = make_config_entry(
        {
            "zones": {"Garden": "Zahrada"},
            "labels": {"Lights": "does-not-exist", "Curtains": label.label_id},
        }
    )
    await setup_integration(hass, entry)

    for step in ("zones", "labels"):
        result = await _start_options_flow(hass, entry)
        result = await hass.config_entries.options.async_configure(
            result["flow_id"], {"next_step_id": step}
        )
        assert result["step_id"] == step
