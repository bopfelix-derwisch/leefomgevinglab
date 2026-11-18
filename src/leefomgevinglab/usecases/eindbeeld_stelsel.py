"""Het eindbeeld als gebiedsdoorsnede: de leefomgeving bovenop, en wat eronder zit.

**Waarom een doorsnede van een gebied en niet een abstract blok.** Twee eerdere versies van deze
maquette faalden op hetzelfde: zij toonden het *stelsel* — plateaus, en daarna een gebouw. Dat
leest alleen voor wie al architect is. De fysieke leefomgeving is echter geen metafoor: er ligt
een gebied, daar staat een bedrijf, daar loost het op een rivier, daar woont iemand op
vierhonderd meter. Wie met data en ICT werkt begrijpt een **doorsnede door de grond** meteen —
bovenop zie je het gebied, en naar beneden zie je waar de gegevens vandaan komen.

Vier lagen, van boven naar beneden:

1. **Het gebied** — wat er fysiek is, en wat er gebeurt. Een vergunningaanvraag, een melding,
   een inspectie, iemand die wil weten wat hier mag.
2. **Wat er met gegevens gebeurt** — innemen, controleren, bewaren, delen, op de kaart zetten,
   signaleren, verantwoorden, uitleggen, terugmelden. Dit zijn BALO's negen informatiefuncties,
   maar die term staat er met opzet niet: wie geen architect is heeft er niets aan, en wie het
   wel is herkent ze aan het uitlegveld.
3. **Waarop het past** — de informatieobjecten en de standaarden die maken dat gegevens uit
   verschillende bronnen op elkaar aansluiten. Dit is de doorsnede: je ziet het pas als je het
   model opensnijdt, en het is precies wat niemand ziet tot het ontbreekt.
4. **De bodem** — de stekkerdozen: API's, inlogvoorzieningen, basisregistraties, en de regel dat
   gegevens bij de bron blijven.

**De doorkijk naar de architectuurwereld zit in elk element, niet in een voetnoot.** Elk ding in
deze maquette draagt twee extra velden: `architectuur` (hoe het in vaktaal heet — de
informatiefunctie, de waardestroom, het ArchiMate-begrip) en `waar` (de pagina in dit lab waar
het écht draait, met echte data). Daarmee is dit geen vrijblijvende plaat: wie doorklikt komt bij
werkende code uit. `tests/test_eindbeeld_stelsel.py` dwingt af dat geen enkel element die twee
velden mist.

**Bronnen.** BALO businessarchitectuur v1.0 (§5.5 voor de indeling van het eindbeeld, §8.1 voor
de keten van data naar handelingsperspectief, §8.4 voor de negen functies) en de doelarchitectuur
stelsel LO 2037 (concept). De vragen in de uitlegvelden zijn woordelijk van BALO. Beide stukken
zijn intern; geen publieke URL, niet in de repo.

**Geen vastgesteld beleid.** BALO v1.0 draagt zelf de status concept en noemt het eindbeeld "nog
in bewerking"; de verdeling van functies heet in de doelarchitectuur een werkhypothese.
"""

