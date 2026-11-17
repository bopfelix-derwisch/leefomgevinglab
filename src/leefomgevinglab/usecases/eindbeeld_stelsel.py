"""Het functioneel eindbeeld van het stelsel leefomgeving, als gebouw dat je kunt rondlopen.

**Waarom een gebouw.** De vorige maquette toonde vijf plateaus door de tijd en werd te druk: wie
geen architect is, ziet dan platen zweven. Een gebouw kent iedereen. Het heeft een **fundering**
waar alles op rust, **verdiepingen** die op elkaar staan, een **dak** waar de regels vandaan
komen, en twee **gevels**: aan de ene kant wordt geleverd, aan de andere kant gehaald. Je loopt
eromheen en van elke kant zie je iets anders — en dát is precies wat een architectuurplaat op
papier niet kan.

De indeling is niet verzonnen maar die van BALO zelf. §5.5 "Functioneel eindbeeld stelsel" zet
de stelselafspraken en waardeketens bovenaan, de bevoegde gezagen links, de gebruikers rechts, en
onderaan de fysieke stelselinfrastructuur met de basisregistraties. §8.1 beschrijft de
informatieketen in vijf niveaus: data → informatie → kennis → inzicht en handelingsperspectief,
met terugkoppeling die de keten sluit — "geen lineaire productielijn, maar een leercyclus". Die
vier niveaus zijn de verdiepingen; de terugkoppeling loopt er als trappenhuis dwars doorheen,
want zij gaat naar beneden terwijl al het andere omhoog gaat.

**De vensters zijn de vragen.** BALO stelt door het hele stuk heen vragen die in het eindbeeld
beantwoord moeten worden — over API's, over bronhouderschap, over wat er op een locatie geldt.
Die staan hier **woordelijk** in de gevels, op het vlak waar zij thuishoren. Een gebouw met
vensters waar niets achter zit is een plaatje; een venster met een echte vraag erin maakt het een
werkstuk. Welke vraag bij welk vlak hoort is wel een lezing van dit lab — zie `HERKOMST`.

**Wat dit niet is.** Geen vastgesteld beleid. BALO v1.0 draagt zelf de status CONCEPT, het
eindbeeld is "ontwikkeld samen met het programma D-VTH en is nog in bewerking", en de verdeling
van informatiefuncties heet in de doelarchitectuur een werkhypothese. Het gebouw staat er dus
als voorstel, niet als besluit.
"""

#: De fundering. In BALO's plaat de onderste balk: de fysieke stelselinfrastructuur waarop alle
#: applicaties zijn aangesloten, en daaronder de basisregistraties. Je ziet haar pas als je
#: ondér het gebouw gaat kijken — en dat is precies het punt: niemand denkt eraan, iedereen
#: leunt erop.
BODEMPLAAT = {
    "naam": "Bodemplaat",
    "kop": "Waar alles op rust",
    "wat": "De fysieke stelselinfrastructuur waarop lokale en centrale applicaties zijn "
           "aangesloten — API's, eHerkenning, de digitale infrastructuur van de "
           "basisregistraties.",
    "waarom": "Dit is de laag waar niemand aan denkt en iedereen op leunt. Valt zij weg, dan "
              "staat er niets meer: geen loket, geen dataspace, geen eigen tool. Daarom ligt "
              "zij hier als plaat onder het gebouw en niet als blokje ernaast.",
    "onderdelen": [
        "Applicaties lokaal en centraal aangesloten op de fysieke stelselinfrastructuur",
        "API's en eHerkenning",
        "Digitale infrastructuur van de basisregistraties",
    ],
    "bron": "BALO v1.0 §5.5, onderste balk van het functioneel eindbeeld",
}

#: Het dak. Bovenin BALO's plaat staan de stelselafspraken, en daaronder de waardeketens die het
#: domein ordenen. Van bovenaf gezien is dat wat het gebouw bij elkaar houdt: niet techniek maar
#: afspraken en opgaven.
DAK = {
    "naam": "Dak",
    "kop": "Wat het gebouw bij elkaar houdt",
    "wat": "De stelselafspraken van het VTH-stelsel: eenheid van taal, governance en "
           "verandermanagement. Daaronder hangen de waardeketens die zeggen wáárvoor het "
           "stelsel bestaat.",
    "waarom": "Een federatief stelsel heeft geen centrale baas; wat het bij elkaar houdt zijn "
              "afspraken. Die staan daarom boven de techniek en niet ernaast — van bovenaf zie "
              "je waar het gebouw door wordt afgedekt.",
    "onderdelen": [
        "Eén taal en vaste identificaties",
        "Bronverantwoordelijkheid",
        "Kwaliteit per gebruiksdoel",
        "Toegangsafspraken",
        "Governance en verandermanagement",
    ],
    "bron": "BALO v1.0 §5.5, bovenste balk; stelselafspraken ook in de doelarchitectuur",
}

