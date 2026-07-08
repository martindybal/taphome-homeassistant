# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this repository is

A [HACS](https://hacs.xyz/) custom integration that connects [TapHome](https://taphome.com) smart home devices to [Home Assistant](https://www.home-assistant.io). The repository root **is** the integration package — it gets copied/mounted into `config/custom_components/taphome/` of a Home Assistant instance. Domain: `taphome`, `iot_class: local_push`, versioned with CalVer in `manifest.json`.

## Commands

CI (`.github/workflows/ci.yaml`, Python 3.14 — current Home Assistant requires
`>=3.14.2`) runs these checks — run them locally before pushing:

```bash
python -m venv .venv && source .venv/bin/activate
pip install homeassistant ruff pylint pytest-homeassistant-custom-component taphome-sdk

python -m compileall -q .                                          # compile check
ruff check .                                                       # lint
pylint . --fail-under=9.5                                          # lint, min score 9.5 (config in pyproject.toml)
pytest tests                                                       # integration tests (use the pytest script, not python -m: the repo root on sys.path would shadow stdlib select/time)
```

Home Assistant can only be imported on Linux (it uses `fcntl`/`resource` and a
socket event-loop self-pipe), so the suite does not run on native Windows — use
a Linux box, WSL, or a `python:3.14` container (mount the repo and its
`../taphome-sdk` sibling). `pyproject.toml` holds only the pylint config
(disables the HA-inherent false positives; the repo is not a pip package).

Tests live in `tests/` (pytest-homeassistant-custom-component). `tests/tests_common.py` maps the repo root to `custom_components.taphome`, builds SDK devices from API-shaped fixture dicts and fakes the TapHome HTTP API in memory (`FakeTapHomeApi`); `conftest.py` provides `mock_hub` (patches `TapHomeHubFactory.async_connect` + `TapHomeApi.async_get_location`) and `mock_config_entry`. `pytest.ini` sits in `tests/` on purpose — the repo root is a package and must not become pytest's rootdir.

The TapHome SDK lives in its own repository (https://github.com/martindybal/taphome-sdk, PyPI package `taphome-sdk`); `sdk_locator.py` loads it from a sibling `../taphome-sdk/src` checkout during development (see `docs/development.md`). Its tests, ruff and mypy run in that repository.

CI also runs HACS validation (`hacs/action`, category `integration`).

To run the integration for real: set up the [Home Assistant dev container](https://developers.home-assistant.io/docs/development_environment) and bind-mount this repo into `config/custom_components/taphome/` (see "Contributing" in `readme.md`).

## Home Assistant development context

Official developer docs: https://developers.home-assistant.io/docs/core/ — the authoritative reference for entity models, platform APIs, `manifest.json`, the issue/repairs registry, etc. Per-platform entity docs live under https://developers.home-assistant.io/docs/core/entity/ (e.g. `.../entity/light`, `.../entity/climate`).

A Context7 MCP server is configured in `.mcp.json` for up-to-date library docs. Use `resolve-library-id` with "Home Assistant" and then `query-docs` to pull current Home Assistant core documentation when working on platform code. Falling back to WebFetch against developers.home-assistant.io also works.

Home Assistant conventions that apply here:

- Entities never call APIs from property getters; they set `_attr_*` attributes and let HA read them.
- State updates are pushed: `should_poll` is `False` on all entities.
- Async: everything touching the network is `async`; use HA helpers (`entity_registry`, `area_registry`, `label_registry`, webhook, `config_validation as cv`).
- This integration is configured **via the UI** (config flow + options flow in `config_flow.py`, per-platform option metadata in `platform_descriptors.py`). Legacy YAML (`CONFIG_SCHEMA` in `__init__.py`) is deprecated and only imported into config entries on startup.

## Architecture

Two layers:

1. **`taphome_sdk/`** — self-contained TapHome API client with no Home Assistant imports (only aiohttp). mypy runs only on this package.
2. **Repository root** — Home Assistant platform files (`light.py`, `climate.py`, `cover.py`, …) that bridge SDK devices to HA entities.

### taphome_sdk

- `taphome_api.py` — raw HTTP client (`TapHomeApi`) for the TapHome Core API (local `http://<ip>/api/TapHomeApi/v1` or cloud `https://api.taphome.com/...`).
- `observable.py` — the eventing backbone: `Event` (C#-style, subscribe with `+=`; **replays the last value to new subscribers**) and `ObservableValue` (fires `changed(old, new)` on assignment).
- `device.py` + `device_*.py` — typed device classes, each with an observable `state`. `DeviceFactory.create_device` picks the class by which `ValueType`s the device supports (checked in priority order — e.g. `BLINDS_LEVEL` → `BidirectionalDevice`, `TEMPERATURE_SET_POINT` → `ThermostatDevice`).
- `taphome_hub.py` — `TapHomeHub` owns the device registry (`devices: dict[int, Device]`), connection state, and refresh loop. Refresh interval depends on `ApiConnectionType`: LOCAL 2s, CLOUD 20s, LOCAL_PUSH 60s (webhook received → switches to LOCAL_PUSH). `hub.get_typed_device(id, *types)` is the lookup used by platforms; it raises `DeviceNotExposedError` / `DeviceTypeError`.

### Integration layer (setup flow)

`__init__.py:async_setup`:

1. Validates YAML config; supports multiple TapHome **cores** (hubs), each with its own token/URL/webhook (a core `id` is required when there is more than one).
2. Per core: `TapHomeHubFactory.async_connect` discovers all devices up front, registers an optional HA webhook for push updates, and builds an `AddEntryRequest(hass, core_config, entity_config, hub)` per configured entity.
3. Requests are grouped by a `DomainDefinition` list (one per HA platform; note `button` and `event` share the `buttons` config key), stashed in `hass.data["taphome"][config_key]`, then `load_platform` triggers each platform file.
4. Each platform's `setup_platform` calls `add_taphome_entities(...)` (`add_entry_request.py`) with a factory that resolves the SDK device via `hub.get_typed_device` and picks the entity class by device type (see `light.py:_create_light_entity` for the canonical pattern).

### Per-device config: config subentries

Each exposed device is a **config subentry** (`subentry_type="device"`, constants in `const.py`); its `data` is the device-config dict plus a `SUBENTRY_DATA_PLATFORM` (`"platform"`) key naming the platform bucket (a former `options[<config_key>]` value, e.g. `switches`). Core-level config (zones, labels, webhook, enabled attributes) stays in `entry.options`. **`subentry.py` is the single source of truth for the subentry shape** — its unique-id format (`"{platform}:{id}"`), construction (`build_device_subentry[_data]`), iteration (`iter_device_subentries`) and extraction (`subentry_platform`, `device_config_from_subentry`) helpers are reused by every consumer; do not hand-build subentry dicts elsewhere.

- `__init__.py:_map_subentry_requests` builds `add_entry_requests[domain] = [(subentry_id, AddEntryRequest), …]` from `entry.subentries`; `add_taphome_entities` adds each batch with `config_subentry_id=` so entities **and** their device belong to the subentry (that is what makes Edit/Delete appear on the device page).
- Add/edit/remove of a single device is the `TapHomeDeviceSubentryFlowHandler` (`config_flow.py`, registered via `async_get_supported_subentry_types`). Its add flow is **archetype-first**: a menu of user-facing device types (`DEVICE_ARCHETYPES` — light, switch, thermostat/controlled/range, per-value sensor/binary sensor, …), each opening a form with only that type's fields. Sensor archetypes create **one subentry per selected device value** (`value` key in the data; unique id `"{platform}:{id}:{value}"`); subentries without `value` keep the legacy auto-detect-all behavior. Reconfigure offers every field with the advanced ones in a collapsed section (`OptionField.advanced`), so archetypes are add-time templates only. The archetype steps live in the shared `_TapHomeDeviceArchetypeFlow` mixin, so the subentry flow's Add device and the options-flow **Add device** menu item are the same code (subclasses supply `_archetype_entry` and `_archetype_finish`). The setup wizard creates subentries in bulk (`async_create_entry(subentries=…)`). The options flow also has **Edit device**/**Remove device** steps that resolve an automation-style target (entity/device/area/label) to subentries; removal reviews the devices in a pre-checked multiselect. Every subentry mutation fires the entry's update listener → automatic reload.
- `async_migrate_entry` (`MINOR_VERSION` 2) converts pre-subentry entries: it moves each `options[<config_key>]` device into a subentry and re-homes the existing entity (`config_subentry_id`, unchanged unique id → history preserved) and device (`add_config_subentry_id`).

### Entity layer

- `taphome_entity.py:TapHomeEntity` is the base for all entities: builds `unique_id`, applies zone→area and category→label mappings via HA registries, exposes `taphome_*` extra state attributes (filterable via `enabled_attributes` config), and subscribes to `hub.connection_state` (drives `available`) and `device.state.changed` (drives state + `schedule_update_ha_state`).
- Value-scale converters live on `TapHomeEntity` as static methods (TapHome uses 0..1 floats; HA uses 0..255 bytes or 0..100 percent).
- `taphome_config_entry.py` — frozen dataclasses for config (`TapHomeCoreConfig`, `AddEntryRequest`) and `TapHomeEntityConfig`, which platform-specific config classes subclass (e.g. `TapHomeLightConfig` adds `effect_id`).
- `taphome_issue_registry.py` — creates/clears HA Repairs issues (core unavailable, conflicting `ip`+`api_url` config); user-facing texts come from `translations/*.json`.

### Adding a new platform

Follow the existing pattern: platform file at root with a `TapHome<X>Config` class, entity class(es) inheriting `TapHomeEntity` + the HA entity class, a `_create_*_entity` factory, and `async_setup_entry` calling `add_taphome_entities`; then register a `DomainDefinition` in `__init__.py`, add the config key to `const.py` and `PLATFORMS`, add a `PlatformDescriptor` in `platform_descriptors.py`, and document it in `docs/user-guide.md`.

## Keeping the Home Assistant Core port in sync

This repository is the **source of truth**. The integration is being upstreamed
to Home Assistant Core (fork: martindybal/home-assistant-core, branch
`taphome`, PR #1); the Core copy in `homeassistant/components/taphome` is a
conversion of this repo. Until the Core PR is merged, every change here must
be mirrored there. Intentional differences of the Core copy (do NOT port back):

- no YAML support (`CONFIG_SCHEMA`, `async_setup` import shim, `async_step_import`,
  `resolve_api_url`, `_normalize_device_config`, `_yaml_core_to_options`,
  `_yaml_device_subentries`, YAML fallback unique ids, per-device `unique_id`
  option, `translations.py` `YAML_DEPRECATED`),
- no `sdk_locator.py` (Core installs `taphome-sdk` from PyPI only),
- no `from __future__ import annotations` (banned in Core; this repo needs it
  on Python < 3.14),
- Core `manifest.json` (no `version`, has `quality_scale`), `strings.json`
  instead of `translations/*.json`, `quality_scale.yaml`,
- no `pyproject.toml` (Core uses its own pylint config),
- tests live in `tests/components/taphome` with `tests.common.MockConfigEntry`
  and helpers in the test package `__init__.py`,
- the Core copy carries `@override` decorators and identity (`is`) enum
  comparisons required by Core's mypy configuration.

`diagnostics.py` (config-entry + per-device diagnostics, token redacted),
`entity.py:hub_device_id` (shared Core-hub identifier), the hub device's
`configuration_url` (the Core's local `/localapilog` page, local API only) and
`async_remove_config_entry_device` (removes a device the Core no longer exposes)
are portable and should be mirrored to Core.

## Conventions

- User-facing changes are recorded in `changelog.md` and the version bumped in `manifest.json` (CalVer, e.g. `2026.2.0`).
- User docs live in `readme.md` (overview + install) and `docs/user-guide.md` (setup wizard, Configure dialog, webhook, troubleshooting); keep them in sync with config-flow changes.
- Deprecated config options are not removed abruptly — they log an error explaining the migration (see `language` and `update_interval` handling in `__init__.py`).
