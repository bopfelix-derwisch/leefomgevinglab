# Waterdossier — hub met subnavigatie & prik-op-de-kaart — ontwerp

**Datum:** 2026-09-16
**Bouwt op:** `/lozing` (doelbeeld directe lozing, `usecases/lozing.py` + `lozing_keten/`), `/gebruiksruimte` (`usecases/gebruiksruimte/`), `/balo` (`usecases/balo.py`), `/evruimte` (maplibre-patroon).
**Status:** ontwerp, goedgekeurd voor plan-fase.

---

## 1. Doel

Twee samenhangende toevoegingen rond de waterlozing:

1. **Een waterdossier-hub** — het lozingsverhaal staat nu verspreid over vier tabs die elkaar
   nauwelijks kennen. Er komt één ingang (`/water`) met een gedeelde subnavigatie, zodat de
   bezoeker ziet dat het één dossier is in plaats van vier losse pagina's.
2. **Een prik-op-de-kaart-variant** (`/waterruimte`) — "wat kan hier nog?" op een willekeurig punt
   in Nederland, in plaats van de drie gecureerde IJssel-locaties.

Daarbij wordt het synthetische vergunningregister voor het Maasstroomgebied vervangen door
**echte vergunningen uit de Atlas voor een Schone Maas**.

### De aanleiding voor de hub

Elke statische pagina heeft nu een handgeschreven `<nav>` met een willekeurige greep uit de
tabs: `gebruiksruimte.html` linkt naar 4 andere, `keten-tab.html` naar 5, `balo.html` naar 4 —
en geen twee dezelfde. De hoofdnav in `index.html` is een platte rij van 19 items waarin
`/lozing`, `/gebruiksruimte` en `/balo` nergens als samenhangend geheel te herkennen zijn.

### Afbakening (YAGNI)

- `/gebruiksruimte` blijft **ongewijzigd** in gedrag: de drie gecureerde locaties, hetzelfde
  antwoord. De prik-kaart komt ernaast, niet ervoor in de plaats.
- Alleen de waterpagina's krijgen een subnav. Geen navigatie-refactor voor de andere 15 tabs.
- Geen nieuwe bron voor waterkwaliteitsmetingen. De meetgegevens van de SMWK blijven buiten
  beschouwing; alleen de vergunningen worden overgenomen.
- Geen indirecte lozingen (op het riool). Die ontbreken ook in de Atlas.
- Geen caching van Atlas-antwoorden in een eigen database; de bestaande `cache_dir` volstaat.

---

## 2. Verwant werk: de Atlas voor een Schone Maas

Dit ontwerp positioneert zich expliciet ten opzichte van een bestaand initiatief. Dat hoort op
de pagina te staan, niet alleen in deze spec.

**Wat de Atlas is** (`atlas-smwk.hub.arcgis.com`, ArcGIS Hub van de Schone Maaswaterketen —
de waterschappen Aa en Maas, Brabantse Delta, De Dommel, Limburg, samen met RWS en de
drinkwaterbedrijven). Sinds april 2023 staan de directe lozingsvergunningen erin, doorzoekbaar
op bedrijf, stof en vergunningverlener.

Geverifieerd op 2026-09-16 tegen de live service:

| Laag | Inhoud |
|---|---|
| `Vestigingen_Vergunningen_Uniek/0` | 72 vestigingen met directe lozingsvergunning (punt, RD) |
| `Vestigingen_Vergunningen_Uniek/2` (`VergunningenTabel`) | 782 vergunde voorschriften over 68 parameters |
| `Emissieregistratie_Effluent_incl_totalen_heel_NL/0` | 6717 rijen emissieregistratie (Maasgericht ondanks de titel) |

Per voorschrift: `Statutaire_naam`, `Kenmerk` (bv. `RWS-2015/38632`), `Besluitdatum`,
`Parameter`, `Waarde`, `Eenheid`, `Bemonsteringswijze`, `meetpunt_X_Coordinaat` /
`meetpunt_Y_Coordinaat` (RD).

Een ruimtelijke query werkt rechtstreeks op RD (`inSR=28992`, `distance=…`,
`units=esriSRUnit_Meter`): een punt bij Maastricht geeft 11 vestigingen binnen 5 km, een punt
bij Deventer nul — het is het Maasstroomgebied.

**Wat dit lab toevoegt.** De Atlas toont vergunningen náást elkaar. Wat er niet in zit:

