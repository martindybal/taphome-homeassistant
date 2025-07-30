import importlib.util
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

homeassistant_spec = importlib.util.find_spec("homeassistant")
aiohttp_spec = importlib.util.find_spec("aiohttp")
if homeassistant_spec is None or aiohttp_spec is None:
    pytest.skip("homeassistant or aiohttp not installed", allow_module_level=True)

from taphome_entity import TapHomeEntity  # noqa: E402
from coordinator import (  # noqa: E402
    TapHomeDataUpdateCoordinator,
    TapHomeDataUpdateCoordinatorDevice,
)


def test_conversion_helpers_round_trip() -> None:
    original = 0.6
    ha_byte = TapHomeEntity.convert_taphome_byte_to_ha(original)
    assert ha_byte == pytest.approx(153.0)
    assert TapHomeEntity.convert_ha_byte_to_taphome(ha_byte) == pytest.approx(original)

    ha_percent = TapHomeEntity.convert_taphome_percentage_to_ha(original)
    assert ha_percent == 60
    assert TapHomeEntity.convert_ha_percentage_to_taphome(ha_percent) == pytest.approx(original)


def test_convert_bool_values() -> None:
    assert TapHomeEntity.convert_taphome_bool_to_ha(1) is True
    assert TapHomeEntity.convert_taphome_bool_to_ha(0) is False
    assert TapHomeEntity.convert_taphome_bool_to_ha(42) is None
    assert TapHomeEntity.convert_taphome_bool_to_ha(None) is None


def test_apply_changes_updates_existing_value() -> None:
    device = TapHomeDataUpdateCoordinatorDevice()
    device.taphome_values = [
        {"valueTypeId": 1, "value": 10},
        {"valueTypeId": 2, "value": 20},
    ]

    coordinator = TapHomeDataUpdateCoordinator.__new__(TapHomeDataUpdateCoordinator)
    changed = [{"valueTypeId": 1, "value": 15}]

    new_values = coordinator.apply_changes(device, changed)

    assert new_values == [
        {"valueTypeId": 1, "value": 15},
        {"valueTypeId": 2, "value": 20},
    ]
    assert device.taphome_values == [
        {"valueTypeId": 1, "value": 10},
        {"valueTypeId": 2, "value": 20},
    ]


def test_apply_changes_ignores_unknown_value() -> None:
    device = TapHomeDataUpdateCoordinatorDevice()
    device.taphome_values = [{"valueTypeId": 1, "value": 10}]

    coordinator = TapHomeDataUpdateCoordinator.__new__(TapHomeDataUpdateCoordinator)
    changed = [{"valueTypeId": 2, "value": 99}]

    new_values = coordinator.apply_changes(device, changed)

    assert new_values == [{"valueTypeId": 1, "value": 10}]
    assert device.taphome_values == [{"valueTypeId": 1, "value": 10}]