#: Het gebied bovenop: wat er fysiek staat. Geen voorbeelden uit de lucht gegrepen -- dit is de
#: casus waar de rest van dit lab op draait (een Seveso-bedrijf dat loost op de Maas), zodat de
#: maquette en de werkende pagina's over hetzelfde gaan.
GEBIED = [
    {"id": "bedrijf", "naam": "Chemiebedrijf aan de rivier", "soort": "bedrijf",
     "wat": "Een bedrijf met gevaarlijke stoffen op het terrein. Het heeft een vergunning, "
            "loost op het water en krijgt inspectie.",
     "architectuur": "In het register een vestiging met een KvK- en vestigingsnummer; in IMEV "
                     "een LocatieEVActiviteit, in GIR een milieubelastende activiteit.",
     "waar": "/toezicht", "waar_tekst": "de 69 echte vergunningen in het Maasregister"},
    {"id": "lozingspunt", "naam": "Lozingspunt", "soort": "punt",
     "wat": "De plek waar het bedrijf water loost, met in de vergunning per stof een "
            "grenswaarde.",
     "architectuur": "Een voorschrift met parameter, waarde, eenheid en bemonsteringsregime; "
                     "het geografische punt in RD-coördinaten.",
     "waar": "/wasstraat", "waar_tekst": "de voorschriften, met hun gaten"},
    {"id": "meetpunt", "naam": "Meetpunt in de rivier", "soort": "meting",
     "wat": "Hier wordt gemeten wat er werkelijk in het water zit — los van wat er vergund is.",
     "architectuur": "Meetwaarden uit het Waterkwaliteitsportaal, gekoppeld op Aquo-parameter "
                     "en hoedanigheid; getoetst aan een KRW-norm per meetpunt.",
     "waar": "/kmg", "waar_tekst": "kan · mag · gebeurt, op echte metingen"},
    {"id": "woonwijk", "naam": "Woonwijk op vierhonderd meter", "soort": "kwetsbaar",
     "wat": "Mensen die wonen binnen het bereik van een ongeval. Hun aanwezigheid bepaalt wat "
            "er mag.",
     "architectuur": "Verblijfsobjecten uit de BAG, geteld per gebruiksdoel en ingedeeld naar "
                     "kwetsbaarheid volgens bijlage VI van het Bkl.",
     "waar": "/evruimte", "waar_tekst": "de aandachtsgebieden, live uit de BAG geteld"},
    {"id": "water", "naam": "Het waterlichaam", "soort": "water",
     "wat": "De rivier zelf: wie hem beheert, welke norm er geldt, en wat er bovenstrooms "
            "gebeurt.",
     "architectuur": "Een KRW-oppervlaktewaterlichaam met eigen code, beheerder en toestand; "
                     "de schakel tussen een vergunning en een meting.",
     "waar": "/waterruimte", "waar_tekst": "prik op de kaart en zie wat er geldt"},
]

#: Wat er in het gebied gebeurt. Processen in gewone woorden -- een vergunningaanvraag heet hier
#: geen waardestroom, maar draagt er wel een.
PROCESSEN = [
    {"id": "aanvragen", "naam": "Een bedrijf vraagt iets aan", "wie": "bedrijf",
     "wat": "Mag dit hier, en wat moet ik aanleveren?",
     "architectuur": "Waardestroom W4: van initiatief naar oriëntatie, aanvraag of melding.",
     "waar": "/gebruiksruimte", "waar_tekst": "wat kan hier nog"},
    {"id": "besluiten", "naam": "Het bevoegd gezag besluit", "wie": "vergunningverlener",
     "wat": "Een vergunning met voorschriften, die daarna zelf weer gegevens zijn.",
     "architectuur": "Waardestroom W5: van melding of aanvraag naar besluit en publicatie; het "
                     "besluit als STOP/TPOD-document.",
     "waar": "/dvth", "waar_tekst": "de keten van loket tot register"},
    {"id": "melden", "naam": "Een bedrijf levert gegevens", "wie": "bedrijf",
     "wat": "Wat er geloosd is, wat er is afgevoerd, wat er is opgeslagen.",
     "architectuur": "Waardestroom W6: van verplichting naar gegevensaanlevering en "
                     "betrouwbare registratie.",
     "waar": "/afval", "waar_tekst": "de afvalketen, op open cijfers"},
    {"id": "toezicht", "naam": "Een toezichthouder gaat kijken", "wie": "toezichthouder",
     "wat": "Waar is het risico het grootst, en wat vraag ik ter plaatse?",
     "architectuur": "Waardestroom W7: van registratie naar toezicht, risicoanalyse en "
                     "interventie.",
     "waar": "/toezicht", "waar_tekst": "signalen met bewijs en herkomst"},
    {"id": "oriënteren", "naam": "Iemand wil weten wat hier mag", "wie": "burger",
     "wat": "Een omwonende, een adviseur of een journalist die de kaart opzoekt.",
     "architectuur": "Waardestroom W2: van registratie naar ruimtelijke informatiepositie en "
                     "gebiedsafweging.",
     "waar": "/evruimte", "waar_tekst": "de aandachtsgebieden op de kaart"},
    {"id": "verantwoorden", "naam": "Beleid kijkt of het werkt", "wie": "beleid",
     "wat": "Gaat het de goede kant op, en waar moet de regel anders?",
     "architectuur": "Waardestroom W8: van uitvoeringsdata naar beleidsmonitoring en publieke "
                     "verantwoording.",
     "waar": "/balo", "waar_tekst": "de redeneerlijnen en de witte vlekken"},
]