1. **De optelsom.** Niemand telt de vergunde vrachten op tot een totaal per waterlichaam en zet
   dat af tegen de norm.
2. **De regels op de plek.** Geen DSO-koppeling — geen omgevingsplan, geen verordening, geen
   onderscheid tussen direct en indirect werkende regels.
3. **De vraag vooruit.** De Atlas is retrospectief (wat is vergund, wat meten we). "Wat kan hier
   nóg?" staat er niet in.
4. **Bevoegd gezag op een willekeurig punt.** De Atlas toont wie vergund heeft, niet wie bevoegd
   zóu zijn op een plek waar nog niets ligt.

De aanvulling is dus niet de kaart maar de stap **van vergunningenlijst naar gebruiksruimte**.

**Licentie.** De items staan op `access: public` maar hebben géén `licenseInfo` — anders dan de
CBS-afvalcijfers (CC-BY 4.0) die dit lab elders gebruikt. Consequentie: live bevragen met
bronvermelding en een link terug naar de Atlas, geen kopie van de dataset in de repo, geen
herpublicatie als eigen dataset. Dat wordt zo op de pagina verantwoord.

---

## 3. De hub

### 3.1 `usecases/water_hub.py` — single source of truth

Geen losse links in HTML meer; de hub beschrijft zichzelf.

```python
LEDEN = [
    {"id": "overzicht",    "pad": "/water",          "label": "Overzicht",    ...},
    {"id": "keten",        "pad": "/lozing",         "label": "Keten",        ...},
    {"id": "ruimte",       "pad": "/gebruiksruimte", "label": "Ruimte",       ...},
    {"id": "kaart",        "pad": "/waterruimte",    "label": "Kaart",        ...},
    {"id": "knelpunten",   "pad": "/balo",           "label": "Knelpunten",   ...},
]
```

Per lid: `label` (subnav), `titel` en `samenvatting` (kaart op de landingspagina), `live`
(welke bronnen live worden bevraagd) en `synthetisch` (wat verzonnen is). Dat laatste paar
dwingt af dat elke waterpagina zich verantwoordt op één plek.

Daarnaast `LIJNEN` — de drie draden die in álle leden terugkomen, elk met de leden waar je ze
ziet:

1. **De knip.** Twee bevoegde gezagen over één fabriek; geen koppelvlak dat afdwingt dat de
   MBA-vergunning en de lozingsvergunning op elkaar aansluiten.
2. **Het register dat niet bestaat.** Geen landelijk beeld van wie wat waar loost — en daarmee
   geen optelsom per waterlichaam. Met sinds dit ontwerp de nuance: voor het Maasstroomgebied
   is er wél een regionaal initiatief.
3. **Het effect stroomafwaarts.** Een lozing is geen contour om een punt; hij telt op bij alles
   wat verder stroomopwaarts al geloosd wordt.

Analysefunctie `dekking()` → per lijn welke leden hem raken, zodat de landingspagina die matrix
kan tonen zonder hem te herhalen in HTML.

### 3.2 Subnavigatie

De statische pagina's zijn losse HTML-bestanden zonder templating. De bestaande oplossing voor
precies dit probleem is `_keten_tab()` in `api.py`, die `__DOSSIER__` in `keten-tab.html`
vervangt. Diezelfde weg:

```python
def _waterpagina(bestand: str, actief: str) -> str:
    html = (STATIC / bestand).read_text()
    return html.replace("__WATERNAV__", water_hub.subnav_html(actief))
```

`water_hub.subnav_html(actief)` genereert de balk uit `LEDEN` en markeert het actieve lid. De
drie bestaande waterpagina's krijgen een `__WATERNAV__`-placeholder op de plek van hun huidige
handgeschreven `<nav>`; hun routes gaan via `_waterpagina()`.

**Let op:** `keten-tab.html` bedient zowel `/lozing` als `/dvth`. `/dvth` is geen waterpagina en
mag de balk niet krijgen. `_keten_tab(dossier)` vervangt `__WATERNAV__` daarom door de subnav
voor `lozing` en door een lege string voor `dvth` — hetzelfde mechanisme als `__DOSSIER__`.

`/balo` en `/lozing` behouden daarnaast hun plek in de hoofdnav: `/balo` dekt ook de
Seveso-casus en `/lozing` is de tegenhanger van `/dvth`. Ze zijn lid van de hub, geen eigendom
ervan.

