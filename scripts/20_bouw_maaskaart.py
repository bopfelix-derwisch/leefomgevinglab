#!/usr/bin/env python3
"""De Maas als tekenbare kaart: geometrie vereenvoudigd tot wat een pagina aankan.

De KRW-service van Rijkswaterstaat levert de waterlichamen als polygonen, maar in volle
resolutie is dat ruim tien megabyte voor heel Nederland. Dat is geen kaart die je in een
browser opent. Dit script knipt het terug tot het Maasstroomgebied en vereenvoudigt de omtrek
tot een tolerantie waarbij de vorm herkenbaar blijft en het bestand onder een paar honderd
kilobyte uitkomt.

**Waarom geen achtergrondkaart.** Deze pagina tekent alleen wat uit een benoemde bron komt.
Een tegellaag eronder voegt herkenbaarheid toe maar ook een afhankelijkheid en een
licentievraag, en zij suggereert bovendien een nauwkeurigheid die de vereenvoudigde omtrek niet
heeft. De rivier zonder ondergrond is eerlijker over wat hij is.

**Alles blijft in RD** (EPSG:28992), hetzelfde stelsel als de vergunningen uit de Atlas en de
meetpunten uit het Waterkwaliteitsportaal. Zo is er nergens een projectie nodig en kan een
coördinaat uit welke bron dan ook rechtstreeks op deze kaart.

Draaien:

    PYTHONPATH=src .venv/bin/python scripts/20_bouw_maaskaart.py \\
        --uit /mnt/nvme/geluidsmeter/data/external/wkp/maaskaart.json
"""
import argparse
import json
import sys
from pathlib import Path

import httpx

from leefomgevinglab.usecases.kmg import stroomgebied, toerekening

KRW_WFS = "https://geo.rijkswaterstaat.nl/services/ogc/gdr/kaderrichtlijn_water/ows"
LAGEN = ("kaderrichtlijn_water:KRW_oppervlaktewaterlichamen_vlak",
         "kaderrichtlijn_water:KRW_oppervlaktewaterlichamen_lijn")

# Vereenvoudiging in meters. Op een kaart van ruim 200 kilometer hoog is 150 meter ruim onder
# een beeldpunt; de vorm blijft herkenbaar en het bestand wordt een factor 50 kleiner.
TOLERANTIE_M = 150.0
# Een waterlichaam waarvan na vereenvoudiging minder dan dit overblijft, is op deze schaal geen
# vorm meer maar een vlekje. Die laten we weg en tellen we apart, in plaats van hem als ruis op
# de kaart te zetten.
MINIMUM_OPPERVLAK_M2 = 200_000.0

# Kust- en territoriaal water blijven van de kaart. Niet omdat zij er niet bij horen, maar omdat
# zij het kader opblazen: het territoriale water is een blok van tientallen kilometers in zee,
# en met dat blok erbij wordt de rivier zelf een streepje. Het toerekeningsmodel laat ze om een
# andere reden al liggen -- voor kustwater bestaat geen jaarafvoer -- dus de kaart en het model
# tonen nu hetzelfde gebied. `owlcat` 3 is kustwater, 5 territoriaal water.
CATEGORIE_BUITEN_BEELD = {"3", "5"}


def haal(client: httpx.Client, laag: str) -> list[dict]:
    r = client.get(KRW_WFS, params={
        "service": "WFS", "version": "2.0.0", "request": "GetFeature",
        "typeNames": laag, "outputFormat": "application/json",
        "count": 500, "srsName": "EPSG:28992",
    })
    r.raise_for_status()
    return (r.json() or {}).get("features") or []


