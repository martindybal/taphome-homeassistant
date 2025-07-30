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

from taphome_sdk import Device, SwitchStates, ValueType  # noqa: E402

# load integration as custom_components.taphome
spec = importlib.util.spec_from_file_location(
    "custom_components.taphome", "__init__.py"
)
taphome = importlib.util.module_from_spec(spec)
sys.modules["custom_components.taphome"] = taphome
spec.loader.exec_module(taphome)

class FakeTapHomeApiService:
    def __init__(self, _client=None):
        self.state = SwitchStates.ON

    async def async_discovery_devices(self):
        return [
            Device.from_dict(
                {
                    "deviceId": 1,
                    "type": "switch",
                    "name": "Switch 1",
                    "description": "Switch 1",
                    "supportedValues": [
                        {
                            "valueTypeId": ValueType.SWITCH_STATE.value,
                            "readOnly": False,
                        }
                    ],
                }
            )
        ]

    async def async_get_all_devices_values(self):
        return {
            "devices": [
                {
                    "deviceId": 1,
                    "values": [
                        {"valueTypeId": ValueType.SWITCH_STATE.value, "value": self.state.value}
                    ],
                }
            ]
        }

    async def async_get_device_values(self, device_id):
        return [
            {"valueTypeId": ValueType.SWITCH_STATE.value, "value": self.state.value}
        ]

    async def async_set_device_values(self, device_id, values):
        for val in values:
            if val["ValueTypeId"] == ValueType.SWITCH_STATE.value:
                self.state = SwitchStates(val["Value"])

    def create_device_value(self, value_type, value):
        return {"ValueTypeId": value_type.value, "Value": value}

class FakeCoordinator:
    def __init__(self, hass, update_interval, taphome_api_service, core_id):
        self.hass = hass
        self.taphome_api_service = taphome_api_service
        self.core_id = core_id
        self.update_interval = update_interval
        self._devices = {}
        self.last_update_success = False

    async def async_refresh(self):
        devices = await self.taphome_api_service.async_discovery_devices()
        for dev in devices:
            self._devices[dev.id] = {"device": dev, "values": None}
        values = await self.taphome_api_service.async_get_all_devices_values()
        for item in values["devices"]:
            self._devices[item["deviceId"]]["values"] = item["values"]
        self.last_update_success = True

    def ensure_can_be_register_entity(self, device_id):
        return True

    def register_entity(self, device_id, device_change_handler, state_change_handler):
        device_change_handler()
        state_change_handler()

    def get_device(self, device_id):
        return self._devices[device_id]["device"]

    def get_state(self, device_id, state_type):
        values = self._devices[device_id]["values"]
        if values is None:
            return None
        return state_type(values)

@pytest.fixture(autouse=True)
def patch_integration(monkeypatch):
    monkeypatch.setattr(taphome, "TapHomeApiService", FakeTapHomeApiService)
    monkeypatch.setattr(taphome.TapHomeHttpClientFactory, "create", lambda self, api_url, token: None)
    monkeypatch.setattr(taphome, "TapHomeDataUpdateCoordinator", FakeCoordinator)
    monkeypatch.setattr(taphome, "load_platform", lambda *args, **kwargs: None)
    monkeypatch.setattr(taphome, "async_register_webhook", lambda *args, **kwargs: None)

class FakeHass:
    def __init__(self):
        self.data = {}

@pytest.mark.asyncio
async def test_setup_and_switch_update():
    hass = FakeHass()
    config = {
        taphome.const.TAPHOME_PLATFORM: {
            taphome.const.CONF_CORES: [
                {
                    taphome.const.CONF_TOKEN: "token",
                    taphome.const.CONF_SWITCHES: [{"id": 1}],
                }
            ]
        }
    }
    assert await taphome.async_setup(hass, config)

    entities = []
    def add_entities(new):
        entities.extend(new)

    import switch
    await switch.setup_platform(hass, {}, add_entities)

    assert len(entities) == 1
    switch_entity = entities[0]
    assert switch_entity.is_on
    await switch_entity.async_turn_off()
    assert not switch_entity.is_on
