"""Tests for the TapHome config entry setup and unload."""

from unittest.mock import AsyncMock, patch

from pytest_homeassistant_custom_component.common import MockConfigEntry
from taphome_sdk import (
    TapHomeAuthError,
    TapHomeConnectionError,
    TapHomeHubFactory,
    ValueType,
)

from custom_components.taphome.const import CONF_KNOWN_DEVICE_IDS, DOMAIN
from homeassistant.config_entries import ConfigEntryState
from homeassistant.const import CONF_WEBHOOK_ID, STATE_OFF, STATE_ON
from homeassistant.core import HomeAssistant

from tests_common import make_config_entry, setup_integration


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
