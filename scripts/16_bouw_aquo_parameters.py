#!/usr/bin/env python3
"""Een parameterreferentie afleiden uit de WKP-meetdata: code naast omschrijving.

Waarom dit bestand bestaat. Om een vergunningvoorschrift te codificeren heb je een referentietabel
nodig die een Nederlandse stofnaam aan een code koppelt. Die tabel is Aquo, en Aquo heeft er een
eigen ontsluiting voor — die dit lab niet geladen heeft. Wat we wél hebben is een levering die
Aquo-conform is: de WKP-meetwaarden dragen bij elke rij zowel `ParameterCode` als
`ParameterOmschrijving`. Daaruit valt de koppeling af te leiden, en dat is beter dan een lijst uit
het hoofd van de bouwer: elke regel is terug te voeren op een echte levering.

**Wat dit daarmee niet is.** Dit is geen volledige Aquo-domeintabel maar de doorsnede die in één
meetbestand voorkomt — 492 parameters uit de monitoring van Rijkswaterstaat over 2025. Stoffen die
RWS niet chemisch meet komen er niet in voor, hoe gewoon ze in een vergunning ook zijn: zwevende
stof, Kjeldahl-stikstof, debiet, temperatuur en minerale olie ontbreken alle vijf. Een voorschrift
daarover blijft dus ongecodeerd, en `lozingsmodel.py` meldt dat als zodanig in plaats van te gokken.
Een echte implementatie haalt deze tabel bij Aquo zelf; deze afleiding laat zien wat er dan gebeurt
en wat het oplevert.

Draaien:

    PYTHONPATH=src .venv/bin/python scripts/16_bouw_aquo_parameters.py \\
      /mnt/nvme/geluidsmeter/data/external/wkp/WKP_Meetwaarden_Rijkswaterstaat_2025_*.csv \\
      --uit /mnt/nvme/geluidsmeter/data/external/wkp/aquo_parameters.json
"""
import argparse
import csv
import json
import sys
from datetime import datetime, timezone
from pathlib import Path


def normaliseer(naam: str) -> str:
    """De sleutel waarop twee schrijfwijzen van dezelfde stof elkaar vinden.

    Bewust mager: kleine letters, koppeltekens als spatie, dubbele spaties weg. Geen synoniemen,
    geen stammen, geen fuzzy afstand — die zouden een treffer kunnen opleveren die niemand heeft
    gecontroleerd, en dat is precies het soort stille aanname dat dit dossier weigert.
    """
    return " ".join((naam or "").lower().replace("-", " ").split())


def verdicht(pad: str) -> dict:
    paren: dict[str, set[str]] = {}
    rijen = 0
    with open(pad, encoding="latin-1", newline="") as f:
        for r in csv.DictReader(f, delimiter=";"):
            rijen += 1
            code = (r.get("ParameterCode") or "").strip()
            oms = (r.get("ParameterOmschrijving") or "").strip()
            if code and oms:
                paren.setdefault(code, set()).add(oms)

    parameters = {code: sorted(omschrijvingen) for code, omschrijvingen in sorted(paren.items())}
    # De omgekeerde index is waar het om gaat: van een naam in een vergunning naar een code.
    # Levert een naam meer dan één code op, dan is hij niet eenduidig en wordt er niet gekoppeld.
    op_naam: dict[str, list[str]] = {}
    for code, omschrijvingen in parameters.items():
        for oms in omschrijvingen:
            op_naam.setdefault(normaliseer(oms), []).append(code)

    meerduidig = {n: c for n, c in op_naam.items() if len(c) > 1}
    return {
        "bron": {"naam": "WKP-meetwaarden Rijkswaterstaat",
                 "houder": "Informatiehuis Water",
                 "let_op": "doorsnede van één levering, geen volledige Aquo-domeintabel"},
        "opgehaald_op": datetime.now(timezone.utc).strftime("%Y-%m-%d"),
        "parameters": parameters,
        "op_naam": {n: c[0] for n, c in op_naam.items() if len(c) == 1},
        "meerduidig": {n: sorted(c) for n, c in meerduidig.items()},
        "telling": {"rijen": rijen, "codes": len(parameters),
                    "namen": len(op_naam), "meerduidig": len(meerduidig)},
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("meetwaarden", help="pad naar WKP_Meetwaarden_*.csv")
    ap.add_argument("--uit", required=True, help="pad voor de parameterreferentie")
    a = ap.parse_args()

    d = verdicht(a.meetwaarden)
    uit = Path(a.uit)
    uit.parent.mkdir(parents=True, exist_ok=True)
    uit.write_text(json.dumps(d, ensure_ascii=False, indent=1))
    t = d["telling"]
    print(f"{t['codes']} parameters, {t['namen']} namen "
          f"({t['meerduidig']} meerduidig, niet gekoppeld) uit {t['rijen']} rijen -> {uit}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
