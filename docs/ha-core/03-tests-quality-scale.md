# Fáze 3 — Testy a Integration Quality Scale (Bronze)

Nové integrace se přijímají minimálně na tieru **Bronze**. Bez plného pokrytí
config flow testy PR neprojde CI (`hassfest` + coverage gate).

## 3.1 Vývojové prostředí

1. Fork `home-assistant/core`, clone, branch z `dev` (ne z `master`).
2. Dev container (doporučeno) nebo `script/setup` + `source venv/bin/activate`.
3. Lokální smyčka:

```bash
python -m script.hassfest                                  # manifest, strings, generované soubory
ruff check homeassistant/components/taphome tests/components/taphome
ruff format --check ...
mypy homeassistant/components/taphome
pytest tests/components/taphome --cov=homeassistant/components/taphome --cov-report=term-missing
```

4. Po přidání `requirements` do manifestu: `python -m script.gen_requirements_all`
   (regeneruje `requirements_all.txt` a `requirements_test_all.txt` — commitují
   se spolu s PR).
5. Přidat `homeassistant.components.taphome.*` do `.strict-typing` — striktní
   mypy je pro nové integrace očekávaný standard.

## 3.2 Struktura testů

```
tests/components/taphome/
├── conftest.py
├── fixtures/
│   ├── location.json
│   └── devices_values.json      # reprezentativní mix typů zařízení
├── snapshots/                   # generuje syrupy
├── test_config_flow.py
├── test_init.py
└── test_light.py
```

### `conftest.py` — klíčové fixtures

Vzor Core: **mockuje se knihovna `pytaphome`, ne HTTP**.

```python
@pytest.fixture
def mock_config_entry() -> MockConfigEntry:
    return MockConfigEntry(
        domain=DOMAIN,
        title="TapHome",
        data={CONF_HOST: "10.0.0.5", CONF_TOKEN: "test-token", CONF_WEBHOOK_ID: "wh-id"},
        unique_id="location-1",
    )

@pytest.fixture
def mock_hub() -> Generator[AsyncMock]:
    with (
        patch("homeassistant.components.taphome.TapHomeHubFactory", autospec=True) as factory,
        patch("homeassistant.components.taphome.config_flow.TapHomeHubFactory", new=factory),
    ):
        hub = factory.async_connect.return_value
        hub.location_id = "location-1"
        hub.location_name = "Test Home"
        hub.devices = _devices_from_fixture("devices_values.json")
        yield hub

@pytest.fixture
def mock_setup_entry() -> Generator[AsyncMock]:
    with patch("homeassistant.components.taphome.async_setup_entry", return_value=True) as m:
        yield m
```

Zařízení ve fixtures stavět přes reálné `pytaphome.DeviceFactory` z JSON
odpovědí API (sdílené s testy knihovny, fáze 1.4) — testuje se tak i skutečná
integrace s knihovnou, mockuje se jen síťová vrstva factory/hubu.

## 3.3 Testy po souborech

### `test_config_flow.py` (Bronze: *config-flow-test-coverage* = 100 % souboru)

Config flow je hotový; testy pokryjí každou cestu:

- happy path: user step → entry vytvořena se správnými `data`, `title`,
  `unique_id`; ověřit, že flow končí `CREATE_ENTRY` a `mock_setup_entry`
  byl zavolán,
- `TapHomeAuthenticationError` → `errors={"base": "invalid_auth"}` a **flow
  lze dokončit po opravě** (test pokračuje druhým, úspěšným kolem — review
  to vyžaduje),
- `TapHomeConnectionError` → `errors={"base": "cannot_connect"}` + recovery,
- neočekávaná výjimka → `errors={"base": "unknown"}` + recovery,
- duplicitní hub (`unique_id` shodné) → `abort`, `reason="already_configured"`,
- reauth flow: úspěch (entry aktualizována, `reason="reauth_successful"`)
  i neúspěch; reconfigure flow analogicky — pokud jsou implementovány.

### `test_init.py`

- úspěšný setup → `entry.state is ConfigEntryState.LOADED`, webhook
  zaregistrován,
