"""Shared fixtures for the TapHome integration tests."""

from __future__ import annotations

from pathlib import Path
import sys
from unittest.mock import AsyncMock, patch

sys.path.insert(0, str(Path(__file__).resolve().parent))

from tests_common import (  # noqa: E402
    TEST_LOCATION,
    make_config_entry,
    make_hub,
)

import pytest  # noqa: E402
from pytest_homeassistant_custom_component.common import (  # noqa: E402
    MockConfigEntry,
)
from taphome_sdk import TapHomeApi, TapHomeHubFactory  # noqa: E402



@pytest.fixture(autouse=True)
def auto_enable_custom_integrations(enable_custom_integrations) -> None:
    """Enable loading the integration from custom_components."""
    return


@pytest.fixture
def mock_hub():
    """Patch the SDK connection points and yield the connected hub."""
    hub = make_hub()

    async def _connect(*args, **kwargs):
        # A reload disconnects the hub; reconnect it like the real factory.
        from taphome_sdk import HubConnectionState

        hub.connection_state.value = HubConnectionState.CONNECTED
        return hub

    with (
        patch.object(
            TapHomeHubFactory, "async_connect", AsyncMock(side_effect=_connect)
        ) as connect,
        patch.object(
            TapHomeApi, "async_get_location", AsyncMock(return_value=TEST_LOCATION)
        ) as get_location,
    ):
        hub.mock_connect = connect
        hub.mock_get_location = get_location
        yield hub


@pytest.fixture
def mock_config_entry() -> MockConfigEntry:
    """Return a config entry as created by the config flow."""
    return make_config_entry()