### 3.3 `/water` — de landingspagina

`static/water.html` + `GET /api/water/hub` (levert `LEDEN`, `LIJNEN`, `dekking()`).

Opbouw: het dossier in één alinea (één lozingsactiviteit op een rijkswater, van voornemen tot
handhaving) → de leden als kaarten met per kaart wat live is en wat synthetisch → de drie lijnen
als doorsnijdend blok met de dekkingsmatrix → een blok over de Atlas voor een Schone Maas: wat
daar al is, en wat dit lab eraan toevoegt.

### 3.4 `index.html`

`/gebruiksruimte` verdwijnt uit de hoofdnav en het kaartrooster; de nieuwe ingang
**Waterdossier** → `/water` komt ervoor in de plaats. `/lozing` en `/balo` blijven wél los
staan (zie 3.2): de eerste als tegenhanger van `/dvth`, de tweede omdat hij ook de Seveso-casus
dekt. Netto gaat de hoofdnav van 19 naar 18 items, maar krijgt het dossier één herkenbare kop.

---

## 4. Het waterprofiel

### 4.1 `gebruiksruimte/waterprofiel.py`

De huidige `gebied.WATERLICHAAM` is één hardgecodeerde IJssel. Voor een vrij punt moet elk
rijkswater een profiel krijgen, met een **harde scheiding tussen echt en synthetisch** — dat is
de plek waar dit lab zijn geloofwaardigheid wint of verliest.

**Echt, live uit de KRW-service van RWS** (velden geverifieerd 2026-09-16):

| Veld | Betekenis |
|---|---|
| `naam`, `owl_id`, `sgd_id` | identiteit en stroomgebiedsdistrict |
| `wbhnaam`, `wbhcode` | de waterbeheerder, letterlijk uit de bron |
| `owltype` | KRW-watertype (K2, O2a, R7, M7b…) |
| `owlcat` | categorie (1 rivier, 2 meer, 3 kust, 4 overgangswater) |
| `owlstat` | natuurlijk / sterk veranderd / kunstmatig |
| `omvang` + `eenheid`, `gemdiepte` | omvang en gemiddelde diepte |

**Lab, synthetisch:** debiet en achtergrondconcentratie per parameter, afgeleid van `owlcat` /
`owltype`; normen per watertypegroep. Een rivier, een meer en een kustwater krijgen
verschillende getallen — zonder die differentiatie is "een profiel voor elk rijkswater" een
lege huls.

De returnstructuur markeert dit per veld, zodat de pagina het kan tonen:

```python
{"echt": {...KRW-velden...}, "afgeleid": {...debiet, parameters...},
 "herkomst": {"debiet_m3_s": "afgeleid van owlcat+omvang", ...}}
```

### 4.2 `lozing_keten/bronnen.py`

`contextset()` haalt nu `naam,owl_id,sgd_id,gebtype` op. Uitbreiden met `owltype`, `owlcat`,
`owlstat`, `wbhnaam`, `wbhcode`, `omvang`, `eenheid`, `gemdiepte`.

