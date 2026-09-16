# Waterdossier-hub & prik-op-de-kaart — Implementatieplan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Het verspreide lozingsverhaal bundelen tot één waterdossier met gedeelde subnavigatie, en "wat kan hier nog" beschikbaar maken op een willekeurig punt in Nederland — met echte lozingsvergunningen uit de Atlas voor een Schone Maas waar die bestaan.

**Architecture:** Drie lagen. (1) `water_hub.py` beschrijft het dossier en genereert de subnav; de statische pagina's krijgen die via een `__WATERNAV__`-placeholder, zoals `_keten_tab()` nu `__DOSSIER__` vervangt. (2) `waterprofiel.py` maakt van een KRW-feature een waterlichaamprofiel met een harde scheiding tussen echt en afgeleid; `smwk_atlas.py` + `atlas_register.py` halen echte vergunningen op en rekenen ze om naar vrachten. (3) `service.beeld_op_punt()` wordt de motor onder zowel het bestaande `/gebruiksruimte` als het nieuwe `/waterruimte`.

**Tech Stack:** Python 3.10, FastAPI, httpx, pytest, maplibre-gl 4.7.1, ArcGIS FeatureServer REST, OGC WFS 2.0.

**Spec:** `docs/superpowers/specs/2026-09-16-waterdossier-hub-prikkaart-design.md`

## Global Constraints

- **Taal:** alle code, commentaar, docstrings, commit-berichten en UI-teksten in het **Nederlands**. Dat is de bestaande conventie in deze repo.
- **Testen draaien met:** `cd /mnt/nvme/workspaces/LeefomgevingLab && .venv/bin/python -m pytest` — `tests/conftest.py` zet `src/` op het pad.
- **Geen netwerk in gewone tests.** Elke bron wordt geïnjecteerd via een `_haal`- of `haal`-parameter, zoals `regels.regels_op_locatie(_haal=…)` en `bronnen.contextset(haal=…)` dat al doen. Live-tests staan in aparte `*_live.py`-bestanden.
- **Bron van waarheid voor de Atlas** (geverifieerd 2026-09-16):
  - Vestigingen: `https://services-eu1.arcgis.com/S0XTphM6W3v0bENW/arcgis/rest/services/Vestigingen_Vergunningen_Uniek/FeatureServer/0`
  - Voorschriften: `…/FeatureServer/2` (`VergunningenTabel`)
  - Ruimtelijke query op RD: `inSR=28992`, `geometryType=esriGeometryPoint`, `distance=…`, `units=esriSRUnit_Meter`, `spatialRel=esriSpatialRelIntersects`
- **Licentie Atlas:** `access: public`, géén `licenseInfo`. Altijd live bevragen met bronvermelding + link; **nooit** de dataset in de repo opnemen.
- **KRW-service:** `https://geo.rijkswaterstaat.nl/services/ogc/gdr/kaderrichtlijn_water/ows`, geometrieattribuut heet `shape` (niet `geom`).
- **PDOK bestuurlijke gebieden negeert `cql_filter`** — altijd bbox gebruiken. Zie `bronnen.py`.
- **Commit-trailer:** elke commit eindigt met `Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>`.
- **Niet pushen.** Committen mag zelfstandig; `git push` is altijd een expliciete vraag van Bob.

---

## Bestandsoverzicht

| Bestand | Verantwoordelijkheid | Taak |
|---|---|---|
| `src/leefomgevinglab/usecases/water_hub.py` | Wat het waterdossier is: leden, lijnen, dekking, subnav-HTML | 1 |
| `src/leefomgevinglab/static/water.html` | Landingspagina van het dossier | 2 |
| `src/leefomgevinglab/usecases/lozing_keten/bronnen.py` | *(wijzig)* extra KRW-velden, `wbhnaam` als bevoegd gezag | 4 |
| `src/leefomgevinglab/usecases/gebruiksruimte/waterprofiel.py` | KRW-feature → waterlichaamprofiel, echt/afgeleid gescheiden | 5 |
| `src/leefomgevinglab/connectors/smwk_atlas.py` | Atlas bevragen: vestigingen + voorschriften bij een punt | 6 |
| `src/leefomgevinglab/usecases/gebruiksruimte/atlas_register.py` | Atlas-voorschriften → registerposten met vrachten in kg/jaar | 7 |
| `src/leefomgevinglab/usecases/gebruiksruimte/ruimte.py` | *(wijzig)* accepteer voorberekende vrachten | 7 |
| `src/leefomgevinglab/usecases/gebruiksruimte/service.py` | *(wijzig)* `beeld_op_punt()` als motor, `beeld()` als wrapper | 8 |
| `src/leefomgevinglab/static/waterruimte.html` | Prik-op-de-kaart, maplibre | 10 |
| `src/leefomgevinglab/geluidsmeter/api.py` | *(wijzig)* routes + `_waterpagina()` | 2, 3, 9 |

**Afwijking van de spec, bewust:** de spec plaatste de parameter-crosswalk in `waterprofiel.py`. In dit plan zit hij in `atlas_register.py`, samen met de vrachtafleiding. Reden: beide gaan over "hoe vertaal ik een Atlas-voorschrift naar een registerpost"; `waterprofiel.py` gaat over het water zelf. Eén verantwoordelijkheid per bestand.

---

### Task 1: De hub beschrijft zichzelf

**Files:**
- Create: `src/leefomgevinglab/usecases/water_hub.py`
- Test: `tests/test_water_hub.py`

**Interfaces:**
- Consumes: niets
- Produces: `LEDEN: list[dict]`, `LIJNEN: list[dict]`, `lid(id: str) -> dict`, `dekking() -> list[dict]`, `subnav_html(actief: str | None) -> str`, `overzicht() -> dict`

- [ ] **Step 1: Schrijf de falende test**

Maak `tests/test_water_hub.py`:

```python
import re

from leefomgevinglab.usecases import water_hub as wh


def test_elk_lid_heeft_een_pad_een_label_en_een_verantwoording():
    assert len(wh.LEDEN) == 5
    for l in wh.LEDEN:
        assert l["pad"].startswith("/")
        assert l["label"] and l["titel"] and l["samenvatting"]
        # het paar dat afdwingt dat elke waterpagina zich verantwoordt
        assert isinstance(l["live"], list) and isinstance(l["synthetisch"], list)


def test_lid_ids_zijn_uniek_en_opzoekbaar():
    ids = [l["id"] for l in wh.LEDEN]
    assert len(ids) == len(set(ids))
    assert wh.lid("kaart")["pad"] == "/waterruimte"


def test_de_drie_lijnen_lopen_door_het_hele_dossier():
    assert len(wh.LIJNEN) == 3
    for lijn in wh.LIJNEN:
        assert lijn["kop"] and lijn["tekst"]
        assert lijn["leden"], "een lijn zonder leden is geen doorsnijdende lijn"
        for lid_id in lijn["leden"]:
            assert wh.lid(lid_id), f"onbekend lid: {lid_id}"


def test_dekking_geeft_per_lijn_de_leden_die_hem_raken():
    d = wh.dekking()
    assert len(d) == 3
    for rij in d:
        assert rij["lijn"] and rij["leden"]
        assert len(rij["leden"]) >= 2, "een lijn die maar één pagina raakt is geen rode draad"


def test_subnav_markeert_precies_een_actief_item():
    html = wh.subnav_html("ruimte")
    assert html.count('aria-current="page"') == 1
    assert '/gebruiksruimte' in html
    for l in wh.LEDEN:
        assert l["pad"] in html, f"{l['pad']} ontbreekt in de subnav"


def test_subnav_zonder_actief_item_markeert_niets():
    assert wh.subnav_html(None).count('aria-current="page"') == 0


def test_subnav_ontsnapt_geen_html_uit_de_labels():
    """De labels zijn van ons, maar de balk mag geen ruwe < of > doorlaten."""
    html = wh.subnav_html("keten")
    assert "<script" not in html.lower()
    assert re.search(r'<nav[^>]*class="waternav"', html)


def test_overzicht_levert_alles_wat_de_pagina_nodig_heeft():
    o = wh.overzicht()
    assert o["leden"] == wh.LEDEN
    assert o["lijnen"] == wh.LIJNEN
    assert o["dekking"] == wh.dekking()
    assert "atlas" in o and o["atlas"]["url"].startswith("https://")
    assert o["atlas"]["licentie"], "de licentiepositie hoort expliciet op de pagina"
```

- [ ] **Step 2: Draai de test en zie hem falen**

Run: `.venv/bin/python -m pytest tests/test_water_hub.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'leefomgevinglab.usecases.water_hub'`

- [ ] **Step 3: Schrijf de minimale implementatie**

Maak `src/leefomgevinglab/usecases/water_hub.py`:

```python
"""Het waterdossier: welke pagina's er bij horen, en wat ze delen.

Het lozingsverhaal stond verspreid over vier tabs die elkaar nauwelijks kenden — elke pagina
had een eigen handgeschreven nav met een willekeurige greep uit de andere. Deze module is de
enige plek waar staat wat het dossier is; de subnavigatie wordt eruit gegenereerd.

Per lid staat expliciet wat er live wordt opgehaald en wat synthetisch is. Dat paar dwingt af
dat elke waterpagina zich op één plek verantwoordt.
"""
from html import escape

LEDEN = [
    {"id": "overzicht", "pad": "/water", "label": "Overzicht",
     "titel": "Het dossier in één beeld",
     "samenvatting": "Wat er speelt bij één directe lozing op een rijkswater, en waar in dit lab "
                     "je elk stuk daarvan terugvindt.",
     "live": [], "synthetisch": []},
    {"id": "keten", "pad": "/lozing", "label": "Keten",
     "titel": "Doelbeeld: de keten in 8 stappen",
     "samenvatting": "Van aanvraag via het DSO-loket tot handhaving volgens de LHSO, met de knip "
                     "tussen twee bevoegde gezagen en het register dat niet bestaat.",
     "live": ["REV-WFS", "RWS KRW-service", "PDOK bestuurlijke gebieden"],
     "synthetisch": ["het bedrijf", "Register Lozingen"]},
    {"id": "ruimte", "pad": "/gebruiksruimte", "label": "Ruimte",
     "titel": "Wat kan hier nog? — drie locaties aan de IJssel",
     "samenvatting": "Drie gemeenten, twee provincies, één waterlichaam: de regels verschillen per "
                     "locatie, de gebruiksruimte is gedeeld.",
     "live": ["DSO Ozon (regelingen op punt)", "RWS KRW-service"],
     "synthetisch": ["vergunningregister", "normen", "achtergrondconcentraties"]},
    {"id": "kaart", "pad": "/waterruimte", "label": "Kaart",
     "titel": "Wat kan hier nog? — prik op de kaart",
     "samenvatting": "Dezelfde vraag op een willekeurig punt. Op de Maas met echte vergunningen "
                     "uit de Atlas voor een Schone Maas, elders met een synthetisch register.",
     "live": ["DSO Ozon", "RWS KRW-service", "PDOK bestuurlijke gebieden",
              "Atlas voor een Schone Maas"],
     "synthetisch": ["normen", "achtergrondconcentraties", "debiet per waterlichaam"]},
    {"id": "knelpunten", "pad": "/balo", "label": "Knelpunten",
     "titel": "Waar de keten vastloopt",
     "samenvatting": "Beide doelbeeld-casussen langs de BALO-redeneerlijnen: 16 informatiebehoeften, "
                     "waarvan 8 onvervuld.",
     "live": [], "synthetisch": ["de koppeling van BALO aan deze casussen"]},
]

LIJNEN = [
    {"id": "knip", "kop": "De knip",
     "tekst": "Twee bevoegde gezagen over één fabriek: de lozingsactiviteit gaat naar de "
              "waterbeheerder, het milieudeel blijft bij de gemeente. Er is geen koppelvlak dat "
              "afdwingt dat beide besluiten op elkaar aansluiten, terwijl een emissiebeperking in "
              "het ene spoor de vracht in het andere verandert.",
     "leden": ["keten", "ruimte", "kaart", "knelpunten"]},
    {"id": "register", "kop": "Het register dat niet bestaat",
     "tekst": "Er is geen landelijk beeld van wie wat waar loost, en dus geen optelsom per "
              "waterlichaam. Voor het Maasstroomgebied is er wél een regionaal initiatief — de "
              "Atlas voor een Schone Maas — en juist het contrast met de rest van Nederland laat "
              "zien wat een landelijk register zou opleveren.",
     "leden": ["keten", "ruimte", "kaart", "knelpunten"]},
    {"id": "stroomafwaarts", "kop": "Het effect ligt stroomafwaarts",
     "tekst": "Een lozing is geen contour om een punt. Hij werkt door in een watersysteem en telt "
              "op bij alles wat verder stroomopwaarts al geloosd wordt. Het CIM-VTH-Flo kent geen "
              "relatie tussen een lozing en het water dat hem ontvangt.",
     "leden": ["keten", "ruimte", "kaart"]},
]

ATLAS = {
    "naam": "Atlas voor een Schone Maas",
    "url": "https://atlas-smwk.hub.arcgis.com/",
    "houder": "Schone Maaswaterketen — waterschappen Aa en Maas, Brabantse Delta, De Dommel en "
              "Limburg, met Rijkswaterstaat en de drinkwaterbedrijven",
    "wat_er_al_is": [
        "72 vestigingen met een directe lozingsvergunning, als punt op de kaart",
        "782 vergunde voorschriften over 68 parameters, met kenmerk en besluitdatum",
        "meetgegevens van 38 stoffen, vier keer per jaar sinds 2023",
    ],
    "wat_dit_lab_toevoegt": [
        "de optelsom: vergunde vrachten bij elkaar, afgezet tegen de norm van het waterlichaam",
        "de regels op de plek, live uit het DSO, met onderscheid direct/indirect werkend",
        "de vraag vooruit: niet wat er vergund is, maar wat er nog bij kan",
        "het bevoegd gezag op een willekeurig punt, ook waar nog niets ligt",
    ],
    "licentie": "De lagen staan publiek open maar dragen geen expliciete licentie. Dit lab "
                "bevraagt ze live met bronvermelding en neemt geen kopie van de dataset op.",
}


def lid(id: str) -> dict:
    """Het lid met dit id; KeyError als het niet bestaat — luid falen."""
    for l in LEDEN:
        if l["id"] == id:
            return l
    raise KeyError(id)


def dekking() -> list[dict]:
    """Per lijn de leden die hem raken, met hun labels — voor de matrix op de landingspagina."""
    return [{"lijn": lijn["kop"], "id": lijn["id"],
             "leden": [{"id": i, "label": lid(i)["label"], "pad": lid(i)["pad"]}
                       for i in lijn["leden"]]}
            for lijn in LIJNEN]


def subnav_html(actief: str | None) -> str:
    """De balk die op elke waterpagina terugkomt. Eén bron, dus overal dezelfde."""
    items = []
    for l in LEDEN:
        huidig = ' aria-current="page"' if l["id"] == actief else ""
        items.append(f'<a href="{escape(l["pad"])}"{huidig}>{escape(l["label"])}</a>')
    return ('<nav class="waternav" aria-label="Waterdossier">'
            '<span class="waternav-kop">Waterdossier</span>' + "".join(items) + "</nav>")


def overzicht() -> dict:
    return {"leden": LEDEN, "lijnen": LIJNEN, "dekking": dekking(), "atlas": ATLAS}
```

