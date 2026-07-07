# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this repository is

A [HACS](https://hacs.xyz/) custom integration that connects [TapHome](https://taphome.com) smart home devices to [Home Assistant](https://www.home-assistant.io). The repository root **is** the integration package — it gets copied/mounted into `config/custom_components/taphome/` of a Home Assistant instance. Domain: `taphome`, `iot_class: local_push`, versioned with CalVer in `manifest.json`.

## Commands

CI (`.github/workflows/ci.yaml`, Python 3.12) runs these checks — run them locally before pushing:

```bash
python -m venv .venv && source .venv/bin/activate
pip install homeassistant ruff pylint pytest-homeassistant-custom-component taphome-sdk

python -m compileall -q .                                          # compile check
ruff check .                                                       # lint
pylint . --fail-under=9.5                                          # lint, min score 9.5
pytest tests                                                       # integration tests (use the pytest script, not python -m: the repo root on sys.path would shadow stdlib select/time)
```

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

### Entity layer

- `taphome_entity.py:TapHomeEntity` is the base for all entities: builds `unique_id`, applies zone→area and category→label mappings via HA registries, exposes `taphome_*` extra state attributes (filterable via `enabled_attributes` config), and subscribes to `hub.connection_state` (drives `available`) and `device.state.changed` (drives state + `schedule_update_ha_state`).
- Value-scale converters live on `TapHomeEntity` as static methods (TapHome uses 0..1 floats; HA uses 0..255 bytes or 0..100 percent).
- `taphome_config_entry.py` — frozen dataclasses for config (`TapHomeCoreConfig`, `AddEntryRequest`) and `TapHomeEntityConfig`, which platform-specific config classes subclass (e.g. `TapHomeLightConfig` adds `effect_id`).
- `taphome_issue_registry.py` — creates/clears HA Repairs issues (core unavailable, conflicting `ip`+`api_url` config); user-facing texts come from `translations/*.json`.

### Adding a new platform

Follow the existing pattern: platform file at root with a `TapHome<X>Config` class, entity class(es) inheriting `TapHomeEntity` + the HA entity class, a `_create_*_entity` factory, and `async_setup_entry` calling `add_taphome_entities`; then register a `DomainDefinition` in `__init__.py`, add the config key to `const.py` and `PLATFORMS`, add a `PlatformDescriptor` in `platform_descriptors.py`, and document it in `docs/user-guide.md`.

## Conventions

- User-facing changes are recorded in `changelog.md` and the version bumped in `manifest.json` (CalVer, e.g. `2026.2.0`).
- User docs live in `readme.md` (overview + install) and `docs/user-guide.md` (setup wizard, Configure dialog, webhook, troubleshooting); keep them in sync with config-flow changes.
- Deprecated config options are not removed abruptly — they log an error explaining the migration (see `language` and `update_interval` handling in `__init__.py`).
