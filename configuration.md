## Do you need help?
I would be happy to configure your TapHome integration, integrate gadgets from Home Assistant to TapHome or set up complex smart rules for you. Feel free to contact me [dybal.it](https://www.dybal.it/).

## Basic setup
You need to expose the devices via [TapHome API](https://taphome.com/en/support/601227274).
To add the TapHome API interface in TapHome app you have to go to
_Settings → Expose devices → TapHome API_.

Then choose the devices that you want to expose to Home Assistant using the _Add device_ option.

Take the authorization token at the top of the screen — you will enter it when adding the integration. **Do not share your token anywhere!**

### Local access
The preferred way is local access with webhook (local_push). Provide the IP address of your core when adding the integration and make sure that your core IP address will not change in the future.

## Configuration via UI (recommended)

1. In Home Assistant go to _Settings → Devices & services → Add integration_ and search for **TapHome**.
2. Enter the authorization token and the IP address of your core (or enable **Use TapHome cloud** to connect through the TapHome cloud instead). The webhook and other core settings can be filled in here too. Each TapHome core is added as a separate integration entry.
3. Open the integration entry and press **Configure** to manage everything else:
   - **Core settings** – the same connection, webhook, description and exposed-attribute fields as when adding the core.
   - **Zones (areas)** – rename TapHome zones to Home Assistant areas or ignore them.
   - **Labels (categories)** – rename TapHome categories to Home Assistant labels or ignore them.
   - **Add devices** – pick the devices exposed on the core (searchable, with each device's room/zone shown) and then the platform (lights, covers, climates, …) they should be added as.
   - **Edit devices** – pick a configured device (searchable) and adjust the advanced per-device options (device class, effects, climate controller ids, …) matching the tables below.
   - **Remove devices** – pick the devices whose entities should be removed from Home Assistant.

The connection settings (token, IP address / cloud) can also be changed later via **Core settings** or the entry's **Reconfigure** action. When the core rejects the token, Home Assistant automatically starts a re-authentication flow.

## YAML Configuration (deprecated)

**YAML configuration is deprecated.** An existing `taphome:` section in `configuration.yaml` is imported into the UI automatically on startup — entities keep their unique IDs and history. After the import, remove the `taphome:` section; changes made in YAML are no longer applied. The tables below still document all options, which are all available in the UI as well.

The integration is configured in `configuration.yaml`. Each TapHome core is defined under `taphome.cores`. Every core requires an authentication token and at least one platform configuration.

### Core options

Each entry under `cores` supports the following keys:

| Option | Type | Description |
| --- | --- | --- |
| `token` | string | **Required.** API token of the TapHome core. |
| `id` | string | **Required when multiple cores are used.** String identifier of core, e.g., `apartment_8` or `primary`. |
| `api_url` | string | API URL of your core `http://192.168.1.3/api/TapHomeApi/v1`. |
| `webhook_id` | string | Register a webhook for push updates in Home Assistant, e.g., `taphome_primary`. |
| `use_description_as_entity_id` | bool | Use TapHome device descriptions as entity IDs. |
| `use_description_as_name` | bool | Use TapHome device descriptions as entity names. |
| `enabled_attributes` | list | Extra attributes to expose. Allowed values: `taphome_id`, `taphome_name`, `taphome_description`, `taphome_category`, `taphome_zone`, `taphome_operation_mode`. |

### Entity definition

Every device entry accepts at least the TapHome device `id`. Instead of using a bare number you may supply a mapping and add `unique_id` or platform specific options.

```yaml
lights:
  - 12345
  - id: 67890
    unique_id: "living_room_ceiling"
    effect_id: 22222
```

**Use the `unique_id` parameter with caution. It is not usually necessary because the integration generates it based on a combination of the TapHome device ID, domain, and value type.**

### Platforms

#### Binary sensor

| Option | Type | Description |
| --- | --- | --- |
| `id` | int | **Required.** TapHome device id. |
| `device_class` | string | Optional Home Assistant device class. |
| `value_type` | string | Optional TapHome value type. |

```yaml
binary_sensors:
  - 101
  - id: 103
    device_class: window
  - id: 104
    device_class: garage_door
  - id: 105
    device_class: door
```

The value type and device class are automatically filled in based on taphome value types. However, taphome does not cover all cases. [You can look default mappings](https://github.com/martindybal/taphome-homeassistant/blob/production/binary_sensor.py).

#### Button

| Option | Type | Description |
| --- | --- | --- |
| `id` | int | **Required.** TapHome device id. |
| `device_class` | string | Optional device class. |
| `actions` | list | List of actions to expose (`press` by default). |

```yaml
buttons:
  - 201
  - id: 202
    device_class: restart
    actions:
      - press
      - long_press
```

Each button also provides a matching `event` entity that fires when the button is pressed.

#### Climate

| Option | Type | Description |
| --- | --- | --- |
| `id` | int | **Required.** Thermostat id or range high thermostat id. |
| `range_high_thermostat_id` | int | High thermostat id for range climates. |
| `range_low_thermostat_id` | int | Low thermostat id for range climates. |
| `target_temperature_step` | float | Step for setting target temperature. |
| `precision` | float | Temperature precision in °C. |
| `hvac_switch_id` | int | Digital output controlling HVAC. |
| `hvac_mode` | string | Fixed HVAC mode used with `hvac_switch_id`. Available [hvac modes](https://developers.home-assistant.io/docs/core/entity/climate/#hvac-modes). |
| `hvac_mode_id` | int | Multi value switch id providing HVAC modes. |
| `hvac_action_id` | int | Multi value switch id providing HVAC action. |
| `preset_mode_id` | int | Multi value switch id providing preset modes. |
| `fan_mode_id` | int | Multi value switch id providing fan modes. |
| `swing_mode_id` | int | Multi value switch id providing vertical swing modes. |
| `swing_horizontal_mode_id` | int | Multi value switch id providing horizontal swing modes. |
| `target_humidity_id` | int | Analog output id for target humidity. |
| `min_humidity` | int | Minimum humidity percentage. |
| `max_humidity` | int | Maximum humidity percentage. |

```yaml
climates:
  - id: 301
    hvac_switch_id: 302
    hvac_mode: heat
    preset_mode_id: 303
  - id: 311
    range_low_thermostat_id: 312
    range_high_thermostat_id: 313
    hvac_mode_id: 314

    # range mode hvac
    - range_low_thermostat_id: 5011
      range_high_thermostat_id: 5010
      hvac_mode_id: 5005
      hvac_switch_id: 5001
      hvac_action_id: 5003

    # valve hvac
    - id: 5014
      hvac_mode_id: 5005
      hvac_switch_id: 5001 # thermovalve
      hvac_action_id: 5003 # current hvac action of source (heatpump)
      preset_mode_id: 5005 # current hvac mode of source (heatpump)

    # mode hvac
    - id: 5007
      hvac_mode_id: 5005
      hvac_action_id: 5003

    # switch hvac
    - id: 5020
      hvac_mode: cool
      hvac_switch_id: 5001
      hvac_action_id: 5003

    # without hvac
    - id: 5009
      hvac_action_id: 5003
```

#### Cover

| Option | Type | Description |
| --- | --- | --- |
| `id` | int | **Required.** TapHome device id. |
| `device_class` | string | Optional device class. |
| `close_threshold` | int | Percentage used to detect the closed state. Suitable for blinds where 70 can be closed enough. Or garage door if you want to ventilate. |

```yaml
covers:
  - 401
  - id: 402
    device_class: blind
    close_threshold: 90
```

#### Fan

| Option | Type | Description |
| --- | --- | --- |
| `id` | int | **Required.** TapHome device id. |
| `preset_mode_id` | int | Multi value switch id providing preset modes. |

```yaml
fans:
  - 501
  - id: 502
    preset_mode_id: 503
```

#### Humidifier

| Option | Type | Description |
| --- | --- | --- |
| `id` | int | **Required.** TapHome device id. |
| `switch_id` | int | Digital output that turns the device on/off. |
| `action_id` | int | Multi value switch id providing current action. |
| `mode_id` | int | Multi value switch id providing available modes. |
| `humidity_sensor_id` | int | Sensor id reporting current humidity. |
| `min_humidity` | int | Minimum humidity percentage (default `0`). |
| `max_humidity` | int | Maximum humidity percentage (default `100`). |
| `device_class` | string | Optional device class. |

```yaml
humidifiers:
  - 601
  - id: 602
    switch_id: 603
    humidity_sensor_id: 604
    min_humidity: 30
    max_humidity: 70
```

#### Light

| Option | Type | Description |
| --- | --- | --- |
| `id` | int | **Required.** TapHome device id. |
| `effect_id` | int | Multi value switch id providing available scenes or effects. |

```yaml
lights:
  - 701
  - id: 702
    effect_id: 703
```

On/off, dimmable, dual white and RGB lights are supported.

#### Select (multi value switch)

| Option | Type | Description |
| --- | --- | --- |
| `id` | int | **Required.** Multi value switch identifier. |

```yaml
multivalue_switches:
  - 801
  - 802
```

#### Sensor

| Option | Type | Description |
| --- | --- | --- |
| `id` | int | **Required.** TapHome device id. |
| `device_class` | string | Optional device class. |
| `value_type` | string | Optional TapHome value type. |
| `unit_of_measurement` | string | Override unit of measurement. |
| `state_class` | string | Override state class. |

The value type, device class, unit of measurement, state class are automatically filled in based on taphome value types. However, taphome does not cover all cases. [You can look default mappings](https://github.com/martindybal/taphome-homeassistant/blob/production/sensor.py).

```yaml
sensors:
  - 901
  - id: 902
    device_class: VOLUME_STORAGE
    unit_of_measurement: m³
    state_class: measurement
  - 903
```

#### Switch

| Option | Type | Description |
| --- | --- | --- |
| `id` | int | **Required.** TapHome device id. |
| `device_class` | string | Optional device class. |

```yaml
switches:
  - 1001
  - id: 1002
    device_class: outlet
```

#### Time

| Option | Type | Description |
| --- | --- | --- |
| `id` | int | **Required.** Session duration variable identifier. |

**The time must not exceed 24 hours.**

```yaml
times:
  - id: 1101
```

#### Valve

| Option | Type | Description |
| --- | --- | --- |
| `id` | int | **Required.** TapHome device id. |
| `device_class` | string | Optional device class. |

```yaml
valves:
  - 1201
  - id: 1202
    device_class: water
```

### My home configuration as example

```yaml

taphome:
  cores:
    - id: primary
      use_description_as_entity_id: true
      token: !secret taphome_primary_token
      ip: 192.168.1.3
      webhook_id: taphome_primary
      binary_sensors:
        - 77
        - 78
        - 79
        - id: 54
          device_class: running
        - id: 55
          device_class: running
        - id: 67
          device_class: running
        - id: 68
          device_class: running
        - id: 10141
          device_class: door
        - id: 10143
          device_class: door
        - id: 1024211
          device_class: window
        - id: 1024212
          device_class: window
        - id: 1034211
          device_class: window
        - id: 1034212
          device_class: window
        - id: 1034311
          device_class: door
        - id: 1034312
          device_class: door
        - id: 10341
          device_class: door
        - id: 10441
          device_class: door
        - id: 1044211
          device_class: window
        - id: 1044212
          device_class: window
        - id: 1044311
          device_class: door
        - id: 1044312
          device_class: door
        - id: 104432
          device_class: door
        - id: 10541
          device_class: door
        - id: 1054311
          device_class: door
        - id: 1054312
          device_class: door
        - id: 10641
          device_class: door
        - id: 10741
          device_class: door
        - id: 1074211
          device_class: window
        - id: 1074212
          device_class: window
        - id: 109431
          device_class: garage_door
        - id: 109432
          device_class: garage_door
        - id: 1094311
          device_class: door
        - id: 1094312
          device_class: door
        - id: 1094321
          device_class: door
        - id: 1094322
          device_class: door
        - id: 2024211
          device_class: window
        - id: 2024212
          device_class: window
        - id: 20341
          device_class: door
        - id: 2034211
          device_class: window
        - id: 2034212
          device_class: window
        - id: 2034221
          device_class: window
        - id: 2034222
          device_class: window
        - id: 20441
          device_class: door
        - id: 2044211
          device_class: window
        - id: 2044212
          device_class: window
        - id: 20541
          device_class: door
        - id: 2054211
          device_class: window
        - id: 2054212
          device_class: window
        - id: 2054221
          device_class: window
        - id: 2054222
          device_class: window
        - id: 20641
          device_class: door
        - id: 20741
          device_class: door
        - id: 2074311
          device_class: door
        - id: 2074312
          device_class: door
        - id: 20841
          device_class: door
        - id: 2084311
          device_class: door
        - id: 2084312
          device_class: door
        - id: 20941
          device_class: door
        - id: 21041
          device_class: door
        - id: 1017
          value_type: 48
          device_class: occupancy
        - id: 1022027
          value_type: 48
          device_class: occupancy
        - id: 1037
          value_type: 48
          device_class: occupancy
        - id: 1047
          value_type: 48
          device_class: occupancy
        - id: 1057
          value_type: 48
          device_class: occupancy
        - id: 1067
          value_type: 48
          device_class: occupancy
        - id: 1077
          value_type: 48
          device_class: occupancy
        - id: 1097
          value_type: 48
          device_class: occupancy
        - id: 2037
          value_type: 48
          device_class: occupancy
        - id: 2047
          value_type: 48
          device_class: occupancy
        - id: 2057
          value_type: 48
          device_class: occupancy
        - id: 2067
          value_type: 48
          device_class: occupancy
        - id: 2077
          value_type: 48
          device_class: occupancy
        - id: 2087
          value_type: 48
          device_class: occupancy
        - id: 2097
          value_type: 48
          device_class: occupancy

      buttons:
        - 50
        - 51
        - 52
        - 53
        - 85
        - 89
        - 90
        - id: 10110
          actions:
            - LongPress
            - DoublePress
        - id: 10310
          actions:
            - LongPress
            - DoublePress
        - id: 10410
          actions:
            - LongPress
            - DoublePress
        - id: 10510
          actions:
            - LongPress
            - DoublePress
        - id: 10610
          actions:
            - LongPress
            - DoublePress
        - id: 10710
          actions:
            - LongPress
            - DoublePress
        - id: 10910
          actions:
            - LongPress
            - DoublePress
        - id: 10220210
          actions:
            - LongPress
            - DoublePress
        - id: 20310
          actions:
            - LongPress
            - DoublePress
        - id: 20410
          actions:
            - LongPress
            - DoublePress
        - id: 20510
          actions:
            - LongPress
            - DoublePress
        - id: 20610
          actions:
            - LongPress
            - DoublePress
        - id: 20710
          actions:
            - LongPress
            - DoublePress
        - id: 20810
          actions:
            - LongPress
            - DoublePress
        - id: 20910
          actions:
            - LongPress
            - DoublePress
        - id: 21010
          actions:
            - LongPress
            - DoublePress
        - id: 40010
          actions:
            - LongPress
            - DoublePress
        - id: 40110
          actions:
            - LongPress
            - DoublePress
        - 20474
        - 20874
        - 43
      climates:
        - id: 21051
          heating_switch_id: 21061
          target_temperature_step: 5
        - id: 201
          hvac_mode: cool
          hvac_switch_id: 203
        - 32
        - id: 35
          hvac_mode_id: 57
          hvac_action_id: 63
          preset_mode_id: 73
          fan_mode_id: 202
          target_humidity_id: 31

        - id: 56
          heating_cooling_mode_id: 57
        - id: 58
          heating_switch_id: 59
        - id: 69
          heating_switch_id: 65
        - id: 1015
          hvac_switch_id: 10151
          hvac_mode_id: 57
          hvac_action_id: 63
          preset_mode_id: 73
        - id: 1035
          hvac_switch_id: 10351
          hvac_mode_id: 57
          hvac_action_id: 63
          preset_mode_id: 73
        - id: 1045
          hvac_switch_id: 104511
          hvac_mode_id: 57
          hvac_action_id: 63
          preset_mode_id: 73
        - id: 1055
          hvac_switch_id: 10551
          hvac_mode_id: 57
          hvac_action_id: 63
          preset_mode_id: 73
        - id: 1075
          hvac_switch_id: 10751
          hvac_mode_id: 57
          hvac_action_id: 63
          preset_mode_id: 73
        - range_low_thermostat_id: 107912
          range_high_thermostat_id: 107913
          hvac_mode: cool
          hvac_switch_id: 107911
        - id: 2035
          hvac_switch_id: 20351
          hvac_mode_id: 57
          hvac_action_id: 63
          preset_mode_id: 73
        - id: 2045
          hvac_switch_id: 20451
          hvac_mode_id: 57
          hvac_action_id: 63
          preset_mode_id: 73
        - id: 2055
          hvac_switch_id: 20551
          hvac_mode_id: 57
          hvac_action_id: 63
          preset_mode_id: 73
        - id: 2075
          hvac_switch_id: 20751
          hvac_mode_id: 57
          hvac_action_id: 63
          preset_mode_id: 73
        - id: 2085
          hvac_switch_id: 20851
          hvac_mode_id: 57
          hvac_action_id: 63
          preset_mode_id: 73

      switches:
        - id: 15
          device_class: switch
        - id: 21061
          device_class: switch
        - 33
        - 40
        - 41
        - 42
        - 44
        - 45
        - 48
        - 64
        - 65
        - 76
        - 86
        - 91
        - 92
        - 93
        - 1054313
        - 20471
        - 20871
        - 20892
        - 20461
        - 210122 #temporary lights transition on/off
      lights:
        - 10111
        - 10112
        - 10211
        - 10212
        - 10311
        - 10312
        - 10313
        - 10411
        - 104111
        - 10412
        - 104121
        - 10413
        - 10414
        - 10415
        - 10511
        - 10512
        - 10513
        - 10514
        - 10612
        - 10711
        - 10712
        - 109131
        - 109132
        - 202111
        - 202112
        - 202121
        - 202122
        - 20311
        - 20312
        - 20313
        - 20411
        - 20412
        - 20413
        - 20511
        - 20512
        - 20513
        - 20611
        - 20612
        - 20711
        - 20712
        - 20713
        - 20714
        - 20811
        - 20812
        - 20911
        - 20912
        - 20913
        - 21011
        - 210121
        - 400111
        - 400112
        - 400121
        - 400122
        - 400131
        - 400132
        - 400141
        - 400142
        - 46
        - 47
      covers:
        - id: 10221
          device_class: shutter
        - id: 10321
          device_class: blind
        - id: 10322
          device_class: blind
        - id: 10323
          device_class: blind
        - id: 10421
          device_class: blind
        - id: 10422
          device_class: blind
        - id: 10423
          device_class: shade
        - id: 10424
          device_class: shade
        - id: 20221
          device_class: shutter
        - id: 20321
          device_class: shade
        - id: 20322
          device_class: blind
        - id: 20421
          device_class: shade
        - id: 20521
          device_class: blind
        - id: 20522
          device_class: blind
        - id: 20721
          device_class: blind
        - id: 20821
          device_class: shutter
          close_threshold: 80
        - id: 10921
          device_class: garage
          close_threshold: 90
      sensors:
        - 3
        - 34
        - 36
        - 37
        - 38
        - 39
        - 60
        - 61
        - 62
        - 74
        - 75
        - id: 87
          device_class: POWER_FACTOR
        - id: 88
          device_class: POWER_FACTOR
        - id: 66
          device_class: volume_flow_rate
          unit_of_measurement: L/min
        - 70
        - 71
        - 72
        - 10332
        - 10331
        - 10731
        - 20931
        - 20331
        - 10433
        - 10432
        - 10434
        - 10131
        - 10132
        - 10431
        - 20832
        - 20531
        - 20731
        - 20732
        - 20431
        - 10631
        - 10531
        - 20332
        - 20631
        - 20831
        - 10391
        - 10491
        - 10931
        - 10932
        - 10933
        - 20391
        - 20491
        - 20591
        - 20891
        - id: 21031
          device_class: temperature
          unit_of_measurement: °C
        - 21032
        - 21033
        - 2021
        - 2022
        - 2023
        - 2024
        - 2025
        - 2026
        - 30010
        - 30011
        - 30012
        - 30013
        - 30014
        - 30015
        - 30016
        - 30017
        - 30018
        - 300181
        - 30019
        - 30020
        - 30021
        - 30022
        - 300221
        - 30023
        - 30024
        - id: 3014
          unit_of_measurement: m³
        - id: 3015
          unit_of_measurement: m³
        - 40031
        - 40032
        - 40033
        - 40034
        - 40041
        - 40042
        - 40043
        - 10335
        - 10435
        - 20335
        - 20435
        - 20535
        - 20835
      multivalue_switches:
        - 1
        - 2
        - 49
        - 57
        - 63
        - 73
        - 202
        - 2101
        - 210123 #temporary lights scene 2NP
        - 210124 #temporary light scene 1NP
        - 40211
        - 40221
        - 40231
        - 40241
      fans:
        - id: 20
          preset_mode_id: 202
        - 21
        - 22
        - 23
        - 24
        - 25
        - 26
        - 27
        - 28
        - 29
      humidifiers:
        - id: 31
          device_class: humidifier
          switch_id: 33
          action_id: 95
          humidity_sensor_id: 34
          min_humidity: 40
          max_humidity: 80
      valves:
        - id: 4021
          device_class: water
        - id: 4022
          device_class: water
        - id: 4023
          device_class: water
        - id: 4024
          device_class: water
        - 10151
        - 10351
        - 104511
        - 104512
        - 10551
        - 10751
        - 20351
        - 20451
        - 20551
        - 20751
        - 20851
      times:
        - 81
        - 82
        - 83
        - 84
        - 20472
        - 20872
```
