"""Verdicht de meetgegevens van het Waterkwaliteitsportaal tot een bruikbare set.

De downloadmodule van het Waterkwaliteitsportaal levert per waterbeheerder en meetjaar twee
CSV's: de meetobjecten (de punten) en de meetwaarden. Dat laatste bestand is voor één beheerder
al 142 MB — te groot om bij elke paginaweergave te lezen. Dit script maakt er één compact
bestand van: per meetpunt en stof het aantal metingen, de mediaan, het maximum en de periode.

De mediaan is de hoofdwaarde, niet het gemiddelde. Meetreeksen bevatten uitschieters — zink op
Eijsden heeft mediaan 4,54 en maximum 49,7 µg/l — en één piek mag het beeld niet bepalen. Het
maximum staat er apart bij, want dat is wat een normtoets interesseert.

Drie dingen die je bij deze bron moet weten, allemaal gemeten op 2026-10-01:

  * `MonsterCompartimentCode` is bij de chemische metingen **leeg**, niet `OW`. Wie daarop
    filtert houdt nul stikstof- en zinkmetingen over.
  * `KwaliteitsoordeelCode = '99'` betekent "Hiaat waarde" en draagt de sentinel
    999999999999 — 3000 van de 384.132 rijen. Zonder filter wordt het maximum onzin.
  * `Monsterophaaldatum` is bij de chemische metingen eveneens **leeg**. De datum staat in
    `Begindatum` (en dezelfde waarde nogmaals in `Resultaatdatum`). Wie alleen op
    `Monsterophaaldatum` leest, houdt voor elk punt en elke stof een lege periode over. Dit
    hoort in dezelfde familie als de eerste valkuil: deze bron laat velden leeg waar je ze
    verwacht.

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
            d = ((r.get("Monsterophaaldatum") or "").strip()
                 or (r.get("Begindatum") or "").strip()
                 or (r.get("Resultaatdatum") or "").strip())
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
