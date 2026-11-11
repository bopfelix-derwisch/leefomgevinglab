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

**De overlapvraag staat apart** (`OVERLAP`). Het REV en het GIR gaan over dezelfde
Seveso-bedrijven, dus de praktische vraag is niet of de modellen op elkaar lijken maar waarop je
ze kunt joinen. Dat antwoord is schraal: van twaalf gedeelde begrippen zijn er drie op een
sleutel te koppelen, en alle drie komen uit een basisregistratie buiten beide registers.

**Eén eerdere bewering op deze pagina was fout** en is hier gecorrigeerd. Er stond dat de
vergunning in IMEV niet voorkomt omdat het REV risico's registreert. Natellen in het schema wees
uit dat 44 van de 88 objecttypen `basisVergunningNummer`, `datumVergunningOfMelding` én
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
     "imev": "geen eigen objecttype, maar wél drie velden op 44 van de 88 objecttypen: "
             "basisVergunningNummer, datumVergunningOfMelding en vergunningsPlicht",
     "gir": "uitdrukkelijk buiten scope gelaten — de Omgevingsvergunning-entiteit is "
            "vervangen door een directe relatie Vergunninghouder → MBA, en een "
            "vergunningnummer komt nergens in het datamodel voor",
     "les": "Geen van beide maakt er een entiteit van, maar daar houdt de gelijkenis op. IMEV "
            "bewaart de identificatie van de vergunning; GIR laat hem vallen. Wie de twee "
            "registers op vergunning wil koppelen, kan dat aan één kant wel en aan de andere "
            "niet."},
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
    {"kop": "Twee registers over dezelfde bedrijven, en één harde sleutel",
     "wat": "Van de twaalf begrippen die het REV en het GIR beide vastleggen, zijn er drie op "
            "een gedeelde sleutel te joinen — en alle drie komen van buiten: het KvK-nummer, "
            "het vestigingsnummer en de BAG-identificatie. Het bedrijf zelf, het bevoegd gezag, "
            "de vergunning en de stof hebben in elk register een eigen sleutel of geen. Wat de "
            "twee registers verbindt, is dus niet wat zij samen hebben afgesproken maar wat zij "
            "elk los van de ander uit een basisregistratie overnemen.",
     "bron": "12 begrippen naast elkaar: 3 joinbaar, 2 deels, 7 niet"},
    {"kop": "IMEV dwingt af dat je zegt waarom een gegeven ontbreekt",
     "wat": "Elf velden in IMEV zijn Voidable: zij mogen leeg zijn, maar dan is een "
            "geenWaardeReden verplicht — gegevenInTransitie, nietVanToepassing of "
            "waardeOnbekend. Het staat op 166 plekken in het schema, en precies op de "
            "identificaties: vergunningnummer, KvK-nummer, BAG-pand. Dat is de zekerheid per "
            "veld uit het waterdossier, maar als standaard in plaats van als labvinding. Aan de "
            "GIR-kant is hetzelfde gegeven simpelweg NULL.",
     "bron": "imev30-schema.yaml, Voidable + VoidReasonValue"},
    {"kop": "Bevoegd gezag is in het ene register een bestuurslaag en in het andere een organisatie",
     "wat": "IMEV heeft bevoegdGezag als enumeratie van vier waarden: rijk, provincie, gemeente, "
            "gegevenInTransitie. GIR heeft reg_org met een OIN van Logius en leidt bevoegdheid af "
            "uit een ruimtelijke vraag op het werkgebied. Uit 'gemeente' volgt niet welke "
            "gemeente, en uit een OIN volgt geen bestuurslaag. Beide zijn juist binnen hun eigen "
            "systeem; samen leveren zij geen antwoord op dezelfde vraag.",
     "bron": "IMEV BevoegdGezag-enum tegenover GIR §4.19.1"},
    {"kop": "Alle drie leunen op andere standaarden, en geen van drieën op elkaar",
     "wat": "GIR erft van RGBZ en ImZTC (zaakgericht werken) plus Juriconnect en BWB voor "
            "wetgeving. IMEV erft van BAG, het handelsregister en NEN3610. CIM-VTH-Flo probeert "
            "er een laag overheen te leggen. In geen van de drie documenten wordt naar de "
            "andere twee verwezen.",
     "bron": "GIR §4.37/§4.38, IMEV-schema, CIM-VTH-Flo"},
]

# De overlap tussen IMEV 3.0 en het GIR-datamodel, begrip voor begrip. Dit is de vraag die
# ertoe doet zodra iemand de twee registers wil koppelen: niet "lijken ze op elkaar" maar
# "waarop kun je joinen". `join` is daarom het belangrijkste veld hier.
OVERLAP = [
    {"begrip": "De Seveso-inrichting zelf",
     "gir": "reg_mba met mba_soort = Seveso-inrichting, plus parent_mba_id voor "
            "subactiviteiten (niet geïmplementeerd)",
     "imev": "SevesoInrichting als eigen objecttype, 19 properties",
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
     "imev": "CASNummer als eigen type, met een reguliere expressie die het formaat afdwingt",
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
     "imev": "Voidable: het veld mag ontbreken, maar dan moet er een geenWaardeReden bij — "
             "gegevenInTransitie, nietVanToepassing of waardeOnbekend",
     "join": "nee", "waarom": "Dit is het scherpste verschil. IMEV dwingt af dat je zégt "
             "waarom iets leeg is; 11 velden mogen zo leeg, op 166 plekken in het schema. Een "
             "NULL in GIR zegt niets."},
    {"begrip": "Historie",
     "gir": "reg_locatie_historie bestaat; reg_mba_historie en "
            "reg_mba_attribuut_waarde_historie zijn ontworpen maar nooit gebouwd",
     "imev": "een /historie-endpoint per resource, werkend",
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
    "live": ["de REV-OpenAPI en het IMEV-schema, rechtstreeks van rev-portaal.nl opgehaald "
             "en hier geteld",
             "de velden per IMEV-objecttype: welke 44 een vergunningnummer dragen, welke 11 "
             "Voidable zijn, en wat de enumeratie BevoegdGezag precies bevat",
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


def telling() -> dict:
    return {"lagen": len(LAGEN), "vertalingen": len(VERTALINGEN),
            "bevindingen": len(BEVINDINGEN), "overlap": len(OVERLAP),
            **{f"join_{k}": v for k, v in overlap_telling().items()},
            "imev_voidable_velden": 11, "imev_voidable_plekken": 166,
            "imev_met_vergunningnummer": 44,
            "imev_definities": 168, "imev_objecttypen": 88,
            "imev_referentietypen": 41, "imev_enumeraties": 27,
            "rev_resources": 2, "rev_paden": 20,
            "gir_tabellen": 38, "gir_niet_gebouwd": 10,
            "cim_views": 7}


def analyse() -> dict:
    return {"bronnen": BRONNEN, "lagen": LAGEN, "vertalingen": VERTALINGEN,
            "overlap": OVERLAP, "bevindingen": BEVINDINGEN,
            "herkomst": HERKOMST, "telling": telling()}
