"""Tests for the TapHome config flow."""

from ipaddress import ip_address

from taphome_sdk import TapHomeAuthError, TapHomeConnectionError, ValueType

from custom_components.taphome.const import (
    CONF_API_URL,
    CONF_IP,
    DEFAULT_CLOUD_API_URL,
    DOMAIN,
)
from homeassistant.config_entries import SOURCE_USER, SOURCE_ZEROCONF
from homeassistant.const import CONF_TOKEN, CONF_WEBHOOK_ID
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResultType
from homeassistant.helpers.service_info.zeroconf import ZeroconfServiceInfo

from pytest_homeassistant_custom_component.common import MockConfigEntry

from tests_common import (
    TEST_API_URL,
    TEST_LOCATION_ID,
    TEST_LOCATION_NAME,
    TEST_TOKEN,
    make_config_entry,
    setup_integration,
)

USER_INPUT = {CONF_TOKEN: TEST_TOKEN, CONF_IP: "10.0.0.5"}


async def _start_user_flow(hass: HomeAssistant):
    return await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": SOURCE_USER}
    )


def _zeroconf_info(
    host: str = "10.0.0.5", location_id: str = TEST_LOCATION_ID
) -> ZeroconfServiceInfo:
    """Return discovery info shaped like a real Core announcement."""
    return ZeroconfServiceInfo(
        ip_address=ip_address(host),
        ip_addresses=[ip_address(host)],
        hostname="Test-Home.local.",
        name="th-Test-Home._th-discovery._tcp.local.",
        port=11764,
        properties={
            "Name": TEST_LOCATION_NAME,
            "LocationId": location_id,
            "IpOnLocalNetwork": host,
            # The app pairing token; unrelated to the API token.
            "AccessToken": "************ABCD",
        },
        type="_th-discovery._tcp.local.",
    )


async def _start_zeroconf_flow(hass: HomeAssistant, info: ZeroconfServiceInfo):
    return await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": SOURCE_ZEROCONF}, data=info
    )


def _subentry_configs(result, platform: str) -> list[dict]:
    """Return the device configs of one platform from a flow result."""
    from custom_components.taphome.const import (
        SUBENTRY_DATA_AUTO_TITLE,
        SUBENTRY_DATA_PLATFORM,
    )

    configs: list[dict] = []
    for subentry in result.get("subentries") or ():
        data = dict(subentry["data"])
        data.pop(SUBENTRY_DATA_AUTO_TITLE, None)
        if data.pop(SUBENTRY_DATA_PLATFORM, None) == platform:
            configs.append(data)
    return configs


async def test_user_flow_creates_entry(hass: HomeAssistant, mock_hub) -> None:
    """The full setup wizard adds a device and creates the entry."""
    result = await _start_user_flow(hass)
    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "user"

    # Connection form: the fixture devices carry no zones or categories, so
    # the wizard continues straight to the device selection.
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], USER_INPUT
    )
    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "add_devices"

    # Pick one device, expose it as a switch.
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], {"devices": ["2"]}
    )
    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "add_devices_platform"

    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], {"Garden Socket (2)": {"domains": ["switches"]}}
    )
    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "add_devices_options"

    result = await hass.config_entries.flow.async_configure(result["flow_id"], {})
    await hass.async_block_till_done()

    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["title"] == TEST_LOCATION_NAME
    assert result["data"][CONF_TOKEN] == TEST_TOKEN
    assert result["data"][CONF_API_URL] == TEST_API_URL
    assert _subentry_configs(result, "switches") == [{"id": 2}]
    assert result["result"].unique_id == TEST_LOCATION_ID


