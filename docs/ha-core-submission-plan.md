# Plán: TapHome jako oficiální integrace v Home Assistant Core

Cíl: dostat integraci `taphome` do repozitáře `home-assistant/core` tak, aby prošla review napoprvé bez zásadních výhrad.

> **Podrobný implementační plán** jednotlivých fází je rozpracován v [ha-core/](ha-core/README.md).

## Souhrn — proč integrace v současné podobě neprojde

Home Assistant má pro **nové** integrace tvrdé požadavky (dev docs + Integration Quality Scale, minimálně tier **Bronze**). Současný stav proti nim:

| Požadavek Core | Současný stav | Verdikt |
|---|---|---|
| UI config flow (`config_flow.py`), žádná YAML konfigurace | Čistě YAML přes `async_setup` + zastaralé `load_platform` | ❌ blokující |
| Komunikace s API výhradně přes externí knihovnu publikovanou na PyPI | `taphome_sdk` je přibalené uvnitř integrace | ❌ blokující |
| Testy (100% pokrytí config flow, testy setupu) | Žádné testy | ❌ blokující |
| Automatický discovery zařízení z hubu, žádné ruční seznamy entit | Každá entita se vyjmenovává v YAML (`lights:`, `covers:`…) | ❌ blokující |
| Pojmenování entit řeší HA UI, ne konfigurace integrace | `use_description_as_entity_id`, `zones`/`labels` mapping, `language` | ❌ nutno odstranit |
| `strings.json` + překlady ve formátu Core | Vlastní `translations.py` + `translations/*.json` (formát custom integrace) | ❌ přepsat |
| `entry.runtime_data`, typovaný `ConfigEntry` | `hass.data[TAPHOME_PLATFORM]` s netypovanými dicty | ❌ přepsat |
| `manifest.json` bez `version`, s `config_flow: true`, `requirements`, `quality_scale` | Má `version` (jen pro custom), prázdné `requirements` | ❌ upravit |
| `has_entity_name = True`, unikátní ID, DeviceInfo | Nutno ověřit/dorovnat u všech platforem | ⚠️ |
| SDK bez závislosti na HA, jen aiohttp | Splněno — SDK neimportuje homeassistant | ✅ dobrý základ |
| `local_push`, async, moderní Python (dataclasses, slots) | Splněno | ✅ |

Dobrá zpráva: architektonicky nejtěžší část (čisté async SDK oddělené od HA, push model přes webhook/observable) už hotová je. Zbývající práce je hlavně „přebalení" do tvaru, který Core vyžaduje.

---

## Fáze 1 — Vyčlenění SDK na PyPI (předpoklad všeho ostatního)

Core PR nesmí obsahovat žádnou logiku protokolu — vše musí být v samostatné knihovně.

1. **Nový repozitář** (např. `martindybal/pytaphome`), přesun celého `taphome_sdk/` do něj.
   - Název balíčku např. `pytaphome` nebo `aiotaphome` (ověřit kolizi na PyPI).
   - `pyproject.toml`, OSI licence (MIT už máš), jediná runtime závislost: `aiohttp`.
2. **CI + testy knihovny** — GitHub Actions: ruff, mypy, pytest. Reviewer se dívá, jestli je knihovna udržovaná a testovaná (pravidlo *dependency-transparency*: build z veřejného zdroje, publikace přes trusted publisher).
3. **Typování**: knihovna by měla mít `py.typed` marker a projít `mypy --strict` — Core na typování integrace navazuje.
4. **Publikace na PyPI** (verze `1.0.0`), releasy tagované v gitu.
5. V integraci pak `manifest.json` → `"requirements": ["pytaphome==1.0.0"]`.

Odhad: 2–4 dny (kód se jen přesouvá, práce je v packagingu, CI a testech).

## Fáze 2 — Přepis integrace na config entries

1. **`config_flow.py`** — UI průvodce:
   - Kroky: zadání připojení (cloud token / lokální IP + token) → *test-before-configure* (ověřit spojení a token, ukázat chybu `cannot_connect` / `invalid_auth`).
   - `unique_id` config entry = ID hubu/core (pravidlo *unique-config-entry* — zabránit dvojímu přidání téhož hubu).
   - Vícero TapHome cores = vícero config entries (dnešní `cores:` seznam zaniká).
   - Volitelně `reauth` flow (Silver) a `reconfigure` flow — doporučuji rovnou, review to hodnotí kladně.
2. **`__init__.py`**:
   - `async_setup_entry` / `async_unload_entry`, platformy přes `hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)`.
   - *test-before-setup*: při startu ověřit dostupnost hubu, jinak `ConfigEntryNotReady`.
   - Typovaný entry: `type TapHomeConfigEntry = ConfigEntry[TapHomeRuntimeData]`, data do `entry.runtime_data`.
