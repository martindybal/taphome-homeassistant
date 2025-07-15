# Changelog

## 2025.2.0
- Added support for `value_type` in sensor and binary sensor configurations, allowing users to define custom sensors for any device.

## 2025.7
- Added entity state attributes
    - `taphome_id` to easily find an entity in taphome.
    - `operation_mode` to indicate Auto or Manual mode.

## 2024.12.0
- Add support for new TapHome 2024.2 variable types
- TapHome 2024.2 exposes climathermostat service setting. So min/max temperature from config can be ignored.
- New Time entity type.
- Notify user when using device not exposed in TapHome API
- Improved communication with TapHome Core for better efficiency: data is now refreshed using webhook updates.

## 2024.8.0
- Introduce `close_threshold` for covers

## 2024.5.0
- New Valve entity type.
- New Humidifier entity type.
- Resolved breaking changes of Home Assistant Core

## 2023.5.0
- Dual whites support
- Discovery minimum and maximum temperature for climates
- Allow change color temperature without turn on light

## 2023.1.0
- New Fan entity type.
- Preserve existing tilt value when adjusting blind position

## 2021.3.1
- Webhooks (remote triggers from Taphome to force update of the whole Taphome context)
- Fix TapHomeElectricCounterElectricityDemandSensorType

## 2021.2.1-pre
- Support for new api endpoint `GetAllDevicesValues`
- Support for local api. Cloud api is not needed anymore
- Support for SelectEntity -> Multivalue switches
- Add TapHomeIsAliveSensor
- Logging

### braking changes
- Support Cores with 2021.3
    - Support for GetAllDevicesValues is needed

## 2020.1.1-pre
- Lights - switch, brightness, RGB
- Covers - blinds, shades, garage doors
- Multiple Core unit support
- Climates - thermostats
- Switches - power outlet, digital out
- Sensors - Humidity, Temperature, Variable, Motion, Generic reed contact, Electric counter (consumption, demand), Brightness, Co2, Wind speed, Pulse counter (total impulse, current hour impulse, frequency)
