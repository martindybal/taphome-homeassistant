"""Tests for the TapHome climate platform."""

import pytest
from taphome_sdk import ValueType

from homeassistant.components.climate import (
    ATTR_CURRENT_TEMPERATURE,
    ATTR_FAN_MODE,
    ATTR_HUMIDITY,
    ATTR_HVAC_ACTION,
    ATTR_HVAC_MODE,
    ATTR_HVAC_MODES,
    ATTR_PRESET_MODE,
    ATTR_SWING_HORIZONTAL_MODE,
    ATTR_SWING_MODE,
    ATTR_TARGET_TEMP_HIGH,
    ATTR_TARGET_TEMP_LOW,
    ATTR_TEMPERATURE,
    DOMAIN as CLIMATE_DOMAIN,
    SERVICE_SET_FAN_MODE,
    SERVICE_SET_HUMIDITY,
    SERVICE_SET_HVAC_MODE,
    SERVICE_SET_PRESET_MODE,
    SERVICE_SET_SWING_HORIZONTAL_MODE,
    SERVICE_SET_SWING_MODE,
    SERVICE_SET_TEMPERATURE,
    HVACAction,
    HVACMode,
)
from homeassistant.const import ATTR_ENTITY_ID
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ServiceValidationError

from tests_common import make_config_entry, make_device, setup_integration

ENTITY_ID = "climate.living_room_thermostat"

# A heating/cooling multi-value switch as TapHome models it: the value index
# encodes the mode (0=off, 1=heating, 2=cooling, 3=heating+cooling).
HEATING_COOLING_SWITCH = {
    "deviceId": 50,
    "type": "MultiValueSwitch",
    "usage": "HeatingCooling",
    "name": "Heating Mode",
    "description": "Heating/cooling selector",
    "supportedValues": [
        {
            "valueTypeId": ValueType.MULTI_VALUE_SWITCH_STATE.value,
            "readOnly": False,
            "enumeratedValues": [
                {"value": 0, "name": "Off", "isEnabled": True},
                {"value": 1, "name": "Heating", "isEnabled": True},
                {"value": 2, "name": "Cooling", "isEnabled": True},
                {"value": 3, "name": "HeatingCooling", "isEnabled": True},
            ],
        },
        {
            "valueTypeId": ValueType.MULTI_VALUE_SWITCH_DESIRED_STATE.value,
            "readOnly": False,
        },
    ],
    "values": {
        ValueType.MULTI_VALUE_SWITCH_STATE: 1.0,
        ValueType.MULTI_VALUE_SWITCH_DESIRED_STATE: 1.0,
    },
}

HVAC_ACTION_SWITCH = {
    **HEATING_COOLING_SWITCH,
    "deviceId": 51,
    "name": "Heating Action",
    "values": {
        ValueType.MULTI_VALUE_SWITCH_STATE: 1.0,
        ValueType.MULTI_VALUE_SWITCH_DESIRED_STATE: 1.0,
    },
}

HEATING_RELAY = {
    "deviceId": 53,
    "type": "PowerOutlet",
    "name": "Heating Relay",
    "description": "Relay driving the boiler",
    "supportedValues": [
        {"valueTypeId": ValueType.SWITCH_STATE.value, "readOnly": False},
    ],
    "values": {ValueType.SWITCH_STATE: 0.0},
}

SECOND_THERMOSTAT = {
    "deviceId": 54,
    "type": "Thermostat",
    "name": "Bedroom Thermostat",
    "description": "Thermostat in the bedroom",
    "supportedValues": [
        {"valueTypeId": ValueType.REAL_TEMPERATURE.value, "readOnly": True},
        {"valueTypeId": ValueType.TEMPERATURE_SET_POINT.value, "readOnly": False},
    ],
    "values": {
        ValueType.REAL_TEMPERATURE: 20.0,
        ValueType.TEMPERATURE_SET_POINT: 21.0,
    },
}


