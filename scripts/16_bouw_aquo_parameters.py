#!/usr/bin/env python3
"""De parameterreferentie: een Nederlandse stofnaam naar een Aquo-code.

Om een vergunningvoorschrift te codificeren heb je een tabel nodig die een stofnaam aan een code
koppelt. Dat is de **Aquo-domeintabel Parameter**, en die is gewoon op te halen — aquo.nl is een
wiki en publiceert elke domeintabel als CSV:

    https://www.aquo.nl/images/aquo/a/a3/Parameter.csv

Dat is de bron die dit script bij voorkeur gebruikt (`--aquo`). 7110 regels, waarvan 5623 geldig,
met per parameter een code, een omschrijving, alternatieve termen, een CAS-nummer, een
geldigheidsperiode en — als een code vervallen is — waardoor hij vervangen is. Vervallen codes
worden hier overgeslagen: een voorschrift koppelen aan een code die niet meer geldt, is erger dan
hem niet koppelen.

**De terugval.** Zonder die tabel kan dit script de koppeling ook afleiden uit de WKP-meetwaarden,
die Aquo-conform zijn en per rij zowel `ParameterCode` als `ParameterOmschrijving` dragen. Dat werkt,
maar het is de doorsnede van één levering: 492 parameters uit de monitoring van Rijkswaterstaat.
Wat RWS niet chemisch meet ontbreekt, hoe gewoon het in een vergunning ook is.

**Het verschil is gemeten, niet geschat.** Op de 367 Atlas-voorschriften rond Belfeld:

    afgeleid uit de WKP-meetset   210 van 367 bruikbaar (57%)
    echte Aquo-domeintabel        309 van 367 bruikbaar (84%)

De winst zit in alledaagse begrippen die RWS niet als chemische meting publiceert maar die wel in
elke vergunning staan: `Zuurgraad` → `pH`, `Zwevende stof` → `ZS`, `Debiet` → `Q`,
`stikstof Kjeldahl` → `NKj`, `Biochemisch zuurstofverbruik` → `BZV`. En ook het samengestelde
voorschrift "som 6 metalen (Zn, Cu, Pb, Ni, Cr, As)" blijkt gewoon een code te hebben: `smetln6`.

Draaien — bij voorkeur met de echte tabel:

    PYTHONPATH=src .venv/bin/python scripts/16_bouw_aquo_parameters.py \\
      --aquo /mnt/nvme/geluidsmeter/data/external/wkp/aquo_Parameter.csv \\
      --uit /mnt/nvme/geluidsmeter/data/external/wkp/aquo_parameters.json

of, als terugval, afgeleid uit een meetbestand:

    PYTHONPATH=src .venv/bin/python scripts/16_bouw_aquo_parameters.py \\
      --meetwaarden <WKP_Meetwaarden_*.csv> --uit <pad>
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


def uit_aquo(pad: str) -> dict:
    """De officiële Aquo-domeintabel Parameter lezen.

    Vervallen codes gaan er hier uit. De tabel draagt ze bewust nog — met `Vervangen door` erbij —
    maar een voorschrift koppelen aan een code die niet meer geldt levert een schijnzekerheid op.
    Alternatieve termen tellen mee als ingang: daar zitten juist de schrijfwijzen in die een
    vergunning gebruikt.
    """
    parameters: dict[str, list[str]] = {}
    op_naam: dict[str, list[str]] = {}
    rijen = vervallen = 0
    with open(pad, encoding="utf-8-sig", newline="") as f:
        for r in csv.DictReader(f, delimiter=";"):
            rijen += 1
            code = (r.get("Codes") or "").strip()
            if not code:
                continue
            if (r.get("Status") or "").strip().lower() == "vervallen":
                vervallen += 1
                continue
            namen = [n.strip() for veld in ("Omschrijving", "Alternatieve term")
                     for n in (r.get(veld) or "").split("|") if n.strip()]
            if namen:
                parameters[code] = sorted(set(namen))
            for naam in namen:
                op_naam.setdefault(normaliseer(naam), []).append(code)

    meerduidig = {n: c for n, c in op_naam.items() if len(set(c)) > 1}
    return {
        "bron": {"naam": "Aquo-domeintabel Parameter", "houder": "Informatiehuis Water",
                 "url": "https://www.aquo.nl/images/aquo/a/a3/Parameter.csv",
                 "let_op": "vervallen codes zijn overgeslagen"},
        "opgehaald_op": datetime.now(timezone.utc).strftime("%Y-%m-%d"),
        "parameters": parameters,
        "op_naam": {n: c[0] for n, c in op_naam.items() if len(set(c)) == 1},
        "meerduidig": {n: sorted(set(c)) for n, c in meerduidig.items()},
        "telling": {"rijen": rijen, "vervallen": vervallen, "codes": len(parameters),
                    "namen": len(op_naam), "meerduidig": len(meerduidig)},
    }


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
    ap.add_argument("--aquo", default=None,
                    help="pad naar de Aquo-domeintabel Parameter.csv (aanbevolen bron)")
    ap.add_argument("--meetwaarden", default=None,
                    help="pad naar WKP_Meetwaarden_*.csv (terugval: afleiden uit een levering)")
    ap.add_argument("--uit", required=True, help="pad voor de parameterreferentie")
    a = ap.parse_args()

    if not a.aquo and not a.meetwaarden:
        ap.error("geef --aquo (de echte domeintabel) of --meetwaarden (de terugval)")
    d = uit_aquo(a.aquo) if a.aquo else verdicht(a.meetwaarden)
    uit = Path(a.uit)
    uit.parent.mkdir(parents=True, exist_ok=True)
    uit.write_text(json.dumps(d, ensure_ascii=False, indent=1))
    t = d["telling"]
    print(f"{t['codes']} parameters, {t['namen']} namen "
          f"({t['meerduidig']} meerduidig, niet gekoppeld) uit {t['rijen']} rijen"
          + (f", {t['vervallen']} vervallen overgeslagen" if t.get("vervallen") else "")
          + f" -> {uit}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