def vereenvoudig(features: list[dict], codes: set[str]) -> tuple[list[dict], dict]:
    """Alleen de gevraagde waterlichamen, met een vereenvoudigde omtrek."""
    from shapely.geometry import mapping, shape

    uit, telling = [], {"bekeken": len(features), "gehouden": 0, "te_klein": 0,
                        "buiten_beeld": 0, "punten_voor": 0, "punten_na": 0}
    for f in features:
        code = (f.get("properties") or {}).get("owl_id")
        if code not in codes:
            continue
        g = shape(f["geometry"])
        telling["punten_voor"] += len(json.dumps(f["geometry"]))
        klein = g.simplify(TOLERANTIE_M, preserve_topology=True)
        if klein.is_empty:
            telling["te_klein"] += 1
            continue
        if klein.geom_type in ("Polygon", "MultiPolygon") and klein.area < MINIMUM_OPPERVLAK_M2:
            telling["te_klein"] += 1
            continue
        p = f.get("properties") or {}
        if str(p.get("owlcat") or "") in CATEGORIE_BUITEN_BEELD:
            telling["buiten_beeld"] += 1
            continue
        uit.append({
            "code": code,
            "naam": (p.get("naam") or code),
            "categorie": p.get("owlcat"), "watertype": p.get("owltype"),
            "beheerder": p.get("wbhnaam"),
            "geometrie": mapping(klein),
        })
        telling["gehouden"] += 1
        telling["punten_na"] += len(json.dumps(mapping(klein)))
    return uit, telling


def bouw(uit_pad: Path, waterlichamen_pad: str | None = None) -> dict:
    register = stroomgebied.laad(waterlichamen_pad)
    if not register.get("beschikbaar"):
        raise SystemExit(register.get("reden"))
    codes = set(stroomgebied.codes_in_district(register, stroomgebied.DISTRICT_MAAS))

    vlakken, lijnen, telling = [], [], {}
    with httpx.Client(timeout=300.0) as client:
        for laag in LAGEN:
            fs = haal(client, laag)
            deel, t = vereenvoudig(fs, codes)
            (vlakken if laag.endswith("vlak") else lijnen).extend(deel)
            for k, v in t.items():
                telling[k] = telling.get(k, 0) + v

    # De grenzen van alles samen, zodat de pagina niet elk punt hoeft te doorlopen om te weten
    # hoe zij moet schalen.
    xs, ys = [], []
    for w in vlakken + lijnen:
        for c in _coords(w["geometrie"]):
            xs.append(c[0])
            ys.append(c[1])

    d = {
        "bron": {"naam": "KRW-oppervlaktewaterlichamen", "houder": "Rijkswaterstaat",
                 "url": KRW_WFS, "crs": "EPSG:28992"},
        "district": stroomgebied.DISTRICT_MAAS,
        "tolerantie_m": TOLERANTIE_M,
        "bbox": [min(xs), min(ys), max(xs), max(ys)] if xs else None,
        "vlakken": vlakken, "lijnen": lijnen,
        # De stroomvolgorde reist mee: zonder die ordening is de kaart een verzameling vormen
        # en kan de pagina niet zeggen wat bovenstrooms van wat ligt.
        "stroomvolgorde": [{"code": c, "naam": n,
                            "grond": toerekening.positie_grond(c)}
                           for c, n in toerekening.STROOMVOLGORDE],
        "zonder_positie": [{"code": c, "reden": r}
                           for c, r in sorted(toerekening.ZONDER_POSITIE.items())],
        "telling": {**telling, "in_district": len(codes),
                    "vlakken": len(vlakken), "lijnen": len(lijnen)},
    }
    uit_pad.parent.mkdir(parents=True, exist_ok=True)
    uit_pad.write_text(json.dumps(d, ensure_ascii=False, separators=(",", ":")))
    return {**d["telling"], "bytes": uit_pad.stat().st_size}


def _coords(geo: dict):
    """Alle coördinaten van een GeoJSON-geometrie, ongeacht haar diepte."""
    def _uit(x):
        if isinstance(x, (list, tuple)) and x and isinstance(x[0], (int, float)):
            yield x
        elif isinstance(x, (list, tuple)):
            for y in x:
                yield from _uit(y)
    yield from _uit(geo.get("coordinates") or [])


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--uit", required=True, help="pad voor het kaartbestand")
    ap.add_argument("--waterlichamen", default=None,
                    help="pad naar krw_waterlichamen.json (scripts/18)")
    a = ap.parse_args()
    t = bouw(Path(a.uit), a.waterlichamen)
    print(f"{t['vlakken']} vlakken + {t['lijnen']} lijnen van {t['in_district']} "
          f"waterlichamen in het district; {t['te_klein']} te klein voor deze schaal, "
          f"{t['buiten_beeld']} kust- of territoriaal water buiten beeld "
          f"-> {t['bytes'] // 1024} kB")
    return 0


if __name__ == "__main__":
    sys.exit(main())