- [ ] **Step 4: Draai de test en zie hem slagen**

Run: `.venv/bin/python -m pytest tests/test_water_hub.py -v`
Expected: PASS — 8 passed

- [ ] **Step 5: Commit**

```bash
git add src/leefomgevinglab/usecases/water_hub.py tests/test_water_hub.py
git commit -m "feat(llab): water_hub beschrijft het dossier en genereert de subnav

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>"
```

---

### Task 2: De landingspagina `/water`

**Files:**
- Create: `src/leefomgevinglab/static/water.html`
- Modify: `src/leefomgevinglab/geluidsmeter/api.py` (routes toevoegen na `api_balo_overzicht`, rond regel 320)
- Test: `tests/test_api_water.py`

**Interfaces:**
- Consumes: `water_hub.overzicht()`, `water_hub.subnav_html()` uit Task 1
- Produces: route `GET /water`, route `GET /api/water/hub`, helper `_waterpagina(bestand: str, actief: str) -> str` in `api.py`

- [ ] **Step 1: Schrijf de falende test**

Maak `tests/test_api_water.py`:

```python
from fastapi.testclient import TestClient

import leefomgevinglab.geluidsmeter.api as api
from leefomgevinglab.usecases import water_hub as wh


def _client(monkeypatch):
    monkeypatch.setattr(api, "load_config", lambda *a, **k: api._config)
    return TestClient(api.app)


def test_hub_api_geeft_leden_lijnen_en_dekking(monkeypatch):
    d = _client(monkeypatch).get("/api/water/hub").json()
    assert len(d["leden"]) == len(wh.LEDEN)
    assert len(d["lijnen"]) == 3
    assert d["dekking"]
    assert d["atlas"]["url"].startswith("https://")


def test_waterpagina_geeft_200_en_haalt_de_hub_op(monkeypatch):
    r = _client(monkeypatch).get("/water")
    assert r.status_code == 200
    assert "/api/water/hub" in r.text


def test_waterpagina_bevat_de_subnav_met_actief_overzicht(monkeypatch):
    r = _client(monkeypatch).get("/water")
    assert 'class="waternav"' in r.text
    assert r.text.count('aria-current="page"') == 1
    assert "__WATERNAV__" not in r.text, "placeholder is niet vervangen"
```

- [ ] **Step 2: Draai de test en zie hem falen**

Run: `.venv/bin/python -m pytest tests/test_api_water.py -v`
Expected: FAIL — alle drie met 404 (routes bestaan nog niet)

- [ ] **Step 3: Voeg de routes toe**

In `src/leefomgevinglab/geluidsmeter/api.py`, bij de overige imports (rond regel 40):

```python
from leefomgevinglab.usecases import water_hub as water_hub_mod
```

Direct ná de functie `api_balo_overzicht` (rond regel 320):

```python
def _waterpagina(bestand: str, actief: str | None) -> str:
    """Een waterpagina met de gedeelde subnav erin; zelfde truc als _keten_tab."""
    html = (Path(__file__).parent.parent / "static" / bestand).read_text()
    return html.replace("__WATERNAV__", water_hub_mod.subnav_html(actief))


@app.get("/water", response_class=HTMLResponse)
def water_page():
    """Het waterdossier: één ingang voor wat over vier tabs verspreid stond."""
    return _waterpagina("water.html", "overzicht")


@app.get("/api/water/hub")
def api_water_hub():
    return water_hub_mod.overzicht()
```

- [ ] **Step 4: Schrijf de landingspagina**

Maak `src/leefomgevinglab/static/water.html`. Neem de `<style>` uit `static/balo.html` als basis (zelfde donkere thema, `--border`, `--dim`) en vul aan met de subnav-stijl:

```html
<!DOCTYPE html>
<html lang="nl">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>Waterdossier — LeefomgevingLab</title>
  <style>
    :root { --bg:#0a1420; --paneel:#0d1b2a; --border:#1a3a5c; --dim:#8fa3b8;
            --tekst:#e0e6ed; --accent:#2ecc8f; }
    * { box-sizing:border-box; }
    body { margin:0; background:var(--bg); color:var(--tekst);
           font:15px/1.6 system-ui,-apple-system,"Segoe UI",sans-serif; }
    header { display:flex; align-items:center; gap:12px; flex-wrap:wrap;
             padding:14px 20px; border-bottom:1px solid var(--border); }
    header h1 { font-size:16px; margin:0; font-weight:600; }
    .mark { width:10px; height:10px; border-radius:50%; background:var(--accent); }
    .badge { font-size:11px; color:var(--dim); border:1px solid var(--border);
             border-radius:10px; padding:2px 8px; }
    header nav { margin-left:auto; display:flex; gap:14px; flex-wrap:wrap; }
    header nav a { color:var(--dim); text-decoration:none; font-size:13px; }
    header nav a:hover { color:var(--tekst); }

    .waternav { display:flex; gap:4px; align-items:center; flex-wrap:wrap;
                padding:10px 20px; background:var(--paneel);
                border-bottom:1px solid var(--border); }
    .waternav-kop { font-size:11px; letter-spacing:.08em; text-transform:uppercase;
                    color:var(--dim); margin-right:10px; }
    .waternav a { color:var(--dim); text-decoration:none; font-size:13px;
                  padding:5px 11px; border-radius:6px; }
    .waternav a:hover { color:var(--tekst); background:#12283f; }
    .waternav a[aria-current="page"] { color:var(--bg); background:var(--accent);
                                       font-weight:600; }

    .wrap { max-width:1040px; margin:0 auto; padding:28px 20px 60px; }
    .hero h2 { font-size:28px; margin:0 0 12px; font-weight:650; }
    .hero h2 span { color:var(--accent); }
    .hero p { max-width:760px; color:#c2cedb; }
    h3 { font-size:17px; margin:34px 0 14px; }
    .rooster { display:grid; gap:14px; grid-template-columns:repeat(auto-fit,minmax(260px,1fr)); }
    .kaart { display:block; text-decoration:none; color:inherit; background:var(--paneel);
             border:1px solid var(--border); border-radius:10px; padding:16px; }
    .kaart:hover { border-color:var(--accent); }
    .kaart h4 { margin:0 0 6px; font-size:15px; }
    .kaart p { margin:0 0 10px; font-size:13px; color:#c2cedb; }
    .tags { display:flex; gap:6px; flex-wrap:wrap; }
    .tag { font-size:10.5px; padding:2px 7px; border-radius:9px; border:1px solid var(--border);
           color:var(--dim); }
    .tag.live { color:var(--accent); border-color:#1d5c43; }
    .tag.syn { color:#e8b84b; border-color:#5c4a1d; }
    .lijn { background:var(--paneel); border:1px solid var(--border); border-radius:10px;
            padding:16px; margin-bottom:12px; }
    .lijn h4 { margin:0 0 6px; font-size:15px; color:var(--accent); }
    .lijn p { margin:0 0 10px; font-size:13.5px; color:#c2cedb; }
    .lijn a { color:var(--dim); font-size:12px; text-decoration:none; border:1px solid var(--border);
              border-radius:6px; padding:3px 9px; margin-right:6px; }
    .lijn a:hover { color:var(--tekst); border-color:var(--accent); }
    .atlas { background:var(--paneel); border:1px solid var(--border); border-radius:10px;
             padding:18px; }
    .atlas-kol { display:grid; gap:18px; grid-template-columns:1fr 1fr; }
    .atlas ul { margin:6px 0 0; padding-left:18px; font-size:13px; color:#c2cedb; }
    .atlas .licentie { margin-top:14px; font-size:12px; color:var(--dim);
                       border-top:1px solid var(--border); padding-top:12px; }
    @media (max-width:760px) { .atlas-kol { grid-template-columns:1fr; } }
  </style>
</head>
<body>
  <header>
    <div class="mark"></div><h1>LeefomgevingLab</h1><span class="badge">waterdossier</span>
    <nav><a href="/">Home</a><a href="/dvth">Doelbeeld D-VTH</a><a href="/vth">VTH-kapstok</a></nav>
  </header>
  __WATERNAV__

  <div class="wrap">
    <div class="hero">
      <h2>Eén lozing, <span>vier vragen</span></h2>
      <p>Een bedrijf wil koel- en proceswater rechtstreeks op een rijkswater lozen. Die ene
        handeling roept vier vragen op die in dit lab elk hun eigen pagina hebben — wie gaat
        erover, wat geldt hier, wat kan er nog bij, en waar loopt het vast. Ze horen bij elkaar,
        dus staan ze hier bij elkaar.</p>
    </div>

    <h3>De vier vragen</h3>
    <div class="rooster" id="leden"></div>

    <h3>Wat er in alle vier terugkomt</h3>
    <div id="lijnen"></div>

    <h3>Verwant werk: de Atlas voor een Schone Maas</h3>
    <div class="atlas" id="atlas"></div>
  </div>

  <script>
    const esc = s => String(s).replace(/[&<>"]/g, c =>
      ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'}[c]));

    fetch("/api/water/hub").then(r => r.json()).then(d => {
      document.getElementById("leden").innerHTML = d.leden
        .filter(l => l.id !== "overzicht")
        .map(l => `<a class="kaart" href="${esc(l.pad)}">
             <h4>${esc(l.titel)}</h4><p>${esc(l.samenvatting)}</p>
             <div class="tags">
               ${l.live.map(x => `<span class="tag live">live · ${esc(x)}</span>`).join("")}
               ${l.synthetisch.map(x => `<span class="tag syn">synthetisch · ${esc(x)}</span>`).join("")}
             </div></a>`).join("");

      const dekking = Object.fromEntries(d.dekking.map(r => [r.id, r.leden]));
      document.getElementById("lijnen").innerHTML = d.lijnen.map(l => `
        <div class="lijn"><h4>${esc(l.kop)}</h4><p>${esc(l.tekst)}</p>
          <div>${(dekking[l.id] || []).map(m =>
            `<a href="${esc(m.pad)}">${esc(m.label)}</a>`).join("")}</div></div>`).join("");

      const a = d.atlas;
      document.getElementById("atlas").innerHTML = `
        <p style="margin:0 0 4px"><a href="${esc(a.url)}" target="_blank" rel="noopener"
           style="color:var(--accent);text-decoration:none">${esc(a.naam)}</a>
           — ${esc(a.houder)}.</p>
        <div class="atlas-kol">
          <div><b style="font-size:13px">Wat daar al is</b>
            <ul>${a.wat_er_al_is.map(x => `<li>${esc(x)}</li>`).join("")}</ul></div>
          <div><b style="font-size:13px">Wat dit lab toevoegt</b>
            <ul>${a.wat_dit_lab_toevoegt.map(x => `<li>${esc(x)}</li>`).join("")}</ul></div>
        </div>
        <p class="licentie">${esc(a.licentie)}</p>`;
    });
  </script>
</body>
</html>
```

- [ ] **Step 5: Draai de test en zie hem slagen**

Run: `.venv/bin/python -m pytest tests/test_api_water.py -v`
Expected: PASS — 3 passed

- [ ] **Step 6: Commit**

```bash
git add src/leefomgevinglab/static/water.html src/leefomgevinglab/geluidsmeter/api.py tests/test_api_water.py
git commit -m "feat(llab): landingspagina /water met de vier vragen en de Atlas-positionering

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>"
```

---

### Task 3: De subnav op de bestaande waterpagina's

**Files:**
- Modify: `src/leefomgevinglab/static/gebruiksruimte.html:117-120` (de `<nav>` in de header)
- Modify: `src/leefomgevinglab/static/balo.html` (de `<nav>` rond regel 190)
- Modify: `src/leefomgevinglab/static/keten-tab.html:162-166` (de `<nav>` in de header)
- Modify: `src/leefomgevinglab/static/index.html:75-93` (hoofdnav) en het kaartrooster (rond regel 232)
- Modify: `src/leefomgevinglab/geluidsmeter/api.py` (routes `/gebruiksruimte`, `/balo`, `_keten_tab`)
- Test: `tests/test_api_water.py` (uitbreiden)

**Interfaces:**
- Consumes: `_waterpagina()` en `water_hub.subnav_html()` uit Task 2
- Produces: geen nieuwe symbolen; alle waterpagina's dragen dezelfde balk

- [ ] **Step 1: Schrijf de falende test**

Voeg toe aan `tests/test_api_water.py`:

```python
import pytest


@pytest.mark.parametrize("pad,actief_label", [
    ("/gebruiksruimte", "Ruimte"),
    ("/balo", "Knelpunten"),
    ("/lozing", "Keten"),
])
def test_waterpaginas_dragen_dezelfde_subnav(monkeypatch, pad, actief_label):
    r = _client(monkeypatch).get(pad)
    assert r.status_code == 200
    assert 'class="waternav"' in r.text
    assert r.text.count('aria-current="page"') == 1
    assert "__WATERNAV__" not in r.text


def test_dvth_is_geen_waterpagina_en_krijgt_de_balk_niet(monkeypatch):
    """keten-tab.html bedient ook /dvth; die hoort niet in het waterdossier."""
    r = _client(monkeypatch).get("/dvth")
    assert r.status_code == 200
    assert 'class="waternav"' not in r.text
    assert "__WATERNAV__" not in r.text, "placeholder moet leeg worden vervangen, niet blijven staan"


def test_hoofdnav_heeft_een_ingang_naar_het_waterdossier(monkeypatch):
    r = _client(monkeypatch).get("/")
    assert 'href="/water"' in r.text
    assert 'href="/gebruiksruimte"' not in r.text, "opgegaan in het dossier"
```

- [ ] **Step 2: Draai de test en zie hem falen**

Run: `.venv/bin/python -m pytest tests/test_api_water.py -v`
Expected: FAIL — de vier nieuwe tests falen; `'class="waternav"' in r.text` is False

- [ ] **Step 3: Zet de placeholder in de drie pagina's**

In `src/leefomgevinglab/static/gebruiksruimte.html`, vervang het `<nav>`-blok in de header (regels 117-120) door een verkorte hoofdnav, en zet de placeholder ná `</header>`:

```html
    <nav><a href="/">Home</a><a href="/water">Waterdossier</a></nav>
  </header>
  __WATERNAV__
```

Doe hetzelfde in `src/leefomgevinglab/static/balo.html` en `src/leefomgevinglab/static/keten-tab.html`.

Neem in alle drie de `.waternav`-CSS over uit `water.html` (het blok van `.waternav {` tot en met `.waternav a[aria-current="page"] { … }`), direct vóór de sluitende `</style>`.

- [ ] **Step 4: Laat de routes de placeholder vervangen**

In `api.py`, vervang `_keten_tab` en de twee paginaroutes:

```python
def _keten_tab(dossier: str) -> str:
    """Eén template voor alle doelbeeld-tabs; de dossiernaam bepaalt welke API hij bevraagt.

    /lozing hoort bij het waterdossier en krijgt de subnav; /dvth niet — daar wordt de
    placeholder leeg vervangen.
    """
    sjabloon = (Path(__file__).parent.parent / "static" / "keten-tab.html").read_text()
    nav = water_hub_mod.subnav_html("keten") if dossier == "lozing" else ""
    return sjabloon.replace("__DOSSIER__", dossier).replace("__WATERNAV__", nav)
```