`bevoegd_gezag()` leidt de waterbeheerder nu af uit "`owl_id` aanwezig → rijkswater". Dat wordt
`wbhnaam` uit de bron, met de bestaande afleiding als fallback wanneer het veld leeg is. De
bestaande uitkomst voor de IJssel blijft gelijk (`wbhnaam` = "Ministerie van Infrastructuur en
Waterstaat (Rijkswaterstaat)").

---

## 5. Het register: echt waar het kan

### 5.1 `connectors/smwk_atlas.py`

Nieuwe connector op `BaseConnector`, ArcGIS FeatureServer.

```python
class SmwkAtlasConnector(BaseConnector):
    def vergunningen_bij_punt(self, x: float, y: float, straal_m: int = 5000) -> list[dict]
```

Twee stappen: vestigingen binnen de straal uit laag `0` (ruimtelijke query op RD), dan hun
voorschriften uit tabel `2` via `where Kenmerk IN (…)`. Antwoord gecachet in de bestaande
`cache_dir`, TTL één dag — net als de Stelselcatalogus.

Faalt de Atlas, dan valt de pagina terug op "register onbekend"; de rest van het beeld gaat
door. Hetzelfde patroon als `regels_op_locatie()`.

### 5.2 Vracht afleiden — gelaagd, en eerlijk over wat niet lukt

De rekensom in `ruimte.bereken()` wil per vergunning een vracht in kg/jaar. De Atlas geeft
`Waarde` + `Eenheid`, in 21 verschillende eenheden. Drie lagen, in volgorde:

1. **De eenheid is al een vracht** (`kilogram per jaar`, `ton per jaar`, `kilogram per dag`,
   `kilogram per week`) → direct omrekenen naar kg/jaar. Geen debiet nodig.
2. **De eenheid is een concentratie** (`milligram per liter`, `microgram per liter`) → vracht =
   concentratie × debiet, mits er bij hetzelfde `Kenmerk` een `Debiet`-voorschrift staat. Dat is
   het geval bij **29 van de 72** vestigingen.
3. **Anders** (`dimensieloos`, `graad Celsius`, `megajoule per seconde`, geen debiet bekend) →
   de vergunning wordt wél getoond, met `vracht_kg_jaar: None` en een reden.

Die derde categorie is geen tekortkoming om weg te poetsen maar een datakwaliteitsbevinding in
de geest van `/wfs-kwaliteit`: van een vergunning waarin alleen een concentratie-eis staat en
geen debiet, valt de vracht niet te bepalen — en dus valt hij ook niet op te tellen. De pagina
telt hoeveel vergunningen in elke laag vallen.

### 5.3 Parameter-crosswalk

De Atlas hanteert eigen parameternamen. Een expliciete crosswalk (klein, curated, in
`waterprofiel.py`):

| Lab-parameter | Atlas-parameter |
|---|---|
| stikstof totaal | `stikstof totaal` (exact) |
| zink | `zink` (exact) |
| AOX | `som extraheerbare organische halogeenverbindingen`, `Extraheerbaar organisch chloor` |
| PFOA | — komt niet voor |

Dat PFOA ontbreekt terwijl het een ZZS is, is zelf een bevinding en wordt als zodanig getoond:
de vergunningen in de Atlas dateren deels van vóór de aandacht voor deze stofgroep (kenmerken
als `DLB2006/8811` en `DLB2007/10829`).

### 5.4 Wanneer welk register

- **Treffers in de Atlas** (Maasstroomgebied) → echte vergunningen, met kenmerk, besluitdatum en
  een link naar de Atlas. Blok gemarkeerd als *bron: Schone Maaswaterketen, live*.
- **Geen treffers, maar wel de IJssel** → het bestaande synthetische `gebied.REGISTER`, zoals nu,
  gemarkeerd als *synthetisch*.
- **Geen van beide** → leeg register. `ruimte.bereken()` kent `register_leeg` al en zet dan de
  kanttekening dat zonder zicht op bestaande vergunningen niet te zien is van wie de ruimte is.

Dit contrast is het inhoudelijke hart van de kaart: **op de Maas werkt dit met echte data, op de
IJssel moet het lab het verzinnen — omdat daar geen atlas is.** Dat is een sterker argument voor
een landelijk register dan een pagina die overal hetzelfde synthetische register toont.

De rekensom blijft overal werken: ruimte-tot-de-norm hangt aan achtergrond versus norm, niet aan
het register. De vergunde vracht staat er los naast (en wordt niet afgetrokken — zie de
toelichting in `ruimte.py`).

---

## 6. De prik-kaart

### 6.1 Refactor van de motor

```python
def beeld_op_punt(x, y, debiet_m3_per_uur=420, live=True, naam=None, ...) -> dict
def beeld(locatie_id, ...) -> dict          # dunne wrapper, zoekt de vaste locatie op
```

`/gebruiksruimte` blijft daarmee onveranderd; beide pagina's delen één motor. Een test legt
vast dat `beeld("deventer")` exact hetzelfde blijft teruggeven als vóór de refactor.

### 6.2 `GET /api/waterruimte?x=&y=&debiet=&live=`

Vier aanroepen in drie sporen — KRW-service én bestuurlijke gebieden, DSO-regels,
Atlas-vergunningen — **parallel** via
`ThreadPoolExecutor`, zoals `/evruimte` dat al doet voor de BAG-tellingen. Serieel zou elke klik
seconden kosten.

Begrenzing: `debiet` blijft geklemd op `MAX_DEBIET` (20.000 m³/u). Coördinaten buiten een ruime
RD-bbox voor Nederland geven een nette 400.

### 6.3 `static/waterruimte.html`

Maplibre, zelfde opzet als `evruimte.html`. Klik = prik. Rechts het paneel: waterlichaam en
bevoegd gezag (live), de regels (live), het register (echt of synthetisch, expliciet gelabeld),
de rekensom per parameter. Snelkoppelingen naar een paar sprekende punten: Maastricht (echte
vergunningen), Deventer (synthetisch), en een punt op regionaal water.

Buiten een rijkswaterlichaam prikken is geen fout maar een antwoord: geen treffer in de
KRW-service betekent regionaal water en dus het waterschap als beheerder; de regels komen er
nog steeds bij; de rekensom vervalt met opgaaf van reden.

---

## 7. Tests

Bestaande suite als patroon (`test_gebruiksruimte.py`, `test_lozing.py`, `test_evruimte.py`),
met gemockte `_haal`.

| Bestand | Legt vast |
|---|---|
| `test_water_hub.py` | elk lid verwijst naar een bestaande route; `dekking()` raakt elke lijn minstens één lid; subnav markeert precies één actief item |
| `test_waterprofiel.py` | echt en synthetisch strikt gescheiden; verschillende `owlcat`/`owltype` geven verschillende profielen; elk afgeleid veld heeft een herkomstregel |
| `test_smwk_atlas.py` | ruimtelijke query bouwt de juiste RD-parameters; de drie vrachtlagen; onbekende eenheid geeft `None` met reden, geen exception |
| `test_api_waterruimte.py` | prik op rijkswater, prik op regionaal water, prik op land, coördinaten buiten NL → 400 |
| `test_gebruiksruimte.py` (uitbreiding) | `beeld(locatie_id)` blijft na de refactor identiek |

Live-tests (`test_dso_live.py`, `test_ev_live.py`) hebben een eigen markering; een
`test_atlas_live.py` volgt dat patroon zodat de suite zonder netwerk groen blijft.

---

## 8. Bestanden

**Nieuw**
- `src/leefomgevinglab/usecases/water_hub.py`
- `src/leefomgevinglab/usecases/gebruiksruimte/waterprofiel.py`
- `src/leefomgevinglab/connectors/smwk_atlas.py`
- `src/leefomgevinglab/static/water.html`
- `src/leefomgevinglab/static/waterruimte.html`
- `tests/test_water_hub.py`, `tests/test_waterprofiel.py`, `tests/test_smwk_atlas.py`,
  `tests/test_api_waterruimte.py`, `tests/test_atlas_live.py`

**Gewijzigd**
- `src/leefomgevinglab/geluidsmeter/api.py` — routes `/water`, `/api/water/hub`,
  `/waterruimte`, `/api/waterruimte`; `_waterpagina()`; bestaande waterroutes erlangs
- `src/leefomgevinglab/usecases/gebruiksruimte/service.py` — `beeld_op_punt()`
- `src/leefomgevinglab/usecases/gebruiksruimte/gebied.py` — `REGISTER` krijgt `owl_id`
- `src/leefomgevinglab/usecases/lozing_keten/bronnen.py` — extra KRW-velden, `wbhnaam`
- `src/leefomgevinglab/static/{index,gebruiksruimte,keten-tab,balo}.html` — `__WATERNAV__`
- `core/config.yaml` — Atlas-endpoint en TTL
- `CLAUDE.md` — sprintstatus

---

## 9. Risico's

| Risico | Mitigatie |
|---|---|
| Atlas-service onbereikbaar of traag | Cache (1 dag), time-out, val terug op "register onbekend"; de rest van het beeld gaat door |
| Atlas verandert veldnamen of trekt de laag terug | Connector faalt luid in `test_atlas_live.py`, zacht op de pagina; de spec noteert de geverifieerde velden en de datum |
| Geen expliciete licentie op de Atlas-data | Live bevragen met bronvermelding en link terug; geen kopie in de repo, geen herpublicatie |
| Vier WFS/API-aanroepen per klik = trage kaart | Parallel via `ThreadPoolExecutor`; `live=0` blijft beschikbaar voor een reproduceerbaar antwoord |
| De refactor breekt `/gebruiksruimte` stilletjes | Test die de bestaande uitvoer vastlegt vóór de refactor |
| Synthetische profielen voor 89 wateren gaan echt lijken | Herkomst per veld in het antwoord; de pagina toont echt en afgeleid gescheiden |
