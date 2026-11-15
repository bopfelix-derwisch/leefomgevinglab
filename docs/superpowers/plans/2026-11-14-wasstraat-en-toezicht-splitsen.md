# Wasstraat vergunningen en toezicht splitsen — plan

**Goal:** De tien signaalregels verdelen over twee pagina's met twee verschillende lezers, omdat
zij twee verschillende vragen beantwoorden. `/wasstraat` is van de **vergunningverlener** en gaat
over het papier; `/toezicht` is van de **toezichthouder** en gaat over de werkelijkheid.

**Aanleiding.** `/toezicht` presenteerde tien signalen als "waar moet ik gaan kijken", maar
gemeten is **7 van de 10 een bevinding over de vergunning zelf** — een ingetrokken Aquo-code, een
parameter buiten de referentie, twee grenswaarden voor dezelfde stof, een concentratie zonder
debiet, een ontbrekend vergunningkenmerk, een onvermeld bemonsteringsregime, geen
geldigheidsperiode. Dat is werk voor wie de vergunning opstelt, niet voor wie op bezoek gaat. In
het dossier van Tata Steel waren 11 van de 15 signalen regel 4, en dat is pure papierhygiëne.

## De splitsing, gemeten en niet bedacht

Een regel hoort bij de werkelijkheid zodra zij meetdata of stroomrichting uit `context` nodig
heeft. Dat is geen smaak maar na te rekenen op de broncode van de regel zelf.

| laag | regels |
|---|---|
| **papier** (wasstraat, 7) | `vervallen_code`, `niet_in_referentie`, `meerdere_grenswaarden`, `vracht_onbepaald`, `vergunning_niet_te_vinden`, `niet_regime_zuiver`, `geen_geldigheidsduur` |
| **werkelijkheid** (toezicht, 3) | `geen_onafhankelijke_meting`, `norm_overschreden_bovenstrooms`, `stof_buiten_register` |

`geen_onafhankelijke_meting` is het grensgeval en gaat naar **toezicht**: de bevinding is dat er
geen onafhankelijke meting bestaat, en dat is een feit over het meetnet, niet over de pen van de
vergunningverlener. Dat die vaststelling óók de vergunning raakt, staat als verwijzing op de
wasstraatpagina.

`laag` komt als veld op `Regel` en wordt uit die ene classificatie afgeleid — géén tweede lijst
die uit de pas kan lopen. Een test dwingt af dat elke regel in `DREMPELS` precies één laag heeft
en dat de twee lagen samen de tien dekken.

## `/wasstraat` — van de vergunningverlener

Titel: **Wasstraat vergunningen**. De vraag: *is deze vergunning handhaafbaar opgeschreven?*

1. **Wat hier gebeurt** — in gewone taal, bovenaan: het register komt binnen, wordt ontdubbeld,
   elke parameter wordt tegen de Aquo-domeintabel gelegd, en zeven regels kijken of de vergunning
   tegen zichzelf klopt. Geen taalmodel in die zeven regels.
2. **De zeven bevindingen** per vergunning, met bewijs en de reparatie die eruit volgt — niet
   "waar moet ik gaan kijken" maar **"wat moet hier recht"**.
3. **De logboeken samengevat en uitgelegd.** De runlog is er al per stap; wat ontbreekt is de
   samenvatting: hoeveel stappen, hoeveel rijen erin en eruit, hoe lang, en in welke stappen een
   taalmodel werkelijk is aangeroepen. Plus per stap één regel over wat die stap doet, zodat de
   lezer de keten begrijpt zonder de code.
4. **De configuratie, alleen-lezen.** De zes agents uit `agents.yaml` met hun rol, hun gereedschap
   en of zij een taalmodel mogen krijgen; de takenorde uit `tasks.yaml`. Gelezen uit diezelfde
   bestanden die de runner uitvoert (`pijplijn.als_gegeven`), nooit uit een tweede lijst.
   **Read-only, en dat is een ontwerpbesluit:** deze pagina staat publiek zonder authenticatie, en
   een schrijfpad zou betekenen dat een bezoeker verandert wat voor iedereen draait.

## `/toezicht` — van de toezichthouder

Titel blijft **Toezichtsignalen**. De vraag: *waar moet ik gaan kijken?*

1. **De uitkomst van de wasstraat** per vestiging, als één regel: is het papier op orde, en zo
   niet, hoeveel bevindingen staan er open. Dat is context voor de inspecteur, geen opdracht —
   een vergunning die niet handhaafbaar is opgeschreven, verandert wat een bezoek kan opleveren.
2. **De metingen** uit het Waterkwaliteitsportaal bij het waterlichaam van deze vestiging, met de
   KRW-norm ernaast waar die bestaat (`kmg/metingen.py`, `kmg/doelen.py`, `krw_normen.json` —
   alles bestaat al en wordt hier alleen samengebracht).
3. **De drie werkelijkheidssignalen**, met het voorbehoud dat `/kmg` al voert: een toerekening is
   een bovengrens en nooit een vaststelling.

## REST

```
GET /api/wasstraat/pijplijn            de configuratie, uit de YAML (bestaand: /api/toezicht/pijplijn)
GET /api/wasstraat/vestigingen         69 vergunningen, identiteit locatiecode::kenmerk
GET /api/wasstraat/dossier?vergunning= de zeven papierbevindingen + runlog + samenvatting
GET /api/toezicht/vestigingen          idem
GET /api/toezicht/dossier?vestiging=   wasstraat-uitkomst + metingen + de drie signalen
```

Geen POST, geen PUT, nergens. De configuratie is te lezen en niet te schrijven.

## Wat blijft zoals het is

De tien regels zelf, `aquo.py`, `dossier.py`, `rapport.py`, `graaf.py`/`vraag.py`,
`runner.py`/`runlog.py`, `uitleg.py`, `terugkoppeling.py` — alle gebouwd, gereviewd en getest. Dit
plan verdeelt wat er is over twee lezers en voegt de samenvatting en de uitleg toe. De
`uit=`-parameter op `dossier()` blijft bestaan (de runlog meldt `uitgezet` en er staan tests op),
maar geen pagina drijft hem aan.

## Randvoorwaarden

Nederlands. Het bestaande palet (beide pagina's zijn lid van het waterdossier). De harde
taalregel, ook op de nieuwe teksten. Geen getal getypt. Geen netwerk in gewone tests. Live
verifiëren **op inhoud en publiek**, niet op statuscode.
