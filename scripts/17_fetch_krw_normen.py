#!/usr/bin/env python3
"""De chemische KRW-normen per meetpunt uit de toetsresultaten halen.

Waarom dit naast `scripts/15` bestaat. Het doelenbestand draagt de ecologische en
fysisch-chemische doelen per waterlichaam — stikstof hoort daarbij — maar **geen enkele chemische
stof**. De normen voor zink en de andere specifieke verontreinigende stoffen staan landelijk in
het Bkl, en de waarde die op een concreet punt is toegepast staat in `KRW-toetsresultaten`. Dat is
dezelfde download; hij was alleen nog niet uitgepakt.

**De koppeling is het lastigste deel en is uitgezocht, niet aangenomen.** Rijkswaterstaat
publiceert metingen onder namespace `NL80` en toetsingen onder stroomgebiedsnamespaces (`NL91`,
`NL94`, …). Hetzelfde fysieke punt heeft dus twee identiteiten en er is geen verklaarde relatie.
Wat wél gelijk blijft is de lokale identificatie: `NL80_BELFBVN` en `NL91_BELFBVN` delen
`BELFBVN`. De regel die hier wordt toegepast:

    match op MeetobjectLokaalID, én namespace == het voorvoegsel van het waterlichaam
    NL91ZM → NL91   ·   NL94_6 → NL94

Die regel klopt voor alle punten die matchen; zes van de negen Maas-meetpunten komen zo aan een
zinktoets. De andere drie — Innamewerk Heel, Brakel en Stad aan 't Haringvliet — zijn geen
KRW-toetspunt voor deze stoffen. Dat is een bevinding en geen fout, en zij krijgen hier dus niets.

**Twee normen per stof, en ze horen bij verschillende grootheden.** Binnen hetzelfde normstelsel
staan voor zink een JG-MKN en een MAC-MKN naast elkaar — bij Belfeld ≤ 7,80 en ≤ 16,6 µg/l. Welke
welke is, staat er met zoveel woorden bij in `WaardebewerkingsmethodeOmschrijving`:
"Jaargemiddelde" respectievelijk "Maximum". Er wordt hier dus niet geraden op grond van de laagste
waarde; de bron zegt het zelf, en `scripts/13` berekent beide grootheden.

**De norm verschilt per punt.** Voor zink is hij gecorrigeerd voor biobeschikbaarheid, dus hij
hangt af van de waterchemie ter plaatse: ≤ 7,80 µg/l op de Maas maar ≤ 3,99 bij de
Haringvlietsluis. Eén landelijke waarde aanhouden zou daar een derde te streng of te ruim zijn.

**Let op de jaren.** De toetsing loopt tot en met 2024, de metingen van dit lab zijn van 2025. De
norm reist dus mee met zijn eigen meetjaar en de pagina hoort dat verschil te benoemen.

Draaien:

    PYTHONPATH=src .venv/bin/python scripts/17_fetch_krw_normen.py \\
      <WKP_KRW-toetsresultaten_Nederland_*.csv> \\
      --metingen /mnt/nvme/geluidsmeter/data/external/wkp/metingen_2025.json \\
      --uit /mnt/nvme/geluidsmeter/data/external/wkp/krw_normen.json
"""
import argparse
import csv
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

# Welke bewerkingsmethode bij welke grootheid uit onze meetset hoort. De sleutel is wat de bron
# zelf opschrijft; de waarde is het veld dat `scripts/13` berekent.
GRONDSLAG = {
    "jaargemiddelde": "jaargemiddelde",
    "maximum": "maximum",
    "zomergemiddelde": "zomergemiddelde",
}


def _getal(s: str):
    s = (s or "").strip().replace("<=", "").replace("<", "").replace(",", ".").strip()
    try:
        return float(s)
    except ValueError:
        return None


def _namespace_van(waterlichaam: str) -> str:
    """Het stroomgebiedsvoorvoegsel waaronder de toetsing van dit waterlichaam is gepubliceerd."""
    wl = (waterlichaam or "").strip()
    return wl.split("_")[0][:4] if wl.startswith("NL94") else wl[:4]


