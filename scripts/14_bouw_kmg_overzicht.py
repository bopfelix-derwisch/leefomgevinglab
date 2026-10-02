#!/usr/bin/env python3
"""Het overzicht over alle Maas-meetpunten voorberekenen tot een klein JSON-bestand.

Waarom voorberekend en niet live: één meetpunt kost koud ongeveer 166 seconden — de Atlas-bevraging
plus een KRW-opzoeking per unieke vergunningcoördinaat. Warm (binnen de cache-dag) is dat ruim 5
seconden. Negen punten live achter elkaar is dus 25 minuten koud, en dat kan geen pagina-aanroep
zijn; een eindpunt dat het parallel doet zou bovendien door de tunnel heen in een gateway-timeout
lopen én negen keer tegelijk op RWS en de Atlas inhakken.

Daarmee is dit overzicht een **momentopname**, net als de meetset zelf, en het draagt om die reden
een ophaaldatum die de pagina toont. Dat is eerlijker dan het lijkt: de metingen zijn al een
handmatige momentopname (de Digitale Delta geeft 401, de WKP-module komt begin 2027), dus een
voorberekend overzicht voegt geen nieuw soort onzekerheid toe.

Het bestand bevat per meetpunt alleen wat de strook nodig heeft: per stof de gemeten waarde, de
vergunde bovengrens en het aandeel. Geen namen van bedrijven — die horen bij het meetpunt zelf, en
een overzicht dat ze zou dupliceren loopt uit de pas zodra de Atlas wijzigt.

Draaien:

    PYTHONPATH=src GELUIDSMETER_CONFIG_PATH=$PWD/core/config.yaml \\
      .venv/bin/python scripts/14_bouw_kmg_overzicht.py \\
      --metingen /mnt/nvme/geluidsmeter/data/external/wkp/metingen_2025.json \\
      --uit /mnt/nvme/geluidsmeter/data/external/wkp/kmg_overzicht.json

Let op: `.env` moet geladen zijn (`set -a && . ./.env && set +a`) voor de DSO-sleutel. Zonder die
sleutel valt alleen de KAN-laag weg; het overzicht gebruikt die niet, dus het bestand blijft geldig.
"""
import argparse
import json
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

from leefomgevinglab.usecases.kmg import service


def _stof_regel(bijdrage: dict) -> dict:
    """Eén stof op één punt, teruggebracht tot wat de strook toont."""
    som = bijdrage.get("som_bovengrens") or 0.0
    rest = bijdrage.get("restant") or 0.0
    gemeten = som + rest
    toerekenbaar = bijdrage.get("toerekenbaar") is not False
    return {
        "code": bijdrage.get("stof"),
        "naam": bijdrage.get("naam"),
        "hoedanigheid": bijdrage.get("hoedanigheid"),
        "hoedanigheid_naam": bijdrage.get("hoedanigheid_naam"),
        "eenheid": bijdrage.get("eenheid"),
        "toerekenbaar": toerekenbaar,
        "reden": bijdrage.get("reden"),
        "gemeten": round(gemeten, 6),
        "vergund": round(som, 6),
        # Het aandeel is alleen zinvol bij een positieve meting en een niet-negatief restant. Een
        # negatief restant betekent dat de vergunde plafonds samen de meting overstijgen; dat is
        # geen fout maar ook geen percentage, en we verzinnen er dus geen.
        #
        # Een niet-toerekenbare reeks krijgt uitdrukkelijk `None` en niet 0,0 procent. Nul leest als
        # "er valt niets toe te rekenen", terwijl de waarheid is "deze twee grootheden zijn niet te
        # vergelijken" -- de vergunning begrenst de totale vracht, de meting betreft een fractie.
        # Dat onderscheid staat op de pagina en hoort dus ook in dit bestand.
        "aandeel_pct": (round(som / gemeten * 100, 2)
                        if toerekenbaar and gemeten > 0 and rest >= 0 else None),
        "posten": len(bijdrage.get("posten") or []),
        # Het KRW-oordeel hoort in de strook, want juist daar wordt duidelijk dat bijna de hele Maas
        # op dezelfde klasse uitkomt terwijl het vergunde aandeel sterk verschilt.
        "klasse": (bijdrage.get("doel") or {}).get("klasse"),
        "doel_waarde": (bijdrage.get("doel") or {}).get("goed_tot"),
        "getoetste_waarde": (bijdrage.get("doel") or {}).get("getoetste_waarde"),
        "doel_grondslag": (bijdrage.get("doel") or {}).get("grondslag"),
    }


def bouw(metingen_pad: str, straal_m: int = 50000, doelen_pad: str | None = None) -> dict:
    punten = service.meetpunten(metingen_pad)
    uit = []
    for i, p in enumerate(punten, 1):
        t0 = time.time()
        b = service.beeld(p["code"], metingen_pad, live=True, straal_m=straal_m,
                          doelen_pad=doelen_pad)
        reg = b["mag"].get("register") or []
        in_band = sum(len(band.get("vergunningen") or [])
                      for band in b["stroomprofiel"]["banden"])
        uit.append({
            "code": p["code"], "naam": p.get("naam"),
            "waterlichaam": p.get("waterlichaam"),
            "waterlichaam_naam": p.get("waterlichaam_naam"),
            "register": len(reg),
            "in_band": in_band,
            "zonder_waterlichaam": len(b["stroomprofiel"].get("zonder_waterlichaam") or []),
            "mag_status": b["mag"].get("status"),
            "stoffen": [_stof_regel(x) for x in (b.get("bijdragen") or [])],
        })
        print(f"  [{i}/{len(punten)}] {p['code']:<22} {time.time() - t0:5.1f}s "
              f"· {len(reg)} vergunningen", flush=True)
    return {
        "opgehaald_op": datetime.now(timezone.utc).strftime("%Y-%m-%d"),
        "straal_m": straal_m,
        "punten": uit,
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--metingen", required=True, help="pad naar de verdichte meetset")
    ap.add_argument("--uit", required=True, help="pad voor het overzicht-JSON")
    ap.add_argument("--straal", type=int, default=50000, help="zoekstraal in meters")
    ap.add_argument("--doelen", default=None, help="pad naar de verdichte KRW-doelen")
    a = ap.parse_args()

    d = bouw(a.metingen, straal_m=a.straal, doelen_pad=a.doelen)
    uit = Path(a.uit)
    uit.parent.mkdir(parents=True, exist_ok=True)
    uit.write_text(json.dumps(d, ensure_ascii=False, indent=1))
    met = sum(1 for p in d["punten"] for s in p["stoffen"] if (s["aandeel_pct"] or 0) > 0)
    print(f"{len(d['punten'])} meetpunten, {met} stof-punt-combinaties met een vergund aandeel "
          f"-> {uit}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
