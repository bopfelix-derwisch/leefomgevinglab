# Kan · mag · gebeurt op het water (`/kmg`) — ontwerp

**Datum:** 2026-10-01
**Bouwt op:** het waterdossier (`/water`, `usecases/water_hub.py`), de prik-op-de-kaart
(`/waterruimte`, `usecases/gebruiksruimte/`), de Atlas-connector (`connectors/smwk_atlas.py`) en
het waterprofiel (`usecases/gebruiksruimte/waterprofiel.py`).
**Status:** ontwerp, goedgekeurd voor plan-fase.

---

## 1. Doel

Het DSO laat in een voorlichtingsfolder zien hoe regels op de kaart zichtbaar worden met drie
lagen over elkaar: wat er volgens de regels **kan**, wat er volgens de vergunningen **mag**, en
wat er volgens de metingen **gebeurt**. Voor geluid en lucht, met een fictief voorbeeld. De
scherpte van die plaat zit in de laatste vraag: de meting constateert een overschrijding, maar
*wie veroorzaakt hem?*

Dit lab heeft `kan` en `mag` voor water al draaien. Deze pagina voegt `gebeurt` toe en stelt
diezelfde vraag — met het verschil dat de drie lagen hier geen fictief voorbeeld zijn.

### Wat dit anders maakt dan de folder

Bij geluid is de stap van bron naar immissiepunt uit te rekenen: geluid dempt voorspelbaar met
afstand, en het DSO kan de bijdrage per bedrijf dus hard maken. Bij water kan dat niet zonder
stromingsmodel. Die asymmetrie is geen tekortkoming van deze pagina maar het onderwerp ervan.

### Voorwaarde vooraf — één download ontbreekt nog

De meetgegevens zijn er (§3). De **KRW-doelen** zijn dat nog niet: die staan als apart onderwerp
in dezelfde downloadmodule maar zijn nog niet opgehaald. Zonder die set is er geen echte norm om
tegen te toetsen.

Wat er gebeurt als hij er bij de bouw nog niet is: `/kmg` toont de metingen dan wél, maar zonder
normoordeel — geen "overschrijding", geen staafdiagram, en een regel die zegt dat het KRW-doel
ontbreekt. Terugvallen op de labnormen uit `waterprofiel.py` is uitdrukkelijk **niet** toegestaan
(zie §4.3): dat zou een echte meting tegen een verzonnen norm zetten en de overschrijding zelf
verzinnen.

De toerekening uit §5 hangt daarmee ook aan deze download, want zonder normoordeel is er geen
overschrijding om toe te rekenen.

### Afbakening (YAGNI)

- Eén stroomgebied: de Maas. Daar zijn vergunningen én metingen echt.
- Eén jaar: 2025, de meest recente volledige set.
- Drie stoffen: stikstof totaal, zink en PFOA. AOX komt in de meetset niet voor.
- Geen stromingsmodel, geen verblijftijd, geen afbraak — zie §5.
- Geen nieuwe kaartpagina: `/waterruimte` blijft de plek waar je vrij prikt. Deze pagina gaat
  over meetpunten, een eindige lijst.

---

## 2. De drie lagen en hun herkomst

| Laag | Bron | Echt of lab |
|---|---|---|
| **Kan** | DSO Ozon, `regelingen_op_punt` op het meetpunt | live, echt |
| **Mag** | Atlas voor een Schone Maas, vergunde vrachten | live, echt |
| **Gebeurt** | Waterkwaliteitsportaal (IHW), momentopname 2025 | echt, handmatig gehaald |
| Norm | KRW-doelen uit het Waterkwaliteitsportaal | echt — zie §4.3 |
| Toerekening | model van dit lab | **lab** |

Dat onderscheid is niet decoratief. Het is wat de pagina te zeggen heeft.

---

## 3. Wat de meetdata werkelijk bevat

Geverifieerd op 2026-10-01 tegen de download `WKP_download_20261001171800` (Rijkswaterstaat,
meetjaar 2025):

