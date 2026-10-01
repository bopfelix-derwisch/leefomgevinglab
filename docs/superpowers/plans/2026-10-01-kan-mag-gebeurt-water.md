# Kan · mag · gebeurt op het water — Implementatieplan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** De derde laag toevoegen aan het waterdossier — echte metingen uit het Waterkwaliteitsportaal naast de regels uit het DSO en de vergunningen uit de Atlas, met een expliciet gemarkeerd model dat laat zien welke vergunningen aan een overschrijding kúnnen bijdragen.

**Architecture:** Een ingestscript verdicht twee WKP-CSV's (142 MB) tot een compacte set per meetpunt en stof. Vier kleine modules onder `usecases/kmg/` doen elk één ding: meetdata lezen, toerekenen, de proclaimer opbouwen, en de drie lagen samenvoegen. De pagina toont ze in de volgorde van de DSO-folder.

**Tech Stack:** Python 3.10, FastAPI, pytest, CSV (Aquo IM Metingen), bestaande connectors voor DSO Ozon en de Atlas voor een Schone Maas.

**Spec:** `docs/superpowers/specs/2026-10-01-kan-mag-gebeurt-water-design.md`

## Global Constraints

- **Taal:** alle code, commentaar, docstrings, commit-berichten en UI-teksten in het **Nederlands**.
- **Testen draaien met:** `cd /mnt/nvme/workspaces/LeefomgevingLab && .venv/bin/python -m pytest` — huidige stand **580 passed**, 0 xfailed, 0 xpassed.
- **Live-aanroepen** werken alleen met de omgeving geladen: `set -a && . ./.env && set +a` vooraf. Zonder dat faalt `load_config()` met een `FileNotFoundError` die als "bron onbereikbaar" wordt gerapporteerd — dat is de omgeving, geen bug.
- **Geen netwerk in gewone tests.** Bronnen worden geïnjecteerd, zoals `regels.regels_op_locatie(_haal=…)` dat al doet.
- **Commit-trailer:** `Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>`. **Niet pushen.**
- **`git add` met expliciete paden.** Nooit `git add -A` — er staan drie ongerelateerde untracked bestanden in de repo.
- **Ruwe CSV's horen niet in git.** Ze gaan naar `/mnt/nvme/geluidsmeter/data/external/wkp/`; alleen de verdichting is klein genoeg om te bewaren.
- **De harde regel uit spec §5.3:** de woorden "veroorzaakt door" komen niet op de pagina voor. Wel "kan bijdragen", "vergunde ruimte", "bovengrens". De uitkomst van het model is nooit een vaststelling.

## Brongegevens, geverifieerd 2026-10-01

De download `WKP_download_20261001171800` (Rijkswaterstaat, meetjaar 2025) staat uitgepakt in de scratchruimte en bevat:

- `WKP_Meetobjecten_Rijkswaterstaat_2025_*.csv` — 322 meetpunten
- `WKP_Meetwaarden_Rijkswaterstaat_2025_*.csv` — 384.259 meetwaarden, 142 MB

**Kolommen die dit plan gebruikt** (puntkomma-gescheiden, `utf-8-sig`):

| Bestand | Kolom | Gebruik |
|---|---|---|
| Meetobjecten | `MeetobjectCode` | sleutel, bv. `NL80_EIJSDPTN` |
| Meetobjecten | `Omschrijving` | leesbare naam, bv. `Eijsden ponton` |
| Meetobjecten | `GeometriePuntX_RD` / `GeometriePuntY_RD` | RD-coördinaten |
| Meetobjecten | `HoortbijGeoobjectIdentificatie` | KRW-waterlichaam, bv. `NL91BOM` |
| Meetwaarden | `MeetobjectCode` | koppeling naar het punt |
| Meetwaarden | `ParameterCode` / `ParameterOmschrijving` | stof |
| Meetwaarden | `EenheidCode` | `mg/l` of `ug/l` |
| Meetwaarden | `Numeriekewaarde` | de waarde; decimaal kan een komma zijn |
| Meetwaarden | `Monsterophaaldatum` | voor de periode |
| Meetwaarden | `KwaliteitsoordeelCode` | **filter** — zie hieronder |
| Meetwaarden | `Limietsymbool` | `<` betekent onder de rapportagegrens |

**Twee valkuilen die bij de verkenning bovenkwamen:**

1. `MonsterCompartimentCode` is bij de chemische metingen **leeg**, niet `OW`. Filteren op `OW` levert nul stikstof- en zinkmetingen op.
2. `KwaliteitsoordeelCode = '99'` betekent **"Hiaat waarde"** en draagt de sentinel `999999999999`. 3000 van de 384.132 rijen. Zonder filter wordt het maximum onzinnig.

Kwaliteitsoordelen in de set: `00` Normale waarde (356.443), `03` grotere spreiding (24.440), `99` Hiaat (3.000), `90` afwijkend maar goedgekeurd (376). **Houd `00`, `03` en `90`; gooi `99` weg.**

**De labstoffen:** `Ntot` stikstof totaal (2467), `Zn` zink (1783), `PFOA` perfluoroctaanzuur (590). AOX zit er niet in.

**De Maas-waterlichamen, stroomafwaarts** (namen uit de KRW-vlaklaag van RWS):

| Volgorde | Code | Naam |
|---|---|---|
| 1 | `NL91BOM` | Bovenmaas |
| 2 | `NL91GM` | Grensmaas |
| 3 | `NL91ZM` | Zandmaas |
| 4 | `NL91BM` | Bedijkte Maas |
| 5 | `NL94_5` | Beneden Maas |
| 6 | `NL94_6` | Bergsche Maas |
| 7 | `NL94_1` | Haringvliet-oost |
| 8 | `NL94_11` | Haringvliet-west |

---

## Bestandsoverzicht

| Bestand | Verantwoordelijkheid | Taak |
|---|---|---|
| `scripts/13_fetch_wkp_metingen.py` | twee CSV's → één compacte JSON per meetjaar | 1 |
| `src/leefomgevinglab/usecases/kmg/metingen.py` | de verdichting lezen en bevragen | 2 |
| `src/leefomgevinglab/usecases/kmg/toerekening.py` | stroomvolgorde + bijdrage per vergunning | 3 |
| `src/leefomgevinglab/usecases/kmg/proclaimer.py` | de verantwoording, opgebouwd uit de data | 4 |
| `src/leefomgevinglab/usecases/kmg/service.py` | de drie lagen samenvoegen | 5 |
| `src/leefomgevinglab/geluidsmeter/api.py` | *(wijzig)* routes `/kmg` en `/api/kmg` | 6 |
| `src/leefomgevinglab/usecases/water_hub.py` | *(wijzig)* vijfde lid in het dossier | 6 |
| `src/leefomgevinglab/static/kmg.html` | de pagina | 7 |
| `CLAUDE.md` | *(wijzig)* sprintstatus | 8 |

---

### Task 1: De CSV's verdichten

**Files:**
- Create: `scripts/13_fetch_wkp_metingen.py`
- Test: `tests/test_wkp_ingest.py`

**Interfaces:**
- Consumes: niets
- Produces: `verdicht(meetobjecten_pad: str, meetwaarden_pad: str, stoffen: set[str]) -> dict` met sleutels `meetjaar`, `bron`, `opgehaald_op`, `punten` (lijst) en `telling` (dict). Elk punt: `code`, `naam`, `rd`, `waterlichaam`, `stoffen` (lijst met `code`, `naam`, `eenheid`, `n`, `mediaan`, `maximum`, `onder_rapportagegrens`, `van`, `tot`).

- [ ] **Step 1: Schrijf de falende test**

Maak `tests/test_wkp_ingest.py`:

```python
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "scripts"))

OBJ_KOP = ("Meetjaar;WaterbeheerderCode;WaterbeheerderNaam;Namespace;Identificatie;"
           "MeetobjectCode;Omschrijving;GeometriePuntX_RD;GeometriePuntY_RD;"
           "KRWwatertypeCode;HoortbijGeoobjectIdentificatie\n")
WRD_KOP = ("Meetjaar;MeetobjectCode;MonsterCompartimentCode;Monsterophaaldatum;"
           "ParameterCode;ParameterOmschrijving;EenheidCode;Limietsymbool;"
           "Numeriekewaarde;KwaliteitsoordeelCode\n")


def _schrijf(tmp_path, objecten, waarden):
    o = tmp_path / "obj.csv"
    w = tmp_path / "wrd.csv"
    o.write_text(OBJ_KOP + "".join(objecten), encoding="utf-8-sig")
    w.write_text(WRD_KOP + "".join(waarden), encoding="utf-8-sig")
    return str(o), str(w)


def _obj(code="NL80_EIJSDPTN", naam="Eijsden ponton", x="176000", y="310000",
         wl="NL91BOM"):
    return f"2025;1;Rijkswaterstaat;NL80;x;{code};{naam};{x};{y};R7;{wl}\n"


def _wrd(code="NL80_EIJSDPTN", par="Ntot", eenheid="mg/l", waarde="3,3",
         kwal="00", limiet="", datum="2025-03-11"):
    return (f"2025;{code};;{datum};{par};stikstof totaal;{eenheid};{limiet};"
            f"{waarde};{kwal}\n")


def test_mediaan_en_maximum_per_punt_en_stof(tmp_path):
    import importlib
    m = importlib.import_module("13_fetch_wkp_metingen")
    o, w = _schrijf(tmp_path, [_obj()],
                    [_wrd(waarde="2,0"), _wrd(waarde="3,0"), _wrd(waarde="10,0")])
    d = m.verdicht(o, w, {"Ntot"})
    stof = d["punten"][0]["stoffen"][0]
    assert stof["n"] == 3
    assert stof["mediaan"] == 3.0
    assert stof["maximum"] == 10.0


def test_hiaatwaarden_tellen_niet_mee(tmp_path):
    """KwaliteitsoordeelCode 99 draagt de sentinel 999999999999."""
    import importlib
    m = importlib.import_module("13_fetch_wkp_metingen")
    o, w = _schrijf(tmp_path, [_obj()],
                    [_wrd(waarde="3,0"),
                     _wrd(waarde="999999999999", kwal="99"),
                     _wrd(waarde="5,0")])
    d = m.verdicht(o, w, {"Ntot"})
    stof = d["punten"][0]["stoffen"][0]
    assert stof["n"] == 2
    assert stof["maximum"] == 5.0
    assert d["telling"]["hiaatwaarden"] == 1


def test_leeg_compartiment_wordt_niet_weggefilterd(tmp_path):
    """Bij chemische metingen is MonsterCompartimentCode leeg — dat is normaal."""
    import importlib
    m = importlib.import_module("13_fetch_wkp_metingen")
    o, w = _schrijf(tmp_path, [_obj()], [_wrd(waarde="3,0")])
    d = m.verdicht(o, w, {"Ntot"})
    assert d["punten"][0]["stoffen"][0]["n"] == 1


def test_waarden_onder_de_rapportagegrens_worden_geteld(tmp_path):
    import importlib
    m = importlib.import_module("13_fetch_wkp_metingen")
    o, w = _schrijf(tmp_path, [_obj()],
                    [_wrd(waarde="3,0"), _wrd(waarde="0,004", limiet="<")])
    stof = m.verdicht(o, w, {"Ntot"})["punten"][0]["stoffen"][0]
    assert stof["n"] == 2
    assert stof["onder_rapportagegrens"] == 1


def test_onleesbare_waarde_laat_de_rij_niet_klappen(tmp_path):
    import importlib
    m = importlib.import_module("13_fetch_wkp_metingen")
    o, w = _schrijf(tmp_path, [_obj()],
                    [_wrd(waarde="3,0"), _wrd(waarde="nvt"), _wrd(waarde="")])
    d = m.verdicht(o, w, {"Ntot"})
    assert d["punten"][0]["stoffen"][0]["n"] == 1
    assert d["telling"]["onleesbaar"] == 2


def test_punt_draagt_coordinaten_en_waterlichaam(tmp_path):
    import importlib
    m = importlib.import_module("13_fetch_wkp_metingen")
    o, w = _schrijf(tmp_path, [_obj()], [_wrd()])
    p = m.verdicht(o, w, {"Ntot"})["punten"][0]
    assert p["code"] == "NL80_EIJSDPTN"
    assert p["naam"] == "Eijsden ponton"
    assert p["rd"] == [176000.0, 310000.0]
    assert p["waterlichaam"] == "NL91BOM"


def test_punten_zonder_gevraagde_stof_vallen_weg(tmp_path):
    import importlib
    m = importlib.import_module("13_fetch_wkp_metingen")
    o, w = _schrijf(tmp_path, [_obj(), _obj(code="NL80_ANDERS", naam="Ergens")],
                    [_wrd()])
    d = m.verdicht(o, w, {"Ntot"})
    assert [p["code"] for p in d["punten"]] == ["NL80_EIJSDPTN"]


def test_periode_komt_uit_de_monsterdata(tmp_path):
    import importlib
    m = importlib.import_module("13_fetch_wkp_metingen")
    o, w = _schrijf(tmp_path, [_obj()],
                    [_wrd(datum="2025-02-01"), _wrd(datum="2025-11-20")])
    stof = m.verdicht(o, w, {"Ntot"})["punten"][0]["stoffen"][0]
    assert stof["van"] == "2025-02-01"
    assert stof["tot"] == "2025-11-20"
```

- [ ] **Step 2: Draai de test en zie hem falen**

Run: `.venv/bin/python -m pytest tests/test_wkp_ingest.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named '13_fetch_wkp_metingen'`

- [ ] **Step 3: Schrijf het script**

Maak `scripts/13_fetch_wkp_metingen.py`:

```python
"""Verdicht de meetgegevens van het Waterkwaliteitsportaal tot een bruikbare set.

De downloadmodule van het Waterkwaliteitsportaal levert per waterbeheerder en meetjaar twee
CSV's: de meetobjecten (de punten) en de meetwaarden. Dat laatste bestand is voor één beheerder
al 142 MB — te groot om bij elke paginaweergave te lezen. Dit script maakt er één compact
bestand van: per meetpunt en stof het aantal metingen, de mediaan, het maximum en de periode.

De mediaan is de hoofdwaarde, niet het gemiddelde. Meetreeksen bevatten uitschieters — zink op
Eijsden heeft mediaan 4,54 en maximum 49,7 µg/l — en één piek mag het beeld niet bepalen. Het
maximum staat er apart bij, want dat is wat een normtoets interesseert.

Twee dingen die je bij deze bron moet weten, allebei gemeten op 2026-10-01:

  * `MonsterCompartimentCode` is bij de chemische metingen **leeg**, niet `OW`. Wie daarop
    filtert houdt nul stikstof- en zinkmetingen over.
  * `KwaliteitsoordeelCode = '99'` betekent "Hiaat waarde" en draagt de sentinel
    999999999999 — 3000 van de 384.132 rijen. Zonder filter wordt het maximum onzin.

Er is geen machine-ingang: de Digitale Delta API van RWS geeft 401 op elk data-eindpunt, en de
WKP-module die metingen via die API gaat publiceren komt pas begin 2027. Dit blijft dus een
momentopname die een mens ophaalt.
"""
import argparse
import csv
import json
import statistics
import sys
from datetime import datetime, timezone
from pathlib import Path

# Kwaliteitsoordelen die we meetellen. '99' (Hiaat waarde) niet — zie de moduletekst.
GOEDE_OORDELEN = {"00", "03", "90"}

# De stoffen waar dit lab mee rekent. AOX komt in deze bron niet voor.
LABSTOFFEN = {"Ntot", "Zn", "PFOA"}

BRON = {
    "naam": "Waterkwaliteitsportaal",
    "houder": "Informatiehuis Water",
    "url": "https://wkp.rws.nl/downloadmodule",
    "informatiemodel": "Aquo IM Metingen",
}


def _getal(tekst: str) -> float | None:
    """De CSV gebruikt soms een komma als decimaalteken."""
    try:
        return float((tekst or "").strip().replace(",", "."))
    except ValueError:
        return None


def _lees_objecten(pad: str) -> dict:
    uit = {}
    with open(pad, encoding="utf-8-sig", newline="") as f:
        for r in csv.DictReader(f, delimiter=";"):
            code = (r.get("MeetobjectCode") or "").strip()
            if not code:
                continue
            x, y = _getal(r.get("GeometriePuntX_RD", "")), _getal(r.get("GeometriePuntY_RD", ""))
            uit[code] = {
                "code": code,
                "naam": (r.get("Omschrijving") or "").strip() or code,
                "rd": [x, y] if x is not None and y is not None else None,
                "waterlichaam": (r.get("HoortbijGeoobjectIdentificatie") or "").strip() or None,
            }
    return uit


def verdicht(meetobjecten_pad: str, meetwaarden_pad: str,
             stoffen: set[str] | None = None) -> dict:
    """Twee CSV's in, één compacte structuur uit."""
    stoffen = stoffen or LABSTOFFEN
    objecten = _lees_objecten(meetobjecten_pad)
    telling = {"rijen": 0, "meegeteld": 0, "hiaatwaarden": 0, "onleesbaar": 0,
               "buiten_stoffen": 0}
    verzameld = {}          # (puntcode, stofcode) -> dict met waarden
    meetjaar = None

    with open(meetwaarden_pad, encoding="utf-8-sig", newline="") as f:
        for r in csv.DictReader(f, delimiter=";"):
            telling["rijen"] += 1
            meetjaar = meetjaar or (r.get("Meetjaar") or "").strip() or None
            par = (r.get("ParameterCode") or "").strip()
            if par not in stoffen:
                telling["buiten_stoffen"] += 1
                continue
            if (r.get("KwaliteitsoordeelCode") or "").strip() == "99":
                telling["hiaatwaarden"] += 1
                continue
            if (r.get("KwaliteitsoordeelCode") or "").strip() not in GOEDE_OORDELEN:
                telling["hiaatwaarden"] += 1
                continue
            waarde = _getal(r.get("Numeriekewaarde", ""))
            if waarde is None:
                telling["onleesbaar"] += 1
                continue
            punt = (r.get("MeetobjectCode") or "").strip()
            sleutel = (punt, par)
            v = verzameld.setdefault(sleutel, {
                "code": par,
                "naam": (r.get("ParameterOmschrijving") or par).strip(),
                "eenheid": (r.get("EenheidCode") or "").strip(),
                "waarden": [], "onder_rapportagegrens": 0, "data": [],
            })
            v["waarden"].append(waarde)
            if (r.get("Limietsymbool") or "").strip() == "<":
                v["onder_rapportagegrens"] += 1
            d = (r.get("Monsterophaaldatum") or "").strip()
            if d:
                v["data"].append(d)
            telling["meegeteld"] += 1

    punten = {}
    for (puntcode, _par), v in verzameld.items():
        obj = objecten.get(puntcode)
        if obj is None:
            continue
        p = punten.setdefault(puntcode, {**obj, "stoffen": []})
        data = sorted(v["data"])
        p["stoffen"].append({
            "code": v["code"], "naam": v["naam"], "eenheid": v["eenheid"],
            "n": len(v["waarden"]),
            "mediaan": round(statistics.median(v["waarden"]), 6),
            "maximum": round(max(v["waarden"]), 6),
            "onder_rapportagegrens": v["onder_rapportagegrens"],
            "van": data[0] if data else None,
            "tot": data[-1] if data else None,
        })

    for p in punten.values():
        p["stoffen"].sort(key=lambda s: s["code"])

    return {
        "meetjaar": meetjaar,
        "bron": BRON,
        "opgehaald_op": datetime.now(timezone.utc).strftime("%Y-%m-%d"),
        "punten": sorted(punten.values(), key=lambda p: p["code"]),
        "telling": telling,
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("meetobjecten", help="pad naar WKP_Meetobjecten_*.csv")
    ap.add_argument("meetwaarden", help="pad naar WKP_Meetwaarden_*.csv")
    ap.add_argument("--uit", required=True, help="pad voor het verdichte JSON-bestand")
    a = ap.parse_args()

    d = verdicht(a.meetobjecten, a.meetwaarden)
    uit = Path(a.uit)
    uit.parent.mkdir(parents=True, exist_ok=True)
    uit.write_text(json.dumps(d, ensure_ascii=False, indent=1))
    t = d["telling"]
    print(f"meetjaar {d['meetjaar']}: {len(d['punten'])} punten, "
          f"{t['meegeteld']} metingen meegeteld van {t['rijen']} rijen "
          f"({t['hiaatwaarden']} hiaat, {t['onleesbaar']} onleesbaar) -> {uit}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
```