```python
@app.get("/gebruiksruimte", response_class=HTMLResponse)
def gebruiksruimte_page():
    return _waterpagina("gebruiksruimte.html", "ruimte")


@app.get("/balo", response_class=HTMLResponse)
def balo_page():
    return _waterpagina("balo.html", "knelpunten")
```

- [ ] **Step 5: Werk de hoofdnav bij**

In `src/leefomgevinglab/static/index.html`, vervang in de nav (regels 75-93) de regel
`<a href="/gebruiksruimte">Wat kan hier nog?</a>` door `<a href="/water">Waterdossier</a>`.

Vervang in het kaartrooster de kaart met `href="/gebruiksruimte"` (rond regel 232) door:

```html
        <a class="card live" href="/water">
          <h3>Waterdossier</h3>
          <p>Eén directe lozing op een rijkswater, van bevoegd gezag tot gebruiksruimte —
             de keten, de kaart en de knelpunten bij elkaar.</p>
        </a>
```

`/lozing` en `/balo` blijven ongewijzigd in nav en rooster staan: de eerste is de tegenhanger
van `/dvth`, de tweede dekt ook de Seveso-casus.

- [ ] **Step 6: Draai de tests en zie ze slagen**

Run: `.venv/bin/python -m pytest tests/test_api_water.py -v`
Expected: PASS — 7 passed

- [ ] **Step 7: Draai de hele suite — niets anders mag breken**

Run: `.venv/bin/python -m pytest -q`
Expected: PASS, geen nieuwe failures ten opzichte van vóór deze taak

- [ ] **Step 8: Commit**

```bash
git add src/leefomgevinglab/static/ src/leefomgevinglab/geluidsmeter/api.py tests/test_api_water.py
git commit -m "feat(llab): gedeelde subnav op alle waterpagina's, dossier-ingang in de hoofdnav

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>"
```

---

### Task 4: De KRW-bron geeft meer prijs

**Files:**
- Modify: `src/leefomgevinglab/usecases/lozing_keten/bronnen.py`
- Test: `tests/test_lozing.py` (uitbreiden)

**Interfaces:**
- Consumes: `wfs.features_params`, `wfs.haal_features` (bestaand)
- Produces: `contextset()` levert extra sleutels `watertype`, `watercategorie`, `waterstatus`, `waterbeheerder`, `omvang`, `omvang_eenheid`, `gemiddelde_diepte`; `bevoegd_gezag()` gebruikt `waterbeheerder`

- [ ] **Step 1: Schrijf de falende test**

Voeg toe aan `tests/test_lozing.py`:

```python
from leefomgevinglab.usecases.lozing_keten import bronnen as lb


def _nep_haal(antwoorden):
    """Geeft per aanroep het volgende antwoord terug; negeert url en params."""
    it = iter(antwoorden)

    def haal(url, params, timeout_s=25.0):
        return next(it)
    return haal


_KRW_VLAK = """{"features":[{"properties":{
    "naam":"IJssel","owl_id":"NL93_IJSSEL","sgd_id":"NLRN","gebtype":"R",
    "owltype":"R7","owlcat":"1","owlstat":"Sterk veranderd",
    "wbhnaam":"Ministerie van Infrastructuur en Waterstaat (Rijkswaterstaat)",
    "wbhcode":"NL_MINIW","omvang":123.4,"eenheid":"km2","gemdiepte":4.2}}]}"""
_GEMEENTE = """{"features":[{"properties":{"naam":"Deventer","ligtInProvincieNaam":"Overijssel"}}]}"""


def test_contextset_neemt_het_watertype_en_de_beheerder_over():
    cs = lb.contextset(206800.0, 474000.0, haal=_nep_haal([_KRW_VLAK, _GEMEENTE]))
    assert cs["waterlichaam"] == "IJssel"
    assert cs["watertype"] == "R7"
    assert cs["watercategorie"] == "1"
    assert cs["waterstatus"] == "Sterk veranderd"
    assert "Rijkswaterstaat" in cs["waterbeheerder"]
    assert cs["omvang"] == 123.4 and cs["omvang_eenheid"] == "km2"
    assert cs["gemiddelde_diepte"] == 4.2


def test_bevoegd_gezag_noemt_de_beheerder_uit_de_bron():
    cs = lb.contextset(206800.0, 474000.0, haal=_nep_haal([_KRW_VLAK, _GEMEENTE]))
    bg = lb.bevoegd_gezag(cs)
    assert "Rijkswaterstaat" in bg["lozingsactiviteit"]
    assert bg["bron_beheerder"] == "RWS KRW-service (veld wbhnaam)"


def test_bevoegd_gezag_valt_terug_als_de_beheerder_leeg_is():
    """Het veld owl_naam is in alle 54 vlakken leeg; wbhnaam kan dat ook worden."""
    zonder = _KRW_VLAK.replace(
        '"wbhnaam":"Ministerie van Infrastructuur en Waterstaat (Rijkswaterstaat)",', '')
    cs = lb.contextset(206800.0, 474000.0, haal=_nep_haal([zonder, _GEMEENTE]))
    bg = lb.bevoegd_gezag(cs)
    assert "Minister van IenW" in bg["lozingsactiviteit"]
    assert bg["bron_beheerder"] == "afgeleid uit de aanwezigheid van owl_id"


def test_geen_rijkswater_geeft_het_waterschap():
    cs = lb.contextset(150000.0, 400000.0, haal=_nep_haal(['{"features":[]}',
                                                           '{"features":[]}', _GEMEENTE]))
    assert cs["rijkswater"] is False
    assert "waterschap" in lb.bevoegd_gezag(cs)["lozingsactiviteit"]
```

- [ ] **Step 2: Draai de test en zie hem falen**

Run: `.venv/bin/python -m pytest tests/test_lozing.py -k "watertype or beheerder or waterschap" -v`
Expected: FAIL — `KeyError: 'watertype'`

- [ ] **Step 3: Breid `bronnen.py` uit**

In `contextset()`, vervang de `velden`-string en de `leeg`-dict:

```python
    leeg = {"straal_m": straal_m, "rd": [x, y], "waterlichaam": None, "owl_id": None,
            "stroomgebiedsdistrict": None, "rijkswater": None, "gemeente": None,
            "provincie": None, "watertype": None, "watercategorie": None,
            "waterstatus": None, "waterbeheerder": None, "omvang": None,
            "omvang_eenheid": None, "gemiddelde_diepte": None, "bronnen": bronnen}
```

In de lus over `KRW_LAGEN`:

```python
        fs = wfs.haal_features(haal, KRW_WFS, wfs.features_params(
            laag, cql=f"DWITHIN(shape, POINT({x} {y}), {straal_m}, meters)",
            count=3,
            velden="naam,owl_id,sgd_id,gebtype,owltype,owlcat,owlstat,"
                   "wbhnaam,wbhcode,omvang,eenheid,gemdiepte"), "RWS KRW-WFS", oms, bronnen)
        if fs:
            p = fs[0]
            waterlichaam = (p.get("naam") or "").strip() or None
            owl_id, sgd = p.get("owl_id"), p.get("sgd_id")
            extra = {"watertype": p.get("owltype"), "watercategorie": p.get("owlcat"),
                     "waterstatus": p.get("owlstat"),
                     "waterbeheerder": (p.get("wbhnaam") or "").strip() or None,
                     "omvang": p.get("omvang"), "omvang_eenheid": p.get("eenheid"),
                     "gemiddelde_diepte": p.get("gemdiepte")}
```

Initialiseer `extra = {}` vóór de lus en neem het op in de return:

```python
    return {**leeg, **extra, "live": True, "volledig": volledig,
            "waterlichaam": waterlichaam, "owl_id": owl_id, "stroomgebiedsdistrict": sgd,
            "rijkswater": bool(owl_id),
            "gemeente": (gem[0].get("naam") if gem else None),
            "provincie": (gem[0].get("ligtInProvincieNaam") if gem else None)}
```

In `bevoegd_gezag()`, vervang de rijkswater-tak:

```python
    if cs.get("rijkswater"):
        beheerder = cs.get("waterbeheerder")
        if beheerder:
            lozing, bron = beheerder, "RWS KRW-service (veld wbhnaam)"
        else:
            lozing = "Minister van IenW, uitgevoerd door Rijkswaterstaat"
            bron = "afgeleid uit de aanwezigheid van owl_id"
        grond = (f"het lozingspunt ligt aan {cs.get('waterlichaam') or 'een rijkswater'} "
                 f"({cs.get('owl_id')}), een water in rijksbeheer")
    elif cs.get("live"):
        lozing, bron = "het waterschap als waterbeheerder", "afgeleid: geen treffer in de KRW-service"
        grond = "geen rijkswaterlichaam gevonden binnen de straal; dan is het regionaal water"
    else:
        lozing, bron = "niet bepaald (bronnen niet bevraagd)", "niet bevraagd"
        grond = "zonder live-modus valt het bevoegd gezag niet af te leiden"
```

en voeg `"bron_beheerder": bron` toe aan de returndict.

- [ ] **Step 4: Draai de tests en zie ze slagen**

Run: `.venv/bin/python -m pytest tests/test_lozing.py -v`
Expected: PASS — inclusief de bestaande lozingstests

- [ ] **Step 5: Commit**

```bash
git add src/leefomgevinglab/usecases/lozing_keten/bronnen.py tests/test_lozing.py
git commit -m "feat(llab): watertype en waterbeheerder uit de KRW-service in plaats van afgeleid

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>"
```

---

### Task 5: Een profiel voor elk rijkswater

**Files:**
- Create: `src/leefomgevinglab/usecases/gebruiksruimte/waterprofiel.py`
- Test: `tests/test_waterprofiel.py`

**Interfaces:**
- Consumes: de contextset-sleutels uit Task 4
- Produces: `profiel(cs: dict) -> dict` met sleutels `echt`, `afgeleid`, `herkomst`, `volledig`; `als_waterlichaam(p: dict) -> dict` in het formaat dat `ruimte.bereken()` verwacht (`debiet_m3_s`, `parameters`)

- [ ] **Step 1: Schrijf de falende test**

Maak `tests/test_waterprofiel.py`:

```python
import pytest

from leefomgevinglab.usecases.gebruiksruimte import waterprofiel as wp

_IJSSEL = {"waterlichaam": "IJssel", "owl_id": "NL93_IJSSEL", "stroomgebiedsdistrict": "NLRN",
           "watertype": "R7", "watercategorie": "1", "waterstatus": "Sterk veranderd",
           "waterbeheerder": "Ministerie van IenW (Rijkswaterstaat)",
           "omvang": 123.4, "omvang_eenheid": "km2", "gemiddelde_diepte": 4.2,
           "rijkswater": True}
_MEER = {**_IJSSEL, "waterlichaam": "IJsselmeer", "owl_id": "NL92_IJSSELMEER",
         "watertype": "M21", "watercategorie": "2", "omvang": 1100.0, "gemiddelde_diepte": 4.5}
_KUST = {**_IJSSEL, "waterlichaam": "Waddenzee", "owl_id": "NL81_1",
         "watertype": "K2", "watercategorie": "3", "omvang": 2154.51, "gemiddelde_diepte": 3.0}


def test_het_echte_deel_komt_ongewijzigd_uit_de_bron():
    p = wp.profiel(_IJSSEL)
    assert p["echt"]["naam"] == "IJssel"
    assert p["echt"]["owl_id"] == "NL93_IJSSEL"
    assert p["echt"]["watertype"] == "R7"
    assert p["echt"]["beheerder"] == "Ministerie van IenW (Rijkswaterstaat)"
    assert p["echt"]["omvang"] == 123.4
    # niets uit het echte deel mag verzonnen zijn
    assert set(p["echt"]) <= {"naam", "owl_id", "stroomgebiedsdistrict", "watertype",
                              "watercategorie", "waterstatus", "beheerder", "omvang",
                              "omvang_eenheid", "gemiddelde_diepte"}


def test_elk_afgeleid_getal_heeft_een_herkomstregel():
    p = wp.profiel(_IJSSEL)
    assert p["afgeleid"]["debiet_m3_s"] > 0
    assert p["afgeleid"]["parameters"]
    for sleutel in p["afgeleid"]:
        assert sleutel in p["herkomst"], f"{sleutel} zonder herkomst"
        assert p["herkomst"][sleutel]


def test_echt_en_afgeleid_overlappen_niet():
    """De scheiding is het hele punt; een veld mag niet in beide zitten."""
    p = wp.profiel(_IJSSEL)
    assert set(p["echt"]) & set(p["afgeleid"]) == set()


def test_verschillende_categorieen_geven_verschillende_profielen():
    rivier, meer, kust = wp.profiel(_IJSSEL), wp.profiel(_MEER), wp.profiel(_KUST)
    debieten = {rivier["afgeleid"]["debiet_m3_s"], meer["afgeleid"]["debiet_m3_s"],
                kust["afgeleid"]["debiet_m3_s"]}
    assert len(debieten) == 3, "zonder differentiatie is 'een profiel per water' een lege huls"
    normen = {p["afgeleid"]["parameters"][0]["norm_mg_l"] for p in (rivier, meer, kust)}
    assert len(normen) > 1


def test_elk_profiel_houdt_een_parameter_zonder_ruimte():
    """PFOA: achtergrond boven de norm. Zonder dat mist elke locatie de scherpste uitkomst."""
    for cs in (_IJSSEL, _MEER, _KUST):
        ps = wp.profiel(cs)["afgeleid"]["parameters"]
        assert any(p["achtergrond_mg_l"] >= p["norm_mg_l"] for p in ps)
        assert any(p["zzs"] for p in ps)


def test_onbekende_categorie_valt_terug_zonder_te_knallen():
    p = wp.profiel({**_IJSSEL, "watercategorie": "9", "watertype": None})
    assert p["afgeleid"]["debiet_m3_s"] > 0
    assert "terugval" in p["herkomst"]["debiet_m3_s"]
    assert p["volledig"] is False


def test_zonder_waterlichaam_is_er_geen_profiel():
    p = wp.profiel({"rijkswater": False, "waterlichaam": None, "owl_id": None})
    assert p["afgeleid"] == {}
    assert p["volledig"] is False
    assert p["reden"]


def test_als_waterlichaam_levert_wat_de_rekensom_verwacht():
    w = wp.als_waterlichaam(wp.profiel(_IJSSEL))
    assert w["debiet_m3_s"] > 0
    for p in w["parameters"]:
        assert {"naam", "norm_mg_l", "achtergrond_mg_l", "zzs", "toelichting"} <= set(p)
```

- [ ] **Step 2: Draai de test en zie hem falen**

Run: `.venv/bin/python -m pytest tests/test_waterprofiel.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named '…waterprofiel'`

- [ ] **Step 3: Schrijf de implementatie**

Maak `src/leefomgevinglab/usecases/gebruiksruimte/waterprofiel.py`:

```python
"""Van een KRW-feature naar een waterlichaamprofiel — met echt en verzonnen strikt gescheiden.

De vaste IJssel in `gebied.py` volstaat voor drie locaties. Wie op een willekeurig punt wil
prikken heeft voor elk rijkswater een profiel nodig. De identiteit van het water komt uit de
KRW-service van RWS en is echt: naam, id, beheerder, watertype, categorie, status, omvang,
gemiddelde diepte.

Het debiet en de achtergrondconcentraties zitten niet in die service en worden hier afgeleid
uit de categorie en de omvang. Die getallen zijn illustratief — het mechanisme is echt, de
cijfers niet. Elk afgeleid veld draagt daarom een herkomstregel, zodat de pagina kan tonen
waar een getal vandaan komt in plaats van het te laten doorgaan voor meting.

Vindt iemand ooit een echte bron voor achtergrondconcentraties per waterlichaam (het
Waterkwaliteitsportaal is de kandidaat), dan vervalt het hele `afgeleid`-blok en blijft de
rest staan.
"""

# Basisprofielen per KRW-categorie: 1 rivier, 2 meer, 3 kust, 4 overgangswater.
# Normen zijn van dezelfde orde als de KRW-doelen maar door dit lab gekozen, niet uit het Bkl
# overgenomen. De verhoudingen tussen de categorieën dragen het verhaal, niet de absolute waarden.
_CATEGORIEEN = {
    "1": {"naam": "rivier", "debiet_basis_m3_s": 300.0, "factor": 1.00},
    "2": {"naam": "meer", "debiet_basis_m3_s": 40.0, "factor": 0.85},
    "3": {"naam": "kustwater", "debiet_basis_m3_s": 1500.0, "factor": 1.60},
    "4": {"naam": "overgangswater", "debiet_basis_m3_s": 800.0, "factor": 1.30},
}
_TERUGVAL = {"naam": "onbekend type", "debiet_basis_m3_s": 150.0, "factor": 1.00}

# Vier parameters, gekozen omdat ze samen het hele spectrum laten zien: één die krap zit, één
# metaal, één somparameter met ruimte, en één ZZS waar de achtergrond al boven de norm ligt.
_PARAMETERS = [
    {"naam": "stikstof totaal", "norm_mg_l": 2.2, "verzadiging": 0.98, "zzs": False,
     "toelichting": "Nutriënt. De norm ligt dicht bij wat er al in zit, dus hier gaat het volume "
                    "van een lozing wél meetellen."},
    {"naam": "zink", "norm_mg_l": 0.0078, "verzadiging": 0.91, "zzs": False,
     "toelichting": "Metaal; krappe marge, grotendeels diffuus van herkomst."},
    {"naam": "AOX", "norm_mg_l": 0.05, "verzadiging": 0.42, "zzs": False,
     "toelichting": "Somparameter organische halogenen; hier nog ruimte."},
    {"naam": "PFOA", "norm_mg_l": 0.0000048, "verzadiging": 1.27, "zzs": True,
     "toelichting": "Zeer zorgwekkende stof. De achtergrond ligt bóven de norm — er is geen "
                    "ruimte, en er geldt een minimalisatieplicht."},
]

_ECHTE_VELDEN = {
    "waterlichaam": "naam", "owl_id": "owl_id", "stroomgebiedsdistrict": "stroomgebiedsdistrict",
    "watertype": "watertype", "watercategorie": "watercategorie", "waterstatus": "waterstatus",
    "waterbeheerder": "beheerder", "omvang": "omvang", "omvang_eenheid": "omvang_eenheid",
    "gemiddelde_diepte": "gemiddelde_diepte",
}


def _debiet(cat: dict, omvang, bekend: bool) -> float:
    """Basisdebiet van de categorie, geschaald met de omvang van dít waterlichaam."""
    basis = cat["debiet_basis_m3_s"]
    if not bekend or not omvang or omvang <= 0:
        return basis
    # Milde schaling: een tien keer zo groot water krijgt ruwweg twee keer het debiet.
    return round(basis * (float(omvang) / 100.0) ** 0.3, 1)


def profiel(cs: dict) -> dict:
    """Een profiel voor het waterlichaam uit deze contextset."""
    echt = {doel: cs.get(bron_veld) for bron_veld, doel in _ECHTE_VELDEN.items()}

    if not cs.get("owl_id"):
        return {"echt": echt, "afgeleid": {}, "herkomst": {}, "volledig": False,
                "reden": "geen rijkswaterlichaam op dit punt; zonder waterlichaam is er geen "
                         "norm om ruimte tegen af te zetten"}

    code = str(cs.get("watercategorie") or "")
    bekend = code in _CATEGORIEEN
    cat = _CATEGORIEEN.get(code, _TERUGVAL)
    q = _debiet(cat, cs.get("omvang"), bekend)

    parameters = []
    for p in _PARAMETERS:
        achtergrond = p["norm_mg_l"] * p["verzadiging"] * cat["factor"]
        parameters.append({"naam": p["naam"], "norm_mg_l": p["norm_mg_l"],
                           "achtergrond_mg_l": achtergrond, "zzs": p["zzs"],
                           "toelichting": p["toelichting"]})

    herkomst_debiet = (f"afgeleid van KRW-categorie {code} ({cat['naam']}) en de omvang "
                       f"uit de bron" if bekend else
                       f"terugval: categorie '{code}' is onbekend, basisdebiet gebruikt")
    return {
        "echt": echt,
        "afgeleid": {"debiet_m3_s": q, "parameters": parameters,
                     "categorie_naam": cat["naam"]},
        "herkomst": {
            "debiet_m3_s": herkomst_debiet,
            "parameters": "normen door dit lab gekozen in de orde van de KRW-doelen, niet uit "
                          "het Bkl overgenomen; achtergrondconcentraties afgeleid van de "
                          f"categoriefactor ({cat['factor']})",
            "categorie_naam": f"KRW-categorie {code} uit de bron" if bekend else "terugval",
        },
        "volledig": bekend,
    }


def als_waterlichaam(p: dict) -> dict:
    """Het profiel in het formaat dat `ruimte.bereken()` verwacht."""
    if not p.get("afgeleid"):
        raise ValueError(p.get("reden") or "geen profiel")
    return {"naam": p["echt"].get("naam"), "owl_id": p["echt"].get("owl_id"),
            "debiet_m3_s": p["afgeleid"]["debiet_m3_s"],
            "parameters": p["afgeleid"]["parameters"]}
```

- [ ] **Step 4: Draai de tests en zie ze slagen**

Run: `.venv/bin/python -m pytest tests/test_waterprofiel.py -v`
Expected: PASS — 8 passed

- [ ] **Step 5: Commit**

```bash
git add src/leefomgevinglab/usecases/gebruiksruimte/waterprofiel.py tests/test_waterprofiel.py
git commit -m "feat(llab): waterprofiel per rijkswater, echt en afgeleid strikt gescheiden

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>"
```

---

### Task 6: De Atlas bevragen

**Files:**
- Create: `src/leefomgevinglab/connectors/smwk_atlas.py`
- Modify: `core/config.yaml` (sectie `leefomgevinglab:`, naast `stelselcatalogus:` rond regel 284)
- Test: `tests/test_smwk_atlas.py`

**Interfaces:**
- Consumes: `BaseConnector.get_json` uit `connectors/base.py`
- Produces: `SmwkAtlasConnector(cache_dir, timeout, cache_ttl, base_url=None)` met methode `vergunningen_bij_punt(x: float, y: float, straal_m: int = 5000) -> list[dict]`; elke post heeft `naam`, `plaats`, `kenmerk`, `locatie`, `url`, `voorschriften: list[dict]`

- [ ] **Step 1: Schrijf de falende test**

Maak `tests/test_smwk_atlas.py`:

```python
import pytest

from leefomgevinglab.connectors.smwk_atlas import SmwkAtlasConnector

_VESTIGINGEN = {"features": [
    {"attributes": {"Kenmerk": "RWS-2015/38632", "Statutaire_naam": "Lawter Maastricht BV",
                    "Plaats": "Maastricht", "Locatieomschrijving": "Maas linkeroever",
                    "URL": "https://example.invalid/verg1"}},
    {"attributes": {"Kenmerk": "DLB2006/8811", "Statutaire_naam": "Chromaflo Technologies BV",
                    "Plaats": "Maastricht", "Locatieomschrijving": "", "URL": ""}},
]}
_VOORSCHRIFTEN = {"features": [
    {"attributes": {"Kenmerk": "RWS-2015/38632", "Parameter": "zink", "Waarde": 0.3,
                    "Eenheid": "milligram per liter", "Besluitdatum": 1420070400000}},
    {"attributes": {"Kenmerk": "RWS-2015/38632", "Parameter": "Debiet", "Waarde": 25.0,
                    "Eenheid": "kubieke meter per uur", "Besluitdatum": 1420070400000}},
    {"attributes": {"Kenmerk": "DLB2006/8811", "Parameter": "stikstof totaal", "Waarde": 1.2,
                    "Eenheid": "ton per jaar", "Besluitdatum": None}},
]}


class _NepConnector(SmwkAtlasConnector):
    """Vervangt alleen het HTTP-deel; de opbouw van de query blijft echt."""

    def __init__(self, tmp_path, antwoorden):
        super().__init__(cache_dir=str(tmp_path))
        self.antwoorden = list(antwoorden)
        self.aanroepen = []

    def get_json(self, url, params=None, headers=None):
        self.aanroepen.append((url, params or {}))
        return self.antwoorden.pop(0)


def test_ruimtelijke_query_gebruikt_rd_en_een_straal(tmp_path):
    c = _NepConnector(tmp_path, [_VESTIGINGEN, _VOORSCHRIFTEN])
    c.vergunningen_bij_punt(177748.0, 321314.0, straal_m=5000)
    url, p = c.aanroepen[0]
    assert url.endswith("/0/query")
    assert p["inSR"] == 28992
    assert p["geometry"] == "177748.0,321314.0"
    assert p["geometryType"] == "esriGeometryPoint"
    assert p["distance"] == 5000
    assert p["units"] == "esriSRUnit_Meter"
    assert p["spatialRel"] == "esriSpatialRelIntersects"
    assert p["f"] == "json"


def test_voorschriften_worden_per_kenmerk_opgehaald(tmp_path):
    c = _NepConnector(tmp_path, [_VESTIGINGEN, _VOORSCHRIFTEN])
    c.vergunningen_bij_punt(177748.0, 321314.0)
    _, p = c.aanroepen[1]
    assert "RWS-2015/38632" in p["where"] and "DLB2006/8811" in p["where"]
    assert p["where"].startswith("Kenmerk IN (")


def test_elke_vestiging_krijgt_haar_eigen_voorschriften(tmp_path):
    c = _NepConnector(tmp_path, [_VESTIGINGEN, _VOORSCHRIFTEN])
    uit = c.vergunningen_bij_punt(177748.0, 321314.0)
    assert len(uit) == 2
    lawter = next(v for v in uit if v["kenmerk"] == "RWS-2015/38632")
    assert lawter["naam"] == "Lawter Maastricht BV"
    assert lawter["plaats"] == "Maastricht"
    assert {v["parameter"] for v in lawter["voorschriften"]} == {"zink", "Debiet"}
    chromaflo = next(v for v in uit if v["kenmerk"] == "DLB2006/8811")
    assert len(chromaflo["voorschriften"]) == 1


def test_besluitdatum_wordt_leesbaar(tmp_path):
    c = _NepConnector(tmp_path, [_VESTIGINGEN, _VOORSCHRIFTEN])
    uit = c.vergunningen_bij_punt(177748.0, 321314.0)
    lawter = next(v for v in uit if v["kenmerk"] == "RWS-2015/38632")
    assert lawter["besluitdatum"] == "2015-01-01"


def test_geen_vestigingen_geeft_geen_tweede_aanroep(tmp_path):
    c = _NepConnector(tmp_path, [{"features": []}])
    assert c.vergunningen_bij_punt(206800.0, 474000.0) == []
    assert len(c.aanroepen) == 1, "zonder vestigingen hoeft de tabel niet bevraagd"


def test_kenmerk_met_apostrof_breekt_de_where_clause_niet(tmp_path):
    vest = {"features": [{"attributes": {"Kenmerk": "RWS-O'Neill/1", "Statutaire_naam": "X",
                                         "Plaats": "Y", "Locatieomschrijving": "", "URL": ""}}]}
    c = _NepConnector(tmp_path, [vest, {"features": []}])
    c.vergunningen_bij_punt(1.0, 2.0)
    _, p = c.aanroepen[1]
    assert "O''Neill" in p["where"], "apostrof moet verdubbeld worden"
```

- [ ] **Step 2: Draai de test en zie hem falen**

Run: `.venv/bin/python -m pytest tests/test_smwk_atlas.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'leefomgevinglab.connectors.smwk_atlas'`

- [ ] **Step 3: Schrijf de connector**

Maak `src/leefomgevinglab/connectors/smwk_atlas.py`:

