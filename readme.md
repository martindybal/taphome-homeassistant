# TapHome Home Assistant integration

[TapHome](https://taphome.com/CZ/home) integration into [Home Assistant](https://www.home-assistant.io).

## Supported devices
- Climates - thermostats
- Covers - blinds, shades, garage doors
- Lights - switch, brightness, RGB
- Sensors - Humidity, Temperature, Variable, Motion, Generic reed contact, Electric counter (consumption, demand), Brightness, Co2, Wind speed, Pulse counter (total impulse, current hour impulse, frequency)
- Switches - power outlet, digital out

## Installation

### Install with HACS (recomended)
Do you you have HACS installed? Just search for TapHome and install it direct from HACS. HACS will keep track of updates and you can easly upgrade TapHome to latest version.

### Install manually

1. Install this platform by creating a `custom_components` folder in the same folder as your configuration.yaml, if it doesn't already exist.
1. Create another folder `taphome` in the `custom_components` folder. Copy all files from this repository into the `taphome` folder.

## Configuration
The configuration is described in more detail in the [wiki](https://github.com/martindybal/taphome-homeassistant/wiki/Configuration)

1. Use [config-generator](https://www.dybal.it/taphome-homeassistant/config-generator/) to generate your config
1. Copy config to your `configuration.yaml`

**If you used first preview of this component (2020.1.1-pre). Your TapHome entities'll duplicate after update. Please follow next steps**
1. Disable taphome (comment `taphome` section in your `configuration.yaml`)
1. Restart Home Assistant Core
1. Remove all TapHome entities
1. Uncomment `taphome` section in your `configuration.yaml`
1. Restart Home Assistant Core again

Home Assistant entities'll recreat with same `entity_id` (If you're not change the name of taphome device in cloudapi setting). So you don't have to change your dashbords or scripts


## License
This repository is under the [GPL v3 with Commons Clause](https://github.com/martindybal/taphome-homeassistant/blob/main/LICENSE.md).

## Contributing
1. [Set up Home Assistant development environment](https://developers.home-assistant.io/docs/development_environment)
1. Clone this repository into `<config_dir>/custom_components/taphome/`
1. Find a [good first issue](https://github.com/martindybal/taphome-homeassistant/issues?q=is%3Aissue+is%3Aopen+label%3A"good+first+issue") for you.
1. Solve it and send me pull request :-)