async def test_zeroconf_flow_creates_entry(hass: HomeAssistant, mock_hub) -> None:
    """A discovered Core asks for the token plus core settings, then runs."""
    result = await _start_zeroconf_flow(hass, _zeroconf_info())
    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "zeroconf_confirm"
    assert result["description_placeholders"] == {
        "name": TEST_LOCATION_NAME,
        "host": "10.0.0.5",
    }
    # The confirm form offers the core settings (webhook, attributes), but not
    # the connection fields (cloud/ip) that discovery already determined.
    assert "webhook_id" in result["data_schema"].schema
    assert CONF_IP not in result["data_schema"].schema

    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], {CONF_TOKEN: TEST_TOKEN, CONF_WEBHOOK_ID: "th_webhook"}
    )
    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "add_devices"

    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], {"devices": ["2"]}
    )
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], {"Garden Socket (2)": {"domains": ["switches"]}}
    )
    result = await hass.config_entries.flow.async_configure(result["flow_id"], {})
    await hass.async_block_till_done()

    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["title"] == TEST_LOCATION_NAME
    assert result["data"][CONF_TOKEN] == TEST_TOKEN
    assert result["data"][CONF_API_URL] == TEST_API_URL
    assert result["result"].unique_id == TEST_LOCATION_ID
    # The core settings entered on the confirm form are stored.
    assert result["result"].options[CONF_WEBHOOK_ID] == "th_webhook"


async def test_zeroconf_flow_runs_the_full_wizard(
    hass: HomeAssistant, mock_hub
) -> None:
    """Discovery runs the same zones -> labels -> add-devices wizard as manual add.

    The confirm step hands off to _async_start_wizard, exactly like async_step_user,
    so a device with a zone/category takes the flow through both mapping steps to
    the device picker (no separate discovery code path).
    """
    from tests_common import make_device

    make_device(
        mock_hub,
        {
            "deviceId": 2,
            "type": "PowerOutlet",
            "name": "Garden Socket",
            "description": "Socket by the terrace",
            "zone": "Garden",
            "category": "Sockets",
            "supportedValues": [
                {"valueTypeId": ValueType.SWITCH_STATE.value, "readOnly": False}
            ],
            "values": {ValueType.SWITCH_STATE: 0.0},
        },
    )
    result = await _start_zeroconf_flow(hass, _zeroconf_info())
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], {CONF_TOKEN: TEST_TOKEN, CONF_WEBHOOK_ID: "taphome"}
    )
    assert result["step_id"] == "zones"
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], {"Garden": {}}
    )
    assert result["step_id"] == "labels"
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], {"Sockets": {}}
    )
    assert result["step_id"] == "add_devices"


async def test_zeroconf_recovers_from_bad_token(
    hass: HomeAssistant, mock_hub
) -> None:
    """A rejected token shows on the confirm form and the flow continues."""
    result = await _start_zeroconf_flow(hass, _zeroconf_info())

    mock_hub.mock_get_location.side_effect = TapHomeAuthError(401)
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], {CONF_TOKEN: "wrong"}
    )
    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "zeroconf_confirm"
    assert result["errors"] == {"base": "invalid_auth"}

    mock_hub.mock_get_location.side_effect = None
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], {CONF_TOKEN: TEST_TOKEN}
    )
    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "add_devices"


async def test_zeroconf_updates_ip_of_configured_entry(
    hass: HomeAssistant, mock_hub
) -> None:
    """Rediscovery of a configured Core refreshes its local API address."""
    entry = make_config_entry()
    entry.add_to_hass(hass)

    result = await _start_zeroconf_flow(hass, _zeroconf_info(host="10.0.0.99"))
    await hass.async_block_till_done()

    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "already_configured"
    assert entry.data[CONF_API_URL] == "http://10.0.0.99/api/TapHomeApi/v1"


async def test_zeroconf_keeps_cloud_connection(
    hass: HomeAssistant, mock_hub
) -> None:
    """A deliberate cloud connection is not switched to the local address."""
    entry = make_config_entry()
    entry.add_to_hass(hass)
    hass.config_entries.async_update_entry(
        entry, data={**entry.data, CONF_API_URL: DEFAULT_CLOUD_API_URL}
    )

    result = await _start_zeroconf_flow(hass, _zeroconf_info(host="10.0.0.99"))
    await hass.async_block_till_done()

    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "already_configured"
    assert entry.data[CONF_API_URL] == DEFAULT_CLOUD_API_URL