async def test_climate_reports_temperatures(hass: HomeAssistant, mock_hub) -> None:
    """The thermostat exposes current and target temperature."""
    await setup_integration(hass, make_config_entry({"climates": [{"id": 3}]}))

    state = hass.states.get(ENTITY_ID)
    assert state.attributes[ATTR_CURRENT_TEMPERATURE] == 21.3
    assert state.attributes[ATTR_TEMPERATURE] == 22.0


async def test_climate_set_temperature(hass: HomeAssistant, mock_hub) -> None:
    """Setting the target temperature writes the set point to the core."""
    await setup_integration(hass, make_config_entry({"climates": [{"id": 3}]}))

    await hass.services.async_call(
        CLIMATE_DOMAIN,
        SERVICE_SET_TEMPERATURE,
        {ATTR_ENTITY_ID: ENTITY_ID, ATTR_TEMPERATURE: 23.5},
        blocking=True,
    )
    await hass.async_block_till_done()

    assert any(
        call[0] == 3 and call[1].get(ValueType.TEMPERATURE_SET_POINT) == 23.5
        for call in mock_hub.api.set_calls
    )
    assert hass.states.get(ENTITY_ID).attributes[ATTR_TEMPERATURE] == 23.5


async def test_climate_push_update(hass: HomeAssistant, mock_hub) -> None:
    """A pushed temperature change updates the entity."""
    await setup_integration(hass, make_config_entry({"climates": [{"id": 3}]}))

    mock_hub.devices[3].state.apply_changes({ValueType.REAL_TEMPERATURE: 19.8})
    await hass.async_block_till_done()

    state = hass.states.get(ENTITY_ID)
    assert state.attributes[ATTR_CURRENT_TEMPERATURE] == 19.8


async def test_climate_static_switch_controller(
    hass: HomeAssistant, mock_hub
) -> None:
    """A fixed-mode HVAC switch toggles heating and reports the action."""
    make_device(mock_hub, HEATING_RELAY)
    make_device(mock_hub, HVAC_ACTION_SWITCH)
    await setup_integration(
        hass,
        make_config_entry(
            {
                "climates": [
                    {
                        "id": 3,
                        "hvac_switch_id": 53,
                        "hvac_mode": "heat",
                        "hvac_action_id": 51,
                    }
                ]
            }
        ),
    )

    state = hass.states.get(ENTITY_ID)
    assert state.state == HVACMode.OFF
    assert state.attributes[ATTR_HVAC_MODES] == [HVACMode.OFF, HVACMode.HEAT]
    assert state.attributes[ATTR_HVAC_ACTION] == HVACAction.OFF

    await hass.services.async_call(
        CLIMATE_DOMAIN,
        SERVICE_SET_HVAC_MODE,
        {ATTR_ENTITY_ID: ENTITY_ID, ATTR_HVAC_MODE: HVACMode.HEAT},
        blocking=True,
    )
    await hass.async_block_till_done()

    assert (53, {ValueType.SWITCH_STATE: 1}) in mock_hub.api.set_calls
    state = hass.states.get(ENTITY_ID)
    assert state.state == HVACMode.HEAT
    # The action device reports index 1 = heating while the switch is on.
    assert state.attributes[ATTR_HVAC_ACTION] == HVACAction.HEATING

    await hass.services.async_call(
        CLIMATE_DOMAIN,
        SERVICE_SET_HVAC_MODE,
        {ATTR_ENTITY_ID: ENTITY_ID, ATTR_HVAC_MODE: HVACMode.OFF},
        blocking=True,
    )
    await hass.async_block_till_done()

    assert (53, {ValueType.SWITCH_STATE: 0}) in mock_hub.api.set_calls
    assert hass.states.get(ENTITY_ID).state == HVACMode.OFF


