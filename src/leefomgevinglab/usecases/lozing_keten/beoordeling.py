"""ABM en immissietoets — sterk vereenvoudigd, maar met de juiste structuur.

De Algemene BeoordelingsMethodiek bepaalt per stof welke saneringsinspanning nodig is; de
immissietoets rekent de restlozing door naar een concentratie in het ontvangende water. Voor
zeer zorgwekkende stoffen geldt bovendien een minimalisatieplicht.

Wat hier gebeurt is een verdunningssom met een vast jaargemiddeld debiet per waterlichaam en
illustratieve toetswaarden. Een echte immissietoets rekent met mengzones, achtergrond-
concentraties, maatgevende afvoeren en stofspecifieke normen. Alles wat hieruit komt is als
indicatief gemarkeerd.
"""
from .casus import DEBIET_M3_S

# saneringsinspanning volgens de ABM-systematiek, vereenvoudigd tot drie klassen
ABM = {
    "Z": "minimalisatie — zeer zorgwekkende stof; vermijden, anders continu verbeteren",
    "B": "verdergaande sanering — beste beschikbare technieken plus aanvullende beperking",
    "A": "sanering conform beste beschikbare technieken",
}


def abm_klasse(parameter: dict) -> str:
    if parameter.get("zzs"):
        return "Z"
    if parameter.get("indicatieve_toetswaarde_mg_l") is not None:
        return "B"
    return "A"


def immissietoets(casus: dict, waterlichaam: str | None) -> dict:
    """Verdun de lozing in het ontvangende water en toets per parameter."""
    debiet_water = DEBIET_M3_S.get(waterlichaam or "", DEBIET_M3_S["_onbekend"])
    debiet_lozing = casus["lozing"]["debiet_m3_per_uur"] / 3600.0
    verdunning = debiet_water / debiet_lozing if debiet_lozing else None

    uit = []
    for p in casus["parameters"]:
        norm = p["indicatieve_toetswaarde_mg_l"]
        immissie = (p["concentratie_mg_l"] / verdunning) if verdunning else None
        if norm is None or immissie is None:
            oordeel, ratio = "geen toetswaarde", None
        else:
            ratio = immissie / norm
            oordeel = ("verwaarloosbaar" if ratio < 0.1
                       else "toelaatbaar" if ratio <= 1.0
                       else "niet toelaatbaar zonder aanvullende maatregelen")
        uit.append({**p, "abm": abm_klasse(p),
                    "immissie_mg_l": round(immissie, 9) if immissie is not None else None,
                    "ratio": round(ratio, 3) if ratio is not None else None,
                    "oordeel": oordeel})

    knelpunten = [p["naam"] for p in uit if p["oordeel"].startswith("niet toelaatbaar")]
    zzs = [p["naam"] for p in uit if p["zzs"]]
    met_ratio = [p for p in uit if p["ratio"] is not None]
    maatgevend = max(met_ratio, key=lambda p: p["ratio"])["naam"] if met_ratio else None
    return {"waterlichaam": waterlichaam, "debiet_waterlichaam_m3_s": debiet_water,
            "debiet_lozing_m3_s": round(debiet_lozing, 4),
            "verdunningsfactor": round(verdunning) if verdunning else None,
            "parameters": uit, "knelpunten": knelpunten, "zzs": zzs, "maatgevend": maatgevend,
            "bindend": "immissie" if knelpunten else "BBT en de ZZS-minimalisatieplicht",
            "indicatief": True}


def voorschriften(toets: dict) -> list:
    """Voorschriften die rechtstreeks uit de toets volgen."""
    v = [
        {"id": "W-01", "tekst": "De lozing voldoet aan de in artikel 2 opgenomen "
                                "emissiegrenswaarden, gemeten op het lozingspunt."},
        {"id": "W-02", "tekst": "De vergunninghouder bemonstert maandelijks en rapporteert "
                                "jaarlijks aan het bevoegd gezag."},
        {"id": "W-03", "tekst": "De zuiveringsvoorziening wordt in goede staat gehouden en "
                                "jaarlijks onderhouden; storingen worden binnen 24 uur gemeld."},
    ]
    if toets["zzs"]:
        v.append({"id": "W-04",
                  "tekst": "Voor " + ", ".join(toets["zzs"]) + " geldt de minimalisatieplicht. De "
                           "vergunninghouder rapporteert vijfjaarlijks over vermijdings- en "
                           "reductiemogelijkheden."})
    if toets["knelpunten"]:
        v.append({"id": "W-05",
                  "tekst": "Voor " + ", ".join(toets["knelpunten"]) + " treft de vergunninghouder "
                           "binnen twee jaar aanvullende maatregelen, zodanig dat de immissie de "
                           "toetswaarde niet langer overschrijdt."})
    return v