- 322 meetpunten, alle met RD-coördinaten in de kolommen `GeometriePuntX_RD` / `GeometriePuntY_RD`
- 384.259 meetwaarden volgens het Aquo-informatiemodel Metingen
- koppeling naar het KRW-waterlichaam via `HoortbijGeoobjectIdentificatie` (`NL91BOM`,
  `NL91GM`, `NL91ZM`, `NL94_*`)
- per meting: datum, tijd, stof met CAS-nummer, eenheid, waarde en kwaliteitsoordeel

De labstoffen erin:

| Stof | Code | Metingen | Opmerking |
|---|---|---|---|
| stikstof totaal | `Ntot` | 2467 | |
| zink | `Zn` | 1783 | |
| PFOA | `PFOA` | 590 | de ZZS uit het waterprofiel |
| AOX | — | 0 | zit niet in deze set |

Het dichtstbijzijnde Maas-station bij de vergunningen rond Maastricht is **Eijsden ponton**
(`NL80_EIJSDPTN`, waterlichaam `NL91BOM`, 11 km):

| Stof | n | mediaan | maximum |
|---|---|---|---|
| stikstof totaal | 52 | 3,30 mg/l | 20,0 mg/l |
| zink | 104 | 4,54 µg/l | 49,7 µg/l |

**Let op bij het filteren:** bij de chemische metingen is `MonsterCompartimentCode` leeg, niet
`OW`. Een filter op `OW` levert nul stikstof- en zinkmetingen op — dat kostte tijdens de
verkenning een misleidende tussenstap.

---

## 4. Ingest

### 4.1 Bron en opslag

De downloadmodule van het Waterkwaliteitsportaal (`wkp.rws.nl/downloadmodule`) levert per
waterbeheerder en meetjaar een zip met twee CSV's: `WKP_Meetobjecten_*` (de punten) en
`WKP_Meetwaarden_*` (de metingen). Er is **geen open machine-ingang**: de Digitale Delta API van
RWS geeft 401 op elk data-eindpunt, en de WKP-module die metingen via die API gaat publiceren
wordt pas begin 2027 opgeleverd. Dit is dus een momentopname die een mens haalt.

De ruwe CSV's gaan naar `/mnt/nvme/geluidsmeter/data/external/wkp/` en blijven buiten de repo.

### 4.2 Verdichting

`scripts/13_fetch_wkp_metingen.py` leest de twee CSV's en schrijft één compact bestand per
meetjaar: per combinatie van meetpunt en stof het aantal metingen, de mediaan, het maximum, de
eerste en laatste monsterdatum, en de eenheid. Van 142 MB naar enkele honderden kilobytes.

De mediaan is de hoofdwaarde, niet het gemiddelde: meetreeksen bevatten uitschieters (zink max
49,7 tegen mediaan 4,54) en één piek mag het beeld niet bepalen. Het maximum staat er apart bij,
want juist dat is relevant voor een normtoets.

### 4.3 De norm moet ook echt worden

Het waterprofiel hanteert nu normen die dit lab zelf koos "in de orde van de KRW-doelen". Zolang
er geen metingen naast stonden was dat verdedigbaar. Met echte metingen ernaast is het dat niet
meer: een echte 3,30 mg/l afzetten tegen een verzonnen 2,20 maakt de overschrijding zelf
verzonnen.

Daarom hoort bij deze ingest een tweede download: **KRW-doelen** uit hetzelfde portaal. De
ingest leest die mee, en `/kmg` toetst tegen de echte KRW-doelen per waterlichaam. Ontbreekt een
doel voor een stof, dan zegt de pagina dat — in plaats van terug te vallen op een labgetal.

Dit raakt `/waterruimte` niet: die blijft op het afgeleide waterprofiel draaien voor punten waar
geen KRW-doel beschikbaar is. De twee pagina's zijn daarmee eerlijk over hun eigen basis.

---

## 5. Het toerekeningsmodel

Dit is het deel waar de pagina betrouwbaar of onbetrouwbaar wordt.

