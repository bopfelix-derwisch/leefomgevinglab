"""Drie modellen over hetzelfde onderwerp — en waarom een informatiemodel geen datamodel is.

Voor externe veiligheid liggen er drie modellen naast elkaar die alle drie over dezelfde
werkelijkheid gaan: een bedrijf dat een risicovolle activiteit uitvoert op een plek, onder
toezicht van een bevoegd gezag. Ze zijn geen varianten van elkaar maar **lagen van een andere
soort**, en de verwarring begint zodra je ze als wisselgeld behandelt.

* **CIM-VTH-Flo** (Geonovum, werkversie) is *conceptueel*: begrippen en hun relaties, zonder
  uitspraak over velden, sleutels of opslag. 7 views, ongeveer 34 kern-objecttypen.
* **IMEV** is het *informatiemodel* externe veiligheid: objecttypen, attributen en definities,
  gepubliceerd als begrippenkader op `definities.geostandaarden.nl/imev/`. Normatief, maar niet
  iets waar een bericht tegen valideert.
* **`imev30-schema.yaml`** is de *technische uitwerking* daarvan: dat model als JSON-schema.
  168 definities, ingedeeld volgens de regel hieronder. Hier valideert een bericht wél tegen.
* **`rev-v5-specification.yaml`** is de *API-specificatie* van het REV: 20 paden over twee
  resourcefamilies plus een conformiteitstoets. Zegt niets over betekenis, alleen over hoe je
  erbij komt.
* **Het GIR 2.0-databasemodel** (ICTU, v3.0 van 25 mei 2023) is *fysiek*: 38 tabellen met
  kolommen, datatypes en foreign keys, en per attribuut een kolom die zegt of het ook echt
  gebouwd is.

**Waarom dit document zo bruikbaar is.** Het GIR-stuk doet precies wat elders ontbreekt: het legt
het informatiemodel naast het datamodel en houdt per entiteit bij wat daarvan gerealiseerd is.
De groene entiteiten in het informatiemodel zijn definitief en zitten in de database; de rest
niet. Een aantal tabellen is wél ontworpen maar nooit gebouwd. Dat is geen slordigheid maar een
eerlijke boekhouding van de afstand tussen model en werkelijkheid — dezelfde gedachte als de
`zekerheid` per veld in het waterdossier, hier toegepast op realisatie in plaats van herkomst.

**Die drie zijn niet uitwisselbaar, en de taal op deze pagina houdt ze apart.** Dat klinkt als
muggenziften tot je ziet wat het kost: "IMEV ontsluit twee objecttypen" is onwaar en
"`rev-v5-specification.yaml` ontsluit twee resourcefamilies" is waar. De eerste formulering legt
een keuze van de API-ontwerper bij het informatiemodel. Hetzelfde geldt de andere kant op:
`Voidable` en de reguliere expressie op een CAS-nummer zijn *schema*-constructies — manieren om
iets uit het model afdwingbaar te maken — en niet zelf modelinhoud. `ARTEFACTEN` houdt die
scheiding vast, en de tests bewaken dat zij niet in de tekst terugglijdt.

**Het verschil is in de bron zelf te zien.** Het veld `info.version` van de API-specificatie is
letterlijk `IMEV 3.0.1`, terwijl de titel `REV API - v5` is: de API leent het versienummer van
het informatiemodel dat zij vervoert. Dat is precies de verwarring, vastgelegd in het bestand.

**De cijfers hier zijn nageteld**, niet overgenomen: de tellingen per bestand komen uit de
bestanden zelf, en de GIR-tellingen uit de inhoudsopgave en de entiteitparagrafen van het pdf.

**De indeling van de 168 definities is een regel, geen lijstje** (`INDELING`, en `indeling()`
past haar toe). Een definitie met `enum` is een enumeratie, met `oneOf` een keuzetype, met
`type: array` een verzameling; een objectvorm die een van de basisvelden `identificatie`,
`bronhouder`, `beginGeldigheid` of `bronobjectID` draagt is een objecttype, en een objectvorm
zonder die velden een structureel hulptype. Dat geeft 79 + 12 + 43 + 27 + 4 + 3 = 168, en
`tests/test_modellen_live.py` rekent het tegen het echte bestand na.

**Deze pagina noemde eerder 88 objecttypen en 41 referentietypen.** Die twee getallen zijn niet
te reproduceren: geen regel die op dit bestand toepasbaar is levert ze op, en samen dekken ze de
168 niet. Ze zijn vervangen door de indeling hierboven — zichtbaar in de tekst, waar "44 van de
88" nu "44 van de 79" is.

**De overlapvraag staat apart** (`OVERLAP`). Het REV en het GIR gaan over dezelfde
Seveso-bedrijven, dus de praktische vraag is niet of de modellen op elkaar lijken maar waarop je
ze kunt joinen. Dat antwoord is schraal: van twaalf gedeelde begrippen zijn er drie op een
sleutel te koppelen, en alle drie komen uit een basisregistratie buiten beide registers.

**Eén eerdere bewering op deze pagina was fout** en is hier gecorrigeerd. Er stond dat de
vergunning in IMEV niet voorkomt omdat het REV risico's registreert. Natellen in het schema wees
uit dat 44 van de 79 objecttypen `basisVergunningNummer`, `datumVergunningOfMelding` én
`vergunningsPlicht` dragen. IMEV maakt er geen entiteit van, maar bewaart de identificatie wel —
precies het tegendeel van wat hier eerst stond.
"""

