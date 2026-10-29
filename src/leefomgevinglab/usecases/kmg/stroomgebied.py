"""Welke waterlichamen horen bij het stroomgebied — uit de bron, niet uit een cirkel.

Dit lab zocht vergunningen binnen **50 km** van het meetpunt. Dat is een cirkel, en een
stroomgebied is geen cirkel: hij pakt benedenstroomse lozingen mee die niet kunnen bijdragen, en
laat bovenstroomse liggen die dat wél kunnen — de Maas is van Eijsden tot het Haringvliet ruim
200 kilometer lang.

`KRW-oppervlaktewaterlichamen` uit het Waterkwaliteitsportaal (zie
`scripts/18_fetch_krw_registers.py`) geeft per waterlichaam zijn stroomgebieddistrict. Daarmee
wordt de vraag "ligt dit binnen bereik" een lidmaatschapsvraag in plaats van een afstandsmeting:
**ligt dit waterlichaam in district Maas?** District Maas telt er 163, waarvan 14 van
Rijkswaterstaat.

De ruimtelijke bevraging van de Atlas blijft een cirkel, want die bron kent alleen punten en
stralen. Maar die cirkel is nu alleen nog een grove greep om álles binnen te halen; het
inhoudelijke filter is het district. Dat is het verschil tussen een straal die bepaalt wat
meetelt en een straal die bepaalt wat opgehaald wordt.

**Wat dit niet oplost.** Lidmaatschap van een district zegt niets over richting. Of een
waterlichaam bovenstrooms ligt blijft de vraag van `toerekening.is_bovenstrooms()`, en daarvoor
bestaat geen bron — zie de stroomvolgorde daar.

Ontbreekt het registerbestand, dan valt deze module terug op "niet te bepalen" en nooit op
"hoort erbij": een onbekend district mag geen lozing de toerekening in praten.
"""
import json
from pathlib import Path

PAD = "/mnt/nvme/geluidsmeter/data/external/wkp/krw_waterlichamen.json"
DISTRICT_MAAS = "Maas"


def laad(pad: str | None = None) -> dict:
    """Het waterlichaamregister, of een lege set die zegt waarom zij leeg is."""
    p = Path(pad or PAD)
    if not p.exists():
        return {"beschikbaar": False, "waterlichamen": {}, "per_district": {},
                "reden": f"registerbestand ontbreekt ({p}); draai scripts/18_fetch_krw_registers.py"}
    d = json.loads(p.read_text())
    return {"beschikbaar": True,
            "waterlichamen": d.get("waterlichamen") or {},
            "per_district": d.get("per_district") or {},
            "bron": d.get("bron"), "opgehaald_op": d.get("opgehaald_op"),
            "reden": None}


def district_van(register: dict, code: str | None) -> str | None:
    if not code:
        return None
    return (register.get("waterlichamen") or {}).get(code, {}).get("district")


def in_district(register: dict, code: str | None, district: str = DISTRICT_MAAS) -> bool | None:
    """Ligt dit waterlichaam in dit district?

    Drie uitkomsten, en het derde is het punt: `True`, `False`, of `None` wanneer het niet te
    bepalen valt — geen register, of een code die er niet in staat. `None` is géén `False`:
    de aanroeper moet die twee uit elkaar kunnen houden, want "ligt er niet in" en "we weten het
    niet" leiden tot verschillende teksten op de pagina.
    """
    if not register.get("beschikbaar") or not code:
        return None
    if code not in (register.get("waterlichamen") or {}):
        return None
    return district_van(register, code) == district


def codes_in_district(register: dict, district: str = DISTRICT_MAAS) -> list[str]:
    return list((register.get("per_district") or {}).get(district) or [])


def naam_van(register: dict, code: str | None) -> str | None:
    if not code:
        return None
    return (register.get("waterlichamen") or {}).get(code, {}).get("naam")
