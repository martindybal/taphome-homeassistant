# Fáze 4 — Odeslání: tři pull requesty

Pořadí: **brands → docs → core**. Brands musí být sloučený dřív, než core PR
projde hassfestem; docs PR se linkuje z core PR a mergují se společně.

Před prvním PR: podepsat CLA (odkaz nabídne bot při otevření PR, lze i předem
na https://www.home-assistant.io/developers/cla/).

## 4a Brands PR (`home-assistant/brands`)

1. Zkontrolovat, zda už `taphome` neexistuje v `custom_integrations/taphome/`
   (kvůli HACS tam možná je). Pokud ano, PR ho **přesune** do
   `core_integrations/taphome/`; pokud ne, vytvoří nový.
2. Soubory (PNG, průhledné pozadí, čtvercové ikony):
   - `core_integrations/taphome/icon.png` — 256×256,
   - `core_integrations/taphome/icon@2x.png` — 512×512,
   - `core_integrations/taphome/logo.png` + `logo@2x.png` — pokud má TapHome
     podélné logo; jinak se použije ikona.
3. Ověřit práva k použití loga TapHome (ideálně písemný souhlas výrobce —
   reviewer se může zeptat).
4. PR je malý, schvaluje se rychle, ale merguje se zpravidla až s core PR —
   otevřít brzy a odkázat z core PR.

## 4b Docs PR (`home-assistant/home-assistant.io`)

Nový soubor `source/_integrations/taphome.markdown`. Front matter:

```yaml
---
title: TapHome
description: Instructions on how to integrate TapHome devices with Home Assistant.
ha_category:
  - Hub
  - Light
ha_release: "2026.X"        # doplní se podle milestone core PR
ha_iot_class: Local Push
ha_config_flow: true
ha_codeowners:
  - '@martindybal'
ha_domain: taphome
ha_integration_type: hub
ha_platforms:
  - light                   # roste s follow-up PRs
ha_quality_scale: bronze
---
```

Povinné sekce (vynucují je docs-* pravidla Bronze):

1. **Úvod** — co je TapHome, co integrace umí (high-level, bez marketingu).
2. **Prerequisites** — jak v TapHome aplikaci zapnout API a získat token,
   která zařízení je nutné „exposnout" do API.
3. `{% include integrations/config_flow.md %}` + popis polí (host, token).
4. **Supported devices** — tabulka typů zařízení → entity (z fáze 2.3),
   včetně poznámky o `switch_as_x` pro univerzální výstupy.
5. **Data updates** — push přes webhook + lokální spojení; jak nastavit
   webhook v TapHome, pokud vyžaduje ruční krok.
6. **Known limitations** — vypuštěné YAML funkce (efekty světel apod.),
   odkaz na migraci z custom integrace.
7. **Troubleshooting** — nedostupný hub, neplatný token, zařízení se
   neobjevuje (není exposnuté v API).
8. **Removing the integration** — `{% include integrations/remove_device_service.md %}`.

Markdown pravidla webu: řádky nelámat uprostřed vět, US English, testovat
lokálně `rake preview` nebo nechat na CI.

## 4c Core PR #1 (`home-assistant/core`)

**Rozsah**: `__init__.py`, `config_flow.py`, `const.py`, `entity.py`,
`discovery.py`, `light.py`, `manifest.json`, `strings.json`,
`quality_scale.yaml` + testy + regenerované soubory
(`requirements_all.txt`, `requirements_test_all.txt`, `CODEOWNERS`,
`homeassistant/generated/*` — vše generuje `script.hassfest` a
`script.gen_requirements_all`, needitovat ručně).

Postup:

1. Branch z `dev`, např. `taphome-init`.
2. Squash lokální historie do smysluplných commitů (`Add TapHome integration`).
3. Otevřít PR proti `dev`; šablona PR — vyplnit poctivě checklist:
   - typ změny: „New integration",
   - odkaz na docs PR (4b) a brands PR (4a),
   - `quality_scale.yaml` hotový.
4. Popis PR: stručně co je TapHome, architektura (pytaphome, push webhook,
   discovery mapování), vědomé limity první verze a plán follow-upů —
   předejde to dotazům v review.
5. Hlídat CI; na připomínky reagovat do několika dní (stale bot zavírá
   neaktivní PR po ~7 dnech bez reakce autora).

Časté připomínky, na které se připravit dopředu:

- „proč tato entita nemá `translation_key`" — mít všechny vedlejší entity
  přeložené,
- „tohle patří do knihovny" — jakákoli logika interpretující API data
  (mapování hodnot, výpočty) musí být v `pytaphome`,
- žádost o zmenšení PR — proto jen `light`,
- dotazy na discovery mapování nejednoznačných výstupů — mít odpověď
  podloženou API metadaty (fáze 2.3).

## 4d Follow-up PRs (po merge PR #1)

Jeden PR = jedna platforma + její testy + rozšíření `ha_platforms` v docs.
Doporučené pořadí podle hodnoty pro uživatele a rizikovosti review:

1. `sensor` + `binary_sensor` (VariableDevice) — jednoduché, read-only,
2. `cover` (BidirectionalDevice),
3. `climate` (ThermostatDevice) — největší; připravit se na diskusi o
   HVAC módech,
4. `switch` (DigitalOutputDevice + switch_as_x dokumentace),
5. `select` (MultiValueSwitchDevice),
6. `event` (+ případně `button`),
7. `fan`, `humidifier`, `valve`, `time` — podle poptávky.

Každý follow-up drobný (< ~500 řádků včetně testů), vždy se snapshot testy.
Mezi PRs udržovat `pytaphome` releasy podle potřeby (bump verze v manifestu
je samostatný malý PR, pokud nesouvisí s platformou).

## Kontrolní seznam fáze 4

- [ ] CLA podepsané
- [ ] brands PR otevřený (ikona 256/512, případný přesun z custom_integrations)
- [ ] docs PR otevřený se všemi povinnými sekcemi
- [ ] core PR #1: hassfest, ruff, mypy, pytest, coverage — vše zelené v CI
- [ ] generované soubory regenerovány skripty, ne ručně
- [ ] popis PR s architekturou a plánem follow-upů
- [ ] po merge: naplánované follow-up PRs dle 4d
