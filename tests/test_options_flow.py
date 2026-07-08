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


async def test_options_menu_device_management(
    hass: HomeAssistant, mock_hub
) -> None:
    """The menu offers add/edit/remove; the old bulk picker is gone."""
    entry = make_config_entry()
    await setup_integration(hass, entry)

    result = await _start_options_flow(hass, entry)
    assert "add_devices" not in result["menu_options"]
    assert "add_device" in result["menu_options"]
    assert "edit_device" in result["menu_options"]
    assert "remove_device" in result["menu_options"]


async def test_options_add_device_archetype_flow(
    hass: HomeAssistant, mock_hub
) -> None:
    """Configure → Add device opens the same archetype flow as Add device."""
    entry = make_config_entry()
    await setup_integration(hass, entry)

    result = await _start_options_flow(hass, entry)
    result = await hass.config_entries.options.async_configure(
        result["flow_id"], {"next_step_id": "add_device"}
    )
    assert result["type"] is FlowResultType.MENU
    assert result["step_id"] == "add_device"

    result = await hass.config_entries.options.async_configure(
        result["flow_id"], {"next_step_id": "cover"}
    )
    assert result["step_id"] == "cover"

    result = await hass.config_entries.options.async_configure(
        result["flow_id"], {"device": "4"}
    )
    await hass.async_block_till_done()

    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "device_added"
    assert device_subentry(entry, "covers", 4) is not None
    assert hass.states.get("cover.bedroom_blinds") is not None


async def _start_subentry_menu(hass: HomeAssistant, entry, archetype: str):
    """Open the add-device menu and pick one archetype."""
    result = await hass.config_entries.subentries.async_init(
        (entry.entry_id, "device"), context={"source": SOURCE_USER}
    )
    assert result["type"] is FlowResultType.MENU
    assert result["step_id"] == "user"
    result = await hass.config_entries.subentries.async_configure(
        result["flow_id"], {"next_step_id": archetype}
    )
    assert result["step_id"] == archetype
    return result


async def test_subentry_add_single_device(hass: HomeAssistant, mock_hub) -> None:
    """The archetype flow adds one device: menu → type form → subentry."""
    entry = make_config_entry()
    await setup_integration(hass, entry)

    # Bedroom Blinds (4) is not configured yet and qualifies as a cover.
    result = await _start_subentry_menu(hass, entry, "cover")
    result = await hass.config_entries.subentries.async_configure(
        result["flow_id"], {"device": "4"}
    )
    await hass.async_block_till_done()

    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert device_subentry(entry, "covers", 4) is not None
    assert hass.states.get("cover.bedroom_blinds") is not None


async def test_subentry_add_thermostat_variants(
    hass: HomeAssistant, mock_hub
) -> None:
    """Each thermostat archetype stores exactly its fields."""
    entry = make_config_entry()
    await setup_integration(hass, entry)

    # Controlled thermostat: mode without a switch is rejected, then a valid
    # switch + fixed mode combination is stored.
    result = await _start_subentry_menu(hass, entry, "thermostat_controlled")
    result = await hass.config_entries.subentries.async_configure(
        result["flow_id"], {"device": "3", "hvac_mode": "heat"}
    )
    assert result["errors"] == {"base": "invalid_hvac_config"}

    result = await hass.config_entries.subentries.async_configure(
        result["flow_id"],
        {"device": "3", "hvac_switch_id": "2", "hvac_mode": "heat"},
    )
    await hass.async_block_till_done()
    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert device_subentry_configs(entry, "climates") == [
        {"id": 3, "hvac_switch_id": 2, "hvac_mode": "heat"}
    ]


