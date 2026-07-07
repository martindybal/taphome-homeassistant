"""Tests for the TapHome options flow (the Configure dialog)."""

from homeassistant.const import CONF_TOKEN, CONF_WEBHOOK_ID
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResultType

from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.taphome.const import CONF_IP
from tests_common import TEST_TOKEN, make_config_entry, setup_integration


async def _start_options_flow(hass: HomeAssistant, entry):
    result = await hass.config_entries.options.async_init(entry.entry_id)
    assert result["type"] is FlowResultType.MENU
    return result


def _device_ids(hass: HomeAssistant, *entity_ids: str) -> list[str]:
    """Resolve entity ids to the Home Assistant device ids edit/remove expect."""
    from homeassistant.helpers import entity_registry as er

    registry = er.async_get(hass)
    device_ids: list[str] = []
    for entity_id in entity_ids:
        entry = registry.async_get(entity_id)
        assert entry is not None and entry.device_id is not None
        device_ids.append(entry.device_id)
    return device_ids


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
        result["flow_id"], {"devices": _device_ids(hass, "switch.garden_socket")}
    )
    await hass.async_block_till_done()

    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert not entry.options.get("switches")
    assert hass.states.get("switch.garden_socket") is None


async def test_options_edit_skips_core_hub_device(
    hass: HomeAssistant, mock_hub
) -> None:
    """The Core hub device is offered by the selector but has no options."""
    from homeassistant.helpers import device_registry as dr

    from custom_components.taphome.const import DOMAIN
    from tests_common import TEST_LOCATION_ID

    entry = make_config_entry()
    await setup_integration(hass, entry)

    hub_device = dr.async_get(hass).async_get_device({(DOMAIN, TEST_LOCATION_ID)})
    assert hub_device is not None

    result = await _start_options_flow(hass, entry)
    result = await hass.config_entries.options.async_configure(
        result["flow_id"], {"next_step_id": "edit_devices"}
    )
    # Selecting only the hub (no configured entity) is treated as no selection.
    result = await hass.config_entries.options.async_configure(
        result["flow_id"], {"devices": [hub_device.id]}
    )
    assert result["errors"] == {"base": "no_devices_selected"}


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


async def test_options_edit_device_field_kinds(hass: HomeAssistant, mock_hub) -> None:
    """Editing devices converts every option field kind to its stored type."""
    entry = make_config_entry(
        {"climates": [{"id": 3}], "lights": [{"id": 1, "effect_id": 6}]}
    )
    await setup_integration(hass, entry)

    result = await _start_options_flow(hass, entry)
    result = await hass.config_entries.options.async_configure(
        result["flow_id"], {"next_step_id": "edit_devices"}
    )
    assert result["step_id"] == "edit_devices"

    # Empty and unknown selections are rejected before the form opens.
    result = await hass.config_entries.options.async_configure(
        result["flow_id"], {"devices": []}
    )
    assert result["errors"] == {"base": "no_devices_selected"}

    result = await hass.config_entries.options.async_configure(
        result["flow_id"],
        {
            "devices": _device_ids(
                hass, "climate.living_room_thermostat", "light.kitchen_light"
            )
        },
    )
    assert result["step_id"] == "edit_devices_form"

    # An invalid device id shows an error and keeps the form open.
    result = await hass.config_entries.options.async_configure(
        result["flow_id"],
        {
            "Living Room Thermostat (3) · climates": {"hvac_switch_id": "abc"},
            "Kitchen Light (1) · lights": {},
        },
    )
    assert result["errors"] == {"base": "invalid_device_id"}

    result = await hass.config_entries.options.async_configure(
        result["flow_id"],
        {
            "Living Room Thermostat (3) · climates": {
                "hvac_switch_id": "2",
                "hvac_mode": "heat",
                "target_temperature_step": 0.5,
                "min_humidity": 30,
            },
            "Kitchen Light (1) · lights": {"effect_id": ""},
        },
    )
    await hass.async_block_till_done()

    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert entry.options["climates"] == [
        {
            "id": 3,
            "hvac_switch_id": 2,
            "hvac_mode": "heat",
            "target_temperature_step": 0.5,
            "min_humidity": 30,
        }
    ]
    # The cleared effect_id was removed from the light.
    assert entry.options["lights"] == [{"id": 1}]


