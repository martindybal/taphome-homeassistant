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

## Running checks

Same checks as CI (`.github/workflows/ci.yaml`):

```bash
python -m venv .venv && source .venv/bin/activate
pip install homeassistant ruff pylint "taphome-sdk @ git+https://github.com/martindybal/taphome-sdk.git@main"

python -m compileall -q .
ruff check .
pylint . --fail-under=9.5
```

SDK tests, lint and typing run in the taphome-sdk repository (`pytest`,
`ruff check .`, `mypy`).

## Releasing the SDK

See the [taphome-sdk README](https://github.com/martindybal/taphome-sdk#releasing):
bump the version in `pyproject.toml`, update `CHANGELOG.md` and publish a
GitHub release with a `v*` tag — the release workflow publishes to PyPI via
trusted publishing. After the first release, add
`"requirements": ["taphome-sdk==<version>"]` to `manifest.json` so production
installs pull the SDK from PyPI.
