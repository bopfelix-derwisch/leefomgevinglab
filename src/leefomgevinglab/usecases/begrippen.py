"""De begrippen die dit lab gebruikt, opgezocht in de Stelselcatalogus Omgevingswet.

Bij het bouwen van de twee doelbeelden en de twee gebruiksruimte-cases zijn op verschillende
plekken termen als losse string in de code gezet: 'bal.seveso-inrichting', 'lozingsactiviteit',
'zeer kwetsbaar gebouw'. Ze stonden nergens gedefinieerd en verwezen nergens naar.

Die termen bestaan wél, met definitie en juridische vindplaats, in de Stelselcatalogus. Deze
module houdt bij welke termen het lab gebruikt, waar, en waarom ze ertoe doen — en lost ze live
op tegen de catalogus. Wat niet gevonden wordt, is óók een uitkomst.
"""
from concurrent.futures import ThreadPoolExecutor

from leefomgevinglab.connectors.base import ConnectorError


def _t(id, term, zoekterm, gebruikt_in, waarom, hardgecodeerd_als=None):
    return {"id": id, "term": term, "zoekterm": zoekterm, "gebruikt_in": gebruikt_in,
            "waarom": waarom, "hardgecodeerd_als": hardgecodeerd_als}


TERMEN = [
    _t("seveso", "Seveso-inrichting", "Seveso-inrichting", ["/dvth", "/evruimte"],
       "De hele Seveso-keten hangt aan dit begrip, maar het stond als verzonnen identificatie in "
       "de code. De catalogus verwijst naar bijlage I bij het Besluit activiteiten leefomgeving.",
       hardgecodeerd_als="bal.seveso-inrichting"),
    _t("mba", "Milieubelastende activiteit", "milieubelastende activiteit", ["/dvth", "/balo"],
       "Het activiteittype waaronder de Seveso-inrichting valt; bepaalt wie bevoegd gezag is."),
    _t("lozingsactiviteit", "Lozingsactiviteit", "lozingsactiviteit", ["/lozing", "/gebruiksruimte"],
       "Het onderscheid tussen lozen op een oppervlaktewaterlichaam en op een zuiveringtechnisch "
       "werk bepaalt of de waterbeheerder of de gemeente beslist — precies de knip uit /lozing.",
       hardgecodeerd_als="bal.lozingsactiviteit-oppervlaktewater"),
    _t("zeer_kwetsbaar", "Zeer kwetsbaar gebouw", "zeer kwetsbaar gebouw", ["/evruimte"],
       "Op /evruimte leiden we dit zelf af uit het BAG-gebruiksdoel. De catalogus heeft de "
       "juridische definitie, en het verschil daartussen is geen detail — zie de kloof hieronder.",
       hardgecodeerd_als="gebruiksdoel bevat onderwijs-, gezondheidszorg- of celfunctie"),
    _t("kwetsbaar", "Kwetsbaar gebouw", "kwetsbaar gebouw", ["/evruimte"],
       "Zelfde verhaal een klasse lager: onze afleiding uit woon-, logies- en winkelfunctie "
       "tegenover de definitie uit het Besluit kwaliteit leefomgeving.",
       hardgecodeerd_als="gebruiksdoel bevat woon-, logies-, bijeenkomst-, winkel- of sportfunctie"),
    _t("aandachtsgebied", "Aandachtsgebied externe veiligheid", "aandachtsgebied",
       ["/dvth", "/evruimte", "/vth-bronnen"],
       "De contouren op de kaart. In de catalogus staan ze als gebiedsaanwijzingtype, met een "
       "eigen conceptschema aan de standaarden-kant."),
    _t("oppervlaktewaterlichaam", "Oppervlaktewaterlichaam", "oppervlaktewaterlichaam",
       ["/lozing", "/gebruiksruimte"],
       "Het ontvangende water. Het CIM-VTH-Flo heeft er geen objecttype voor — daar belandt het "
       "in ANDER GEO-OBJECT — terwijl de catalogus het wél kent."),
    _t("bevoegd_gezag", "Bevoegd gezag", "bevoegd gezag", ["/lozing", "/gebruiksruimte", "/balo"],
       "Wie beslist. In de lozingsketen leiden we dit live af uit de bronnen; de catalogus geeft "
       "de definitie waartegen dat moet kloppen."),
    _t("zzs", "Zeer zorgwekkende stof", "zeer zorgwekkende stof", ["/lozing", "/gebruiksruimte"],
       "Draagt de minimalisatieplicht die in de gebruiksruimte-case de doorslag geeft."),
    _t("omgevingsvergunning", "Omgevingsvergunning", "omgevingsvergunning",
       ["/dvth", "/lozing", "/balo"],
       "Het besluit dat in beide doelbeelden de spil is, en dat in het doelbeeld zijn eigen "
       "gegevens zou moeten dragen."),
]

# De kern van deze integratie: onze eigen afleiding is niet de juridische definitie.
KLOOF = {
    "begrip": "Zeer kwetsbaar gebouw",
    "onze_afleiding": "Verblijfsobject waarvan het BAG-gebruiksdoel een onderwijs-, "
                      "gezondheidszorg- of celfunctie bevat.",
    "juridisch": "Gebouw als bedoeld in bijlage VI, onder E, bij het Besluit kwaliteit "
                 "leefomgeving.",
    "waarom_het_uitmaakt":
        "Het Bkl kijkt naar de functie én naar de aanwezigheid van verminderd zelfredzame "
        "personen. Een schoolgebouw dat leegstaat of een kantoor met een kinderdagverblijf erin "
        "vallen in de BAG anders uit dan in het Bkl. Onze telling op /evruimte is dus een signaal "
        "om naar te kijken, geen toets — en dat verschil overbruggen is precies het werk dat een "
        "uitvoerder nu handmatig doet.",
    "waar": "/evruimte",
}


def los_op(connector, alleen: list | None = None, werkers: int = 6) -> dict:
    """Zoek elke labterm op in de catalogus. Valt de bron weg, dan blijft de lijst staan.

    De zoekopdrachten zijn onafhankelijk; sequentieel kostte dat ruim dertien seconden.
    """
    termen = [t for t in TERMEN if not alleen or t["id"] in alleen]

    def _zoek(t):
        try:
            return t, connector.zoek(t["zoekterm"]), None
        except (ConnectorError, OSError) as exc:
            return t, [], type(exc).__name__

    with ThreadPoolExecutor(max_workers=min(werkers, max(1, len(termen)))) as pool:
        resultaten = list(pool.map(_zoek, termen))

    uit, fout = [], next((f for _, _, f in resultaten if f), None)
    for t, treffers, _ in resultaten:
        uit.append({**t, "treffers": treffers, "gevonden": bool(treffers),
                    "aantal_treffers": len(treffers)})
    status = "onbereikbaar" if fout else "ok"

    gevonden = sum(1 for b in uit if b["gevonden"])
    return {
        "status": status, "fout": fout, "begrippen": uit,
        "telling": {"totaal": len(uit), "gevonden": gevonden,
                    "niet_gevonden": len(uit) - gevonden},
        "kloof": KLOOF,
        "bron": "Stelselcatalogus Omgevingswet — Catalogus Opvragen API v3",
        "toelichting": "Een federatieve SKOS-begrippengraaf: begrippenkaders van onder meer IMEV, "
                       "de regelgeving en de Omgevingswet-standaarden publiceren erin. De API "
                       "levert geen RDF, en de relaties tussen begrippen zijn dun gevuld — aan de "
                       "juridische kant ontbreken ze zelfs helemaal.",
    }
