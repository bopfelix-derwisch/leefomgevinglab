"""De KRW-doelen per waterlichaam lezen en een gemeten waarde ertegen plaatsen.

Dit is de laag die van "wat gebeurt er" naar "wat kan hier nog" gaat. Drie dingen maken dat
subtieler dan het klinkt, en alle drie zijn uit de bron zelf vastgesteld, niet aangenomen.

**De grondslag moet kloppen.** De klassengrenzen gelden voor het **zomergemiddelde** (april tot en
met september), niet voor een jaargemiddelde of -mediaan. Dat staat niet in het doelenbestand maar
is afgeleid uit `KRW-toetsresultaten` van dezelfde download: alle 6620 `Ntot`-toetsingen daarin
gebruiken bewerkingsmethode `Zomergemiddelde`, in mg/l, met zes waarden per punt. `scripts/13`
berekent dat zomergemiddelde; `toets()` weigert te oordelen zodra die waarde ontbreekt. Een mediaan
tegen deze grenzen leggen is toetsen tegen de verkeerde grootheid.

**Twee soorten norm, uit twee bestanden.** Het doelenbestand bevat twaalf kwaliteitselementen en
geen enkele chemische stof. Dat is de systematiek: de ecologische en fysisch-chemische doelen worden
per waterlichaam vastgesteld, de chemische normen zijn landelijk (Bkl bijlage III en IIIa). Die
tweede soort staat wél in `KRW-toetsresultaten`, per meetpunt, en wordt door `scripts/17` ontsloten.
`chemisch()` kijkt daar eerst, want zo'n norm hangt aan het punt en is specifieker dan een doel per
waterlichaam — voor zink is hij bovendien gecorrigeerd voor biobeschikbaarheid en verschilt hij
daardoor per plek: 7,80 µg/l op de Maas tegen 3,99 bij de Haringvlietsluis.

Blijft een stof over waarvoor in geen van beide iets staat, dan geeft deze module uitdrukkelijk
*geen* oordeel, met de reden erbij. Dat geldt vandaag voor PFOA.

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

# Waarom een stof geen doel heeft. Expliciet, want "geen norm vastgesteld" en "wij hebben hem niet
# gevonden" moeten voor een lezer niet hetzelfde zijn.
_GEEN_DOEL = {
    "PFOA": ("voor PFOA is in deze KRW-download geen norm per waterlichaam en geen toetsresultaat "
             "aangetroffen — niet in de doelen en niet in de toetsresultaten over 2021-2024. De "
             "normstelling voor PFAS is landelijk en in beweging; dit lab heeft er geen geladen."),
}


def laad_normen(pad: str) -> dict:
    """De chemische normen per meetpunt lezen (`scripts/17`). Zacht falen, als de rest."""
    p = Path(pad)
    if not p.exists():
        return {"beschikbaar": False, "normen": {},
                "reden": f"geen KRW-normen gevonden op {pad}; haal ze op met scripts/17"}
    try:
        d = json.loads(p.read_text(encoding="utf-8"))
    except (ValueError, OSError) as exc:
        return {"beschikbaar": False, "normen": {},
                "reden": f"het normenbestand is onleesbaar ({type(exc).__name__})"}
    return {**d, "beschikbaar": True}


def chemisch(normenset: dict, meetpunt: str | None, stof: dict) -> dict | None:
    """De chemische norm voor deze stof op dit meetpunt, of None als die er niet is.

    Een stof kan twee normen hebben die bij verschillende grootheden horen: een jaargemiddelde
    (JG-MKN) en een maximum (MAC-MKN). Beide worden teruggegeven; het jaargemiddelde is leidend,
    want dat is de norm waar de toestandsbeoordeling op draait. De koppeling gaat op parametercode
    én hoedanigheid: de zinknorm geldt voor de opgeloste fractie en mag niet tegen de totaalreeks
    worden gelegd.
    """
    if not normenset.get("beschikbaar") or not meetpunt:
        return None
    code, hoed = (stof or {}).get("code"), ((stof or {}).get("hoedanigheid") or "").strip()
    kandidaten = [n for n in (normenset.get("normen") or {}).get(meetpunt, [])
                  if n.get("parameter") == code and (n.get("hoedanigheid") or "").strip() == hoed]
    if not kandidaten:
        return None
    leidend = next((n for n in kandidaten if n["grondslag"] == "jaargemiddelde"), kandidaten[0])
    waarde = stof.get(leidend["grondslag"])
    if waarde is None:
        return None
    return {
        "beschikbaar": True, "soort": "chemische norm",
        "element": leidend["parameter"], "element_naam": stof.get("naam"),
        "eenheid": leidend["eenheid"], "grondslag": leidend["grondslag"],
        "goed_tot": leidend["norm"], "getoetste_waarde": waarde,
        "n": stof.get("n"), "klasse": "voldoet" if waarde <= leidend["norm"] else "voldoet niet",
        "ruimte": round(leidend["norm"] - waarde, 6),
        "normgroep": leidend.get("normgroep"),
        "normjaar": leidend.get("meetjaar"),
        "hoedanigheid": hoed,
        # De tweede grondslag erbij, zodat de pagina kan laten zien dat er twee grenzen zijn.
        "nevengrenzen": [{"grondslag": n["grondslag"], "norm": n["norm"],
                          "waarde": stof.get(n["grondslag"])}
                         for n in kandidaten if n is not leidend],
        "klassen": [], "bron": normenset.get("bron") or {},
        "opgehaald_op": normenset.get("opgehaald_op"),
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


def toets(doelenset: dict, waterlichaam: str | None, stof: dict,
          normenset: dict | None = None, meetpunt: str | None = None) -> dict:
    """Een gemeten stof tegen het doel van haar waterlichaam.

    Levert altijd een woordenboek met `beschikbaar`; is dat onwaar, dan staat in `reden` waarom er
    geen oordeel is. Er wordt nooit teruggevallen op een andere grondslag of een andere norm: liever
    geen oordeel dan een oordeel tegen de verkeerde meetlat.
    """
    # Eerst de chemische norm: die hangt aan het meetpunt en is specifieker dan een doel per
    # waterlichaam. Voor zink is hij bovendien per punt gecorrigeerd voor biobeschikbaarheid.
    chem = chemisch(normenset or {}, meetpunt, stof)
    if chem is not None:
        return chem

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
        return {"beschikbaar": False, "soort": "geen norm gevonden",
                "reden": (f"voor {stof.get('naam') or code} staat geen doel bij dit waterlichaam, "
                          f"en op dit meetpunt is er ook geen KRW-toets voor deze stof")}

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