async def test_climate_dynamic_switch_controller(
    hass: HomeAssistant, mock_hub
) -> None:
    """A switch plus mode device follows the mode the core reports."""
    make_device(mock_hub, HEATING_RELAY)
    make_device(mock_hub, HEATING_COOLING_SWITCH)
    await setup_integration(
        hass,
        make_config_entry(
            {"climates": [{"id": 3, "hvac_switch_id": 53, "hvac_mode_id": 50}]}
        ),
    )

    state = hass.states.get(ENTITY_ID)
    # Mode device reports index 1 = heating; the switch is off.
    assert state.attributes[ATTR_HVAC_MODES] == [HVACMode.OFF, HVACMode.HEAT]
    assert state.state == HVACMode.OFF

    await hass.services.async_call(
        CLIMATE_DOMAIN,
        SERVICE_SET_HVAC_MODE,
        {ATTR_ENTITY_ID: ENTITY_ID, ATTR_HVAC_MODE: HVACMode.HEAT},
        blocking=True,
    )
    await hass.async_block_till_done()

    assert (53, {ValueType.SWITCH_STATE: 1}) in mock_hub.api.set_calls
    assert hass.states.get(ENTITY_ID).state == HVACMode.HEAT

    # The core switching the mode device to cooling re-maps the entity.
    mock_hub.devices[50].state.apply_changes(
        {ValueType.MULTI_VALUE_SWITCH_STATE: 2.0}
    )
    await hass.async_block_till_done()

    state = hass.states.get(ENTITY_ID)
    assert state.attributes[ATTR_HVAC_MODES] == [HVACMode.OFF, HVACMode.COOL]
    assert state.state == HVACMode.COOL


async def test_climate_mode_controller(hass: HomeAssistant, mock_hub) -> None:
    """A heating/cooling multi-value switch drives the HVAC mode directly."""
    make_device(mock_hub, HEATING_COOLING_SWITCH)
    await setup_integration(
        hass, make_config_entry({"climates": [{"id": 3, "hvac_mode_id": 50}]})
    )

    state = hass.states.get(ENTITY_ID)
    assert state.attributes[ATTR_HVAC_MODES] == [
        HVACMode.OFF,
        HVACMode.HEAT,
        HVACMode.COOL,
        HVACMode.HEAT_COOL,
    ]
    assert state.state == HVACMode.HEAT

    await hass.services.async_call(
        CLIMATE_DOMAIN,
        SERVICE_SET_HVAC_MODE,
        {ATTR_ENTITY_ID: ENTITY_ID, ATTR_HVAC_MODE: HVACMode.COOL},
        blocking=True,
    )
    await hass.async_block_till_done()

    assert any(
        call[0] == 50 and call[1].get(ValueType.MULTI_VALUE_SWITCH_STATE) == 2
        for call in mock_hub.api.set_calls
    )
    assert hass.states.get(ENTITY_ID).state == HVACMode.COOL


async def test_climate_auxiliary_features(hass: HomeAssistant, mock_hub) -> None:
    """Preset, fan, swing and target-humidity helpers map to their devices."""
    await setup_integration(
        hass,
        make_config_entry(
            {
                "climates": [
                    {
                        "id": 3,
                        "preset_mode_id": 6,
                        "fan_mode_id": 6,
                        "swing_mode_id": 6,
                        "swing_horizontal_mode_id": 6,
                        "target_humidity_id": 1,
                        "min_humidity": 20,
                        "max_humidity": 80,
                    }
                ]
            }
        ),
    )

    state = hass.states.get(ENTITY_ID)
    assert state.attributes["preset_modes"] == ["Off", "Party", "Relax"]
    assert state.attributes["fan_modes"] == ["Off", "Party", "Relax"]
    assert state.attributes["swing_modes"] == ["Off", "Party", "Relax"]
    assert state.attributes["min_humidity"] == 20
    assert state.attributes["max_humidity"] == 80

    for service, attribute, option, value in (
        (SERVICE_SET_PRESET_MODE, ATTR_PRESET_MODE, "Party", 1),
        (SERVICE_SET_FAN_MODE, ATTR_FAN_MODE, "Relax", 2),
        (SERVICE_SET_SWING_MODE, ATTR_SWING_MODE, "Party", 1),
        (SERVICE_SET_SWING_HORIZONTAL_MODE, ATTR_SWING_HORIZONTAL_MODE, "Relax", 2),
    ):
        await hass.services.async_call(
            CLIMATE_DOMAIN,
            service,
            {ATTR_ENTITY_ID: ENTITY_ID, attribute: option},
            blocking=True,
        )
        await hass.async_block_till_done()
        assert any(
            call[0] == 6
            and call[1].get(ValueType.MULTI_VALUE_SWITCH_STATE) == value
            for call in mock_hub.api.set_calls
        )
        assert hass.states.get(ENTITY_ID).attributes[attribute] == option

    await hass.services.async_call(
        CLIMATE_DOMAIN,
        SERVICE_SET_HUMIDITY,
        {ATTR_ENTITY_ID: ENTITY_ID, ATTR_HUMIDITY: 50},
        blocking=True,
    )
    await hass.async_block_till_done()
    assert (
        1,
        {ValueType.SWITCH_STATE: 1, ValueType.ANALOG_OUTPUT_DESIRED_VALUE: 0.5},
    ) in mock_hub.api.set_calls
    assert hass.states.get(ENTITY_ID).attributes[ATTR_HUMIDITY] == 50


