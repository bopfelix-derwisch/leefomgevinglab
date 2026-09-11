"""De synthetische casus: één directe lozing op de IJssel.

Verzonnen bedrijf, echt RD-punt. Op dat punt geeft de KRW-service van RWS het waterlichaam
IJssel terug en PDOK de gemeente Deventer, zodat de keten het bevoegd gezag en het ontvangende
water live kan bepalen in plaats van ze aan te nemen.
"""
from leefomgevinglab.usecases import lozing

CASUS = {
    "bedrijf": "Overijsselse Papier- en Vezelfabriek B.V.",
    "kvk": "90000117",
    "vestiging": "OPV B.V. — locatie IJsseldijk",
    "adres": "IJsseldijk 3, Deventer",
    "rd": lozing.CASUS["rd"],
    "activiteit": "Lozingsactiviteit op een oppervlaktewaterlichaam",
    "grondslag": "Bal — lozingsactiviteit; waterbeheerder is bevoegd gezag",
    "bevoegd_gezag_lozing": "Minister van IenW, uitgevoerd door Rijkswaterstaat",
    "bevoegd_gezag_mba": "burgemeester en wethouders (uit te lezen uit de bestuurlijke gebieden)",
    "lozing": {
        "soort": "koelwater en gezuiverd proceswater",
        "debiet_m3_per_uur": 420,
        "lozingspunt": "LP-1, uitstroom in de IJssel",
        "continu": True,
    },
    # Indicatieve toetswaarden: illustratief gekozen om de keten te laten rekenen.
    # Dit zijn NIET de wettelijke normen; zie de duiding bij stap 4.
    "parameters": [
        {"naam": "CZV", "vracht_kg_jaar": 138000, "concentratie_mg_l": 37.5,
         "zzs": False, "indicatieve_toetswaarde_mg_l": None},
        {"naam": "stikstof totaal", "vracht_kg_jaar": 9100, "concentratie_mg_l": 2.47,
         "zzs": False, "indicatieve_toetswaarde_mg_l": 2.2},
        {"naam": "zink", "vracht_kg_jaar": 46, "concentratie_mg_l": 0.0125,
         "zzs": False, "indicatieve_toetswaarde_mg_l": 0.0078},
        {"naam": "AOX", "vracht_kg_jaar": 310, "concentratie_mg_l": 0.084,
         "zzs": False, "indicatieve_toetswaarde_mg_l": 0.05},
        {"naam": "PFOA", "vracht_kg_jaar": 0.9, "concentratie_mg_l": 0.00024,
         "zzs": True, "indicatieve_toetswaarde_mg_l": 0.0000048},
    ],
    "aanvraag": {
        "nummer": "OLO-2026-0011882",
        "type": "aanvraag omgevingsvergunning lozingsactiviteit",
        "procedure": "reguliere voorbereidingsprocedure",
        "ingediend": "2026-04-08",
        "bijlagen": ["Lozingsplan", "ABM-toets", "Immissietoets", "ZZS-inventarisatie",
                     "Situatietekening met lozingspunt"],
    },
}

# Indicatief jaargemiddeld debiet per waterlichaam, voor de verdunningsberekening.
# Illustratief; een echte immissietoets rekent met mengzones en maatgevende afvoeren.
DEBIET_M3_S = {"IJssel": 300.0, "_onbekend": 50.0}
