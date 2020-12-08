# TapHome Home Assistant integration

This is demo of integration [TapHome](https://taphome.com/CZ/home) into [Home Assistant](https://www.home-assistant.io).

## Supported devices
- Light switch

## Installation

Copy this folder to `<config_dir>/custom_components/taphome/`.

Add the following entry in your `configuration.yaml`:

```yaml
light:
  - platform: taphome
    token: 00000000-0000-0000-0000-000000000000
    lights:
      - 1
      - 7
```

You have to specify your token and id of your lights. For more information visit https://taphome.com/en/support/601227274

## License
This repository is under the [GPL v3 with Commons Clause](https://github.com/martindybal/taphome-homeassistant/blob/main/LICENSE.md).