async def test_range_climate(hass: HomeAssistant, mock_hub) -> None:
    """Two thermostats form one range climate entity."""
    make_device(mock_hub, SECOND_THERMOSTAT)
    await setup_integration(
        hass,
        make_config_entry(
            {
                "climates": [
                    {
                        "id": 3,
                        "range_high_thermostat_id": 3,
                        "range_low_thermostat_id": 54,
                    }
                ]
            }
        ),
    )

    state = hass.states.get(ENTITY_ID)
    assert state.attributes[ATTR_TARGET_TEMP_HIGH] == 22.0
    assert state.attributes[ATTR_TARGET_TEMP_LOW] == 21.0

    await hass.services.async_call(
        CLIMATE_DOMAIN,
        SERVICE_SET_TEMPERATURE,
        {
            ATTR_ENTITY_ID: ENTITY_ID,
            ATTR_TARGET_TEMP_HIGH: 24.0,
            ATTR_TARGET_TEMP_LOW: 18.0,
        },
        blocking=True,
    )
    await hass.async_block_till_done()

    assert any(
        call[0] == 54 and call[1].get(ValueType.TEMPERATURE_SET_POINT) == 18.0
        for call in mock_hub.api.set_calls
    )
    assert any(
        call[0] == 3 and call[1].get(ValueType.TEMPERATURE_SET_POINT) == 24.0
        for call in mock_hub.api.set_calls
    )


async def test_hvac_controller_rejects_invalid_input(mock_hub) -> None:
    """Unsupported HVAC modes raise a validation error, not a crash."""
    from custom_components.taphome.climate import create_hvac_controller

    make_device(mock_hub, HEATING_RELAY)

    static = create_hvac_controller(mock_hub, 3, 53, HVACMode.HEAT)
    with pytest.raises(ServiceValidationError):
        await static.async_set_hvac_mode(HVACMode.COOL)

    empty = create_hvac_controller(mock_hub, 3, None, None)
    with pytest.raises(ServiceValidationError):
        await empty.async_set_hvac_mode(HVACMode.HEAT)

    with pytest.raises(ValueError):
        create_hvac_controller(mock_hub, 3, 53, HVACMode.HEAT, hvac_mode_id=50)


def test_climate_config_backwards_compatibility() -> None:
    """Deprecated YAML config keys map onto the current option names."""
    from custom_components.taphome.climate import TapHomeClimateConfig

    config = TapHomeClimateConfig({"thermostat": 3, "heat": 53})
    assert config.id == 3
    assert config.hvac_switch_id == 53
    assert config.hvac_mode == HVACMode.HEAT

    config = TapHomeClimateConfig({"thermostat": 3, "cool": 53, "mode": 50})
    assert config.hvac_switch_id == 53
    assert config.hvac_mode == HVACMode.COOL
    assert config.hvac_mode_id == 50
