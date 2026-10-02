#!/usr/bin/env python3
"""De KRW-doelen per waterlichaam verdichten tot een klein JSON-bestand.

Bron: `KRW-doelen`, Download Data-module van het Waterkwaliteitsportaal (Informatiehuis Water),
rapportagejaar 2025, verzameling "KRW-doelen-2025 (corr. 2024)". Zelfde module en zelfde handmatige
weg als de meetwaarden — er is geen machine-ingang.

**Wat hier wel in staat en wat niet.** Dit bestand draagt de *ecologische en fysisch-chemische*
doelen die per waterlichaam worden vastgesteld: twaalf kwaliteitselementen, waaronder `Ntot`,
`Ptot`, `O2`, `pH`, `Cl` en de biologische (vis, macrofauna, flora). Er staat **geen enkele
chemische stof** in: geen zink, geen PFOA, geen metalen. Dat is geen omissie van de download maar
de systematiek — de normen voor chemische stoffen zijn landelijk en staan in het Bkl (bijlage III
voor prioritaire stoffen, IIIa voor de Nederlandse specifieke verontreinigende stoffen). Wie hier
zink zoekt, zoekt in het verkeerde bestand.

**Twee dingen die het bestand zelf niet zegt en die hier zijn vastgelegd.** Er is geen kolom voor
de eenheid en geen voor de grondslag. Beide zijn afgeleid uit `KRW-toetsresultaten` van dezelfde
download: alle 6620 `Ntot`-toetsingen daarin staan in `mg/l` en gebruiken zonder uitzondering
bewerkingsmethode **`Zomergemiddelde`**. Dat is bepalend: een jaargemiddelde of -mediaan naast deze
klassengrenzen leggen is toetsen tegen de verkeerde grootheid. `scripts/13` berekent daarom een
zomergemiddelde over april tot en met september; het aantal waarden daarin (6 per punt) komt overeen
met `Aantalmeetwaarden_gebruikt` in de officiële toetsing.

**Let op het watertype.** Niet elk waterlichaam gebruikt hetzelfde element voor stikstof: de
Maas-waterlichamen van het type R7/R8 hebben `Ntot`, maar Haringvliet-west (NL94_11) heeft
`Nanorg` — anorganisch stikstof. Dit script bewaart wat er staat en vertaalt niets.

Draaien:

    PYTHONPATH=src .venv/bin/python scripts/15_fetch_krw_doelen.py \\
      /mnt/nvme/geluidsmeter/data/external/wkp/WKP_KRW-doelen_Nederland_2025_*.csv \\
      --uit /mnt/nvme/geluidsmeter/data/external/wkp/krw_doelen_2025.json
"""
import argparse
import csv
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

# Afgeleid uit KRW-toetsresultaten van dezelfde download, niet uit het doelenbestand zelf.
# Zonder deze twee is een klassengrens een getal zonder betekenis.
GRONDSLAG = {
    "Ntot": ("mg/l", "zomergemiddelde"),
    "Nanorg": ("mg/l", "zomergemiddelde"),
    "Ptot": ("mg/l", "zomergemiddelde"),
    "Cl": ("mg/l", "zomergemiddelde"),
    "O2": ("%", "zomergemiddelde"),
    "T": ("°C", "maximum"),
    "pH": ("", "zomergemiddelde"),
}


def _getal(s: str):
    s = (s or "").strip().replace(",", ".")
    if not s:
        return None
    try:
        return float(s)
    except ValueError:
        return None


def verdicht(pad: str) -> dict:
    doelen: dict[str, dict] = {}
    namen: dict[str, str] = {}
    watertypen: dict[str, str] = {}
    verzamelingen = set()
    rijen = 0

    with open(pad, encoding="utf-8-sig", newline="") as f:
        for r in csv.DictReader(f, delimiter=";"):
            rijen += 1
            wl = (r.get("WaterlichaamCode") or "").strip()
            el = (r.get("KRWkwaliteitselementCode") or "").strip()
            if not wl or not el:
                continue
            verzamelingen.add((r.get("KRWdoelenverzamelingNaam") or "").strip())
            namen[wl] = (r.get("WaterlichaamNaam") or "").strip()
            watertypen[wl] = (r.get("WaterlichaamKRWwatertypeCode") or "").strip()
            eenheid, grondslag = GRONDSLAG.get(el, ("", ""))
            d = doelen.setdefault(wl, {}).setdefault(el, {
                "code": el,
                "naam": (r.get("KRWkwaliteitselementOmschrijving") or el).strip(),
                "eenheid": eenheid,
                "grondslag": grondslag,
                "klassen": [],
                "goed_tot": None,
            })
            onder_s = (r.get("OndergrensSymbool") or "").strip()
            onder_w = _getal(r.get("OndergrensWaarde", ""))
            boven_s = (r.get("BovengrensSymbool") or "").strip()
            boven_w = _getal(r.get("BovengrensWaarde", ""))
            klasse = (r.get("Classificatie") or "").strip()
            d["klassen"].append({
                "klasse": klasse,
                "onder_symbool": onder_s, "onder": onder_w,
                "boven_symbool": boven_s, "boven": boven_w,
            })
            # De bovengrens van de klasse "goed" is het doel waar deze pagina tegen afzet. Alleen
            # die ene klasse; de rest is context voor de lezer.
            if klasse.lower() == "goed" and boven_w is not None:
                d["goed_tot"] = boven_w

    return {
        "bron": {"naam": "Waterkwaliteitsportaal — KRW-doelen",
                 "houder": "Informatiehuis Water",
                 "url": "https://www.waterkwaliteitsportaal.nl/krw-factsheets-en-gegevensbestanden",
                 "verzameling": sorted(v for v in verzamelingen if v)},
        "opgehaald_op": datetime.now(timezone.utc).strftime("%Y-%m-%d"),
        "waterlichamen": {wl: {"naam": namen.get(wl), "watertype": watertypen.get(wl),
                               "doelen": els}
                          for wl, els in doelen.items()},
        "telling": {"rijen": rijen, "waterlichamen": len(doelen),
                    "elementen": len({e for els in doelen.values() for e in els})},
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("doelen", help="pad naar WKP_KRW-doelen_*.csv")
    ap.add_argument("--uit", required=True, help="pad voor het verdichte JSON-bestand")
    a = ap.parse_args()

    d = verdicht(a.doelen)
    uit = Path(a.uit)
    uit.parent.mkdir(parents=True, exist_ok=True)
    uit.write_text(json.dumps(d, ensure_ascii=False, indent=1))
    t = d["telling"]
    print(f"{t['waterlichamen']} waterlichamen, {t['elementen']} kwaliteitselementen "
          f"uit {t['rijen']} rijen -> {uit}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
