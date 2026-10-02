"""Verdicht de meetgegevens van het Waterkwaliteitsportaal tot een bruikbare set.

De downloadmodule van het Waterkwaliteitsportaal levert per waterbeheerder en meetjaar twee
CSV's: de meetobjecten (de punten) en de meetwaarden. Dat laatste bestand is voor één beheerder
al 142 MB — te groot om bij elke paginaweergave te lezen. Dit script maakt er één compact
bestand van: per meetpunt en stof het aantal metingen, de mediaan, het maximum en de periode.

De mediaan is de hoofdwaarde, niet het gemiddelde. Meetreeksen bevatten uitschieters — zink op
Eijsden heeft mediaan 4,54 en maximum 49,7 µg/l — en één piek mag het beeld niet bepalen. Het
maximum staat er apart bij, want dat is wat een normtoets interesseert.

Vier dingen die je bij deze bron moet weten, allemaal gemeten op 2026-10-01:

  * `MonsterCompartimentCode` is bij de chemische metingen **leeg**, niet `OW`. Wie daarop
    filtert houdt nul stikstof- en zinkmetingen over.
  * `KwaliteitsoordeelCode = '99'` betekent "Hiaat waarde" en draagt de sentinel
    999999999999 — 3000 van de 384.259 rijen, geteld over **alle** parameters in het bestand
    (niet beperkt tot de drie labstoffen; daarbinnen zijn het er maar 18). Zonder filter wordt
    het maximum onzin.
  * **`HoedanigheidCode` scheidt grootheden die er hetzelfde uitzien.** Zink staat op élk
    Maas-meetpunt in twee reeksen: `NVT` (totaal) en `nf` (opgelost, na filtratie). Bij Eijsden
    ponton is dat 52 metingen met mediaan 7,15 µg/l tegen 52 met mediaan 2,80. Sleutel je daar
    niet op, dan rolt er een mediaan van 4,54 uit — een concentratie die niemand heeft gemeten.
    De KRW-norm voor zink geldt bovendien voor de opgeloste fractie, dus poolen maakt ook het
    latere normoordeel onbruikbaar. Stikstof (`N`) en PFOA (`NVT`) zijn vandaag uniform, maar
    `Npg`/`Nnf` bestaan elders in dezelfde download.
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


# Het KRW-zomerhalfjaar voor de fysisch-chemische parameters: april tot en met september.
_ZOMERMAANDEN = {"04", "05", "06", "07", "08", "09"}


def verdicht(meetobjecten_pad: str, meetwaarden_pad: str,
             stoffen: set[str] | None = None) -> dict:
    """Twee CSV's in, één compacte structuur uit.

    Boekhouding in `telling`: `meegeteld` telt de rijen die de inhoudelijke filters doorstaan
    (stof, kwaliteitsoordeel, leesbare waarde). Een deel daarvan valt daarna alsnog af omdat het
    meetobject niet voorkomt in het meetobjectenbestand — dat aantal staat apart in
    `onbekend_meetobject`, als deelverzameling van `meegeteld` (geen aftrek ervan). De som van
    alle `n` over `punten` plus `onbekend_meetobject` is dus gelijk aan `meegeteld`.
    """
    stoffen = stoffen or LABSTOFFEN
    objecten = _lees_objecten(meetobjecten_pad)
    telling = {"rijen": 0, "meegeteld": 0, "hiaatwaarden": 0, "onleesbaar": 0,
               "buiten_stoffen": 0, "onbekend_meetobject": 0, "gemengde_eenheid": 0}
    verzameld = {}          # (puntcode, stofcode, hoedanigheid) -> dict met waarden
    meetjaar = None

    with open(meetwaarden_pad, encoding="utf-8-sig", newline="") as f:
        for r in csv.DictReader(f, delimiter=";"):
            telling["rijen"] += 1
            meetjaar = meetjaar or (r.get("Meetjaar") or "").strip() or None
            par = (r.get("ParameterCode") or "").strip()
            if par not in stoffen:
                telling["buiten_stoffen"] += 1
                continue
            if (r.get("KwaliteitsoordeelCode") or "").strip() not in GOEDE_OORDELEN:
                # Code '99' = "Hiaat waarde": draagt de sentinel 999999999999 i.p.v. een
                # echte meting. Andere afgekeurde codes vallen hier ook onder.
                telling["hiaatwaarden"] += 1
                continue
            waarde = _getal(r.get("Numeriekewaarde", ""))
            if waarde is None:
                telling["onleesbaar"] += 1
                continue
            punt = (r.get("MeetobjectCode") or "").strip()
            hoed = (r.get("HoedanigheidCode") or "").strip()
            eenheid = (r.get("EenheidCode") or "").strip()
            # Sleutelen op hoedanigheid is niet optioneel: zink komt op élk Maas-meetpunt in twee
            # reeksen voor, totaal (NVT) en opgelost na filtratie (nf), met medianen die een
            # factor 2,5 verschillen. Zonder deze sleutel worden die tot één mediaan gepoold en
            # staat er een concentratie op de pagina die niemand gemeten heeft.
            sleutel = (punt, par, hoed)
            v = verzameld.setdefault(sleutel, {
                "code": par,
                "naam": (r.get("ParameterOmschrijving") or par).strip(),
                "eenheid": eenheid,
                "hoedanigheid": hoed,
                "hoedanigheid_naam": (r.get("HoedanigheidOmschrijving") or "").strip(),
                "waarden": [], "onder_rapportagegrens": 0, "data": [], "eenheden": set(),
                "paren": [],
            })
            v["eenheden"].add(eenheid)
            v["waarden"].append(waarde)
            # Datum bij de waarde bewaren: het KRW-oordeel voor de fysisch-chemische parameters
            # gaat over het **zomergemiddelde**, niet over een jaargemiddelde of -mediaan. Zonder
            # de maand bij elke waarde is dat achteraf niet meer te berekenen.
            v["paren"].append((None, waarde))
            if (r.get("Limietsymbool") or "").strip() == "<":
                v["onder_rapportagegrens"] += 1
            d = ((r.get("Monsterophaaldatum") or "").strip()
                 or (r.get("Begindatum") or "").strip()
                 or (r.get("Resultaatdatum") or "").strip())
            if d:
                v["data"].append(d)
            v["paren"][-1] = (d or None, waarde)
            telling["meegeteld"] += 1

    punten = {}
    for (puntcode, _par, _hoed), v in verzameld.items():
        # De eenheid werd van de eerste rij van de reeks genomen. Controleer dat de rest
        # dezelfde draagt: een reeks met twee eenheden levert een mediaan over twee
        # grootheden, en dat is precies de aanname die dit lab al een factor 1000 heeft gekost.
        if len(v["eenheden"]) > 1:
            telling["gemengde_eenheid"] += len(v["waarden"])
            continue
        obj = objecten.get(puntcode)
        if obj is None:
            # Meetwaarde verwijst naar een MeetobjectCode die niet in het meetobjectenbestand
            # staat — de twee WKP-bestanden passen dan niet bij elkaar. Niet stil laten vallen.
            telling["onbekend_meetobject"] += len(v["waarden"])
            continue
        p = punten.setdefault(puntcode, {**obj, "stoffen": []})
        data = sorted(v["data"])
        zomer = [w for d, w in v["paren"] if d and d[5:7] in _ZOMERMAANDEN]
        p["stoffen"].append({
            "code": v["code"], "naam": v["naam"], "eenheid": v["eenheid"],
            "hoedanigheid": v["hoedanigheid"], "hoedanigheid_naam": v["hoedanigheid_naam"],
            "n": len(v["waarden"]),
            "mediaan": round(statistics.median(v["waarden"]), 6),
            "maximum": round(max(v["waarden"]), 6),
            "onder_rapportagegrens": v["onder_rapportagegrens"],
            # Het zomergemiddelde is de grootheid waartegen de KRW-klassengrenzen gelden. Apart
            # van de mediaan, want die twee zijn niet uitwisselbaar en een pagina die ze door
            # elkaar haalt toetst tegen de verkeerde norm.
            "zomergemiddelde": round(statistics.fmean(zomer), 6) if zomer else None,
            "n_zomer": len(zomer),
            "van": data[0] if data else None,
            "tot": data[-1] if data else None,
        })

    for p in punten.values():
        p["stoffen"].sort(key=lambda s: (s["code"], s["hoedanigheid"]))

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
          f"({t['hiaatwaarden']} hiaat, {t['onleesbaar']} onleesbaar, "
          f"{t['onbekend_meetobject']} onbekend meetobject, "
          f"{t['gemengde_eenheid']} gemengde eenheid) -> {uit}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
