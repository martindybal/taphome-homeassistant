"""Tests for the TapHome config entry setup and unload."""

import logging
from unittest.mock import AsyncMock, patch

from pytest_homeassistant_custom_component.common import MockConfigEntry
from taphome_sdk import (
    HubConnectionState,
    TapHomeAuthError,
    TapHomeConnectionError,
    TapHomeHubFactory,
    ValueType,
)

from custom_components.taphome.const import CONF_KNOWN_DEVICE_IDS, DOMAIN
from homeassistant.config_entries import ConfigEntryState
from homeassistant.const import (
    CONF_WEBHOOK_ID,
    STATE_OFF,
    STATE_ON,
    STATE_UNAVAILABLE,
)
from homeassistant.core import HomeAssistant

from tests_common import make_config_entry, setup_integration


async def test_subentry_title_follows_taphome(
    hass: HomeAssistant, mock_hub
) -> None:
    """The subentry title follows the TapHome device, unless the user renames."""
    from tests_common import device_subentry

    entry = make_config_entry()
    await setup_integration(hass, entry)
    # Title format: id, description, zone, category.
    assert device_subentry(entry, "switches", 2).title == "2, Socket by the terrace"

    # Changing the device in TapHome updates the title on the next reload.
    mock_hub.devices[2].description = "Terrace socket"
    await hass.config_entries.async_reload(entry.entry_id)
    await hass.async_block_till_done()
    assert device_subentry(entry, "switches", 2).title == "2, Terrace socket"

    # Once the user renames the subentry, TapHome changes no longer override it.
    hass.config_entries.async_update_subentry(
        entry, device_subentry(entry, "switches", 2), title="My Socket"
    )
    await hass.async_block_till_done()
    mock_hub.devices[2].description = "Something else"
    await hass.config_entries.async_reload(entry.entry_id)
    await hass.async_block_till_done()
    assert device_subentry(entry, "switches", 2).title == "My Socket"


async def test_setup_and_unload_entry(
    hass: HomeAssistant, mock_hub, mock_config_entry: MockConfigEntry
) -> None:
    """A config entry sets up its platforms and unloads cleanly."""
    await setup_integration(hass, mock_config_entry)

    assert mock_config_entry.state is ConfigEntryState.LOADED
    assert hass.states.get("light.kitchen_light") is not None
    assert hass.states.get("switch.garden_socket") is not None
    assert hass.states.get("sensor.outside_temperature") is not None

    assert await hass.config_entries.async_unload(mock_config_entry.entry_id)
    await hass.async_block_till_done()

    assert mock_config_entry.state is ConfigEntryState.NOT_LOADED


async def test_setup_entry_connection_error_retries(
    hass: HomeAssistant, mock_config_entry: MockConfigEntry
) -> None:
    """An unreachable core puts the entry into retry state."""
    with patch.object(
        TapHomeHubFactory,
        "async_connect",
        AsyncMock(side_effect=TapHomeConnectionError("boom")),
    ):
        mock_config_entry.add_to_hass(hass)
        await hass.config_entries.async_setup(mock_config_entry.entry_id)
        await hass.async_block_till_done()

    assert mock_config_entry.state is ConfigEntryState.SETUP_RETRY


async def test_setup_entry_auth_error_starts_reauth(
    hass: HomeAssistant, mock_config_entry: MockConfigEntry
) -> None:
    """A rejected token fails setup and starts the reauth flow."""
    with patch.object(
        TapHomeHubFactory,
        "async_connect",
        AsyncMock(side_effect=TapHomeAuthError(401)),
    ):
        mock_config_entry.add_to_hass(hass)
        await hass.config_entries.async_setup(mock_config_entry.entry_id)
        await hass.async_block_till_done()

    assert mock_config_entry.state is ConfigEntryState.SETUP_ERROR
    assert any(
        flow["context"]["source"] == "reauth"
        for flow in hass.config_entries.flow.async_progress()
    )


