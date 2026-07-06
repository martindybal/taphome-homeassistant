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

    assert sorted(mock_config_entry.data[CONF_KNOWN_DEVICE_IDS]) == [1, 2, 5]


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