- [ ] **Step 4: Draai de tests en zie ze slagen**

Run: `.venv/bin/python -m pytest tests/test_wkp_ingest.py -v`
Expected: PASS — 8 passed

- [ ] **Step 5: Draai het script op de echte data**

De uitgepakte download staat in de scratchruimte van deze sessie. Zoek hem met:

```bash
ls /mnt/nvme/cache/claude-1001/-mnt-nvme-workspaces-LeefomgevingLab/*/scratchpad/wkp_rws/
```

Maak de doelmap en draai:

```bash
sudo mkdir -p /mnt/nvme/geluidsmeter/data/external/wkp && sudo chown bob:bob /mnt/nvme/geluidsmeter/data/external/wkp
S=$(ls -d /mnt/nvme/cache/claude-1001/-mnt-nvme-workspaces-LeefomgevingLab/*/scratchpad/wkp_rws | head -1)
.venv/bin/python scripts/13_fetch_wkp_metingen.py \
  "$S"/WKP_Meetobjecten_Rijkswaterstaat_2025_*.csv \
  "$S"/WKP_Meetwaarden_Rijkswaterstaat_2025_*.csv \
  --uit /mnt/nvme/geluidsmeter/data/external/wkp/metingen_2025.json
```

Verwacht: meetjaar 2025, enkele tientallen punten, ongeveer 4800 metingen meegeteld, 3000 hiaatwaarden overgeslagen. Kopieer ook de ruwe CSV's naar diezelfde map, zodat de bron naast de verdichting staat. Zet de uitvoer in je verslag.

- [ ] **Step 6: Commit**

```bash
git add scripts/13_fetch_wkp_metingen.py tests/test_wkp_ingest.py
git commit -m "feat(llab): WKP-meetgegevens verdicht tot een bruikbare set

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>"
```

---

### Task 2: De meetset bevragen

**Files:**
- Create: `src/leefomgevinglab/usecases/kmg/__init__.py`, `src/leefomgevinglab/usecases/kmg/metingen.py`
- Modify: `core/config.yaml` (sectie `leefomgevinglab:`)
- Test: `tests/test_kmg_metingen.py`

**Interfaces:**
- Consumes: de JSON-structuur uit Task 1
- Produces: `laad(pad: str) -> dict`, `punten(set_: dict, waterlichamen: list[str] | None = None) -> list[dict]`, `punt(set_: dict, code: str) -> dict` (KeyError bij onbekend)

- [ ] **Step 1: Schrijf de falende test**

Maak `tests/test_kmg_metingen.py`:

```python
import json

import pytest

from leefomgevinglab.usecases.kmg import metingen

SET = {
    "meetjaar": "2025",
    "bron": {"naam": "Waterkwaliteitsportaal", "houder": "Informatiehuis Water"},
    "opgehaald_op": "2026-10-01",
    "punten": [
        {"code": "NL80_EIJSDPTN", "naam": "Eijsden ponton", "rd": [176000.0, 310000.0],
         "waterlichaam": "NL91BOM",
         "stoffen": [{"code": "Ntot", "naam": "stikstof totaal", "eenheid": "mg/l",
                      "n": 52, "mediaan": 3.3, "maximum": 20.0,
                      "onder_rapportagegrens": 0, "van": "2025-01-08", "tot": "2025-12-10"}]},
        {"code": "NL80_HEEL", "naam": "Heel", "rd": [190000.0, 350000.0],
         "waterlichaam": "NL91ZM",
         "stoffen": [{"code": "Zn", "naam": "zink", "eenheid": "ug/l",
                      "n": 26, "mediaan": 6.02, "maximum": 17.7,
                      "onder_rapportagegrens": 2, "van": "2025-02-01", "tot": "2025-11-01"}]},
    ],
    "telling": {"rijen": 100, "meegeteld": 78, "hiaatwaarden": 20, "onleesbaar": 2},
}


def test_laden_van_een_bestand(tmp_path):
    p = tmp_path / "m.json"
    p.write_text(json.dumps(SET), encoding="utf-8")
    d = metingen.laad(str(p))
    assert d["meetjaar"] == "2025"
    assert len(d["punten"]) == 2


def test_ontbrekend_bestand_geeft_een_lege_set(tmp_path):
    """De pagina moet het zonder meetset ook doen, met opgaaf van reden."""
    d = metingen.laad(str(tmp_path / "bestaat-niet.json"))
    assert d["punten"] == []
    assert d["beschikbaar"] is False
    assert d["reden"]


def test_punten_filteren_op_waterlichaam():
    uit = metingen.punten(SET, waterlichamen=["NL91BOM"])
    assert [p["code"] for p in uit] == ["NL80_EIJSDPTN"]


def test_punten_zonder_filter_geeft_alles():
    assert len(metingen.punten(SET)) == 2


def test_een_punt_opzoeken():
    p = metingen.punt(SET, "NL80_HEEL")
    assert p["naam"] == "Heel"
    assert p["stoffen"][0]["code"] == "Zn"


def test_onbekend_punt_faalt_luid():
    with pytest.raises(KeyError):
        metingen.punt(SET, "NL80_BESTAATNIET")
```

- [ ] **Step 2: Draai de test en zie hem falen**

Run: `.venv/bin/python -m pytest tests/test_kmg_metingen.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'leefomgevinglab.usecases.kmg'`

- [ ] **Step 3: Schrijf de module**

Maak `src/leefomgevinglab/usecases/kmg/__init__.py`:

```python
"""Kan, mag en gebeurt op het water.

Het DSO laat voor geluid en lucht zien hoe drie lagen over elkaar heen zichtbaar worden: wat de
regels toestaan, wat er vergund is, en wat er gemeten wordt. Deze module doet dat voor water.

Het verschil met de DSO-plaat zit in de laatste stap. Bij geluid is de bijdrage van een bedrijf
aan een immissiepunt uit te rekenen, want geluid dempt voorspelbaar met afstand. Bij water kan
dat niet zonder stromingsmodel. Wat hier staat is daarom een bovengrens, geen vaststelling.
"""
```

Maak `src/leefomgevinglab/usecases/kmg/metingen.py`:

```python
"""De verdichte meetset lezen en bevragen.

De set komt uit `scripts/13_fetch_wkp_metingen.py` en is een momentopname: er bestaat geen
machine-ingang bij het Waterkwaliteitsportaal. Ontbreekt het bestand, dan geeft `laad()` een
lege set met een reden in plaats van een exception — de pagina kan dan nog steeds de andere
twee lagen tonen en zeggen waarom de derde ontbreekt.
"""
import json
from pathlib import Path


def laad(pad: str) -> dict:
    p = Path(pad)
    if not p.exists():
        return {"beschikbaar": False, "punten": [], "meetjaar": None, "bron": None,
                "opgehaald_op": None, "telling": {},
                "reden": f"geen meetset gevonden op {pad}; haal hem op met "
                         "scripts/13_fetch_wkp_metingen.py"}
    d = json.loads(p.read_text(encoding="utf-8"))
    d["beschikbaar"] = True
    d.setdefault("reden", "")
    return d


def punten(set_: dict, waterlichamen: list[str] | None = None) -> list[dict]:
    """De meetpunten, eventueel beperkt tot een lijst waterlichamen."""
    alle = set_.get("punten") or []
    if waterlichamen is None:
        return list(alle)
    toegestaan = set(waterlichamen)
    return [p for p in alle if p.get("waterlichaam") in toegestaan]


def punt(set_: dict, code: str) -> dict:
    """Eén meetpunt; KeyError bij een onbekende code — luid falen."""
    for p in set_.get("punten") or []:
        if p["code"] == code:
            return p
    raise KeyError(code)
```

- [ ] **Step 4: Draai de tests en zie ze slagen**

Run: `.venv/bin/python -m pytest tests/test_kmg_metingen.py -v`
Expected: PASS — 6 passed

- [ ] **Step 5: Voeg de config toe**

In `core/config.yaml`, binnen `leefomgevinglab:`, direct ná het blok `smwk_atlas:`:

```yaml
  kmg:
    # Kan, mag en gebeurt op het water. De meetset is een momentopname uit het
    # Waterkwaliteitsportaal (Informatiehuis Water); er is geen machine-ingang — de Digitale
    # Delta API van RWS geeft 401 en de WKP-module die dit zou oplossen komt begin 2027.
    # Verversen: scripts/13_fetch_wkp_metingen.py op een nieuwe download.
    metingen_pad: "/mnt/nvme/geluidsmeter/data/external/wkp/metingen_2025.json"
```

- [ ] **Step 6: Commit**

```bash
git add src/leefomgevinglab/usecases/kmg/ tests/test_kmg_metingen.py core/config.yaml
git commit -m "feat(llab): de verdichte WKP-meetset lezen en bevragen

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>"
```

---

### Task 3: Het toerekeningsmodel

**Files:**
- Create: `src/leefomgevinglab/usecases/kmg/toerekening.py`
- Test: `tests/test_kmg_toerekening.py`

**Interfaces:**
- Consumes: registerposten uit `atlas_register.naar_register()` (met `naam`, `kenmerk`, `vrachten`)
- Produces: `STROOMVOLGORDE: list[tuple[str, str]]`, `is_bovenstrooms(van: str, naar: str) -> bool`, `bijdragen(gemeten_mg_l: float, parameter: str, register: list[dict], waterlichaam_meetpunt: str, waterlichaam_per_post: dict[str, str], debiet_m3_s: float) -> dict` met sleutels `posten`, `restant_mg_l`, `som_bijdragen_mg_l`, `voorbehoud`

- [ ] **Step 1: Schrijf de falende test**

Maak `tests/test_kmg_toerekening.py`:

```python
import pytest

from leefomgevinglab.usecases.kmg import toerekening as t


def test_de_stroomvolgorde_loopt_van_bovenmaas_naar_haringvliet():
    codes = [c for c, _naam in t.STROOMVOLGORDE]
    assert codes[0] == "NL91BOM"
    assert codes.index("NL91GM") < codes.index("NL91ZM")
    assert codes.index("NL91ZM") < codes.index("NL94_5")
    assert len(codes) == len(set(codes)), "geen dubbele codes"


def test_elke_code_heeft_een_echte_naam():
    namen = dict(t.STROOMVOLGORDE)
    assert namen["NL91BOM"] == "Bovenmaas"
    assert namen["NL91GM"] == "Grensmaas"
    assert namen["NL91ZM"] == "Zandmaas"


def test_bovenstrooms_herkent_de_richting():
    assert t.is_bovenstrooms("NL91BOM", "NL91ZM") is True
    assert t.is_bovenstrooms("NL91ZM", "NL91BOM") is False


def test_hetzelfde_waterlichaam_telt_mee():
    assert t.is_bovenstrooms("NL91BOM", "NL91BOM") is True


def test_onbekend_waterlichaam_telt_niet_mee():
    assert t.is_bovenstrooms("NL00_ONBEKEND", "NL91ZM") is False


def _post(naam, vracht, parameter="stikstof totaal"):
    return {"naam": naam, "kenmerk": f"K-{naam}", "vrachten": {parameter: vracht}}


def test_alleen_bovenstroomse_vergunningen_dragen_bij():
    reg = [_post("Boven", 1000.0), _post("Beneden", 1000.0)]
    wl = {"K-Boven": "NL91BOM", "K-Beneden": "NL94_5"}
    d = t.bijdragen(3.3, "stikstof totaal", reg, "NL91ZM", wl, debiet_m3_s=250.0)
    namen = [p["naam"] for p in d["posten"]]
    assert namen == ["Boven"]


def test_de_som_van_bijdragen_en_restant_is_de_gemeten_waarde():
    reg = [_post("A", 1_000_000.0), _post("B", 500_000.0)]
    wl = {"K-A": "NL91BOM", "K-B": "NL91GM"}
    d = t.bijdragen(3.3, "stikstof totaal", reg, "NL91ZM", wl, debiet_m3_s=250.0)
    assert d["som_bijdragen_mg_l"] + d["restant_mg_l"] == pytest.approx(3.3, rel=1e-9)


def test_zonder_bovenstroomse_vergunningen_is_het_restant_alles():
    reg = [_post("Beneden", 1000.0)]
    wl = {"K-Beneden": "NL94_6"}
    d = t.bijdragen(3.3, "stikstof totaal", reg, "NL91BOM", wl, debiet_m3_s=250.0)
    assert d["posten"] == []
    assert d["restant_mg_l"] == pytest.approx(3.3)


def test_een_vergunning_zonder_deze_stof_draagt_niet_bij():
    reg = [_post("A", 1000.0, parameter="zink")]
    wl = {"K-A": "NL91BOM"}
    d = t.bijdragen(3.3, "stikstof totaal", reg, "NL91ZM", wl, debiet_m3_s=250.0)
    assert d["posten"] == []


def test_de_bijdrage_is_vracht_gedeeld_door_de_jaarafvoer():
    """1.000.000 kg/jaar in 250 m3/s = 250 * 31.536.000 * 1000 liter."""
    reg = [_post("A", 1_000_000.0)]
    wl = {"K-A": "NL91BOM"}
    d = t.bijdragen(10.0, "stikstof totaal", reg, "NL91ZM", wl, debiet_m3_s=250.0)
    liters = 250.0 * 31_536_000 * 1000
    verwacht = 1_000_000.0 * 1e6 / liters          # kg -> mg, gedeeld door liters
    assert d["posten"][0]["bijdrage_mg_l"] == pytest.approx(verwacht, rel=1e-6)


def test_het_voorbehoud_staat_altijd_in_de_uitkomst():
    d = t.bijdragen(3.3, "stikstof totaal", [], "NL91BOM", {}, debiet_m3_s=250.0)
    assert d["voorbehoud"]
    assert "bovengrens" in d["voorbehoud"].lower()


def test_de_uitkomst_bevat_het_woord_veroorzaakt_niet():
    """Spec 5.3: dit is een meetlat, geen vaststelling."""
    reg = [_post("A", 1000.0)]
    wl = {"K-A": "NL91BOM"}
    d = t.bijdragen(3.3, "stikstof totaal", reg, "NL91ZM", wl, debiet_m3_s=250.0)
    tekst = repr(d).lower()
    assert "veroorzaakt" not in tekst
```

- [ ] **Step 2: Draai de test en zie hem falen**

Run: `.venv/bin/python -m pytest tests/test_kmg_toerekening.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named '…kmg.toerekening'`

- [ ] **Step 3: Schrijf de module**

Maak `src/leefomgevinglab/usecases/kmg/toerekening.py`:

```python
"""Welke vergunningen kúnnen bijdragen aan een gemeten waarde, en hoeveel?

Dit is het deel waar deze pagina betrouwbaar of onbetrouwbaar wordt, dus het voorbehoud staat
in de uitkomst en niet alleen in de documentatie.

Wat het model doet: van elke vergunde vracht bovenstrooms van het meetpunt de bijdrage aan de
concentratie berekenen, door de vracht te delen door de jaarafvoer van het waterlichaam. Wat
overblijft tussen de som daarvan en de gemeten waarde heet 'bovenstrooms en diffuus' — dat
omvat buitenlandse bronnen, landbouw, riooloverstorten en atmosferische depositie.

Wat het model niet doet: geen verblijftijd, geen menging, geen afbraak of bezinking, en geen
rekening met het moment van lozen tegenover het moment van meten. Het rekent bovendien met de
vergúnde ruimte, niet met de werkelijke lozing, en een vergunning wordt zelden volledig benut.
De uitkomst is daarmee een bovengrens.

En het belangrijkste: dit is géén vaststelling van wie een overschrijding veroorzaakt. De
DSO-folder waar dit idee vandaan komt zegt het zelf — toezicht stelt dat vast, met het vergunde
beeld als meetlat. Deze module levert de meetlat.
"""

SECONDEN_PER_JAAR = 31_536_000

# De Maas stroomafwaarts. Namen uit de KRW-vlaklaag van RWS, nagekeken 2026-10-01.
# Dit is een keuze van dit lab: de bron kent geen expliciete volgorde, alleen losse
# waterlichamen. Zijtakken en kanalen staan er bewust niet in — die zouden een
# stroomschema vergen in plaats van een lijst.
STROOMVOLGORDE = [
    ("NL91BOM", "Bovenmaas"),
    ("NL91GM", "Grensmaas"),
    ("NL91ZM", "Zandmaas"),
    ("NL91BM", "Bedijkte Maas"),
    ("NL94_5", "Beneden Maas"),
    ("NL94_6", "Bergsche Maas"),
    ("NL94_1", "Haringvliet-oost"),
    ("NL94_11", "Haringvliet-west"),
]

_INDEX = {code: i for i, (code, _naam) in enumerate(STROOMVOLGORDE)}

VOORBEHOUD = (
    "Deze verdeling is een bovengrens, berekend met een sterk versimpeld model van dit lab: de "
    "vergunde vracht gedeeld over de jaarafvoer van het waterlichaam, zonder verblijftijd, "
    "menging of afbraak. Een vergunning wordt zelden volledig benut, dus de werkelijke bijdrage "
    "ligt lager. Welk aandeel aan wie toekomt stelt het toezicht vast, niet deze pagina."
)


def is_bovenstrooms(waterlichaam: str, meetpunt_waterlichaam: str) -> bool:
    """Ligt `waterlichaam` bovenstrooms van het meetpunt, of is het hetzelfde?

    Een onbekend waterlichaam telt niet mee: dan weten we de richting niet, en meetellen zou
    een bijdrage suggereren die we niet kunnen onderbouwen.
    """
    a, b = _INDEX.get(waterlichaam), _INDEX.get(meetpunt_waterlichaam)
    if a is None or b is None:
        return False
    return a <= b


def bijdragen(gemeten_mg_l: float, parameter: str, register: list[dict],
              waterlichaam_meetpunt: str, waterlichaam_per_post: dict[str, str],
              debiet_m3_s: float) -> dict:
    """Per vergunning de bijdrage aan de gemeten concentratie, plus wat overblijft."""
    liters_per_jaar = debiet_m3_s * SECONDEN_PER_JAAR * 1000.0
    posten = []
    for post in register:
        wl = waterlichaam_per_post.get(post.get("kenmerk") or "")
        if not wl or not is_bovenstrooms(wl, waterlichaam_meetpunt):
            continue
        vracht_kg = (post.get("vrachten") or {}).get(parameter)
        if not vracht_kg:
            continue
        bijdrage = vracht_kg * 1e6 / liters_per_jaar if liters_per_jaar else 0.0
        posten.append({
            "naam": post.get("naam"), "kenmerk": post.get("kenmerk"),
            "waterlichaam": wl, "vracht_kg_jaar": vracht_kg,
            "bijdrage_mg_l": bijdrage,
        })

    posten.sort(key=lambda p: p["bijdrage_mg_l"], reverse=True)
    som = sum(p["bijdrage_mg_l"] for p in posten)
    return {
        "posten": posten,
        "som_bijdragen_mg_l": som,
        "restant_mg_l": gemeten_mg_l - som,
        "restant_label": "bovenstrooms en diffuus",
        "debiet_m3_s": debiet_m3_s,
        "voorbehoud": VOORBEHOUD,
    }
```