async def test_options_edit_sensor_value_type(hass: HomeAssistant, mock_hub) -> None:
    """Sensor overrides store the value type and free-text unit."""
    from taphome_sdk import ValueType

    entry = make_config_entry()
    await setup_integration(hass, entry)

    result = await _start_options_flow(hass, entry)
    result = await hass.config_entries.options.async_configure(
        result["flow_id"], {"next_step_id": "edit_devices"}
    )
    result = await hass.config_entries.options.async_configure(
        result["flow_id"], {"devices": _device_ids(hass, "sensor.outside_temperature")}
    )
    assert result["step_id"] == "edit_devices_form"

    result = await hass.config_entries.options.async_configure(
        result["flow_id"],
        {
            "Outside Temperature (5) · sensors": {
                "value_type": str(ValueType.VARIABLE_STATE.value),
                "unit_of_measurement": "°C",
                "device_class": "temperature",
            }
        },
    )
    await hass.async_block_till_done()

    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert entry.options["sensors"] == [
        {
            "id": 5,
            "value_type": ValueType.VARIABLE_STATE.value,
            "unit_of_measurement": "°C",
            "device_class": "temperature",
        }
    ]


async def test_options_edit_without_configured_devices_aborts(
    hass: HomeAssistant, mock_hub
) -> None:
    """Edit and remove abort when nothing is configured yet."""
    entry = make_config_entry()
    entry_no_devices = MockConfigEntry(
        domain=entry.domain,
        title=entry.title,
        unique_id="empty-location",
        data=dict(entry.data),
        options={},
    )
    await setup_integration(hass, entry_no_devices)

    for menu_item in ("edit_devices", "remove_devices"):
        result = await _start_options_flow(hass, entry_no_devices)
        result = await hass.config_entries.options.async_configure(
            result["flow_id"], {"next_step_id": menu_item}
        )
        assert result["type"] is FlowResultType.ABORT
        assert result["reason"] == "no_devices_configured"


async def test_options_remove_device_error_branches(
    hass: HomeAssistant, mock_hub
) -> None:
    """Empty and unknown removal selections are rejected."""
    entry = make_config_entry()
    await setup_integration(hass, entry)

    result = await _start_options_flow(hass, entry)
    result = await hass.config_entries.options.async_configure(
        result["flow_id"], {"next_step_id": "remove_devices"}
    )
    result = await hass.config_entries.options.async_configure(
        result["flow_id"], {"devices": []}
    )
    assert result["errors"] == {"base": "no_devices_selected"}


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


async def test_options_edit_button_multi_enum(hass: HomeAssistant, mock_hub) -> None:
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

    result = await _start_options_flow(hass, entry)
    result = await hass.config_entries.options.async_configure(
        result["flow_id"], {"next_step_id": "edit_devices"}
    )
    result = await hass.config_entries.options.async_configure(
        result["flow_id"], {"devices": _device_ids(hass, "button.hall_button")}
    )
    assert result["step_id"] == "edit_devices_form"

    result = await hass.config_entries.options.async_configure(
        result["flow_id"],
        {"Hall Button (8) · buttons": {"actions": ["press", "long_press"]}},
    )
    await hass.async_block_till_done()

    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert entry.options["buttons"] == [
        {"id": 8, "actions": ["press", "long_press"]}
    ]


async def test_options_device_labels_show_mapped_area(
    hass: HomeAssistant, mock_hub
) -> None:
    """Configured devices show their mapped area in the device labels."""
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
    entry = make_config_entry(
        {"switches": [{"id": 2}, {"id": 9}], "zones": {"Garden": area.id}}
    )
    await setup_integration(hass, entry)

    result = await _start_options_flow(hass, entry)
    result = await hass.config_entries.options.async_configure(
        result["flow_id"], {"next_step_id": "edit_devices"}
    )
    result = await hass.config_entries.options.async_configure(
        result["flow_id"], {"devices": _device_ids(hass, "switch.pool_pump")}
    )
    assert result["step_id"] == "edit_devices_form"

    # The section key resolves the zone through the mapping to the area name.
    result = await hass.config_entries.options.async_configure(
        result["flow_id"], {"Pool Pump (9) — Zahrada · switches": {}}
    )
    await hass.async_block_till_done()
    assert result["type"] is FlowResultType.CREATE_ENTRY


