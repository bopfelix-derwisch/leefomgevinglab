# LeefomgevingLab — Claude Code instructies

> **Machine-breed:** `~/.claude/CLAUDE.md` (gedeelde faciliteiten + valkuilen) en `ORIN3_SYSTEEM.md` — niet hier herhalen.
> **Domein:** Edge & Geo (deelt geo-basisdata met `waterlab`). **Start via** `orin3` → window `leefomgevinglab` (pad `/mnt/nvme/workspaces/LeefomgevingLab`) voor consistente memory.
> Voorheen het losse project *Geluidsmeter*; geluid is nu één use-case hierin. Paden/mappen die nog `geluidsmeter` heten (o.a. de NVMe-datadir) zijn **niet** fout — die naam is bewust niet meeverhuisd.

Lees altijd eerst: `CLAUDE_NOTES.md`
Dan: `core/config.yaml`

---

## ⚠️ Kritieke waarschuwingen

| # | Valkuil | Correct |
|---|---------|---------|
| 1 | `find ~` **bevriest** op orin3 | Gebruik `ls` of specifieke paden |
| 2 | Poort **8791** is bezet | Door `felix-nazaten/upload_server.py` — LeefomgevingLab gebruikt **8792** |
| 3 | NVMe data-dirs vereisen **sudo** | `sudo mkdir /mnt/nvme/geluidsmeter/... && sudo chown bob:bob` |
| 4 | C922 mic is **gedeeld** met Derwisch ritueel.py | Conflict als ritueel.py opneemt — check eerst |
| 5 | `core/location_private.yaml` **nooit committen** | Staat in .gitignore — bevat echte coördinaten |
| 6 | Data staat op **NVMe**, niet in de repo | `/mnt/nvme/geluidsmeter/data/` — staat ook in .gitignore |

---

## Repo-locatie

| Repo | Pad | Remote |
|------|-----|--------|
| LeefomgevingLab | `/home/bob/LeefomgevingLab` (symlink → `/mnt/nvme/workspaces/LeefomgevingLab`) | https://github.com/bopfelix-derwisch/leefomgevinglab |

Push met: `git push origin master`
> Repo hernoemd `geluidsmeter` → `leefomgevinglab` (2026-07-29); `origin` bijgewerkt, oude URL redirect (301).

---

## Services (draaien — status 2026-08-31)

| Unit | Staat | Wat |
|---|---|---|
| `leefomgevinglab-api.service` | enabled + active | FastAPI op **8792** (`uvicorn leefomgevinglab.geluidsmeter.api:app --app-dir src`) |
| `leefomgevinglab-embed.service` | enabled + active | llama-server **bge-m3 embeddings op 8082** (voor de RAG) |
| `leefomgevinglab-capture.service` | geïnstalleerd, **disabled + inactive** | audio capture loop; bewust uit (C922 wordt gedeeld met Derwisch `ritueel.py`) |
| `leefomgevinglab-tunnel.service` | alleen in `systemd/`, **niet geïnstalleerd** | overbodig: de tunnel is dashboard-managed via de centrale `cloudflared` |

Unit-bronbestanden staan in `systemd/`; geïnstalleerd staan ze in `/etc/systemd/system/`.
Na wijziging: `sudo cp systemd/leefomgevinglab-*.service /etc/systemd/system/ && sudo systemctl daemon-reload && sudo systemctl restart leefomgevinglab-api`.
Ze worden bewaakt door **sysmonitor** (`~/sysmonitor/sysmonitor.py`, SERVICES + ENDPOINTS).

---

## Architectuur (kort)

```
C922 USB-mic (plughw:CARD=Webcam,DEV=0)
  → audio_capture.py (sounddevice, 60s frames)
  → feature_extract.py (RMS/Lmax/banden — géén ruwe audio)
  → JSONL → /mnt/nvme/geluidsmeter/data/raw_features/
  → aggregate.py → GeoParquet → /mnt/nvme/geluidsmeter/data/processed/
  → Portolan CLI → STAC catalogus
```

---

## Sprint status

