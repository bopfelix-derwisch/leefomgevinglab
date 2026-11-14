"""Verdicht welke Aquo-codes ergens gemeten worden, voor `toezicht.signalen.
regel_geen_onafhankelijke_meting` (`context["gemeten_codes"]`).

Dit is een andere verdichting dan `scripts/13_fetch_wkp_metingen.py`. Dat script bewaart de
GEMETEN WAARDEN van drie stoffen (Ntot/Zn/PFOA) als mediaan en maximum per meetpunt. Het signaal
hier heeft geen waarde nodig, alleen het antwoord op "bestaat hier een onafhankelijke meting voor
deze stof" -- dus is de verdichting hier alleen de VERZAMELING Aquo-codes (`ParameterCode`) die
voorkomen op de meetpunten die dit lab al kent.

**Scope: dezelfde meetpunten als `metingen_2025.json`** (de `MeetobjectCode`'s die de drie
labstoffen droegen, 92 stuks), niet alle 322 RWS-meetpunten in de ruwe CSV. Live geteld
(2026-11-14): alle 322 meetpunten samen dragen 491 verschillende codes, de 92 bekende meetpunten
470-472 (afhankelijk van de kwaliteitsfilter) -- een klein verschil, niet een factor. De andere
230 meetpunten zijn overwegend biologische/ecologische monitoringpunten (fytoplankton, macrofauna
e.d.); die stoffen komen in een lozingsvoorschrift niet terug, en meetellen zou de illusie geven
dat dit lab een breder meetnet kent dan het elders al toont. `--alle-meetpunten` schakelt deze
beperking uit voor wie toch de volledige 322 wil.

Dezelfde kwaliteitsfilter als scripts/13 (`GOEDE_OORDELEN`): een rij met kwaliteitsoordeel '99'
(Hiaat waarde) draagt de sentinel 999999999999 in plaats van een echte meting en telt dus niet
als "hier wordt deze stof gemeten".

Er is, net als bij scripts/13, geen machine-ingang: dit blijft een momentopname die met de hand
wordt opgehaald.
"""
import argparse
import csv
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

# Zelfde kwaliteitsoordelen als scripts/13 -- '99' (Hiaat waarde) niet.
GOEDE_OORDELEN = {"00", "03", "90"}

BRON = {
    "naam": "Waterkwaliteitsportaal",
    "houder": "Informatiehuis Water",
    "url": "https://wkp.rws.nl/downloadmodule",
    "informatiemodel": "Aquo IM Metingen",
}


def _meetpuntcodes(metingen_pad: str) -> set[str]:
    """De `MeetobjectCode`'s uit een al-verdichte meetset (`scripts/13`'s uitkomst) -- de scope
    die deze verdichting standaard aanhoudt. Geen eigen lezing van de meetobjecten-CSV: die
    scope is al vastgelegd op de plek waar hij ontstond."""
    d = json.loads(Path(metingen_pad).read_text(encoding="utf-8"))
    return {p["code"] for p in d.get("punten") or [] if p.get("code")}


def verdicht(meetwaarden_pad: str, puntcodes: set[str] | None) -> dict:
    """De verzameling Aquo-codes op `puntcodes` (of alle meetpunten in het bestand als
    `puntcodes` `None` is), met de kwaliteitsfilter van `GOEDE_OORDELEN`."""
    codes: set[str] = set()
    telling = {"rijen": 0, "meegeteld": 0, "hiaatwaarden": 0, "buiten_meetpunten": 0, "leeg": 0}
    meetjaar = None
    with open(meetwaarden_pad, encoding="utf-8-sig", newline="") as f:
        for r in csv.DictReader(f, delimiter=";"):
            telling["rijen"] += 1
            meetjaar = meetjaar or (r.get("Meetjaar") or "").strip() or None
            punt = (r.get("MeetobjectCode") or "").strip()
            if puntcodes is not None and punt not in puntcodes:
                telling["buiten_meetpunten"] += 1
                continue
            if (r.get("KwaliteitsoordeelCode") or "").strip() not in GOEDE_OORDELEN:
                telling["hiaatwaarden"] += 1
                continue
            code = (r.get("ParameterCode") or "").strip()
            if not code:
                telling["leeg"] += 1
                continue
            codes.add(code)
            telling["meegeteld"] += 1
    return {
        "beschikbaar": True,
        "codes": sorted(codes),
        "aantal_codes": len(codes),
        "aantal_meetpunten": len(puntcodes) if puntcodes is not None else None,
        "meetjaar": meetjaar,
        "bron": BRON,
        "opgehaald_op": datetime.now(timezone.utc).strftime("%Y-%m-%d"),
        "telling": telling,
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("meetwaarden", help="pad naar WKP_Meetwaarden_*.csv")
    ap.add_argument("--metingen", required=True,
                     help="pad naar metingen_2025.json (scripts/13) -- levert de meetpuntenscope, "
                          "tenzij --alle-meetpunten is gegeven")
    ap.add_argument("--alle-meetpunten", action="store_true",
                     help="negeer de meetpuntenscope en tel alle meetpunten in de ruwe CSV mee")
    ap.add_argument("--uit", required=True, help="pad voor het verdichte JSON-bestand")
    a = ap.parse_args()

    puntcodes = None if a.alle_meetpunten else _meetpuntcodes(a.metingen)
    d = verdicht(a.meetwaarden, puntcodes)
    uit = Path(a.uit)
    uit.parent.mkdir(parents=True, exist_ok=True)
    uit.write_text(json.dumps(d, ensure_ascii=False, indent=1))
    t = d["telling"]
    print(f"{d['aantal_codes']} Aquo-codes"
          + (f" op {d['aantal_meetpunten']} meetpunten" if d['aantal_meetpunten'] is not None
             else " (alle meetpunten)")
          + f" (meegeteld {t['meegeteld']} van {t['rijen']} rijen, {t['hiaatwaarden']} hiaat, "
            f"{t['buiten_meetpunten']} buiten de meetpuntenscope, {t['leeg']} leeg) -> {uit}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
