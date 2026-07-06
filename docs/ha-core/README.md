# TapHome → Home Assistant Core: implementační plán

Podrobný, prováděcí plán pro přesun integrace do `home-assistant/core`.
Přehledové zdůvodnění a tabulka „požadavek vs. současný stav" je v
[../ha-core-submission-plan.md](../ha-core-submission-plan.md).

**Poznámka:** UI konfigurace (config flow) je řešena samostatně a tento plán ji
nerozpracovává. Dokument [02-integration-rewrite.md](02-integration-rewrite.md)
pouze definuje rozhraní, které config flow musí naplnit (obsah `entry.data`,
`unique_id` config entry), aby na něj zbytek integrace mohl navázat.

## Dokumenty

| Fáze | Dokument | Obsah |
|---|---|---|
| 1 | [01-pytaphome-library.md](01-pytaphome-library.md) | Vyčlenění SDK do PyPI balíčku — **hotovo** jako [`taphome-sdk`](https://github.com/martindybal/taphome-sdk); zbývá release na PyPI ([pypi-setup.md](pypi-setup.md)) |
| 2 | [02-integration-rewrite.md](02-integration-rewrite.md) | Přepis integrace na config entries: `__init__.py`, discovery entit, `entity.py`, webhook, `strings.json`, přepis platforem, odstraňované funkce |
| 3 | [03-tests-quality-scale.md](03-tests-quality-scale.md) | Testy v Core, `quality_scale.yaml`, Bronze pravidla, lokální tooling (hassfest, ruff, mypy) |
| 4 | [04-submission.md](04-submission.md) | Tři pull requesty: brands, dokumentace, core — obsah, pořadí, strategie malých PR |
| 5 | [05-maintenance-migration.md](05-maintenance-migration.md) | Review proces, povinnosti codeownera, migrace stávajících HACS uživatelů |

## Pořadí prací a průběh

Fáze 1 blokuje vše ostatní (Core PR nesmí obsahovat kód protokolu).
Brands PR (fáze 4a) je nezávislý a může běžet souběžně.

- [x] **1. SDK v samostatném repu** — [taphome-sdk](https://github.com/martindybal/taphome-sdk), balíček `taphome-sdk`: src layout, injektovaná session, typované výjimky, webhook bez `aiohttp.web`, py.typed, 30 testů, CI, release workflow (větev `claude/sdk-package`)
- [ ] **1b. Release `1.0.0` na PyPI** — viz [pypi-setup.md](pypi-setup.md); poté doplnit `requirements` do manifestu
- [ ] **4a. Brands PR** — logo a ikona v `home-assistant/brands`
- [ ] **2. Přepis integrace** ve forku `home-assistant/core` (rozsah prvního PR: `light`)
- [ ] **3. Testy + `quality_scale.yaml`** (Bronze)
- [ ] **4b. Docs PR** — `home-assistant.io`
- [ ] **4c. Core PR #1** — `__init__` + config flow + `entity` + `light` + testy
- [ ] **4d. Follow-up PRs** — zbylé platformy po jednom (`sensor`, `cover`, `climate`, `switch`, `binary_sensor`, `select`, `fan`, `humidifier`, `valve`, `button`, `event`, `time`)
- [ ] **5. Migrace uživatelů** — poslední release custom integrace, archivace HACS repa

## Cílová struktura v Core

```
homeassistant/components/taphome/
├── __init__.py          # async_setup_entry / async_unload_entry
├── config_flow.py       # (hotové, mimo rozsah tohoto plánu)
├── const.py             # DOMAIN, klíče entry.data
├── entity.py            # TapHomeEntity — společný základ (pravidlo common-modules)
├── light.py             # PR #1; další platformy v follow-up PRs
├── manifest.json
├── strings.json
├── icons.json           # volitelné
└── quality_scale.yaml

tests/components/taphome/
├── conftest.py
├── fixtures/            # JSON odpovědi TapHome API
├── test_config_flow.py
├── test_init.py
└── test_light.py        # + snapshoty (syrupy)
```