async def test_subentry_add_range_thermostat(hass: HomeAssistant, mock_hub) -> None:
    """The range thermostat requires both thermostats; high becomes the id."""
    from taphome_sdk import ValueType

    from tests_common import make_device

    make_device(
        mock_hub,
        {
            "deviceId": 7,
            "type": "Thermostat",
            "name": "Low Thermostat",
            "description": "Cooling thermostat",
            "supportedValues": [
                {"valueTypeId": ValueType.REAL_TEMPERATURE.value, "readOnly": True},
                {
                    "valueTypeId": ValueType.TEMPERATURE_SET_POINT.value,
                    "readOnly": False,
                },
            ],
            "values": {
                ValueType.REAL_TEMPERATURE: 21.0,
                ValueType.TEMPERATURE_SET_POINT: 24.0,
            },
        },
    )
    entry = make_config_entry()
    await setup_integration(hass, entry)

    result = await _start_subentry_menu(hass, entry, "thermostat_range")
    result = await hass.config_entries.subentries.async_configure(
        result["flow_id"], {"range_high_thermostat_id": "3"}
    )
    assert result["errors"] == {"base": "range_thermostats_required"}

    result = await hass.config_entries.subentries.async_configure(
        result["flow_id"],
        {"range_high_thermostat_id": "3", "range_low_thermostat_id": "7"},
    )
    await hass.async_block_till_done()
    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert device_subentry_configs(entry, "climates") == [
        {"id": 3, "range_high_thermostat_id": 3, "range_low_thermostat_id": 7}
    ]


