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
    d = json.loads(p.read_text(encoding="utf-8"))
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
