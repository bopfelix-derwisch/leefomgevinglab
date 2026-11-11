"""Drie modellen over hetzelfde onderwerp — en waarom een informatiemodel geen datamodel is.

Voor externe veiligheid liggen er drie modellen naast elkaar die alle drie over dezelfde
werkelijkheid gaan: een bedrijf dat een risicovolle activiteit uitvoert op een plek, onder
toezicht van een bevoegd gezag. Ze zijn geen varianten van elkaar maar **lagen van een andere
soort**, en de verwarring begint zodra je ze als wisselgeld behandelt.

* **CIM-VTH-Flo** (Geonovum, werkversie) is *conceptueel*: begrippen en hun relaties, zonder
  uitspraak over velden, sleutels of opslag. 7 views, ongeveer 34 kern-objecttypen.
* **IMEV 3.0** is *logisch en uitwisselbaar*: een JSON-schema achter een OpenAPI, dat precies
  vastlegt wat er over de koppeling gaat. 168 definities, waarvan 88 objecttypen, 41
  referentietypen en 27 enumeraties.
* **Het GIR 2.0-databasemodel** (ICTU, v3.0 van 25 mei 2023) is *fysiek*: 38 tabellen met
  kolommen, datatypes en foreign keys, en per attribuut een kolom die zegt of het ook echt
  gebouwd is.

**Waarom dit document zo bruikbaar is.** Het GIR-stuk doet precies wat elders ontbreekt: het legt
het informatiemodel naast het datamodel en houdt per entiteit bij wat daarvan gerealiseerd is.
De groene entiteiten in het informatiemodel zijn definitief en zitten in de database; de rest
niet. Een aantal tabellen is wél ontworpen maar nooit gebouwd. Dat is geen slordigheid maar een
eerlijke boekhouding van de afstand tussen model en werkelijkheid — dezelfde gedachte als de
`zekerheid` per veld in het waterdossier, hier toegepast op realisatie in plaats van herkomst.

**De cijfers hier zijn nageteld**, niet overgenomen: de IMEV-tellingen komen uit het schema zelf
(`imev30-schema.yaml`), de eindpunten uit de OpenAPI (`rev-v5-specification.yaml`), en de
GIR-tellingen uit de inhoudsopgave en de entiteitparagrafen van het pdf.
"""

BRONNEN = {
    "cim": {
        "naam": "CIM-VTH-Flo",
        "voluit": "Conceptueel Informatiemodel VTH Fysieke Leefomgeving",
        "houder": "Geonovum", "versie": "werkversie", "licentie": "CC BY 4.0",
        "url": "https://github.com/Geonovum/vth-cim-flo",
    },
    "imev": {
        "naam": "IMEV 3.0",
        "voluit": "Informatiemodel Externe Veiligheid, als JSON-schema achter de REV-API",
        "houder": "Register Externe Veiligheid", "versie": "3.0.1 (API v5)",
        "licentie": "publiek",
        "url": "https://rev-portaal.nl/oas/imev30-schema.yaml",
    },
    "gir": {
        "naam": "GIR 2.0 databasemodel",
        "voluit": "Databasemodel Register, de gezamenlijke inspectieruimte voor Seveso-toezicht",
        "houder": "ICTU", "versie": "3.0, 25 mei 2023", "licentie": "intern document",
        "url": None,
    },
}

# De drie lagen naast elkaar. `soort` is het punt: deze modellen vervangen elkaar niet.
LAGEN = [
    {"id": "cim", "soort": "conceptueel",
     "legt_vast": "welke begrippen er zijn en hoe zij zich tot elkaar verhouden",
     "zegt_niets_over": "velden, datatypes, sleutels, opslag",
     "omvang": "7 views, ~34 kern-objecttypen",
     "vorm": "UML-achtige objecttypen met definities",
     "toetsbaar": "nee — je kunt er geen bericht tegen valideren",
     "kleur": "kan"},
    {"id": "imev", "soort": "logisch / uitwisseling",
     "legt_vast": "wat er precies over de koppeling gaat, met types en verplichtingen",
     "zegt_niets_over": "hoe een register het intern opslaat",
     "omvang": "168 definities: 88 objecttypen, 41 referentietypen, 27 enumeraties",
     "vorm": "JSON-schema achter een OpenAPI",
     "toetsbaar": "ja — een bericht valideert of het valideert niet",
     "kleur": "gebeurt"},
    {"id": "gir", "soort": "fysiek",
     "legt_vast": "kolommen, datatypes, foreign keys, locking, historie",
     "zegt_niets_over": "de betekenis van een begrip buiten deze database",
     "omvang": "38 tabellen, waarvan ongeveer 10 ontworpen maar nooit gebouwd",
     "vorm": "ER-diagram plus kolomtabellen, per attribuut een kolom 'gerealiseerd'",
     "toetsbaar": "ja, maar alleen binnen dit systeem",
     "kleur": "mag"},
]

