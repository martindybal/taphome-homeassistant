# TapHome Home Assistant integration

[TapHome](https://taphome.com/CZ/home) integration into [Home Assistant](https://www.home-assistant.io). The integration runs locally, and status updates are immediate thanks to the TapHome webhook to Home Assistant.

## Supported platforms

- Binary sensor
- Button
- Climate
- Cover
- Event
- Fan
- Humidifier
- Light
- Select (multi value switch)
- Sensor
- Switch
- Time
- Valve

## Installation

### Install with HACS (recommended)
If you have [HACS](https://hacs.xyz/) installed, search for **TapHome** and install it directly. HACS tracks updates and makes upgrading simple.

### Install manually

1. Create a `custom_components` folder next to your `configuration.yaml` if it does not exist.
2. Inside `custom_components`, create a folder named `taphome`.
3. Copy all files from this repository into the `taphome` folder.

## Configuration
The configuration is described in detail in the [wiki](https://github.com/martindybal/taphome-homeassistant/wiki/Configuration).

### Do you need help?
I would be happy to configure your TapHome integration, integrate gadgets from Home Assistant to TapHome or set up complex smart rules for you. Feel free to contact me [dybal.it](https://www.dybal.it/).

## License
This repository is under the [GPL v3 with Commons Clause](LICENSE.md).

## Contributing
1. [Set up Home Assistant development environment](https://developers.home-assistant.io/docs/development_environment)
2. Clone this repository
3. Mount repository into dev container
```json
  "mounts": [
    "source=/Users/martin/Repos/taphome-homeassistant,target=${containerWorkspaceFolder}/config/custom_components/taphome/,type=bind,consistency=cached"
  ],
```
4. Rebuild the devcontainer (`Dev Containers: Rebuild Container`)
5. Find a [good first issue](https://github.com/martindybal/taphome-homeassistant/issues?q=is%3Aissue+is%3Aopen+label%3A"good+first+issue") for you
6. Solve it and send a pull request :-)