#: Laag 2: wat er met gegevens gebeurt. Dit zijn BALO's negen informatiefuncties (§8.4), hier
#: met een naam die een gewone lezer begrijpt. De vakterm staat in `architectuur` -- zo verliest
#: niemand iets: de ene lezer heeft het werkwoord, de andere de code.
HANDELINGEN = [
    {"id": "innemen", "naam": "Binnenhalen", "code": "F1",
     "wat": "Een aanvraag, een melding of een meting komt binnen — via een loket of doordat de "
            "bron het zelf klaarzet.",
     "architectuur": "Informatiefunctie F1 (ontvangen en innemen). In 2037: via het "
                     "Omgevingsloket, of ophalen bij de bron.",
     "waar": "/onderwater", "waar_tekst": "de pijplijn die dit echt doet"},
    {"id": "controleren", "naam": "Nakijken", "code": "F2",
     "wat": "Klopt het, is het volledig, en is het goed genoeg voor waar het voor gebruikt "
            "wordt?",
     "architectuur": "Informatiefunctie F2 (valideren en verrijken); kwaliteit per gebruiksdoel "
                     "is een stelselafspraak.",
     "waar": "/wasstraat", "waar_tekst": "de controle op echte vergunningen"},
    {"id": "bewaren", "naam": "Bewaren", "code": "F3",
     "wat": "Vastleggen wie wat wanneer heeft gezegd, zodat het later terug te vinden is.",
     "architectuur": "Informatiefunctie F3 (registreren en beheren). In 2037 bij de bronhouder, "
                     "niet centraal.",
     "waar": "/modellen", "waar_tekst": "hoe drie modellen dat verschillend doen"},
    {"id": "delen", "naam": "Doorgeven", "code": "F4",
     "wat": "Een ander systeem kan het ophalen — zonder te bellen, zonder een bestand te mailen.",
     "architectuur": "Informatiefunctie F4 (beschikbaar stellen en delen), als gegevensdienst "
                     "bij de bron.",
     "waar": "/vth-bronnen", "waar_tekst": "34 registraties en of ze bereikbaar zijn"},
    {"id": "plaatsen", "naam": "Op de kaart zetten", "code": "F5",
     "wat": "Waar ligt het, en wat ligt eromheen? Zonder plek is een gegeven zelden bruikbaar.",
     "architectuur": "Informatiefunctie F5 (lokaliseren en ruimtelijk duiden); geometrie bij de "
                     "bron, duiding bij de gebruiker.",
     "waar": "/evruimte", "waar_tekst": "aandachtsgebieden over de BAG"},
    {"id": "signaleren", "naam": "Opvallen", "code": "F6",
     "wat": "Uit losse gegevens komt een aanwijzing: hier klopt iets niet, hier moet je kijken.",
     "architectuur": "Informatiefunctie F6 (analyseren en signaleren), in de dataspace of met "
                     "eigen gereedschap.",
     "waar": "/toezicht", "waar_tekst": "tien regels, elk met bewijs"},
    {"id": "verantwoorden", "naam": "Laten zien hoe het gaat", "code": "F7",
     "wat": "Een cijfer waar beleid en publiek op kunnen vertrouwen.",
     "architectuur": "Informatiefunctie F7 (monitoren en verantwoorden), als informatieproduct "
                     "uit de dataspace.",
     "waar": "/eindbeeld", "waar_tekst": "hoe een informatieproduct eruitziet"},
    {"id": "uitleggen", "naam": "Uitleggen wat het betekent", "code": "F8",
     "wat": "Wat is een zeer kwetsbaar gebouw? Wat valt onder deze regel? Zonder uitleg is data "
            "geen kennis.",
     "architectuur": "Informatiefunctie F8 (kennis ontsluiten en verklaren); landelijk via "
                     "IPLO, en kennis als code.",
     "waar": "/begrippen", "waar_tekst": "tien termen, live uit de Stelselcatalogus"},
    {"id": "terugmelden", "naam": "Terugzeggen wat er fout was", "code": "F9",
     "wat": "Wie een fout vindt, meldt hem terug — anders blijft dezelfde fout iedereen hinderen.",
     "architectuur": "Informatiefunctie F9 (terugkoppelen en leren). BALO noemt de keten "
                     "daarom een leercyclus, geen productielijn.",
     "waar": "/kwaliteit", "waar_tekst": "wat er misgaat en wat eraan te doen is"},
]

