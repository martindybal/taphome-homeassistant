"""Shared constants and helpers for the TapHome integration tests.

The repository root is the integration package (HACS ``content_in_root``), so
before anything imports ``custom_components.taphome`` this module places a
``custom_components`` package pointing at the repository root on ``sys.path``.
"""

from __future__ import annotations

import os
from pathlib import Path
import shutil
import sys
import tempfile
from unittest.mock import Mock

_REPO_ROOT = Path(__file__).resolve().parents[1]


def ensure_custom_components_package() -> None:
    """Make ``custom_components.taphome`` importable from the repository root."""
    if any(
        (Path(entry) / "custom_components" / "taphome" / "manifest.json").is_file()
        for entry in sys.path
    ):
        return

    base = Path(tempfile.mkdtemp(prefix="taphome_tests_"))
    package_dir = base / "custom_components"
    package_dir.mkdir()
    target = package_dir / "taphome"
    try:
        os.symlink(_REPO_ROOT, target, target_is_directory=True)
    except OSError:
        # Windows without developer mode cannot create symlinks.
        shutil.copytree(
            _REPO_ROOT,
            target,
            ignore=shutil.ignore_patterns(
                ".git", ".venv", "tests", "docs", "__pycache__"
            ),
        )
    sys.path.insert(0, str(base))


ensure_custom_components_package()

from taphome_sdk import (  # noqa: E402
    HubConnectionState,
    Location,
    TapHomeHub,
    ValueType,
)
from taphome_sdk.device_factory import DeviceFactory  # noqa: E402
from taphome_sdk.taphome_api import (  # noqa: E402
    DeviceMetadata,
    DeviceValues,
    SetDeviceValueResponse,
    ValueChangeResult,
)

from homeassistant.core import HomeAssistant  # noqa: E402

TEST_API_URL = "http://10.0.0.5/api/TapHomeApi/v1"
TEST_TOKEN = "test-token"
TEST_LOCATION_ID = "11111111-2222-3333-4444-555555555555"
TEST_LOCATION_NAME = "Test Home"

TEST_LOCATION = Location(
    location_id=TEST_LOCATION_ID,
    location_name=TEST_LOCATION_NAME,
    taphome_api_version=1,
    timestamp=1,
)

# Raw metadata mirroring the TapHome API discovery response. Devices carry no
# zone/category on purpose: the setup wizard then skips the zone/label steps,
# which keeps the flow tests focused on connection and device selection.
DEVICE_DEFINITIONS: tuple[dict, ...] = (
    {
        "deviceId": 1,
        "type": "LightSwitch",
        "name": "Kitchen Light",
        "description": "Kitchen ceiling light",
        "supportedValues": [
            {"valueTypeId": ValueType.ANALOG_OUTPUT_VALUE.value, "readOnly": False},
            {
                "valueTypeId": ValueType.ANALOG_OUTPUT_DESIRED_VALUE.value,
                "readOnly": False,
            },
            {"valueTypeId": ValueType.SWITCH_STATE.value, "readOnly": False},
        ],
        "values": {
            ValueType.ANALOG_OUTPUT_VALUE: 0.0,
            ValueType.ANALOG_OUTPUT_DESIRED_VALUE: 0.0,
            ValueType.SWITCH_STATE: 0.0,
        },
    },
    {
        "deviceId": 2,
        "type": "PowerOutlet",
        "name": "Garden Socket",
        "description": "Socket by the terrace",
        "supportedValues": [
            {"valueTypeId": ValueType.SWITCH_STATE.value, "readOnly": False},
        ],
        "values": {ValueType.SWITCH_STATE: 0.0},
    },
    {
        "deviceId": 3,
        "type": "Thermostat",
        "name": "Living Room Thermostat",
        "description": "Thermostat in the living room",
        "supportedValues": [
            {"valueTypeId": ValueType.REAL_TEMPERATURE.value, "readOnly": True},
            {"valueTypeId": ValueType.TEMPERATURE_SET_POINT.value, "readOnly": False},
        ],
        "values": {
            ValueType.REAL_TEMPERATURE: 21.3,
            ValueType.TEMPERATURE_SET_POINT: 22.0,
        },
    },
    {
        "deviceId": 4,
        "type": "Blinds",
        "name": "Bedroom Blinds",
        "description": "Blinds in the bedroom",
        "supportedValues": [
            {"valueTypeId": ValueType.BLINDS_LEVEL.value, "readOnly": False},
            {"valueTypeId": ValueType.BLINDS_IS_MOVING.value, "readOnly": True},
        ],
        "values": {
            ValueType.BLINDS_LEVEL: 0.0,
            ValueType.BLINDS_IS_MOVING: 0.0,
        },
    },
    {
        "deviceId": 5,
        "type": "Variable",
        "name": "Outside Temperature",
        "description": "Temperature in the garden",
        "supportedValues": [
            {"valueTypeId": ValueType.VARIABLE_STATE.value, "readOnly": True},
        ],
        "values": {ValueType.VARIABLE_STATE: 23.4},
    },
    {
        "deviceId": 6,
        "type": "MultiValueSwitch",
        "name": "Scene Switch",
        "description": "Living room scenes",
        "supportedValues": [
            {
                "valueTypeId": ValueType.MULTI_VALUE_SWITCH_STATE.value,
                "readOnly": False,
                "enumeratedValues": [
                    {"value": 0, "name": "Off", "isEnabled": True},
                    {"value": 1, "name": "Party", "isEnabled": True},
                    {"value": 2, "name": "Relax", "isEnabled": True},
                ],
            },
            {
                "valueTypeId": ValueType.MULTI_VALUE_SWITCH_DESIRED_STATE.value,
                "readOnly": False,
            },
        ],
        "values": {
            ValueType.MULTI_VALUE_SWITCH_STATE: 0.0,
            ValueType.MULTI_VALUE_SWITCH_DESIRED_STATE: 0.0,
        },
    },
)