- `TapHomeConnectionError` při connectu → `SETUP_RETRY`,
- `TapHomeAuthenticationError` → `SETUP_ERROR` + spuštěný reauth flow
  (`any(entry.async_get_active_flows(hass, {"reauth"}))`),
- unload → `NOT_LOADED`, webhook odregistrován, `hub.async_disconnect`
  zavolán (žádné lingering tasks — plugin HA to jinak shodí),
- webhook: POST na `/api/webhook/{id}` → `hub.async_handle_webhook`
  dostal payload (přes `hass_client_no_auth` fixture).

### `test_light.py` (a další platformy ve follow-up PRs)

Vzor snapshot testů Core:

```python
async def test_entities(hass, mock_hub, mock_config_entry, entity_registry, snapshot) -> None:
    with patch("homeassistant.components.taphome.PLATFORMS", [Platform.LIGHT]):
        await setup_integration(hass, mock_config_entry)
    await snapshot_platform(hass, entity_registry, snapshot, mock_config_entry.entry_id)
```

Plus cílené testy chování:

- `turn_on` s brightness/color_temp/hs → správné volání na mock zařízení
  (`async_set_output_value(0.5)` apod. — ověřuje konverze 0–255 ↔ 0–1),
- push update: vyvolání `device.state.changed` → nový stav v
  `hass.states`, bez pollingu,
- výpadek spojení: `hub.connection_state` → entity `unavailable`,
- discovery filtr: zařízení nepatřící platformě nevytvoří entitu.

## 3.4 `quality_scale.yaml`

Soubor v adresáři integrace; hassfest ho validuje proti deklarovanému
`quality_scale: bronze` v manifestu. Očekávané stavy Bronze pravidel:

| Pravidlo | Stav | Poznámka |
|---|---|---|
| `action-setup` | exempt | integrace nemá vlastní služby |
| `appropriate-polling` | exempt | čistý push (`local_push`) |
| `brands` | done | fáze 4a |
| `common-modules` | done | `entity.py`; koordinátor nemáme (push) — exempt komentářem u `coordinator.py` části |
| `config-flow` | done | hotové |
| `config-flow-test-coverage` | done | 3.3 |
| `dependency-transparency` | done | fáze 1.5 |
| `docs-actions` | exempt | žádné služby |
| `docs-high-level-description` | done | fáze 4b |
| `docs-installation-instructions` | done | fáze 4b |
| `docs-removal-instructions` | done | fáze 4b |
| `entity-event-setup` | done | subscribe v `async_added_to_hass` (2.4) |
| `entity-unique-id` | done | `{location_id}_{device_id}` |
| `has-entity-name` | done | 2.4 |
| `runtime-data` | done | 2.2 |
| `test-before-configure` | done | config flow testuje spojení |
| `test-before-setup` | done | `ConfigEntryNotReady` / `ConfigEntryAuthFailed` |
| `unique-config-entry` | done | `location_id` jako unique_id |

Formát souboru:

```yaml
rules:
  action-setup:
    status: exempt
    comment: The integration does not register any custom services.
  appropriate-polling:
    status: exempt
    comment: The integration is push based (webhook + persistent hub connection).
  brands: done
  # ...
```

Silver/Gold pravidla lze rovnou označit `done`, pokud je splňujeme
(`reauthentication-flow`, `parallel-updates`, `entity-translations`,
`diagnostics`…) — zvyšuje to důvěryhodnost PR, ale neblokuje. Doporučuji
rovnou splnit levná pravidla: `parallel-updates: 0` v každé platformě
(push integrace), `diagnostics.py` (výpis zařízení hubu s redakcí tokenu),
`entity-category` u diagnostických entit.

## Kontrolní seznam fáze 3

- [ ] fork + dev prostředí, hassfest/ruff/mypy/pytest smyčka běží
- [ ] `.strict-typing` záznam, mypy zelené
- [ ] `conftest.py` + fixtures z reálných API odpovědí
- [ ] `test_config_flow.py` — 100 % pokrytí `config_flow.py`, včetně recovery cest
- [ ] `test_init.py` — setup/retry/auth/unload/webhook
- [ ] `test_light.py` — snapshoty + chování + konverze
- [ ] `quality_scale.yaml` kompletní, hassfest zelený
- [ ] celkové pokrytí složky ≥ 95 %