- ✅ **Sprint 0:** structuur, config, code, systemd units, git init
- ✅ **Sprint 1:** NVMe dirs, venv, packages, C922 mic werkend (32kHz, gain 3/15)
- ✅ **Sprint 2:** aggregatie + GeoParquet
- ✅ **Sprint 3:** Portolan installeren + catalogus
- ✅ **Sprint 4:** bronnenmatch Atlas/CVGG/PDOK + dashboard
- ✅ **Sprint 5:** publieke demo via Cloudflare Tunnel — destijds `geluid.felixisfelix.com`, **nu `leefomgevinglab.felixisfelix.com`** (de oude hostname bestaat niet meer)
- ✅ **LeefomgevingLab fundering:** connector-laag (BaseConnector) + UC-04 REV-viewer met routes `/viewer`, `/api/rev/features` (PDOK OGC API), `/api/duiding` (lokale Qwen duiding). Code onder `src/leefomgevinglab/` (connectors/ + usecases/).
- ✅ **Geluid is nu één use-case** — niet meer gepland maar **live**: `/public` en `/dashboard` geven 200 (geverifieerd 2026-08-31). Let op de omgekeerde mapstructuur: de FastAPI-app van *alle* use-cases zit in `src/leefomgevinglab/geluidsmeter/api.py` — die modulenaam is historisch, het is niet alleen de geluidsmeter.
- 🚧 **UC-03b — RAG:** vergunningen-chatbot op `/chatbot` (`POST /api/chat`). RAG-pijplijn: IPLO/DSO-docs ingest → chunking → embeddings via llama.cpp `/v1/embeddings` (default poort 8082) → VectorStore (NVMe) → conversationele antwoorden met bronverwijzing, vangnet, no-hallucination-prompt. Index gebouwd via `scripts/07_build_rag_index.py`; embedding-server moet voor live gebruik actief zijn.
- 🚧 **UC-08 — Afval/circulair-dashboard:** provincie-choropleth + trend + Qwen-duiding op open CBS-afvalcijfers (83558NED, CC-BY 4.0) als open proxy voor het gesloten LMA/AMICE-aggregaat. Routes `/afval`, `/api/afval/{meta,choropleth,trend,duiding}`. Ingest via `scripts/11_fetch_afval_aggregaat.py` → `/mnt/nvme/geluidsmeter/data/external/afval/`. Code onder `src/leefomgevinglab/usecases/afval/` + `connectors/cbs_afval.py`.
- 🚧 **UC-08b — Afvaldatabase & doorkijk:** DuckDB-database (`afvaldb/`) met canoniek datamodel (CBS↔AMICE: `afval_feit` + `afvalstroom_crosswalk`), gevuld uit CBS (live) + CLO/Afvalfonds/LMA (snapshot: pdfplumber of curated CSV) via `scripts/12_fetch_afval_bronnen.py`. Holt-forecast (`afvaldb/forecast.py`) → `/api/afval/forecast` + doorkijk-grafiek en extra cijfers in de modal. DB op `/mnt/nvme/geluidsmeter/data/external/afval/afval.duckdb`.
- 🚧 **UC-08c — Brondata & data-chatbot:** linkerpaneel op `/afval` met brondata-uitleg (`GET /api/afval/bronnen`) en een NL→SQL-chatbot (`POST /api/afval/chat`, `usecases/afval/chat.py`) die read-only DuckDB-SELECT's genereert (Qwen), valideert (SELECT-only, verboden trefwoorden, LIMIT) en samenvat. Toont de uitgevoerde SQL + bron/disclaimer.
- ✅ **WFS-datakwaliteit (`/wfs-kwaliteit`, `/api/wfs-kwaliteit`):** live scan over álle REV-WFS-lagen — exacte tellingen via `resultType=hits` (+ CQL-filter per bronhouder/activiteit) en sample-metrics (geometrie, lege velden, IMEV 3.0.2). Code: `usecases/wfs_kwaliteit.py`. Cache per filtercombinatie in `cache_dir`, TTL 1 dag; koude scan duurt ~60-85s.
- ✅ **VTH-kapstok (`/vth`):** het Cim-VTH-Flo van Geonovum (Conceptueel Informatiemodel VTH Fysieke Leefomgeving, werkversie, CC BY 4.0) als kapstok over alle use-cases — 7 views met kern-objecttypen, een dekkingsmatrix (9 use-cases × 7 views), de witte vlekken en een roadmapvoorstel in twee sporen. Statische pagina (`static/vth.html`), mapping staat als JS-constante bovenin. Bron: github.com/Geonovum/vth-cim-flo.
- ✅ **Bronnenkaart CIM-VTH (`/vth-bronnen`, `/api/vth/bronnen`, `/api/vth/bronnen/check`):** 34 registraties bij rijk/RWS/provincies/waterschappen/omgevingsdiensten/gemeenten gemapt op de kern-objecttypen, met interactieve bipartiete SVG-kaart (filters, klik-focus, zoek), overlap-analyse, dekking per view en een **live endpoint-check**. Catalogus in `usecases/vth_bronnen.py` (single source of truth; de pagina haalt alles via de API). NB: `check_endpoints` gebruikt `AsyncHTTPTransport(retries=3)` — zonder retries meldt httpx vals-negatief 'onbereikbaar' op PDOK, omdat het IPv6-pad daarheen vanaf orin3 regelmatig stilvalt en httpx géén Happy-Eyeballs-fallback naar IPv4 doet (curl wel).
- ✅ **Modellen naast elkaar (`/modellen`, `/api/modellen`):** CIM-VTH-Flo, het **IMEV-stelsel** en het **GIR 2.0 databasemodel** (ICTU v3.0, 25 mei 2023, intern document — géén URL op de pagina) als lagen van een *andere soort*. Data in `usecases/modellen.py`: `ARTEFACTEN`, `LAGEN` (5), `INDELING` + `indeling()`, `VERTALINGEN` (5 begrippen), `OVERLAP` (12 begrippen REV ↔ GIR), `BEVINDINGEN` (12) en `HERKOMST`. **⚠️ "IMEV" is vier bestanden en drie soorten ding — houd ze in tekst én sleutelnamen apart:** (1) het **informatiemodel** staat bij **Geonovum** op `definities.geostandaarden.nl/imev/` (live bevestigd: `/api/begrippen` vindt 'kwetsbaar gebouw' onder conceptschema IMEV) en is normatief maar **niet toetsbaar** — je valideert er geen bericht tegen; (2) het **berichtschema** `imev30-schema.yaml` bij RWS is de technische uitwerking en wél toetsbaar; (3) de **API-specificatie** `rev-v5-specification.yaml` zegt alleen hóe je erbij komt en draagt **nul eigen schemas** (haar `components` bevat alleen `securitySchemes`); plus (4) de envelop `imev30-oas-schema.yaml` en (5) `common-schema.yaml` (NEN3610ID + GeoJSON). Van de **58 $ref's** in de spec gaan er **43 naar de envelop**, 7 naar de geotypes en maar **8 naar de inhoud** (alleen `GebouwOfLocatie` en `LocatieEVActiviteit`) — een OpenAPI is overwegend verpakking. Dus: "de API-specificatie ontsluit 2 resourcefamilies" is waar, "IMEV ontsluit 2 objecttypen" is onwaar; dat legt een keuze van de API-ontwerper bij het informatiemodel. Omgekeerd zijn `Voidable` en de CAS-regex **schema**constructies, geen modelinhoud. Tellingsleutels heten daarom `schema_*` / `api_*`, nooit `imev_*`; een test bewaakt dat, en een tweede test (`test_geen_enkele_tekst_schrijft_de_api_keuze_aan_het_informatiemodel_toe`) scant de teksten op de verschuiving. De spec zelf laat de verwarring zien: `info.version` is letterlijk `IMEV 3.0.1` terwijl de titel `REV API - v5` is. **Twee correcties (2026-11-11/12), beide gevonden door na te tellen:** de pagina beweerde eerst dat de vergunning in IMEV niet voorkomt — in werkelijkheid dragen **44 van de 79** objecttypen `basisVergunningNummer`, `datumVergunningOfMelding` én `vergunningsPlicht` (GIR laat het nummer juist vallen); en de eerder vermelde **88 objecttypen / 41 referentietypen waren niet te reproduceren**. `INDELING` is nu een regel in plaats van een lijstje: enum → enumeratie, oneOf → keuzetype, array → verzameling, object mét een van `identificatie`/`bronhouder`/`beginGeldigheid`/`bronobjectID` → objecttype, object zonder → hulptype. Dat geeft **79 + 12 + 43 + 27 + 4 + 3 = 168**. `tests/test_modellen_live.py` (marker `live`, staat standaard uit, aanzetten met `pytest --run-live` -- zie live-fixes-report.md fix 3) haalt alle vier de bestanden op en rekent élk getal na. **Valkuilen bij die bestanden:** ze hebben **CRLF**-regeleindes, dus `^[ \t]+$` schoont een witruimteregel níet — `\r` moet in de tekenklasse; en `imev30-oas-schema.yaml` bevat op **regel 449 een tab** en is daardoor **geen geldige YAML** (PyYAML weigert het hele bestand). GIR doet bevoegd gezag omgekeerd: `reg_org` met een OIN, bevoegdheid als **GEO-query** op het werkgebied (dus niet op historie te bevragen), terwijl het schema `bevoegdGezag` als enum van vier heeft — een **bestuurslaag, geen organisatie**; de organisatiesleutel is `bronhoudercode` (`^[A-Z,0-9]{3,6}$`). **De overlapsectie beantwoordt één vraag: waarop kun je joinen?** Van de 12 gedeelde begrippen zijn er **3 joinbaar, 2 deels, 7 niet** — en alle drie de joinbare leunen op een basisregistratie buiten beide registers (KvK-nummer, vestigingsnummer, BAG). Niets wat de twee registers zelf afspraken verbindt ze. Noemenswaardig voor de rest van dit lab: **`Voidable`** (11 velden, 166 plekken) eist bij een leeg veld een `geenWaardeReden` — `gegevenInTransitie`, `nietVanToepassing` of `waardeOnbekend`. Dat is de `zekerheid`-per-veld uit het waterdossier, maar als standaard; aan de GIR-kant is hetzelfde gegeven simpelweg NULL.
- **⚠️ "GIR" is óók meer dan één ding, en `/modellen` trapte daar zelf in.** De pagina leert dat
  IMEV vier bestanden en drie soorten ding is, maar schreef aan de andere kant "GIR 2.0
  databasemodel" en hing daar uitspraken onder die over *GIR* gaan. **GIR heeft óók een
  informatiemodel**, en dat staat op dezelfde laag als IMEV — niet op de fysieke. De set van
  november 2023 bestaat uit **13 views, waarvan 3 UML-klassenmodellen** (Enterprise Architect
  geeft die het diagramtype `class`: Registers, Inspectieresultaten, RGBZ-zaakschema) en 10
  architectuurviews (`business` ×3, `motivation` ×5, `application` ×1) plus een begrippenlijst met
  wettelijke vindplaats per begrip. `GIR_ARTEFACTEN` houdt die **drie** artefacten apart:
  informatiemodel, architectuurviews, databasemodel. Zodra je ze scheidt, blijken **twee
  uitspraken onjuist**:
  1. *"GIR laat de vergunningidentificatie vallen"* → de architectuur draagt
     **`Omgevingsvergunning`** en **`Vergunninghouder`** als klasse, met een **`Besluit`** dat
     `Besluitidentificatie {id}`, `Url`, `Bestuursorgaan`, ingangs- en vervaldatum voert (via het
     zaakgerichte RGBZ-spoor; er is ook een `BesluitInformatieobject`). De overlaprij zegt nu dat
     béide kanten een identificatie vastleggen maar uit twee stelsels zonder crosswalk — join
     blijft `nee`, om een andere reden. De kop **3 joinbaar / 2 deels / 7 niet** verschuift niet.
  2. *"'heeft als bevoegd gezag' bestaat in GIR niet als gegeven"* → in de view `Registers` is het
     een **gemodelleerde associatie**, naast `is gelegen in werkgebied van` en een
     `Overheidsorganisatie` met `heeft werkgebied: vlakOfMultivlak`. Het is hét **databasemodel**
     dat die relatie als GEO-query oplost in plaats van haar op te slaan.
  **De overlaptabel vergelijkt nu op gelijk niveau.** Zij zette IMEV tegenover het
  GIR-*databasemodel* — een berichtschema tegenover tabellen — en de moduledocstring zei dat zelf
  al ("een GIR-kolom en een IMEV-veld zijn niet dezelfde soort ding"), maar deed het toch omdat de
  informatiemodelkant ontbrak. Elke rij draagt nu `gir_im`, en de pagina toont **drie kolommen**:
  REV-informatiemodel + schema · GIR-informatiemodel · GIR-databasemodel. De eerste twee zijn van
  gelijke soort; het **joinoordeel blijft over de registers** gaan en niet over de modellen (3 ja /
  2 deels / 7 nee, ongewijzigd). Op twee van de twaalf begrippen lopen de twee GIR-artefacten
  uiteen, en dát is de opbrengst van het scheiden: **de vergunning** (informatiemodel:
  `Omgevingsvergunning` + `Besluit`; database: buiten scope) en de **domino-relatie**
  (informatiemodel: `datum dominoaanwijzing` + `/domino blootgesteld vanuit [0..*]` met associatie
  'domino veroorzakend naar'; database: `reg_domino_relatie` ontworpen maar nooit gebouwd).
  Twee dingen die de vergelijking op dit niveau opleverde:
  * **GIR markeert zijn joinbare sleutels zélf als afgeleid.** `/kvk-nummer`,
    `/vestigingsnummer`, `/rsin` en `/oin` staan met een schuine streep — in UML de notatie voor
    een afgeleid attribuut. De pagina concludeerde al dat de drie joinbare begrippen op een
    sleutel van buiten leunen; het GIR-informatiemodel zegt dat onafhankelijk, in notatie.
  * **De stof heeft in GIR nergens een CAS-nummer.** Niet in het databasemodel (vrije tekst in een
    sleutel-waardetabel) en niet in het informatiemodel (`Stofcategorie` met code, gevaarsoort en
    drempelwaarden; `Gevaarlijke stof` met hoeveelheid kennisgeving). IMEV valideert `CASNummer`
    als eigen type. Dit is het enige van de twaalf begrippen waarvan de GIR-kant er in het
    informatiemodel **niet** beter uitkomt.
  De `gir`-rij in `LAGEN` zegt nu zelf dat zij over het **databasemodel** gaat en niet over GIR —
  die gelijkstelling ("GIR = fysiek") is precies wat de twee uitspraken liet verschuiven. De
  pagina toont de drie artefacten met dezelfde opmaak als de IMEV-artefacten.
  **Twee andere dingen uit die set, inhoudelijk relevant voor dit lab:**
  * De view **`Inspectieresultaten`** modelleert een bevinding **compléter dan `/toezicht`**: een
    `Aandachtspunt` draagt normenkader, stelling, voorgesteld oordeel en voorgestelde wettelijke
    grondslag van de overtreding; een `Inspectieresultaat` daarnaast bevinding, motivatie,
    oordeel, grondslag mét juncto, datum herstel geconstateerd en **begunstigingstermijn**. De
    signalen hier hebben bewijs, herkomst en zwaarte — maar géén grondslag en géén termijn.
  * GIR heeft wél een eigen vorm voor onzekerheid, maar alleen voor datums: een **eigen type
    `DatumIncompleet`** plus multipliciteiten (`[0..1]`, `[0..*]`). "Aan de GIR-kant is het
    simpelweg NULL" was dus te kort door de bocht; wat GIR niet heeft is een **reden** bij een
    leeg veld, en dat is het verschil met IMEV's `Voidable` dat overblijft.
  **De modelset staat niet in de repo** — intern document zonder publieke URL, net als het
  ICTU-databasemodel; de pagina zegt bij beide artefacten expliciet "geen publieke URL", zodat zij
  niet suggereert dat een lezer het kan nakijken.
  **En een test die om de verkeerde reden groen bleef:**
  `test_de_vergunning_is_eenzijdig_vastgelegd` asserteerde `"buiten scope" in o["gir"]` — en de
  gecorrigeerde tekst bevat die woorden óók, nu over het databasemodel. De test keurde de
  correctie dus goed zonder haar te zien. Hij heet nu
  `test_de_vergunning_is_aan_beide_kanten_vastgelegd_maar_onvergelijkbaar` en pint de inhoudelijke
  positie.