async def test_zeroconf_without_location_id_aborts(
    hass: HomeAssistant, mock_hub
) -> None:
    """An announcement without the location id cannot be used."""
    info = _zeroconf_info()
    info.properties.pop("LocationId")

    result = await _start_zeroconf_flow(hass, info)

    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "invalid_discovery_info"


async def test_user_flow_recovers_from_errors(hass: HomeAssistant, mock_hub) -> None:
    """Auth and connection errors show on the form and the flow can continue."""
    result = await _start_user_flow(hass)

    mock_hub.mock_get_location.side_effect = TapHomeAuthError(401)
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], USER_INPUT
    )
    assert result["type"] is FlowResultType.FORM
    assert result["errors"] == {"base": "invalid_auth"}

    mock_hub.mock_get_location.side_effect = TapHomeConnectionError("boom")
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], USER_INPUT
    )
    assert result["type"] is FlowResultType.FORM
    assert result["errors"] == {"base": "cannot_connect"}

    mock_hub.mock_get_location.side_effect = None
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], USER_INPUT
    )
    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "add_devices"
    assert not result.get("errors")


async def test_user_flow_requires_ip_without_cloud(
    hass: HomeAssistant, mock_hub
) -> None:
    """Leaving both cloud and IP empty is rejected."""
    result = await _start_user_flow(hass)
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], {CONF_TOKEN: TEST_TOKEN}
    )

    assert result["type"] is FlowResultType.FORM
    assert result["errors"] == {"base": "ip_required"}


async def test_user_flow_aborts_for_configured_core(
    hass: HomeAssistant, mock_hub
) -> None:
    """The same core (location id) cannot be added twice."""
    entry = make_config_entry()
    entry.add_to_hass(hass)

    result = await _start_user_flow(hass)
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], USER_INPUT
    )

    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "already_configured"


async def test_user_flow_rejects_empty_device_selection(
    hass: HomeAssistant, mock_hub
) -> None:
    """Submitting the device picker with nothing selected shows an error."""
    result = await _start_user_flow(hass)
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], USER_INPUT
    )
    assert result["step_id"] == "add_devices"

    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], {"devices": []}
    )

    assert result["type"] is FlowResultType.FORM
    assert result["errors"] == {"base": "no_devices_selected"}


async def test_reauth_flow_updates_token(hass: HomeAssistant, mock_hub) -> None:
    """The reauth flow stores the new token on the entry."""
    entry = make_config_entry()
    await setup_integration(hass, entry)

    entry.async_start_reauth(hass)
    await hass.async_block_till_done()

    [flow] = hass.config_entries.flow.async_progress()
    assert flow["step_id"] == "reauth_confirm"

    result = await hass.config_entries.flow.async_configure(
        flow["flow_id"], {CONF_TOKEN: "new-token"}
    )
    await hass.async_block_till_done()

    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "reauth_successful"
    assert entry.data[CONF_TOKEN] == "new-token"


async def test_reconfigure_flow_updates_connection(
    hass: HomeAssistant, mock_hub
) -> None:
    """The reconfigure flow stores a changed IP address."""
    entry = make_config_entry()
    await setup_integration(hass, entry)

    result = await entry.start_reconfigure_flow(hass)
    assert result["step_id"] == "reconfigure"

    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], {CONF_TOKEN: TEST_TOKEN, CONF_IP: "10.0.0.99"}
    )
    await hass.async_block_till_done()

    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "reconfigure_successful"
    assert entry.data[CONF_API_URL] == "http://10.0.0.99/api/TapHomeApi/v1"