```python
"""De Atlas voor een Schone Maas: echte lozingsvergunningen, ruimtelijk bevraagbaar.

Van de Schone Maaswaterketen — de waterschappen Aa en Maas, Brabantse Delta, De Dommel en
Limburg, met Rijkswaterstaat en de drinkwaterbedrijven. Sinds april 2023 staan de directe
lozingsvergunningen erin. Voor het Maasstroomgebied is dit het register dat elders in
Nederland ontbreekt.

Twee lagen op één FeatureServer:
  * laag 0 — de vestigingen als punt (72 stuks), ruimtelijk bevraagbaar;
  * tabel 2 — de vergunde voorschriften (782 stuks), gekoppeld via `Kenmerk`.

De ruimtelijke query gaat rechtstreeks op RD (`inSR=28992`). Geverifieerd 2026-09-16: een punt
bij Maastricht geeft 11 vestigingen binnen 5 km, een punt bij Deventer nul.

Licentie: de lagen staan publiek open maar dragen geen expliciete licentie. Daarom live
bevragen met bronvermelding, en geen kopie van de dataset in deze repo.
"""
from datetime import datetime, timezone

from .base import BaseConnector

BASIS = ("https://services-eu1.arcgis.com/S0XTphM6W3v0bENW/arcgis/rest/services/"
         "Vestigingen_Vergunningen_Uniek/FeatureServer")

_VESTIGING_VELDEN = "Kenmerk,Statutaire_naam,Plaats,Locatieomschrijving,URL"
_VOORSCHRIFT_VELDEN = ("Kenmerk,Parameter,Waarde,Eenheid,Besluitdatum,Bemonsteringswijze,"
                       "meetpunt_X_Coordinaat,meetpunt_Y_Coordinaat")

BRON = {"naam": "Atlas voor een Schone Maas", "url": "https://atlas-smwk.hub.arcgis.com/",
        "houder": "Schone Maaswaterketen"}


def _datum(ms) -> str | None:
    """ArcGIS levert epoch-milliseconden; maak er een leesbare datum van."""
    if ms is None:
        return None
    try:
        return datetime.fromtimestamp(float(ms) / 1000.0, tz=timezone.utc).strftime("%Y-%m-%d")
    except (TypeError, ValueError, OSError):
        return None


class SmwkAtlasConnector(BaseConnector):
    def __init__(self, cache_dir: str, timeout: float = 20.0, cache_ttl: int = 86400,
                 base_url: str | None = None):
        super().__init__(cache_dir=cache_dir, timeout=timeout, cache_ttl=cache_ttl)
        self.base_url = (base_url or BASIS).rstrip("/")

    def vergunningen_bij_punt(self, x: float, y: float, straal_m: int = 5000) -> list[dict]:
        """De vergunde vestigingen binnen `straal_m` van dit RD-punt, met hun voorschriften."""
        vest = self.get_json(f"{self.base_url}/0/query", {
            "geometry": f"{x},{y}", "geometryType": "esriGeometryPoint", "inSR": 28992,
            "spatialRel": "esriSpatialRelIntersects", "distance": straal_m,
            "units": "esriSRUnit_Meter", "outFields": _VESTIGING_VELDEN,
            "returnGeometry": "false", "f": "json",
        })
        posten = {}
        for f in vest.get("features") or []:
            a = f.get("attributes") or {}
            kenmerk = a.get("Kenmerk")
            if not kenmerk or kenmerk in posten:
                continue
            posten[kenmerk] = {
                "kenmerk": kenmerk, "naam": a.get("Statutaire_naam"), "plaats": a.get("Plaats"),
                "locatie": (a.get("Locatieomschrijving") or "").strip() or None,
                "url": (a.get("URL") or "").strip() or None,
                "besluitdatum": None, "voorschriften": [],
            }
        if not posten:
            return []

        # ArcGIS kent geen parameterbinding; apostrofs verdubbelen is de SQL-conventie.
        lijst = ",".join("'" + k.replace("'", "''") + "'" for k in posten)
        voors = self.get_json(f"{self.base_url}/2/query", {
            "where": f"Kenmerk IN ({lijst})", "outFields": _VOORSCHRIFT_VELDEN,
            "returnGeometry": "false", "f": "json",
        })
        for f in voors.get("features") or []:
            a = f.get("attributes") or {}
            post = posten.get(a.get("Kenmerk"))
            if post is None:
                continue
            post["voorschriften"].append({
                "parameter": a.get("Parameter"), "waarde": a.get("Waarde"),
                "eenheid": a.get("Eenheid"), "bemonstering": a.get("Bemonsteringswijze"),
                "rd": [a.get("meetpunt_X_Coordinaat"), a.get("meetpunt_Y_Coordinaat")],
            })
            post["besluitdatum"] = post["besluitdatum"] or _datum(a.get("Besluitdatum"))

        return list(posten.values())
```

- [ ] **Step 4: Draai de tests en zie ze slagen**

Run: `.venv/bin/python -m pytest tests/test_smwk_atlas.py -v`
Expected: PASS — 6 passed

- [ ] **Step 5: Voeg de config toe**

In `core/config.yaml`, direct ná het blok `stelselcatalogus:` (rond regel 290), binnen `leefomgevinglab:`:

```yaml
  smwk_atlas:
    # Atlas voor een Schone Maas (Schone Maaswaterketen) — echte directe lozingsvergunningen
    # in het Maasstroomgebied: 72 vestigingen, 782 voorschriften, 68 parameters.
    # Ruimtelijk bevraagbaar op RD (inSR=28992). Geverifieerd 2026-09-16.
    # LET OP: publiek toegankelijk maar zónder expliciete licentie — altijd live bevragen met
    # bronvermelding, nooit de dataset kopiëren.
    base_url: "https://services-eu1.arcgis.com/S0XTphM6W3v0bENW/arcgis/rest/services/Vestigingen_Vergunningen_Uniek/FeatureServer"
    straal_m: 5000
    cache_ttl_s: 86400
```

- [ ] **Step 6: Commit**

```bash
git add src/leefomgevinglab/connectors/smwk_atlas.py tests/test_smwk_atlas.py core/config.yaml
git commit -m "feat(llab): connector op de Atlas voor een Schone Maas

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>"
```

---

### Task 7: Van vergunning naar vracht

**Files:**
- Create: `src/leefomgevinglab/usecases/gebruiksruimte/atlas_register.py`
- Modify: `src/leefomgevinglab/usecases/gebruiksruimte/ruimte.py` (de lus in `bereken`, regels 26-33)
- Test: `tests/test_atlas_register.py`, `tests/test_gebruiksruimte.py` (uitbreiden)

**Interfaces:**
- Consumes: de postenstructuur uit Task 6
- Produces: `naar_register(posten: list[dict]) -> dict` met sleutels `register`, `telling`, `bron`; registerposten dragen `vrachten: dict[str, float]` (kg/jaar) en `onbepaald: list[dict]`

- [ ] **Step 1: Schrijf de falende test**

Maak `tests/test_atlas_register.py`:

```python
import pytest

from leefomgevinglab.usecases.gebruiksruimte import atlas_register as ar


def _post(kenmerk="K1", **kw):
    return {"kenmerk": kenmerk, "naam": "Testfabriek BV", "plaats": "Maastricht",
            "locatie": None, "url": None, "besluitdatum": "2015-01-01",
            "voorschriften": kw.get("voorschriften", [])}


def _v(parameter, waarde, eenheid):
    return {"parameter": parameter, "waarde": waarde, "eenheid": eenheid,
            "bemonstering": None, "rd": [None, None]}


# ---------- laag 1: de eenheid is al een vracht ----------

def test_vracht_in_kilogram_per_jaar_wordt_overgenomen():
    d = ar.naar_register([_post(voorschriften=[_v("zink", 120.0, "kilogram per jaar")])])
    assert d["register"][0]["vrachten"]["zink"] == pytest.approx(120.0)


def test_ton_per_jaar_wordt_omgerekend():
    d = ar.naar_register([_post(voorschriften=[_v("stikstof totaal", 1.2, "ton per jaar")])])
    assert d["register"][0]["vrachten"]["stikstof totaal"] == pytest.approx(1200.0)


def test_kilogram_per_dag_en_per_week():
    d = ar.naar_register([_post(voorschriften=[
        _v("zink", 1.0, "kilogram per dag"),
        _v("AOX", 1.0, "kilogram per week")])])
    v = d["register"][0]["vrachten"]
    assert v["zink"] == pytest.approx(365.0)
    assert v["AOX"] == pytest.approx(52.0)


# ---------- laag 2: concentratie × debiet ----------

def test_concentratie_maal_debiet_geeft_een_vracht():
    """0,3 mg/l bij 25 m3/uur = 0,3 * 25 * 24 * 365 / 1000 = 65,7 kg/jaar."""
    d = ar.naar_register([_post(voorschriften=[
        _v("zink", 0.3, "milligram per liter"),
        _v("Debiet", 25.0, "kubieke meter per uur")])])
    assert d["register"][0]["vrachten"]["zink"] == pytest.approx(65.7, rel=1e-3)


def test_microgram_per_liter_wordt_eerst_milligram():
    d = ar.naar_register([_post(voorschriften=[
        _v("zink", 300.0, "microgram per liter"),
        _v("Debiet", 25.0, "kubieke meter per uur")])])
    assert d["register"][0]["vrachten"]["zink"] == pytest.approx(65.7, rel=1e-3)


@pytest.mark.parametrize("eenheid,factor_naar_uur", [
    ("kubieke meter per uur", 1.0),
    ("kubieke meter per dag", 1 / 24),
    ("kubieke met per etmaal", 1 / 24),      # let op: tikfout staat zo in de bron
    ("kubieke meter per seconde", 3600.0),
])
def test_debiet_eenheden_worden_naar_m3_per_uur_gebracht(eenheid, factor_naar_uur):
    d = ar.naar_register([_post(voorschriften=[
        _v("zink", 1.0, "milligram per liter"), _v("Debiet", 24.0, eenheid)])])
    verwacht = 24.0 * factor_naar_uur * 24 * 365 / 1000.0
    assert d["register"][0]["vrachten"]["zink"] == pytest.approx(verwacht, rel=1e-3)


# ---------- laag 3: niet af te leiden ----------

def test_concentratie_zonder_debiet_levert_geen_vracht_maar_wel_een_reden():
    d = ar.naar_register([_post(voorschriften=[_v("zink", 0.3, "milligram per liter")])])
    post = d["register"][0]
    assert "zink" not in post["vrachten"]
    assert post["onbepaald"][0]["parameter"] == "zink"
    assert "debiet" in post["onbepaald"][0]["reden"].lower()


def test_onbruikbare_eenheid_valt_netjes_in_onbepaald():
    d = ar.naar_register([_post(voorschriften=[
        _v("Zuurgraad", 6.5, "dimensieloos"),
        _v("Warmte", 0.5, "megajoule per seconde")])])
    post = d["register"][0]
    assert post["vrachten"] == {}
    assert {o["parameter"] for o in post["onbepaald"]} == {"Zuurgraad", "Warmte"}


def test_lege_waarde_knalt_niet():
    d = ar.naar_register([_post(voorschriften=[_v("zink", None, "kilogram per jaar")])])
    assert d["register"][0]["vrachten"] == {}


# ---------- crosswalk naar de labparameters ----------

def test_aox_synoniemen_landen_op_de_labparameter():
    for naam in ("som extraheerbare organische halogeenverbindingen",
                 "Extraheerbaar organisch chloor"):
        d = ar.naar_register([_post(voorschriften=[_v(naam, 10.0, "kilogram per jaar")])])
        assert "AOX" in d["register"][0]["vrachten"], naam


def test_parameters_buiten_de_crosswalk_tellen_niet_mee_in_de_som():
    d = ar.naar_register([_post(voorschriften=[_v("barium", 10.0, "kilogram per jaar")])])
    assert d["register"][0]["vrachten"] == {}
    assert d["telling"]["buiten_crosswalk"] >= 1


def test_pfoa_komt_niet_voor_in_de_atlas_en_dat_is_de_bevinding():
    assert "PFOA" not in ar.CROSSWALK.values() or ar.CROSSWALK_BEVINDING
    assert "PFOA" in ar.CROSSWALK_BEVINDING


# ---------- telling ----------

def test_telling_laat_zien_hoeveel_er_niet_af_te_leiden_was():
    d = ar.naar_register([
        _post("K1", voorschriften=[_v("zink", 120.0, "kilogram per jaar")]),
        _post("K2", voorschriften=[_v("zink", 0.3, "milligram per liter")]),
    ])
    assert d["telling"]["vracht_direct"] == 1
    assert d["telling"]["onbepaald"] == 1
    assert d["bron"]["naam"] == "Atlas voor een Schone Maas"
```

- [ ] **Step 2: Draai de test en zie hem falen**

Run: `.venv/bin/python -m pytest tests/test_atlas_register.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named '…atlas_register'`

- [ ] **Step 3: Schrijf de omrekening**

Maak `src/leefomgevinglab/usecases/gebruiksruimte/atlas_register.py`:

```python
"""Atlas-voorschriften omzetten naar registerposten met een vracht in kg/jaar.

De rekensom in `ruimte.py` wil per vergunning weten hoeveel kilo per jaar er van een stof in
het water gaat. De Atlas geeft `Waarde` + `Eenheid` in 21 verschillende eenheden. Drie lagen,
in volgorde:

  1. de eenheid is al een vracht (kg/jaar, ton/jaar, kg/dag, kg/week) — direct omrekenen;
  2. de eenheid is een concentratie (mg/l, µg/l) — vracht = concentratie × debiet, mits bij
     hetzelfde kenmerk een Debiet-voorschrift staat. Dat is zo bij 29 van de 72 vestigingen;
  3. anders — de vergunning wordt wél getoond, maar zonder vracht en mét een reden.

Die derde categorie is geen tekortkoming om weg te poetsen. Van een vergunning waarin alleen
een concentratie-eis staat en geen debiet, valt de vracht niet te bepalen — en dus valt hij
ook niet op te tellen. Precies het soort bevinding dat /wfs-kwaliteit voor het REV doet.
"""
from .gebied import vracht_kg_jaar

# De labparameters waar de rekensom mee werkt; alles daarbuiten telt niet mee in de som.
CROSSWALK = {
    "stikstof totaal": "stikstof totaal",
    "zink": "zink",
    "som extraheerbare organische halogeenverbindingen": "AOX",
    "extraheerbaar organisch chloor": "AOX",
}

CROSSWALK_BEVINDING = (
    "PFOA komt in de Atlas niet voor als vergunde parameter. De opgenomen vergunningen dateren "
    "deels van vóór de aandacht voor deze stofgroep — kenmerken als DLB2006/8811 en "
    "DLB2007/10829 — terwijl PFOA juist de stof is waar de norm al overschreden wordt. "
    "Een register dat de ZZS niet kent, kan er ook niet op sturen."
)

# Eenheid → factor naar kilogram per jaar.
_VRACHT = {
    "kilogram per jaar": 1.0,
    "ton per jaar": 1000.0,
    "kilogram per dag": 365.0,
    "kilogram per week": 52.0,
}

# Eenheid → factor naar milligram per liter.
_CONCENTRATIE = {
    "milligram per liter": 1.0,
    "microgram per liter": 0.001,
}

# Eenheid → factor naar kubieke meter per uur. "kubieke met per etmaal" is een tikfout in de
# bron; hij staat er echt zo in, dus hij wordt hier ook zo herkend.
_DEBIET = {
    "kubieke meter per uur": 1.0,
    "kubieke meter per dag": 1 / 24,
    "kubieke met per etmaal": 1 / 24,
    "kubieke meter per etmaal": 1 / 24,
    "kubieke meter per week": 1 / 168,
    "kubieke meter per jaar": 1 / 8760,
    "kubieke meter per seconde": 3600.0,
}


def _norm(s) -> str:
    return (s or "").strip().lower()


def _debiet_m3_per_uur(voorschriften: list[dict]) -> float | None:
    for v in voorschriften:
        if _norm(v.get("parameter")) == "debiet" and v.get("waarde") is not None:
            factor = _DEBIET.get(_norm(v.get("eenheid")))
            if factor:
                return float(v["waarde"]) * factor
    return None


def _post(post: dict, telling: dict) -> dict:
    voors = post.get("voorschriften") or []
    debiet = _debiet_m3_per_uur(voors)
    vrachten, onbepaald = {}, []

    for v in voors:
        parameter, waarde, eenheid = v.get("parameter"), v.get("waarde"), _norm(v.get("eenheid"))
        if _norm(parameter) == "debiet":
            continue
        lab = CROSSWALK.get(_norm(parameter))
        if lab is None:
            telling["buiten_crosswalk"] += 1
            continue
        if waarde is None:
            onbepaald.append({"parameter": lab, "eenheid": v.get("eenheid"),
                              "reden": "geen waarde in de vergunning"})
            telling["onbepaald"] += 1
            continue

        if eenheid in _VRACHT:
            vrachten[lab] = vrachten.get(lab, 0.0) + float(waarde) * _VRACHT[eenheid]
            telling["vracht_direct"] += 1
        elif eenheid in _CONCENTRATIE:
            if debiet is None:
                onbepaald.append({"parameter": lab, "eenheid": v.get("eenheid"),
                                  "reden": "concentratie-eis zonder debiet-voorschrift; zonder "
                                           "debiet is de vracht niet te bepalen"})
                telling["onbepaald"] += 1
                continue
            mg_l = float(waarde) * _CONCENTRATIE[eenheid]
            vrachten[lab] = vrachten.get(lab, 0.0) + vracht_kg_jaar(debiet, mg_l)
            telling["vracht_uit_concentratie"] += 1
        else:
            onbepaald.append({"parameter": lab, "eenheid": v.get("eenheid"),
                              "reden": f"eenheid '{v.get('eenheid')}' is geen vracht en geen "
                                       "concentratie"})
            telling["onbepaald"] += 1

    return {"naam": post.get("naam"), "plaats": post.get("plaats"),
            "kenmerk": post.get("kenmerk"), "besluitdatum": post.get("besluitdatum"),
            "locatie": post.get("locatie"), "url": post.get("url"),
            "debiet_m3_per_uur": debiet, "vrachten": vrachten, "onbepaald": onbepaald}


def naar_register(posten: list[dict]) -> dict:
    """De Atlas-posten als register, in het formaat dat `ruimte.bereken()` verwacht."""
    telling = {"vestigingen": len(posten), "vracht_direct": 0, "vracht_uit_concentratie": 0,
               "onbepaald": 0, "buiten_crosswalk": 0}
    register = [_post(p, telling) for p in posten]
    return {"register": register, "telling": telling, "echt": True,
            "bevinding": CROSSWALK_BEVINDING,
            "bron": {"naam": "Atlas voor een Schone Maas",
                     "url": "https://atlas-smwk.hub.arcgis.com/",
                     "houder": "Schone Maaswaterketen",
                     "licentie": "publiek toegankelijk, geen expliciete licentie; live bevraagd "
                                 "met bronvermelding"}}
```

