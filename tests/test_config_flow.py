"""Tests for the TapHome config flow."""

from taphome_sdk import TapHomeAuthError, TapHomeConnectionError

from custom_components.taphome.const import CONF_API_URL, CONF_IP, DOMAIN
from homeassistant.config_entries import SOURCE_USER
from homeassistant.const import CONF_TOKEN
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResultType

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
    assert result["options"]["switches"] == [{"id": 2}]
    assert result["result"].unique_id == TEST_LOCATION_ID


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
