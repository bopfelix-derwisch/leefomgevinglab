"""Atlas-voorschriften omzetten naar registerposten met een vracht in kg/jaar.

De rekensom in `ruimte.py` wil per vergunning weten hoeveel kilo per jaar er van een stof in
het water gaat. De Atlas geeft `Waarde` + `Eenheid` in 21 verschillende eenheden. Drie lagen,
in volgorde:

  1. de eenheid is al een vracht (kg/jaar, ton/jaar, kg/dag, kg/week) — direct omrekenen;
  2. de eenheid is een concentratie (mg/l, µg/l) — vracht = concentratie × debiet, mits bij
     hetzelfde kenmerk een Debiet-voorschrift staat. Dat is zo bij 29 van de 72 vestigingen;
  3. anders — de vergunning wordt wél getoond, maar zonder vracht en mét een reden.

Die derde categorie is geen tekortkoming om weg te poetsen. Van een vergunning waarin alleen
een concentratie-eis staat en geen debiet, valt de vracht niet te bepalen — en dus valt hij
ook niet op te tellen. Precies het soort bevinding dat /wfs-kwaliteit voor het REV doet.
"""
from .gebied import vracht_kg_jaar

# De labparameters waar de rekensom mee werkt; alles daarbuiten telt niet mee in de som.
CROSSWALK = {
    "stikstof totaal": "stikstof totaal",
    "zink": "zink",
    "aox": "AOX",
    "som extraheerbare organische halogeenverbindingen": "AOX",
    "extraheerbaar organisch chloor": "AOX",
}

CROSSWALK_BEVINDING = (
    "PFOA komt in de Atlas niet voor als vergunde parameter. De opgenomen vergunningen dateren "
    "deels van vóór de aandacht voor deze stofgroep — kenmerken als DLB2006/8811 en "
    "DLB2007/10829 — terwijl PFOA juist de stof is waar de norm al overschreden wordt. "
    "Een register dat de ZZS niet kent, kan er ook niet op sturen."
)

# Eenheid → factor naar kilogram per jaar.
_VRACHT = {
    "kilogram per jaar": 1.0,
    "ton per jaar": 1000.0,
    "kilogram per dag": 365.0,
    "kilogram per week": 52.0,
}

# Eenheid → factor naar milligram per liter.
_CONCENTRATIE = {
    "milligram per liter": 1.0,
    "microgram per liter": 0.001,
}

# Eenheid → factor naar kubieke meter per uur. "kubieke met per etmaal" is een tikfout in de
# bron; hij staat er echt zo in, dus hij wordt hier ook zo herkend.
_DEBIET = {
    "kubieke meter per uur": 1.0,
    "kubieke meter per dag": 1 / 24,
    "kubieke met per etmaal": 1 / 24,
    "kubieke meter per etmaal": 1 / 24,
    "kubieke meter per week": 1 / 168,
    "kubieke meter per jaar": 1 / 8760,
    "kubieke meter per seconde": 3600.0,
}


def _norm(s) -> str:
    return (s or "").strip().lower()


def _debiet_m3_per_uur(voorschriften: list[dict]) -> float | None:
    for v in voorschriften:
        if _norm(v.get("parameter")) == "debiet" and v.get("waarde") is not None:
            factor = _DEBIET.get(_norm(v.get("eenheid")))
            if factor:
                return float(v["waarde"]) * factor
    return None


def _post(post: dict, telling: dict) -> dict:
    voors = post.get("voorschriften") or []
    debiet = _debiet_m3_per_uur(voors)
    vrachten, onbepaald = {}, []

    for v in voors:
        parameter, waarde, eenheid = v.get("parameter"), v.get("waarde"), _norm(v.get("eenheid"))
        if _norm(parameter) == "debiet":
            continue

        # Een onherkende eenheid is een datakwaliteitsbevinding op zichzelf — die geldt ook
        # voor een parameter die niet in de crosswalk staat, dus dit gaat vóór die toets.
        if eenheid not in _VRACHT and eenheid not in _CONCENTRATIE:
            lab = CROSSWALK.get(_norm(parameter), parameter)
            onbepaald.append({"parameter": lab, "eenheid": v.get("eenheid"),
                              "reden": f"eenheid '{v.get('eenheid')}' is geen vracht en geen "
                                       "concentratie"})
            telling["onbepaald"] += 1
            continue

        lab = CROSSWALK.get(_norm(parameter))
        if lab is None:
            telling["buiten_crosswalk"] += 1
            continue
        if waarde is None:
            onbepaald.append({"parameter": lab, "eenheid": v.get("eenheid"),
                              "reden": "geen waarde in de vergunning"})
            telling["onbepaald"] += 1
            continue

        if eenheid in _VRACHT:
            vrachten[lab] = vrachten.get(lab, 0.0) + float(waarde) * _VRACHT[eenheid]
            telling["vracht_direct"] += 1
        else:
            if debiet is None:
                onbepaald.append({"parameter": lab, "eenheid": v.get("eenheid"),
                                  "reden": "concentratie-eis zonder debiet-voorschrift; zonder "
                                           "debiet is de vracht niet te bepalen"})
                telling["onbepaald"] += 1
                continue
            mg_l = float(waarde) * _CONCENTRATIE[eenheid]
            vrachten[lab] = vrachten.get(lab, 0.0) + vracht_kg_jaar(debiet, mg_l)
            telling["vracht_uit_concentratie"] += 1

    return {"naam": post.get("naam"), "plaats": post.get("plaats"),
            "kenmerk": post.get("kenmerk"), "locatiecode": post.get("locatiecode"),
            "besluitdatum": post.get("besluitdatum"),
            "locatie": post.get("locatie"), "url": post.get("url"),
            "debiet_m3_per_uur": debiet, "vrachten": vrachten, "onbepaald": onbepaald}


def naar_register(posten: list[dict]) -> dict:
    """De Atlas-posten als register, in het formaat dat `ruimte.bereken()` verwacht."""
    telling = {"vestigingen": len(posten), "vracht_direct": 0, "vracht_uit_concentratie": 0,
               "onbepaald": 0, "buiten_crosswalk": 0}
    register = [_post(p, telling) for p in posten]
    return {"register": register, "telling": telling, "echt": True,
            "bevinding": CROSSWALK_BEVINDING,
            "bron": {"naam": "Atlas voor een Schone Maas",
                     "url": "https://atlas-smwk.hub.arcgis.com/",
                     "houder": "Schone Maaswaterketen",
                     "licentie": "publiek toegankelijk, geen expliciete licentie; live bevraagd "
                                 "met bronvermelding"}}