- [ ] **Step 4: Laat de rekensom voorberekende vrachten accepteren**

In `src/leefomgevinglab/usecases/gebruiksruimte/ruimte.py`, voeg boven `bereken` toe:

```python
def _vracht_van(post: dict, parameter: str) -> float:
    """De vracht van één vergunning voor één parameter.

    Het synthetische register geeft debiet + concentratie; de Atlas geeft soms rechtstreeks een
    vergunde vracht. Beide vormen komen hier binnen.
    """
    if "vrachten" in post:
        return post["vrachten"].get(parameter, 0.0)
    return vracht_kg_jaar(post["debiet_m3_per_uur"], post["concentraties"].get(parameter, 0.0))
```

en vervang in `bereken` de regel die `bijdragen` opbouwt (regel 26-27):

```python
        bijdragen = [(v["naam"], _vracht_van(v, naam)) for v in register]
```

- [ ] **Step 5: Leg vast dat beide registervormen werken**

Voeg toe aan `tests/test_gebruiksruimte.py`:

```python
def test_rekensom_verwerkt_zowel_concentratie_als_voorberekende_vracht():
    w = {"debiet_m3_s": 300.0, "parameters": [
        {"naam": "zink", "norm_mg_l": 0.0078, "achtergrond_mg_l": 0.0071, "zzs": False,
         "toelichting": "t"}]}
    voornemen = {"debiet_m3_per_uur": 100.0, "concentraties": {"zink": 0.001}}

    oud = [{"naam": "A", "debiet_m3_per_uur": 100.0, "concentraties": {"zink": 0.01}}]
    nieuw = [{"naam": "A", "vrachten": {"zink": ruimte.vracht_kg_jaar(100.0, 0.01)}}]

    a = ruimte.bereken(voornemen, oud, w)["parameters"][0]
    b = ruimte.bereken(voornemen, nieuw, w)["parameters"][0]
    assert a["vergund_kg_jaar"] == b["vergund_kg_jaar"]
```

Voeg bovenin `ruimte.py` `vracht_kg_jaar` toe aan de her-export zodat de test hem kan gebruiken — die import staat er al (`from .gebied import SECONDEN_PER_JAAR, vracht_kg_jaar`), dus dit werkt zonder wijziging.

- [ ] **Step 6: Draai de tests en zie ze slagen**

Run: `.venv/bin/python -m pytest tests/test_atlas_register.py tests/test_gebruiksruimte.py -v`
Expected: PASS — alle nieuwe tests plus de bestaande gebruiksruimte-tests

- [ ] **Step 7: Commit**

```bash
git add src/leefomgevinglab/usecases/gebruiksruimte/ tests/test_atlas_register.py tests/test_gebruiksruimte.py
git commit -m "feat(llab): Atlas-vergunningen omgerekend naar vrachten, in drie eerlijke lagen

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>"
```

---

### Task 8: De motor werkt op een punt

**Files:**
- Modify: `src/leefomgevinglab/usecases/gebruiksruimte/service.py`
- Modify: `src/leefomgevinglab/usecases/gebruiksruimte/gebied.py` (`REGISTER` krijgt `owl_id`)
- Test: `tests/test_gebruiksruimte.py` (uitbreiden)

**Interfaces:**
- Consumes: `waterprofiel.profiel/als_waterlichaam` (Task 5), `atlas_register.naar_register` (Task 7), `bronnen.contextset` (Task 4)
- Produces: `beeld_op_punt(x, y, debiet_m3_per_uur=420, live=True, naam=None, _haal_regels=None, _haal_water=None, _haal_atlas=None) -> dict`; `beeld(locatie_id, …)` blijft bestaan als wrapper

- [ ] **Step 1: Leg het huidige gedrag vast vóór de refactor**

Dit is een karakteriseringstest: hij moet **nu al** slagen, en ná de refactor nog steeds.
Voeg toe aan `tests/test_gebruiksruimte.py`:

```python
def test_beeld_op_vaste_locatie_blijft_hetzelfde_na_de_refactor():
    """Karakterisering: /gebruiksruimte mag door de refactor niet stilletjes veranderen."""
    b = service.beeld("deventer", debiet_m3_per_uur=420, live=False)
    assert b["locatie"]["gemeente"] == "Deventer"
    assert b["locatie"]["rd"] == [206800.0, 474000.0]
    assert b["water"]["naam"] == "IJssel"
    assert b["water"]["debiet_m3_s"] == 300.0
    assert [p["naam"] for p in b["ruimte"]["parameters"]] == [
        "stikstof totaal", "zink", "AOX", "PFOA"]
    assert b["ruimte"]["conclusie"]["antwoord"] == "nee, tenzij"
    assert b["ruimte"]["conclusie"]["bepalend"] == "PFOA"
    assert len(b["register"]) == 5
    assert b["max_debiet"] == 20000
    assert len(b["informatiefuncties"]) == 5
```

- [ ] **Step 2: Draai hem en zie hem NU al slagen**

Run: `.venv/bin/python -m pytest tests/test_gebruiksruimte.py::test_beeld_op_vaste_locatie_blijft_hetzelfde_na_de_refactor -v`
Expected: PASS — dit legt het bestaande gedrag vast. Faalt hij, pas dan de verwachtingen aan
aan wat de code nú doet (niet de code aan de test).

- [ ] **Step 3: Schrijf de test voor het nieuwe gedrag**

Voeg toe aan `tests/test_gebruiksruimte.py`:

```python
_KRW_MAAS = """{"features":[{"properties":{
    "naam":"Maas","owl_id":"NL91_MAAS","sgd_id":"NLMS","gebtype":"R",
    "owltype":"R7","owlcat":"1","owlstat":"Sterk veranderd",
    "wbhnaam":"Ministerie van Infrastructuur en Waterstaat (Rijkswaterstaat)",
    "wbhcode":"NL_MINIW","omvang":210.0,"eenheid":"km2","gemdiepte":5.0}}]}"""
_GEM_MAASTRICHT = """{"features":[{"properties":{"naam":"Maastricht","ligtInProvincieNaam":"Limburg"}}]}"""
_GEEN = '{"features":[]}'


def _haal_reeks(antwoorden):
    it = iter(antwoorden)

    def haal(url, params, timeout_s=25.0):
        return next(it)
    return haal


def _atlas_maastricht(x, y, straal_m):
    return [{"kenmerk": "RWS-2015/38632", "naam": "Lawter Maastricht BV", "plaats": "Maastricht",
             "locatie": None, "url": None, "besluitdatum": "2015-01-01",
             "voorschriften": [
                 {"parameter": "zink", "waarde": 0.3, "eenheid": "milligram per liter",
                  "bemonstering": None, "rd": [x, y]},
                 {"parameter": "Debiet", "waarde": 25.0, "eenheid": "kubieke meter per uur",
                  "bemonstering": None, "rd": [x, y]}]}]


def test_prik_op_de_maas_gebruikt_echte_vergunningen():
    b = service.beeld_op_punt(177748.0, 321314.0, live=True,
                              _haal_water=_haal_reeks([_KRW_MAAS, _GEM_MAASTRICHT]),
                              _haal_regels=lambda rd: [],
                              _haal_atlas=_atlas_maastricht)
    assert b["water"]["naam"] == "Maas"
    assert b["register_bron"]["echt"] is True
    assert b["register"][0]["kenmerk"] == "RWS-2015/38632"
    assert b["ruimte"]["parameters"], "de rekensom draait ook op de Maas"


def test_prik_buiten_het_maasstroomgebied_valt_terug_op_synthetisch():
    b = service.beeld_op_punt(206800.0, 474000.0, live=True,
                              _haal_water=_haal_reeks([_KRW_MAAS, _GEM_MAASTRICHT]),
                              _haal_regels=lambda rd: [],
                              _haal_atlas=lambda x, y, straal_m: [])
    assert b["register_bron"]["echt"] is False
    assert b["register_bron"]["reden"]


def test_prik_zonder_rijkswater_geeft_geen_rekensom_maar_wel_een_antwoord():
    b = service.beeld_op_punt(150000.0, 400000.0, live=True,
                              _haal_water=_haal_reeks([_GEEN, _GEEN, _GEM_MAASTRICHT]),
                              _haal_regels=lambda rd: [],
                              _haal_atlas=lambda x, y, straal_m: [])
    assert b["rijkswater"] is False
    assert b["ruimte"] is None
    assert b["geen_ruimte_reden"]
    assert "waterschap" in b["bevoegd_gezag"]["lozingsactiviteit"]


def test_atlas_storing_laat_de_rest_van_het_beeld_staan():
    def stuk(x, y, straal_m):
        raise RuntimeError("Atlas plat")

    b = service.beeld_op_punt(177748.0, 321314.0, live=True,
                              _haal_water=_haal_reeks([_KRW_MAAS, _GEM_MAASTRICHT]),
                              _haal_regels=lambda rd: [], _haal_atlas=stuk)
    assert b["water"]["naam"] == "Maas"
    assert b["register_bron"]["status"] == "onbereikbaar"
    assert b["ruimte"] is not None
```

- [ ] **Step 4: Draai de nieuwe tests en zie ze falen**

Run: `.venv/bin/python -m pytest tests/test_gebruiksruimte.py -k "prik or atlas_storing" -v`
Expected: FAIL — `AttributeError: module … has no attribute 'beeld_op_punt'`

- [ ] **Step 5: Geef het synthetische register zijn waterlichaam**

In `src/leefomgevinglab/usecases/gebruiksruimte/gebied.py`, voeg aan elke post in `REGISTER`
de sleutel `"owl_id": "NL93_IJSSEL"` toe, en pas de docstring boven `REGISTER` aan:

```python
# Het register dat niet bestaat: bestaande lozingsvergunningen op ditzelfde waterlichaam.
# Verzonnen bedrijven; concentraties in mg/l op het lozingspunt. Alleen van toepassing op de
# IJssel — buiten het Maasstroomgebied is er geen echt register om op terug te vallen.
```

- [ ] **Step 6: Schrijf de motor**

Herschrijf `src/leefomgevinglab/usecases/gebruiksruimte/service.py` — vervang `beeld()` door:

```python
def _atlas_standaard(x: float, y: float, straal_m: int):
    """De echte Atlas-bevraging; los gehouden zodat de tests hem kunnen vervangen."""
    from leefomgevinglab.connectors.smwk_atlas import SmwkAtlasConnector
    from leefomgevinglab.geluidsmeter.config import load_config
    cfg = load_config().get("leefomgevinglab", {})
    at = cfg.get("smwk_atlas", {})
    c = SmwkAtlasConnector(cache_dir=cfg.get("cache_dir", "/tmp/llab_cache"),
                           cache_ttl=at.get("cache_ttl_s", 86400),
                           base_url=at.get("base_url") or None)
    return c.vergunningen_bij_punt(x, y, straal_m=straal_m)


def _register(x, y, owl_id, straal_m, live, haal) -> tuple[list, dict]:
    """Echte vergunningen waar ze bestaan, synthetische waar dat niet zo is."""
    if not live:
        return list(gebied.REGISTER), {
            "echt": False, "status": "overgeslagen",
            "reden": "zonder live-modus wordt de Atlas niet bevraagd",
            "bron": {"naam": "synthetisch register van dit lab"}}
    try:
        posten = (haal or _atlas_standaard)(x, y, straal_m)
    except Exception as exc:
        return list(gebied.REGISTER), {
            "echt": False, "status": "onbereikbaar", "fout": type(exc).__name__,
            "reden": "de Atlas was niet bereikbaar; teruggevallen op het synthetische register",
            "bron": {"naam": "synthetisch register van dit lab"}}

    if posten:
        d = atlas_register.naar_register(posten)
        return d["register"], {"echt": True, "status": "ok", "telling": d["telling"],
                               "bevinding": d["bevinding"], "bron": d["bron"]}

    if owl_id == "NL93_IJSSEL":
        return list(gebied.REGISTER), {
            "echt": False, "status": "ok",
            "reden": "geen vergunningen in de Atlas: die dekt alleen het Maasstroomgebied. Voor "
                     "de IJssel valt dit lab terug op een synthetisch register — precies het gat "
                     "dat een landelijk register zou vullen.",
            "bron": {"naam": "synthetisch register van dit lab"}}

    return [], {"echt": False, "status": "ok",
                "reden": "geen register voor dit waterlichaam. Buiten het Maasstroomgebied "
                         "bestaat er geen overzicht van wie hier al loost.",
                "bron": {"naam": "geen"}}


def beeld_op_punt(x: float, y: float, debiet_m3_per_uur: float = 420, live: bool = True,
                  naam: str | None = None, straal_m: int = 5000,
                  _haal_regels=None, _haal_water=None, _haal_atlas=None) -> dict:
    """Alles bij elkaar op één punt: waar ben ik, wat geldt hier, wat ligt er al, wat kan er nog?"""
    water = water_bronnen.contextset(x, y, straal_m=1000, live=live, haal=_haal_water)
    rijkswater = bool(water.get("rijkswater")) if live else True
    r = regels.regels_op_locatie(x, y, rijkswater=rijkswater, live=live, _haal=_haal_regels)
    v = voornemen(debiet_m3_per_uur)

    p = waterprofiel.profiel(water)
    register, register_bron = _register(x, y, water.get("owl_id"), straal_m, live, _haal_atlas)

    if p.get("afgeleid"):
        u = ruimte.bereken(v, register, waterprofiel.als_waterlichaam(p))
        geen_ruimte_reden = None
    else:
        u = None
        geen_ruimte_reden = p.get("reden")

    return {
        "locatie": {"naam": naam or "gekozen punt", "rd": [x, y],
                    "gemeente": water.get("gemeente"), "provincie": water.get("provincie")},
        "water": {**p["echt"], "profiel": p, "live": water},
        "rijkswater": rijkswater,
        "bevoegd_gezag": water_bronnen.bevoegd_gezag(water),
        "regels": r,
        "register": register,
        "register_bron": register_bron,
        "voornemen": v,
        "ruimte": u,
        "geen_ruimte_reden": geen_ruimte_reden,
        "informatiefuncties": INFORMATIEFUNCTIES,
        "max_debiet": MAX_DEBIET,
        "verantwoording": VERANTWOORDING,
    }


def beeld(locatie_id: str, debiet_m3_per_uur: float = 420, live: bool = True,
          _haal_regels=None, _haal_water=None) -> dict:
    """De gecureerde drieluik-variant: een vaste locatie aan de IJssel.

    Dunne wrapper om `beeld_op_punt`, met het vaste IJssel-waterlichaam en -register in plaats
    van een afgeleid profiel — zodat /gebruiksruimte precies blijft antwoorden wat hij altijd al
    antwoordde.
    """
    loc = gebied.LOCATIES[locatie_id]                 # KeyError bij onbekende locatie: luid falen
    x, y = loc["rd"]

    water = water_bronnen.contextset(x, y, straal_m=1000, live=live, haal=_haal_water)
    rijkswater = bool(water.get("rijkswater")) if live else True
    r = regels.regels_op_locatie(x, y, rijkswater=rijkswater, live=live, _haal=_haal_regels)
    v = voornemen(debiet_m3_per_uur)
    u = ruimte.bereken(v, gebied.REGISTER, gebied.WATERLICHAAM)

    return {
        "locatie": {**loc, "rd": list(loc["rd"])},
        "water": {**gebied.WATERLICHAAM, "live": water},
        "rijkswater": rijkswater,
        "bevoegd_gezag": water_bronnen.bevoegd_gezag(water),
        "regels": r,
        "register": gebied.REGISTER,
        "voornemen": v,
        "ruimte": u,
        "informatiefuncties": INFORMATIEFUNCTIES,
        "locaties": list(gebied.LOCATIES.values()),
        "max_debiet": MAX_DEBIET,
        "verantwoording": VERANTWOORDING,
    }
```