BRONNEN = {
    "cim": {
        "naam": "CIM-VTH-Flo",
        "voluit": "Conceptueel Informatiemodel VTH Fysieke Leefomgeving",
        "houder": "Geonovum", "versie": "werkversie", "licentie": "CC BY 4.0",
        "url": "https://github.com/Geonovum/vth-cim-flo",
    },
    "imev": {
        "naam": "IMEV",
        "voluit": "Informatiemodel Externe Veiligheid — het model zelf, als begrippenkader",
        "houder": "Geonovum / Geostandaarden", "versie": "3.0",
        "licentie": "publiek",
        "url": "https://definities.geostandaarden.nl/imev/",
    },
    "schema": {
        "naam": "imev30-schema.yaml",
        "voluit": "IMEV als JSON-schema: de technische uitwerking waar een bericht tegen "
                  "valideert",
        "houder": "Register Externe Veiligheid (RWS)", "versie": "3.0",
        "licentie": "publiek",
        "url": "https://rev-portaal.nl/oas/imev30-schema.yaml",
    },
    "api": {
        "naam": "rev-v5-specification.yaml",
        "voluit": "OpenAPI-specificatie van de REV-API v5 — hoe je bij de gegevens komt",
        "houder": "Rijkswaterstaat", "versie": "v5 (info.version: IMEV 3.0.1)",
        "licentie": "publiek",
        "url": "https://rev-portaal.nl/oas/rev-v5-specification.yaml",
    },
    "gir": {
        "naam": "GIR 2.0 databasemodel",
        "voluit": "Databasemodel Register, de gezamenlijke inspectieruimte voor Seveso-toezicht",
        "houder": "ICTU", "versie": "3.0, 25 mei 2023", "licentie": "intern document",
        "url": None,
    },
}

# Wat het REV publiceert, bestand voor bestand. Dit staat apart omdat "IMEV" in de praktijk
# voor alle vier wordt gebruikt, en elk van de vier iets anders is. `verwijzingen` is het aantal
# $ref's uit de API-specificatie naar dat bestand -- geteld, niet geschat.
ARTEFACTEN = [
    {"bestand": "IMEV (het informatiemodel)",
     "soort": "model",
     "wat": "objecttypen, attributen en definities van de externe-veiligheidswerkelijkheid, "
            "gepubliceerd als begrippenkader met eigen namespace",
     "niet": "geen bestand dat je kunt valideren of aanroepen",
     "houder": "Geonovum / Geostandaarden",
     "vindplaats": "definities.geostandaarden.nl/imev/",
     "omvang": "begrippen met definitie, ook te vinden via de Stelselcatalogus Omgevingswet",
     "verwijzingen": None},
    {"bestand": "imev30-schema.yaml",
     "soort": "berichtschema",
     "wat": "datzelfde model als JSON-schema: types, verplichte velden, enumeraties, patronen",
     "niet": "zegt niets over paden, methoden of autorisatie",
     "houder": "Register Externe Veiligheid (RWS)",
     "vindplaats": "rev-portaal.nl/oas/imev30-schema.yaml",
     "omvang": "168 definities: 79 objecttypen, 43 keuzetypen, 27 enumeraties, 12 hulptypen, "
               "4 eenvoudige typen, 3 verzamelingen",
     "verwijzingen": 8},
    {"bestand": "rev-v5-specification.yaml",
     "soort": "API-specificatie",
     "wat": "20 paden over twee resourcefamilies plus een conformiteitstoets, met oauth2 en "
            "paginering",
     "niet": "bevat zélf geen enkel inhoudelijk schema — components draagt alleen "
             "securitySchemes",
     "houder": "Rijkswaterstaat",
     "vindplaats": "rev-portaal.nl/oas/rev-v5-specification.yaml",
     "omvang": "20 paden, 2 resourcefamilies, 0 eigen schemas",
     "verwijzingen": None},
    {"bestand": "imev30-oas-schema.yaml",
     "soort": "envelop",
     "wat": "de verpakking van de API: LinksContainer, Link, Page, ValidationReport, "
            "OverdrachtResponse, FeatureTypes",
     "niet": "niets over externe veiligheid; dit is HAL, paginering en foutmelding",
     "houder": "Register Externe Veiligheid (RWS)",
     "vindplaats": "rev-portaal.nl/oas/imev30-oas-schema.yaml",
     "omvang": "25 schemas, geen ervan inhoudelijk",
     "verwijzingen": 43},
    {"bestand": "common-schema.yaml",
     "soort": "gedeelde types",
     "wat": "NEN3610ID en de GeoJSON-geometrieën: Point, Polygon, MultiPolygon en de rest",
     "niet": "domeinonafhankelijk; hier zit geen enkel begrip van externe veiligheid in",
     "houder": "Register Externe Veiligheid (RWS)",
     "vindplaats": "rev-portaal.nl/oas/common-schema.yaml",
     "omvang": "11 schemas",
     "verwijzingen": 7},
]

