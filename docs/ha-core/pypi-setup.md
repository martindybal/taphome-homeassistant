# Návod: nastavení PyPI a publikace `taphome-sdk`

Publikace používá **trusted publishing** (OIDC) — v repozitáři ani na GitHubu
se neukládá žádný API token či heslo. PyPI ověří, že build přichází
z konkrétního workflow konkrétního repozitáře.

## 1. Účet na PyPI

1. Registrace na https://pypi.org/account/register/ (pokud účet ještě není).
2. Zapnout 2FA (Account settings → Two factor authentication) — bez 2FA nelze
   spravovat projekty.

## 2. Trusted publisher pro nový projekt (pending publisher)

Projekt `taphome-sdk` na PyPI ještě neexistuje — vytvoří se automaticky prvním
publishem přes tzv. *pending publisher*:

1. https://pypi.org/manage/account/publishing/ → sekce **Add a new pending publisher**.
2. Vyplnit přesně:
   - **PyPI Project Name**: `taphome-sdk`
   - **Owner**: `martindybal`
   - **Repository name**: `taphome-sdk`
   - **Workflow name**: `release.yml`
   - **Environment name**: `pypi`
3. Uložit. (Platí 90 dní — do té doby je potřeba provést první release.)

## 3. GitHub environment

Workflow `release.yml` publikuje z environmentu `pypi` (jméno musí sedět
s krokem 2):

1. GitHub → repo `taphome-sdk` → **Settings → Environments → New environment**
   → název `pypi`.
2. Volitelně doporučeno: **Required reviewers** = ty sám — každý publish na
   PyPI pak vyžaduje ruční potvrzení, ochrana proti omylem vydanému tagu.

Žádné secrets se nenastavují — OIDC token vystavuje GitHub za běhu
(`permissions: id-token: write` ve workflow).

## 4. První release

1. Mergnout větev `claude/sdk-package` do `main`.
2. GitHub → **Releases → Draft a new release**:
   - Tag: `v1.0.0` (create new tag on publish, target `main`),
   - Title: `v1.0.0`, popis z `CHANGELOG.md`.
3. **Publish release** → spustí se workflow `Release to PyPI`
   (build → publish). Po doběhnutí je balíček na
   https://pypi.org/project/taphome-sdk/.
4. Ověření: `pip install taphome-sdk==1.0.0`.

## 5. Po publikaci — napojení integrace

1. V `manifest.json` integrace doplnit:
   ```json
   "requirements": ["taphome-sdk==1.0.0"]
   ```
   (Nedoplňovat dřív — Home Assistant instaluje requirements z PyPI při
   načtení integrace a neexistující balíček by setup shodil.)
2. Lokální vývoj se tím nemění: `sdk_locator.py` upřednostní checkout
   `d:\repos\taphome-sdk` před nainstalovaným balíčkem
   (viz [development.md](../development.md)).

## Další verze

Každá změna SDK = nová verze: bump `version` v `pyproject.toml` + zápis do
`CHANGELOG.md` + GitHub release s tagem `v<verze>` + bump verze
v `requirements` manifestu integrace. Core nepřijímá git závislosti, jen
pinované verze z PyPI.

## Záložní varianta: API token místo trusted publishing

Kdyby OIDC nebylo žádoucí: PyPI → Account settings → API tokens → token se
scope na projekt, uložit jako GitHub secret `PYPI_API_TOKEN` a v release
workflow předat `pypa/gh-action-pypi-publish` vstup
`password: ${{ secrets.PYPI_API_TOKEN }}`. Trusted publishing je ale
bezpečnější (nic k úniku) a PyPI ho doporučuje.