Voeg bovenaan `service.py` toe aan de imports:

```python
from . import atlas_register, gebied, regels, ruimte, waterprofiel
```

en hernoem de bestaande inline-verantwoording tot een constante:

```python
VERANTWOORDING = ("Regelingen live uit het DSO. Het register met bestaande vergunningen bestaat "
                  "landelijk niet; voor het Maasstroomgebied komt het live uit de Atlas voor een "
                  "Schone Maas, daarbuiten is het synthetisch. Normen en achtergrondconcentraties "
                  "zijn illustratief. Het mechanisme is echt, de cijfers niet.")
```

- [ ] **Step 7: Draai alle gebruiksruimte-tests**

Run: `.venv/bin/python -m pytest tests/test_gebruiksruimte.py -v`
Expected: PASS — inclusief de karakteriseringstest uit Step 1, ongewijzigd

- [ ] **Step 8: Commit**

```bash
git add src/leefomgevinglab/usecases/gebruiksruimte/ tests/test_gebruiksruimte.py
git commit -m "feat(llab): gebruiksruimte-motor werkt op een willekeurig punt

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>"
```

---

### Task 9: Het endpoint `/api/waterruimte`

**Files:**
- Modify: `src/leefomgevinglab/geluidsmeter/api.py`
- Modify: `src/leefomgevinglab/usecases/gebruiksruimte/service.py` (parallelle bevraging)
- Test: `tests/test_api_waterruimte.py`

**Interfaces:**
- Consumes: `service.beeld_op_punt()` uit Task 8
- Produces: route `GET /api/waterruimte?x=&y=&debiet=&live=`, route `GET /waterruimte`

- [ ] **Step 1: Schrijf de falende test**

Maak `tests/test_api_waterruimte.py`:

```python
from fastapi.testclient import TestClient

import leefomgevinglab.geluidsmeter.api as api


def _client(monkeypatch):
    monkeypatch.setattr(api, "load_config", lambda *a, **k: api._config)
    return TestClient(api.app)


def test_prik_zonder_live_geeft_een_reproduceerbaar_antwoord(monkeypatch):
    r = _client(monkeypatch).get("/api/waterruimte?x=206800&y=474000&live=0")
    assert r.status_code == 200
    d = r.json()
    assert d["locatie"]["rd"] == [206800.0, 474000.0]
    assert d["regels"]["status"] == "overgeslagen"


def test_coordinaten_buiten_nederland_geven_400(monkeypatch):
    c = _client(monkeypatch)
    for x, y in [(-50000, 400000), (400000, 400000), (150000, 200000), (150000, 700000)]:
        r = c.get(f"/api/waterruimte?x={x}&y={y}&live=0")
        assert r.status_code == 400, f"({x},{y}) had geweigerd moeten worden"
        assert "rd" in r.json()["detail"].lower()


def test_debiet_wordt_begrensd(monkeypatch):
    d = _client(monkeypatch).get("/api/waterruimte?x=206800&y=474000&debiet=999999&live=0").json()
    assert d["voornemen"]["debiet_m3_per_uur"] == d["max_debiet"]


def test_ontbrekende_coordinaten_geven_422(monkeypatch):
    assert _client(monkeypatch).get("/api/waterruimte").status_code == 422


def test_kaartpagina_geeft_200_met_de_subnav(monkeypatch):
    r = _client(monkeypatch).get("/waterruimte")
    assert r.status_code == 200
    assert 'class="waternav"' in r.text
    assert r.text.count('aria-current="page"') == 1
    assert "/api/waterruimte" in r.text
```

- [ ] **Step 2: Draai de test en zie hem falen**

Run: `.venv/bin/python -m pytest tests/test_api_waterruimte.py -v`
Expected: FAIL — 404 op beide routes

- [ ] **Step 3: Voeg de routes toe**

In `api.py`, direct ná `api_gebruiksruimte`:

```python
# Ruime RD-bbox rond Nederland inclusief Noordzee-deel; daarbuiten is een prik een tikfout.
_RD_GRENZEN = (-7000.0, 300000.0, 289000.0, 629000.0)


@app.get("/waterruimte", response_class=HTMLResponse)
def waterruimte_page():
    return _waterpagina("waterruimte.html", "kaart")


@app.get("/api/waterruimte")
def api_waterruimte(x: float, y: float, debiet: float = 420, live: int = 1):
    """Wat kan hier nog, op dit punt? Regels en water live; vergunningen echt waar ze bestaan."""
    xmin, ymin, xmax, ymax = _RD_GRENZEN
    if not (xmin <= x <= xmax and ymin <= y <= ymax):
        raise HTTPException(status_code=400,
                            detail=f"RD-coördinaat buiten Nederland: ({x}, {y})")
    ll = _config.get("leefomgevinglab", {})
    straal = ll.get("smwk_atlas", {}).get("straal_m", 5000)
    return gebruiksruimte_service.beeld_op_punt(x, y, debiet_m3_per_uur=debiet,
                                                live=bool(live), straal_m=straal)
```

- [ ] **Step 4: Maak de bevraging parallel**

In `service.py`, vervang in `beeld_op_punt` de drie opeenvolgende aanroepen door een
`ThreadPoolExecutor` — hetzelfde patroon als `evruimte/service.py:71`. Voeg bovenaan toe:

```python
from concurrent.futures import ThreadPoolExecutor
```

en in `beeld_op_punt`, vóór het gebruik van `water`, `r` en `register`:

```python
    # Drie sporen die niets van elkaar nodig hebben; serieel zou elke prik seconden kosten.
    # De regels hebben `rijkswater` alleen nodig voor hun duiding, niet voor de bevraging —
    # die wordt achteraf gecorrigeerd.
    with ThreadPoolExecutor(max_workers=3) as pool:
        f_water = pool.submit(water_bronnen.contextset, x, y, straal_m=1000, live=live,
                              haal=_haal_water)
        f_regels = pool.submit(regels.regels_op_locatie, x, y, rijkswater=True, live=live,
                               _haal=_haal_regels)
        water = f_water.result()
        rijkswater = bool(water.get("rijkswater")) if live else True
        f_reg = pool.submit(_register, x, y, water.get("owl_id"), straal_m, live, _haal_atlas)
        r = f_regels.result()
        register, register_bron = f_reg.result()

    if not rijkswater:
        # De duiding van de waterschapsverordening kantelt op regionaal water; opnieuw duiden
        # is goedkoop (geen netwerk) en houdt de bevraging parallel.
        r["regelingen"] = [regels.duiding({"titel": g["titel"], "type": g["type"],
                                           "bevoegd_gezag": g["bevoegd_gezag"]}, rijkswater)
                           for g in r.get("regelingen", [])]
```

Verwijder de oorspronkelijke seriële regels voor `water`, `rijkswater`, `r` en de aanroep van
`_register` verderop in de functie.

- [ ] **Step 5: Draai de tests en zie ze slagen**

Run: `.venv/bin/python -m pytest tests/test_api_waterruimte.py tests/test_gebruiksruimte.py -v`
Expected: PASS — de kaartpagina-test faalt nog (`waterruimte.html` bestaat niet); die komt in
Task 10. Markeer hem tot dan met `@pytest.mark.xfail(reason="pagina volgt in Task 10")`.

- [ ] **Step 6: Commit**

```bash
git add src/leefomgevinglab/geluidsmeter/api.py src/leefomgevinglab/usecases/gebruiksruimte/service.py tests/test_api_waterruimte.py
git commit -m "feat(llab): /api/waterruimte — wat kan hier nog op een willekeurig punt

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>"
```

---

### Task 10: De kaart

**Files:**
- Create: `src/leefomgevinglab/static/waterruimte.html`
- Modify: `tests/test_api_waterruimte.py` (xfail-markering weghalen)

**Interfaces:**
- Consumes: `GET /api/waterruimte` uit Task 9
- Produces: de pagina op `/waterruimte`

- [ ] **Step 1: Haal de xfail weg**

Verwijder in `tests/test_api_waterruimte.py` de `@pytest.mark.xfail` boven
`test_kaartpagina_geeft_200_met_de_subnav`.

- [ ] **Step 2: Draai en zie hem falen**

Run: `.venv/bin/python -m pytest tests/test_api_waterruimte.py::test_kaartpagina_geeft_200_met_de_subnav -v`
Expected: FAIL — `FileNotFoundError: … waterruimte.html`

- [ ] **Step 3: Schrijf de pagina**

Maak `src/leefomgevinglab/static/waterruimte.html`. Neem `static/evruimte.html` als vertrekpunt
(zelfde maplibre-versie, zelfde donkere thema, zelfde popup-stijl) en pas aan:

```html
<!DOCTYPE html>
<html lang="nl">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>Wat kan hier nog? — LeefomgevingLab</title>
  <link href="https://unpkg.com/maplibre-gl@4.7.1/dist/maplibre-gl.css" rel="stylesheet" />
  <script src="https://unpkg.com/maplibre-gl@4.7.1/dist/maplibre-gl.js"></script>
  <script src="https://unpkg.com/proj4@2.12.1/dist/proj4.js"></script>
  <style>
    /* Neem de :root-variabelen, header-, .waternav- en popup-stijl over uit evruimte.html. */
    body { margin:0; background:var(--bg); color:var(--tekst);
           font:15px/1.6 system-ui,-apple-system,"Segoe UI",sans-serif; }
    .kolommen { display:flex; height:calc(100vh - 110px); }
    #map { flex:1; }
    aside { width:400px; overflow-y:auto; background:var(--paneel);
            border-left:1px solid var(--border); padding:16px; }
    .snel { display:flex; gap:6px; flex-wrap:wrap; padding:10px 20px;
            border-bottom:1px solid var(--border); align-items:center; }
    .snel button { background:#12283f; color:var(--tekst); border:1px solid var(--border);
                   border-radius:6px; padding:5px 11px; font-size:12.5px; cursor:pointer; }
    .snel button:hover { border-color:var(--accent); }
    .hint { color:var(--dim); font-size:12px; margin-left:auto; }
    .blok { border:1px solid var(--border); border-radius:8px; padding:12px; margin-bottom:12px; }
    .blok h4 { margin:0 0 8px; font-size:13px; text-transform:uppercase; letter-spacing:.05em;
               color:var(--dim); }
    .merk { font-size:10.5px; padding:2px 7px; border-radius:9px; border:1px solid var(--border); }
    .merk.echt { color:var(--accent); border-color:#1d5c43; }
    .merk.syn { color:#e8b84b; border-color:#5c4a1d; }
    .balk { height:7px; background:#12283f; border-radius:4px; overflow:hidden; margin:4px 0 2px; }
    .balk i { display:block; height:100%; background:var(--accent); }
    .balk i.vol { background:#e8734b; }
    table { width:100%; border-collapse:collapse; font-size:12.5px; }
    td, th { padding:4px 3px; border-bottom:1px solid var(--border); text-align:left; }
    .dim { color:var(--dim); font-size:12px; }
  </style>
</head>
<body>
  <header>
    <div class="mark"></div><h1>LeefomgevingLab</h1><span class="badge">prik op de kaart</span>
    <nav><a href="/">Home</a><a href="/water">Waterdossier</a></nav>
  </header>
  __WATERNAV__

  <div class="snel">
    <button data-x="177748" data-y="321314">Maastricht — echte vergunningen</button>
    <button data-x="206800" data-y="474000">Deventer — synthetisch register</button>
    <button data-x="150000" data-y="400000">regionaal water</button>
    <label class="hint">debiet
      <input id="debiet" type="range" min="1" max="20000" value="420" step="1" />
      <b id="debiet-uit">420</b> m³/u
    </label>
    <span class="hint">klik op de kaart om ergens anders te prikken</span>
  </div>

  <div class="kolommen">
    <div id="map"></div>
    <aside id="paneel"><p class="dim">Kies een punt op de kaart.</p></aside>
  </div>

  <script>
    proj4.defs("EPSG:28992",
      "+proj=sterea +lat_0=52.1561605555556 +lon_0=5.38763888888889 +k=0.9999079 " +
      "+x_0=155000 +y_0=463000 +ellps=bessel " +
      "+towgs84=565.417,50.3319,465.552,-0.398957,0.343988,-1.8774,4.0725 +units=m +no_defs");
    const naarRD = (lon, lat) => proj4("EPSG:4326", "EPSG:28992", [lon, lat]);
    const naarWGS = (x, y) => proj4("EPSG:28992", "EPSG:4326", [x, y]);
    const esc = s => String(s ?? "").replace(/[&<>"]/g, c =>
      ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'}[c]));
    const getal = (n, d = 1) => n === null || n === undefined ? "—" : Number(n).toFixed(d);

    const map = new maplibregl.Map({
      container: "map",
      style: "https://basemaps.cartocdn.com/gl/dark-matter-gl-style/style.json",
      center: [5.7, 52.0], zoom: 6.6,
    });
    map.addControl(new maplibregl.NavigationControl(), "top-right");

    let marker = null;
    const debiet = document.getElementById("debiet");
    const debietUit = document.getElementById("debiet-uit");
    let laatste = null;

    debiet.addEventListener("input", () => { debietUit.textContent = debiet.value; });
    debiet.addEventListener("change", () => { if (laatste) prik(laatste[0], laatste[1]); });

    map.on("click", e => {
      const [x, y] = naarRD(e.lngLat.lng, e.lngLat.lat);
      prik(Math.round(x), Math.round(y));
    });

    document.querySelectorAll(".snel button").forEach(b =>
      b.addEventListener("click", () => prik(+b.dataset.x, +b.dataset.y)));

    function prik(x, y) {
      laatste = [x, y];
      const [lon, lat] = naarWGS(x, y);
      if (marker) marker.remove();
      marker = new maplibregl.Marker({ color: "#2ecc8f" }).setLngLat([lon, lat]).addTo(map);
      document.getElementById("paneel").innerHTML = '<p class="dim">Bezig met ophalen…</p>';
      fetch(`/api/waterruimte?x=${x}&y=${y}&debiet=${debiet.value}&live=1`)
        .then(r => r.ok ? r.json() : r.json().then(d => Promise.reject(d.detail)))
        .then(toon)
        .catch(msg => {
          document.getElementById("paneel").innerHTML =
            `<p class="dim">Niet gelukt: ${esc(msg)}</p>`;
        });
    }

    function toon(d) {
      const bg = d.bevoegd_gezag || {};
      const water = d.water || {};
      const herkomst = (water.profiel && water.profiel.herkomst) || {};

      let h = `<div class="blok"><h4>Waar</h4>
        <p style="margin:0"><b>${esc(water.naam || "geen rijkswaterlichaam")}</b>
        ${water.owl_id ? `<span class="dim">(${esc(water.owl_id)})</span>` : ""}<br>
        <span class="dim">${esc(d.locatie.gemeente)} · ${esc(d.locatie.provincie)} ·
        RD ${d.locatie.rd[0]}, ${d.locatie.rd[1]}</span></p>
        <p style="margin:8px 0 0;font-size:13px">Bevoegd gezag lozing:
        <b>${esc(bg.lozingsactiviteit)}</b><br>
        <span class="dim">${esc(bg.bron_beheerder)}</span></p></div>`;

      const t = (d.regels && d.regels.telling) || {};
      h += `<div class="blok"><h4>Wat hier geldt</h4>
        <p class="dim" style="margin:0 0 6px">${esc(d.regels.bron)} —
        ${Object.entries(t).map(([k, v]) => `${v} ${esc(k)}`).join(", ") || "geen regelingen"}</p>
        ${(d.regels.regelingen || []).slice(0, 8).map(g =>
          `<div style="margin-bottom:6px;font-size:12.5px">
             <b>${esc(g.titel)}</b>
             <span class="merk">${esc(g.werking)}</span>
             ${g.van_toepassing ? "" : '<span class="merk syn">raakt dit niet</span>'}
           </div>`).join("")}</div>`;

      const rb = d.register_bron || {};
      h += `<div class="blok"><h4>Wat er al ligt
        <span class="merk ${rb.echt ? "echt" : "syn"}">${rb.echt ? "echt" : "synthetisch"}</span>
        </h4>
        <p class="dim" style="margin:0 0 6px">${esc((rb.bron && rb.bron.naam) || "")}
        ${rb.reden ? "— " + esc(rb.reden) : ""}</p>
        ${(d.register || []).slice(0, 8).map(v =>
          `<div style="font-size:12.5px;margin-bottom:4px">${esc(v.naam)}
             <span class="dim">${esc(v.kenmerk || v.plaats || "")}</span></div>`).join("")
          || '<p class="dim" style="margin:0">Geen bekende vergunningen.</p>'}
        ${rb.telling ? `<p class="dim" style="margin:8px 0 0">
          ${rb.telling.vracht_direct} vracht rechtstreeks vergund,
          ${rb.telling.vracht_uit_concentratie} berekend uit concentratie × debiet,
          ${rb.telling.onbepaald} niet af te leiden.</p>` : ""}
        ${rb.bevinding ? `<p class="dim" style="margin:6px 0 0">${esc(rb.bevinding)}</p>` : ""}
        </div>`;

      if (!d.ruimte) {
        h += `<div class="blok"><h4>Wat er nog kan</h4>
          <p style="margin:0">${esc(d.geen_ruimte_reden)}</p></div>`;
      } else {
        const c = d.ruimte.conclusie;
        h += `<div class="blok"><h4>Wat er nog kan</h4>
          <p style="margin:0 0 8px"><b>${esc(c.antwoord)}</b> — ${esc(c.waarom)}</p>
          <table><tr><th>parameter</th><th>vrij</th><th>gevraagd</th><th></th></tr>
          ${d.ruimte.parameters.map(p => {
            const pct = p.benutting_pct === null ? 0 : Math.min(p.benutting_pct, 100);
            return `<tr><td>${esc(p.naam)}${p.zzs ? ' <span class="merk syn">ZZS</span>' : ""}
              <div class="balk"><i class="${p.oordeel === "past" ? "" : "vol"}"
                style="width:${pct}%"></i></div></td>
              <td>${getal(p.vrij_kg_jaar)}</td><td>${getal(p.gevraagd_kg_jaar, 2)}</td>
              <td>${esc(p.oordeel)}</td></tr>`;
          }).join("")}</table>
          <p class="dim" style="margin:8px 0 0">Debiet waterlichaam
            ${getal(d.ruimte.debiet_waterlichaam_m3_s)} m³/s —
            ${esc(herkomst.debiet_m3_s || "")}</p>
          <p class="dim" style="margin:4px 0 0">${esc(herkomst.parameters || "")}</p>
          </div>`;
      }

      h += `<p class="dim">${esc(d.verantwoording)}</p>`;
      document.getElementById("paneel").innerHTML = h;
    }

    prik(177748, 321314);
  </script>
</body>
</html>
```

- [ ] **Step 4: Draai de tests en zie ze slagen**

Run: `.venv/bin/python -m pytest tests/test_api_waterruimte.py -v`
Expected: PASS — 5 passed

- [ ] **Step 5: Commit**

```bash
git add src/leefomgevinglab/static/waterruimte.html tests/test_api_waterruimte.py
git commit -m "feat(llab): prik-op-de-kaart voor de gebruiksruimte op het water

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>"
```

---

### Task 11: Live verifiëren en vastleggen

**Files:**
- Create: `tests/test_atlas_live.py`
- Modify: `CLAUDE.md` (sprintstatus)
- Test: de hele suite

**Interfaces:**
- Consumes: alles uit Task 1-10
- Produces: geen nieuwe symbolen

- [ ] **Step 1: Schrijf de live-test**

Maak `tests/test_atlas_live.py` (patroon van `tests/test_ev_live.py`):

```python
"""Live smoke tegen de Atlas voor een Schone Maas. Skipt zonder live-test-vlag.

De Atlas vraagt zelf geen sleutel; DSO_API_KEY is in deze repo de generieke vlag die
live-tests aanzet — test_ev_live.py doet hetzelfde voor de REV-WFS.
"""
import os
import pytest

from leefomgevinglab.connectors.smwk_atlas import SmwkAtlasConnector

pytestmark = pytest.mark.skipif(not os.environ.get("DSO_API_KEY"),
                                reason="live-tests uit (DSO_API_KEY niet gezet)")


def test_maastricht_geeft_echte_vergunningen(tmp_path):
    c = SmwkAtlasConnector(cache_dir=str(tmp_path))
    uit = c.vergunningen_bij_punt(177748.0, 321314.0, straal_m=5000)
    assert len(uit) >= 5, "verwacht ~11 vestigingen bij Maastricht"
    assert any(v["voorschriften"] for v in uit)
    assert all(v["kenmerk"] for v in uit)


def test_deventer_ligt_buiten_het_maasstroomgebied(tmp_path):
    c = SmwkAtlasConnector(cache_dir=str(tmp_path))
    assert c.vergunningen_bij_punt(206800.0, 474000.0, straal_m=5000) == []


def test_de_velden_uit_de_spec_bestaan_nog(tmp_path):
    """Faalt luid als de Atlas zijn schema wijzigt."""
    c = SmwkAtlasConnector(cache_dir=str(tmp_path))
    uit = c.vergunningen_bij_punt(177748.0, 321314.0, straal_m=5000)
    v = next(v for v in uit if v["voorschriften"])["voorschriften"][0]
    assert {"parameter", "waarde", "eenheid"} <= set(v)
```

Geen markerregistratie nodig: deze repo kent geen pytest-markers en gebruikt `skipif` op
`DSO_API_KEY`. Zonder die variabele slaat de suite het bestand gewoon over.

- [ ] **Step 2: Draai de live-test**

Run: `.venv/bin/python -m pytest tests/test_atlas_live.py -v`
Expected: 3 passed met netwerk én `DSO_API_KEY` gezet (die staat in `.env`, dus draai zo
nodig `set -a && . .env && set +a` eerst); anders 3 skipped. Faalt hij op bereikbaarheid,
noteer dat en ga door — de gewone suite mag er niet van afhangen.

- [ ] **Step 3: Draai de hele suite**

Run: `.venv/bin/python -m pytest -q`
Expected: PASS — geen nieuwe failures ten opzichte van de nulmeting vóór Task 1

- [ ] **Step 4: Verifieer live in de draaiende dienst**

```bash
sudo systemctl restart leefomgevinglab-api
sleep 3
for pad in /water /waterruimte /gebruiksruimte /lozing /balo /dvth; do
  printf "%-16s %s\n" "$pad" "$(curl -s -o /dev/null -w '%{http_code}' http://localhost:8792$pad)"
done
curl -s "http://localhost:8792/api/waterruimte?x=177748&y=321314&live=1" \
  | python3 -c "import sys,json; d=json.load(sys.stdin); \
    print(d['water']['naam'], '|', d['register_bron']['echt'], '|', len(d['register']), 'posten')"
curl -s "http://localhost:8792/api/waterruimte?x=206800&y=474000&live=1" \
  | python3 -c "import sys,json; d=json.load(sys.stdin); \
    print(d['water']['naam'], '|', d['register_bron']['echt'], '|', d['register_bron']['reden'][:60])"
```

Expected: zes keer `200`; Maastricht geeft `Maas | True | ≥5 posten`; Deventer geeft
`IJssel | False | geen vergunningen in de Atlas…`

- [ ] **Step 5: Werk `CLAUDE.md` bij**

Voeg onder "Sprint status" toe, ná de `/begrippen`-regel:

```markdown
- ✅ **Waterdossier (`/water`, `/api/water/hub`):** de vier waterpagina's (`/lozing`,
  `/gebruiksruimte`, `/waterruimte`, `/balo`) als één dossier met een gedeelde subnav-balk.
  `usecases/water_hub.py` is de enige plek waar staat wat het dossier is; de balk wordt eruit
  gegenereerd en via een `__WATERNAV__`-placeholder geïnjecteerd (zelfde truc als `__DOSSIER__`
  in `_keten_tab`). NB: `keten-tab.html` bedient óók `/dvth` — daar wordt de placeholder leeg
  vervangen, want dat is geen waterpagina.
- ✅ **Prik op de kaart (`/waterruimte`, `/api/waterruimte?x=&y=&debiet=&live=`):** "wat kan hier
  nog" op een willekeurig RD-punt. `waterprofiel.py` maakt van een KRW-feature een profiel met
  echt (naam, `owl_id`, `wbhnaam`, `owltype`, `owlcat`, `owlstat`, omvang, `gemdiepte`) strikt
  gescheiden van afgeleid (debiet, achtergrondconcentraties) — elk afgeleid veld draagt een
  herkomstregel. **Het register is echt waar het bestaat:** de Atlas voor een Schone Maas
  (`connectors/smwk_atlas.py`) levert voor het Maasstroomgebied 72 vestigingen en 782 vergunde
  voorschriften, ruimtelijk bevraagbaar op RD (`inSR=28992`); daarbuiten valt het lab terug op
  het synthetische register. Dat contrast is de boodschap. Vrachtafleiding in drie lagen
  (`atlas_register.py`): eenheid is al een vracht → direct; concentratie + debiet-voorschrift →
  berekend (29 van 72 vestigingen); anders → getoond zonder vracht, met reden. Let op: de
  Atlas-lagen zijn publiek maar dragen **geen expliciete licentie** — live bevragen met
  bronvermelding, nooit kopiëren. PFOA komt er niet in voor, terwijl dat juist de stof is
  waarvan de achtergrond boven de norm ligt.
```

- [ ] **Step 6: Commit**

```bash
git add tests/test_atlas_live.py CLAUDE.md
git commit -m "test(llab): live-verificatie tegen de Atlas + sprintstatus bijgewerkt

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>"
```

---

## Zelfcontrole van dit plan

**Spec-dekking** — elke sectie uit de spec heeft een taak:

| Spec | Taak |
|---|---|
| §3.1 `water_hub.py` | 1 |
| §3.2 subnav + `keten-tab`/`dvth`-uitzondering | 3 |
| §3.3 `/water` landingspagina | 2 |
| §3.4 `index.html` | 3 |
| §4.1 `waterprofiel.py` | 5 |
| §4.2 `bronnen.py` extra velden + `wbhnaam` | 4 |
| §5.1 `smwk_atlas.py` | 6 |
| §5.2 vracht in drie lagen | 7 |
| §5.3 parameter-crosswalk | 7 |
| §5.4 welk register wanneer | 8 |
| §6.1 `beeld_op_punt` + karakteriseringstest | 8 |
| §6.2 `/api/waterruimte` + parallel + begrenzing | 9 |
| §6.3 `waterruimte.html` | 10 |
| §7 tests | 1-11 |
| §8 bestandslijst | bestandsoverzicht hierboven |
| §9 risico's | 6 (cache/terugval), 8 (storing), 9 (parallel), 11 (live-test) |

**Typeconsistentie** — nagelopen: `subnav_html(actief)` in Task 1 = aanroep in Task 2 en 3;
`profiel()`/`als_waterlichaam()` in Task 5 = gebruik in Task 8; `vergunningen_bij_punt(x, y,
straal_m)` in Task 6 = de `_haal_atlas`-signatuur in Task 8; `naar_register()` levert
`register`/`telling`/`bron`/`bevinding`, alle vier gebruikt in Task 8 en 10; registerposten
dragen `vrachten`, wat `_vracht_van` in Task 7 leest.

**Twee punten waar de uitvoerder moet opletten:**

1. **Task 9 Step 4** haalt de regels op met `rijkswater=True` vóórdat bekend is of dat klopt, en
   duidt ze achteraf opnieuw. Dat mag alleen omdat `duiding()` geen netwerk gebruikt. Verandert
   dat ooit, dan moet de parallellisatie anders.
2. **Task 8 Step 6** laat `beeld()` bewust het vaste `gebied.WATERLICHAAM` en `gebied.REGISTER`
   gebruiken in plaats van het afgeleide profiel. Dat is geen duplicatie uit luiheid maar de
   garantie dat `/gebruiksruimte` hetzelfde blijft antwoorden; de karakteriseringstest bewaakt
   het.