async def test_webhook_updates_device_state(
    hass: HomeAssistant,
    hass_client_no_auth,
    mock_hub,
    mock_config_entry: MockConfigEntry,
) -> None:
    """A webhook call pushes new device values into the entities."""
    mock_config_entry = make_config_entry({CONF_WEBHOOK_ID: "taphome-test"})
    await setup_integration(hass, mock_config_entry)
    assert hass.states.get("switch.garden_socket").state == STATE_OFF

    client = await hass_client_no_auth()
    response = await client.post(
        "/api/webhook/taphome-test",
        json={
            "devices": [
                {
                    "deviceId": 2,
                    "values": [
                        {"valueTypeId": ValueType.SWITCH_STATE.value, "value": 1}
                    ],
                }
            ],
            "timestamp": 2,
        },
    )
    await hass.async_block_till_done()

    assert response.status == 200
    assert hass.states.get("switch.garden_socket").state == STATE_ON

    # A malformed body is ignored without breaking the webhook.
    response = await client.post("/api/webhook/taphome-test", data=b"not json")
    await hass.async_block_till_done()
    assert response.status == 200
    assert hass.states.get("switch.garden_socket").state == STATE_ON


async def test_new_core_embeds_location_id_in_unique_ids(
    hass: HomeAssistant, mock_hub
) -> None:
    """A core added now discriminates its entity unique ids by location id."""
    from custom_components.taphome.const import CONF_CORE_UNIQUE_ID
    from homeassistant.helpers import entity_registry as er

    from tests_common import TEST_LOCATION_ID

    entry = make_config_entry()
    entry.add_to_hass(hass)
    hass.config_entries.async_update_entry(
        entry, data={**entry.data, CONF_CORE_UNIQUE_ID: TEST_LOCATION_ID}
    )
    await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()

    registry = er.async_get(hass)
    switch = registry.async_get("switch.garden_socket")
    assert switch.unique_id == f"taphome.{TEST_LOCATION_ID}.switch.2".lower()
    # The core connectivity sensor is per-core too.
    assert registry.async_get_entity_id(
        "binary_sensor",
        DOMAIN,
        f"taphome.{TEST_LOCATION_ID}.binary_sensor.isalive".lower(),
    ) is not None


async def test_existing_core_keeps_undiscriminated_unique_ids(
    hass: HomeAssistant, mock_config_entry: MockConfigEntry, mock_hub
) -> None:
    """An entry without the location marker keeps its original unique ids."""
    from homeassistant.helpers import entity_registry as er

    await setup_integration(hass, mock_config_entry)

    registry = er.async_get(hass)
    switch = registry.async_get("switch.garden_socket")
    assert switch.unique_id == "taphome.switch.2"
    assert registry.async_get_entity_id(
        "binary_sensor", DOMAIN, "taphome.binary_sensor.isalive"
    ) is not None


async def test_first_setup_records_known_devices(
    hass: HomeAssistant, mock_hub, mock_config_entry: MockConfigEntry
) -> None:
    """The first setup stores the exposed devices as the known baseline."""
    await setup_integration(hass, mock_config_entry)

    assert sorted(mock_config_entry.data[CONF_KNOWN_DEVICE_IDS]) == [1, 2, 3, 4, 5, 6]


async def test_new_device_creates_repair_issue(
    hass: HomeAssistant, mock_hub, mock_config_entry: MockConfigEntry
) -> None:
    """A newly exposed device raises a repair issue after a reload."""
    from taphome_sdk.device_factory import DeviceFactory
    from taphome_sdk.taphome_api import DeviceMetadata

    from homeassistant.helpers import issue_registry as ir

    await setup_integration(hass, mock_config_entry)

    metadata = DeviceMetadata.from_dict(
        {
            "deviceId": 9,
            "type": "PowerOutlet",
            "name": "New Socket",
            "description": "Fresh from the app",
            "supportedValues": [
                {"valueTypeId": ValueType.SWITCH_STATE.value, "readOnly": False}
            ],
        }
    )
    device = DeviceFactory.create_device(
        mock_hub.api,
        mock_hub.connection_type,
        metadata,
        {ValueType.SWITCH_STATE: 0.0},
    )
    mock_hub.devices[9] = device

    await hass.config_entries.async_reload(mock_config_entry.entry_id)
    await hass.async_block_till_done()

    issue_registry = ir.async_get(hass)
    assert any(
        issue.domain == DOMAIN and "new_device" in issue.issue_id
        for issue in issue_registry.issues.values()
    )


