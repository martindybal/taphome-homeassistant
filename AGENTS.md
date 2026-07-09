# AGENTS.md

Guidance for coding agents (Claude Code, Codex, …) working in this repository.

## What this repository is

A [HACS](https://hacs.xyz/) custom integration that connects [TapHome](https://taphome.com) smart home devices to [Home Assistant](https://www.home-assistant.io). The repository root **is** the integration package — it gets copied/mounted into `config/custom_components/taphome/` of a Home Assistant instance. Domain: `taphome`, `iot_class: local_push`, versioned with CalVer in `manifest.json`. The integration targets the **Platinum** quality scale (see `docs/core-quality-scale.yaml` for the per-rule status drafted for the Core port).

## Commands

CI (`.github/workflows/ci.yaml`, Python 3.14 — current Home Assistant requires
`>=3.14.2`) runs these checks — run them locally before pushing:

```bash
python -m venv .venv && source .venv/bin/activate
pip install homeassistant ruff pylint pytest-homeassistant-custom-component taphome-sdk

python -m compileall -q .                                          # compile check
ruff check .                                                       # lint
pylint . --fail-under=9.5                                          # lint, min score 9.5 (config in pyproject.toml)
pytest tests --cov=custom_components.taphome                       # integration tests; keep coverage ≥95 % (Silver rule)
```

Use the `pytest` script, not `python -m pytest`: with `python -m` the repo root
lands on `sys.path` and its `select.py`/`time.py` shadow the stdlib. The same
shadowing breaks `python -m mypy` and similar tools when run **from** this
directory — run them from elsewhere.

Home Assistant can only be imported on Linux (it uses `fcntl`/`resource` and a
socket event-loop self-pipe), so the suite does not run on native Windows — use
a Linux box, WSL, or a `python:3.14` container: mount the repo **and its
`../taphome-sdk` sibling** under a common parent (e.g. `/work/...`), `pip
install -e /work/taphome-sdk`, then run pytest from the repo mount.
`pyproject.toml` holds only the pylint config (disables the HA-inherent false
positives; the repo is not a pip package).

**CI installs `taphome-sdk` from PyPI** (same as `manifest.json`
requirements). When a change here needs new SDK API, release the SDK first —
otherwise CI (and user installs) break. Locally, `sdk_locator.py` prefers the
sibling `../taphome-sdk/src` checkout, so code can run ahead of the released
SDK; don't let that mask an unreleased dependency.

Tests live in `tests/` (pytest-homeassistant-custom-component).
`tests/tests_common.py` maps the repo root to `custom_components.taphome`,
builds SDK devices from API-shaped fixture dicts (`make_device`) and fakes the
TapHome HTTP API in memory: `FakeTapHomeApi` records `set_calls`, mirrors
"desired" values to actual ones, serves discovery/all-values from
`discovery_definitions` (append to simulate a newly exposed device) and can
reject writes per device via `fail_devices`. `conftest.py` provides `mock_hub`
(patches `TapHomeHubFactory.async_connect` + `TapHomeApi.async_get_location`)
and `mock_config_entry`. Every platform has a `tests/test_<platform>.py`;
repair flows are covered in `tests/test_repairs.py`. `pytest.ini` sits in
`tests/` on purpose — the repo root is a package and must not become pytest's
rootdir.

The TapHome SDK lives in its own repository
(https://github.com/martindybal/taphome-sdk, PyPI package `taphome-sdk`);
`sdk_locator.py` loads it from a sibling `../taphome-sdk/src` checkout during
development (see `docs/development.md`). Its tests, ruff and mypy (strict) run
in that repository.

CI also runs HACS validation (`hacs/action`, category `integration`).

To run the integration for real: set up the [Home Assistant dev container](https://developers.home-assistant.io/docs/development_environment) and bind-mount this repo into `config/custom_components/taphome/` (see "Contributing" in `readme.md`).

## Home Assistant development context

Official developer docs: https://developers.home-assistant.io/docs/core/ — the authoritative reference for entity models, platform APIs, `manifest.json`, the issue/repairs registry, the quality scale, etc. Per-platform entity docs live under https://developers.home-assistant.io/docs/core/entity/ (e.g. `.../entity/light`, `.../entity/climate`).

A Context7 MCP server is configured in `.mcp.json` for up-to-date library docs. Use `resolve-library-id` with "Home Assistant" and then `query-docs` to pull current Home Assistant core documentation when working on platform code. Falling back to WebFetch against developers.home-assistant.io also works.

Home Assistant conventions that apply here:

- Entities never call APIs from property getters; they set `_attr_*` attributes and let HA read them.
- State updates are pushed: `should_poll` is `False` and `PARALLEL_UPDATES = 0` in every platform file.
- Entity action methods are decorated with `handle_taphome_errors` (below) so SDK failures surface as translated `HomeAssistantError`s; invalid user input raises `ServiceValidationError` (see the HVAC controllers in `climate.py`).
- Async: everything touching the network is `async`; use HA helpers (`entity_registry`, `area_registry`, `label_registry`, webhook, `config_validation as cv`).
- This integration is configured **via the UI** (config flow + options flow in `config_flow.py`, per-platform option metadata in `platform_descriptors.py`). Legacy YAML (`CONFIG_SCHEMA` in `__init__.py`) is deprecated and only imported into config entries on startup.
- Cores are **discovered via zeroconf**: they announce `_th-discovery._tcp.local.` with TXT records `Name`, `LocationId` (= the config-entry unique id) and `IpOnLocalNetwork`; `async_step_zeroconf` asks only for the token and refreshes the API URL of already configured local entries on rediscovery. The `AccessToken` TXT record is the app pairing token — unrelated to the API token, never use it. There is no SSDP and DHCP hostnames are not stable.
- The YAML-era core `id` is no longer offered in any UI form; `entry.data[CONF_ID]` of existing (YAML-imported) entries is still read because entity unique ids embed it — it goes away with the YAML removal.

## Architecture

Two layers:

1. **`taphome-sdk`** (separate repository, sibling checkout `../taphome-sdk`) — self-contained TapHome API client with no Home Assistant imports (only aiohttp); passes `mypy --strict` there.
2. **Repository root** — Home Assistant platform files (`light.py`, `climate.py`, `cover.py`, …) that bridge SDK devices to HA entities.

### taphome_sdk (in ../taphome-sdk/src/taphome_sdk)

- `taphome_api.py` — raw HTTP client (`TapHomeApi`) for the TapHome Core API (local `http://<ip>/api/TapHomeApi/v1` or cloud `https://api.taphome.com/...`).
- `exceptions.py` + `taphome_api.py`/`taphome_hub.py` — every SDK error inherits `TapHomeError`: `TapHomeAuthError`, `TapHomeConnectionError`, `ValueChangeFailedException` (raised when the Core rejects a change **or** returns no usable response — failures are never silently swallowed), `DeviceNotExposedError`, `DeviceTypeError`.
- `observable.py` — the eventing backbone: `Event` (C#-style, subscribe with `+=`; **replays the last value to new subscribers**) and `ObservableValue` (fires `changed(old, new)` only when the value actually changes).
- `device.py` + `device_*.py` — typed device classes, each with an observable `state`. `DeviceFactory.create_device` picks the class by which `ValueType`s the device supports (checked in priority order — e.g. `BLINDS_LEVEL` → `BidirectionalDevice`, `TEMPERATURE_SET_POINT` → `ThermostatDevice`).
- `taphome_hub.py` — `TapHomeHub` owns the device registry (`devices: dict[int, Device]`), connection state, and refresh loop. Refresh interval depends on `ApiConnectionType`: LOCAL 2s, CLOUD 20s, LOCAL_PUSH 60s (webhook received → switches to LOCAL_PUSH). `hub.get_typed_device(id, *types)` is the lookup used by platforms; it raises `DeviceNotExposedError` / `DeviceTypeError`. `hub.async_discover_new_devices()` re-runs discovery at runtime and registers newly exposed devices. `connection_state` is `HubConnectionState.CONNECTED`/`FAILED`/`AUTH_FAILED`/`DISCONNECTED`; poll failures log one warning, then debug until recovery.

### Integration layer (config-entry setup)

`__init__.py:async_setup_entry` (one entry per TapHome **core**):

1. Connects via `TapHomeHubFactory.async_connect` with HA's shared aiohttp session; `TapHomeAuthError` → `ConfigEntryAuthFailed` (starts reauth), anything else → `ConfigEntryNotReady` (retry with backoff).
2. Subscribes to `hub.connection_state`: entities are available only while CONNECTED; the loss and the recovery are each logged **once** (log-when-unavailable); a Repairs issue mirrors the outage; `AUTH_FAILED` at runtime starts the reauth flow.
3. Registers the Core as the hub device (with `configuration_url` to its local `/localapilog` page on local connections), registers the optional push webhook, removes registry entities whose device is no longer configured, and runs new-device detection. Detection is **event-driven**: the SDK surfaces device ids seen in incoming values (webhook or poll) that are not registered on `hub.new_device_ids`; `_subscribe_new_device_detection` reacts by resolving the metadata on demand (`hub.async_discover_new_devices`) — no periodic timer. It also runs once at setup (and thus every reload) to set the baseline and re-sync stale issues. Unknown exposed devices raise a fixable repair issue (`repairs.py:NewDeviceRepairFlow`, which reuses the `_TapHomeDeviceArchetypeFlow` type menu — the device is fixed, so it offers only the archetypes that device qualifies for, plus ignore); the known-device baseline lives in `entry.data[CONF_KNOWN_DEVICE_IDS]`.
4. Builds `add_entry_requests[domain] = [(subentry_id, AddEntryRequest), …]` from the entry's device subentries per the `DomainDefinition` list (one per HA platform; `button` and `event` share the `buttons` config key), stores everything in `entry.runtime_data` (`TapHomeRuntimeData`), registers the update listener (any options/subentry change → `async_schedule_reload`) and forwards to `PLATFORMS`.
5. Each platform's `async_setup_entry` calls `add_taphome_entities(...)` (`add_entry_request.py`) with a factory that resolves the SDK device via `hub.get_typed_device` and picks the entity class by device type (see `light.py:_create_light_entity` for the canonical pattern). A missing or mistyped device raises a Repairs issue instead of failing setup.

Legacy YAML (`CONFIG_SCHEMA` + `async_setup`) only imports an existing `taphome:` section into config entries and raises a deprecation issue.

### Per-device config: config subentries

Each exposed device is a **config subentry** (`subentry_type="device"`, constants in `const.py`); its `data` is the device-config dict plus a `SUBENTRY_DATA_PLATFORM` (`"platform"`) key naming the platform bucket (a former `options[<config_key>]` value, e.g. `switches`). Core-level config (zones, labels, webhook, enabled attributes) stays in `entry.options`. **`subentry.py` is the single source of truth for the subentry shape** — its unique-id format (`"{platform}:{id}"`), construction (`build_device_subentry[_data]`), iteration (`iter_device_subentries`) and extraction (`subentry_platform`, `device_config_from_subentry`) helpers are reused by every consumer; do not hand-build subentry dicts elsewhere.

- `__init__.py:_map_subentry_requests` builds the per-domain request lists from `entry.subentries`; `add_taphome_entities` adds each batch with `config_subentry_id=` so entities **and** their device belong to the subentry (that is what makes Edit/Delete appear on the device page).
- Add/edit/remove of a single device is the `TapHomeDeviceSubentryFlowHandler` (`config_flow.py`, registered via `async_get_supported_subentry_types`). Its add flow is **archetype-first**: a menu of user-facing device types (`DEVICE_ARCHETYPES` — light, switch, thermostat/controlled/range, per-value sensor/binary sensor, …), each opening a form with only that type's fields. Sensor archetypes create **one subentry per selected device value** (`value` key in the data; unique id `"{platform}:{id}:{value}"`); subentries without `value` keep the legacy auto-detect-all behavior. Reconfigure offers every field with the advanced ones in a collapsed section (`OptionField.advanced`), so archetypes are add-time templates only. The archetype steps live in the shared `_TapHomeDeviceArchetypeFlow` mixin, so the subentry flow's Add device and the options-flow **Add device** menu item are the same code (subclasses supply `_archetype_entry` and `_archetype_finish`). The setup wizard creates subentries in bulk (`async_create_entry(subentries=…)`). The options flow also has **Edit device**/**Remove device** steps that resolve an automation-style target (entity/device/area/label) to subentries; removal reviews the devices in a pre-checked multiselect. Every subentry mutation fires the entry's update listener → automatic reload.
- `async_migrate_entry` (`MINOR_VERSION` 2) converts pre-subentry entries: it moves each `options[<config_key>]` device into a subentry and re-homes the existing entity (`config_subentry_id`, unchanged unique id → history preserved) and device (`add_config_subentry_id`).

### Entity layer

- `entity.py:TapHomeEntity` is the base for all entities: builds `unique_id`, applies zone→area and category→label mappings via HA registries, exposes `taphome_*` extra state attributes (filterable via `enabled_attributes` config), and subscribes to `hub.connection_state` (drives `available`) and `device.state.changed` (drives state + `schedule_update_ha_state`). The unique id embeds a per-core segment (`TapHomeCoreConfig.unique_id_segment`): the location id for cores added after this was introduced (stored in `entry.data[CONF_CORE_UNIQUE_ID]` at creation, so different cores never collide), the legacy YAML `id` for imported cores, or nothing for older UI cores — never changed for existing entries, so history is preserved. `TapHomeCoreConfig.id` stays only for display/issues and the hub-device fallback.
- `entity.py:handle_taphome_errors` decorates every entity action method (`async_turn_on`, `async_set_*`, …): it translates SDK errors into `HomeAssistantError` with a translation key — `change_rejected` for `ValueChangeFailedException`, `communication_error` for other `TapHomeError`s (`exceptions` section in `translations/*.json`, all six languages).
- Value-scale converters live on `TapHomeEntity` as static methods (TapHome uses 0..1 floats; HA uses 0..255 bytes or 0..100 percent).
- `binary_sensor.py:TapHomeIsAliveSensor` is the Core connectivity sensor: a **diagnostic** entity attached to the hub device, named by its device class (no custom name).
- `taphome_config_entry.py` — frozen dataclasses for config (`TapHomeCoreConfig`, `AddEntryRequest`) and `TapHomeEntityConfig`, which platform-specific config classes subclass (e.g. `TapHomeLightConfig` adds `effect_id`).
- `taphome_issue_registry.py` — creates/clears HA Repairs issues (core unavailable, device not exposed, device type mismatch, new device found); issue ids are namespaced by `entry_id` so cores never collide, while `core_id` is only user-facing text; texts come from `translations/*.json`. `repairs.py` implements the fixable new-device flow; `diagnostics.py` provides entry- and device-level diagnostics (token redacted).

### Adding a new platform

Follow the existing pattern: platform file at root with `PARALLEL_UPDATES = 0`, a `TapHome<X>Config` class, entity class(es) inheriting `TapHomeEntity` + the HA entity class (action methods decorated with `handle_taphome_errors`), a `_create_*_entity` factory, and `async_setup_entry` calling `add_taphome_entities`; then register a `DomainDefinition` in `__init__.py`, add the config key to `const.py` **and the platform to `PLATFORMS`** (forgetting `PLATFORMS` means the platform never loads — this bug shipped once with `number`), add a `PlatformDescriptor` in `platform_descriptors.py`, write a `tests/test_<platform>.py`, and document it in `docs/user-guide.md`.

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
  instead of `translations/*.json`, `quality_scale.yaml` (draft with all
  tiers and exempt reasoning: `docs/core-quality-scale.yaml` in this repo),
- no `pyproject.toml` (Core uses its own pylint config); the Core copy is
  listed in `.strict-typing` and must pass Core's strict mypy,
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

- User-facing changes are recorded in `changelog.md` and the version bumped in `manifest.json` (CalVer, e.g. `2026.7.1`).
- `manifest.json` pins an exact `taphome-sdk` version; bumping it requires that SDK release to exist on PyPI first (SDK changes ship as a release with its own CHANGELOG entry).
- User-facing error/issue texts always go through translation keys; add new keys to **all six** `translations/*.json` files (en, cs, de, hu, it, sk).
- User docs live in `readme.md` (overview + install) and `docs/user-guide.md` (setup wizard, Configure dialog, webhook, automation examples, known limitations, troubleshooting, removal); keep them in sync with config-flow changes.
- Deprecated config options are not removed abruptly — they log an error explaining the migration (see `language` and `update_interval` handling in `__init__.py`).