# Hoe de 168 definities van het berichtschema zijn ingedeeld. Dit staat hier als regel en niet
# als uitkomst, zodat de getallen op de pagina na te rekenen zijn tegen het bestand zelf -- en
# zodat een volgende schemaversie de tellingen meeneemt in plaats van ze stil te laten verouderen.
BASISVELDEN = ("identificatie", "bronhouder", "beginGeldigheid", "bronobjectID")

INDELING = [
    ("enumeraties", "heeft een enum: een gesloten lijst toegestane waarden", 27),
    ("keuzetypen", "heeft een oneOf: dit of dat, bijvoorbeeld een afstand of een geometrie", 43),
    ("verzamelingen", "is een array: de omhullende van een lijst resultaten", 3),
    ("objecttypen", "is een object dat een van de basisvelden draagt — dit zijn de echte "
                    "objecttypen van het model", 79),
    ("hulptypen", "is een object zonder basisveld: structureel, geen objecttype van het "
                  "model (Voidable, IdentificatieSchema, Stof)", 12),
    ("eenvoudige_typen", "is een string met een patroon, zoals CASNummer", 4),
]


def indeling(schemas: dict | None = None) -> dict:
    """Pas de indelingsregel toe. Zonder argument de vastgelegde uitkomst.

    Met een argument -- de `components.schemas` van een echt schemabestand -- wordt zij
    opnieuw uitgerekend. Zo kan een live test de getallen op de pagina natellen in plaats van
    ze te geloven. De som moet het totaal aantal definities zijn; een definitie die in geen
    bak valt, zou een stil gat in de telling zijn.
    """
    if schemas is None:
        return {naam: aantal for naam, _, aantal in INDELING}
    uit = {naam: 0 for naam, _, _ in INDELING}
    for v in schemas.values():
        if not isinstance(v, dict):
            continue
        if "enum" in v:
            uit["enumeraties"] += 1
        elif "oneOf" in v:
            uit["keuzetypen"] += 1
        elif v.get("type") == "array":
            uit["verzamelingen"] += 1
        elif "properties" in v or v.get("type") == "object":
            velden = set(v.get("properties") or {})
            sleutel = ("objecttypen" if any(b in velden for b in BASISVELDEN)
                       else "hulptypen")
            uit[sleutel] += 1
        else:
            uit["eenvoudige_typen"] += 1
    return uit