### 5.1 Wat het model doet

Voor een meetpunt met een overschrijding:

1. **Welke vergunningen kunnen bijdragen?** Alleen die op een waterlichaam dat bovenstrooms van
   het meetpunt ligt, of op het waterlichaam zelf. Bovenstrooms wordt bepaald met een
   gecureerde volgorde van de Maas-waterlichamen (Bovenmaas → Grensmaas → Zandmaas → …),
   als tabel in de labcode.
2. **Hoe groot is de bijdrage?** De vergunde vracht in kg/jaar gedeeld door de jaarafvoer van het
   waterlichaam in liters, geeft een concentratiebijdrage in mg/l.
3. **Wat blijft over?** Gemeten waarde minus de som van de bijdragen. Dat restant heet
   *bovenstrooms en diffuus* en omvat alles wat niet uit een vergunning in het register komt:
   buitenlandse bronnen, landbouw, riooloverstorten, atmosferische depositie.

### 5.2 Wat het model niet doet, en dat moet op de pagina staan

- Geen verblijftijd, geen menging, geen afbraak of bezinking.
- Geen rekening met het moment van lozen tegenover het moment van meten.
- Geen onderscheid tussen vergunde ruimte en werkelijke lozing — een vergunning wordt zelden
  volledig benut, dus de berekende bijdrage is een bovengrens.
- Geen enkele vergunning buiten het Maasstroomgebied, want daar bestaat het register niet.

### 5.3 De harde regel

De uitkomst van dit model wordt **nooit** gepresenteerd als een vaststelling van wie de
overschrijding veroorzaakt. De folder is daar zelf expliciet over: *toezicht stelt vast wie die
veroorzaakt, met het vergunde beeld als meetlat*. Deze pagina levert die meetlat, niet het
oordeel.

Concreet: de woorden "veroorzaakt door" komen niet op de pagina voor. Wel: "kan bijdragen",
"vergunde ruimte", "bovengrens".

---

## 6. De proclaimer

De pagina krijgt een proclaimer — geen disclaimer. Niet uitleggen waar we níet voor instaan, maar
hoe dit gemaakt is en waar we wél voor instaan. Hij staat op de pagina zelf, niet verstopt
achter een link, en dekt vier dingen:

**Wat echt is en hoe we eraan kwamen.** Welke laag uit welke bron komt, met de datum van de
momentopname, wie de bronhouder is en onder welke voorwaarden we hem gebruiken. Dat de metingen
gevalideerde KRW-monitoring van Rijkswaterstaat zijn, met hoeveel metingen per stof het beeld is
opgebouwd, en dat ze met de hand zijn gehaald omdat er geen machine-ingang bestaat.

**Wat van ons is.** Dat de toerekening een model van dit lab is, wat het wel en niet meeneemt, en
waarom de uitkomst een bovengrens is. In gewone taal, niet in een voetnoot.

**Wat je er niet mee kunt.** Dat dit geen vaststelling is van wie een overschrijding veroorzaakt,
en dat die vaststelling bij het toezicht ligt.

**Waar het gat zit.** Dat `kan` en `mag` machinaal binnenkomen en `gebeurt` niet, dat de
Digitale Delta API van RWS vandaag 401 geeft, en dat de WKP-module die dit zou oplossen begin
2027 wordt opgeleverd. Met een datum erbij, zodat een lezer over een jaar kan zien of het
inmiddels anders is.

De proclaimer is geen tekstblok dat los van de code leeft: hij wordt gegenereerd uit dezelfde
gegevens die de pagina voedt — meetjaar, aantallen metingen, de datum van de momentopname, de
bronnaam. Wat er staat klopt dan per definitie met wat je ziet.

---

## 7. De pagina

Nieuw lid van het waterdossier, naast de vier bestaande. Route `/kmg`, data via
`GET /api/kmg?meetpunt=&live=`.

**Keuze van het meetpunt:** een lijst van de Maas-stations met hun waterlichaam, gesorteerd
stroomafwaarts. Geen kaart — `/waterruimte` is al de kaart, en hier gaat het om een eindige,
benoemde set punten.