- [ ] **Step 4: Draai de tests en zie ze slagen**

Run: `.venv/bin/python -m pytest tests/test_kmg_toerekening.py -v`
Expected: PASS — 12 passed

- [ ] **Step 5: Commit**

```bash
git add src/leefomgevinglab/usecases/kmg/toerekening.py tests/test_kmg_toerekening.py
git commit -m "feat(llab): toerekeningsmodel met het voorbehoud in de uitkomst

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>"
```

---

### Task 4: De proclaimer

**Files:**
- Create: `src/leefomgevinglab/usecases/kmg/proclaimer.py`
- Test: `tests/test_kmg_proclaimer.py`

**Interfaces:**
- Consumes: de meetset uit Task 2, de registerbron uit `atlas_register.naar_register()`
- Produces: `bouw(meetset: dict, register_bron: dict, regels_bron: str, doelen_beschikbaar: bool) -> dict` met sleutels `kopjes` (lijst van `{kop, tekst}`) en `gegevens` (de getallen die erin zitten)

- [ ] **Step 1: Schrijf de falende test**

Maak `tests/test_kmg_proclaimer.py`:

```python
from leefomgevinglab.usecases.kmg import proclaimer

MEETSET = {
    "beschikbaar": True, "meetjaar": "2025", "opgehaald_op": "2026-10-01",
    "bron": {"naam": "Waterkwaliteitsportaal", "houder": "Informatiehuis Water",
             "url": "https://wkp.rws.nl/downloadmodule"},
    "punten": [{"code": "A", "stoffen": [{"code": "Ntot", "n": 52},
                                         {"code": "Zn", "n": 104}]}],
    "telling": {"meegeteld": 156, "hiaatwaarden": 3000},
}
REGISTER_BRON = {"echt": True, "bron": {"naam": "Atlas voor een Schone Maas"}}


def _tekst(p):
    return " ".join(k["tekst"] for k in p["kopjes"]).lower()


def test_de_proclaimer_heeft_vier_kopjes():
    p = proclaimer.bouw(MEETSET, REGISTER_BRON, "DSO Ozon", doelen_beschikbaar=True)
    assert len(p["kopjes"]) == 4
    for k in p["kopjes"]:
        assert k["kop"] and k["tekst"]


def test_het_meetjaar_komt_uit_de_data_niet_uit_een_vaste_tekst():
    p = proclaimer.bouw({**MEETSET, "meetjaar": "2024"}, REGISTER_BRON, "DSO Ozon", True)
    assert "2024" in _tekst(p)
    assert "2025" not in _tekst(p)


def test_het_aantal_metingen_klopt_met_de_meetset():
    p = proclaimer.bouw(MEETSET, REGISTER_BRON, "DSO Ozon", True)
    assert p["gegevens"]["metingen"] == 156
    assert "156" in _tekst(p)


def test_de_bronhouder_wordt_genoemd():
    p = proclaimer.bouw(MEETSET, REGISTER_BRON, "DSO Ozon", True)
    assert "informatiehuis water" in _tekst(p)
    assert "atlas voor een schone maas" in _tekst(p)


def test_het_gat_wordt_benoemd_met_een_datum():
    p = proclaimer.bouw(MEETSET, REGISTER_BRON, "DSO Ozon", True)
    t = _tekst(p)
    assert "2027" in t, "de WKP-module komt begin 2027 — dat hoort erbij"
    assert "401" in t, "de Digitale Delta API geeft vandaag 401"


def test_zonder_meetset_zegt_de_proclaimer_dat():
    leeg = {"beschikbaar": False, "punten": [], "telling": {},
            "reden": "geen meetset gevonden", "meetjaar": None, "bron": None,
            "opgehaald_op": None}
    p = proclaimer.bouw(leeg, REGISTER_BRON, "DSO Ozon", True)
    assert "geen meetgegevens" in _tekst(p)


def test_zonder_krw_doelen_zegt_de_proclaimer_dat():
    p = proclaimer.bouw(MEETSET, REGISTER_BRON, "DSO Ozon", doelen_beschikbaar=False)
    assert "geen krw-doel" in _tekst(p) or "zonder normoordeel" in _tekst(p)


def test_de_proclaimer_belooft_geen_vaststelling():
    p = proclaimer.bouw(MEETSET, REGISTER_BRON, "DSO Ozon", True)
    t = _tekst(p)
    assert "veroorzaakt door" not in t
    assert "toezicht" in t
```

- [ ] **Step 2: Draai de test en zie hem falen**

Run: `.venv/bin/python -m pytest tests/test_kmg_proclaimer.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named '…kmg.proclaimer'`

- [ ] **Step 3: Schrijf de module**

Maak `src/leefomgevinglab/usecases/kmg/proclaimer.py`:

```python
"""De verantwoording bij deze pagina — een proclaimer, geen disclaimer.

Niet uitleggen waar we níet voor instaan, maar hoe dit gemaakt is en waar we wél voor instaan.

De tekst wordt opgebouwd uit dezelfde gegevens die de pagina voeden: het meetjaar, het aantal
metingen, de ophaaldatum en de bronnaam komen uit de meetset zelf. Daarmee kan wat er staat
niet uit de pas lopen met wat je ziet — een test dwingt dat af.
"""


def _metingen(meetset: dict) -> int:
    t = meetset.get("telling") or {}
    if t.get("meegeteld"):
        return int(t["meegeteld"])
    return sum(s.get("n", 0) for p in (meetset.get("punten") or [])
               for s in (p.get("stoffen") or []))


def bouw(meetset: dict, register_bron: dict, regels_bron: str,
         doelen_beschikbaar: bool) -> dict:
    """De vier kopjes van de proclaimer, met de getallen uit de data."""
    beschikbaar = bool(meetset.get("beschikbaar"))
    bron = meetset.get("bron") or {}
    houder = bron.get("houder") or "onbekende bronhouder"
    bronnaam = bron.get("naam") or "onbekende bron"
    jaar = meetset.get("meetjaar") or "onbekend jaar"
    opgehaald = meetset.get("opgehaald_op") or "onbekende datum"
    n = _metingen(meetset)
    punten = len(meetset.get("punten") or [])
    reg = (register_bron.get("bron") or {}).get("naam") or "onbekend register"
    hiaat = (meetset.get("telling") or {}).get("hiaatwaarden", 0)

    if beschikbaar:
        echt = (
            f"De gemeten waarden op deze pagina komen uit het {bronnaam} van {houder}. Het is "
            f"gevalideerde monitoring over meetjaar {jaar}: {n} metingen op {punten} meetpunten, "
            f"volgens het Aquo-informatiemodel Metingen. Wij hebben die set op {opgehaald} "
            f"opgehaald en verdicht tot een mediaan en een maximum per meetpunt en stof. "
            f"Daarbij zijn {hiaat} waarden met het kwaliteitsoordeel 'Hiaat waarde' overgeslagen; "
            f"die dragen een plaatshoudergetal en zijn geen meting. "
            f"De vergunningen komen uit de {reg} en worden bij elke weergave live opgehaald. "
            f"De regels die hier gelden komen live uit {regels_bron}."
        )
    else:
        echt = (
            f"Er zijn op dit moment **geen meetgegevens** geladen: {meetset.get('reden') or ''} "
            f"De vergunningen uit de {reg} en de regels uit {regels_bron} worden wel live "
            f"opgehaald en staan hieronder."
        )

    van_ons = (
        "De verdeling van een gemeten waarde over de vergunningen is een model van dit lab, geen "
        "gegeven uit een bron. Wij delen de vergunde vracht van elke bovenstroomse lozing door de "
        "jaarafvoer van het waterlichaam, en noemen wat overblijft 'bovenstrooms en diffuus'. "
        "Daar zit geen verblijftijd in, geen menging, geen afbraak en geen bezinking, en er wordt "
        "gerekend met de vergunde ruimte in plaats van met de werkelijke lozing. Omdat een "
        "vergunning zelden volledig wordt benut, is elke berekende bijdrage een bovengrens. "
        "De volgorde van de Maas-waterlichamen waarmee wij 'bovenstrooms' bepalen is eveneens "
        "door ons vastgelegd; de bron kent die volgorde niet."
    )

    if not doelen_beschikbaar:
        van_ons += (
            " Er zijn geen KRW-doelen geladen, dus deze pagina toont de metingen **zonder "
            "normoordeel**. Terugvallen op de illustratieve normen die dit lab elders gebruikt "
            "zou een echte meting tegen een verzonnen norm zetten; dat doen wij hier niet."
        )

    niet_mee = (
        "Deze pagina stelt niet vast wie een overschrijding teweegbrengt. Dat oordeel ligt bij "
        "het toezicht, dat daarvoor het vergunde beeld als meetlat gebruikt. Wat u hier ziet is "
        "die meetlat: welke vergunningen bovenstrooms liggen en hoeveel ruimte zij hebben. Een "
        "balk in de grafiek betekent 'kan bijdragen', niet 'heeft bijgedragen'."
    )

    gat = (
        "Twee van de drie lagen komen machinaal binnen: de regels uit het DSO en de vergunningen "
        "uit de Atlas. De metingen niet. De Digitale Delta API van Rijkswaterstaat geeft vandaag "
        "op elk data-eindpunt een 401, en de module van het Waterkwaliteitsportaal waarmee "
        "waterbeheerders hun metingen rechtstreeks via die API gaan publiceren wordt begin 2027 "
        "opgeleverd. Tot die tijd is de derde laag een momentopname die iemand met de hand "
        f"ophaalt — deze is van {opgehaald}. Leest u dit later: kijk of het inmiddels anders is."
    )

    return {
        "kopjes": [
            {"kop": "Wat u ziet en waar het vandaan komt", "tekst": echt},
            {"kop": "Wat van ons is", "tekst": van_ons},
            {"kop": "Wat u hier niet uit kunt afleiden", "tekst": niet_mee},
            {"kop": "Waar het gat zit", "tekst": gat},
        ],
        "gegevens": {"meetjaar": jaar, "metingen": n, "meetpunten": punten,
                     "opgehaald_op": opgehaald, "hiaatwaarden": hiaat,
                     "bron": bronnaam, "houder": houder, "register": reg,
                     "doelen_beschikbaar": doelen_beschikbaar},
    }
```

