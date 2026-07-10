# TapHome integration — user guide

This guide covers everything the integration can do and how to configure it.
Everything is set up in the Home Assistant UI — no YAML is needed. If you are
upgrading from a YAML configuration, see [Migrating from YAML](#migrating-from-yaml).

## Prerequisites

Before adding the integration, prepare your TapHome core in the TapHome app:

1. Open the TapHome app and go to **Settings → Integrations → TapHome API**
   (called *Exposed devices* on some versions).
2. Enable the API and **expose every device** you want to control from Home
   Assistant. Devices that are not exposed are invisible to the integration.
3. Copy the API **token**.
4. For a local connection, note the **IP address** of the core. A fixed IP
   address (DHCP reservation) is strongly recommended — the integration talks
   to the core by IP.

## Adding a core

**Automatic discovery**: a TapHome core with the API enabled announces itself
on the local network, so it normally appears in _Settings → Devices &
services_ as a discovered device on its own. Click **Add**, enter the API
token, and continue with step 3 below. When the core's IP address changes
later, discovery updates the integration automatically.

To add a core manually (e.g. a cloud connection, or a core on another
network): _Settings → Devices & services → Add integration → **TapHome**_

1. **Connection** — fill in the token, and either the local IP address of the
   core or check *Use TapHome cloud*. A local connection is recommended: it is
   faster, works without internet access, and supports short polling
   intervals. The same form also offers the core settings described in
   [Core settings](#core-settings); the defaults are fine to start with.
2. The integration verifies the connection and reads the devices exposed in
   the TapHome API.
3. **Zones** (shown only when your devices have zones) — map TapHome zones to
   Home Assistant areas. A zone left empty uses its TapHome name as the area;
   tick **Ignore** to assign no area at all.
4. **Labels** (shown only when your devices have categories) — every category
   becomes a label on the device and its entities; the mapping renames it and
   **Ignore** skips it.
5. **Devices** — pick the devices to add. For each device choose the
   platform(s) it should be exposed as (light, switch, cover, …) and fill in
   optional per-device settings. Only platforms compatible with the device
   type are offered.

Each TapHome core is one integration entry. If you have several cores, add
the integration once per core.

### Which platform for which device?

| TapHome device | Platforms offered |
|---|---|
| Light (on/off, dimmable, RGB, tunable white) | Light |
| Switched output, socket | Switch, Light, Fan, Humidifier, Valve |
| Analog output (0–100 %) | Light, Fan, Humidifier, Valve |
| Blinds / shutters / positional drive | Cover, Fan, Humidifier, Valve |
| Thermostat | Climate |
| Multi-value switch | Select (and as light effects, climate modes, …) |
| Wall button | Button, Event |
| Variable | Sensor, Binary sensor, Number, Time |
| Any device | Sensor, Binary sensor (readings it exposes) |

Sensor and binary sensor types (temperature, humidity, CO₂, …) are detected
automatically from the values the device exposes; the per-device options can
override the detected device class, unit or value type when needed.

## Configure dialog

Open _Settings → Devices & services → TapHome → **Configure**_. The menu
offers:

- **Core settings** — connection (IP/cloud, token), webhook id, naming flags
  and exposed attributes:
  - *Use description as entity id / as name*: TapHome devices have a name
    (often a technical one) and a description. These flags choose which one
    seeds the entity ids and names of newly added entities. Renaming
    individual entities afterwards works as usual in Home Assistant.
  - *Exposed attributes*: which `taphome_*` state attributes entities carry
    (id, name, description, zone, category, operation mode).
- **Add device** — the same typed add flow as the **+ Add device** button on
  the integration page (see below).
- **Edit device** — find a configured device by picking the device *or any of
  its entities* (whichever you know), then change its options. Advanced options
  (including other variants of the same device type) are collapsed at the
  bottom, so a simple thermostat can be upgraded to a controlled one.
- **Remove device** — the same picker; a summary shows the device, its
  configurations and entities before everything is removed.
- **Zones** / **Labels** — edit the zone → area and category → label mapping
  at any time.

Each exposed device is a **device subentry** of the Core; devices are added and
managed right where they live:

- **Add a device** — the Core entry page has **+ Add device**, and Configure
  offers the identical flow (the bulk picker exists only in the initial setup
  wizard). Pick the *type* you are adding (light, switch, thermostat,
  controlled thermostat, range thermostat, sensor, …) and the form asks exactly
  for what that type needs. For sensors and binary sensors you pick the device
  and then which of its values to expose — each value becomes its own entry, so
  it can be removed individually later.
- **Edit a device** — open the device (from the Core's device list, or _Settings
  → Devices & services → Devices_) and use its **⋮ → Edit**. Every option is
  offered; the advanced ones are collapsed.
- **Remove a device** — the device's **⋮ → Delete** removes the device **and**
  its entities from Home Assistant. No manual registry cleanup is needed.

Changes are applied by reloading the integration entry automatically.

### Per-device options worth knowing

- **Light — Effects**: pick a TapHome multi-value switch that drives light
  effects; its options appear as effects on the light entity.
- **Climate**: a TapHome thermostat can be linked with other devices —
  heating/cooling switch, HVAC mode/action multi-value switches, preset, fan
  and swing modes, a target-humidity output, and a second thermostat for
  heat/cool ranges.
- **Cover — Close threshold**: position (%) below which the cover reports
  closed.
- **Button — Actions**: which press actions (press, double press, long press)
  the event entity announces.
- **Number — Minimum value / Maximum value / Step**: override the range and
  resolution of the number entity. Left empty, the integration uses the range
  TapHome reports for the variable; if TapHome reports none, Home Assistant
  applies its own defaults (0–100, step 1). Set these when your variable
  accepts values outside 0–100 (e.g. a setpoint up to 250) or needs a finer
  step.

## State updates (webhook)

The integration is push-based. Configure a webhook to get instant updates:

1. In **Core settings**, set a *Webhook id* (the default `taphome` is fine —
   change it to something random if your Home Assistant is reachable from the
   internet).
2. In the TapHome app, create a **webhook** rule that sends device changes to
   `http://<home-assistant>:8123/api/webhook/<webhook id>`.

Without a webhook the integration polls: every 2 s on a local connection,
every 20 s over the TapHome cloud. Once the first webhook arrives, polling
drops to a once-a-minute safety net.

## New devices

When you expose a new device in the TapHome API later, the integration
notices it as soon as the device first reports a value (through the webhook
or the regular poll — usually within seconds, and on every restart or reload)
and raises a **repair issue** (_Settings → Repairs_). Opening it starts the
same guided flow as **Add device**: pick the device type you want (only the
types that device supports are offered — e.g. a thermostat can become a
thermostat, controlled thermostat, range thermostat, sensor or binary
sensor), fill in any options, done. Or choose **Ignore this device** so it is
not offered again. Devices are never added on their own: which type a TapHome
device should be exposed as is your decision.

## Migrating from YAML

YAML configuration (`taphome:` in `configuration.yaml`) is deprecated:

- On startup, an existing YAML section is **imported automatically** into a
  config entry — including all devices, their options, zone/label mappings
  and the webhook. Entity unique ids are preserved, so history and
  automations keep working.
- A repair issue reminds you to delete the `taphome:` section afterwards.
  Until you delete it, changes made in YAML are ignored — the config entry
  is the source of truth.
- The previously documented YAML options all have UI equivalents (see
  [Configure dialog](#configure-dialog)).

## Troubleshooting

**"Failed to connect" when adding the core**
- Check the IP address and that Home Assistant can reach it (`ping` from the
  HA host). The core API listens on plain HTTP port 80.
- The TapHome API must be enabled in the TapHome app.

**"Invalid authentication"**
- The token was rejected. Copy it again from the TapHome app. When the token
  changes later, the integration starts a re-authentication flow on its own.

**A device is missing in the device picker**
- It is not exposed in the TapHome API. Expose it in the TapHome app, then
  reload the integration; a repair issue will offer to add it.

**Entities are unavailable**
- The connection to the core dropped. The integration reconnects
  automatically and recovers the entities; check the network if it persists.

**States update slowly**
- Set up the webhook (see [State updates](#state-updates-webhook)). Slow
  updates without a webhook are expected on cloud connections.

**Wrong sensor type or unit**
- Override the detected device class / unit / value type in
  _Configure → Edit devices_.

**An action fails with "TapHome did not apply the requested change"**
- The core accepted the request but reported the change as failed — usually
  the device is blocked in TapHome (e.g. a rule or manual override). Check
  the device in the TapHome app; the entity state reloads automatically so
  Home Assistant shows what the core really did.

## Automation examples

TapHome entities are regular Home Assistant entities, so anything in the
automation editor works. Two patterns worth copying:

React to a physical TapHome wall button (the `event` entity fires for every
press type — `press`, `long_press`, `double_press`, `triple_press`):

```yaml
automation:
  - alias: "Hallway button toggles the lights"
    triggers:
      - trigger: state
        entity_id: event.hallway_button
    conditions:
      - condition: template
        value_template: >-
          {{ trigger.to_state.attributes.event_type == 'press' }}
    actions:
      - action: light.toggle
        target:
          entity_id: light.hallway
```

Get notified when the connection to the core drops (the diagnostic
connectivity sensor lives on the Core hub device):

```yaml
automation:
  - alias: "TapHome core offline"
    triggers:
      - trigger: state
        entity_id: binary_sensor.my_home_connectivity
        to: "off"
        for: "00:05:00"
    actions:
      - action: notify.notify
        data:
          message: "TapHome core has been unreachable for 5 minutes."
```

## Known limitations

- **Discovery needs the same network.** Cores are discovered via mDNS, which
  does not cross most subnet/VLAN boundaries — a core on another network or
  connected through the TapHome cloud is added manually. The API token must
  always be entered by hand; it cannot be read from the network.
- **Only devices exposed in the TapHome API are available.** Expose them in
  the TapHome app under _Exposed devices → TapHome API_ first.
- **One value direction per poll.** Without a webhook, state changes are
  polled (2 s locally, 20 s via cloud), so very short pulses between two
  polls can be missed — set up the [webhook](#state-updates-webhook) for
  instant pushes.
- **Cloud connections are slower** and meant as a fallback; a local
  connection to the core is recommended.
- **Scenes/rules stay in TapHome.** The integration exposes devices and
  values; TapHome scenes and rules are not imported (multi-value switches
  used for scenes can be exposed as `select` entities).

## Removing the integration

To remove a single device, open its device page and use **⋮ → Delete** on
its config subentry. To remove the whole integration:

1. Open _Settings → Devices & services → TapHome_.
2. On each TapHome Core entry, choose **⋮ → Delete**. This disconnects from
   the core, unregisters the webhook and removes the entry's devices and
   entities.
3. If you use HACS, you can then remove the repository download under
   _HACS → TapHome → Remove_ and restart Home Assistant.

Nothing is changed on the TapHome core itself — the API token and the
exposed devices stay as they are, so re-adding the integration later
restores the same devices.