# Hetzelfde begrip, drie keer anders gevangen. Dit is de kern van de analyse: geen van de drie
# is fout, en geen van de drie is door een van de andere te vervangen.
VERTALINGEN = [
    {"begrip": "Wie voert de activiteit uit?",
     "cim": "BETROKKENE in een rol; een organisatie met een wettelijke VTH-taak is "
            "VTH-INSTANTIE",
     "imev": "drie losse velden: naamExploitant, kvkNummerExploitant, "
             "vestigingsnummerExploitant — geen eigen objecttype",
     "gir": "reg_exploitant als eigen tabel, met een FK naar reg_rechtspersoon en naar "
            "reg_mba; een MBA heeft precies één exploitant",
     "les": "Het CIM maakt er een rol van, IMEV drie attributen, GIR een koppeltabel. Alle "
            "drie juist binnen hun soort — en wie ze gelijkstelt, verliest de rol of de sleutel."},
    {"begrip": "Wat mag dit bedrijf?",
     "cim": "TOESTEMMING is een kern-objecttype van de Activiteit-view, naast ALGEMEEN "
            "VERBINDEND VOORSCHRIFT en SPECIFIEK VOORSCHRIFT",
     "imev": "komt niet voor; het REV registreert risico's, geen vergunningen",
     "gir": "uitdrukkelijk buiten scope gelaten — de Omgevingsvergunning-entiteit is "
            "vervangen door een directe relatie Vergunninghouder → MBA",
     "les": "Het begrip dat het hele VTH-stelsel draagt, zit in geen van de twee werkende "
            "systemen. GIR zegt er zelf bij waarom: de omgevingsvergunning is zelf nog in "
            "ontwikkeling."},
    {"begrip": "Wie is hier bevoegd gezag?",
     "cim": "VTH-INSTANTIE, een objecttype met een relatie naar de activiteit",
     "imev": "bevoegdGezag als veld op het object",
     "gir": "géén foreign key maar een GEO-query: valt de locatie binnen het werkgebied van "
            "de organisatie, dan is dat het bevoegd gezag",
     "les": "In GIR bestaat deze relatie niet als gegeven. Zij wordt bij elke bevraging "
            "opnieuw uitgerekend, is niet op historie te bevragen, en verschuift zodra iemand "
            "een werkgebiedgeometrie aanpast."},
    {"begrip": "Welke eigenschappen heeft de activiteit?",
     "cim": "attributen van het objecttype, conceptueel benoemd",
     "imev": "88 objecttypen met echte velden en 27 enumeraties; een CASnummer is een eigen "
             "type",
     "gir": "een generieke sleutel-waardetabel: mba_type → attribuut_definitie → "
            "attribuut_waarde, waarbij elke waarde een varchar is en het type ernaast staat "
            "als enum (Tekst, Datum, Getal, Booleans, Lijst)",
     "les": "Hier lopen de twee uitersten uiteen. IMEV kiest specifiek: niets past wat er niet "
            "in staat, en alles is af te dwingen. GIR kiest generiek: alles past, en niets is "
            "af te dwingen — het datamodel kent de betekenis van zijn eigen inhoud niet."},
    {"begrip": "Op welke wet berust dit?",
     "cim": "ALGEMEEN VERBINDEND VOORSCHRIFT als objecttype",
     "imev": "BKLActiviteit als type, met verwijzing naar de activiteit uit het Bkl",
     "gir": "wettelijke grondslag als Juriconnect-URI in een varchar, plus een reg_wet-tabel "
            "met BWB-nummer — die laatste is nooit gebouwd",
     "les": "Juriconnect is een resolvbare identificatie voor wetgeving. Dat is precies het "
            "soort sleutel dat het waterdossier bij vergunningvoorschriften mist, en hier "
            "staat hij gewoon in het model."},
]