async def test_subentry_add_sensor_values(hass: HomeAssistant, mock_hub) -> None:
    """The sensor flow creates one subentry and entity per selected value."""
    from taphome_sdk import ValueType

    from tests_common import make_device

    make_device(
        mock_hub,
        {
            "deviceId": 9,
            "type": "THSensor",
            "name": "Climate Sensor",
            "description": "Temperature and humidity",
            "supportedValues": [
                {"valueTypeId": ValueType.REAL_TEMPERATURE.value, "readOnly": True},
                {"valueTypeId": ValueType.HUMIDITY.value, "readOnly": True},
            ],
            "values": {
                ValueType.REAL_TEMPERATURE: 21.5,
                ValueType.HUMIDITY: 0.45,
            },
        },
    )
    entry = make_config_entry()
    await setup_integration(hass, entry)

    result = await _start_subentry_menu(hass, entry, "sensor")
    result = await hass.config_entries.subentries.async_configure(
        result["flow_id"], {"device": "9"}
    )
    assert result["step_id"] == "sensor_values"

    result = await hass.config_entries.subentries.async_configure(
        result["flow_id"],
        {
            "values": [
                str(ValueType.REAL_TEMPERATURE.value),
                str(ValueType.HUMIDITY.value),
            ]
        },
    )
    await hass.async_block_till_done()

    assert result["type"] is FlowResultType.CREATE_ENTRY
    configs = device_subentry_configs(entry, "sensors")
    assert {"id": 9, "value": ValueType.REAL_TEMPERATURE.value} in configs
    assert {"id": 9, "value": ValueType.HUMIDITY.value} in configs

    # Each value became its own entity of the same device.
    from homeassistant.helpers import entity_registry as er

    from custom_components.taphome.const import DOMAIN

    registry = er.async_get(hass)
    temperature_entity = registry.async_get_entity_id(
        "sensor", DOMAIN, "taphome.sensor.realtemperature.9"
    )
    humidity_entity = registry.async_get_entity_id(
        "sensor", DOMAIN, "taphome.sensor.humidity.9"
    )
    assert temperature_entity is not None
    assert humidity_entity is not None
    assert hass.states.get(temperature_entity) is not None
    assert hass.states.get(humidity_entity) is not None

    # Removing one value's subentry keeps the other value's entity.
    temperature = next(
        subentry
        for subentry in entry.subentries.values()
        if subentry.data.get("value") == ValueType.REAL_TEMPERATURE.value
    )
    hass.config_entries.async_remove_subentry(entry, temperature.subentry_id)
    await hass.async_block_till_done()
    assert hass.states.get(temperature_entity) is None
    assert hass.states.get(humidity_entity) is not None


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

    # An invalid device id (in the advanced section) keeps the form open.
    result = await hass.config_entries.subentries.async_configure(
        result["flow_id"], {"advanced_options": {"hvac_switch_id": "abc"}}
    )
    assert result["step_id"] == "reconfigure"
    assert result["errors"] == {"base": "invalid_device_id"}

    # A simple thermostat is upgraded to a controlled one via the advanced
    # section, together with a basic field.
    result = await hass.config_entries.subentries.async_configure(
        result["flow_id"],
        {
            "target_temperature_step": 0.5,
            "advanced_options": {
                "hvac_switch_id": "2",
                "hvac_mode": "heat",
                "min_humidity": 30,
            },
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
            "unit_of_measurement": "°C",
            "device_class": "temperature",
            "advanced_options": {
                "value_type": str(ValueType.VARIABLE_STATE.value),
            },
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


async def test_options_edit_device_via_entity(hass: HomeAssistant, mock_hub) -> None:
    """Edit device resolves an entity pick straight to its subentry form."""
    entry = make_config_entry()
    await setup_integration(hass, entry)

    result = await _start_options_flow(hass, entry)
    result = await hass.config_entries.options.async_configure(
        result["flow_id"], {"next_step_id": "edit_device"}
    )
    assert result["step_id"] == "edit_device"

    # Submitting an empty target is rejected.
    result = await hass.config_entries.options.async_configure(
        result["flow_id"], {"target": {}}
    )
    assert result["errors"] == {"base": "select_target"}

    result = await hass.config_entries.options.async_configure(
        result["flow_id"], {"target": {"entity_id": "switch.garden_socket"}}
    )
    assert result["step_id"] == "edit_device_form"

    result = await hass.config_entries.options.async_configure(
        result["flow_id"], {"device_class": "outlet"}
    )
    await hass.async_block_till_done()

    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "reconfigure_successful"
    assert device_subentry_configs(entry, "switches") == [
        {"id": 2, "device_class": "outlet"}
    ]


async def test_options_edit_device_via_device_pick(
    hass: HomeAssistant, mock_hub
) -> None:
    """A device exposed twice offers a configuration pick before the form."""
    from homeassistant.helpers import entity_registry as er

    entry = make_config_entry({"lights": [{"id": 1}], "switches": [{"id": 1}]})
    await setup_integration(hass, entry)

    registry = er.async_get(hass)
    light = registry.async_get("light.kitchen_light")
    assert light is not None and light.device_id is not None

    result = await _start_options_flow(hass, entry)
    result = await hass.config_entries.options.async_configure(
        result["flow_id"], {"next_step_id": "edit_device"}
    )
    result = await hass.config_entries.options.async_configure(
        result["flow_id"], {"target": {"device_id": light.device_id}}
    )
    assert result["step_id"] == "edit_device_pick"

    switches = device_subentry(entry, "switches", 1)
    result = await hass.config_entries.options.async_configure(
        result["flow_id"], {"config": switches.subentry_id}
    )
    assert result["step_id"] == "edit_device_form"

    result = await hass.config_entries.options.async_configure(
        result["flow_id"], {"device_class": "outlet"}
    )
    await hass.async_block_till_done()
    assert result["type"] is FlowResultType.ABORT
    assert device_subentry_configs(entry, "switches") == [
        {"id": 1, "device_class": "outlet"}
    ]


async def test_options_remove_device_via_entity(
    hass: HomeAssistant, mock_hub
) -> None:
    """Remove device shows a summary and removes the subentry and entity."""
    entry = make_config_entry()
    await setup_integration(hass, entry)
    assert hass.states.get("switch.garden_socket") is not None

    result = await _start_options_flow(hass, entry)
    result = await hass.config_entries.options.async_configure(
        result["flow_id"], {"next_step_id": "remove_device"}
    )
    result = await hass.config_entries.options.async_configure(
        result["flow_id"], {"target": {"entity_id": "switch.garden_socket"}}
    )
    assert result["step_id"] == "remove_device_confirm"

    # All resolved devices are pre-selected; submitting removes them.
    result = await hass.config_entries.options.async_configure(
        result["flow_id"], {"devices": ["2"]}
    )
    await hass.async_block_till_done()

    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "device_removed"
    assert device_subentry(entry, "switches", 2) is None
    assert hass.states.get("switch.garden_socket") is None


async def test_options_edit_device_rejects_hub_device(
    hass: HomeAssistant, mock_hub
) -> None:
    """The Core hub device has no device configuration to edit."""
    from homeassistant.helpers import device_registry as dr

    from custom_components.taphome.const import DOMAIN
    from tests_common import TEST_LOCATION_ID

    entry = make_config_entry()
    await setup_integration(hass, entry)

    hub_device = dr.async_get(hass).async_get_device({(DOMAIN, TEST_LOCATION_ID)})
    assert hub_device is not None

    result = await _start_options_flow(hass, entry)
    result = await hass.config_entries.options.async_configure(
        result["flow_id"], {"next_step_id": "edit_device"}
    )
    result = await hass.config_entries.options.async_configure(
        result["flow_id"], {"target": {"device_id": hub_device.id}}
    )
    assert result["errors"] == {"base": "no_device_config"}


async def test_options_remove_device_via_area(hass: HomeAssistant, mock_hub) -> None:
    """An area target fans out to this entry's devices in that area."""
    from homeassistant.helpers import area_registry as ar, device_registry as dr

    from custom_components.taphome.const import DOMAIN
    from tests_common import TEST_LOCATION_ID

    entry = make_config_entry()
    await setup_integration(hass, entry)

    area = ar.async_get(hass).async_create("Zahrada")
    device_registry = dr.async_get(hass)
    socket = device_registry.async_get_device({(DOMAIN, f"{TEST_LOCATION_ID}_2")})
    device_registry.async_update_device(socket.id, area_id=area.id)

    result = await _start_options_flow(hass, entry)
    result = await hass.config_entries.options.async_configure(
        result["flow_id"], {"next_step_id": "remove_device"}
    )
    result = await hass.config_entries.options.async_configure(
        result["flow_id"], {"target": {"area_id": area.id}}
    )
    assert result["step_id"] == "remove_device_confirm"

    # Submitting without input keeps the default: every resolved device.
    result = await hass.config_entries.options.async_configure(result["flow_id"], {})
    await hass.async_block_till_done()

    assert result["reason"] == "device_removed"
    assert device_subentry(entry, "switches", 2) is None
    assert hass.states.get("switch.garden_socket") is None


async def test_options_remove_device_via_suggested_area(
    hass: HomeAssistant, mock_hub
) -> None:
    """An area from the TapHome zone resolves; unticked devices are kept."""
    from homeassistant.helpers import area_registry as ar, device_registry as dr
    from taphome_sdk import ValueType

    from custom_components.taphome.const import DOMAIN
    from tests_common import TEST_LOCATION_ID, make_device

    make_device(
        mock_hub,
        {
            "deviceId": 9,
            "type": "PowerOutlet",
            "name": "Pool Pump",
            "description": "Pump by the pool",
            "zone": "Pracovna",
            "supportedValues": [
                {"valueTypeId": ValueType.SWITCH_STATE.value, "readOnly": False}
            ],
            "values": {ValueType.SWITCH_STATE: 0.0},
        },
    )
    entry = make_config_entry({"switches": [{"id": 2}, {"id": 9}]})
    await setup_integration(hass, entry)

    # The zone became an area via suggested_area during device creation; move
    # the Garden Socket into the same area to get a two-device review list.
    area = ar.async_get(hass).async_get_area_by_name("Pracovna")
    assert area is not None
    device_registry = dr.async_get(hass)
    socket = device_registry.async_get_device({(DOMAIN, f"{TEST_LOCATION_ID}_2")})
    device_registry.async_update_device(socket.id, area_id=area.id)

    result = await _start_options_flow(hass, entry)
    result = await hass.config_entries.options.async_configure(
        result["flow_id"], {"next_step_id": "remove_device"}
    )
    result = await hass.config_entries.options.async_configure(
        result["flow_id"], {"target": {"area_id": area.id}}
    )
    assert result["step_id"] == "remove_device_confirm"

    # Unticking the Garden Socket keeps it; only the Pool Pump is removed.
    result = await hass.config_entries.options.async_configure(
        result["flow_id"], {"devices": ["9"]}
    )
    await hass.async_block_till_done()
    assert result["reason"] == "device_removed"
    assert device_subentry(entry, "switches", 9) is None
    assert device_subentry(entry, "switches", 2) is not None
    assert hass.states.get("switch.garden_socket") is not None
