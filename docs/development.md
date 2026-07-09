# Local development

## Repository layout

The integration depends on the [taphome-sdk](https://github.com/martindybal/taphome-sdk)
Python package. In production it is installed from PyPI; during development it
is loaded from a local checkout so SDK changes apply immediately without
publishing a release.

Clone both repositories side by side, e.g. into `d:\repos`:

```
d:\repos\
├── taphome-homeassistant\   (this repository)
└── taphome-sdk\             (the SDK repository)
```

`sdk_locator.py` (imported first by the integration) picks the SDK up in this
order:

1. the directory set in the `TAPHOME_SDK_PATH` environment variable
   (must point to the `src` folder of the SDK checkout, e.g.
   `d:\repos\taphome-sdk\src`),
2. `../taphome-sdk/src` relative to this repository — the side-by-side layout
   above, found automatically with no configuration,
3. otherwise the `taphome_sdk` package installed by pip/Home Assistant is used.

Symlinking this repository into `config/custom_components/taphome` keeps the
side-by-side detection working — the locator resolves symlinks.

`sdk_locator.py` only affects **imports**. Home Assistant still checks the
`manifest.json` requirement (`taphome-sdk==<version>`) against the installed
package metadata before it loads the integration or opens any of its flows.
When the manifest pins a version that is not on PyPI yet (SDK changes not
released), install the local checkout into the Home Assistant environment so
the check passes without contacting PyPI:

```bash
pip install -e ../taphome-sdk   # inside the HA venv/container
```

or start Home Assistant with `hass --skip-pip-packages taphome-sdk`.

## Running checks

Same checks as CI (`.github/workflows/ci.yaml`):

```bash
python -m venv .venv && source .venv/bin/activate
pip install homeassistant ruff pylint pytest-homeassistant-custom-component taphome-sdk

python -m compileall -q .
ruff check .
pylint . --fail-under=9.5
pytest tests  # the pytest script, not python -m: repo root on sys.path would shadow stdlib select/time
```

The pytest suite in `tests/` covers the config flow (setup wizard, reauth,
reconfigure), the options flow, entry setup/unload, the webhook, YAML import
and the light, switch, sensor, cover, climate and select platforms. `tests/tests_common.py` builds SDK
devices from API-shaped fixtures and fakes the TapHome HTTP API in memory —
tests exercise the real SDK and integration code without any network.

SDK tests, lint and typing run in the taphome-sdk repository (`pytest`,
`ruff check .`, `mypy`).

`docs/mock_core/` contains a small mock TapHome API server useful for manual
testing against a running Home Assistant.

## Testing zeroconf discovery

Real cores announce `_th-discovery._tcp.local.` on the LAN, but multicast
does not reach a Home Assistant instance running behind Docker Desktop/WSL2
NAT (typical for a dev instance on Windows), so the discovery card never
appears there no matter what the integration does.

`docs/mock_core/announce_discovery.py` replays the announcement from inside
the same environment as Home Assistant, where multicast loops back:

```bash
# inside the HA container/venv — announce a real core:
python docs/mock_core/announce_discovery.py --ip 192.168.1.3 \
    --name "My Home" --location-id <location guid>

# or announce the mock API server (defaults match its fixtures):
python docs/mock_core/announce_discovery.py --ip 127.0.0.1
```

The discovery card appears within seconds; confirming it talks to the
announced IP over plain HTTP, which passes through NAT fine. A fully real
end-to-end test (core announcement → card) needs Home Assistant with a real
presence on the LAN — e.g. a Linux host/VM with host networking or a bridged
adapter.

## Releasing the SDK

See the [taphome-sdk README](https://github.com/martindybal/taphome-sdk#releasing):
bump the version in `pyproject.toml`, update `CHANGELOG.md` and publish a
GitHub release with a `v*` tag — the release workflow publishes to PyPI via
trusted publishing. After each release, bump
`"requirements": ["taphome-sdk==<version>"]` in `manifest.json` so production
installs pull the new SDK from PyPI.