#: De verdiepingen, van onder naar boven: de informatieketen van BALO §8.1. Elke verdieping zegt
#: wat er op dat niveau ontstaat, en wat er nodig is om een niveau hoger te komen -- dat laatste
#: is wat een trap tot een trap maakt in plaats van een stapel dozen.
VERDIEPINGEN = [
    {"id": "data", "nr": 1, "naam": "Data",
     "wat": "Ruwe of gestructureerde gegevens over feiten, objecten, locaties, activiteiten, "
            "stoffen, meldingen, vergunningen, inspecties of indicatoren.",
     "omhoog": "Data wordt pas informatie als duidelijk is in welke context zij geldt: welk "
               "object, welke contour, welk werkingsgebied, welke beperking.",
     "aanbod": ["Registraties in zaaksystemen van bevoegd gezag en omgevingsdienst",
                 "Registraties in plansystemen (omgevingsdocumenten, toepasbare regels)",
                 "Meetnetten en geo-informatie",
                 "Basis- en sectorale registraties"],
     "vraag": ["Eigen GIS en lokale systemen halen gegevens rechtstreeks bij de bron"]},
    {"id": "informatie", "nr": 2, "naam": "Informatie",
     "wat": "Data die betekenis krijgt in een context: wie heeft gemeld, waarop heeft het "
            "betrekking, welke status geldt, is het gevalideerd, en voor welk gebruiksdoel is "
            "het geschikt.",
     "omhoog": "Informatie wordt pas kennis als zij wordt geduid en verbonden met regels, "
               "ervaring en handelingskennis.",
     "aanbod": ["Kwaliteitsprocessen bij de bronhouder",
                 "Metadata, herkomst en andere kwaliteitsinformatie",
                 "Compliance en validatie in de dataspace"],
     "vraag": ["Dataspaces of hubs per milieuthema leveren informatieproducten",
                "Kwaliteitsbeelden",
                "Consumeerbare data voor wie zelf wil combineren"]},
    {"id": "kennis", "nr": 3, "naam": "Kennis",
     "wat": "Uitleg van regelgeving, toepassing van informatiemodellen, interpretatie van "
            "toezichtinformatie, duiding van risico's, beleidskennis en gezaghebbende "
            "antwoorden.",
     "omhoog": "Kennis wordt pas inzicht als zij leidt tot een keuze, een besluit of een "
               "interventie.",
     "aanbod": ["Kennisontsluiting via IPLO, ook machineleesbaar",
                 "Regels en kennis als code",
                 "Begrippen, informatiemodellen en standaarden"],
     "vraag": ["Het digitale loket: wat geldt hier en wat is hier vergund",
                "Kennisproducten voor beleid",
                "Gezaghebbende antwoorden, ook voor AI-tools"]},
    {"id": "inzicht", "nr": 4, "naam": "Inzicht en handelingsperspectief",
     "wat": "Een gebiedsafweging, een toezichtprioriteit, een beleidsmonitor, een publiekskaart, "
            "een vergunningbeoordeling of een antwoord aan een gebruiker.",
     "omhoog": "Hier houdt de keten op — en begint de terugkoppeling: wat hier blijkt, moet "
               "terug naar beneden.",
     "aanbod": ["Analyses voor toezicht",
                 "Risicobeelden over thema's heen"],
     "vraag": ["Dossiers en signalen in lokale systemen",
                "De vergunde ruimte op een locatie",
                "Atlassen en publiekskaarten",
                "Eigen AI-agents van de gebruiker"]},
]

#: Het trappenhuis: terugkoppeling en leren. Dit is het enige dat naar benéden loopt, en daarom
#: krijgt het een eigen plek dwars door alle verdiepingen in plaats van een vijfde verdieping.
#: BALO zegt het zelf: de keten is geen lineaire productielijn maar een leercyclus.
TRAPPENHUIS = {
    "naam": "Terugkoppeling en leren",
    "kop": "Het enige dat naar beneden loopt",
    "wat": "Signalen uit toezicht, gebruik, datakwaliteit, gebruikersvragen, monitoring en "
           "beleidsverantwoording vloeien terug naar bronhouders, registers, "
           "informatiemodellen, standaarden, kennisproducten en beleid.",
    "waarom": "Zonder deze weg terug is het gebouw een fabriek: er gaat data in en er komt een "
              "product uit, en niemand hoort het als het product niet klopt. Mét deze weg is "
              "het een leercyclus — en dat is wat BALO er zelf over zegt.",
    "bron": "BALO v1.0 §8.1, 'de informatieketen is geen lineaire productielijn, maar een "
            "leercyclus'",
}

