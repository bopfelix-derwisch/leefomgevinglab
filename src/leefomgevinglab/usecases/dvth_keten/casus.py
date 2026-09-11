"""De synthetische casus: één hogedrempel Seveso-inrichting.

Volledig verzonnen bedrijf. Het RD-punt is echt en ligt in een gebied waar de REV-WFS
daadwerkelijk aandachtsgebieden kent, zodat stap 3 iets te vinden heeft — zonder dat we
een bestaand bedrijf beschrijven.
"""
from leefomgevinglab.usecases import dvth

CASUS = {
    "bedrijf": "Zuidhaven Chemie B.V.",
    "kvk": "90000042",                       # verzonnen, buiten het uitgegeven bereik
    "vestiging": "Zuidhaven Chemie B.V. — locatie Havenweg",
    "adres": "Havenweg 14, Zuidhaven",
    "rd": dvth.CASUS["rd"],
    "activiteit": "Exploiteren van een Seveso-inrichting",
    "drempel": "hoog",
    "grondslag": "Bal §3.3.1 — hogedrempelinrichting; één milieubelastende activiteit",
    "bevoegd_gezag": "Gedeputeerde Staten",
    "uitvoering": "Seveso-omgevingsdienst",
    "stoffen": [
        {"naam": "ammoniak", "categorie": "acuut toxisch, categorie 2",
         "hoeveelheid_ton": 180, "drempel_ton": 50, "maatgevend": True},
        {"naam": "propaan", "categorie": "brandbaar gas, categorie 1",
         "hoeveelheid_ton": 45, "drempel_ton": 50, "maatgevend": False},
    ],
    "installaties": [
        {"naam": "Ammoniakopslagtank T-101", "type": "tot vloeistof verdicht gas",
         "inhoud_m3": 300, "opstelling": "bovengronds, ingeterpt"},
        {"naam": "Verlaadstation V-2", "type": "verlading tankauto's", "inhoud_m3": None,
         "opstelling": "overkapping met vloeistofdichte vloer"},
        {"naam": "Propaanopslag P-3", "type": "drukhouder", "inhoud_m3": 90,
         "opstelling": "bovengronds"},
    ],
    "aanvraag": {
        "nummer": "OLO-2026-0004417",
        "type": "aanvraag omgevingsvergunning milieubelastende activiteit",
        "procedure": "uitgebreide voorbereidingsprocedure",
        "ingediend": "2026-03-02",
        "bijlagen": ["Veiligheidsrapport (VR)", "Aanvraagformulier MBA",
                     "QRA-rapportage", "Situatietekening"],
    },
}

# Indicatieve afstanden voor de aandachtsgebieden. Géén QRA — een QRA rekent met
# scenario's, weerklassen en faalfrequenties. Deze tabel is bedoeld om de keten te laten
# lopen, en is als indicatief gemarkeerd waar hij in de uitvoer terechtkomt.
AFSTANDEN_M = {
    "gifwolkaandachtsgebied": 1500,
    "brandaandachtsgebied": 90,
    "explosieaandachtsgebied": 60,
}