# Wat de analyse oplevert. Elke bevinding wijst naar het document of de bron waar zij op berust.
BEVINDINGEN = [
    {"kop": "Een informatiemodel is niet te vervangen door een datamodel, en andersom ook niet",
     "wat": "De drie modellen staan niet op een schaal van abstract naar concreet waarop je "
            "een punt kunt kiezen. Zij beantwoorden verschillende vragen: wat betekent het, "
            "wat gaat er over de lijn, en hoe staat het op schijf. Een project dat er één "
            "kiest, verliest de vragen van de andere twee.",
     "bron": "de drie bronnen naast elkaar"},
    {"kop": "GIR houdt de afstand tussen model en werkelijkheid bij — per attribuut",
     "wat": "Het document heeft een kolom 'gerealiseerd' naast elk attribuut, en benoemt tien "
            "tabellen die wel ontworpen zijn maar nooit gebouwd: historie, besluit, wet, taak, "
            "domino-relatie, arboactiviteit, contactpersoon, SBI-activiteit. Dat is een "
            "eerlijke boekhouding, en zeldzaam.",
     "bron": "GIR 2.0 databasemodel, §1.2 en de entiteitparagrafen"},
    {"kop": "Het REV ontsluit twee objecttypen, niet 88",
     "wat": "De API v5 heeft precies twee resources: LocatieEVActiviteiten en "
            "GebouwenOfLocaties. Alle 88 objecttypen uit het schema zitten daaronder als "
            "oneOf-varianten. Dat is een bewuste en nette keuze, maar wie het schema leest als "
            "een inhoudsopgave van de API, zoekt zich suf.",
     "bron": "rev-v5-specification.yaml, 20 paden over 2 resourcefamilies"},
    {"kop": "De sleutels die het waterdossier mist, staan hier gewoon in het model",
     "wat": "IMEV kent kvkNummerExploitant, vestigingsnummerExploitant, idPandBAG, "
            "idNummeraanduidingBAG en CASnummer als eigen type. Precies de vier identificaties "
            "waar het waterdossier op vastliep. Het probleem is dus niet dat Nederland ze niet "
            "kan modelleren; het wordt per domein opnieuw besloten.",
     "bron": "imev30-schema.yaml, LocatieActiviteit (25 properties)"},
    {"kop": "Een relatie in het model kan in de database een query zijn",
     "wat": "'Heeft als bevoegd gezag' is in GIR geen opgeslagen verband maar een ruimtelijke "
            "vraag. Dat is efficiënt en het is verdedigbaar, maar het betekent dat het "
            "antwoord van gisteren niet reproduceerbaar is. Een conceptueel model ziet dat "
            "verschil niet; een datamodel maakt het.",
     "bron": "GIR 2.0, §4.19.1 'heeft als bevoegd gezag'"},
    {"kop": "Alle drie leunen op andere standaarden, en geen van drieën op elkaar",
     "wat": "GIR erft van RGBZ en ImZTC (zaakgericht werken) plus Juriconnect en BWB voor "
            "wetgeving. IMEV erft van BAG, het handelsregister en NEN3610. CIM-VTH-Flo probeert "
            "er een laag overheen te leggen. In geen van de drie documenten wordt naar de "
            "andere twee verwezen.",
     "bron": "GIR §4.37/§4.38, IMEV-schema, CIM-VTH-Flo"},
]

# Wat dit lab zelf kan nakijken, en wat uit de documenten komt. Zonder dat onderscheid leest een
# analyse als één geheel terwijl de helft niet te verifiëren is.
HERKOMST = {
    "live": ["de REV-OpenAPI en het IMEV-schema, rechtstreeks van rev-portaal.nl opgehaald "
             "en hier geteld",
             "de REV-WFS, waarop /wfs-kwaliteit al een scan draait tegen IMEV 3.0.2"],
    "document": ["het GIR 2.0 databasemodel — een intern ICTU-document, niet publiek te "
                 "bevragen; alle GIR-cijfers komen uit het pdf",
                 "CIM-VTH-Flo, een werkversie waarvan de views en objecttypen in /vth staan"],
}


def telling() -> dict:
    return {"lagen": len(LAGEN), "vertalingen": len(VERTALINGEN),
            "bevindingen": len(BEVINDINGEN),
            "imev_definities": 168, "imev_objecttypen": 88,
            "imev_referentietypen": 41, "imev_enumeraties": 27,
            "rev_resources": 2, "rev_paden": 20,
            "gir_tabellen": 38, "gir_niet_gebouwd": 10,
            "cim_views": 7}


def analyse() -> dict:
    return {"bronnen": BRONNEN, "lagen": LAGEN, "vertalingen": VERTALINGEN,
            "bevindingen": BEVINDINGEN, "herkomst": HERKOMST, "telling": telling()}
