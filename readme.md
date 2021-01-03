# TapHome Home Assistant integration

[TapHome](https://taphome.com/CZ/home) integration into [Home Assistant](https://www.home-assistant.io).

## Supported devices
- Lights - switch, brightness, RGB
- Covers - blinds, shades, garage doors
- Climates - thermostats
- Switches - power outlet, digital out
- Sensors - Humidity, Temperature, Variable, Motion, Generic reed contact, Electric counter (consumption, demand), Brightness, Co2, Wind speed, Pulse counter (total impulse, current hour impulse, frequency)

## Installation

Copy this folder to `<config_dir>/custom_components/taphome/`.

Add the following entry in your `configuration.yaml`:

```yaml
taphome:
  cores:
    - token: 00000000-0000-0000-0000-000000000000
      lights:
        - 1
        - 2
      covers:
        - 3
        - 4
        - 5
      climates:
        - thermostat: 14
          mode: 13
      switches:
        - 13
      sensors:
        - 8
        - 9
        - 10
        - 14
        - 15
        - 16
        - 17
      binary_sensors:
        - 18
```

You have to specify your token and id of your lights. For more information visit https://taphome.com/en/support/601227274

## License
This repository is under the [GPL v3 with Commons Clause](https://github.com/martindybal/taphome-homeassistant/blob/main/LICENSE.md).

## Contributing
1. [Set up Home Assistant development environment](https://developers.home-assistant.io/docs/development_environment)
1. Clone this repository into `<config_dir>/custom_components/taphome/`
1. Find a [good first issue](https://github.com/martindybal/taphome-homeassistant/issues?q=is%3Aissue+is%3Aopen+label%3A"good+first+issue") for you.
1. Solve it and send me pull request :-)

## Documentation
### Multiple core units
You can use multiple TapHome Core units in your installation. For this cases you can use config like this:

```yaml
taphome:
  cores:
    - token: 00000000-0000-0000-0000-000000000000
      lights:
        - 1
        - 2
    - token: 00000000-0000-0000-0000-000000000000
      lights:
        - 1
      covers:
        - 6
```
