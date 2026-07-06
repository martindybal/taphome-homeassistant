# Fáze 1 — Knihovna `pytaphome` na PyPI

Home Assistant vyžaduje, aby veškerá komunikace s API probíhala přes samostatnou
knihovnu publikovanou na PyPI (pravidlo *dependency-transparency* + review
guideline „no protocol logic in the integration"). Přesouvá se celý dnešní
adresář `taphome_sdk/` — ten už dnes neimportuje nic z Home Assistantu, takže
jde primárně o packaging a několik úprav veřejného API.

## 1.1 Nový repozitář a struktura

Repo: `martindybal/pytaphome` (ověřit dostupnost jména `pytaphome` na PyPI;
záloha: `aiotaphome`).

```
pytaphome/
├── src/pytaphome/
│   ├── __init__.py          # dnešní taphome_sdk/__init__.py (re-exporty)
│   ├── py.typed             # NOVÝ — marker pro typing
│   ├── api.py               # z taphome_api.py
│   ├── hub.py               # z taphome_hub.py
│   ├── device.py
│   ├── device_analog_output.py
│   ├── device_bidirectional.py
│   ├── device_button.py
│   ├── device_digital_output.py
│   ├── device_factory.py
│   ├── device_generic_output_adapter.py
│   ├── device_light.py
│   ├── device_multivalue_switch.py
│   ├── device_thermostat.py
│   ├── device_variable.py
│   ├── exceptions.py        # NOVÝ — viz 1.2.3
│   ├── helpers.py
│   ├── observable.py
│   ├── operation_mode.py
│   ├── switch_state.py
│   └── value_type.py
├── tests/
├── pyproject.toml
├── README.md                # popis API + příklad použití
├── CHANGELOG.md
└── LICENSE                  # MIT (převzít)
```

## 1.2 Nutné úpravy veřejného API knihovny

Tyto změny vyžaduje buď přímo review Core, nebo je potřebuje integrace
(config flow, `ConfigEntryNotReady`/`ConfigEntryAuthFailed`).

### 1.2.1 Injektovaná `aiohttp.ClientSession`

HA pravidlo *inject-websession*: integrace předává session z
`async_get_clientsession(hass)`, knihovna si nesmí vytvářet vlastní
(resp. jen jako fallback).

```python
class TapHomeApi:
    def __init__(self, api_url: str, token: str, session: aiohttp.ClientSession) -> None: ...

class TapHomeHubFactory:
    @staticmethod
    async def async_connect(api_url: str, token: str, session: aiohttp.ClientSession) -> TapHomeHub: ...
```

### 1.2.2 Odstranit `aiohttp.web.Request` z rozhraní hubu

`TapHomeHub.async_handle_webhook(request: aiohttp.web.Request)` váže knihovnu
na serverovou část aiohttp. Změnit na přijetí už rozparsovaných dat:

```python
async def async_handle_webhook(self, payload: dict[str, Any]) -> None: ...
```

Parsování `Request` → `dict` (a odpověď webhookují) zůstane v integraci.
Stejně tak import `from aiohttp.web import Request` zmizí z `hub.py`.

### 1.2.3 Typované výjimky místo návratových stavů

Dnes `TapHomeHubFactory.async_connect` vrací hub i při neúspěchu a volající
kontroluje `hub.connection_state`. Config flow a `async_setup_entry` potřebují
rozlišit „špatný token" od „hub nedostupný":

```python
# exceptions.py
class TapHomeError(Exception): ...
class TapHomeConnectionError(TapHomeError): ...      # síť, timeout, 5xx
class TapHomeAuthenticationError(TapHomeError): ...  # 401/403 — špatný token
```

- `TapHomeApi` mapuje `ClientResponseError` na tyto výjimky.
- `TapHomeHubFactory.async_connect` při neúspěchu **vyhazuje**, nevrací
  odpojený hub. `HubConnectionState` zůstává pro průběžné výpadky za běhu
  (observable, na který se váže dostupnost entit).

### 1.2.4 Identita hubu pro `unique_id` a device registry

Integrace potřebuje stabilní identifikátor instalace (unique_id config entry,
`DeviceInfo` hubu). `Location` už v API existuje — zajistit, aby `TapHomeHub`
po připojení vystavoval:

```python
hub.location_id: str      # stabilní ID instalace z API
hub.location_name: str
```

Ověřit, co přesně TapHome API vrací (endpoint `location`), a doplnit do
`Location.from_dict`. Pokud API stabilní ID nedává, použít jako unique_id
token-hash nebo nechat config flow řešit (mimo rozsah této fáze — jen
zdokumentovat, co knihovna umí poskytnout).

### 1.2.5 Metadata typu zařízení pro discovery

`DeviceFactory.create_device` dnes typ odvozuje z `supported_values` — to
zůstává. Navíc vystavit na `Device`/`DeviceMetadata` surové `type` pole
z API odpovědi (pokud ho API vrací), aby integrace mohla rozhodovat
nejednoznačné případy (DigitalOutput = světlo vs. spínač), viz fáze 2.3.

### 1.2.6 Řízené ukončení

`TapHomeHub` má `periodic_refresh_task` a odběry událostí. Doplnit:

```python
async def async_disconnect(self) -> None:
    """Cancel periodic refresh a uvolnit odběry."""
```

Volá se z `async_unload_entry`. Bez toho neprojde test unloadu
(lingering tasks — pytest plugin HA je detekuje a shodí test).

### 1.2.7 `Event`/`ObservableValue` — párové odhlašování

Entity se musí umět odhlásit (`async_will_remove_from_hass`). `Event` už má
`subscribe`/`+=`; zkontrolovat a případně doplnit `unsubscribe`/`-=` a vracet
z `subscribe` callable pro odhlášení (vzor HA):

```python
unsubscribe = device.state.changed.subscribe(handler)  # vrací callable
```

## 1.3 Packaging

`pyproject.toml` (hatchling):

```toml
[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[project]
name = "pytaphome"
version = "1.0.0"
description = "Async Python client for the TapHome smart home API"
readme = "README.md"
license = "MIT"
requires-python = ">=3.13"        # HA 2026.x vyžaduje 3.13
dependencies = ["aiohttp>=3.9"]

[project.urls]
Repository = "https://github.com/martindybal/pytaphome"
```

- Python floor držet shodný s aktuálním HA (dnes 3.13; před odesláním Core PR
  ověřit v `home-assistant/core/pyproject.toml`).
- Verzování: semver. Každá změna API knihovny = release + bump v manifestu
  integrace (Core neakceptuje git/URL závislosti, jen pinované PyPI verze
  `pytaphome==x.y.z`).

## 1.4 Testy knihovny

Reviewer Core si knihovnu otevře — musí vypadat udržovaně.

- `pytest` + `pytest-asyncio`; HTTP mock přes `aioresponses`.
- `tests/fixtures/*.json` — reálné (anonymizované) odpovědi TapHome API:
  `location`, `getAllDevicesValues`, jednotlivé typy zařízení. Tytéž fixtures
  se pak zrecyklují v testech integrace v Core (fáze 3).
- Pokrýt: `DeviceFactory` (každá větev → správný typ zařízení),
  mapování výjimek (401 → `TapHomeAuthenticationError`, timeout →
  `TapHomeConnectionError`), webhook payload → aktualizace stavu zařízení,
  `ObservableValue`/`Event` subscribe/unsubscribe, reconnect logika hubu.
- Cíl pokrytí: ≥ 90 %.

## 1.5 CI a publikace

GitHub Actions:

- `ci.yml`: ruff check + format, `mypy --strict src/`, pytest s coverage.
- `release.yml`: build + publish na PyPI přes **trusted publishing** (OIDC,
  bez API tokenů), spouštěný tagem `v*`. HA pravidlo
  *dependency-transparency* vyžaduje, aby release šel dohledatelně
  z veřejného zdroje.

## 1.6 Dopad na tento repozitář (custom integrace)

Po vydání `pytaphome==1.0.0`:

1. Smazat `taphome_sdk/`.
2. Všechny importy `from .taphome_sdk import ...` → `from pytaphome import ...`.
3. `manifest.json`: `"requirements": ["pytaphome==1.0.0"]`.
4. Přizpůsobit volání změněným signaturám (session, výjimky, webhook payload,
   `async_disconnect`).
5. Vydat jako release custom integrace — poslouží jako beta test knihovny
   na reálných instalacích **před** odesláním do Core.

## Kontrolní seznam fáze 1

Realizováno v repu [taphome-sdk](https://github.com/martindybal/taphome-sdk)
(balíček `taphome-sdk`, ne `pytaphome`), větev `claude/sdk-package`:

- [x] Repo `taphome-sdk`, přesun kódu (src layout), `py.typed`
- [x] 1.2.1 injektovaná session (`TapHomeApi`/`TapHomeHub`/factory)
- [x] 1.2.2 webhook bez `aiohttp.web` (přijímá rozparsovaný `dict`)
- [x] 1.2.3 `exceptions.py` (`TapHomeError`, `TapHomeAuthError`, `TapHomeConnectionError`)
- [x] 1.2.4 `location_id` / `location_name` (existovalo v `Location`)
- [x] 1.2.5 typová metadata zařízení (`DeviceMetadata.device_type`/`usage` — existovalo)
- [x] 1.2.6 ukončení přes `hub.disconnect()` (ruší periodic refresh; využívá `async_unload_entry`)
- [x] 1.2.7 odhlašování odběrů (`Event.unsubscribe`/`-=` — existovalo)
- [x] pyproject, README s příkladem, CHANGELOG
- [x] testy (30), ruff, mypy zelené (striktní mypy zatím ne — TODO)
- [x] CI + trusted publishing workflow
- [ ] release `1.0.0` na PyPI — postup v [pypi-setup.md](pypi-setup.md)
- [x] custom integrace přepnutá na externí `taphome_sdk` (`sdk_locator.py` pro lokální vývoj)
- [ ] ověření na reálné instalaci
