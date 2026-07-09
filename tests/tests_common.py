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

# Import the integration before pytest-homeassistant-custom-component installs
# its own custom_components module, so the package stays cached in sys.modules.
import custom_components.taphome  # noqa: E402,F401

# aiodns (used by aiohttp/Home Assistant) lazily spawns a process-wide pycares
# shutdown daemon thread. Start it before the first test so the thread-leak
# check of pytest-homeassistant-custom-component sees it in its baseline.
try:
    import pycares  # noqa: E402

    pycares._shutdown_manager.start()  # noqa: SLF001
except (ImportError, AttributeError):
    pass

from taphome_sdk import (  # noqa: E402
    HubConnectionState,
    Location,
    TapHomeHub,
    ValueType,
)
from taphome_sdk.device_factory import DeviceFactory  # noqa: E402
from taphome_sdk.taphome_api import (  # noqa: E402
    DeviceMetadata,
    DevicesValuesResponse,
    DeviceValues,
    DiscoveryResponse,
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
        # Device ids whose set calls report FAILED, like a rejecting core.
        self.fail_devices: set[int] = set()
        # Raw metadata returned by the discovery endpoint; tests append here
        # to simulate a device newly exposed in the TapHome app.
        self.discovery_definitions: list[dict] = list(DEVICE_DEFINITIONS)

    async def async_set_device_values(
        self, device_id: int, values: dict[ValueType, float]
    ) -> SetDeviceValueResponse:
        self.set_calls.append((device_id, dict(values)))
        if device_id in self.fail_devices:
            return SetDeviceValueResponse(
                device_id=device_id,
                values_changed=dict.fromkeys(values, ValueChangeResult.FAILED),
                timestamp=1,
            )
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

    async def async_discovery_devices(self) -> DiscoveryResponse:
        return DiscoveryResponse(
            devices={
                definition["deviceId"]: DeviceMetadata.from_dict(definition)
                for definition in self.discovery_definitions
            },
            timestamp=1,
        )

    async def async_get_all_devices_values(self) -> DevicesValuesResponse:
        return DevicesValuesResponse(
            devices={
                device_id: DeviceValues(
                    device_id=device_id,
                    values=dict(values),
                    error_code=None,
                    message=None,
                )
                for device_id, values in self.values.items()
            },
            timestamp=1,
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
    """Return a config entry as created by the config flow (device subentries)."""
    from pytest_homeassistant_custom_component.common import MockConfigEntry

    from custom_components.taphome.const import (
        CONF_API_URL,
        DEVICE_CONFIG_KEYS,
        DOMAIN,
    )
    from custom_components.taphome.subentry import build_device_subentry_data
    from homeassistant.config_entries import ConfigSubentryData
    from homeassistant.const import CONF_ID, CONF_TOKEN

    raw = {
        "lights": [{"id": 1}],
        "switches": [{"id": 2}],
        "sensors": [{"id": 5}],
        **(extra_options or {}),
    }
    device_keys = set(DEVICE_CONFIG_KEYS)

    options: dict = {}
    subentries: list[ConfigSubentryData] = []
    for key, value in raw.items():
        if key not in device_keys or not isinstance(value, list):
            options[key] = value
            continue
        for device_config in value:
            config = (
                dict(device_config)
                if isinstance(device_config, dict)
                else {"id": device_config}
            )
            title = f"TapHome device {int(config['id'])}"
            subentries.append(build_device_subentry_data(key, config, title))

    return MockConfigEntry(
        domain=DOMAIN,
        title=TEST_LOCATION_NAME,
        unique_id=TEST_LOCATION_ID,
        minor_version=2,
        data={
            CONF_TOKEN: TEST_TOKEN,
            CONF_API_URL: TEST_API_URL,
            CONF_ID: None,
        },
        options=options,
        subentries_data=subentries,
    )


async def setup_integration(hass: HomeAssistant, config_entry) -> None:
    """Add the config entry to hass and set it up."""
    config_entry.add_to_hass(hass)
    await hass.config_entries.async_setup(config_entry.entry_id)
    await hass.async_block_till_done()


def device_subentry(config_entry, platform: str, device_id: int):
    """Return the device subentry for one platform/device, or None."""
    from custom_components.taphome.subentry import (
        iter_device_subentries,
        subentry_platform,
    )

    for subentry in iter_device_subentries(config_entry):
        if (
            subentry_platform(subentry.data) == platform
            and int(subentry.data.get("id")) == device_id
        ):
            return subentry
    return None


def device_subentry_configs(config_entry, platform: str) -> list[dict]:
    """Return the device configs (minus the platform key) for one platform."""
    from custom_components.taphome.subentry import (
        device_config_from_subentry,
        iter_device_subentries,
        subentry_platform,
    )

    return [
        device_config_from_subentry(subentry.data)
        for subentry in iter_device_subentries(config_entry)
        if subentry_platform(subentry.data) == platform
    ]