async def test_user_flow_with_zones_and_labels(hass: HomeAssistant, mock_hub) -> None:
    """Zones and labels discovered on devices walk through the mapping steps."""
    from tests_common import make_device

    from homeassistant.helpers import area_registry as ar, label_registry as lr

    area = ar.async_get(hass).async_create("Zahrada")
    label = lr.async_get(hass).async_create("Osvětlení")
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

    result = await _start_user_flow(hass)
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], USER_INPUT
    )
    assert result["step_id"] == "zones"

    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], {"Garden": {"area": area.id}}
    )
    assert result["step_id"] == "labels"

    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], {"Lights": {"label": label.label_id}}
    )
    assert result["step_id"] == "add_devices"

    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], {"devices": ["9"]}
    )
    assert result["step_id"] == "add_devices_platform"

    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        {"Pool Pump (9) — Garden · Lights": {"domains": ["switches"]}},
    )
    assert result["step_id"] == "add_devices_options"

    result = await hass.config_entries.flow.async_configure(result["flow_id"], {})
    await hass.async_block_till_done()

    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["options"]["zones"] == {"Garden": area.id}
    assert result["options"]["labels"] == {"Lights": label.label_id}
    assert _subentry_configs(result, "switches") == [{"id": 9}]


async def test_user_flow_without_devices_creates_entry(
    hass: HomeAssistant, mock_hub
) -> None:
    """A core with no exposed devices is added without the wizard."""
    mock_hub.devices.clear()

    result = await _start_user_flow(hass)
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], USER_INPUT
    )
    await hass.async_block_till_done()

    assert result["type"] is FlowResultType.CREATE_ENTRY


async def test_user_flow_device_load_errors(hass: HomeAssistant, mock_hub) -> None:
    """Errors while loading the devices are shown on the connection form."""
    mock_hub.mock_connect.side_effect = TapHomeAuthError(401)
    result = await _start_user_flow(hass)
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], USER_INPUT
    )
    assert result["errors"] == {"base": "invalid_auth"}

    mock_hub.mock_connect.side_effect = TapHomeConnectionError("boom")
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], USER_INPUT
    )
    assert result["errors"] == {"base": "cannot_connect"}


async def test_add_devices_error_branches(hass: HomeAssistant, mock_hub) -> None:
    """The deselect-all helper re-shows the picker with nothing selected."""
    result = await _start_user_flow(hass)
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], USER_INPUT
    )
    assert result["step_id"] == "add_devices"

    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], {"devices": ["2"], "clear_selection": True}
    )
    assert result["step_id"] == "add_devices"
    assert not result.get("errors")


async def test_add_devices_without_platforms_creates_entry(
    hass: HomeAssistant, mock_hub
) -> None:
    """Leaving every platform unselected finishes without adding devices."""
    result = await _start_user_flow(hass)
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], USER_INPUT
    )
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], {"devices": ["2"]}
    )
    assert result["step_id"] == "add_devices_platform"

    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], {"Garden Socket (2)": {"domains": []}}
    )
    await hass.async_block_till_done()

    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert _subentry_configs(result, "switches") == []


async def test_add_device_without_options_skips_options_step(
    hass: HomeAssistant, mock_hub
) -> None:
    """Platforms without per-device options are added directly."""
    result = await _start_user_flow(hass)
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], USER_INPUT
    )
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], {"devices": ["6"]}
    )
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], {"Scene Switch (6)": {"domains": ["multivalue_switches"]}}
    )
    await hass.async_block_till_done()

    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert _subentry_configs(result, "multivalue_switches") == [{"id": 6}]


async def test_add_device_options_validation(hass: HomeAssistant, mock_hub) -> None:
    """Invalid per-device options show an error and the flow recovers."""
    result = await _start_user_flow(hass)
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], USER_INPUT
    )
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], {"devices": ["1"]}
    )
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], {"Kitchen Light (1)": {"domains": ["lights"]}}
    )
    assert result["step_id"] == "add_devices_options"

    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], {"Kitchen Light (1) · lights": {"effect_id": "abc"}}
    )
    assert result["type"] is FlowResultType.FORM
    assert result["errors"] == {"base": "invalid_device_id"}

    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], {"Kitchen Light (1) · lights": {"effect_id": "6"}}
    )
    await hass.async_block_till_done()

    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert _subentry_configs(result, "lights") == [{"id": 1, "effect_id": 6}]