async def test_connection_loss_logs_once_and_recovers(
    hass: HomeAssistant, mock_hub, mock_config_entry: MockConfigEntry, caplog
) -> None:
    """Losing the Core logs once, marks entities unavailable and recovers."""
    await setup_integration(hass, mock_config_entry)
    caplog.set_level(logging.INFO)
    caplog.clear()

    mock_hub.connection_state.value = HubConnectionState.FAILED
    await hass.async_block_till_done()

    assert hass.states.get("switch.garden_socket").state == STATE_UNAVAILABLE
    lost_logs = [record for record in caplog.records if "lost" in record.message]
    assert len(lost_logs) == 1
    assert lost_logs[0].levelno == logging.INFO

    mock_hub.connection_state.value = HubConnectionState.CONNECTED
    await hass.async_block_till_done()

    assert hass.states.get("switch.garden_socket").state != STATE_UNAVAILABLE
    recovered = [
        record for record in caplog.records if "re-established" in record.message
    ]
    assert len(recovered) == 1


async def test_runtime_auth_error_starts_reauth(
    hass: HomeAssistant, mock_hub, mock_config_entry: MockConfigEntry
) -> None:
    """A token rejected while running starts the reauth flow."""
    await setup_integration(hass, mock_config_entry)

    mock_hub.connection_state.value = HubConnectionState.AUTH_FAILED
    await hass.async_block_till_done()

    assert any(
        flow["context"]["source"] == "reauth"
        for flow in hass.config_entries.flow.async_progress()
    )


def _expose_device(mock_hub, device_id: int) -> None:
    """Expose a new device in the fake API (discovery + values)."""
    mock_hub.api.discovery_definitions.append(
        {
            "deviceId": device_id,
            "type": "PowerOutlet",
            "name": "New Socket",
            "description": "Exposed while running",
            "supportedValues": [
                {"valueTypeId": ValueType.SWITCH_STATE.value, "readOnly": False}
            ],
        }
    )
    mock_hub.api.values[device_id] = {ValueType.SWITCH_STATE: 0.0}


async def _push_webhook(mock_hub, device_id: int, value: int) -> None:
    """Deliver a webhook payload carrying one device's value."""
    await mock_hub.async_handle_webhook(
        {
            "devices": [
                {
                    "deviceId": device_id,
                    "values": [
                        {"valueTypeId": ValueType.SWITCH_STATE.value, "value": value}
                    ],
                }
            ],
            "timestamp": 2,
        }
    )


async def test_new_device_reported_when_its_values_arrive(
    hass: HomeAssistant, mock_hub, mock_config_entry: MockConfigEntry
) -> None:
    """A device exposed after setup is reported the moment its values arrive."""
    from homeassistant.helpers import issue_registry as ir

    await setup_integration(hass, mock_config_entry)
    issue_registry = ir.async_get(hass)

    _expose_device(mock_hub, 42)
    # An incoming value (here a webhook) for an unregistered device is the
    # signal: the hub resolves its metadata on demand and it is reported.
    await _push_webhook(mock_hub, 42, 1)
    await hass.async_block_till_done()

    assert 42 in mock_hub.devices
    assert any(
        issue.domain == DOMAIN and issue.issue_id.endswith("_42")
        for issue in issue_registry.issues.values()
    )
    # The resolved device is dropped from the pending set, so no re-fire loop.
    assert mock_hub.new_device_ids.value == frozenset()


async def test_known_device_value_does_not_trigger_detection(
    hass: HomeAssistant, mock_hub, mock_config_entry: MockConfigEntry
) -> None:
    """Values for already known devices raise no new-device issue."""
    from homeassistant.helpers import issue_registry as ir

    await setup_integration(hass, mock_config_entry)

    await _push_webhook(mock_hub, 2, 1)
    await hass.async_block_till_done()

    issue_registry = ir.async_get(hass)
    assert not any(
        issue.domain == DOMAIN and "new_device" in issue.issue_id
        for issue in issue_registry.issues.values()
    )
    assert mock_hub.new_device_ids.value == frozenset()