- [ ] **Step 4: Draai de tests en zie ze slagen**

Run: `.venv/bin/python -m pytest tests/test_kmg_proclaimer.py -v`
Expected: PASS — 8 passed

- [ ] **Step 5: Commit**

```bash
git add src/leefomgevinglab/usecases/kmg/proclaimer.py tests/test_kmg_proclaimer.py
git commit -m "feat(llab): proclaimer opgebouwd uit de gegevens die de pagina voeden

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>"
```

---

### Task 5: De drie lagen samenvoegen

**Files:**
- Create: `src/leefomgevinglab/usecases/kmg/service.py`
- Test: `tests/test_kmg_service.py`

**Interfaces:**
- Consumes: `metingen.laad/punten/punt` (Task 2), `toerekening.bijdragen` (Task 3), `proclaimer.bouw` (Task 4), `regels.regels_op_locatie` en `atlas_register.naar_register` (bestaand)
- Produces: `meetpunten(pad: str) -> list[dict]`, `beeld(code: str, pad: str, live: bool = True, _haal_regels=None, _haal_atlas=None) -> dict`

- [ ] **Step 1: Schrijf de falende test**

Maak `tests/test_kmg_service.py`:

```python
import json

import pytest

from leefomgevinglab.usecases.kmg import service

PUNT = {
    "code": "NL80_EIJSDPTN", "naam": "Eijsden ponton", "rd": [176000.0, 310000.0],
    "waterlichaam": "NL91BOM",
    "stoffen": [{"code": "Ntot", "naam": "stikstof totaal", "eenheid": "mg/l",
                 "n": 52, "mediaan": 3.3, "maximum": 20.0,
                 "onder_rapportagegrens": 0, "van": "2025-01-08", "tot": "2025-12-10"}],
}
SET = {"meetjaar": "2025", "opgehaald_op": "2026-10-01",
       "bron": {"naam": "Waterkwaliteitsportaal", "houder": "Informatiehuis Water"},
       "punten": [PUNT], "telling": {"meegeteld": 52, "hiaatwaarden": 0}}


def _pad(tmp_path):
    p = tmp_path / "m.json"
    p.write_text(json.dumps(SET), encoding="utf-8")
    return str(p)


def _atlas(x, y, straal_m):
    return [{"kenmerk": "K1", "naam": "Testfabriek BV", "plaats": "Maastricht",
             "locatie": None, "url": None, "besluitdatum": "2015-01-01",
             "locatiecode": None, "vestigingsnummer_kvk": None,
             "voorschriften": [
                 {"parameter": "stikstof totaal", "waarde": 10.0,
                  "eenheid": "milligram per liter", "bemonstering": None, "rd": [x, y]},
                 {"parameter": "Debiet", "waarde": 100.0,
                  "eenheid": "kubieke meter per uur", "bemonstering": None, "rd": [x, y]}]}]


def test_meetpunten_lijst(tmp_path):
    uit = service.meetpunten(_pad(tmp_path))
    assert [p["code"] for p in uit] == ["NL80_EIJSDPTN"]


def test_beeld_bevat_de_drie_lagen(tmp_path):
    b = service.beeld("NL80_EIJSDPTN", _pad(tmp_path), live=True,
                      _haal_regels=lambda rd: [], _haal_atlas=_atlas)
    assert "kan" in b and "mag" in b and "gebeurt" in b
    assert b["meetpunt"]["naam"] == "Eijsden ponton"


def test_gebeurt_draagt_de_gemeten_waarden(tmp_path):
    b = service.beeld("NL80_EIJSDPTN", _pad(tmp_path), live=True,
                      _haal_regels=lambda rd: [], _haal_atlas=_atlas)
    stof = b["gebeurt"]["stoffen"][0]
    assert stof["code"] == "Ntot"
    assert stof["mediaan"] == 3.3


def test_de_proclaimer_zit_in_het_antwoord(tmp_path):
    b = service.beeld("NL80_EIJSDPTN", _pad(tmp_path), live=True,
                      _haal_regels=lambda rd: [], _haal_atlas=_atlas)
    assert len(b["proclaimer"]["kopjes"]) == 4


def test_onbekend_meetpunt_faalt_luid(tmp_path):
    with pytest.raises(KeyError):
        service.beeld("NL80_BESTAATNIET", _pad(tmp_path), live=False)


def test_zonder_live_worden_de_bronnen_niet_bevraagd(tmp_path):
    b = service.beeld("NL80_EIJSDPTN", _pad(tmp_path), live=False)
    assert b["kan"]["status"] == "overgeslagen"
    assert b["mag"]["status"] == "overgeslagen"


def test_zonder_meetset_blijven_de_andere_lagen_staan(tmp_path):
    b = service.beeld("", str(tmp_path / "bestaat-niet.json"), live=False,
                      toestaan_zonder_meetpunt=True)
    assert b["gebeurt"]["beschikbaar"] is False
    assert b["proclaimer"]["kopjes"]
```

- [ ] **Step 2: Draai de test en zie hem falen**

Run: `.venv/bin/python -m pytest tests/test_kmg_service.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named '…kmg.service'`

- [ ] **Step 3: Schrijf de module**

Maak `src/leefomgevinglab/usecases/kmg/service.py`:

