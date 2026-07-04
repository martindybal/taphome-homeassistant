# Changelog

## 2026.7

- **Configuration via UI (config flow)**: The integration is now set up and managed entirely in the Home Assistant UI.
  - Add a core in _Settings → Devices & services_ with its IP address (or API URL) and token; each core is a separate integration entry validated against the core.
  - The **Configure** dialog covers everything YAML supported: core settings (webhook, description flags, exposed attributes), zone → area and category → label mapping with rename/ignore, per-platform device selection from devices discovered on the core, and advanced per-device options (device class, effects, climate controller ids, …).
  - **Reconfigure** updates the connection settings and an automatic re-authentication flow starts when the core rejects the token.
- **YAML configuration is deprecated**: An existing `taphome:` section is imported into the UI automatically on startup — entity unique IDs and history are preserved (the YAML core `id` is kept). A repair issue reminds you to remove the YAML section; changes made in YAML are no longer applied after the import.
- Reloading or removing an integration entry now properly stops polling and unregisters the webhook.
- Minimum supported Home Assistant version is 2025.3.
- The documented button `actions` value `long_press` (with underscore) is now parsed correctly.

## 2026.3

- New Number entity type. TapHome Variables can now be exposed as writable number entities, allowing users to read and write numeric values from Home Assistant. Min/max bounds from TapHome metadata are respected.

## 2026.2

- **Home Assistant 2026.2 Compatibility Fix**: Fixed entity ID format validation errors introduced in Home Assistant 2026.2 (PR #160302)
  - Home Assistant now enforces strict entity ID validation requiring `{domain}.{object_id}` format
  - Domain part cannot contain underscores or multiple dots
  - Refactored `TapHomeEntity` constructor to accept separate `domain` and `unique_id_determination` parameters for cleaner code
  - Entity IDs now correctly generated as `button.press_device_name` instead of invalid `button.PRESS.device_name`
  - Unique IDs remain unchanged to preserve existing entity configurations and automations

## 2025.8.1

- Support covers without `blindsIsMoving`, assuming target position is reached immediately.

## 2025.8

- Configure the TapHome core with `ip` or full `api_url`; conflicts raise an issue and `api_url` wins.
- Completely rewritten TapHome integration (SDK 2.0). The integration has been rebuilt on TapHome SDK 2.0, offering:
  - A full code rewrite for cleaner, more maintainable architecture
  - Smoother developer experience with simplified API methods
  - Improved communication with TapHome Core for faster updates and fewer failures
- Cover movement & direction detection
  Covers now report not only when they’re moving but also the direction (opening vs. closing) for more precise automations.
- `is_alive_sensor` enhancements
  The “alive” sensor can now distinguish between local LAN and cloud connections, helping you monitor connectivity health.
- Added button event entity using the same configuration as button entities.
- Added raining binary sensor and rain counter sensor for precipitation monitoring.

- New humidifier configuration options
  You can now bind additional sensors/switches to your humidifier entity via:
  - `action_id` – track current status of the device
  - `switch_id` – toggle the device on/off
  - `mode_id`   – The current active mode
  - `humidity_sensor_id` – The current humidity measured by the device
  - `device_class` – Set Home Assistant humidifier device class

- New fan configuration options
  - `preset_mode_id` – fan may have preset modes that automatically control the percentage speed or other functionality.

- Climate entity configuration rewritten
  - `hvac_switch_id` – digital output toggling the device on or off
  - `hvac_mode` – fixed HVAC mode used with `hvac_switch_id`
  - `hvac_mode_id` – multivalue switch providing selectable HVAC modes
  - `hvac_action_id` – multivalue switch reporting current HVAC action
  - `range_low_thermostat_id` / `range_high_thermostat_id` – thermostats for heat/cool range control
  - `preset_mode_id` – multivalue switch with preset modes
  - `fan_mode_id` – multivalue switch controlling fan mode
  - `swing_mode_id` – multivalue switch controlling vertical swing
  - `swing_horizontal_mode_id` – multivalue switch controlling horizontal swing
  - `target_humidity_id` – analog output controlling desired humidity
  - `min_humidity` / `max_humidity` – humidity limits for the humidifier
  - `precision` – override temperature reporting precision
  - `target_temperature_step` - The supported step size a target temperature can be increased or decreased HVAC can be configured in several ways:
  - `hvac_switch_id` + `hvac_mode` – static mode controlled by a switch
  - `hvac_switch_id` + `hvac_mode_id` – switch combined with selectable modes. In case you control the valve that can heat or cool.
  - `hvac_mode_id` only – modes control the device state directly
  - no hvac fields – entity works in read‑only mode
  Legacy keys (`thermostat`, `heat`, `cool`, `mode`, etc.) are still recognised and translated to the new options, so existing configurations remain functional.

- New light configuration options
  - `effect_id` - allows defining a multi-value switch in a light’s configuration that can trigger individual effects or entire light scenes.

- Added gas demand, water consumption, and water demand sensors.

## 2025.7

- Added detection of cover movement based on the blindsIsMoving state to enable tracking of opening and closing directions.
- Entity state attributes were added. This feature is enabled by default, and you can modify it via the `enabled_attributes` list in core configuration.
  - `taphome_id` to easily find an entity in taphome.
  - `taphome_name` the TapHome device name.
  - `taphome_description` the TapHome device description.
  - `taphome_category` the TapHome device category name.
  - `taphome_zone` the TapHome device zone name.
  - `taphome_operation_mode` to indicate Auto or Manual mode.
- Improve communication with the TapHome Core.
- Improve the way TapHome informs users about configuration and communication issues.

## 2025.2.0

- Added support for `value_type` in sensor and binary sensor configurations, allowing users to define custom sensors for any device.

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
