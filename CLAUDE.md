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
- 🚧 **Doelbeeld D-VTH (`/dvth`, `/api/dvth/architectuur`):** doelarchitectuur voor één MBA Seveso-inrichting — DSO-loket → zaaksysteem OD → Data.OD → analyse/beoordeling → besluit als STOP/TPOD met uit IMEV afgeleid objectmodel → omgebouwd REV → GIR/LBR → LHSO, met CIM-VTH-Flo als informatiemodel. Interactieve architectuurplaat (17 componenten, 17 koppelvlakken), de keten in 8 stappen en een roadmap van 23 features. Data in `usecases/dvth.py`. **Het ketentje draait**: `GET /api/dvth/keten?live=1&straal=1000` doorloopt alle 8 stappen in ~1,4 s, met live bevraging van REV-WFS (DWITHIN) en BAG (bbox) op het RD-punt in stap 3; `live=0` slaat dat over en is reproduceerbaar. Code in `usecases/dvth_keten/` (casus, cim, bronnen, tpod, lbr, lhso, stappen, motor). Straal begrensd op 5000 m.
- 🚧 **Doelbeeld directe lozing (`/lozing`, `/api/lozing/{architectuur,keten}`):** spiegeldossier van D-VTH — één lozingsactiviteit op een rijkswater (IJssel bij Deventer), RWS namens de minister als bevoegd gezag. Kern: de **knip** (gemeente doet de MBA, waterbeheerder de lozing, geen koppelvlak ertussen), ABM + immissietoets i.p.v. afstandscirkels, **Aquo** i.p.v. IMEV als annotatiebron, en een **Register Lozingen dat niet bestaat**. Stap 2/3 leiden het bevoegd gezag **live** af: een treffer in de KRW-service van RWS (89 rijkswaterlichamen) betekent rijkswater → minister; PDOK bestuurlijke gebieden geeft de gemeente. Code: `usecases/lozing.py` + `usecases/lozing_keten/`.
- **Gedeelde ketenkern** (`usecases/ketenkern/`): `cim` (objectbibliotheek met validatie tegen het CIM), `lhso` (interventiematrix), `wfs` (WFS-helpers met retries) en `motor` (dossier-onafhankelijk; een dossier levert DOSSIER/CASUS/STAPPEN/ANNOTATIES). Beide tabs draaien op **één sjabloon** `static/keten-tab.html`; de route vervangt `__DOSSIER__` en alle teksten komen uit `PRESENTATIE` in het architectuurmodule. Een derde dossier kost daarmee alleen een architectuur- en een ketenmodule.
- ✅ **BALO-redeneerlijnen (`/balo`, `/api/balo/overzicht`):** beide doelbeeld-casussen geplot op het redeneermodel van de BALO-businessarchitectuur v0.9 (concept, RWS/WVL). Per ketenstap links **redeneerlijn 2** (waardestroom W1–W8 → informatiebehoefte → informatiefuncties uit de gesloten set van 9) en rechts **redeneerlijn 3** (informatieobjecten → registers, met status bestaat/moet om/bestaat niet). Plus de gedeelde knelpunten (stappen waar béíde ketens vastlopen), een besluitenkwadrant kosten × waarde met 7 besluiten, en de vijf vragen die BALO zelf aan management stelt. Kern van de pagina is de **informatiebehoefte als spil**: 16 behoeften (één per ketenstap), elk met eigenaar, waarde-als-het-lukt, kosten-als-het-niet-lukt en status (voldaan/deels/niet). Analysefuncties `behoeften()`, `cyclus()`, `waardeoverzicht()`, `besluitwaarde()` en `onbediend()`. Uitkomst: 2 voldaan / 6 deels / 8 niet; 5 van 8 waardestromen geraakt (W1, W3, W8 niet); W5 is het zwartste gat met 5 onvervulde behoeften. De waarde van een besluit is niet beweerd maar afgeleid uit de behoeften die het bedient — een test dwingt af dat waarde=hoog ≥2 behoeften betekent. Data in `usecases/balo.py`. NB: structuur en begrippen komen uit het document, de koppeling aan de casussen en de kosten-batenafweging zijn van dit lab — dat onderscheid staat ook op de pagina.
- ✅ **Gebruiksruimte (`/gebruiksruimte`, `/api/gebruiksruimte?locatie=&debiet=&live=`):** 'wat kan hier nog?' voor een lozing op de IJssel. Combineert (a) **regels op de locatie live uit het DSO** (Ozon `regelingen_op_punt`, ~20 per punt) geclassificeerd naar **direct werkend / indirect werkend / geldt hier maar raakt dit voornemen niet** — dat laatste is de waterschapsverordening op rijkswater; (b) een **synthetisch register** met 5 bestaande lozingsvergunningen op hetzelfde waterlichaam; (c) de rekensom ruimte-tot-de-norm per parameter. Drie locaties (Brummen/Deventer/Doesburg, 2 provincies) aan hetzelfde KRW-waterlichaam: de regels verschillen per locatie, de gebruiksruimte is gedeeld. Code: `usecases/gebruiksruimte/` (gebied, regels, ruimte, service). NB: de vergunde vracht zit al ín de achtergrondconcentratie en wordt dus **niet** van de ruimte afgetrokken — hij staat apart om te tonen hoeveel van de belasting in menselijke hand is. PFOA heeft per opzet géén ruimte (achtergrond > norm); stikstof kantelt om bij ~20.000 m³/u. Getallen illustratief, mechanisme echt.
- ✅ **EV-gebruiksruimte (`/evruimte`, `/api/evruimte?locatie=&live=`):** ruimtelijke tegenhanger van `/gebruiksruimte`, als **maplibre-kaart**. De drie aandachtsgebieden van een voorgenomen Seveso-inrichting (gifwolk 1500 m, brand 90 m, explosie 60 m) over de **bestaande REV-aandachtsgebieden** (live als GeoJSON), met de verblijfsobjecten eronder **live geteld in de BAG per gebruiksdoel** en ingedeeld naar zeer kwetsbaar / kwetsbaar / beperkt kwetsbaar. Vijf locaties: Europoort (ruim), Botlek en Gouda (vol), Zutphen, plus een illustratieve plek pal naast een school waar de harde grens wél optreedt. Code: `usecases/evruimte/`. **Cruciaal: PDOK negeert `cql_filter` volledig** (BAG én bestuurlijke gebieden) — een DWITHIN in CQL geeft stilzwijgend de héle dataset terug. Gebruik de standaard **FES-filter via POST** (`filter=<fes:Filter>` met `DWithin` + `PropertyIsLike` op `gebruiksdoel`); de REV-GeoServer accepteert `cql_filter` juist wél. BAG-tellingen draaien parallel (ThreadPoolExecutor, 8 workers): 13 s → 4-6 s.
- **Valkuilen bij de waterbronnen:** het geometrieattribuut heet bij de RWS KRW-service `shape` en bij PDOK bestuurlijke gebieden `geom`; die laatste **negeert `cql_filter`** — gebruik een bbox. `owl_naam` is in alle 54 KRW-vlakken leeg, de naam staat in `naam`. Waterschapsgrenzen zijn alléén als WMS en atom-download ontsloten, niet als WFS. Wat vandaag niet bestaat staat als `nieuw`/`wijzigt` gemarkeerd: STOP/TPOD kent géén toepassingsprofiel voor een vergunningbesluit, het REV wordt nu via een eigen IMEV-aanleverketen gevuld, en Data.OD is nog een initiatief van DCMR + OD De Vallei.

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
