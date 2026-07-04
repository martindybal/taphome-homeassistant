# Fáze 5 — Review, údržba a migrace uživatelů custom integrace

## 5.1 Průběh review

- Review nové integrace trvá typicky **týdny až měsíce**; počítat s 2–5 koly
  připomínek. Rychlost výrazně zvyšuje: malý PR, hotový quality_scale,
  odpovědi do 1–2 dnů.
- Stale bot: PR bez reakce autora se po týdnu označí a následně zavře —
  pokud nebude čas reagovat, převést PR do draftu.
- Změny vyžádané v review, které se dotknou `pytaphome`, znamenají release
  knihovny + bump v manifestu uvnitř téhož PR.

## 5.2 Povinnosti codeownera po merge

- GitHub ping na každou issue/PR s labelem `integration: taphome`
  v `home-assistant/core` — očekává se reakce.
- Issues od uživatelů chodí do centrálního trackeru Core (proto se
  `issue_tracker` z manifestu maže).
- Údržba `pytaphome`: bezpečnostní záplaty aiohttp kompatibility, nové typy
  zařízení TapHome.
- Breaking changes v integraci podléhají pravidlům Core (deprecation period,
  zápis do release notes přes label `breaking-change`).
- Postupné zvyšování quality scale (Silver: `reauthentication-flow`,
  `log-when-unavailable`, `parallel-updates`; Gold: `diagnostics`,
  `entity-translations`, discovery…) — každý posun = PR měnící
  `quality_scale` v manifestu + doplněná pravidla.

## 5.3 Migrace stávajících uživatelů HACS/custom integrace

Custom integrace se stejnou doménou `taphome` **překryje** verzi z Core —
uživatelé s nainstalovanou custom verzí by novou integraci vůbec neviděli.
Plán:

1. **Do vydání v Core**: custom repo žije dál a slouží jako beta kanál
   (už běží na `pytaphome`, fáze 1.6).
2. **Poslední release custom integrace** (vydat ve chvíli, kdy vyjde HA
   s TapHome v Core):
   - v `async_setup` založit repair issue („TapHome je nyní součástí Home
     Assistant — odinstalujte custom integraci a nastavte ji přes
     Nastavení → Zařízení a služby"), s odkazem na migrační návod,
   - migrační návod v README: soupis YAML možností → jejich UI ekvivalenty
     (zóny → oblasti, přejmenování → UI rename, `enabled_attributes` → bez
     náhrady…),
   - **entity dostanou nová unique_id** (formát z fáze 2.4 je jiný než dnešní
     `taphome.{domain}...`) — historie a automatizace na entity_id se dají
     zachovat ručním přejmenováním entit; uvést to výslovně v návodu.
     Alternativa (zachovat stará unique_id v Core) nedává smysl — starý
     formát by neprošel review.
3. **Archivace**: HACS repo označit jako deprecated (README banner +
   `archived` na GitHubu až po odeznění migrace, např. 6 měsíců), issues
   přesměrovat na Core tracker.

## 5.4 Souběh vývoje (do merge)

Než Core PR projde, udržovat obě větve s minimem duplicit:

- veškerá logika nová v `pytaphome` → sdílená automaticky,
- custom repo může převzít Core strukturu (config flow, entity.py) dopředu —
  custom integrace smí používat config entries stejně jako Core; tím se
  otestuje na reálných instalacích přesně ten kód, který jde do review.

## Kontrolní seznam fáze 5

- [ ] plán reakcí na review (kapacita 1–2 dny na odpověď)
- [ ] migrační návod v README custom repa
- [ ] poslední release custom integrace s repair issue
- [ ] deprecated banner + přesměrování issues
- [ ] archivace HACS repa po odeznění migrace