- 🚧 **Doelbeeld D-VTH (`/dvth`, `/api/dvth/architectuur`):** doelarchitectuur voor één MBA Seveso-inrichting — DSO-loket → zaaksysteem OD → Data.OD → analyse/beoordeling → besluit als STOP/TPOD met uit IMEV afgeleid objectmodel → omgebouwd REV → GIR/LBR → LHSO, met CIM-VTH-Flo als informatiemodel. Interactieve architectuurplaat (17 componenten, 17 koppelvlakken), de keten in 8 stappen en een roadmap van 23 features. Data in `usecases/dvth.py`. **Het ketentje draait**: `GET /api/dvth/keten?live=1&straal=1000` doorloopt alle 8 stappen in ~1,4 s, met live bevraging van REV-WFS (DWITHIN) en BAG (bbox) op het RD-punt in stap 3; `live=0` slaat dat over en is reproduceerbaar. Code in `usecases/dvth_keten/` (casus, cim, bronnen, tpod, lbr, lhso, stappen, motor). Straal begrensd op 5000 m.
- ✅ **Maquette van het eindbeeld (`/maquette`, `/api/maquette`):** het functioneel eindbeeld
  uit BALO als **gebouw dat je ronddraait**. Een **bodemplaat** waar alles op rust, **vier
  verdiepingen**, een **dak** met de stelselafspraken, en twee gevels — links wordt geleverd,
  rechts wordt gehaald. In de gevels zitten **vensters**, en achter elk venster zit een vraag die
  BALO woordelijk stelt. Doel: iets tastbaars dat ook zonder architectuuropleiding te begrijpen
  is; daarom een gebouw en geen diagram.
  **De eerste versie toonde óók de transitie** (vijf plateaus door de tijd) en werd daarmee te
  druk om te lezen. Die data is niet weg: `usecases/maquette.py` en zijn tests blijven, en de
  route staat op `/api/maquette/transitie` — met op de pagina de mededeling dat een eigen
  weergave later komt. Niet stil laten vallen, niet half tonen.
  **De indeling is van BALO, niet verzonnen.** §5.5 zet de stelselafspraken bovenaan, de
  bevoegde gezagen links, de gebruikers rechts en de fysieke stelselinfrastructuur onderaan. §8.1
  beschrijft de informatieketen in **vijf niveaus**: data → informatie → kennis → inzicht en
  handelingsperspectief, plus **terugkoppeling** die de keten sluit ("geen lineaire
  productielijn, maar een leercyclus"). Die vier niveaus zijn de verdiepingen; de terugkoppeling
  is het **trappenhuis**, want zij gaat naar beneden terwijl al het andere omhoog gaat.
  **Wat van dit lab is:** het gebouw als vorm, en op welk vlak elke vraag hangt. BALO tekent een
  platte figuur en hangt de vragen nergens aan. `HERKOMST` markeert dat per regel en de pagina
  toont die tabel; een test eist dat er zowel `bron`- als `lab`-regels in staan.
  **Een bevinding die uit de data zelf komt** en die je ziet door het gebouw te draaien: onderin
  levert bijna alleen de aanbodkant (4 om 1), bovenin haalt bijna alleen de vraagkant (2 om 4).
  Een test dwingt dat af — valt het weg, dan is het een stapel en geen keten.
  **⚠️ Let op het teken van `rotateX`.** In CSS kantelt een positieve `rotateX` de bovenkant van
  de kijker wég, dus *van bovenaf kijken is een negatieve hoek*. Dat stond eerst omgekeerd en toen
  toonde de knop "Van boven" het gebouw van onderen — alleen te zien door ernaar te kijken, niet
  door de code te lezen. Een test pint de tekens nu vast. **En de bodemplaat heeft een eigen
  ónderkant nodig**: zij had alleen een bovenvlak, en van onderaf keek je tegen niets aan.
  Vorm: CSS-3D, **geen WebGL-bibliotheek** — de vlakken blijven DOM-elementen, dus de teksten
  blijven scherp en de vensters zijn met het toetsenbord bereikbaar. Draaien kan met slepen, met
  de pijltjestoetsen en met vijf standpuntknoppen; een standpunt is **deelbaar via de URL**
  (`?standpunt=bodemplaat`). De schaal volgt de scènebreedte, met een `ResizeObserver` erop.
  **⚠️ Valkuil bij het controleren in chromium headless:** `--window-size=400` geeft hier géén
  viewport van 400 maar van **500**. Een screenshot lijkt dan afgesneden terwijl de opmaak klopt.
  Meet de viewport eerst met een kale testpagina voordat je een "mobiele" fout gaat repareren die
  er niet is.
- 🚧 **Doelbeeld directe lozing (`/lozing`, `/api/lozing/{architectuur,keten}`):** spiegeldossier van D-VTH — één lozingsactiviteit op een rijkswater (IJssel bij Deventer), RWS namens de minister als bevoegd gezag. Kern: de **knip** (gemeente doet de MBA, waterbeheerder de lozing, geen koppelvlak ertussen), ABM + immissietoets i.p.v. afstandscirkels, **Aquo** i.p.v. IMEV als annotatiebron, en een **Register Lozingen dat niet bestaat**. Stap 2/3 leiden het bevoegd gezag **live** af: een treffer in de KRW-service van RWS (89 rijkswaterlichamen) betekent rijkswater → minister; PDOK bestuurlijke gebieden geeft de gemeente. Code: `usecases/lozing.py` + `usecases/lozing_keten/`.
- **Gedeelde ketenkern** (`usecases/ketenkern/`): `cim` (objectbibliotheek met validatie tegen het CIM), `lhso` (interventiematrix), `wfs` (WFS-helpers met retries) en `motor` (dossier-onafhankelijk; een dossier levert DOSSIER/CASUS/STAPPEN/ANNOTATIES). Beide tabs draaien op **één sjabloon** `static/keten-tab.html`; de route vervangt `__DOSSIER__` en alle teksten komen uit `PRESENTATIE` in het architectuurmodule. Een derde dossier kost daarmee alleen een architectuur- en een ketenmodule.
- ✅ **BALO-redeneerlijnen (`/balo`, `/api/balo/overzicht`):** beide doelbeeld-casussen geplot op het redeneermodel van de BALO-businessarchitectuur v0.9 (concept, RWS/WVL). Per ketenstap links **redeneerlijn 2** (waardestroom W1–W8 → informatiebehoefte → informatiefuncties uit de gesloten set van 9) en rechts **redeneerlijn 3** (informatieobjecten → registers, met status bestaat/moet om/bestaat niet). Plus de gedeelde knelpunten (stappen waar béíde ketens vastlopen), een besluitenkwadrant kosten × waarde met 7 besluiten, en de vijf vragen die BALO zelf aan management stelt. Kern van de pagina is de **informatiebehoefte als spil**: 16 behoeften (één per ketenstap), elk met eigenaar, waarde-als-het-lukt, kosten-als-het-niet-lukt en status (voldaan/deels/niet). Analysefuncties `behoeften()`, `cyclus()`, `waardeoverzicht()`, `besluitwaarde()` en `onbediend()`. Uitkomst: 2 voldaan / 6 deels / 8 niet; 5 van 8 waardestromen geraakt (W1, W3, W8 niet); W5 is het zwartste gat met 5 onvervulde behoeften. De waarde van een besluit is niet beweerd maar afgeleid uit de behoeften die het bedient — een test dwingt af dat waarde=hoog ≥2 behoeften betekent. Data in `usecases/balo.py`. NB: structuur en begrippen komen uit het document, de koppeling aan de casussen en de kosten-batenafweging zijn van dit lab — dat onderscheid staat ook op de pagina.
- ✅ **Gebruiksruimte (`/gebruiksruimte`, `/api/gebruiksruimte?locatie=&debiet=&live=`):** 'wat kan hier nog?' voor een lozing op de IJssel. Combineert (a) **regels op de locatie live uit het DSO** (Ozon `regelingen_op_punt`, ~20 per punt) geclassificeerd naar **direct werkend / indirect werkend / geldt hier maar raakt dit voornemen niet** — dat laatste is de waterschapsverordening op rijkswater; (b) een **synthetisch register** met 5 bestaande lozingsvergunningen op hetzelfde waterlichaam; (c) de rekensom ruimte-tot-de-norm per parameter. Drie locaties (Brummen/Deventer/Doesburg, 2 provincies) aan hetzelfde KRW-waterlichaam: de regels verschillen per locatie, de gebruiksruimte is gedeeld. Code: `usecases/gebruiksruimte/` (gebied, regels, ruimte, service). NB: de vergunde vracht zit al ín de achtergrondconcentratie en wordt dus **niet** van de ruimte afgetrokken — hij staat apart om te tonen hoeveel van de belasting in menselijke hand is. PFOA heeft per opzet géén ruimte (achtergrond > norm); stikstof kantelt om bij ~20.000 m³/u. Getallen illustratief, mechanisme echt.
- ✅ **EV-gebruiksruimte (`/evruimte`, `/api/evruimte?locatie=&live=`):** ruimtelijke tegenhanger van `/gebruiksruimte`, als **maplibre-kaart**. De drie aandachtsgebieden van een voorgenomen Seveso-inrichting (gifwolk 1500 m, brand 90 m, explosie 60 m) over de **bestaande REV-aandachtsgebieden** (live als GeoJSON), met de verblijfsobjecten eronder **live geteld in de BAG per gebruiksdoel** en ingedeeld naar zeer kwetsbaar / kwetsbaar / beperkt kwetsbaar. Vijf locaties: Europoort (ruim), Botlek en Gouda (vol), Zutphen, plus een illustratieve plek pal naast een school waar de harde grens wél optreedt. Code: `usecases/evruimte/`. **Cruciaal: PDOK negeert `cql_filter` volledig** (BAG én bestuurlijke gebieden) — een DWITHIN in CQL geeft stilzwijgend de héle dataset terug. Gebruik de standaard **FES-filter via POST** (`filter=<fes:Filter>` met `DWithin` + `PropertyIsLike` op `gebruiksdoel`); de REV-GeoServer accepteert `cql_filter` juist wél. BAG-tellingen draaien parallel (ThreadPoolExecutor, 8 workers): 13 s → 4-6 s.
- ✅ **Begrippen (`/begrippen`, `/api/begrippen`, `/api/begrip?term=`):** de 10 termen die dit lab hardgecodeerd gebruikte, live opgezocht in de **Stelselcatalogus Omgevingswet** — een federatieve SKOS-begrippengraaf (conceptschema's o.a. Regelgeving, Wetgeving, Activiteit, IMEV, IMAM). Alle 10 gevonden, met definitie en juridische vindplaats (Seveso-inrichting → bijlage I Bal; zeer kwetsbaar gebouw → bijlage VI onder E; ZZS → art. 5.22a). Connector `connectors/stelselcatalogus.py`, register + oplossing in `usecases/begrippen.py`. **Drie valkuilen van deze API**: (1) `Accept: application/json` geeft **406** — het moet `application/hal+json` zijn; (2) queryparameters die niet bij het endpoint horen geven een **400**, dus bij `/begrippen` alleen `zoekTerm` meesturen (géén `pageSize`); (3) er komt **geen RDF** uit (turtle/ld+json/rdf+xml → 406) en de SKOS-relaties zijn dun gevuld — aan de juridische kant ontbreken ze. Zelfde `DSO_API_KEY_PROD` als Ozon; opzoekingen draaien parallel en worden een dag gecachet. Op `/evruimte` staat de juridische definitie nu naast onze BAG-afleiding, met het verschil expliciet benoemd.
- ✅ **Waterdossier (`/water`, `/api/water/hub`):** de waterpagina's als één dossier met een
  gedeelde subnav-balk — **14 leden** vandaag (geen vier, zoals hier eerder stond; vraag
  `/api/water/hub` als je het actuele lidmaatschap wilt weten in plaats van het hier na te lezen).
  De samenvatting per lid in `LEDEN` is een **bewering over de pagina** en kan dus verouderen:
  de `toezicht`-samenvatting beloofde na de wasstraat-splitsing nog tien regels plus pijplijn en
  runlog, terwijl die pagina drie regels toont en geen van beide heeft. Een test in
  `tests/test_water_hub.py` controleert nu per lid dat zulke beweringen met de route kloppen.
  `usecases/water_hub.py` is de enige plek waar staat wat het dossier is; de balk wordt eruit
  gegenereerd en via een `__WATERNAV__`-placeholder geïnjecteerd (zelfde truc als `__DOSSIER__`
  in `_keten_tab`). NB: `keten-tab.html` bedient óók `/dvth` — daar wordt de placeholder leeg
  vervangen, want dat is geen waterpagina.
  **De homepagina mag géén tweede inhoudsopgave van het dossier worden:** `/` draagt precies één
  ingang (`/water`) en linkt niet naar de losse leden — anders staat het lidmaatschap op twee
  plekken en verouderen ze uit elkaar. `tests/test_api_water.py::test_de_homepagina_heeft_precies_een_ingang_naar_het_waterdossier`
  leidt die lijst uit `LEDEN` af, dus een nieuw dossierlid wordt automatisch meebewaakt. De
  **rondleiding** (`/demo`) valt hier bewust buiten: dat is een geleide wandeling langs concrete
  pagina's en juist wél bedoeld om diep te linken.
- ✅ **Prik op de kaart (`/waterruimte`, `/api/waterruimte?x=&y=&debiet=&live=`):** "wat kan hier
  nog" op een willekeurig RD-punt. `waterprofiel.py` maakt van een KRW-feature een profiel met
  echt (naam, `owl_id`, `wbhnaam`, `owltype`, `owlcat`, `owlstat`, omvang, `gemdiepte`) strikt
  gescheiden van afgeleid (debiet, achtergrondconcentraties) — elk afgeleid veld draagt een
  herkomstregel. `gemdiepte` staat in die opsomming maar is in de praktijk altijd leeg: de bron
  levert er een sentinel (-9999) voor in plaats van een meting (zie de valkuil hieronder), en
  `waterprofiel.profiel()` zet die sentinel om naar `None` in plaats van hem als echt getal door
  te geven. De waterbeheerder komt uit het KRW-veld `wbhnaam`, met de oude afleiding
  (rijkswater → RWS, anders het waterschap) als terugval wanneer dat veld leeg is. **Het register
  is echt waar het bestaat:** de Atlas voor een Schone Maas (`connectors/smwk_atlas.py`) levert
  voor het Maasstroomgebied 72 vestigingen en 782 vergunde voorschriften, ruimtelijk bevraagbaar
  op RD (`inSR=28992`); daarbuiten valt het lab terug op het synthetische register. Dat contrast
  is de boodschap. Vestigingen zonder vergunningkenmerk (o.a. de RWZI's van Waterschapsbedrijf
  Limburg) worden ontdubbeld op `Locatiecode` en blijven met `kenmerk: None` in het register staan
  in plaats van weggefilterd. Hun voorschriften worden **óók** op `Locatiecode` gekoppeld (naast
  de normale koppeling via `Kenmerk`): tabel 2 draagt 29 rijen met een leeg/NULL kenmerk, verdeeld
  over zes locatiecodes (`HAVENS` 7, `RWZIB`/`RWZIL`/`RWZIW` 5, `RWZIV` 4, `JWMAAS` 3) — zonder die
  tweede koppeling bleven precies de posten zonder kenmerk, waaronder vier rioolwaterzuiveringen,
  zonder voorschrift en dus zonder vracht. Vrachtafleiding in drie lagen (`atlas_register.py`):
  eenheid is al een vracht → direct; concentratie + debiet-voorschrift → berekend (28 van de 69
  posten); anders → getoond zonder vracht, met reden (`onbepaald`, voorbehouden aan de stoffen die
  dit lab volgt; wat erbuiten valt telt als `buiten_crosswalk`). Komt een stof met meerdere
  grenswaarden voor in dezelfde vergunning, dan wordt na ontdubbeling van identieke rijen het
  **maximum** genomen, niet de som. Twee getallen die je uit elkaar moet houden: **45 van de 64**
  vergunningen in de bron dragen (ná ontdubbeling van identieke rijen, exclusief het
  Debiet-voorschrift zelf) voor minstens één stof meer dan één grenswaarde — dáárom is optellen
  fout — terwijl het veld `meerdere_grenswaarden` er **9 van de 63** posten mét kenmerk mee
  markeert, omdat het alleen gaat over de drie stoffen die dit lab volgt. (De 64 is geen tikfout
  naast de 63: dat zijn de 63 kenmerken plus één emmer met de rijen zonder kenmerk.) Waar de
  vracht van sommige vergunningen niet te bepalen viel, is het vergunde totaal een **ondergrens**;
  `ruimte.bereken()` meldt dat expliciet in een kanttekening.
  Let op: de Atlas-lagen zijn publiek maar dragen **geen expliciete licentie** — live bevragen met
  bronvermelding, nooit kopiëren. PFOA komt er niet in voor, terwijl dat juist de stof is waarvan
  de achtergrond boven de norm ligt.
- ✅ **Kan · mag · gebeurt (`/kmg`, `/api/kmg?meetpunt=&live=`):** de drie lagen van de
  DSO-voorlichtingsfolder toegepast op water. **Kan** = de regels op het punt, live uit het DSO;
  **mag** = de vergunningen, live uit de Atlas voor een Schone Maas; **gebeurt** = de gemeten
  waarden uit het **Waterkwaliteitsportaal** van Informatiehuis Water (meetjaar 2025, Aquo IM
  Metingen). `scripts/13_fetch_wkp_metingen.py` verdicht 142 MB CSV naar mediaan en maximum per
  meetpunt en stof: **384.259 rijen → 4822 metingen op 92 meetpunten**, waarvan de pagina er **9**
  toont (de set is landelijk, de pagina volgt alleen de Maas). **Drie valkuilen van die bron:**
  `MonsterCompartimentCode` is bij chemische metingen leeg (filteren op `OW` geeft nul stikstof- en
  zinkmetingen); `KwaliteitsoordeelCode = '99'` ("Hiaat waarde") draagt de sentinel
  `999999999999` — 3000 van de 384.259 rijen, geteld over álle parameters in het bestand; en
  `Monsterophaaldatum` is leeg, de datum staat in `Begindatum`; en **`HoedanigheidCode`
  scheidt grootheden die hetzelfde heten** — zink staat op élk Maas-punt in twee reeksen, totaal
  (`NVT`) en opgelost na filtratie (`nf`), bij Eijsden 52 metingen met mediaan 7,15 µg/l tegen 52
  met 2,80. Zonder die sleutel poolt de verdichting ze tot 4,54: een concentratie die niemand
  gemeten heeft. De KRW-norm voor zink geldt juist voor de opgeloste fractie. **Geen machine-ingang
  voor de méétwaarden:** de Digitale Delta API van RWS geeft 401 op elk data-eindpunt en de
  WKP-module die dit oplost komt begin 2027, dus de meetset blijft een handmatige momentopname.
- **De WKP-downloadmodule heeft wél een open JSON-API** (gevonden 2026-10-29, `scripts/18`). De
  Angular-app waar je je doorheen klikt praat met `https://wkp.rws.nl/api/v1/data-downloads` —
  geen sleutel, geen login. De basis staat in de runtime-configuratie van de app zelf,
  `https://wkp.rws.nl/assets/config/config.json`, veld `backendUrl`; vraag je die op `/`, dan
  krijg je de SPA-fallback (200 met index.html) in plaats van 404, dus een pad "bestaat" daar
  altijd. Drie eindpunten: `GET /options/themes-and-subjects` (de catalogus, **29 onderwerpen** in
  vier thema's), `GET /options/filter-values?subject_id=N` (jaren, districten, beheerders per
  onderwerp) en `POST /download` (zip met csv of gpkg). **Het POST-verzoek is een lijst en het
  veld heet `subjectId`** — stuur je het `subject`-object dat de frontend intern doorgeeft, dan
  antwoordt de API `[0].SubjectId: Must not be null`. Niet officieel gepubliceerd, dus `scripts/18`
  zoekt de onderwerp-id's op naam op in plaats van ze hard te coderen; een verschoven catalogus
  valt dan luid om in plaats van stil het verkeerde bestand binnen te halen.
- **Twee registers die het locatieprobleem verkleinen** (`scripts/18_fetch_krw_registers.py` →
  `krw_monitoringlocaties.json` + `krw_waterlichamen.json`). `KRW-monitoringlocaties-geometrie`
  (id 9) is strikt beter dan het meetobjectenbestand per beheerder dat `scripts/13` gebruikt: dat
  dekt alleen Rijkswaterstaat (322 punten, 131 mét waterlichaam), dit dekt heel Nederland (**1571
  punten, alle 1571 mét `waterlichaamCode`**) en komt als GeoPackage al in EPSG:28992 binnen. Het
  overbrugt ook de namespacebreuk die `scripts/17` met de hand oplost: Eijsden heet in de
  meetwaarden `NL80_EIJSDPTN` en hier `NL91_EIJSDPTN`, mét `NL91BOM` erbij.
  `KRW-oppervlaktewaterlichamen` (id 17) geeft 745 waterlichamen met district en beheerder;
  **district Maas telt er 163**, waarvan 14 van Rijkswaterstaat, terwijl
  `toerekening.STROOMVOLGORDE` er **8** kent — het Julianakanaal (`NL91JK`) en de Midden-Limburgse
  en Noord-Brabantse kanalen (`NL90_1`) zijn rijkswater in de Maas en vallen vandaag buiten de hele
  toerekening. Hiermee kan de zoekcirkel van 50 km vervangen worden door een lidmaatschapsvraag
  ("ligt dit waterlichaam in district Maas?"). **Wat er in géén van de 29 onderwerpen staat** is de
  bovenstrooms-relatie tussen waterlichamen; `VoorgangerCode` lijkt erop maar is versiehistorie,
  geen hydrologie. De stroomvolgorde blijft dus een labkeuze.
  **Let op de eenheden** — dit is de duurste valkuil van deze use-case: stikstof staat in mg/l maar
  **PFOA en zink in µg/l**. `toerekening.bijdragen()` rekent intern in mg/l en schaalt de uitkomst
  naar de eenheid van de meting (`EENHEIDSFACTOR`); een onbekende eenheid faalt luid in plaats van
  stil mg/l aan te nemen. Zonder die schaling stond zink een factor 1000 te laag op de pagina —
  alle tests gebruikten mg/l-fixtures, dus dat kwam pas boven bij een live run.
  Het toerekeningsmodel (`usecases/kmg/toerekening.py`) deelt de vergunde vracht van bovenstroomse
  lozingen door de jaarafvoer en is **uitdrukkelijk een bovengrens, geen vaststelling** — de woorden
  "veroorzaakt door" staan niet op de pagina, en `tests/test_api_kmg.py` bewaakt dat op de HTML
  zelf — plus dat de pagina "bovengrens", "kan bijdragen" en "nooit een vaststelling" ook echt
  uitspreekt, want vermijden is niet genoeg. Een afvoer van nul werpt een
  `ValueError`: juist daar valt het model om, en een stille 0,0 zou "deze vergunning draagt niets
  bij" suggereren. **Drie getallen in dat model zijn labkeuzes en komen uit geen bron:** de
  stroomvolgorde van de Maas (Bovenmaas → Grensmaas → Zandmaas → Bedijkte Maas → Beneden Maas →
  Bergsche Maas → Haringvliet-oost → -west), de jaarafvoer per waterlichaam
  (`service.DEBIET_M3_S`) en de zoekstraal (`kmg.straal_m`, 50 km — ruimer dan de 5 km van
  `/gebruiksruimte`, want bovenstrooms kan tientallen kilometers weg liggen). Alle drie staan nu in
  de proclaimer benoemd; eerder lazen ze als brongegeven.
  **Het waterlichaam per vergunning wordt opgezocht uit haar eigen coördinaat**
  (`service._waterlichaam_per_vergunning()`, uit `voorschriften[].rd`, ontdubbeld en parallel), niet
  uit dat van het meetpunt. Dat ging eerder mis en maakte `is_bovenstrooms()` dode code: élke
  vergunning binnen de straal telde mee, ook benedenstroomse. Een vergunning waarvan het
  waterlichaam niet te vinden is, blijft met reden buiten de toerekening
  (`mag.buiten_toerekening`) in plaats van stil weg te vallen. **Let op de grofmazigheid:**
  `is_bovenstrooms(X, X)` is waar, dus een lozing op hetzelfde waterlichaam telt mee ook als zij
  daarbinnen stroomafwaarts ligt; preciezer zou een stromingsmodel vergen. Pagina en proclaimer
  zeggen dat nu expliciet.
  **Het informatiemodel lozingsvoorschriften** (`usecases/kmg/lozingsmodel.py`) codificeert elk
  Atlas-voorschrift en voert per veld een **zekerheid** mee: uit de bron, afgeleid, aangenomen of
  ontbrekend. Dat tweede is het punt — een model dat alleen velden vastlegt maakt een onvolledige
  vergunning er netjes uitzien. Uitkomst over de negen meetpunten: **85% bruikbaar, nul volledig**.
  Die nul is de bevinding: geen enkel voorschrift draagt een geldigheidsperiode, en bij alle is de
  hoedanigheid een aanname (`HOEDANIGHEID_AANNAME`, effluent gelezen als totale fractie).
  De parameterreferentie is de **Aquo-domeintabel Parameter**, op te halen als CSV van
  `https://www.aquo.nl/images/aquo/a/a3/Parameter.csv` — aquo.nl is een wiki en publiceert elke
  domeintabel zo. 5630 geldige codes; de 1479 vervallen worden overgeslagen. Dat is gemeten tegen
  de vorige aanpak (afleiden uit de WKP-meetwaarden, 492 codes): **57% → 84% bruikbaar** op
  dezelfde 367 voorschriften, en de gekoppelde stoffen per register van **3 → 42**. De winst zit in
  alledaagse begrippen die RWS niet chemisch meet maar die in elke vergunning staan: `Zuurgraad` →
  `pH`, `Debiet` → `Q`. Ook `"som 6 metalen (Zn, Cu, Pb, Ni, Cr, As)"` heeft een code
  (`smetln6`) — dit lab nam eerst aan van niet.
  **Let op: `Zwevende stof` koppelt níét**, al stond dat hier eerder wel. De Aquo-code `ZS` is
  **vervallen** (beide rijen in de domeintabel), en `laad_parameters()` slaat vervallen codes
  over — terecht, want een ingetrokken code is geen sleutel. Gevolg: `op_naam["zwevende stof"]`
  is `None`, terwijl dit mét 83 voorschriften de **meest voorkomende parameter in het hele
  Maasregister** is. Geconstateerd 2026-10-29 door de kwaliteitscontrole op `/kennisgraaf`;
  `Vervangen door` is leeg, dus de bron biedt geen opvolger.
  `toerekening.bijdragen()` koppelt daardoor op Aquo-code (`vrachten_aquo`) met de Nederlandse
  omschrijving als terugval. **De chemische normen** komen uit `KRW-toetsresultaten`
  (`scripts/17`): zink ≤ 7,80 µg/l op het **jaargemiddelde** van de **opgeloste** fractie, per punt
  gecorrigeerd voor biobeschikbaarheid (3,99 bij de Haringvlietsluis). De koppeling meetpunt ↔
  toetsing gaat op `MeetobjectLokaalID` plus de stroomgebiedsnamespace van het waterlichaam, want
  RWS publiceert metingen onder `NL80` en toetsingen onder `NL91`/`NL94`. Let op: in datzelfde
  bestand staan ook klassengrenzen van de fysisch-chemische maatlatten, waar `Normwaarde` de grens
  is van de klasse waarin de waarde viel — die worden uitgesloten op het oordeel ("Voldoet" hoort
  bij een norm, een klassenaam bij een maatlat).
  **Een vergunning begrenst de totale vracht**, dus aan een meting van een deelgrootheid wordt
  níet toegerekend: `HOEDANIGHEID_VERGELIJKBAAR` is een toelatende lijst (`NVT`, `N`), zodat een
  onbekende hoedanigheid géén toerekening oplevert in plaats van een stille vergelijking van twee
  verschillende grootheden.
  **Wat eruit komt is de boodschap:** het vergunde deel van een gemeten waarde loopt van **0%** tot
  **14%** — 14,3% stikstof en 7,0% zink bij Belfeld boven, 0,1% en 2,1% bij Eijsden ponton, en bij
  Keizersveer precies niets terwijl er 19 vergunningen in het register staan (geen ervan ligt
  bovenstrooms). Het register verklaart hoogstens een zevende van wat er gemeten wordt, en op de
  meeste punten niets. PFOA levert een lege bijdragenlijst: die stof
  komt in het register niet voor. **Gecorrigeerd (live-fixes-report.md, fix 2):** `/api/kmg` las
  het chemische-normenbestand via `leefomgevinglab.kmg.normen_pad`, een sleutel die niet bestaat
  — de normenset was daardoor altijd leeg en de pagina toonde alle stoffen zonder normoordeel,
  ook zink. Het echte pad staat onder `leefomgevinglab.waterpresentatie.normen_pad`
  (`_kmg_normen_pad` in `api.py`); nu die klopt, krijgt zink op elk meetpunt zijn echte KRW-norm
  (7,80 µg/l op de opgeloste fractie, zoals hierboven). PFOA blijft zonder normoordeel, maar dat
  is nu een echt gat in de bron (geen norm of toetsresultaat in de KRW-download), niet een
  configuratiefout. Terugvallen op de illustratieve normen die dit lab elders gebruikt blijft
  verboden — dat zou een echte meting tegen een verzonnen norm zetten. De pagina draagt een
  **proclaimer** die uit de data zelf wordt opgebouwd, zodat tekst en getallen niet uit de pas
  kunnen lopen met wat de lezer ziet.
- ✅ **Wasstraat & toezicht — één regelset, twee lezers (`/wasstraat` + `/toezicht`):** hetzelfde
  Maas-register, maar met de vraag van de **toezichthouder** in plaats van die van de
  vergunningverlener: niet "wat kan hier nog" maar **"waar moet ik gaan kijken"**. Een gat in de
  data is hier zélf een signaal, geen beperking. Tien **deterministische** signaalregels
  (`usecases/toezicht/signalen.py`), elk een gewone functie met een eigen test — **géén taalmodel
  in de signaalbepaling**, want een signaal dat een model "zag" is niet navraagbaar. Het model legt
  alleen uit, en **zwijgt zonder benoemde vindplaats**.
  **De tien regels staan op twee assen, en die twee zijn níet hetzelfde — houd ze apart:**
  * **`Regel.laag`** (één `frozenset` in `signalen.py`, nergens een tweede lijst) scheidt
    **papier** (7) van **werkelijkheid** (3): heeft deze regel meetdata of stroomrichting nodig?
    Dat bepaalt op wélke pagina zij landt — `/wasstraat` voor de vergunningverlener,
    `/toezicht` voor de toezichthouder. Beide filtermodules (`wasstraat.dossier._is_papier`,
    `toezicht.weergave._is_werkelijkheid`) lezen die ene eigenschap.
  * **`signalen.is_voorbehoud`** (afgeleid uit drempel ≥ 99 in `DREMPELS`) scheidt binnen het
    papier de **bevinding** (5) van het **voorbehoud** (2). `niet_regime_zuiver` en
    `geen_geldigheidsduur` zijn geen bevinding: de eerste vuurt op **68 van de 69**
    vergunningen (hij vuurt juist alléén als het regime er staat, dus "vermeld het regime" was
    een onuitvoerbare opdracht), de tweede op **69 van de 69** omdat de Atlas geen
    geldigheidsperiode per voorschrift kent — een tekort in de bron, niet in de vergunning.
    Stonden ze als bevinding in de lijst, dan was het minimum aantal papiersignalen 1 en was
    `wasstraat.op_orde` **dode code**. Nu zijn ze een voorbehoud en haalt **4 van de 69**
    vergunningen nul bevindingen. **Let op bij dat getal:** zonder de Aquo-domeintabel zijn het
    16, want dan vuurt `vervallen_code` nergens (55 treffers) omdat elke code geldig lijkt.
    `tests/test_toezicht_live.py::test_op_orde_is_bereikbaar_op_het_echte_register` pint dit op
    het echte register — een fixture kán dit niet vangen, want de fixture is de verzonnen toestand.
  **`/wasstraat` (de vergunningverlener)** draagt per bevinding de reparatie die eruit volgt, de
  uitleg mét vindplaats (de vierde pijplijnstap kost **7,4 van de 7,4 seconden** en leverde eerder
  `waarom`/`waarom_vindplaatsen` op die de pagina niet toonde — dat was het bewijsstuk dat de
  reparatie onderbouwt, bijvoorbeeld *"'Zwevende stof' is in de Aquo-domeintabel ingetrokken (code
  ZS, status Vervallen)"*), en de pijplijn plus runlog. **Read-only, bewust**: geen POST/PUT/
  PATCH/DELETE op enige route, en de enige bezoeker-gestuurde invoer is de id-string, die
  uitsluitend in een opzoeking op het register wordt gebruikt. De tests eisen **405** en niet
  `in (404, 405)` — met 404 erbij slaagt zo'n test ook als de route helemaal weg is en bewaakt
  zij niets.
  **`/toezicht` (de toezichthouder)** draagt de drie werkelijkheidssignalen met bewijs en de vraag
  die je ter plaatse kunt stellen, de metingen bij het waterlichaam van deze vergunning (mét
  hoedanigheid en oordeel apart), en de uitkomst van de papiercontrole als context. Het
  waterlichaam staat **alleen hier** op de kaart, niet op `/wasstraat`: de Atlas draagt dat veld
  nooit, dus de papierkaart zette er een rood ontbrekend-signaal op terwijl de zusterpagina het
  uit een coördinaatopzoeking wél weet — twee publieke pagina's die elkaar tegenspraken over
  hetzelfde feit.
  **De identiteit reist mee in de URL** (`?vergunning=` op `/wasstraat`, `?vestiging=` op
  `/toezicht`, met `history.replaceState` bij wisselen in de kiezer). Zonder dat las een
  inspecteur bij Solvay "13 bevindingen staan open voor **deze** vergunning", klikte door, en
  kreeg de bevindingen van een andere vestiging te zien.
  **Twee voorbehouden die `/toezicht` expliciet uitspreekt** omdat `norm_overschreden_bovenstrooms`
  anders een richting beweert die zij niet heeft vastgesteld: (a) betreft een bewijsregel een
  meetpunt in hetzelfde waterlichaam als de vestiging, dan is de stroomrichting daar niet
  vastgesteld — `toerekening.is_bovenstrooms(X, X)` is per definitie waar (live op `HAVENS`:
  twee van de vier bewijsregels liggen stroomopwaarts van de vestiging); en (b) staat het
  waterlichaam niet in `toerekening.STROOMVOLGORDE` (`NL90_1` draagt **18** vergunningen), dan
  meldt het dossier dat via `toerekening.reden_niet_bovenstrooms()` in plaats van stil "geen
  signaal bovenstrooms" te laten lezen.
  **De invariant waarop de twee pagina's samen rusten** staat als live test vast: `/wasstraat`
  draait de pijplijn met één contextsleutel en `/toezicht` met vijf, dus "13 bevindingen staan
  open" is alleen waar zolang geen papierregel een contextsleutel leest. Over alle 69
  vergunningen: 0 afwijkingen. Eén regel die dat ooit doet, en de twee pagina's noemen
  verschillende getallen voor hetzelfde feit zonder dat er iets omvalt.
  Verder: `dossier.py` (de kaart met ontbrekende velden zichtbaar, de gerangschikte signalen, de
  voorbehouden), `rapport.py` (een `.xlsx`, een blad per signaal), `graaf.py`/`vraag.py` (lokale
  triple-store plus een **AST-gebaseerde** SPARQL-validator — regex op SPARQL is te omzeilen; een
  ontbrekende `LIMIT` wordt geweigerd en een te grote ook, zodat de uitgevoerde query nooit
  afwijkt van wat de lezer ziet), `aquo.py` (geldige **én ingetrokken** codes uit de ruwe CSV —
  zonder die tweede opzoektabel is signaal 2 dode code, want `lozingsmodel.laad_parameters()`
  levert alleen geldige codes), `uitleg.py`, `terugkoppeling.py`, `woordvorm.py` (de Nederlandse
  **ij-digraaf**: `.capitalize()` maakt van "ijzer" → "Ijzer"), `runner.py`/`runlog.py`/
  `pijplijn.py`, en `wasstraat/dossier.py` + `toezicht/weergave.py` voor de twee filters.
  **De agents staan in CrewAI-vorm in `config/agents.yaml`**, en dat is het punt en geen
  inrichtingsdetail: in dit lab is de gegevensherkomst zichtbaar en de **bewerking** niet. Drie van
  de zes agents dragen géén `llm`-sleutel — de grens "agents bepalen geen signalen" staat er als
  een *afwezig veld* in plaats van als een belofte in proza, en de runner geeft die agents nooit
  een model door, ook niet als `draai()` er een meekrijgt. **`mag_llm` ≠ gebruik:** die sleutel in
  `/api/wasstraat/pijplijn` meet *gerechtigdheid* (heet daarom niet meer `heeft_llm`); wat er in
  een run werkelijk is aangeroepen staat per stap in de runlog, via een tellende omhulling. De
  configuratiepagina is **read-only** — de reden staat als één zin bij de tabel, geen
  disclaimerblok. CrewAI zelf draait hier aantoonbaar (1.15.41, aarch64, tegen Qwen op `:8080`)
  maar past **niet in deze venv**: het eist `pydantic<2.13` en dit project draait op 2.13.4.
  Telemetrie staat er standaard aan, uit met één van `OTEL_SDK_DISABLED`,
  `CREWAI_DISABLE_TELEMETRY`, `CREWAI_DISABLE_TRACKING`.
  **Vier valkuilen die deze use-case duur heeft betaald**, alle vier gevonden door de **draaiende
  dienst** te bevragen en geen van de vier door code te lezen: (1) **`locatiecode` is géén
  sleutel** — 69 registerregels, 61 distincte codes, en de 8 dubbele dekken twéé verschillende
  vergunningen op dezelfde locatie (Tata Steel: `RWS-2015/19557` met 118 rijen én
  `RWS/DNB-2012/5083` met 12), dus acht vergunningen waren onbereikbaar; de identiteit is nu
  `locatiecode::kenmerk`. (2) **132 van de 782 voorschriften zijn identieke dubbele rijen** (17%) —
  `gebruiksruimte/atlas_register._dedupe()` bestond al met precies die reden in zijn docstring;
  `toezicht` ontdubbelt nu één keer, op de grens waar het register binnenkomt. (3) **grenswaarden
  in verschillende eenheden vergelijken** gaf "factor 35.704.419×" op Warmte (MJ/dag tegen
  MJ/seconde) — regel 4 groepeert nu op `(parameter, eenheid)` en sluit `Zuurgraad` uit, want een
  pH-venster is een correcte vergunning en een pH-verhouding is sowieso betekenisloos; de telling
  ging van 164 naar **114**, en 54% van die oude 164 was artefact. (4) **een bare Aquo-code matcht
  een gewoon Nederlands woord** — `Te` (tellurium) in "vracht niet **te** bepalen" gaf twee
  signalen een tellurium-norm mét bronvermelding. Codes matchen nu hoofdlettergevoelig op
  woordgrens.
  **En de les die boven die vier uitstijgt:** in élke reviewronde van deze use-case kwam iedere
  must-fix uit het **bevragen van de draaiende dienst**, en geen enkele uit het lezen van de diff.
  De ernstige defecten zaten bovendien niet in code die verkeerd rekende, maar in **tests, logs en
  docstrings die beweerden iets te bewaken** — zes keer. Bevraag dus de dienst, en wantrouw een
  groene test die je niet hebt zien falen.
  NB: een afwezige uitleg is zichtbaar als afwezig, mét de reden, en met onderscheid tussen "geen
  bron had iets" en "al eerder gegeven". Deel C (de `.xlsx`) en de bevraagbare laag zijn gebouwd en
  getest maar hebben nog géén route — eerlijk afwezig, niet beweerd. Plannen en beslissingen:
  `docs/superpowers/plans/2026-11-13-toezichtsignalen-agentic-maas.md` en
  `2026-11-14-wasstraat-en-toezicht-splitsen.md`.
- ✅ **Onder water (`/onderwater`, `/api/onderwater`):** de technische anatomie van `/wasstraat`
  en `/toezicht`, als 15e lid van het waterdossier. In dit lab is de gegevens*herkomst* zichtbaar
  en de *bewerking* niet; deze pagina brengt die bij elkaar: de twee pagina's met hun aantallen,
  de tien regels met drempel en wat `omvang` daar betekent, de agents en taken, de
  taalmodelgrens, de vijf bronnen met hun licentiepositie, en de configuratiesleutels.
  **Deze pagina doet beweringen over andere code, en dat is haar risico:** typt zij haar getallen,
  dan gaat zij liegen zodra de code schuift, en de lezer heeft niets anders om dat tegen te
  houden. Alles telbare is daarom afgeleid — regels uit `signalen.REGELS`, drempels uit
  `DREMPELS`, de twee assen uit `Regel.laag` en `is_voorbehoud`, agents en taken uit de YAML die
  de runner zelf leest. `tests/test_onderwater.py` scant de uitlegteksten op losse getallen en
  `tests/test_api_onderwater.py` eist dat géén regel-id en géén agentnaam in de HTML staat.
  **Twee harde grenzen:** geen configuratiesectie dumpen (`core/config.yaml` draagt ook
  `submit_token` en api-headernamen, dus `CONFIGSLEUTELS` is een **witte lijst**), en geen
  absoluut serverpad — paden worden tot hun laatste twee segmenten afgekort, dezelfde regel die
  de eindreview op `/api/wasstraat/pijplijn` oplegde. Een ontbrekende sleutel wordt als
  *ontbrekend* getoond en niet weggelaten: dat laatste zou precies de misconfiguratie verbergen
  die deze pagina hoort te laten zien, en dat is één keer echt gebeurd met `normen_pad`.
  **Bij de twee signaalpagina's horen twee aanvullingen:** op `/wasstraat` klappen de agentrijen
  open (`goal`, `backstory`, tools, taken en de `llm`-regel uit de YAML — die laatste werd tot
  één boolean platgeslagen terwijl zij model, endpoint en "geïnjecteerd door de runner" noemt);
  op `/toezicht` staan de agents die in **déze** run hebben gedraaid, via
  `pijplijn.gedraaide_agents`, dat de **runlog** als bron neemt en niet de configuratie — zes
  agents staan in de YAML, vier draaien, en `vraagsteller`/`terugkoppelaar` hebben geen taak.
  `mag_llm` (mocht) en `llm_aangeroepen` (deed) staan daar náást elkaar; bij Solvay mocht de
  uitlegger wel en deed hij niet. Alle drie gebruiken een `<details>` in plaats van eigen
  klikcode, zodat de rij van zichzelf toetsenbordbereikbaar is.
  **De proza is apart bewaakt** (`tests/test_paginaproza.py`): de twee signaalpagina's schrijven
  hun aantallen uitgeschreven ("Zeven deterministische regels … Vijf daarvan leveren een
  bevinding op"), en dat is precies waar een pagina stil kan gaan liegen — in de eindreview
  tweemaal gebeurd. Elke claim wordt tegen de catalogus gelegd (7 op `/wasstraat`, 3 op
  `/toezicht`). **Let op bij die test:** de HTML moet eerst op **witruimte genormaliseerd**
  worden, want de zinnen zijn op leeslengte afgebroken en zonder dat raakt geen enkel patroon
  iets — de bewaking is dan groen en leeg. Er staat ook een ondergrens op het aantal gevonden
  claims, en de niet-leegheid is met een mutatie op de echte pagina bewezen.
- ✅ **De vraagweg (`POST /api/toezicht/vraag`, chatbox op `/toezicht`):** een vrije vraag over
  de toezichtgraaf — NL → SPARQL → **validatie** → uitvoering, met de uitgevoerde query zichtbaar.
  Vierde toepassing van hetzelfde huisstramien naast `/chatbot` (RAG), `/datavraag` (NL→SPARQL) en
  `/afval` (NL→SQL). De machinerie (`graaf.py`, `vraag.py`) bestond al en getest; wat ontbrak was
  een route — en één inhoudelijk stuk.
  **Dat stuk is de brug: `graaf.bouw` neemt nu ook de signalen op als `t:Signaal`**, met `t:laag`
  (papier/werkelijkheid) en `t:rol` (bevinding/voorbehoud) als de twee assen. Zonder die klasse kon
  de graaf wél zeggen welke grenswaarde aangenomen is, maar niet welke vergunning een open
  wasstraatbevinding heeft — en juist de vraag die over de twee lezers heen loopt heeft waarde.
  Live geverifieerd: *"Welke vergunningen hebben een papierbevinding en ook een
  werkelijkheidssignaal?"* geeft **58 vergunningen** met naam, locatiecode en kenmerk.
  **`context` mag een functie `vestiging -> dict` zijn, en dat is noodzaak geen gemak:**
  `waterlichaam` wordt uit de eigen coördinaat van elke vergunning opgezocht. Eén waterlichaam aan
  het hele register toekennen zou `regel_norm_overschreden_bovenstrooms` laten vuren met een
  richting die voor vrijwel elke vergunning onjuist is.
  **De graaf wordt gecachet (TTL 1 dag), want hij is duur** — niet de triples (~72.000 in 0,5 s)
  maar het waterlichaam per vergunning (~8 s over 62, al parallel in `kmg_service`). Koud duurt
  een vraag ~38 s, warm ~10 s; dat laatste is vrijwel geheel het taalmodel.
  **De route loopt dóór de `vraagsteller`-agent, niet eromheen** (`runner.Crew.los_uitvoeren`).
  Die agent heeft geen taak in `tasks.yaml` — zijn werk is een losse actie — maar de actie gaat
  langs dezelfde drie poorten als een pijplijnstap: de tool komt uit zijn eigen `tools`-lijst, het
  taalmodel door de §4.4-grens, en de stap komt in de runlog met `llm` op **gebruik**. Haal de
  `llm`-sleutel bij `vraagsteller` weg en de vraagweg weigert, in plaats van stil toch een model te
  gebruiken; een test dwingt dat af. Zonder deze omweg deed de route het werk van een agent achter
  zijn rug om en bepaalde `agents.yaml` voor dit pad niets.
  **Dit is de eerste plek bij deze pagina's waar werkelijk een taalmodel draait** — beide
  dossierroutes geven `llm=None` door en blijven dat doen. De pagina zegt dat expliciet, en een
  test bewaakt die zin: anders wordt "geen taalmodel" stil onwaar.
  **Twee dingen die alleen uit het bevragen van de draaiende dienst kwamen:** (1) het model schreef
  een correcte brugvraag maar selecteerde het vestigingsknooppunt, en dat is een **blank node** —
  100 rijen met `Na5f43702f94c…`, onbruikbaar. De naam zat alleen drie stappen diep achter
  `t:heeftVeld` → Bewering → `t:waarde`. `naam`, `locatiecode` en `kenmerk` staan nu óók als
  gewone literal op de vestiging (`IDENTIFICERENDE_VELDEN`), met de Bewering ernaast voor de
  zekerheid; de grounding zegt expliciet die te selecteren. (2) Zonder `DISTINCT` levert een dubbel
  `t:heeftSignaal`-pad het kruisproduct op — 100 rijen over 69 vergunningen — dus de grounding
  schrijft `SELECT DISTINCT` voor bij twee paden. **En de validator bewees zich live:** gevraagd om
  alles te verwijderen schreef het model `DELETE WHERE { ?signaal a t:Signaal }. LIMIT 1000000`,
  en die is geweigerd, zichtbaar als geweigerde query, met nul rijen. De pagina labelt zo'n query
  dan ook als *"Geweigerde query — niet uitgevoerd"* en niet als uitgevoerd.
- ✅ **De graaf wordt opgebouwd en bewaard, niet elke keer opnieuw** (`scripts/22_bouw_toezicht
  graaf.py` → `leefomgevinglab.toezicht.graaf_pad`, Turtle op NVMe, **nooit in de repo**). De
  vraagweg leest dat bestand bij voorkeur en bouwt alleen live als het ontbreekt.
  **De reden is niet snelheid.** Nagemeten: inlezen ~4 s tegen ~9 s live bouwen, op een vraag die
  ~10 s aan het taalmodel besteedt — en de graaf stond al een dag in het geheugen. De winst is
  (a) **herleidbaarheid**: een bestand draagt een datum, dus een antwoord is te herleiden tot een
  versie van het register, en (b) **robuustheid**: live bouwen heeft de Atlas plús een
  coördinaatopzoeking per vergunning nodig, dus zonder bestand ligt de vraagweg eruit zodra de
  Atlas eruit ligt. Gemeten uitkomst: 69 vestigingen, 650 voorschriften, 598 signalen, **72.682
  triples, 2,4 MB**, bouwen in ~14 s.
  **Eén bouwer, twee aanroepers** (`usecases/toezicht/graafbouw.py`). De route bouwde de graaf
  eerst zelf en het script ook — en het script deed het **zonder context**, dus zonder
  `t:Signaal`, dus zonder de brug tussen de twee lezers. Een bestand met die halve graaf is erger
  dan geen bestand, want de route leest het bestand bij voorkeur.
  **⚠️ En de fout die daarna nog opdook, is precies de reden dat hier een live test op staat:**
  het script bouwde op het **rauwe** Atlas-antwoord terwijl de route eerst ontdubbelt
  (`register.voorbereid`, 132 letterlijk herhaalde voorschriften = 17% van 782). Verschil:
  **75.190 tegen 72.682 triples**, 782 tegen 650 voorschriften — en niets viel om. Sinds de fix
  zijn ze gelijk, en `tests/test_toezicht_live.py::test_de_opgebouwde_graaf_op_schijf_is_dezelfde
  _als_de_route_live_bouwt` vergelijkt de telling per klasse (niet de triples zelf: blank-node-
  id's verschillen per bouw).
  **Verouderen mag niet stil.** Een oud bestand wordt wél gebruikt — beter een herleidbaar
  antwoord van vorige week dan geen antwoord — maar `meta["verouderd"]` gaat aan boven
  `graaf_max_ouderdom_dagen` (standaard 7) en de pagina zet er een rode waarschuwing bij mét het
  commando om opnieuw te bouwen. `telling()` rekent **uitsluitend uit de graaf**, nooit uit het
  register ernaast: het pad dat van schijf leest heeft dat register niet, en zou dan een getal
  moeten verzinnen dat niet uit de graaf komt die de vragen beantwoordt.
  Verversen:
  ```bash
  W=/mnt/nvme/geluidsmeter/data/external/wkp
  PYTHONPATH=src .venv/bin/python scripts/22_bouw_toezichtgraaf.py \
      --aquo $W/aquo_Parameter.csv --metingen $W/metingen_2025.json \
      --normen $W/krw_normen.json --doelen $W/krw_doelen_2025.json \
      --gemeten-codes $W/gemeten_codes.json \
      --uit /mnt/nvme/geluidsmeter/data/external/toezicht/toezicht.ttl
  ```
  Zonder `--doelen` en `--gemeten-codes` bouwt het script een graaf zonder de drie
  werkelijkheidssignalen; het script meldt dat luid in plaats van het stil op te leveren.
- ✅ **Het waterdossier op `/onderwater`** (`GET /api/onderwater/waterdossier`): het
  informatiemodel en de kennisgraaf, als eigen secties onder de anatomie van de twee
  signaalpagina's.
  **Het informatiemodel** (`kmg/lozingsmodel.py`, memo op `/watermodel`) wordt gepresenteerd op
  wat het bijzonder maakt: niet welke velden het vastlegt maar dat elk veld een **zekerheid**
  meevoert. `onderwater.VELDEN_ZEKERHEID` geeft per veld de **hoogste zekerheid die het kan
  halen**, met de reden — en twee velden kunnen per bron nooit "uit de bron" zijn: de
  **hoedanigheid** is altijd `aangenomen` (geen parameternaam in het Maasstroomgebied zegt totaal
  of opgelost, en voor zink is dat bepalend) en de **geldigheidsperiode** `ontbreekt` altijd (geen
  begin/einddatum per voorschrift). Een test toetst elke `hoogste_zekerheid` tegen
  `lozingsmodel.ZEKERHEDEN`, zodat hier geen waarde kan staan die het model niet kent; de vier
  zekerheden en alle tellingen komen uit de constanten.
  **"De kennisgraaf" bestaat niet — er zijn twee grafen met een ander doel**, en ze verwisselen
  wekt de verwachting dat je aan de ene kant vragen kunt stellen die alleen aan de andere te
  beantwoorden zijn:
  * **Stoffengraaf** (*referentiegraaf*, `/kennisgraaf`): stof → CAS → Aquo-parameter. Gemeten:
    **38 knopen, 29 randen, 29 met herkomst** — dus élke rand draagt een bron, en dát tilt hem
    boven een tabel uit (een koppeling is te verwerpen in plaats van te geloven). Plus
    somparameters mét hun delen, zodat dubbeltelling te zien is in plaats van te gebeuren.
  * **Toezichtgraaf** (*registergraaf*, `/toezicht`): **73.071 triples, 69 vergunningen, 650
    voorschriften, 598 signalen, 29 overschrijdingen**. Zekerheid hangt aan de bewéring en niet
    aan de rij, en een vraag kan over de twee lezers heen lopen.
  **⚠️ De route bouwt de toezichtgraaf níet.** Alleen als hij al in het geheugen zit gaan zijn
  tellingen mee; anders staat de sectie er met `nog_niet_geteld` en de melding dat een vraag op
  `/toezicht` hem warm maakt. Een uitlegpagina die een graaf van 73.000 triples opbouwt omdat
  iemand haar opent (~9 s live, plus een coördinaatopzoeking per vergunning) is zelf het probleem
  dat zij beschrijft. Om dezelfde reden is dit een **apart eindpunt**: `/api/onderwater` leest
  alleen YAML en constanten en blijft instant, en de pagina laadt deze sectie los bij.
  In een echte browser nagekeken, koud én warm: 4 zekerheidskaartjes, 7 veldrijen, 2 graafkaarten,
  en koud precies één "nog niet geteld".
- **⚠️ Vier valkuilen van de vraagweg, alle vier gevonden doordat de vraag "niet meer werkte"** —
  en geen van de vier door code te lezen. Ze hebben één gemene deler: de lezer kreeg *"Geen
  resultaten voor deze vraag"*, en dat leest als "er is niets aan de hand" in plaats van "de
  vraag is verkeerd gesteld". Dat is het stilste soort fout dat deze laag kan maken.
  1. **`LIMIT` begrenst de uitvoer, niet het werk.** Een geldige query met `LIMIT 100` die
     `t:Meting` tegen `t:Norm` joinde liep in rdflib **119 seconden** voor 21 rijen (350 metingen
     × 6143 normen als nested loop). De pagina deed minutenlang niets en cloudflared geeft het
     eerder op dan rdflib. Daarom: `vraag.QUERY_DEADLINE_S` (20 s) met een **eigen** boodschap —
     "kon niet worden uitgevoerd" zou suggereren dat de query fout was, terwijl zij goed was en
     alleen te zwaar. NB: die deadline begrenst de *wachttijd*, niet het werk; rdflib kent geen
     afbreekpunt, dus de thread rekent in de achtergrond door (daemon). Een procesgrens zou het
     werk écht afkappen en staat genoteerd in plaats van half gebouwd.
  2. **Die join hoort niet in de query.** De vergelijking is al gemaakt door `kmg.doelen` +
     `toezicht.context.toetsing`, mét de juiste sleutel (**meetpunt én stof** — een KRW-norm geldt
     per meetpunt, zink is per punt gecorrigeerd voor biobeschikbaarheid). Zij staat nu als
     `t:Overschrijding` in de graaf: 119 s → **0,25 s**. Een query die zelf joint gaat ook
     makkelijk mis op de sleutel.
  3. **Niets verbond een vergunning met een meting.** Het model schreef
     `?vestiging t:heeftMeting ?meting` — een predicaat dat niet bestaat — en had geen
     alternatief: de vraag "papierbevinding **én** een meting boven de norm" was niet uit te
     drukken. De schakel is het waterlichaam; dat staat nu óók als gewone literal op de
     `t:Vestiging` (het wordt per vergunning uit haar coördinaat afgeleid, de Atlas levert het
     nooit). Meegekomen correctie: de Bewering zei voor álle 69 `zekerheid "ontbreekt"` terwijl
     de route het wél wist — nu `"afgeleid"`, met de oude tegenspraak weg.
  4. **Afwezigheid is in deze graaf een positief feit.** Op "welke vergunningen missen een
     kenmerk" schreef het model `FILTER(!BOUND(?kenmerk))` op een variabele die een triple
     pattern al bond: per definitie leeg. Het juiste pad is de Bewering met
     `t:zekerheid "ontbreekt"` (of `FILTER NOT EXISTS`), en dat staat nu in de grounding.
  **De grounding draagt daarom vier uitgewerkte vraag-naar-query-paren** (`vraag.VOORBEELDEN`),
  en die zijn **uitvoerbare documentatie**: een test valideert elke query en een live test voert
  ze uit op de echte graaf en **eist rijen**. Een voorbeeld dat niets oplevert valt dus om in de
  suite in plaats van stil een verkeerd patroon te onderwijzen. Gemeten na de fixes: 61 / 3 / 31 /
  100 rijen, elk onder 1,4 s aan querytijd; de 11–30 s die een vraag kost is vrijwel geheel het
  lokale taalmodel. **En `Crew.los_uitvoeren` meet nu de duur** — hij gaf geen `duur` aan
  `runlog.stap`, dus de runlog meldde `0 s` voor een stap van 25 s. Een runlog die een duur
  rapporteert zonder hem te meten liegt met een getal, op een pagina die meten als belofte voert.
- **`.env` wordt in `tests/conftest.py` geladen, niet per ongeluk.** De live-tests lezen hun
  sleutel rechtstreeks uit `os.environ`, en die stond daar tot 2026-11-15 alleen omdat
  `geluidsmeter/api.py` bij import `load_dotenv()` aanroept en bijna elk testbestand `api`
  importeert — een **zijeffect van de collectievolgorde**. `pytest --run-live
  tests/test_dso_live.py` alleen faalde daardoor met `KeyError: 'DSO_API_KEY'` terwijl die
  sleutel in `.env` staat, terwijl een volledige run slaagde. De gate zelf blijft losgekoppeld
  van elke omgevingsvariabele en hangt uitsluitend aan `--run-live`; een standaardrun skipt 31
  tests. Alle vijf de `*_live.py`-bestanden slagen nu ook los gedraaid.
- **Valkuilen bij de waterbronnen:** het geometrieattribuut heet bij de RWS KRW-service `shape` en bij PDOK bestuurlijke gebieden `geom`; die laatste **negeert `cql_filter`** — gebruik een bbox. `owl_naam` is in alle 54 KRW-vlakken leeg, de naam staat in `naam`. **`gemdiepte` is in alle 54 vlakken én 35 lijnen exact `-9999`** (geverifieerd 2026-09-23) — nooit een echte meting, dus `waterprofiel.profiel()` filtert die sentinel naar `None`. Waterschapsgrenzen zijn alléén als WMS en atom-download ontsloten, niet als WFS. `owlcat` kent live vijf waarden, niet vier: naast rivier/meer/kust/overgangswater bestaat categorie 5 (territoriaal water: Eems/Maas/Rijn/Schelde, watertype K0). Wat vandaag niet bestaat staat als `nieuw`/`wijzigt` gemarkeerd: STOP/TPOD kent géén toepassingsprofiel voor een vergunningbesluit, het REV wordt nu via een eigen IMEV-aanleverketen gevuld, en Data.OD is nog een initiatief van DCMR + OD De Vallei.

---

## Eerste run (Sprint 1)

```bash
# NVMe dirs (eenmalig, jij doet dit met sudo)
sudo mkdir -p /mnt/nvme/geluidsmeter/data/{raw_features,processed,external/{atlas,cvgg,pdok_3d_geluid},catalog}
sudo chown -R bob:bob /mnt/nvme/geluidsmeter

# Venv
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

# Eerste test (5s, geen opslaan)
python3 scripts/01_record_features.py --duration 5 --dry-run
```

---

## Poorten (context orin3)

| Dienst | Poort |
|---|---|
| **LeefomgevingLab API** | **8792** |
| **LeefomgevingLab embeddings (bge-m3)** | **8082** |
| felix-nazaten upload | 8791 (bezet) |
| Derwisch transcriptie | 8790 |
| Derwisch backend | 8789 (**https**, self-signed) |
| morele-helper admin | 8788 |
| waterlab dashboard | 8000 |
| sysmonitor status | 8795 |
| Derwisch LLM Qwen | 8080 |
| ~~Derwisch LLM Nemo~~ | ~~8081~~ — unit is disabled, er draait niets |
