"""LBR — Landelijke Benadering Risicobedrijven: de inspectiemethodiek achter GIR.

Sinds 2022 de manier waarop Seveso-inrichtingen worden geïnspecteerd, langs drie pijlers.
Door bevindingen naar die pijlers te structureren worden ze vergelijkbaar tussen inspecties
en tussen diensten — in plaats van vrije tekst per inspecteur.

De bevindingen hieronder zijn verzonnen, maar elk verwijst naar een voorschrift uit het
besluit van stap 5. Dat is de lus die het doelbeeld wil sluiten: handhaven op wat vergund is.
"""

PIJLERS = ("Systeem", "Techniek", "Cultuur")

# oordeel → hoe zwaar het meeweegt in de LHSO-afweging
OORDELEN = {"voldoet": 0, "aandachtspunt": 1, "tekortkoming": 2, "ernstige tekortkoming": 3}


def bevindingen(casus: dict) -> list:
    """Bevindingen van één inspectie, gestructureerd naar de drie LBR-pijlers."""
    tank = next((i["naam"] for i in casus["installaties"] if "Ammoniakopslag" in i["naam"]),
                "de opslagtank")
    return [
        {"id": "BEV-01", "pijler": "Systeem", "oordeel": "tekortkoming",
         "voorschrift": "V-03",
         "constatering": "Het veiligheidsbeheerssysteem beschrijft de periodieke beoordeling van "
                         "de scenario's, maar de laatste beoordeling dateert van drie jaar terug "
                         "terwijl de installatie sindsdien is gewijzigd.",
         "gedrag": "onverschillig", "gevolgen": "beperkt"},
        {"id": "BEV-02", "pijler": "Techniek", "oordeel": "ernstige tekortkoming",
         "voorschrift": "V-01",
         "constatering": f"De wettelijk voorgeschreven herkeuring van {tank} is elf maanden "
                         "overschreden; de tank is in die periode in bedrijf gebleven.",
         "gedrag": "calculerend", "gevolgen": "aanzienlijk"},
        {"id": "BEV-03", "pijler": "Cultuur", "oordeel": "aandachtspunt",
         "voorschrift": "V-04",
         "constatering": "Operators melden bijna-ongevallen wisselend; in de registratie van het "
                         "afgelopen jaar ontbreken meldingen die in interviews wel worden genoemd.",
         "gedrag": "goedwillend", "gevolgen": "beperkt"},
    ]


def is_overtreding(bevinding: dict) -> bool:
    """Niet elke bevinding is een overtreding — een aandachtspunt is dat niet."""
    return OORDELEN[bevinding["oordeel"]] >= OORDELEN["tekortkoming"]