#: Laag 3, de doorsnede: waarop gegevens passen. Per informatieobject de standaard die het
#: koppelbaar maakt, én wat er misgaat zonder. Dat laatste is het punt van deze laag -- een
#: standaard is onzichtbaar tot zij ontbreekt.
AANSLUITINGEN = [
    {"id": "vergunning", "object": "Vergunning en voorschrift",
     "standaard": "IMEV 3.0 · STOP/TPOD",
     "verbindt": "het besluit van het bevoegd gezag met het register en met de kaart",
     "zonder": "Een vergunningnummer is dan een tekstveld; twee registers over hetzelfde "
               "bedrijf zijn niet te koppelen.",
     "architectuur": "IMEV is het informatiemodel bij Geonovum; het berichtschema erbij is "
                     "toetsbaar, de API-specificatie draagt zelf geen inhoud.",
     "waar": "/modellen", "waar_tekst": "IMEV naast GIR, begrip voor begrip"},
    {"id": "meting", "object": "Meting en norm", "standaard": "Aquo · KRW",
     "verbindt": "wat een bedrijf mag lozen met wat er in het water gemeten wordt",
     "zonder": "'Zink' in een vergunning en 'Zn' in een meting blijven twee dingen. Zonder "
               "hoedanigheid vergelijk je bovendien twee verschillende grootheden.",
     "architectuur": "De Aquo-domeintabel Parameter als sleutel; normen uit de "
                     "KRW-toetsresultaten, per meetpunt gecorrigeerd.",
     "waar": "/kennisgraaf", "waar_tekst": "de koppeling stof → code, met herkomst per rand"},
    {"id": "locatie", "object": "Locatie en gebouw", "standaard": "BAG · NEN3610",
     "verbindt": "een adres, een pand en een punt op de kaart met elkaar",
     "zonder": "Iedere bron telt zijn eigen woningen, en niemand weet of het dezelfde zijn.",
     "architectuur": "Basisregistratie Adressen en Gebouwen; NEN3610 als gedeeld "
                     "geo-informatiemodel onder de sectorale modellen.",
     "waar": "/evruimte", "waar_tekst": "verblijfsobjecten per gebruiksdoel geteld"},
    {"id": "begrip", "object": "Begrip en definitie", "standaard": "Stelselcatalogus · SKOS",
     "verbindt": "het woord in de wet met het veld in het systeem",
     "zonder": "Iedereen gebruikt 'inrichting' en 'activiteit' net anders, en de discussie gaat "
               "over taal in plaats van over de zaak.",
     "architectuur": "Een federatieve SKOS-begrippengraaf; 'eenheid van taal' is in BALO een "
                     "stelselafspraak en geen wens.",
     "waar": "/begrippen", "waar_tekst": "tien termen met hun juridische vindplaats"},
    {"id": "zaak", "object": "Zaak en besluit", "standaard": "RGBZ · ImZTC",
     "verbindt": "het dossier bij de omgevingsdienst met het landelijke beeld",
     "zonder": "Het besluit bestaat wel, maar niemand buiten het zaaksysteem kan ernaar "
               "verwijzen.",
     "architectuur": "Zaakgericht werken; in het GIR-informatiemodel draagt een Besluit een "
                     "eigen identificatie, in het databasemodel is het buiten scope.",
     "waar": "/modellen", "waar_tekst": "waarom die twee niet op elkaar passen"},
    {"id": "uitwisseling", "object": "De uitwisseling zelf", "standaard": "OGC API · REST",
     "verbindt": "het ene systeem met het andere, zonder tussenpersoon",
     "zonder": "Dan is er weer een portaal nodig waar iemand bestanden heen stuurt.",
     "architectuur": "Gegevensdiensten bij de bron in plaats van aanleverportalen — het "
                     "scharnierpunt van het federatieve eindbeeld.",
     "waar": "/wfs-kwaliteit", "waar_tekst": "een live scan over alle lagen"},
]

#: Laag 4, de bodem: de stekkerdozen. Niet de inhoud maar de voorziening waar alles in geprikt
#: wordt. Je ziet hem nooit, tot hij het niet doet.
BODEM = [
    {"id": "koppelvlakken", "naam": "De stopcontacten", "wat": "API's waar systemen in prikken",
     "architectuur": "Fysieke stelselinfrastructuur waarop lokale en centrale applicaties zijn "
                     "aangesloten.",
     "waar": "/vth-bronnen", "waar_tekst": "welke er zijn, en welke antwoorden"},
    {"id": "toegang", "naam": "De sleutel", "wat": "Weten wie er aanklopt: eHerkenning en "
                                                     "andere inlogvoorzieningen",
     "architectuur": "Toegangsafspraken als stelselafspraak; autorisatie per gebruiksdoel.",
     "waar": "/onderwater", "waar_tekst": "wat een route wel en niet mag"},
    {"id": "basis", "naam": "De fundering", "wat": "Basisregistraties: adressen, gebouwen, "
                                                     "ondergrond, topografie",
     "architectuur": "Digitale infrastructuur van de basisregistraties — BAG, BGT, BRO.",
     "waar": "/viewer", "waar_tekst": "live bevraagd, niet gekopieerd"},
    {"id": "bron", "naam": "Data blijft waar zij ontstaat", "wat": "Geen aanleverportalen meer: "
                                                                    "de bron zet zelf klaar",
     "architectuur": "Bronverantwoordelijkheid; in 2037 levert de bronhouder via een eigen "
                     "gegevensdienst, met metadata en herkomst.",
     "waar": "/waterruimte", "waar_tekst": "het register live bevraagd bij de bron"},
]

