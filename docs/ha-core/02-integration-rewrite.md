# Fáze 2 — Přepis integrace na config entries

Probíhá už ve forku `home-assistant/core` v adresáři
`homeassistant/components/taphome/`. Config flow je řešen samostatně a tento
dokument ho nerozpracovává — kapitola 2.1 pouze fixuje rozhraní, na které
zbytek kódu navazuje.

## 2.1 Rozhraní config entry (kontrakt vůči hotovému config flow)

- `entry.data`:
  - `CONF_HOST` — IP/hostname lokálního hubu, `None`/nepřítomno = cloud
    (`https://api.taphome.com/api/TapHomeApi/v1`),
  - `CONF_TOKEN` — API token,
  - `CONF_WEBHOOK_ID` — vygenerované `webhook.async_generate_id()` při
    vytvoření entry (ne zadávané uživatelem).
- `entry.unique_id` = `hub.location_id` (viz fáze 1.2.4) — pravidlo
  *unique-config-entry*.
- Jedna config entry = jeden TapHome core. Dnešní YAML seznam `cores:` zaniká;
  více cores = uživatel přidá integraci vícekrát.

## 2.2 `__init__.py`

Kompletní náhrada dnešního `async_setup` + `CONFIG_SCHEMA` + `load_platform`:

```python
type TapHomeConfigEntry = ConfigEntry[TapHomeHub]

PLATFORMS = [Platform.LIGHT]  # roste s follow-up PRs

async def async_setup_entry(hass: HomeAssistant, entry: TapHomeConfigEntry) -> bool:
    session = async_get_clientsession(hass)
    try:
        hub = await TapHomeHubFactory.async_connect(_api_url(entry), entry.data[CONF_TOKEN], session)
    except TapHomeAuthenticationError as err:
        raise ConfigEntryAuthFailed from err          # spustí reauth flow
    except TapHomeConnectionError as err:
        raise ConfigEntryNotReady from err            # HA opakuje setup

    entry.runtime_data = hub

    webhook.async_register(hass, DOMAIN, entry.title, entry.data[CONF_WEBHOOK_ID], _handle_webhook(hub))
    entry.async_on_unload(lambda: webhook.async_unregister(hass, entry.data[CONF_WEBHOOK_ID]))
    entry.async_on_unload(hub.async_disconnect)

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True

async def async_unload_entry(hass: HomeAssistant, entry: TapHomeConfigEntry) -> bool:
    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
```

Zásady:

- **Žádné `hass.data`** — vše přes `entry.runtime_data` (pravidlo
  *runtime-data*). Pokud bude runtime stav víc než hub (např. mapa
  device → platforma z 2.3), zabalit do `@dataclass TapHomeRuntimeData`.
- Webhook handler v integraci rozparsuje `Request` na dict a předá
  `hub.async_handle_webhook(payload)` (viz fáze 1.2.2).
- Zaregistrovat repair issue při ztrátě spojení za běhu lze zachovat —
  napojit na `hub.connection_state.changed` zde (viz 2.7).

## 2.3 Automatický discovery entit (náhrada YAML seznamů)

Největší koncepční změna: entity se vytvoří **ze všech zařízení, která hub
vystavuje** (`hub.devices`), žádné vyjmenovávání. `DeviceFactory` už dnes
klasifikuje zařízení podle `supported_values` — na to se namapují platformy:

| Třída zařízení (pytaphome) | Platforma HA | Poznámka |
|---|---|---|
| `RGBLightDevice`, `DualWhiteLightDevice` | `light` | jednoznačné |
| `ThermostatDevice` | `climate` | jednoznačné |
| `BidirectionalDevice` | `cover` | výchozí; viz nejednoznačnosti níže |
| `MultiValueSwitchDevice` | `select` | jednoznačné |
| `ButtonDevice` | `event` (+ `button` pokud API umí stisk vyvolat) | |
| `VariableDevice` (read-only) | `sensor` / `binary_sensor` dle `ValueType` | |
| `SessionDurationVariableDevice` | `time` | |
| `AnalogOutputDevice` | `light` (výchozí) | nejednoznačné |
| `DigitalOutputDevice` | `switch` (výchozí) | nejednoznačné |

### Nejednoznačné výstupy — řešení bez YAML

Dnes o doméně (light/switch/fan/humidifier/valve/cover) rozhoduje uživatel
YAML klíčem. V Core:

1. **Primárně rozhodnout z metadat API**: ověřit, zda TapHome API u zařízení
   vrací typ/kategorii (fáze 1.2.5). Pokud ano, sestavit mapovací tabulku
   `deviceType → platforma` a nejednoznačnost z velké části zmizí.