3. **Automatický discovery entit**: entity se vytvoří ze všeho, co hub přes API vystaví (`device_factory` už mapování umí). Žádné YAML seznamy. Uživatel nechtěné entity zakáže v UI.
4. **Odstranit celou vrstvu pojmenování**: `use_description_as_entity_id`, `use_description_as_name`, `zones`, `labels`, `enabled_attributes`, `language`. V Core platí: `_attr_has_entity_name = True`, jméno entity z `translation_key` nebo z názvu zařízení; přejmenování/oblasti řeší uživatel v UI.
5. **Zařízení**: každé TapHome zařízení = záznam v device registry (`DeviceInfo` s `identifiers`, `manufacturer="TapHome"`, `model`, `via_device` na hub).
6. **Webhook**: registrace webhoku přesunout do setupu entry a rušit při unloadu; ID webhoku generovat, ne brát z YAML.
7. **Překlady**: `strings.json` (config flow texty, `entity` translation keys, `issues` pro repairs) — stávající `translations/*.json` obsah se přemapuje; do Core se ale commitá jen `strings.json` + `translations/en.json`, ostatní jazyky jdou přes Lokalise.
8. **`icons.json`** pro vlastní ikony entit (pokud dávají smysl).
9. **Repairs** (`taphome_issue_registry`) zachovat — je to plus — ale texty přes `strings.json`.

Odhad: 1–2 týdny. Doporučuji vyvíjet rovnou ve forku `home-assistant/core` (dev container), ať od začátku běží `hassfest`, ruff a pytest v prostředí Core.

## Fáze 3 — Kvalita: Bronze (povinné minimum) a testy

Do integrace přidat `quality_scale.yaml` se stavem všech pravidel. Bronze mimo jiné znamená:

- `config-flow` + plné pokrytí config flow testy (fakticky 100 % `config_flow.py`),
- `test-before-configure`, `test-before-setup`, `unique-config-entry`,
- `entity-unique-id`, `has-entity-name`, `runtime-data`, `appropriate-polling` (u nás push → OK),
- `action-setup` (služby registrovat v `async_setup`, pokud nějaké budou — dnes žádné vlastní služby nemáš, takže N/A),
- `common-modules` (koordinátor/entity do `coordinator.py`/`entity.py`),
- dokumentační pravidla (`docs-high-level-description`, `docs-installation-instructions`, `docs-removal-instructions`, `docs-actions`).

**Testy** (`tests/components/taphome/`):
- `test_config_flow.py` — všechny cesty: úspěch, špatný token, nedostupný hub, duplicitní entry, reauth/reconfigure.
- `test_init.py` — setup/unload, `ConfigEntryNotReady`.
- Testy platforem se snapshoty (`syrupy`) — mock knihovny přes `pytest` fixtures (Core pattern: mockovat `pytaphome`, ne HTTP).

Odhad: 1 týden.

## Fáze 4 — Tři pull requesty (v tomto pořadí)

1. **`home-assistant/brands`** — logo + ikona TapHome (PNG dle specifikace). Malý PR, schvaluje se rychle; bez něj hassfest v Core PR neprojde.
2. **`home-assistant/home-assistant.io`** — dokumentační stránka `source/_integrations/taphome.markdown`: popis, co integrace umí, instalace, odebrání, podporovaná zařízení, troubleshooting. Linkuje se z Core PR.
3. **`home-assistant/core`** — samotný kód. **Zásadní: nový integrace se přijímá po malých částech.** První PR = config flow + `__init__` + **1–2 platformy** (doporučuji `light` + `sensor` nebo jen `light`) + testy. Zbylých ~11 platforem (climate, cover, fan, humidifier, valve, select, switch, binary_sensor, button, event, time) jde jako série follow-up PRs, každý malý a s testy. PR s 13 platformami najednou reviewer vrátí.

Před odesláním: podepsat CLA, přidat se do `CODEOWNERS` (generuje hassfest z manifestu), projít `script/hassfest`, `ruff`, `mypy`.

## Fáze 5 — Review a údržba

- Review nové integrace typicky trvá **týdny až měsíce** — počítat s několika koly připomínek; PR, na který autor týden nereaguje, se zavírá jako stale (draft → ready pomáhá).
- Jako codeowner budeš dostávat ping na issues/PRs týkající se integrace — je to trvalý závazek.
- **Migrace stávajících uživatelů custom integrace**: doména `taphome` custom verze překryje Core verzi. Plán: po zveřejnění v Core vydat poslední verzi custom integrace, která uživatele přes repair issue vyzve k odinstalaci custom verze a nastavení přes UI, a HACS repozitář archivovat. YAML import flow do Core PR nedávat — u nových integrací se import z YAML nepřijímá.

## Doporučené pořadí prací

1. PyPI knihovna `pytaphome` (fáze 1) — bez ní nejde nic dál.
2. Brands PR (fáze 4.1) — nezávislé, může běžet hned.
3. Přepis na config entries + discovery ve forku core (fáze 2), zúžený na `light`.
4. Testy + `quality_scale.yaml` (fáze 3).
5. Docs PR a Core PR (fáze 4.2–4.3).
6. Follow-up PRs s dalšími platformami, jeden po druhém.

Celkový odhad čisté práce: **3–5 týdnů**, plus kalendářní čas na review.