**Per meetpunt, in de volgorde van de folder:**

*Kan* — de regelingen die op dit punt gelden, live uit het DSO, met het bestaande onderscheid
tussen direct en indirect werkend.

*Mag* — de vergunningen op dit waterlichaam en bovenstrooms, met hun vergunde vracht, uit de
Atlas. Inclusief de bestaande melding wanneer een vergunning meerdere grenswaarden kent.

*Gebeurt* — per stof de gemeten mediaan en het maximum, het aantal metingen, de periode, en het
KRW-doel ernaast. Met de uitkomst: binnen de norm, of overschrijding.

*En dan de vraag* — bij een overschrijding het staafdiagram van bijdragen: per vergunning een
balk, en het restant als "bovenstrooms en diffuus". Met de proclaimer eronder.

---

## 8. Tests

| Bestand | Legt vast |
|---|---|
| `test_wkp_ingest.py` | de CSV-verdichting: mediaan en maximum per punt en stof, lege `MonsterCompartimentCode` wordt níet weggefilterd, onleesbare waarden worden overgeslagen zonder de rij te laten klappen |
| `test_kmg_toerekening.py` | alleen bovenstroomse vergunningen tellen mee; de som van bijdragen plus restant is gelijk aan de gemeten waarde; een vergunning benedenstrooms draagt nul bij; bij een meetpunt zonder bovenstroomse vergunningen is het restant honderd procent |
| `test_kmg_proclaimer.py` | de proclaimer noemt het meetjaar, het aantal metingen en de bronnaam die ook in de data zitten — een afwijking tussen tekst en gegevens laat de test vallen |
| `test_api_kmg.py` | onbekend meetpunt geeft 404; `live=0` levert een reproduceerbaar antwoord; de drie lagen zitten alle drie in het antwoord |

De tweede test is de belangrijkste: hij dwingt af dat de optelling klopt, zodat het staafdiagram
geen gat of overlap kan vertonen.

---

## 9. Bestanden

**Nieuw**
- `scripts/13_fetch_wkp_metingen.py` — verdichting van de WKP-CSV's
- `src/leefomgevinglab/usecases/kmg/__init__.py`
- `src/leefomgevinglab/usecases/kmg/metingen.py` — de verdichte meetset lezen en bevragen
- `src/leefomgevinglab/usecases/kmg/toerekening.py` — het model uit §5
- `src/leefomgevinglab/usecases/kmg/proclaimer.py` — de tekst uit §6, uit de data opgebouwd
- `src/leefomgevinglab/usecases/kmg/service.py` — de drie lagen samenvoegen
- `src/leefomgevinglab/static/kmg.html`
- vier testbestanden uit §8

**Gewijzigd**
- `src/leefomgevinglab/geluidsmeter/api.py` — routes `/kmg` en `/api/kmg`
- `src/leefomgevinglab/usecases/water_hub.py` — vijfde lid in het dossier
- `core/config.yaml` — pad naar de verdichte meetset
- `CLAUDE.md` — sprintstatus

---

## 10. Risico's

| Risico | Mitigatie |
|---|---|
| De toerekening wordt gelezen als een vaststelling | §5.3 is een harde regel; de proclaimer herhaalt hem; een test bewaakt de woordkeus |
| De momentopname veroudert stil | meetjaar en ophaaldatum staan in de proclaimer, uit de data zelf |
| Geen KRW-doel voor een stof | de pagina zegt dat er geen doel is, in plaats van terug te vallen op een labgetal |
| De gecureerde stroomvolgorde klopt niet | staat als tabel op één plek, met bronvermelding; een test legt de volgorde vast |
| AOX ontbreekt in de meetset | de pagina toont die stof niet bij `gebeurt` en zegt waarom |
| De 142 MB CSV belandt in git | ruwe bestanden op NVMe, buiten de repo; alleen de verdichting is klein genoeg om te bewaren |