#: De twee gevels. Links wordt geleverd, rechts wordt gehaald. Wie om het gebouw heen loopt, ziet
#: dus letterlijk een andere kant van dezelfde verdiepingen.
GEVELS = [
    {"id": "aanbod", "naam": "Aanbodgevel", "kant": "links",
     "kop": "Wie levert",
     "wat": "Bevoegde gezagen, omgevingsdiensten, meetnetten en basisregistraties. In het "
            "eindbeeld ontsluit de bron zélf, met metadata en herkomst — geen aanleverportalen "
            "meer.",
     "wie": ["Bevoegd gezag en omgevingsdiensten", "Meetnetbeheerders", "Bedrijven die melden",
              "Houders van basisregistraties"]},
    {"id": "vraag", "naam": "Vraaggevel", "kant": "rechts",
     "kop": "Wie haalt",
     "wat": "Vergunningverleners, toezichthouders, beleidsmakers, bedrijven en burgers. Zij "
            "combineren consumeerbare data met eigen tools in plaats van te wachten op een "
            "landelijke viewer.",
     "wie": ["Vergunningverlening", "Toezicht en handhaving", "Beleid", "Bedrijven en branche",
              "Burgers"]},
]

#: De vragen die BALO door het stuk heen stelt, **woordelijk**. Elk venster in het gebouw draagt
#: er één. `vlak` is waar het venster zit — en dat is een lezing van dit lab (zie `HERKOMST`):
#: BALO stelt de vragen, maar hangt ze niet aan een gevel.
#:
#: Een venster zonder vraag erachter is een plaatje; dit is wat het gebouw een werkstuk maakt.
VRAGEN = [
    # Dak: waarvoor bestaat het stelsel, en wie besluit wat.
    {"vraag": "Waarom doen we dit en wat is het?", "vlak": "dak"},
    {"vraag": "Welke waardestromen zijn leidend voor de doelarchitectuur?", "vlak": "dak"},
    {"vraag": "Welke informatiebehoeften zijn bepalend voor de informatiepositie?",
     "vlak": "dak"},
    {"vraag": "Welke diensten moet RWS duurzaam organiseren?", "vlak": "dak"},
    {"vraag": "Waar is consolidatie logisch en waar is variatie inhoudelijk noodzakelijk?",
     "vlak": "dak"},
    {"vraag": "Welke informatiefuncties keren over meerdere waardestromen terug?",
     "vlak": "dak"},

    # Bodemplaat: de techniek waarop alles rust.
    {"vraag": "Welke API's bestaan of zijn nodig?", "vlak": "bodemplaat"},
    {"vraag": "Wie beheert de API?", "vlak": "bodemplaat"},
    {"vraag": "Waar worden API's geregistreerd?", "vlak": "bodemplaat"},
    {"vraag": "Welke specificatie geldt?", "vlak": "bodemplaat"},
    {"vraag": "Hoe wordt versiebeheer gedaan?", "vlak": "bodemplaat"},
    {"vraag": "Welke non-functionals gelden?", "vlak": "bodemplaat"},
    {"vraag": "Welke toegang is nodig?", "vlak": "bodemplaat"},
    {"vraag": "Welke generieke bouwstenen zijn kansrijk?", "vlak": "bodemplaat"},
    {"vraag": "Welke patronen kunnen domeinbreed worden toegepast?", "vlak": "bodemplaat"},

    # Aanbodgevel: wat een bronhouder moet regelen.
    {"vraag": "Waar is een eigen register, dataproduct of voorziening nodig?", "vlak": "aanbod",
     "verdieping": "data"},
    {"vraag": "Welke informatieobjecten, begrippen en standaarden zijn leidend?",
     "vlak": "aanbod", "verdieping": "informatie"},
    {"vraag": "Waar moet RWS aansluiten op bestaande stelsels en standaarden?",
     "vlak": "aanbod", "verdieping": "kennis"},
    {"vraag": "Wat moet goed gaan?", "vlak": "aanbod", "verdieping": "inzicht"},

    # Vraaggevel: wat een gebruiker wil weten.
    {"vraag": "Welke beperkingen gelden op deze locatie?", "vlak": "vraag",
     "verdieping": "kennis"},
    {"vraag": "Welke risico's, contouren of milieubelastingen zijn relevant?", "vlak": "vraag",
     "verdieping": "inzicht"},
    {"vraag": "Welke feedback krijgt de gebruiker?", "vlak": "vraag", "verdieping": "informatie"},
    {"vraag": "Welke kwaliteit heeft deze data en welke beperkingen gelden voor gebruik?",
     "vlak": "vraag", "verdieping": "data"},
]