async def test_unconfigurable_devices_raise_issues(
    hass: HomeAssistant, mock_hub
) -> None:
    """Missing and mistyped devices raise issues instead of breaking setup."""
    from homeassistant.helpers import issue_registry as ir

    # Device 99 is not exposed at all; device 2 is a socket, not a thermostat.
    entry = make_config_entry({"climates": [{"id": 2}], "switches": [{"id": 99}]})
    await setup_integration(hass, entry)

    assert entry.state is ConfigEntryState.LOADED
    issue_registry = ir.async_get(hass)
    issue_ids = {
        issue.issue_id
        for issue in issue_registry.issues.values()
        if issue.domain == DOMAIN
    }
    assert any("device_not_exposed" in issue_id for issue_id in issue_ids)
    assert any("device_type_mismatch" in issue_id for issue_id in issue_ids)


async def test_devices_are_registered(
    hass: HomeAssistant, mock_hub, mock_config_entry: MockConfigEntry
) -> None:
    """The Core and every TapHome device appear in the device registry."""
    from homeassistant.helpers import device_registry as dr

    from tests_common import TEST_LOCATION_ID, TEST_LOCATION_NAME

    await setup_integration(hass, mock_config_entry)

    device_registry = dr.async_get(hass)
    hub_device = device_registry.async_get_device({(DOMAIN, TEST_LOCATION_ID)})
    assert hub_device is not None
    assert hub_device.manufacturer == "TapHome"
    assert hub_device.model == "Core"
    assert hub_device.name == TEST_LOCATION_NAME

    socket = device_registry.async_get_device({(DOMAIN, f"{TEST_LOCATION_ID}_2")})
    assert socket is not None
    assert socket.name == "Garden Socket"
    assert socket.manufacturer == "TapHome"
    assert socket.via_device_id == hub_device.id
    # The hub device links to the Core's local log page (local API connection).
    assert hub_device.configuration_url == "http://10.0.0.5/localapilog"


async def test_remove_config_entry_device(
    hass: HomeAssistant, mock_hub, mock_config_entry: MockConfigEntry
) -> None:
    """Only the hub and devices no longer exposed by the Core can be removed."""
    from homeassistant.helpers import device_registry as dr

    from custom_components.taphome import async_remove_config_entry_device
    from tests_common import TEST_LOCATION_ID

    await setup_integration(hass, mock_config_entry)
    registry = dr.async_get(hass)
    hub_device = registry.async_get_device({(DOMAIN, TEST_LOCATION_ID)})
    socket = registry.async_get_device({(DOMAIN, f"{TEST_LOCATION_ID}_2")})

    # The Core hub device and a device still exposed by the Core are kept.
    assert not await async_remove_config_entry_device(hass, mock_config_entry, hub_device)
    assert not await async_remove_config_entry_device(hass, mock_config_entry, socket)

    # A device the Core no longer exposes can be removed.
    mock_hub.devices.pop(2)
    assert await async_remove_config_entry_device(hass, mock_config_entry, socket)


