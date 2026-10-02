"""De KRW-doelen per waterlichaam lezen en een gemeten waarde ertegen plaatsen.

Dit is de laag die van "wat gebeurt er" naar "wat kan hier nog" gaat. Drie dingen maken dat
subtieler dan het klinkt, en alle drie zijn uit de bron zelf vastgesteld, niet aangenomen.

**De grondslag moet kloppen.** De klassengrenzen gelden voor het **zomergemiddelde** (april tot en
met september), niet voor een jaargemiddelde of -mediaan. Dat staat niet in het doelenbestand maar
is afgeleid uit `KRW-toetsresultaten` van dezelfde download: alle 6620 `Ntot`-toetsingen daarin
gebruiken bewerkingsmethode `Zomergemiddelde`, in mg/l, met zes waarden per punt. `scripts/13`
berekent dat zomergemiddelde; `toets()` weigert te oordelen zodra die waarde ontbreekt. Een mediaan
tegen deze grenzen leggen is toetsen tegen de verkeerde grootheid.

**Niet elke stof heeft hier een doel.** Het doelenbestand bevat twaalf kwaliteitselementen en geen
enkele chemische stof — geen zink, geen PFOA. Dat is de systematiek: chemische normen zijn landelijk
en staan in het Bkl (bijlage III prioritaire stoffen, IIIa Nederlandse specifieke verontreinigende
stoffen). Voor die stoffen geeft deze module uitdrukkelijk *geen* oordeel, met de reden erbij.

**Het element verschilt per watertype.** De Maas-waterlichamen van type R7/R8 hebben `Ntot`, maar
Haringvliet-west (O2b) heeft `Nanorg`. `_ELEMENT_KANDIDATEN` probeert ze in volgorde; er wordt niets
vertaald of gelijkgesteld.
"""
import json
from pathlib import Path

# Welke KRW-kwaliteitselementen bij een stof uit onze meetset horen, in volgorde van voorkeur.
# Een stof die hier niet staat heeft geen doel per waterlichaam — zie de modulebeschrijving.
_ELEMENT_KANDIDATEN = {
    "Ntot": ("Ntot", "Nanorg"),
    "Ptot": ("Ptot",),
}

# Waarom een stof geen doel per waterlichaam heeft. Expliciet, want "geen doel" en "doel niet
# gevonden" moeten voor een lezer niet hetzelfde zijn.
_GEEN_DOEL = {
    "Zn": ("de norm voor zink staat niet in de KRW-doelen per waterlichaam maar landelijk in het "
           "Bkl (bijlage IIIa, Nederlandse specifieke verontreinigende stoffen). Hij geldt voor de "
           "**opgeloste** fractie en wordt gecorrigeerd voor biobeschikbaarheid, dus hij verschilt "
           "per waterlichaam — in de KRW-toetsresultaten van 2025 loopt hij voor de Bergsche Maas "
           "van 7,80 tot 18,4 µg/l. Dit lab heeft die normen niet geladen."),
    "PFOA": ("voor PFOA is in deze KRW-download geen norm per waterlichaam en ook geen "
             "toetsresultaat aangetroffen. De normstelling voor PFAS is landelijk en in beweging; "
             "dit lab heeft er geen geladen."),
}


def laad(pad: str) -> dict:
    """De verdichte KRW-doelen lezen. Zacht falen: de pagina moet door kunnen zonder doelen.

    Dezelfde keuze als bij `metingen.laad()`, en om dezelfde reden: het ontbreken van een norm is
    een toestand die deze pagina moet kunnen tonen, geen reden om om te vallen.
    """
    p = Path(pad)
    if not p.exists():
        return {"beschikbaar": False,
                "reden": f"geen KRW-doelen gevonden op {pad}; haal ze op met "
                         f"scripts/15_fetch_krw_doelen.py",
                "waterlichamen": {}}
    try:
        d = json.loads(p.read_text(encoding="utf-8"))
    except (ValueError, OSError) as exc:
        return {"beschikbaar": False,
                "reden": f"het doelenbestand is onleesbaar ({type(exc).__name__})",
                "waterlichamen": {}}
    return {**d, "beschikbaar": True}


def _klasse_van(waarde: float, klassen: list[dict]) -> str | None:
    """In welke klasse een waarde valt, volgens de grenzen zoals de bron ze geeft."""
    for k in klassen:
        onder, boven = k.get("onder"), k.get("boven")
        if onder is not None:
            if k.get("onder_symbool") == ">" and not waarde > onder:
                continue
            if k.get("onder_symbool") == ">=" and not waarde >= onder:
                continue
        if boven is not None:
            if k.get("boven_symbool") == "<" and not waarde < boven:
                continue
            if k.get("boven_symbool") == "<=" and not waarde <= boven:
                continue
        return k.get("klasse")
    return None


def toets(doelenset: dict, waterlichaam: str | None, stof: dict) -> dict:
    """Een gemeten stof tegen het doel van haar waterlichaam.

    Levert altijd een woordenboek met `beschikbaar`; is dat onwaar, dan staat in `reden` waarom er
    geen oordeel is. Er wordt nooit teruggevallen op een andere grondslag of een andere norm: liever
    geen oordeel dan een oordeel tegen de verkeerde meetlat.
    """
    code = (stof or {}).get("code")
    if code in _GEEN_DOEL:
        return {"beschikbaar": False, "reden": _GEEN_DOEL[code], "soort": "geen doel per waterlichaam"}
    if not doelenset.get("beschikbaar"):
        return {"beschikbaar": False, "soort": "niet geladen",
                "reden": doelenset.get("reden") or "de KRW-doelen zijn niet geladen"}
    wl = (doelenset.get("waterlichamen") or {}).get(waterlichaam or "")
    if not wl:
        return {"beschikbaar": False, "soort": "waterlichaam onbekend",
                "reden": f"geen KRW-doelen gevonden voor waterlichaam {waterlichaam or '?'}"}

    beschikbaar_els = wl.get("doelen") or {}
    doel = next((beschikbaar_els[e] for e in _ELEMENT_KANDIDATEN.get(code, ())
                 if e in beschikbaar_els), None)
    if doel is None:
        return {"beschikbaar": False, "soort": "geen doel per waterlichaam",
                "reden": f"voor {stof.get('naam') or code} staat geen doel bij dit waterlichaam"}

    waarde = stof.get("zomergemiddelde")
    if waarde is None:
        return {"beschikbaar": False, "soort": "grondslag ontbreekt",
                "reden": (f"het doel geldt voor het {doel.get('grondslag') or 'zomergemiddelde'}, "
                          f"en dat is voor deze stof niet te berekenen uit de meetset")}

    goed_tot = doel.get("goed_tot")
    return {
        "beschikbaar": True,
        "element": doel.get("code"), "element_naam": doel.get("naam"),
        "eenheid": doel.get("eenheid"), "grondslag": doel.get("grondslag"),
        "goed_tot": goed_tot,
        "getoetste_waarde": waarde,
        "n": stof.get("n_zomer"),
        "klasse": _klasse_van(waarde, doel.get("klassen") or []),
        # Positief: er is nog ruimte tot de bovengrens van 'goed'. Negatief: de waarde zit daar al
        # boven, en dan is 'wat kan hier nog' niet een hoeveelheid maar een tekort.
        "ruimte": (round(goed_tot - waarde, 6) if goed_tot is not None else None),
        "klassen": doel.get("klassen") or [],
        "bron": doelenset.get("bron") or {},
        "opgehaald_op": doelenset.get("opgehaald_op"),
    }