async def test_reauth_flow_errors(hass: HomeAssistant, mock_hub) -> None:
    """Connection errors and a different core are rejected during reauth."""
    from tests_common import TEST_LOCATION

    entry = make_config_entry()
    await setup_integration(hass, entry)

    entry.async_start_reauth(hass)
    await hass.async_block_till_done()
    [flow] = hass.config_entries.flow.async_progress()

    mock_hub.mock_get_location.side_effect = TapHomeConnectionError("boom")
    result = await hass.config_entries.flow.async_configure(
        flow["flow_id"], {CONF_TOKEN: "new-token"}
    )
    assert result["errors"] == {"base": "cannot_connect"}

    mock_hub.mock_get_location.side_effect = TapHomeAuthError(401)
    result = await hass.config_entries.flow.async_configure(
        flow["flow_id"], {CONF_TOKEN: "new-token"}
    )
    assert result["errors"] == {"base": "invalid_auth"}

    from dataclasses import replace

    mock_hub.mock_get_location.side_effect = None
    mock_hub.mock_get_location.return_value = replace(
        TEST_LOCATION, location_id="other-location"
    )
    result = await hass.config_entries.flow.async_configure(
        flow["flow_id"], {CONF_TOKEN: "new-token"}
    )
    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "unique_id_mismatch"


async def test_setup_flow_base_class_contract(hass: HomeAssistant) -> None:
    """The shared setup flow requires subclasses to provide the state."""
    import pytest

    from custom_components.taphome.config_flow import _TapHomeSetupFlow

    flow = _TapHomeSetupFlow()
    with pytest.raises(NotImplementedError):
        _ = flow._devices
    with pytest.raises(NotImplementedError):
        await flow._async_commit("zones")


async def test_user_flow_via_cloud(hass: HomeAssistant, mock_hub) -> None:
    """Enabling the cloud connection uses the TapHome cloud API URL."""
    mock_hub.devices.clear()
    result = await _start_user_flow(hass)
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], {CONF_TOKEN: TEST_TOKEN, "use_cloud": True}
    )
    await hass.async_block_till_done()

    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["data"][CONF_API_URL] == "https://api.taphome.com/api/TapHomeApi/v1"


async def test_user_flow_empty_location_response(
    hass: HomeAssistant, mock_hub
) -> None:
    """An empty location response counts as a connection failure."""
    mock_hub.mock_get_location.return_value = None
    result = await _start_user_flow(hass)
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], USER_INPUT
    )
    assert result["errors"] == {"base": "cannot_connect"}


async def test_reconfigure_renders_stored_connection(
    hass: HomeAssistant, mock_hub
) -> None:
    """The reconfigure form derives its defaults from the stored API URL."""
    from custom_components.taphome.const import DEFAULT_CLOUD_API_URL

    for index, api_url in enumerate(
        (DEFAULT_CLOUD_API_URL, "https://proxy.example/taphome")
    ):
        entry = MockConfigEntry(
            domain=DOMAIN,
            title=f"TapHome {index}",
            unique_id=f"loc-{index}",
            data={CONF_TOKEN: TEST_TOKEN, CONF_API_URL: api_url, "id": None},
            options={},
        )
        await setup_integration(hass, entry)
        result = await entry.start_reconfigure_flow(hass)
        assert result["step_id"] == "reconfigure"


async def test_flow_helpers_handle_unknown_devices(hass: HomeAssistant) -> None:
    """Selection helpers cope with devices that disappeared from the core."""
    from custom_components.taphome.config_flow import TapHomeConfigFlow

    flow = TapHomeConfigFlow()

    assert flow._platforms_for_device(99) == []
    assert flow._device_label(99) == "Unknown device (99)"
    # The setup wizard has no configured subentries to read.
    assert flow._device_subentries() == []
    assert flow._configured_device_ids() == set()
