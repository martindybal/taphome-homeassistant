# Changelog

## 2026.7.1

Quality-scale improvements on the road to Home Assistant Core:

- **Automatic discovery**: TapHome Cores on the local network are now discovered via mDNS/zeroconf and appear in _Settings → Devices & services_ on their own — click Add, enter the API token, done. When a configured Core changes its IP address, discovery updates the connection automatically (deliberate cloud connections are left untouched).
- **The optional core `id` field was removed from the UI forms** (add, reconfigure, core settings). It was a YAML-era concept for telling cores apart; entries are now identified by their location. Existing entries that have an id keep it internally, so entity ids and history are unaffected.
- **Cores added from now on embed their location id in entity unique ids**, so two cores can never produce colliding entities (previously UI-added cores had no discriminator). Existing entries are untouched — their unique ids, history and automations are preserved exactly.

- **Translated error messages for failed actions**: when the Core rejects a change or cannot be reached while controlling an entity, the service call now fails with a translated, actionable error message instead of a raw SDK traceback. Setting an HVAC mode a thermostat does not support reports a proper validation error.
- **Quieter, clearer connection logging**: losing the connection to the Core logs a single message and another one on recovery; the SDK logs the first poll failure as a warning and further ones only at debug level (no more one error per poll cycle).
- **Runtime re-authentication**: if the Core starts rejecting the token while Home Assistant is running, the re-authentication flow starts automatically (previously this only happened at startup).
- **Live new-device detection**: a device exposed in the TapHome app is noticed the moment its first value arrives (via webhook or the regular poll), not only after a restart or reload; each still raises the fixable repair issue. This replaces the previous periodic re-scan.
- **New-device repair flow is now a device-type picker**: instead of a bare platform dropdown, adding a newly found device starts the same guided "Add device" flow — choose which of the types the device supports (thermostat / controlled / range, sensor, binary sensor, light, switch, …), then its options. Per-value sensors are supported here too.
- Fixed: the **Number** device type could not be added from the Add device menu (a missing platform descriptor made it error out).
- **The is-alive sensor is a proper diagnostic entity**: it belongs to the Core hub device, is categorized as diagnostic and takes the standard "Connectivity" name (its unique id is unchanged, so history is preserved; the displayed name regenerates unless you renamed it earlier).
- **Fixed: number entities were never created** — the `number` platform was missing from the platform list after the config-entry conversion.
- All platforms declare `PARALLEL_UPDATES`; new tests cover the button, event, fan, humidifier, number, time and valve platforms and the new-device repair flow.
- **Migration is now idempotent**: a config entry whose subentry migration was interrupted (or a YAML core that listed the same device twice) no longer gets stuck — the migration skips devices that already have a subentry.
- The rarely used per-device `unique_id` YAML option is no longer honored; a device exposed on a platform always gets the standard generated entity id. (If you set custom `unique_id`s in YAML, those entities regenerate once on upgrade and lose their prior history.)
- Repair issues (core unavailable, device not exposed / type mismatch) are namespaced per config entry, so they no longer collide between two cores.
- Requires [taphome-sdk 1.1.0](https://github.com/martindybal/taphome-sdk/blob/main/CHANGELOG.md).

## 2026.7

- **Devices and Home Assistant naming**: every TapHome device is now a device in the Home Assistant device registry (with the Core as its hub); entities take the device name and the TapHome zone pre-fills the suggested area. Configured zone → area and category → label mappings are applied to the device itself (the category label is added to the entity as well). The `use description as entity id/name` options were removed — rename entities and devices in the Home Assistant UI. Entity unique ids (and therefore history and automations) are unchanged; displayed names may regenerate unless you renamed them earlier.
- **Manage devices from the device page**: each exposed TapHome device is now a config subentry of the Core, so a single device can be edited (**⋮ → Edit**) or removed (**⋮ → Delete**) directly from its device page, and the Core entry page has **+ Add device**. The Configure dialog keeps the bulk **Add devices** picker plus the zone/label mappings; its separate _Edit devices_ and _Remove devices_ steps are removed (superseded by the per-device actions). Existing configurations migrate automatically to subentries — entity unique ids, history and automations are preserved.
- **Add devices by type**: **+ Add device** (and the Configure dialog's _Add device_, which opens the identical flow) starts from a menu of device types (light, switch, cover, thermostat, controlled thermostat, range thermostat, sensor, …) and each type asks only for what it needs. Sensors and binary sensors pick a device and then **which of its values** to expose — every value becomes its own entry that can be edited or removed individually. Editing still offers every option, with the advanced ones collapsed, so a device can be converted between variants (e.g. a simple thermostat into a controlled one). The old bulk _Add devices_ picker remains only in the initial setup wizard.
- **Edit/Remove device in the Configure dialog**: find a configured device by picking the device or any of its entities; removal shows a summary of configurations and entities first.
- **Zone → area and category → label mapping behaves like the YAML era again**: an unmapped zone/category uses its TapHome name, a mapped one resolves to the target area/label (created when missing — YAML name targets work), and `ignore` assigns nothing (no more stray areas for ignored zones). Labels are applied for **every** category again. The Zones/Labels mapping forms gained an **Ignore** checkbox.
- Subentries imported from YAML are titled with the API id and discovery metadata (`TapHome api device 15 - Sleep, Ložnice, Akce`) instead of the bare id.
- **Diagnostics**: the Core and every device now offer **Download diagnostics** (from the integration entry and each device page) — a redacted dump of the connection, device metadata and current values, useful for bug reports.
- **Core link and cleanup**: the Core hub device links to its local log page (`http://<core-ip>/localapilog`, local connections only), and a device the Core no longer exposes can be deleted from its device page.

- **Test suite**: the integration now has automated tests (config flow wizard, options flow, reauth/reconfigure, entry setup/unload, webhook push, YAML import, light/switch/sensor/cover/climate/select platforms) running in CI.
- **Documentation rewritten for the UI era**: the YAML reference (`configuration.md`) and the YAML config generator were removed; the new [user guide](docs/user-guide.md) documents the setup wizard, the Configure dialog, webhook setup, migration from YAML and troubleshooting.

- **The TapHome SDK moved to its own repository and PyPI package** [`taphome-sdk`](https://github.com/martindybal/taphome-sdk); it is no longer bundled inside the integration. Production installs use the PyPI package (via `manifest.json` requirements once published); developers can keep a local `taphome-sdk` checkout next to this repository — see [docs/development.md](docs/development.md).

- **Configuration via UI (config flow)**: The integration is now set up and managed entirely in the Home Assistant UI.
  - Add a core in _Settings → Devices & services_ with its token and either its IP address or the TapHome cloud; core settings (webhook, description flags, exposed attributes) can be filled in right when adding. Each core is a separate integration entry validated against the core.
  - The **Configure** dialog covers everything YAML supported: **Core settings** (connection, webhook, description flags, exposed attributes — the same fields as when adding the core), zone → area and category → label mapping with rename/ignore, adding, editing and removing devices via searchable pickers that show each device's room/zone, and advanced per-device options (device class, effects, climate controller ids, …).
  - **Reconfigure** and **Configure → Core settings** both show the same connection and core settings fields, so the connection can be changed from either place; an automatic re-authentication flow also starts when the core rejects the token.
  - The button that starts the setup now reads **Add TapHome Core** instead of the generic Home Assistant "Add hub".
- **YAML configuration is deprecated**: An existing `taphome:` section is imported into the UI automatically on startup — entity unique IDs and history are preserved (the YAML core `id` is kept). A repair issue reminds you to remove the YAML section; changes made in YAML are no longer applied after the import.
- Reloading or removing an integration entry now properly stops polling and unregisters the webhook.
- Removing a device from the configuration also removes its entities from the entity registry — no manual cleanup in Home Assistant is needed.
- New devices exposed in the TapHome API (found when the integration is reloaded or Home Assistant restarts) raise a repair issue that lets you add the device — pick the platform to expose it as, or ignore it so it is not reported again.
- The **Add devices** picker no longer pre-selects a device that is already used as another device's helper (for example a thermostat's HVAC switch); it can still be selected manually to expose it on its own.
- Sensor and binary sensor types are detected automatically; their per-device options are now collapsed as advanced (and skipped in the new-device repair flow), so they are out of the way but still available to override.
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