#: De standpunten: van welke kant je het gebouw bekijkt, en wat je dan ziet. Dit is de lijst
#: waaruit de pagina haar knoppen maakt, zodat er geen tweede opsomming bestaat.
STANDPUNTEN = [
    {"id": "aanbod", "naam": "Aanbodzijde", "ziet": "Wie levert er in elke verdieping",
     "draai": {"x": 8, "y": 62}},
    {"id": "vraag", "naam": "Vraagzijde", "ziet": "Wie haalt er uit elke verdieping",
     "draai": {"x": 8, "y": -62}},
    # **Let op het teken.** In CSS kantelt een positieve `rotateX` de bovenkant van de kijker
    # wég, dus van bovenaf kijken is een negatieve hoek. Dat stond hier eerst omgekeerd, en toen
    # toonde de knop "Van boven" het gebouw van onderen -- alleen te zien door ernaar te kijken.
    {"id": "dak", "naam": "Van boven", "ziet": "De stelselafspraken en de beleidsopgaven",
     "draai": {"x": -62, "y": 0}},
    {"id": "bodemplaat", "naam": "Van onder", "ziet": "De bodemplaat waar alles op rust",
     "draai": {"x": 58, "y": 0}},
    {"id": "doorsnede", "naam": "Doorsnede", "ziet": "De vier verdiepingen op elkaar",
     "draai": {"x": 6, "y": 0}},
]

#: Wat uit BALO komt en wat dit lab erbij leest. Dezelfde discipline als `/modellen` en `/balo`.
HERKOMST = [
    {"wat": "De indeling bovenaan (stelselafspraken, waardeketens), links de bevoegde gezagen, "
            "rechts de gebruikers en onderaan de fysieke stelselinfrastructuur",
     "van": "bron", "bron": "BALO v1.0 §5.5, figuur 'Functioneel eindbeeld'"},
    {"wat": "De vier verdiepingen: data, informatie, kennis, inzicht en handelingsperspectief",
     "van": "bron", "bron": "BALO v1.0 §8.1, de informatieketen in vijf niveaus"},
    {"wat": "Terugkoppeling en leren als weg terug naar beneden",
     "van": "bron", "bron": "BALO v1.0 §8.1, 'geen lineaire productielijn, maar een leercyclus'"},
    {"wat": "De vragen in de vensters, woordelijk",
     "van": "bron", "bron": "BALO v1.0, verspreid door het stuk"},
    {"wat": "Op welk vlak een vraag hangt, en op welke verdieping",
     "van": "lab", "bron": "BALO stelt de vragen maar hangt ze niet aan een gevel of een niveau; "
                            "die plaatsing is een lezing van dit lab"},
    {"wat": "Het gebouw als vorm — fundering, verdiepingen, dak, twee gevels",
     "van": "lab", "bron": "BALO tekent een platte figuur. Dat die figuur zich als gebouw laat "
                            "lezen is de keuze van dit lab, gemaakt zodat iemand zonder "
                            "architectuuropleiding er omheen kan lopen"},
]


def vragen_per_vlak(vlak: str) -> list[dict]:
    """De vensters op één vlak, in de volgorde waarin ze staan."""
    return [v for v in VRAGEN if v["vlak"] == vlak]


def telling() -> dict:
    """Alles wat de pagina als aantal noemt, hier geteld -- nooit in de tekst getypt."""
    per_vlak: dict[str, int] = {}
    for v in VRAGEN:
        per_vlak[v["vlak"]] = per_vlak.get(v["vlak"], 0) + 1
    return {
        "verdiepingen": len(VERDIEPINGEN),
        "vragen": len(VRAGEN),
        "vragen_per_vlak": per_vlak,
        "standpunten": len(STANDPUNTEN),
        "gevels": len(GEVELS),
        # Hoeveel vragen aan een verdieping hangen: dat zijn de vensters die meebewegen als je
        # een verdieping kiest, tegenover de vragen die over het hele gebouw gaan.
        "vragen_op_een_verdieping": sum(1 for v in VRAGEN if v.get("verdieping")),
        "bron_regels": sum(1 for h in HERKOMST if h["van"] == "bron"),
        "lab_regels": sum(1 for h in HERKOMST if h["van"] == "lab"),
    }


def gebouw() -> dict:
    """Het hele eindbeeld: fundering, verdiepingen, dak, gevels, trappenhuis en de vensters."""
    return {
        "bodemplaat": {**BODEMPLAAT, "vragen": vragen_per_vlak("bodemplaat")},
        "dak": {**DAK, "vragen": vragen_per_vlak("dak")},
        "verdiepingen": VERDIEPINGEN,
        "trappenhuis": TRAPPENHUIS,
        "gevels": [{**g, "vragen": vragen_per_vlak(g["id"])} for g in GEVELS],
        "standpunten": STANDPUNTEN,
        "herkomst": HERKOMST,
        "telling": telling(),
    }
