"""Het studiegebied: drie locaties aan de IJssel, en het waterlichaam dat ze delen.

De locaties liggen in drie gemeenten en twee provincies. Daarmee verschillen de regels per
locatie, terwijl de gebruiksruimte een eigenschap is van het wáter — en dus gedeeld. Dat
contrast is de kern van deze case.

Alle getallen zijn illustratief gekozen om de rekensom te laten werken. Ze zijn NIET de
wettelijke normen of gemeten achtergrondwaarden; het mechanisme is echt, de cijfers niet.
"""

LOCATIES = {
    "brummen": {"id": "brummen", "naam": "IJsseloever bij Brummen", "rd": (210500.0, 458500.0),
                "gemeente": "Brummen", "provincie": "Gelderland", "waterlichaam": "IJssel"},
    "deventer": {"id": "deventer", "naam": "IJsseldijk Deventer", "rd": (206800.0, 474000.0),
                 "gemeente": "Deventer", "provincie": "Overijssel", "waterlichaam": "IJssel"},
    "doesburg": {"id": "doesburg", "naam": "Havengebied Doesburg", "rd": (206000.0, 447500.0),
                 "gemeente": "Doesburg", "provincie": "Gelderland", "waterlichaam": "IJssel"},
}

SECONDEN_PER_JAAR = 31_536_000

WATERLICHAAM = {
    "naam": "IJssel", "owl_id": "NL93_IJSSEL", "stroomgebiedsdistrict": "NLRN",
    "beheer": "rijkswater — minister van IenW, uitgevoerd door Rijkswaterstaat",
    "debiet_m3_s": 300.0,
    "parameters": [
        {"naam": "stikstof totaal", "norm_mg_l": 2.2, "achtergrond_mg_l": 2.16, "zzs": False,
         "toelichting": "Nutriënt; de IJssel zit al vlak tegen de norm aan. Krappe marge, dus hier "
                        "gaat het volume van een lozing wél meetellen."},
        {"naam": "zink", "norm_mg_l": 0.0078, "achtergrond_mg_l": 0.0071, "zzs": False,
         "toelichting": "Metaal; krappe marge, grotendeels diffuus van herkomst."},
        {"naam": "AOX", "norm_mg_l": 0.05, "achtergrond_mg_l": 0.021, "zzs": False,
         "toelichting": "Somparameter organische halogenen; hier nog ruimte."},
        {"naam": "PFOA", "norm_mg_l": 0.0000048, "achtergrond_mg_l": 0.0000061, "zzs": True,
         "toelichting": "Zeer zorgwekkende stof. De achtergrond ligt bóven de norm — er is geen "
                        "ruimte, en er geldt een minimalisatieplicht."},
    ],
}

# Het register dat niet bestaat: bestaande lozingsvergunningen op ditzelfde waterlichaam.
# Verzonnen bedrijven; concentraties in mg/l op het lozingspunt.
REGISTER = [
    {"naam": "Papierfabriek Gelre B.V.", "plaats": "Zutphen", "kenmerk": "RWS-2019-LOZ-0042",
     "debiet_m3_per_uur": 350,
     "concentraties": {"stikstof totaal": 3.1, "zink": 0.009, "AOX": 0.11, "PFOA": 0.00002}},
    {"naam": "Zuivelcoöperatie IJsselvallei", "plaats": "Deventer", "kenmerk": "RWS-2021-LOZ-0117",
     "debiet_m3_per_uur": 180,
     "concentraties": {"stikstof totaal": 6.4, "zink": 0.004, "AOX": 0.02, "PFOA": 0.0}},
    {"naam": "RWZI Deventer — effluent", "plaats": "Deventer", "kenmerk": "RWS-2017-LOZ-0008",
     "debiet_m3_per_uur": 2100,
     "concentraties": {"stikstof totaal": 7.8, "zink": 0.012, "AOX": 0.03, "PFOA": 0.000031}},
    {"naam": "Metaalwarenfabriek Doesburg", "plaats": "Doesburg", "kenmerk": "RWS-2022-LOZ-0203",
     "debiet_m3_per_uur": 95,
     "concentraties": {"stikstof totaal": 1.2, "zink": 0.21, "AOX": 0.04, "PFOA": 0.0}},
    {"naam": "Koelwater energiecentrale Harculo", "plaats": "Zwolle", "kenmerk": "RWS-2015-LOZ-0001",
     "debiet_m3_per_uur": 4500,
     "concentraties": {"stikstof totaal": 0.3, "zink": 0.001, "AOX": 0.0, "PFOA": 0.0}},
]


def vracht_kg_jaar(debiet_m3_per_uur: float, concentratie_mg_l: float) -> float:
    """mg/l × m³/uur → kg/jaar. 1 mg/l op 1 m³ is 1 gram."""
    return debiet_m3_per_uur * 24 * 365 * concentratie_mg_l / 1000.0


def parameter(naam: str) -> dict:
    return next(p for p in WATERLICHAAM["parameters"] if p["naam"] == naam)