#: De lagen zelf, van boven naar beneden. `snijvlak` zegt of deze laag pas zichtbaar wordt als je
#: het model opensnijdt -- dat is wat een doorsnede een doorsnede maakt.
LAGEN = [
    {"id": "gebied", "nr": 1, "naam": "Het gebied",
     "kop": "Wat er is, en wat er gebeurt",
     "wat": "De fysieke leefomgeving: een bedrijf, een lozingspunt, een woonwijk, een rivier. "
            "En de dingen die er spelen — een aanvraag, een melding, een inspectie.",
     "snijvlak": False},
    {"id": "handelingen", "nr": 2, "naam": "Wat er met gegevens gebeurt",
     "kop": "Negen handelingen die steeds terugkomen",
     "wat": "Binnenhalen, nakijken, bewaren, doorgeven, op de kaart zetten, opvallen, laten zien "
            "hoe het gaat, uitleggen, en terugzeggen wat er fout was.",
     "snijvlak": False},
    {"id": "aansluitingen", "nr": 3, "naam": "Waarop het past",
     "kop": "De doorsnede",
     "wat": "De informatieobjecten en de standaarden die maken dat gegevens uit verschillende "
            "bronnen op elkaar aansluiten. Deze laag zie je niet — tot zij ontbreekt.",
     "snijvlak": True},
    {"id": "bodem", "nr": 4, "naam": "De bodem",
     "kop": "De stekkerdozen",
     "wat": "Stopcontacten, sleutels, fundering, en de regel dat gegevens blijven waar zij "
            "ontstaan.",
     "snijvlak": False},
]

#: Data die stroomt: waar iets begint, waar het uitkomt, en wat er onderweg gebeurt. Omhoog wordt
#: data informatie; omlaag gaat de correctie terug. Die tweede richting is wat een keten een
#: leercyclus maakt -- en zij wordt in platen bijna altijd vergeten.
STROMEN = [
    {"id": "omhoog", "richting": "omhoog", "naam": "Van bron naar beeld",
     "van": "bodem", "naar": "gebied",
     "wat": "Een meting bij een meetpunt wordt een getal in een register, krijgt een norm "
            "ernaast, en wordt een signaal op het scherm van een toezichthouder.",
     "architectuur": "De keten data → informatie → kennis → inzicht en handelingsperspectief "
                     "(BALO §8.1).",
     "waar": "/kmg", "waar_tekst": "die keten, op echte metingen"},
    {"id": "omlaag", "richting": "omlaag", "naam": "Van bevinding terug naar de bron",
     "van": "gebied", "naar": "bodem",
     "wat": "Een toezichthouder ziet dat een code niet klopt, meldt dat terug, en de bronhouder "
            "herstelt het. Anders struikelt iedereen over dezelfde fout.",
     "architectuur": "Terugkoppelen en leren (F9). BALO: 'geen lineaire productielijn, maar een "
                     "leercyclus'.",
     "waar": "/kwaliteit", "waar_tekst": "de fouten die dit lab zelf vond"},
]

#: Wat het oplevert, per soort lezer. Een maquette zonder dit is een plaat voor de bouwer.
WAARDE = [
    {"wie": "Een bedrijf", "waarde": "In één keer goed aanvragen of melden, en vooraf weten wat "
                                      "er geldt — in plaats van achteraf horen wat er miste."},
    {"wie": "Een vergunningverlener", "waarde": "Zien wat er al vergund is op deze plek, en een "
                                                 "besluit nemen dat daarna zelf weer bruikbaar "
                                                 "is als gegeven."},
    {"wie": "Een toezichthouder", "waarde": "Eén beeld per bedrijf: vergunning, meldingen, "
                                             "metingen en inspecties naast elkaar, met de vraag "
                                             "die je ter plaatse kunt stellen."},
    {"wie": "Een omwonende", "waarde": "Opzoeken wat hier mag en wat hier gebeurt, zonder een "
                                        "verzoek te hoeven indienen."},
    {"wie": "Beleid", "waarde": "Zien of de regel werkt, op uitvoeringsdata in plaats van op "
                                 "een uitvraag."},
    {"wie": "Wie met data en ICT werkt", "waarde": "Eén keer bouwen wat iedereen nodig heeft — "
                                                    "valideren, delen, terugmelden — in plaats "
                                                    "van per register opnieuw."},
]