2. **Zbytek řešit HA mechanismem `switch_as_x`**: `DigitalOutputDevice` se
   vystaví jako `switch` a uživatel si ho v UI přepne na light / fan / valve /
   siren („Change device type of a switch"). To je oficiálně doporučený vzor —
   do dokumentace integrace přidat návod.
3. `AnalogOutputDevice`: výchozí `light` (stmívatelný výstup); pokud metadata
   z bodu 1 řeknou jinak (fan, cover pozice), použít je. Pro `number` jako
   generický fallback se rozhodnout až podle reálných dat z API.

Rozhodnutí zdokumentovat v kódu (mapovací modul, např. `discovery.py`
s jedinou funkcí `platform_for_device(device) -> Platform | None`), aby se
dalo v review obhájit a testovat.

### Rozdělení do platform souborů

Každá platforma dostane standardní vstup:

```python
async def async_setup_entry(
    hass: HomeAssistant,
    entry: TapHomeConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    hub = entry.runtime_data
    async_add_entities(
        _create_light(device)
        for device in hub.devices.values()
        if platform_for_device(device) is Platform.LIGHT
    )
```

`setup_platform`, `DiscoveryInfoType`, `add_entry_request.py`,
`TapHome*Config` třídy a celý `taphome_config_entry.py` se mažou.

## 2.4 `entity.py` — přepis společného základu

Dnešní `taphome_entity.py` se výrazně zmenší. Změny bod po bodu:

| Dnes | V Core |
|---|---|
| ruční `unique_id` s doménou a `core.id` | `_attr_unique_id = f"{hub.location_id}_{device.id}"`; u zařízení s více entitami suffix (`_{value_type}`) |
| `use_description_as_entity_id` + `async_generate_entity_id` | smazat — entity_id generuje HA z device name |
| `use_description_as_name` / `_attr_name = device.name` | `_attr_has_entity_name = True`; hlavní entita zařízení `_attr_name = None` (jméno = jméno zařízení), vedlejší entity přes `_attr_translation_key` |
| zápis do area/label registry (`_async_set_area`, `_async_set_label`) | smazat; zóna z TapHome → `DeviceInfo(suggested_area=device.zone)` — HA nabídne oblast samo, uživatel může změnit |
| `extra_state_attributes` (`taphome_id`, `taphome_name`, …) + `enabled_attributes` | smazat celé — statická metadata patří do device registry, ne do atributů stavu |
| subscribe v `__init__`, nikdy unsubscribe | subscribe v `async_added_to_hass`, odhlášení přes `self.async_on_remove(device.state.changed.subscribe(...))` (Bronze pravidlo *entity-event-setup*) |
| `schedule_update_ha_state` + kontrola `hass is not None` | `self.async_write_ha_state()` z callbacku (event loop) — kontrola odpadá díky správnému místu subscribe |
| `should_poll` cached_property | `_attr_should_poll = False` (třídní atribut) |
| dostupnost přes handler `connection_state` | `available` property čtoucí `hub.connection_state` + `device.state is not None` |

Nový základ (skica):

```python
class TapHomeEntity(Entity):
    _attr_has_entity_name = True
    _attr_should_poll = False

    def __init__(self, hub: TapHomeHub, device: Device) -> None:
        self._hub = hub
        self._device = device
        self._attr_unique_id = f"{hub.location_id}_{device.id}"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, f"{hub.location_id}_{device.id}")},
            name=device.name,
            manufacturer="TapHome",
            suggested_area=device.zone,
            via_device=(DOMAIN, hub.location_id),
        )

    async def async_added_to_hass(self) -> None:
        self.async_on_remove(self._device.state.changed.subscribe(self._handle_state_update))
        self.async_on_remove(self._hub.connection_state.changed.subscribe(self._handle_state_update))

    @property
    def available(self) -> bool:
        return self._hub.connection_state.value is HubConnectionState.CONNECTED
```

Hub samotný = zařízení v registry (`DeviceInfo` s `identifiers={(DOMAIN,
hub.location_id)}`, `name=hub.location_name`, `configuration_url` na lokální
IP) — registruje se v `__init__.py` přes `device_registry`.

Konverzní statické metody (`convert_th_percentage_to_ha_byte`, …) přesunout
do `pytaphome.helpers`, případně nahradit `homeassistant.util.percentage` a
`value_to_brightness` / `brightness_to_value` z `homeassistant.util.color`.

## 2.5 Přepis platforem — společný postup a odchylky

Pro každou platformu (vzor `light.py`):

1. Smazat `TapHome*Config` třídu a `setup_platform`.
2. `async_setup_entry` + filtr přes `platform_for_device` (2.3).
3. Entity dědí z nového `TapHomeEntity`; stavové callbacky zůstávají, jen
   se subscribe přesune do `async_added_to_hass`.
4. `_attr_translation_key` + záznam v `strings.json` pro vedlejší entity.

Odchylky a ztráty funkcí (vědomé, zdokumentovat v docs PR):

- **`light.effect_id`** (párování světla s `MultiValueSwitchDevice` jako
  seznam efektů) — YAML párování dvou zařízení nelze v discovery odvodit.
  V Core verzi **vypustit**; multivalue switch se objeví jako samostatná
  `select` entita vedle světla. Pokud TapHome API umí vztah vyjádřit,
  lze vrátit později samostatným PR.
- Obdobně prověřit `climate.py`, `fan.py`, `humidifier.py`, `cover.py` —
  všechny YAML odkazy na jiná zařízení (`*_id` klíče v configu) buď odvodit
  z API, nebo pro první verzi vypustit. Sepsat inventuru před začátkem
  (grep `get_optional(".*_id"` přes platformy).
- **`button` + `event` z jednoho configu**: v Core vytvoří `ButtonDevice`
  entitu `event` (fyzické stisky, `event_types` = hodnoty `ButtonAction`);
  `button` entitu jen pokud API umožňuje stisk vyvolat.
- `unique_id` override per entita — smazat bez náhrady.

## 2.6 `strings.json` a překlady

- Vytvořit `strings.json`: sekce `config` (kroky, chyby, abort — texty ke
  hotovému config flow), `entity` (translation keys vedlejších entit),
  `issues` (viz 2.7), `selector` dle potřeby.
- Obsah dnešních `translations/en.json` (issues) se přenese do `strings.json`;
  `translations/en.json` v Core se generuje ze `strings.json`.
- **Ostatní jazyky (cs, de, hu, it, sk) se do Core necommitují** — po merge
  se překlady dělají přes Lokalise (developers.home-assistant.io →
  Translations). Připravit si texty, ať je lze po zveřejnění rychle vložit.
- Smazat `translations.py` (vlastní loader) — v Core zakázaný vzor.

## 2.7 Repairs (`taphome_issue_registry.py`)

Zachovat jako plus, ale zredukovat:

- `ip_and_api_url_set` — zaniká (config flow už kombinaci nedovolí).
- `device_not_exposed`, `device_type_mismatch` — zaniká v discovery režimu
  (nevyjmenováváme ID, tudíž nemůže chybět); chybová hlášení nahradí log
  warning při přeskočení nepodporovaného zařízení.
- `core_unavailable` — **nezakládat repair issue**; nedostupnost vyjadřují
  entity `available=False` a `ConfigEntryNotReady`. Repair issue pro běžný
  výpadek by review neprošel (HA to považuje za duplicitní signál).

Výsledek: `taphome_issue_registry.py` se pravděpodobně smaže celý; pokud
zůstane nějaký skutečně opravitelný stav (např. zastaralý firmware hubu),
texty jdou do `strings.json` → `issues`.

## 2.8 `manifest.json`

```json
{
  "domain": "taphome",
  "name": "TapHome",
  "codeowners": ["@martindybal"],
  "config_flow": true,
  "documentation": "https://www.home-assistant.io/integrations/taphome",
  "integration_type": "hub",
  "iot_class": "local_push",
  "quality_scale": "bronze",
  "requirements": ["pytaphome==1.0.0"]
}
```

Změny proti dnešku: smazat `version` (jen pro custom integrace, hassfest ho
v Core odmítne), smazat `issue_tracker` (Core používá centrální tracker),
`documentation` míří na home-assistant.io, přidat `config_flow`,
`quality_scale`, `requirements`. Klíče abecedně (hassfest kontroluje).

Volitelně doplnit `zeroconf`/`dhcp` discovery hubu v LAN, pokud TapHome core
něco inzeruje (mDNS/UPnP) — velké plus pro UX i review; ověřit na reálném
zařízení (`avahi-browse -a`).

## 2.9 Co se maže bez náhrady

| Soubor / funkce | Náhrada |
|---|---|
| `CONFIG_SCHEMA`, YAML `cores:` | config entries |
| `add_entry_request.py`, `taphome_config_entry.py` | discovery + `entity.py` |
| `translations.py`, `translations/*.json` | `strings.json` + Lokalise |
| `use_description_as_*`, `zones`, `labels`, `enabled_attributes`, `language`, `update_interval` | UI HA (`suggested_area`, přejmenování entit, labels) |
| `hacs.json`, `version` v manifestu | — |
| `docs/config-generator` | — (bez YAML nemá smysl) |

## Kontrolní seznam fáze 2

- [ ] `const.py` — DOMAIN + klíče `entry.data` (kontrakt 2.1)
- [ ] `__init__.py` — setup/unload entry, webhook, runtime_data
- [ ] `discovery.py` — `platform_for_device` + testovatelná mapovací tabulka
- [ ] rozhodnutí nejednoznačných výstupů (metadata API / switch_as_x) ověřené na reálném hubu
- [ ] `entity.py` — nový základ dle 2.4
- [ ] `light.py` přepsaný (rozsah PR #1)
- [ ] inventura `*_id` vazeb v ostatních platformách + rozhodnutí co vypustit
- [ ] `strings.json`, smazané vlastní překlady
- [ ] zredukované repairs dle 2.7
- [ ] `manifest.json` dle 2.8
- [ ] hassfest zelený (`python -m script.hassfest`)
