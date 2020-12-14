# TapHome Home Assistant integration

This is demo of integration [TapHome](https://taphome.com/CZ/home) into [Home Assistant](https://www.home-assistant.io).

## Supported devices
- Lights - switch, brightness, RGB
- Covers - blinds, shades, garage doors

## Installation

Copy this folder to `<config_dir>/custom_components/taphome/`.

Add the following entry in your `configuration.yaml`:

```yaml
taphome:
  token: 00000000-0000-0000-0000-000000000000
  lights:
    - 1
    - 2
  covers:
    - 3
    - 4
    - 5
```

You have to specify your token and id of your lights. For more information visit https://taphome.com/en/support/601227274

## License
This repository is under the [GPL v3 with Commons Clause](https://github.com/martindybal/taphome-homeassistant/blob/main/LICENSE.md).

## Contributing
1. [Set up Home Assistant development environment](https://developers.home-assistant.io/docs/development_environment)
1. Clone this repository into `<config_dir>/custom_components/taphome/`
1. Find a [good first issue](https://github.com/martindybal/taphome-homeassistant/issues?q=is%3Aissue+is%3Aopen+label%3A"good+first+issue") for you.
1. Solve it and send me pull request :-)
