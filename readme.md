# TapHome Home Assistant integration

[TapHome](https://taphome.com/CZ/home) integration into [Home Assistant](https://www.home-assistant.io).

## Supported devices
- Lights - switch, brightness, RGB
- Covers - blinds, shades, garage doors
- Climates - thermostats
- Switches - power outlet, digital out
- Sensors - Humidity, Temperature, Variable, Motion, Generic reed contact, Electric counter (consumption, demand), Brightness, Co2, Wind speed, Pulse counter (total impulse, current hour impulse, frequency)

## Quick start

This is official [HACS](https://hacs.xyz) repository. So [use HACS](https://hacs.xyz/docs/basic/getting_started) to install it! Or you can
copy this folder to `<config_dir>/custom_components/taphome/` manually if you want.

Add TapHome entry in to your `configuration.yaml`. Configuration scheme is described in [wiki](https://github.com/martindybal/taphome-homeassistant/wiki/Configuration).

```yaml
taphome:
  cores:
    - token: 00000000-0000-0000-0000-000000000000
      lights:
        - 1
      covers:
        - 3
      climates:
        - thermostat: 14
          mode: 13
      switches:
        - 13
      sensors:
        - 8
      binary_sensors:
        - 18
```

## License
This repository is under the [GPL v3 with Commons Clause](https://github.com/martindybal/taphome-homeassistant/blob/main/LICENSE.md).

## Contributing
1. [Set up Home Assistant development environment](https://developers.home-assistant.io/docs/development_environment)
1. Clone this repository into `<config_dir>/custom_components/taphome/`
1. Find a [good first issue](https://github.com/martindybal/taphome-homeassistant/issues?q=is%3Aissue+is%3Aopen+label%3A"good+first+issue") for you.
1. Solve it and send me pull request :-)