async def test_migration_moves_option_devices_to_subentries(
    hass: HomeAssistant, mock_hub
) -> None:
    """A pre-subentry entry migrates its device lists, preserving unique ids."""
    from homeassistant.const import CONF_ID, CONF_TOKEN
    from homeassistant.helpers import device_registry as dr, entity_registry as er

    from custom_components.taphome.const import CONF_API_URL, SUBENTRY_TYPE_DEVICE
    from tests_common import TEST_API_URL, TEST_LOCATION_ID, TEST_TOKEN

    entry = MockConfigEntry(
        domain=DOMAIN,
        title="TapHome",
        unique_id=TEST_LOCATION_ID,
        version=1,
        minor_version=1,
        data={CONF_TOKEN: TEST_TOKEN, CONF_API_URL: TEST_API_URL, CONF_ID: None},
        options={"switches": [{"id": 2}]},
    )
    entry.add_to_hass(hass)

    # A pre-subentry install already has the device and entity in the registries.
    device_registry = dr.async_get(hass)
    entity_registry = er.async_get(hass)
    device = device_registry.async_get_or_create(
        config_entry_id=entry.entry_id,
        identifiers={(DOMAIN, f"{TEST_LOCATION_ID}_2")},
        name="Garden Socket",
    )
    entity = entity_registry.async_get_or_create(
        "switch",
        DOMAIN,
        "taphome.switch.2",
        config_entry=entry,
        device_id=device.id,
    )

    await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()

    assert entry.minor_version == 2
    assert "switches" not in entry.options
    subentries = [
        subentry
        for subentry in entry.subentries.values()
        if subentry.subentry_type == SUBENTRY_TYPE_DEVICE
    ]
    assert len(subentries) == 1
    subentry = subentries[0]
    assert subentry.data["platform"] == "switches"
    assert subentry.data["id"] == 2

    # The entity keeps its unique id (history) and now belongs to the subentry.
    migrated = entity_registry.async_get(entity.entity_id)
    assert migrated.unique_id == "taphome.switch.2"
    assert migrated.config_subentry_id == subentry.subentry_id

    migrated_device = device_registry.async_get(device.id)
    assert migrated_device.config_entries_subentries[entry.entry_id] == {
        subentry.subentry_id
    }


async def test_migration_is_idempotent(hass: HomeAssistant, mock_hub) -> None:
    """A device listed twice (or a re-run) yields one subentry, no crash.

    async_add_subentry raises on a duplicate unique id, so migration must skip
    devices that already have a subentry.
    """
    from homeassistant.const import CONF_ID, CONF_TOKEN

    from custom_components.taphome.const import CONF_API_URL, SUBENTRY_TYPE_DEVICE
    from tests_common import TEST_API_URL, TEST_LOCATION_ID, TEST_TOKEN

    entry = MockConfigEntry(
        domain=DOMAIN,
        title="TapHome",
        unique_id=TEST_LOCATION_ID,
        version=1,
        minor_version=1,
        data={CONF_TOKEN: TEST_TOKEN, CONF_API_URL: TEST_API_URL, CONF_ID: None},
        options={"switches": [{"id": 2}, {"id": 2}]},
    )
    entry.add_to_hass(hass)

    await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()

    assert entry.state is ConfigEntryState.LOADED
    assert entry.minor_version == 2
    subentries = [
        subentry
        for subentry in entry.subentries.values()
        if subentry.subentry_type == SUBENTRY_TYPE_DEVICE
    ]
    assert len(subentries) == 1
    assert subentries[0].data["id"] == 2


async def test_zone_and_label_mapping_apply_to_device(
    hass: HomeAssistant, mock_hub
) -> None:
    """A mapped zone/category sets the device area and labels device + entity."""
    from homeassistant.helpers import (
        area_registry as ar,
        device_registry as dr,
        entity_registry as er,
        label_registry as lr,
    )

    from tests_common import TEST_LOCATION_ID, make_device

    # Give the switch device (id 2) a zone and a category to map.
    make_device(
        mock_hub,
        {
            "deviceId": 2,
            "type": "PowerOutlet",
            "name": "Garden Socket",
            "description": "Socket by the terrace",
            "zone": "Garden",
            "category": "Curtains",
            "supportedValues": [
                {"valueTypeId": ValueType.SWITCH_STATE.value, "readOnly": False},
            ],
            "values": {ValueType.SWITCH_STATE: 0.0},
        },
    )

    area = ar.async_get(hass).async_create("Zahrada")
    label = lr.async_get(hass).async_create("Rolety")

    entry = make_config_entry(
        {
            "zones": {"Garden": area.id},
            "labels": {"Curtains": label.label_id},
        }
    )
    await setup_integration(hass, entry)

    device = dr.async_get(hass).async_get_device({(DOMAIN, f"{TEST_LOCATION_ID}_2")})
    assert device is not None
    assert device.area_id == area.id
    assert label.label_id in device.labels

    entity_registry = er.async_get(hass)
    switch_entities = [
        registry_entry
        for registry_entry in er.async_entries_for_device(entity_registry, device.id)
        if registry_entry.domain == "switch"
    ]
    assert len(switch_entities) == 1
    assert label.label_id in switch_entities[0].labels