def verdicht(toets_pad: str, metingen_pad: str) -> dict:
    meetset = json.loads(Path(metingen_pad).read_text(encoding="utf-8"))
    # lokale identificatie -> (meetpuntcode, verwachte namespace)
    wil = {}
    for p in meetset.get("punten") or []:
        code = (p.get("code") or "")
        lokaal = code.split("_", 1)[1] if "_" in code else code
        wil[lokaal] = (code, _namespace_van(p.get("waterlichaam") or ""))

    csv.field_size_limit(10 ** 7)
    gevonden: dict[str, dict] = {}
    rijen = 0
    with open(toets_pad, encoding="utf-8-sig", newline="") as f:
        for r in csv.DictReader(f, delimiter=";"):
            rijen += 1
            lokaal = (r.get("MeetobjectLokaalID") or "").strip()
            doel = wil.get(lokaal)
            if not doel or (r.get("MeetobjectNamespace") or "").strip() != doel[1]:
                continue
            bewerking = (r.get("WaardebewerkingsmethodeOmschrijving") or "").strip().lower()
            grondslag = GRONDSLAG.get(bewerking)
            norm = _getal(r.get("Normwaarde", ""))
            if grondslag is None or norm is None:
                continue
            eenheid = (r.get("EenheidCode") or "").strip()
            # Alleen echte slaag-zakgrenzen overnemen. In hetzelfde bestand staan ook de
            # klassengrenzen van de fysisch-chemische maatlatten, en die zijn iets anders: daar is
            # `Normwaarde` de bovengrens van de klasse waarin de waarde viel, niet een norm. Bij
            # Eijsden levert dat voor stikstof 5,0 ("Matig") terwijl het doel 2,5 is. Wie die twee
            # door elkaar haalt, laat elk meetpunt slagen. Het onderscheid zit in het oordeel:
            # "Voldoet" hoort bij een norm, een klassenaam bij een maatlat.
            if (r.get("ClassificatieOmschrijving") or "").strip().lower() not in (
                    "voldoet", "voldoet niet"):
                continue
            if eenheid == "DIMSLS":
                # De dimensieloze reeks is de risicoverhouding, geen concentratienorm. Die laten
                # we hier liggen: hem naast een gemeten concentratie zetten zou onzin opleveren.
                continue
            sleutel = "|".join([doel[0], (r.get("ParameterCode") or "").strip(),
                                (r.get("HoedanigheidCode") or "").strip(), eenheid, grondslag])
            jaar = (r.get("Meetjaar") or "").strip()
            huidig = gevonden.get(sleutel)
            if huidig is None or jaar > huidig["meetjaar"]:
                gevonden[sleutel] = {
                    "meetpunt": doel[0],
                    "parameter": (r.get("ParameterCode") or "").strip(),
                    "hoedanigheid": (r.get("HoedanigheidCode") or "").strip(),
                    "eenheid": eenheid,
                    "grondslag": grondslag,
                    "norm": norm,
                    "symbool": (r.get("Normwaarde") or "").strip()[:2].strip(),
                    "meetjaar": jaar,
                    "normgroep": (r.get("NormgroepOmschrijving") or "").strip(),
                    "getoetst": _getal(r.get("Numeriekewaarde", "")),
                    "klasse": (r.get("ClassificatieOmschrijving") or "").strip(),
                }

    per_punt: dict[str, list] = {}
    for v in gevonden.values():
        per_punt.setdefault(v["meetpunt"], []).append(v)
    for lijst in per_punt.values():
        lijst.sort(key=lambda v: (v["parameter"], v["hoedanigheid"], v["grondslag"]))

    zonder = sorted(c for c, _ in wil.values() if c not in per_punt)
    return {
        "bron": {"naam": "Waterkwaliteitsportaal — KRW-toetsresultaten",
                 "houder": "Informatiehuis Water",
                 "koppeling": ("op MeetobjectLokaalID plus de stroomgebiedsnamespace van het "
                               "waterlichaam; RWS publiceert metingen onder NL80 en toetsingen "
                               "onder NL91/NL94")},
        "opgehaald_op": datetime.now(timezone.utc).strftime("%Y-%m-%d"),
        "normen": per_punt,
        "zonder_toets": zonder,
        "telling": {"rijen": rijen, "meetpunten_gevraagd": len(wil),
                    "meetpunten_met_norm": len(per_punt), "normen": len(gevonden)},
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("toetsresultaten", help="pad naar WKP_KRW-toetsresultaten_*.csv")
    ap.add_argument("--metingen", required=True, help="pad naar de verdichte meetset")
    ap.add_argument("--uit", required=True, help="pad voor het normenbestand")
    a = ap.parse_args()

    d = verdicht(a.toetsresultaten, a.metingen)
    uit = Path(a.uit)
    uit.parent.mkdir(parents=True, exist_ok=True)
    uit.write_text(json.dumps(d, ensure_ascii=False, indent=1))
    t = d["telling"]
    print(f"{t['normen']} normen op {t['meetpunten_met_norm']} van {t['meetpunten_gevraagd']} "
          f"meetpunten, uit {t['rijen']} rijen -> {uit}")
    if d["zonder_toets"]:
        print("zonder KRW-toets: " + ", ".join(d["zonder_toets"]))
    return 0


if __name__ == "__main__":
    sys.exit(main())
