# TapHome Home Assistant integration

[TapHome](https://taphome.com) integration into
[Home Assistant](https://www.home-assistant.io). Runs locally; state changes
arrive instantly through a TapHome webhook. Fully configured in the Home
Assistant UI — no YAML.

## Features

- **UI setup with a guided wizard** — add the core with its token, map
  TapHome zones to areas and categories to labels, pick devices and the
  platforms they appear as.
- **Local push** — instant state updates via webhook, with polling as a
  fallback; the TapHome cloud is supported too.
- **Managed from the Configure dialog** — add, edit and remove devices,
  change the connection or mappings at any time; removed devices clean up
  their entities automatically.
- **New device detection** — devices newly exposed in the TapHome API show
  up as repair issues that add them in two clicks.
- **Re-authentication flow** — a changed token is handled without removing
  and re-adding the integration.

## Supported platforms

Binary sensor, Button, Climate, Cover, Event, Fan, Humidifier, Light, Number,
Select (multi-value switch), Sensor, Switch, Time, Valve.

Changes are described in [changelog.md](/changelog.md).

## Installation

### HACS (recommended)

Search for **TapHome** in [HACS](https://hacs.xyz/) and install it. HACS
tracks updates and makes upgrading simple.

### Manual

1. Create a `custom_components` folder next to your `configuration.yaml` if
   it does not exist.
2. Inside `custom_components`, create a folder named `taphome`.
3. Copy all files from this repository into the `taphome` folder.

## Getting started

1. In the TapHome app, enable the **TapHome API**, expose the devices you
   want in Home Assistant, and copy the API token.
2. In Home Assistant, go to _Settings → Devices & services → Add integration
   → **TapHome**_, enter the token and the core's IP address, and follow the
   wizard.

The full documentation — per-device options, webhook setup, zone/label
mapping, migration from YAML and troubleshooting — is in the
**[user guide](/docs/user-guide.md)**.

### Do you need help?

I would be happy to configure your TapHome integration, integrate gadgets
from Home Assistant to TapHome or set up complex smart rules for you. Feel
free to contact me at [dybal.it](https://www.dybal.it/).

## License

This repository is under [GPL v3](LICENSE).

## Contributing

The integration depends on the [taphome-sdk](https://github.com/martindybal/taphome-sdk)
package; see [docs/development.md](/docs/development.md) for the repository
layout, local SDK loading and the checks CI runs (including the pytest
suite in `tests/`).

1. [Set up the Home Assistant development environment](https://developers.home-assistant.io/docs/development_environment)
2. Clone this repository (and `taphome-sdk` next to it)
3. Mount the repository into the dev container
```json
  "mounts": [
    "source=/Users/martin/Repos/taphome-homeassistant,target=${containerWorkspaceFolder}/config/custom_components/taphome/,type=bind,consistency=cached"
  ],
```
4. Rebuild the devcontainer (`Dev Containers: Rebuild Container`)
5. Find a [good first issue](https://github.com/martindybal/taphome-homeassistant/issues?q=is%3Aissue+is%3Aopen+label%3A"good+first+issue")
6. Solve it and send a pull request :-)