async def test_zone_mapping_by_name_and_ignore(
    hass: HomeAssistant, mock_hub
) -> None:
    """YAML name targets create areas; ignored zones get no area at all."""
    from homeassistant.helpers import area_registry as ar, device_registry as dr

    from tests_common import TEST_LOCATION_ID, make_device

    for device_id, zone in ((2, "Garden"), (9, "Zvlhčovač")):
        make_device(
            mock_hub,
            {
                "deviceId": device_id,
                "type": "PowerOutlet",
                "name": f"Socket {device_id}",
                "description": "",
                "zone": zone,
                "supportedValues": [
                    {"valueTypeId": ValueType.SWITCH_STATE.value, "readOnly": False},
                ],
                "values": {ValueType.SWITCH_STATE: 0.0},
            },
        )
    entry = make_config_entry(
        {
            "switches": [{"id": 2}, {"id": 9}],
            "zones": {"Garden": "Zahrada", "Zvlhčovač": {"ignore": True}},
        }
    )
    await setup_integration(hass, entry)

    area_registry = ar.async_get(hass)
    device_registry = dr.async_get(hass)

    # The YAML mapping target is a name: the area is created and assigned.
    zahrada = area_registry.async_get_area_by_name("Zahrada")
    assert zahrada is not None
    mapped = device_registry.async_get_device({(DOMAIN, f"{TEST_LOCATION_ID}_2")})
    assert mapped.area_id == zahrada.id
    # The raw TapHome zone name must not leak into an area of its own.
    assert area_registry.async_get_area_by_name("Garden") is None

    # An ignored zone assigns no area and creates none.
    ignored = device_registry.async_get_device({(DOMAIN, f"{TEST_LOCATION_ID}_9")})
    assert ignored.area_id is None
    assert area_registry.async_get_area_by_name("Zvlhčovač") is None


async def test_labels_created_from_categories(
    hass: HomeAssistant, mock_hub
) -> None:
    """Without a mapping every category becomes a label of the same name."""
    from homeassistant.helpers import (
        device_registry as dr,
        entity_registry as er,
        label_registry as lr,
    )

    from tests_common import TEST_LOCATION_ID, make_device

    make_device(
        mock_hub,
        {
            "deviceId": 2,
            "type": "PowerOutlet",
            "name": "Garden Socket",
            "description": "Socket by the terrace",
            "category": "Osvětlení",
            "supportedValues": [
                {"valueTypeId": ValueType.SWITCH_STATE.value, "readOnly": False},
            ],
            "values": {ValueType.SWITCH_STATE: 0.0},
        },
    )
    entry = make_config_entry()
    await setup_integration(hass, entry)

    label = lr.async_get(hass).async_get_label_by_name("Osvětlení")
    assert label is not None

    device = dr.async_get(hass).async_get_device({(DOMAIN, f"{TEST_LOCATION_ID}_2")})
    assert label.label_id in device.labels

    entity_registry = er.async_get(hass)
    switch_entities = [
        registry_entry
        for registry_entry in er.async_entries_for_device(entity_registry, device.id)
        if registry_entry.domain == "switch"
    ]
    assert label.label_id in switch_entities[0].labels


async def test_unload_unsubscribes_entities(
    hass: HomeAssistant, mock_hub, mock_config_entry: MockConfigEntry
) -> None:
    """Unloading the entry removes all entity subscriptions from the SDK."""
    event = mock_hub.devices[2].state.changed
    baseline = len(event._handlers)

    await setup_integration(hass, mock_config_entry)
    assert len(event._handlers) > baseline

    assert await hass.config_entries.async_unload(mock_config_entry.entry_id)
    await hass.async_block_till_done()

    assert len(event._handlers) == baseline
