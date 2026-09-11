"""Toezicht op een lozingsactiviteit — drie sporen in plaats van de LBR-pijlers.

Voor Seveso-inrichtingen bestaat de LBR met Systeem, Techniek en Cultuur, vastgelegd in GIR.
Voor een lozing is er geen landelijke methodiek met die status. Wat er wél is, valt uiteen in
drie sporen, en het middelste maakt dit dossier bijzonder: het effect is meetbaar.

Elke bevinding verwijst naar een voorschrift uit het besluit, zodat de lus tussen vergunnen en
handhaven gesloten blijft.
"""

SPOREN = ("Administratief", "Meetgegevens", "Technisch")

OORDELEN = {"voldoet": 0, "aandachtspunt": 1, "tekortkoming": 2, "ernstige tekortkoming": 3}


def bevindingen(casus: dict, toets: dict) -> list:
    zzs = ", ".join(toets["zzs"]) or "de betrokken stoffen"
    knel = toets["knelpunten"][0] if toets["knelpunten"] else (toets.get("maatgevend") or "een genormeerde parameter")
    return [
        {"id": "BEV-W1", "spoor": "Administratief", "oordeel": "aandachtspunt",
         "voorschrift": "W-02",
         "constatering": "De jaarrapportage is drie weken na de termijn ingediend; de maandelijkse "
                         "bemonstering is wel volledig uitgevoerd.",
         "gedrag": "goedwillend", "gevolgen": "vrijwel nihil"},
        {"id": "BEV-W2", "spoor": "Meetgegevens", "oordeel": "ernstige tekortkoming",
         "voorschrift": "W-01",
         "constatering": f"In vier van de twaalf maandmonsters overschrijdt {knel} de vergunde "
                         "emissiegrenswaarde op het lozingspunt. De overschrijdingen vallen samen "
                         "met perioden van lage afvoer, waarin het ontvangende water minder "
                         "verdunning biedt dan waarmee in de vergunning is gerekend.",
         "gedrag": "calculerend", "gevolgen": "van belang"},
        {"id": "BEV-W3", "spoor": "Technisch", "oordeel": "tekortkoming",
         "voorschrift": "W-03",
         "constatering": "Het onderhoud aan de nabezinking is een jaar overgeslagen; bij twee "
                         "storingen is de melding aan het bevoegd gezag achterwege gebleven.",
         "gedrag": "onverschillig", "gevolgen": "beperkt"},
        {"id": "BEV-W4", "spoor": "Administratief", "oordeel": "tekortkoming",
         "voorschrift": "W-04",
         "constatering": f"De vijfjaarlijkse rapportage over vermijdings- en reductiemogelijkheden "
                         f"voor {zzs} ontbreekt; er is geen onderbouwing dat minimalisatie is "
                         "onderzocht.",
         "gedrag": "onverschillig", "gevolgen": "van belang"},
    ]


def is_overtreding(bevinding: dict) -> bool:
    return OORDELEN[bevinding["oordeel"]] >= OORDELEN["tekortkoming"]