# Setting a "desired" value makes the core apply it to the actual value; the
# fake API mirrors that so a reload after a command returns the new state.
_DESIRED_TO_ACTUAL = {
    ValueType.ANALOG_OUTPUT_DESIRED_VALUE: ValueType.ANALOG_OUTPUT_VALUE,
    ValueType.MULTI_VALUE_SWITCH_DESIRED_STATE: ValueType.MULTI_VALUE_SWITCH_STATE,
    ValueType.HUE_BRIGHTNESS_DESIRED_VALUE: ValueType.HUE_BRIGHTNESS,
}


class FakeTapHomeApi:
    """Stateful in-memory stand-in for the TapHome HTTP API."""

    def __init__(self) -> None:
        self.values: dict[int, dict[ValueType, float]] = {
            definition["deviceId"]: dict(definition.get("values", {}))
            for definition in DEVICE_DEFINITIONS
        }
        self.set_calls: list[tuple[int, dict[ValueType, float]]] = []

    async def async_set_device_values(
        self, device_id: int, values: dict[ValueType, float]
    ) -> SetDeviceValueResponse:
        self.set_calls.append((device_id, dict(values)))
        stored = self.values.setdefault(device_id, {})
        for value_type, value in values.items():
            stored[value_type] = value
            actual = _DESIRED_TO_ACTUAL.get(value_type)
            if actual is not None:
                stored[actual] = value
        return SetDeviceValueResponse(
            device_id=device_id,
            values_changed=dict.fromkeys(values, ValueChangeResult.CHANGED),
            timestamp=1,
        )

    async def async_get_device_values(self, device_id: int) -> DeviceValues:
        return DeviceValues(
            device_id=device_id,
            values=dict(self.values.get(device_id, {})),
            error_code=None,
            message=None,
        )


def make_device(hub: TapHomeHub, definition: dict):
    """Create one SDK device on the hub from raw API-shaped metadata."""
    metadata = DeviceMetadata.from_dict(definition)
    device = DeviceFactory.create_device(
        hub.api, hub.connection_type, metadata, dict(definition.get("values", {}))
    )
    assert device is not None
    hub.devices[metadata.id] = device
    return device


def make_hub(api: FakeTapHomeApi | None = None) -> TapHomeHub:
    """Build a connected hub with the fixture devices and a fake API."""
    hub = TapHomeHub(TEST_API_URL, TEST_TOKEN, Mock())
    hub.api = api or FakeTapHomeApi()
    hub.location = TEST_LOCATION

    for definition in DEVICE_DEFINITIONS:
        make_device(hub, definition)

    hub.connection_state.value = HubConnectionState.CONNECTED
    return hub


def make_config_entry(extra_options: dict | None = None):
    """Return a config entry as created by the config flow."""
    from pytest_homeassistant_custom_component.common import MockConfigEntry

    from custom_components.taphome.const import CONF_API_URL, DOMAIN
    from homeassistant.const import CONF_ID, CONF_TOKEN

    return MockConfigEntry(
        domain=DOMAIN,
        title=TEST_LOCATION_NAME,
        unique_id=TEST_LOCATION_ID,
        data={
            CONF_TOKEN: TEST_TOKEN,
            CONF_API_URL: TEST_API_URL,
            CONF_ID: None,
        },
        options={
            "lights": [{"id": 1}],
            "switches": [{"id": 2}],
            "sensors": [{"id": 5}],
            **(extra_options or {}),
        },
    )


async def setup_integration(hass: HomeAssistant, config_entry) -> None:
    """Add the config entry to hass and set it up."""
    config_entry.add_to_hass(hass)
    await hass.config_entries.async_setup(config_entry.entry_id)
    await hass.async_block_till_done()
