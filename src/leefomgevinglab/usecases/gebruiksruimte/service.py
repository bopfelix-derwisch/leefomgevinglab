"""Het beeld op een locatie: regels, vergunningen en de ruimte die overblijft."""
from leefomgevinglab.usecases.lozing_keten import bronnen as water_bronnen

from . import gebied, regels, ruimte

MAX_DEBIET = 20_000          # m³/uur; begrenst wat de gebruiker kan vragen

# Concentraties van het voornemen (mg/l), gelijk aan de lozingscasus op /lozing.
VOORNEMEN_CONCENTRATIES = {
    "stikstof totaal": 2.47, "zink": 0.0125, "AOX": 0.084, "PFOA": 0.00024,
}

# Welke informatiefuncties deze case aantoont, en waaraan je dat ziet.
INFORMATIEFUNCTIES = [
    {"nr": 5, "naam": "Lokaliseren en ruimtelijk duiden",
     "hoe": "De regels worden op het RD-punt opgehaald en het ontvangende waterlichaam wordt "
            "afgeleid uit de KRW-service — beide live."},
    {"nr": 4, "naam": "Beschikbaar stellen en delen",
     "hoe": "De regelingen komen als API-antwoord uit het DSO in plaats van als pdf."},
    {"nr": 8, "naam": "Kennis ontsluiten en verklaren",
     "hoe": "Per regeling staat er wat hij voor dít voornemen betekent, inclusief de regelingen "
            "die hier wél gelden maar deze lozing niet raken."},
    {"nr": 3, "naam": "Registreren en beheren",
     "hoe": "De bestaande vergunningen komen uit een register dat niet bestaat; hier nagebootst "
            "om te laten zien wat het zou opleveren."},
    {"nr": 6, "naam": "Analyseren en signaleren",
     "hoe": "De cumulatie: de ruimte tot de norm afgezet tegen wat er al vergund is, per parameter."},
]


def voornemen(debiet_m3_per_uur: float) -> dict:
    debiet = max(1.0, min(float(debiet_m3_per_uur), MAX_DEBIET))
    return {"soort": "directe lozing van koel- en gezuiverd proceswater",
            "debiet_m3_per_uur": debiet, "concentraties": dict(VOORNEMEN_CONCENTRATIES)}


def beeld(locatie_id: str, debiet_m3_per_uur: float = 420, live: bool = True,
          _haal_regels=None, _haal_water=None) -> dict:
    """Alles bij elkaar: waar ben ik, wat geldt hier, wat ligt er al, en wat kan er nog?"""
    loc = gebied.LOCATIES[locatie_id]                 # KeyError bij onbekende locatie: luid falen
    x, y = loc["rd"]

    water = water_bronnen.contextset(x, y, straal_m=1000, live=live, haal=_haal_water)
    rijkswater = bool(water.get("rijkswater")) if live else True
    r = regels.regels_op_locatie(x, y, rijkswater=rijkswater, live=live, _haal=_haal_regels)

    v = voornemen(debiet_m3_per_uur)
    u = ruimte.bereken(v, gebied.REGISTER, gebied.WATERLICHAAM)

    return {
        "locatie": {**loc, "rd": list(loc["rd"])},
        "water": {**gebied.WATERLICHAAM, "live": water},
        "rijkswater": rijkswater,
        "bevoegd_gezag": water_bronnen.bevoegd_gezag(water),
        "regels": r,
        "register": gebied.REGISTER,
        "voornemen": v,
        "ruimte": u,
        "informatiefuncties": INFORMATIEFUNCTIES,
        "locaties": list(gebied.LOCATIES.values()),
        "max_debiet": MAX_DEBIET,
        "verantwoording": "Regelingen live uit het DSO. Het register met bestaande vergunningen "
                          "bestaat niet en is synthetisch; normen en achtergrondconcentraties zijn "
                          "illustratief gekozen. Het mechanisme is echt, de cijfers niet.",
    }