```python
"""De drie lagen van de DSO-folder, samengevoegd voor één meetpunt.

Kan — de regelingen die op het meetpunt gelden, live uit het DSO.
Mag — de vergunningen op dit waterlichaam en bovenstrooms, live uit de Atlas.
Gebeurt — de gemeten waarden uit de verdichte WKP-set.

En daarna de vraag die de folder stelt: ligt het gemeten boven de norm, welke vergunningen
kunnen dan bijdragen? Het antwoord daarop is een bovengrens, geen vaststelling — zie
`toerekening.py`.
"""
from leefomgevinglab.usecases.gebruiksruimte import atlas_register, regels

from . import metingen, proclaimer, toerekening

# Jaarafvoer per Maas-waterlichaam, m3/s. Keuze van dit lab: de KRW-service levert geen
# afvoergegevens. Orde van grootte van de Maas bij gemiddelde afvoer.
DEBIET_M3_S = {
    "NL91BOM": 230.0, "NL91GM": 240.0, "NL91ZM": 250.0, "NL91BM": 260.0,
    "NL94_5": 270.0, "NL94_6": 280.0, "NL94_1": 300.0, "NL94_11": 310.0,
}
STANDAARD_DEBIET = 250.0


def meetpunten(pad: str) -> list[dict]:
    """De beschikbare meetpunten, stroomafwaarts gesorteerd."""
    set_ = metingen.laad(pad)
    volgorde = {c: i for i, (c, _n) in enumerate(toerekening.STROOMVOLGORDE)}
    punten = metingen.punten(set_, waterlichamen=list(volgorde))
    namen = dict(toerekening.STROOMVOLGORDE)
    for p in punten:
        p["waterlichaam_naam"] = namen.get(p.get("waterlichaam"), "")
    punten.sort(key=lambda p: (volgorde.get(p.get("waterlichaam"), 99), p["code"]))
    return punten


def _atlas_standaard(x: float, y: float, straal_m: int):
    from leefomgevinglab.connectors.smwk_atlas import SmwkAtlasConnector
    from leefomgevinglab.geluidsmeter.config import load_config
    cfg = load_config().get("leefomgevinglab", {})
    at = cfg.get("smwk_atlas", {})
    c = SmwkAtlasConnector(cache_dir=cfg.get("cache_dir", "/tmp/llab_cache"),
                           cache_ttl=at.get("cache_ttl_s", 86400),
                           base_url=at.get("base_url") or None)
    return c.vergunningen_bij_punt(x, y, straal_m=straal_m)


def beeld(code: str, pad: str, live: bool = True, straal_m: int = 50000,
          _haal_regels=None, _haal_atlas=None,
          toestaan_zonder_meetpunt: bool = False) -> dict:
    """Kan, mag en gebeurt op één meetpunt."""
    set_ = metingen.laad(pad)
    if set_.get("beschikbaar"):
        punt = metingen.punt(set_, code)        # KeyError bij onbekende code
    elif toestaan_zonder_meetpunt:
        punt = {"code": code, "naam": "(geen meetset)", "rd": None,
                "waterlichaam": None, "stoffen": []}
    else:
        raise KeyError(code)

    x, y = (punt.get("rd") or [None, None])
    wl = punt.get("waterlichaam")

    # Kan — de regels op het meetpunt
    if live and x is not None:
        kan = regels.regels_op_locatie(x, y, rijkswater=True, live=True, _haal=_haal_regels)
    else:
        kan = {"live": False, "status": "overgeslagen", "regelingen": [],
               "bron": regels.BRON, "telling": {}}

    # Mag — de vergunningen in de buurt, omgerekend naar vrachten
    if live and x is not None:
        try:
            posten = (_haal_atlas or _atlas_standaard)(x, y, straal_m)
            reg = atlas_register.naar_register(posten)
            mag = {"status": "ok", **reg}
        except Exception as exc:                 # noqa: BLE001 — bron mag wegvallen
            mag = {"status": "onbereikbaar", "fout": type(exc).__name__,
                   "register": [], "telling": {}, "bron": {}, "echt": False}
    else:
        mag = {"status": "overgeslagen", "register": [], "telling": {},
               "bron": {}, "echt": False}

    # Gebeurt — de metingen
    gebeurt = {"beschikbaar": bool(set_.get("beschikbaar")),
               "reden": set_.get("reden", ""), "meetjaar": set_.get("meetjaar"),
               "stoffen": punt.get("stoffen") or []}

    # De vraag: wie kan bijdragen? Alleen zinvol met een meting én vergunningen.
    debiet = DEBIET_M3_S.get(wl, STANDAARD_DEBIET)
    wl_per_post = {p.get("kenmerk"): wl for p in (mag.get("register") or []) if p.get("kenmerk")}
    vraag = []
    for stof in gebeurt["stoffen"]:
        naam = stof.get("naam")
        d = toerekening.bijdragen(stof.get("mediaan") or 0.0, naam,
                                  mag.get("register") or [], wl or "", wl_per_post, debiet)
        vraag.append({"stof": stof.get("code"), "naam": naam, **d})

    return {
        "meetpunt": {**punt,
                     "waterlichaam_naam": dict(toerekening.STROOMVOLGORDE).get(wl, "")},
        "kan": kan,
        "mag": mag,
        "gebeurt": gebeurt,
        "bijdragen": vraag,
        "proclaimer": proclaimer.bouw(set_, mag, regels.BRON, doelen_beschikbaar=False),
    }
```

- [ ] **Step 4: Draai de tests en zie ze slagen**

Run: `.venv/bin/python -m pytest tests/test_kmg_service.py -v`
Expected: PASS — 7 passed

- [ ] **Step 5: Draai de hele suite**

Run: `.venv/bin/python -m pytest -q`
Expected: geen nieuwe failures ten opzichte van 580 passed

- [ ] **Step 6: Commit**

```bash
git add src/leefomgevinglab/usecases/kmg/service.py tests/test_kmg_service.py
git commit -m "feat(llab): de drie lagen samengevoegd per meetpunt

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>"
```

---

### Task 6: Routes en het dossier

**Files:**
- Modify: `src/leefomgevinglab/geluidsmeter/api.py`
- Modify: `src/leefomgevinglab/usecases/water_hub.py`
- Test: `tests/test_api_kmg.py`

**Interfaces:**
- Consumes: `service.meetpunten/beeld` (Task 5), `_waterpagina()` (bestaand)
- Produces: routes `GET /kmg`, `GET /api/kmg/meetpunten`, `GET /api/kmg?meetpunt=&live=`

- [ ] **Step 1: Schrijf de falende test**

Maak `tests/test_api_kmg.py`:

```python
from fastapi.testclient import TestClient

import leefomgevinglab.geluidsmeter.api as api
from leefomgevinglab.usecases import water_hub as wh


def _client(monkeypatch):
    monkeypatch.setattr(api, "load_config", lambda *a, **k: api._config)
    return TestClient(api.app)


def test_meetpunten_endpoint(monkeypatch):
    r = _client(monkeypatch).get("/api/kmg/meetpunten")
    assert r.status_code == 200
    assert isinstance(r.json(), list)


def test_onbekend_meetpunt_geeft_404(monkeypatch):
    r = _client(monkeypatch).get("/api/kmg?meetpunt=BESTAAT_NIET&live=0")
    assert r.status_code == 404


def test_pagina_geeft_200_met_de_subnav(monkeypatch):
    r = _client(monkeypatch).get("/kmg")
    assert r.status_code == 200
    assert 'class="waternav"' in r.text
    assert r.text.count('aria-current="page"') == 1
    assert "__WATERNAV__" not in r.text
    assert "/api/kmg" in r.text


def test_het_dossier_heeft_nu_zes_leden():
    assert len(wh.LEDEN) == 6
    assert wh.lid("kmg")["pad"] == "/kmg"


def test_het_nieuwe_lid_verantwoordt_zijn_bronnen():
    l = wh.lid("kmg")
    assert "Waterkwaliteitsportaal" in " ".join(l["live"] + l["synthetisch"])
```

- [ ] **Step 2: Draai de test en zie hem falen**

Run: `.venv/bin/python -m pytest tests/test_api_kmg.py -v`
Expected: FAIL — 404 op de routes, en `len(wh.LEDEN) == 5`

- [ ] **Step 3: Voeg het lid toe aan het dossier**

In `src/leefomgevinglab/usecases/water_hub.py`, ná het lid `knelpunten`:

```python
    {"id": "kmg", "pad": "/kmg", "label": "Kan · mag · gebeurt",
     "titel": "Drie lagen over elkaar, met de metingen erbij",
     "samenvatting": "Wat de regels toestaan, wat er vergund is en wat er gemeten wordt — en "
                     "welke vergunningen aan een overschrijding kunnen bijdragen.",
     "live": ["DSO Ozon", "Atlas voor een Schone Maas"],
     "synthetisch": ["toerekeningsmodel van dit lab",
                     "momentopname Waterkwaliteitsportaal (geen machine-ingang)"]},
```

Neem het lid ook op in de lijn `register` in `LIJNEN`, want het gaat over hetzelfde gat.

- [ ] **Step 4: Voeg de routes toe**

In `api.py`, bij de imports:

```python
from leefomgevinglab.usecases.kmg import service as kmg_service
```

Direct ná `api_waterruimte`:

```python
def _kmg_pad() -> str:
    return _config.get("leefomgevinglab", {}).get("kmg", {}).get(
        "metingen_pad", "/mnt/nvme/geluidsmeter/data/external/wkp/metingen_2025.json")


@app.get("/kmg", response_class=HTMLResponse)
def kmg_page():
    """Kan, mag en gebeurt op het water — de drie lagen over elkaar."""
    return _waterpagina("kmg.html", "kmg")


@app.get("/api/kmg/meetpunten")
def api_kmg_meetpunten():
    return kmg_service.meetpunten(_kmg_pad())


@app.get("/api/kmg")
def api_kmg(meetpunt: str, live: int = 1):
    try:
        return kmg_service.beeld(meetpunt, _kmg_pad(), live=bool(live))
    except KeyError:
        raise HTTPException(status_code=404, detail=f"onbekend meetpunt: {meetpunt}")
```

- [ ] **Step 5: Draai de tests**

Run: `.venv/bin/python -m pytest tests/test_api_kmg.py tests/test_water_hub.py tests/test_api_water.py -v`
Expected: de paginatest faalt nog (`kmg.html` bestaat niet); de rest slaagt. Markeer die ene tot Task 7 met `@pytest.mark.xfail(reason="pagina volgt in Task 7", strict=True)`.

- [ ] **Step 6: Commit**

```bash
git add src/leefomgevinglab/geluidsmeter/api.py src/leefomgevinglab/usecases/water_hub.py tests/test_api_kmg.py
git commit -m "feat(llab): routes en dossierlid voor kan-mag-gebeurt

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>"
```

---

### Task 7: De pagina

**Files:**
- Create: `src/leefomgevinglab/static/kmg.html`
- Modify: `tests/test_api_kmg.py` (xfail weghalen)

**Interfaces:**
- Consumes: `GET /api/kmg/meetpunten` en `GET /api/kmg` (Task 6)

- [ ] **Step 1: Haal de xfail weg en zie de test falen**

Run: `.venv/bin/python -m pytest tests/test_api_kmg.py::test_pagina_geeft_200_met_de_subnav -v`
Expected: FAIL — `FileNotFoundError: … kmg.html`

- [ ] **Step 2: Schrijf de pagina**