# De lagen naast elkaar. `soort` is het punt: deze modellen vervangen elkaar niet.
LAGEN = [
    {"id": "cim", "soort": "conceptueel",
     "legt_vast": "welke begrippen er zijn en hoe zij zich tot elkaar verhouden",
     "zegt_niets_over": "velden, datatypes, sleutels, opslag",
     "omvang": "7 views, ~34 kern-objecttypen",
     "vorm": "UML-achtige objecttypen met definities",
     "toetsbaar": "nee — je kunt er geen bericht tegen valideren",
     "kleur": "kan"},
    {"id": "imev", "soort": "informatiemodel",
     "legt_vast": "welke objecttypen en attributen de externe-veiligheidswerkelijkheid heeft, "
                  "met een definitie per begrip",
     "zegt_niets_over": "hoe dat in een bericht of een database terechtkomt",
     "omvang": "begrippenkader met eigen namespace op definities.geostandaarden.nl",
     "vorm": "objecttypen met definities, ook als SKOS-begrippen in de Stelselcatalogus",
     "toetsbaar": "nee — normatief, maar je valideert er geen bericht tegen",
     "kleur": "gebeurt"},
    {"id": "schema", "soort": "technische uitwerking",
     "legt_vast": "wat er precies over de koppeling gaat, met types, verplichtingen en "
                  "patronen",
     "zegt_niets_over": "waarom een veld bestaat, en hoe een register het intern opslaat",
     "omvang": "168 definities: 79 objecttypen, 43 keuzetypen, 27 enumeraties, 12 hulptypen, "
               "4 eenvoudige typen, 3 verzamelingen",
     "vorm": "JSON-schema in een losse components-bundel",
     "toetsbaar": "ja — een bericht valideert of het valideert niet",
     "kleur": "paars"},
    {"id": "api", "soort": "interface",
     "legt_vast": "welke paden er zijn, welke methoden, welke autorisatie, hoe paginering werkt",
     "zegt_niets_over": "de betekenis of de structuur van wat erover gaat — dat staat in de "
                        "schemabestanden waarnaar zij verwijst",
     "omvang": "20 paden, 2 resourcefamilies, 0 eigen schemas",
     "vorm": "OpenAPI 3.0.1 die naar drie externe schemabestanden verwijst",
     "toetsbaar": "ja, maar alleen op de vorm van het verzoek",
     "kleur": "teal"},
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
#
# De `imev`-kolom gaat over het REV-stelsel als geheel en benoemt zelf of een uitspraak over het
# **informatiemodel** of over het **berichtschema** gaat. Dat onderscheid wegpoetsen zou dezelfde
# fout zijn als die deze pagina aanwijst, één niveau lager.
VERTALINGEN = [
    {"begrip": "Wie voert de activiteit uit?",
     "cim": "BETROKKENE in een rol; een organisatie met een wettelijke VTH-taak is "
            "VTH-INSTANTIE",
     "imev": "het informatiemodel kent geen rol en geen eigen objecttype voor de exploitant; "
             "het berichtschema draagt drie losse velden op de activiteit: naamExploitant, "
             "kvkNummerExploitant, vestigingsnummerExploitant",
     "gir": "reg_exploitant als eigen tabel, met een FK naar reg_rechtspersoon en naar "
            "reg_mba; een MBA heeft precies één exploitant",
     "les": "Het CIM maakt er een rol van, IMEV drie attributen, GIR een koppeltabel. Alle "
            "drie juist binnen hun soort — en wie ze gelijkstelt, verliest de rol of de sleutel."},
    {"begrip": "Wat mag dit bedrijf?",
     "cim": "TOESTEMMING is een kern-objecttype van de Activiteit-view, naast ALGEMEEN "
            "VERBINDEND VOORSCHRIFT en SPECIFIEK VOORSCHRIFT",
     "imev": "geen eigen objecttype, maar in het berichtschema wél drie velden op 44 van de "
             "79 objecttypen: basisVergunningNummer, datumVergunningOfMelding en "
             "vergunningsPlicht",
     "gir": "uitdrukkelijk buiten scope gelaten — de Omgevingsvergunning-entiteit is "
            "vervangen door een directe relatie Vergunninghouder → MBA, en een "
            "vergunningnummer komt nergens in het datamodel voor",
     "les": "Geen van beide maakt er een entiteit van, maar daar houdt de gelijkenis op. IMEV "
            "bewaart de identificatie van de vergunning; GIR laat hem vallen. Wie de twee "
            "registers op vergunning wil koppelen, kan dat aan één kant wel en aan de andere "
            "niet."},
    {"begrip": "Wie is hier bevoegd gezag?",
     "cim": "VTH-INSTANTIE, een objecttype met een relatie naar de activiteit",
     "imev": "bevoegdGezag als veld op het object, in het schema een enumeratie van vier "
             "waarden — dus een bestuurslaag, geen organisatie",
     "gir": "géén foreign key maar een GEO-query: valt de locatie binnen het werkgebied van "
            "de organisatie, dan is dat het bevoegd gezag",
     "les": "In GIR bestaat deze relatie niet als gegeven. Zij wordt bij elke bevraging "
            "opnieuw uitgerekend, is niet op historie te bevragen, en verschuift zodra iemand "
            "een werkgebiedgeometrie aanpast."},
    {"begrip": "Welke eigenschappen heeft de activiteit?",
     "cim": "attributen van het objecttype, conceptueel benoemd",
     "imev": "het informatiemodel benoemt de eigenschappen per objecttype; het berichtschema "
             "maakt ze afdwingbaar — 79 objecttypen met echte velden, 27 enumeraties, en een "
             "CASNummer met een reguliere expressie erop",
     "gir": "een generieke sleutel-waardetabel: mba_type → attribuut_definitie → "
            "attribuut_waarde, waarbij elke waarde een varchar is en het type ernaast staat "
            "als enum (Tekst, Datum, Getal, Booleans, Lijst)",
     "les": "Hier lopen de twee uitersten uiteen. IMEV kiest specifiek: niets past wat er niet "
            "in staat, en alles is af te dwingen. GIR kiest generiek: alles past, en niets is "
            "af te dwingen — het datamodel kent de betekenis van zijn eigen inhoud niet."},
    {"begrip": "Op welke wet berust dit?",
     "cim": "ALGEMEEN VERBINDEND VOORSCHRIFT als objecttype",
     "imev": "BKLActiviteit als type in het schema, met verwijzing naar de activiteit uit het "
             "Bkl; daarnaast idActiviteitTR met een IMOW-identificatie uit het DSO",
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
    {"kop": "\"IMEV\" is vier bestanden en drie soorten ding",
     "wat": "Het informatiemodel staat bij Geonovum op definities.geostandaarden.nl. Het "
            "berichtschema (imev30-schema.yaml), de API-specificatie "
            "(rev-v5-specification.yaml), de envelop (imev30-oas-schema.yaml) en de gedeelde "
            "geotypes (common-schema.yaml) staan bij RWS op rev-portaal.nl. Vier bestanden, "
            "twee houders, en in het dagelijks gesprek heten ze alle vier IMEV. Daarmee "
            "verschuiven uitspraken ongemerkt van het model naar de interface en terug.",
     "bron": "de vier bestanden en hun vindplaatsen, elk apart opgehaald"},
    {"kop": "De API-specificatie ontsluit twee resourcefamilies — en dat is geen uitspraak over IMEV",
     "wat": "rev-v5-specification.yaml heeft 20 paden over LocatieEVActiviteiten en "
            "GebouwenOfLocaties, plus een conformiteitstoets. De 79 objecttypen hangen "
            "daaronder via twee ingangen: de spec verwijst precies acht keer naar het "
            "berichtschema, voor GebouwOfLocatie en LocatieEVActiviteit. Dat is een keuze van "
            "de API-ontwerper, niet een eigenschap van het informatiemodel — en wie het als "
            "'IMEV ontsluit er twee' opschrijft, legt haar bij de verkeerde partij.",
     "bron": "rev-v5-specification.yaml: 20 paden, 8 verwijzingen naar imev30-schema.yaml"},
    {"kop": "Het meeste van de API-specificatie gaat niet over externe veiligheid",
     "wat": "Van de 58 verwijzingen in de spec gaan er 43 naar de envelop "
            "(LinksContainer, Page, ValidationReport, OverdrachtResponse), 7 naar de gedeelde "
            "geotypes en 8 naar het inhoudelijke schema. De spec zelf draagt nul eigen "
            "schemas: haar components-blok bevat alleen securitySchemes. Een OpenAPI is "
            "overwegend verpakking, en dat is precies waarom zij het informatiemodel niet kan "
            "vervangen.",
     "bron": "58 $ref's in rev-v5-specification.yaml, geteld per doelbestand"},
    {"kop": "Een van de vier gepubliceerde bestanden parseert niet",
     "wat": "imev30-oas-schema.yaml bevat op regel 449 een regel met twee tabtekens. YAML "
            "verbiedt tabs voor indentatie, dus PyYAML weigert het hele bestand met "
            "'found character \\t that cannot start any token'. De regel is verder leeg — het is "
            "achtergebleven witruimte, geen inhoudelijke fout — maar het effect is dat een "
            "strikte parser bij de envelop van de REV-API afslaat. Dit lab vond het door het "
            "bestand te willen tellen; wie de spec alleen leest, ziet het niet.",
     "bron": "imev30-oas-schema.yaml regel 449, opgehaald 2026-11-12"},
    {"kop": "De sleutels die het waterdossier mist, staan hier gewoon in het schema",
     "wat": "kvkNummerExploitant, vestigingsnummerExploitant, idPandBAG, "
            "idNummeraanduidingBAG en CASNummer als eigen type. Precies de identificaties "
            "waar het waterdossier op vastliep. Het probleem is dus niet dat Nederland ze niet "
            "kan modelleren; het wordt per domein opnieuw besloten.",
     "bron": "imev30-schema.yaml, LocatieActiviteit (25 properties)"},
    {"kop": "Een relatie in het model kan in de database een query zijn",
     "wat": "'Heeft als bevoegd gezag' is in GIR geen opgeslagen verband maar een ruimtelijke "
            "vraag. Dat is efficiënt en het is verdedigbaar, maar het betekent dat het "
            "antwoord van gisteren niet reproduceerbaar is. Een conceptueel model ziet dat "
            "verschil niet; een datamodel maakt het.",
     "bron": "GIR 2.0, §4.19.1 'heeft als bevoegd gezag'"},
    {"kop": "Twee registers over dezelfde bedrijven, en één harde sleutel",
     "wat": "Van de twaalf begrippen die het REV en het GIR beide vastleggen, zijn er drie op "
            "een gedeelde sleutel te joinen — en alle drie komen van buiten: het KvK-nummer, "
            "het vestigingsnummer en de BAG-identificatie. Het bedrijf zelf, het bevoegd gezag, "
            "de vergunning en de stof hebben in elk register een eigen sleutel of geen. Wat de "
            "twee registers verbindt, is dus niet wat zij samen hebben afgesproken maar wat zij "
            "elk los van de ander uit een basisregistratie overnemen.",
     "bron": "12 begrippen naast elkaar: 3 joinbaar, 2 deels, 7 niet"},
    {"kop": "Het berichtschema dwingt af dat je zegt waarom een gegeven ontbreekt",
     "wat": "Elf velden zijn Voidable: zij mogen leeg zijn, maar dan is een "
            "geenWaardeReden verplicht — gegevenInTransitie, nietVanToepassing of "
            "waardeOnbekend. Het staat op 166 plekken in het schema, en precies op de "
            "identificaties: vergunningnummer, KvK-nummer, BAG-pand. Dat is de zekerheid per "
            "veld uit het waterdossier, maar als standaard in plaats van als labvinding. Aan de "
            "GIR-kant is hetzelfde gegeven simpelweg NULL.",
     "bron": "imev30-schema.yaml, Voidable + VoidReasonValue"},
    {"kop": "Bevoegd gezag is in het ene register een bestuurslaag en in het andere een organisatie",
     "wat": "Het berichtschema heeft bevoegdGezag als enumeratie van vier waarden: rijk, provincie, gemeente, "
            "gegevenInTransitie. GIR heeft reg_org met een OIN van Logius en leidt bevoegdheid af "
            "uit een ruimtelijke vraag op het werkgebied. Uit 'gemeente' volgt niet welke "
            "gemeente, en uit een OIN volgt geen bestuurslaag. Beide zijn juist binnen hun eigen "
            "systeem; samen leveren zij geen antwoord op dezelfde vraag.",
     "bron": "IMEV BevoegdGezag-enum tegenover GIR §4.19.1"},
    {"kop": "Allemaal leunen zij op andere standaarden, en geen van hen op elkaar",
     "wat": "GIR erft van RGBZ en ImZTC (zaakgericht werken) plus Juriconnect en BWB voor "
            "wetgeving. Het REV-stelsel erft van BAG, het handelsregister en NEN3610 — die "
            "laatste staat als NEN3610ID in common-schema.yaml, met zes verwijzingen uit de "
            "API-specificatie. CIM-VTH-Flo probeert er een laag overheen te leggen. In geen "
            "van de documenten wordt naar de andere verwezen.",
     "bron": "GIR §4.37/§4.38, common-schema.yaml, CIM-VTH-Flo"},
]

# De overlap tussen het REV en het GIR-datamodel, begrip voor begrip. Dit is de vraag die ertoe
# doet zodra iemand de twee registers wil koppelen: niet "lijken ze op elkaar" maar "waarop kun
# je joinen". `join` is daarom het belangrijkste veld hier.
#
# De vergelijking is scheef van opzet en dat is geen slordigheid: links staat een *datamodel* en
# rechts een *berichtschema*. Een GIR-kolom en een IMEV-veld zijn niet dezelfde soort ding. De
# `imev`-kant zegt daarom per rij of het gegeven uit het informatiemodel komt of een constructie
# van het schema is -- `Voidable` en de CAS-expressie zijn het laatste.
OVERLAP = [
    {"begrip": "De Seveso-inrichting zelf",
     "gir": "reg_mba met mba_soort = Seveso-inrichting, plus parent_mba_id voor "
            "subactiviteiten (niet geïmplementeerd)",
     "imev": "SevesoInrichting als eigen objecttype in het schema, 19 properties — alle base- "
             "en vergunningvelden, niets Seveso-specifieks",
     "join": "nee", "waarom": "GIR sleutelt op een eigen uuid, IMEV op identificatie plus "
             "bronobjectID. Hetzelfde bedrijf, twee nummers, geen vertaling."},
    {"begrip": "Wie het uitvoert",
     "gir": "reg_exploitant → reg_rechtspersoon, met kvk en rsin uit het handelsregister",
     "imev": "naamExploitant, kvkNummerExploitant en vestigingsnummerExploitant als velden "
             "op de activiteit",
     "join": "ja", "waarom": "Het KvK-nummer staat in beide. Dit is de enige harde join "
             "tussen de twee registers."},
    {"begrip": "De vestiging",
     "gir": "reg_vestiging.vestigingsnummer, zoals door het KvK uitgegeven",
     "imev": "vestigingsnummerExploitant en vestigingsnummerAanvrager",
     "join": "ja", "waarom": "Zelfde bron, zelfde nummer. Let op: GIR waarschuwt dat "
             "hetzelfde vestigingsnummer meermaals in de tabel kan staan, omdat vestigingen "
             "per rechtspersoon worden opgehaald."},
    {"begrip": "De plek",
     "gir": "reg_locatie met reg_adres; de geografische positie komt uit de BAG-adressen",
     "imev": "idNummeraanduidingBAG, idPandBAG en een eigen geometrie",
     "join": "ja", "waarom": "Allebei via de BAG. IMEV draagt daarnaast zelf geometrie, GIR "
             "leidt die af uit het adres."},
    {"begrip": "Het bevoegd gezag",
     "gir": "reg_org met een OIN van Logius; welke organisatie bevoegd is volgt uit een "
            "GEO-query op het werkgebied",
     "imev": "bevoegdGezag als enum met vier waarden — rijk, provincie, gemeente, "
             "gegevenInTransitie — plus bronhoudercode van 3 tot 6 tekens",
     "join": "nee", "waarom": "IMEV noemt de bestuurslaag, GIR de organisatie. Uit 'gemeente' "
             "volgt niet wélke gemeente, en uit een OIN volgt geen bestuurslaag."},
    {"begrip": "De vergunning",
     "gir": "niets — de entiteit is buiten scope gelaten",
     "imev": "basisVergunningNummer (1-50 tekens), datumVergunningOfMelding, vergunningsPlicht",
     "join": "nee", "waarom": "Eenzijdig: IMEV heeft het nummer, GIR heeft het niet. Er valt "
             "niets te koppelen zolang één kant het gegeven niet bewaart."},
    {"begrip": "De wettelijke grondslag",
     "gir": "wettelijke grondslag als Juriconnect-URI in een varchar; reg_wet met BWB-nummer "
            "is ontworpen maar nooit gebouwd",
     "imev": "balActiviteit als lijst, plus idActiviteitTR — een IMOW-identificatie uit het "
             "DSO, bijvoorbeeld nl.imow-mnre1034.activiteit.KoelinstalKooldioKoolwstAmmo",
     "join": "deels", "waarom": "Beide verwijzen naar wetgeving, maar via verschillende "
             "stelsels: Juriconnect wijst naar de tekst, IMOW naar de activiteit in het "
             "omgevingsplan. Die twee zijn te verbinden, maar niet zonder tussentabel."},
    {"begrip": "De stof",
     "gir": "een waarde in de generieke attribuuttabel, opgeslagen als varchar",
     "imev": "CASNummer als eigen type; de reguliere expressie die het formaat afdwingt is een "
             "constructie van het berichtschema, niet van het informatiemodel",
     "join": "nee", "waarom": "IMEV valideert het CAS-nummer, GIR kent het niet als begrip. "
             "Aan de GIR-kant is een stof een vrije tekst in een sleutel-waardetabel."},
    {"begrip": "Geldigheid in de tijd",
     "gir": "datum_ingang en datum_einde, met een losse precision-kolom (1=jaar, 2=jaar en "
            "maand, 3=compleet) voor onvolledige datums uit het handelsregister",
     "imev": "beginGeldigheid en eindGeldigheid op alle 79 objecttypen die een levensloop "
             "hebben",
     "join": "deels", "waarom": "Hetzelfde begrip, andere omgang met onzekerheid. GIR maakt "
             "een onvolledige datum expliciet; IMEV kent die precisie niet."},
    {"begrip": "Een ontbrekende waarde",
     "gir": "NULL",
     "imev": "Voidable in het berichtschema: het veld mag ontbreken, maar dan moet er een "
             "geenWaardeReden bij — gegevenInTransitie, nietVanToepassing of waardeOnbekend",
     "join": "nee", "waarom": "Dit is het scherpste verschil. IMEV dwingt af dat je zégt "
             "waarom iets leeg is; 11 velden mogen zo leeg, op 166 plekken in het schema. Een "
             "NULL in GIR zegt niets."},
    {"begrip": "Historie",
     "gir": "reg_locatie_historie bestaat; reg_mba_historie en "
            "reg_mba_attribuut_waarde_historie zijn ontworpen maar nooit gebouwd",
     "imev": "een /historie-endpoint per resource in de API-specificatie, werkend",
     "join": "nee", "waarom": "IMEV levert de tijdlijn, GIR deels. Een vergelijking over de "
             "tijd is daarmee aan één kant onmogelijk."},
    {"begrip": "Domino-relaties tussen Seveso-bedrijven",
     "gir": "reg_domino_relatie met veroorzaker en blootgestelde; nooit gebouwd, en nu "
            "vervangen door een losse boolean op de MBA",
     "imev": "geen tegenhanger",
     "join": "nee", "waarom": "Een relatie die alleen in GIR bestaat, en daar als vlag in "
             "plaats van als relatie. Welk bedrijf welk ander blootstelt, is in geen van beide "
             "registers te bevragen."},
]

# Wat dit lab zelf kan nakijken, en wat uit de documenten komt. Zonder dat onderscheid leest een
# analyse als één geheel terwijl de helft niet te verifiëren is.
HERKOMST = {
    "live": ["alle vier de schemabestanden van rev-portaal.nl/oas, elk apart opgehaald en "
             "hier geteld — inclusief de tab op regel 449 die er één onparseerbaar maakt",
             "de 58 verwijzingen in de API-specificatie, per doelbestand geteld: 43 envelop, "
             "8 inhoud, 7 geotypes",
             "de velden per objecttype in het berichtschema: welke 44 een vergunningnummer "
             "dragen, welke 11 Voidable zijn, en wat de enumeratie BevoegdGezag bevat",
             "dat IMEV óók als begrippenkader bestaat: /api/begrippen vindt 'kwetsbaar gebouw' "
             "onder conceptschema IMEV op definities.geostandaarden.nl",
             "de REV-WFS, waarop /wfs-kwaliteit al een scan draait tegen IMEV 3.0.2"],
    "document": ["het GIR 2.0 databasemodel — een intern ICTU-document, niet publiek te "
                 "bevragen; alle GIR-cijfers komen uit het pdf",
                 "CIM-VTH-Flo, een werkversie waarvan de views en objecttypen in /vth staan"],
}


def overlap_telling() -> dict:
    """Hoeveel van de twaalf begrippen zijn te joinen, en hoeveel niet."""
    uit = {"ja": 0, "deels": 0, "nee": 0}
    for o in OVERLAP:
        uit[o["join"]] += 1
    return uit


def verwijzingen() -> dict:
    """De $ref's uit de API-specificatie, per doelbestand. Geteld, niet geschat."""
    uit = {a["bestand"]: a["verwijzingen"] for a in ARTEFACTEN if a["verwijzingen"]}
    return {"per_bestand": uit, "totaal": sum(uit.values()),
            "aandeel_envelop": uit["imev30-oas-schema.yaml"] / sum(uit.values())}


def telling() -> dict:
    return {"lagen": len(LAGEN), "vertalingen": len(VERTALINGEN),
            "bevindingen": len(BEVINDINGEN), "overlap": len(OVERLAP),
            "artefacten": len(ARTEFACTEN),
            "refs_totaal": verwijzingen()["totaal"],
            "refs_envelop": verwijzingen()["per_bestand"]["imev30-oas-schema.yaml"],
            "refs_inhoud": verwijzingen()["per_bestand"]["imev30-schema.yaml"],
            "api_eigen_schemas": 0,
            **{f"join_{k}": v for k, v in overlap_telling().items()},
            "schema_voidable_velden": 11, "schema_voidable_plekken": 166,
            "schema_met_vergunningnummer": 44,
            "schema_definities": 168,
            **{f"schema_{k}": v for k, v in indeling().items()},
            "api_resourcefamilies": 2, "api_paden": 20,
            "gir_tabellen": 38, "gir_niet_gebouwd": 10,
            "cim_views": 7}


def analyse() -> dict:
    return {"bronnen": BRONNEN, "artefacten": ARTEFACTEN, "lagen": LAGEN,
            "vertalingen": VERTALINGEN, "overlap": OVERLAP, "bevindingen": BEVINDINGEN,
            "herkomst": HERKOMST, "telling": telling()}