async def test_options_edit_legacy_int_config(hass: HomeAssistant, mock_hub) -> None:
    """Device configs stored as bare ids (YAML legacy) can still be edited."""
    entry = make_config_entry({"switches": [2]})
    await setup_integration(hass, entry)

    result = await _start_options_flow(hass, entry)
    result = await hass.config_entries.options.async_configure(
        result["flow_id"], {"next_step_id": "edit_devices"}
    )
    result = await hass.config_entries.options.async_configure(
        result["flow_id"], {"devices": _device_ids(hass, "switch.garden_socket")}
    )
    assert result["step_id"] == "edit_devices_form"

    result = await hass.config_entries.options.async_configure(
        result["flow_id"], {"Garden Socket (2) · switches": {"device_class": "outlet"}}
    )
    await hass.async_block_till_done()

    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert entry.options["switches"] == [{"id": 2, "device_class": "outlet"}]


async def test_options_edit_skips_unmatchable_registry_entries(
    hass: HomeAssistant, mock_hub
) -> None:
    """Registry entries that do not map to a configured device are skipped."""
    from homeassistant.helpers import entity_registry as er

    entry = make_config_entry()
    await setup_integration(hass, entry)

    registry = er.async_get(hass)
    # A domain the integration has no configuration list for.
    registry.async_get_or_create("lock", "taphome", "lock-unique", config_entry=entry)
    # A unique id that does not encode a TapHome device id.
    registry.async_get_or_create("light", "taphome", "custom-unique", config_entry=entry)
    # A parseable device id that is not in the configured options.
    registry.async_get_or_create(
        "light", "taphome", "taphome.light.77", config_entry=entry
    )

    result = await _start_options_flow(hass, entry)
    result = await hass.config_entries.options.async_configure(
        result["flow_id"], {"next_step_id": "edit_devices"}
    )
    assert result["step_id"] == "edit_devices"


async def test_options_mapping_renders_legacy_values(
    hass: HomeAssistant, mock_hub
) -> None:
    """Stored area/label names and unknown ids resolve when rendering."""
    from tests_common import make_device

    from homeassistant.helpers import area_registry as ar
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
    from homeassistant.helpers import label_registry as lr

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


async def test_options_device_label_without_mapping_shows_zone(
    hass: HomeAssistant, mock_hub
) -> None:
    """Without a zone mapping the raw TapHome zone appears in device labels."""
    from tests_common import make_device

    from taphome_sdk import ValueType

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
    entry = make_config_entry({"switches": [{"id": 2}, {"id": 9}]})
    await setup_integration(hass, entry)

    result = await _start_options_flow(hass, entry)
    result = await hass.config_entries.options.async_configure(
        result["flow_id"], {"next_step_id": "edit_devices"}
    )
    result = await hass.config_entries.options.async_configure(
        result["flow_id"], {"devices": _device_ids(hass, "switch.pool_pump")}
    )
    result = await hass.config_entries.options.async_configure(
        result["flow_id"], {"Pool Pump (9) — Garden · switches": {}}
    )
    await hass.async_block_till_done()
    assert result["type"] is FlowResultType.CREATE_ENTRY


async def test_options_edit_renders_stored_values(
    hass: HomeAssistant, mock_hub
) -> None:
    """Stored option values of every kind are suggested when editing."""
    from taphome_sdk import ValueType

    entry = make_config_entry(
        {
            "climates": [{"id": 3, "target_temperature_step": 0.5}],
            "sensors": [{"id": 5, "value_type": ValueType.VARIABLE_STATE.value}],
        }
    )
    await setup_integration(hass, entry)

    result = await _start_options_flow(hass, entry)
    result = await hass.config_entries.options.async_configure(
        result["flow_id"], {"next_step_id": "edit_devices"}
    )
    result = await hass.config_entries.options.async_configure(
        result["flow_id"],
        {
            "devices": _device_ids(
                hass, "climate.living_room_thermostat", "sensor.outside_temperature"
            )
        },
    )
    assert result["step_id"] == "edit_devices_form"