Maak `src/leefomgevinglab/static/kmg.html`. Neem de opzet van `static/waterruimte.html` over: dezelfde `:root`-variabelen (`--bg:#080c14`, `--panel`, `--text` — **niet** `--paneel`/`--tekst`), hetzelfde `.waternav`-blok met de selector `.waternav a[aria-current]`, en de `__WATERNAV__`-placeholder ná `</header>`.

Structuur van de pagina:

- Een keuzelijst bovenaan met de meetpunten uit `/api/kmg/meetpunten`, met het waterlichaam erbij, stroomafwaarts gesorteerd.
- Drie blokken onder elkaar in de volgorde van de folder, elk met een gekleurde kop: **Kan** (groen), **Mag** (oranje), **Gebeurt** (blauw). Zelfde kleurtaal als de folder.
- Per stof in *Gebeurt*: de mediaan, het maximum, het aantal metingen en de periode. Staat er geen KRW-doel, dan een regel die dat zegt in plaats van een oordeel.
- Onder de drie blokken het staafdiagram van bijdragen per stof: één balk per vergunning plus een balk voor het restant, met de labels uit `bijdragen[].posten[].naam` en `restant_label`.
- Onderaan de proclaimer: de vier kopjes uit `proclaimer.kopjes`, elk met kop en tekst.

Escaping: haal élke waarde die uit de API komt door een `esc()`-helper, net als `waterruimte.html` dat doet — bedrijfsnamen, regelingtitels en redenen komen uit externe bronnen.

Robuustheid: `gebeurt.beschikbaar === false`, een leeg `mag.register`, een lege `bijdragen`-lijst en een ontbrekend `rd` moeten allemaal een leesbare regel opleveren en geen `undefined` in beeld.

Mobiel: de pagina moet bruikbaar zijn op 390 px. Voeg een `@media (max-width: 900px)` toe die de blokken onder elkaar zet en vaste breedtes loslaat — `/waterruimte` had dat aanvankelijk niet en was daardoor op een telefoon onbruikbaar.

- [ ] **Step 3: Draai de tests en zie ze slagen**

Run: `.venv/bin/python -m pytest tests/test_api_kmg.py -v`
Expected: PASS — 5 passed, 0 xfailed, 0 xpassed

- [ ] **Step 4: Controleer de pagina echt**

```bash
set -a && . ./.env && set +a
.venv/bin/python -c "
import sys; sys.path.insert(0,'src')
from fastapi.testclient import TestClient
import leefomgevinglab.geluidsmeter.api as api
c=TestClient(api.app)
h=c.get('/kmg').text
print('placeholder weg:', '__WATERNAV__' not in h)
print('actief item    :', h.count('aria-current=\"page\"'))
print('mediaquery     :', h.count('@media'))
for v in ('--paneel','--tekst'): print(f'{v} (hoort er NIET te staan):', v in h)
"
```

- [ ] **Step 5: Commit**

```bash
git add src/leefomgevinglab/static/kmg.html tests/test_api_kmg.py
git commit -m "feat(llab): de pagina kan-mag-gebeurt met de proclaimer

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>"
```

---

### Task 8: Live verifiëren en vastleggen

**Files:**
- Modify: `CLAUDE.md`
- Test: de hele suite

- [ ] **Step 1: Draai de hele suite**

Run: `.venv/bin/python -m pytest -q`
Expected: 580 + de nieuwe tests, 0 failed, 0 xfailed, 0 xpassed

- [ ] **Step 2: Herstart de dienst en controleer de routes**

```bash
sudo systemctl restart leefomgevinglab-api && sleep 4
for p in /water /waterruimte /gebruiksruimte /lozing /balo /dvth /kmg; do
  printf "%-16s %s\n" "$p" "$(curl -s -o /dev/null -w '%{http_code}' http://localhost:8792$p)"
done
curl -s "http://localhost:8792/api/kmg/meetpunten" | python3 -c "
import sys,json; d=json.load(sys.stdin)
print(len(d),'meetpunten'); [print(' ',p['code'],p['naam'],p.get('waterlichaam_naam')) for p in d[:5]]"
```

Verwacht: zeven keer 200 en een lijst meetpunten met Eijsden ponton erbij.

- [ ] **Step 3: Controleer één meetpunt live**

```bash
curl -s "http://localhost:8792/api/kmg?meetpunt=NL80_EIJSDPTN&live=1" | python3 -c "
import sys,json; d=json.load(sys.stdin)
print('meetpunt :', d['meetpunt']['naam'], '|', d['meetpunt'].get('waterlichaam_naam'))
print('kan      :', d['kan']['status'], len(d['kan'].get('regelingen',[])), 'regelingen')
print('mag      :', d['mag']['status'], len(d['mag'].get('register',[])), 'vergunningen')
print('gebeurt  :', [(s['code'], s['mediaan'], s['eenheid']) for s in d['gebeurt']['stoffen']])
print('proclaimer:', len(d['proclaimer']['kopjes']), 'kopjes')
print('voorbehoud aanwezig:', all('bovengrens' in b['voorbehoud'].lower() for b in d['bijdragen']))"
```

Zet de uitvoer in je verslag.

- [ ] **Step 4: Werk `CLAUDE.md` bij**

Voeg onder "Sprint status" toe, ná de regel over de prik-op-de-kaart:

```markdown
- ✅ **Kan · mag · gebeurt (`/kmg`, `/api/kmg?meetpunt=&live=`):** de drie lagen van de
  DSO-voorlichtingsfolder toegepast op water. **Kan** uit het DSO (live), **mag** uit de Atlas
  voor een Schone Maas (live), **gebeurt** uit het Waterkwaliteitsportaal van Informatiehuis
  Water — meetjaar 2025, 322 RWS-meetpunten, Aquo IM Metingen. `scripts/13_fetch_wkp_metingen.py`
  verdicht 142 MB CSV tot mediaan en maximum per meetpunt en stof. **Twee valkuilen van die
  bron:** `MonsterCompartimentCode` is bij chemische metingen leeg (filteren op `OW` geeft nul
  stikstof- en zinkmetingen), en `KwaliteitsoordeelCode = '99'` ("Hiaat waarde") draagt de
  sentinel `999999999999` — 3000 van de 384.132 rijen. **Geen machine-ingang:** de Digitale
  Delta API van RWS geeft 401 op elk data-eindpunt en de WKP-module die dit oplost komt begin
  2027; de meetset is dus een handmatige momentopname. Het toerekeningsmodel
  (`usecases/kmg/toerekening.py`) deelt de vergunde vracht van bovenstroomse lozingen over de
  jaarafvoer en is **uitdrukkelijk een bovengrens, geen vaststelling** — de woorden "veroorzaakt
  door" staan niet op de pagina, en een test bewaakt dat. De stroomvolgorde van de Maas
  (Bovenmaas → Grensmaas → Zandmaas → Bedijkte Maas → Beneden Maas → Bergsche Maas →
  Haringvliet) is een keuze van dit lab; de bron kent geen volgorde. De pagina draagt een
  **proclaimer** die uit de data zelf wordt opgebouwd, zodat tekst en getallen niet uit de pas
  kunnen lopen.
```

- [ ] **Step 5: Commit**

```bash
git add CLAUDE.md
git commit -m "docs(llab): sprintstatus kan-mag-gebeurt, met de valkuilen van de WKP-bron

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>"
```

---

## Zelfcontrole van dit plan

**Spec-dekking:**

| Spec | Taak |
|---|---|
| §1 Voorwaarde vooraf (KRW-doelen ontbreken) | 4 (proclaimer meldt het), 5 (`doelen_beschikbaar=False`), 7 (pagina toont geen oordeel) |
| §2 drie lagen met herkomst | 5, 6 (dossierlid), 7 |
| §3 wat de meetdata bevat | 1 (de twee valkuilen zijn tests) |
| §4.1 bron en opslag | 1 stap 5, 2 (config) |
| §4.2 verdichting | 1 |
| §4.3 norm moet echt worden | 4, 5 — `doelen_beschikbaar` staat op `False` tot de download er is |
| §5.1 wat het model doet | 3 |
| §5.2 wat het niet doet | 3 (`VOORBEHOUD`), 4 (proclaimer) |
| §5.3 de harde regel | 3 (test op "veroorzaakt"), 4 (test op "toezicht") |
| §6 de proclaimer | 4 |
| §7 de pagina | 7 |
| §8 tests | 1-7 |
| §9 bestanden | bestandsoverzicht hierboven |
| §10 risico's | 1 (sentinel), 3 (volgorde als tabel met test), 4 (datum uit data), 7 (mobiel) |

**Typeconsistentie nagelopen:** `verdicht()` levert de structuur die `metingen.laad()` leest;
`metingen.punt()` levert het punt dat `service.beeld()` gebruikt; `toerekening.bijdragen()`
krijgt registerposten met `kenmerk` en `vrachten`, precies wat `atlas_register.naar_register()`
produceert; `proclaimer.bouw()` krijgt de meetset en de registerbron zoals `service` ze heeft.

**Twee dingen waar de uitvoerder op moet letten:**

1. **`doelen_beschikbaar` staat in Task 5 hardgecodeerd op `False`.** Dat is bewust: de
   KRW-doelen zijn nog niet opgehaald, en terugvallen op de labnormen is volgens spec §4.3
   verboden. Komt die download er, dan is dit de plek waar hij binnenkomt.
2. **De jaarafvoer per waterlichaam in `service.DEBIET_M3_S` is een labkeuze**, net als de
   stroomvolgorde. De KRW-service levert geen afvoergegevens. Zet dat in het commentaar en laat
   het in de proclaimer terugkomen, anders lijkt het een gegeven uit een bron.