#: Wat uit de bron komt en wat dit lab erbij leest.
HERKOMST = [
    {"wat": "De vier lagen: het gebied, wat er met gegevens gebeurt, waarop het past, en de "
            "bodem met de infrastructuur",
     "van": "bron", "bron": "BALO v1.0 §5.5, figuur 'Functioneel eindbeeld'"},
    {"wat": "De negen handelingen met gegevens",
     "van": "bron", "bron": "BALO v1.0 §8.4, de negen informatiefuncties"},
    {"wat": "De keten van data naar handelingsperspectief, en de terugkoppeling die hem sluit",
     "van": "bron", "bron": "BALO v1.0 §8.1"},
    {"wat": "De waardestromen bij de processen in het gebied",
     "van": "bron", "bron": "BALO v1.0 §6.3"},
    {"wat": "De namen in gewone taal: binnenhalen, nakijken, opvallen, terugzeggen",
     "van": "lab", "bron": "BALO noemt ze ontvangen, valideren, analyseren en terugkoppelen. De "
                            "vaktaal staat bij elk element in het uitlegveld, zodat niemand iets "
                            "verliest — maar de maquette opent in gewone woorden"},
    {"wat": "Het gebied als bovenste laag, met een concreet bedrijf aan een rivier",
     "van": "lab", "bron": "BALO tekent het stelsel, niet een gebied. Dit lab zet de fysieke "
                            "leefomgeving bovenop omdat dat de enige laag is die iedereen "
                            "herkent — en gebruikt daarvoor de casus waar de rest van dit lab "
                            "ook op draait"},
    {"wat": "Welke standaard bij welk informatieobject hoort, en wat er zonder misgaat",
     "van": "lab", "bron": "de standaarden zijn echt en worden in dit lab gebruikt; de koppeling "
                            "'zonder deze standaard gaat dit mis' is een lezing van dit lab, "
                            "gegrond in wat hier daadwerkelijk is misgegaan"},
]


def _alle_elementen() -> list[dict]:
    """Elk ding in de maquette dat een uitlegveld hoort te dragen. Eén plek, zodat de bewaking
    niet kan verouderen als er een lijst bijkomt."""
    return [*GEBIED, *PROCESSEN, *HANDELINGEN, *AANSLUITINGEN, *BODEM, *STROMEN]


def telling() -> dict:
    """Alles wat de pagina als aantal noemt, hier geteld."""
    elementen = _alle_elementen()
    return {
        "lagen": len(LAGEN),
        "in_het_gebied": len(GEBIED),
        "processen": len(PROCESSEN),
        "handelingen": len(HANDELINGEN),
        "aansluitingen": len(AANSLUITINGEN),
        "bodem": len(BODEM),
        "stromen": len(STROMEN),
        "waarde_voor": len(WAARDE),
        "elementen": len(elementen),
        # De doorkijk naar de architectuurwereld, geteld: hoeveel elementen verwijzen naar een
        # pagina in dit lab waar het écht draait. Is dat niet alles, dan is de maquette op die
        # plek vrijblijvend.
        "met_uitleg": sum(1 for e in elementen if e.get("architectuur")),
        "met_doorkijk": sum(1 for e in elementen if e.get("waar")),
        "paginas": sorted({e["waar"] for e in elementen if e.get("waar")}),
        "bron_regels": sum(1 for h in HERKOMST if h["van"] == "bron"),
        "lab_regels": sum(1 for h in HERKOMST if h["van"] == "lab"),
    }


def maquette() -> dict:
    """De hele doorsnede: de lagen met hun inhoud, de stromen, de waarde en de herkomst."""
    return {
        "lagen": LAGEN,
        "gebied": GEBIED,
        "processen": PROCESSEN,
        "handelingen": HANDELINGEN,
        "aansluitingen": AANSLUITINGEN,
        "bodem": BODEM,
        "stromen": STROMEN,
        "waarde": WAARDE,
        "herkomst": HERKOMST,
        "telling": telling(),
    }
