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
    try:
        d = json.loads(p.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError) as exc:
        # Een half geschreven of anderszins onleesbaar bestand is voor een bezoeker niet te
        # onderscheiden van een ontbrekend bestand, maar de reden wél — dat scheelt tussen
        # "download ontbreekt" en "download overdoen".
        return {"beschikbaar": False, "punten": [], "meetjaar": None, "bron": None,
                "opgehaald_op": None, "telling": {},
                "reden": f"meetset op {pad} is onleesbaar ({exc}); haal hem opnieuw op met "
                         "scripts/13_fetch_wkp_metingen.py"}
    # beschikbaar/reden zijn namen die metingen.py zelf bezet; het verdichtingsscript levert ze
    # vandaag niet, maar mag ze in een latere versie niet stilzwijgend gaan overschrijven.
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


def laad_codes(pad: str) -> dict:
    """De verzameling Aquo-codes die ergens op de bekende meetpunten voorkomt (`scripts/
    21_fetch_wkp_gemeten_codes.py`) — voor `toezicht.signalen.regel_geen_onafhankelijke_meting`
    (`context["gemeten_codes"]`). Dit is iets anders dan `laad()` hierboven: dat bestand draagt
    de **waarden** van drie stoffen (Ntot/Zn/PFOA); dit bestand draagt alleen *welke* codes
    ergens voorkomen, over het hele meetnet dat dit lab kent. Zacht falen, net als `laad()`."""
    p = Path(pad)
    if not p.exists():
        return {"beschikbaar": False, "codes": [],
                "reden": f"geen gemeten-codes gevonden op {pad}; haal ze op met "
                         "scripts/21_fetch_wkp_gemeten_codes.py"}
    try:
        d = json.loads(p.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError) as exc:
        return {"beschikbaar": False, "codes": [],
                "reden": f"de gemeten-codes op {pad} zijn onleesbaar ({exc})"}
    d["beschikbaar"] = True
    d.setdefault("codes", [])
    return d


def codes_set(d: dict) -> set[str]:
    """`laad_codes()`'s uitkomst als platte set, voor `context["gemeten_codes"]`."""
    return set(d.get("codes") or [])
