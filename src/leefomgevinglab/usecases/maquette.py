"""De maquette: de doelarchitectuur stelsel leefomgeving 2037, met de transitie als derde as.

**Wat dit is.** Een schaalmodel van het stelselbeeld 2037 waar je door de tijd kunt reizen. Vijf
**plateaus** (2026 · 2027 · 2028-2030 · 2031-2033 · 2034-2037) liggen achter elkaar in de diepte;
op elk plateau staan de RWS-voorzieningen uit de roadmap, verdeeld over drie lagen. Tussen twee plateaus
zit een **gap**: wat er verandert. Dat is geen metafoor maar de staande woordenschat van deze
wereld -- ArchiMate kent in zijn Implementation & Migration-uitbreiding letterlijk `Plateau` ("a
relatively stable state of the architecture during a limited period of time") en `Gap`, en TOGAF
noemt hetzelfde een *Transition Architecture* op weg naar de *Target Architecture*. Een
architectuurplaat die alleen het eindbeeld toont, laat juist het enige weg waar een
managementbesluit over gaat: de weg ernaartoe.

**Waarom dit een eigen pagina is en niet een kolom bij `/dvth`.** `/dvth` is één dossier: één MBA
Seveso-inrichting door de keten. Dit is het stelsel eromheen, en de vraag is een andere -- niet
"hoe loopt dit geval" maar "wie doet in 2037 wat, en wat moet er tussen nu en dan besloten
worden". Ze delen de begrippen en verwijzen naar elkaar.

**De bronnen, en wat van wie is.**

* `Doelarchitectuur stelsel LO 2037 en roadmap v0.1` (concept, 9-10 november 2026) -- hieruit
  komen de vijf plateaus, de voorzieningen met hun fasetekst, de beslismomenten en de
  plaatsing van de informatiefuncties in 2037. De fasetekst is **geciteerd**, niet samengevat.
* `BALO businessarchitectuur v1.0` -- de waardestromen (§6.3) en de informatiefuncties
  (§8.4), in BALO's eigen woorden. Woordelijk gelijk aan de v0.9 die `/balo` gebruikt; dat is
  nagekeken, de waardestromen zijn tussen die twee versies niet veranderd.

**En wat van dit lab is: de plaatsing in de lagen.** De bron zegt per informatiefunctie waar zij
in 2037 hoort ("bij de bron", "in de dataspace", "landelijk: IPLO"), maar zegt niet per
voorziening in welke laag zij per plateau staat. Die plaatsing (`lagen` per voorziening) is **een
lezing van dit lab** van de geciteerde fasetekst -- dat een REV waarvan de bronhouders zelf
leveren naar de aanbodlaag schuift, en dat een Atlas waarvan de presentatie naar DSO-LV en lokale
GIS verschuift naar de vraaglaag beweegt. Die beweging is wat de maquette toont, en zij is
daarom als interpretatie gemarkeerd (`HERKOMST`), niet als brongegeven. Het alternatief --
voorzieningen stil op één plek laten staan -- zou een transitiepad tonen waarin niets beweegt.

**Niets in deze module is vastgesteld beleid.** De bron zegt het zelf herhaaldelijk: fasering en
jaartallen zijn een voorstel ter toetsing, de verdeling van informatiefuncties is een
werkhypothese, en vast staan alleen de offerteperiode D-VTH 2027-2030, visie DSO 2032 en
eindbeeld 2037. `VASTSTAAND` houdt die drie apart van de rest, zodat de pagina het verschil kan
laten zien in plaats van het in een voetnoot te verstoppen.
"""

#: De drie lagen van het stelselbeeld (slide 1 van de doelarchitectuur). Dit is de verticale as
#: van de maquette. De kleuren verwijzen naar de triade die dit lab al gebruikt voor "drie lagen"
#: (`/kmg`: kan · mag · gebeurt), zodat de kleur betekenis draagt in plaats van versiering te zijn.
LAGEN = [
    {"id": "aanbod", "naam": "Aanbod", "wie": "bronhouders",
     "wat": "VTH- en zaaksystemen, plan- en regelsystemen, meetnetten en geo-bronnen, basis- en "
            "sectorale registraties.",
     "belofte": "Geen aanleverportalen meer: de bron ontsluit zelf, met metadata, herkomst en "
                "herstel na terugmelding."},
    {"id": "knooppunt", "naam": "Knooppunt", "wie": "landelijke voorzieningen en dataspaces",
     "wat": "Landelijke voorzieningen, thematische dataspaces en de federatieve afspraken "
            "daartussen.",
     "belofte": "Kwaliteitsborging en informatieproducten, niet een extra kopie van de data."},
    {"id": "vraag", "naam": "Vraag", "wie": "gebruikers",
     "wat": "Bevoegd gezag en omgevingsdiensten, initiatiefnemers en bedrijven, beleidsmakers, "
            "en eigen (AI-)tools en lokale GIS.",
     "belofte": "Gebruikers combineren consumeerbare data zelf."},
]

#: De vijf plateaus. `stelselstand` is geciteerd uit de rij "Stelsel en programma" van de roadmap.
PLATEAUS = [
    {"id": "p2026", "label": "Nu", "jaren": "2026", "naam": "Vertrekpunt",
     "stelselstand": "BALO v1.0 vastgesteld; offerte D-VTH; stelselbeeld in concept"},
    {"id": "p2027", "label": "Fase 1", "jaren": "2027", "naam": "Verkennen en besluiten",
     "stelselstand": "Start uitvoering D-VTH. Verkenningen leveren per thema eindbeeld, roadmap "
                     "en advies"},
    {"id": "p2830", "label": "Fase 2", "jaren": "2028-2030",
     "naam": "Ontkoppelen en standaardiseren",
     "stelselstand": "Proeftuinen D-VV en D-TH opschalen; eenheid van taal in beheer; einde "
                     "offerteperiode"},
    {"id": "p3133", "label": "Fase 3", "jaren": "2031-2033", "naam": "Federeren",
     "stelselstand": "Visie DSO 2032; thematische dataspaces werken; aansluitvoorwaarden gelden"},
    {"id": "p3437", "label": "Fase 4", "jaren": "2034-2037", "naam": "Afbouwen en borgen",
     "stelselstand": "Tijdelijke portalen, registers en viewers zijn afgebouwd"},
]

#: De informatiefuncties (BALO §8.4) met hun plaats in 2037 volgens de doelarchitectuur.
#: `laag` is afgeleid uit die plaatsbepaling -- "bij de bron" is de aanbodlaag, "dataspace" het
#: knooppunt, "eigen tools" de vraagkant -- en staat dus in `HERKOMST` als lezing van dit lab.
FUNCTIES = [
    {"id": "F1", "naam": "Ontvangen en innemen",
     "plek_2037": "Omgevingsloket, of ophalen bij de bron", "laag": "knooppunt"},
    {"id": "F2", "naam": "Valideren en verrijken",
     "plek_2037": "Bij de bron; compliance in dataspace", "laag": "aanbod"},
    {"id": "F3", "naam": "Registreren en beheren",
     "plek_2037": "Bij de bronhouder, niet centraal", "laag": "aanbod"},
    {"id": "F4", "naam": "Beschikbaar stellen en delen",
     "plek_2037": "Gegevensdiensten bij de bron", "laag": "aanbod"},
    {"id": "F5", "naam": "Lokaliseren en ruimtelijk duiden",
     "plek_2037": "Geometrie bij bron, duiding bij gebruiker", "laag": "vraag"},
    {"id": "F6", "naam": "Analyseren en signaleren",
     "plek_2037": "Dataspace en eigen (AI-)tools", "laag": "knooppunt"},
    {"id": "F7", "naam": "Monitoren en verantwoorden",
     "plek_2037": "Informatieproducten uit dataspace", "laag": "knooppunt"},
    {"id": "F8", "naam": "Kennis ontsluiten en verklaren",
     "plek_2037": "Landelijk: IPLO, kennis als code", "laag": "knooppunt"},
    {"id": "F9", "naam": "Terugkoppelen en leren",
     "plek_2037": "Stelselbreed: naar bron en beleid", "laag": "vraag"},
]

#: De waardestromen (BALO §6.3). Woordelijk gelijk aan `balo.py` (v0.9) -- nagekeken.
WAARDESTROMEN = [
    {"id": "W1", "wat": "Van beleidsopgave naar uitvoerbare regels, kennis en informatie"},
    {"id": "W2", "wat": "Van registratie naar ruimtelijke informatiepositie en gebiedsafweging"},
    {"id": "W3", "wat": "Van kennisvraag naar gezaghebbend antwoord"},
    {"id": "W4", "wat": "Van initiatief naar oriëntatie, aanvraag of melding"},
    {"id": "W5", "wat": "Van melding of aanvraag naar besluit en publicatie"},
    {"id": "W6", "wat": "Van verplichting naar gegevensaanlevering en betrouwbare registratie"},
    {"id": "W7", "wat": "Van registratie naar toezicht, risicoanalyse en interventie"},
    {"id": "W8", "wat": "Van uitvoeringsdata naar beleidsmonitoring en publieke verantwoording"},
]

#: De stelselafspraken (slide 1).
STELSELAFSPRAKEN = ["Eén taal", "vaste identificaties", "bronverantwoordelijkheid",
                     "kwaliteit per gebruiksdoel", "toegangsafspraken",
                     "governance en verandermanagement"]

#: De voorzieningen uit de roadmap (één per rij). `fasen` is **geciteerd** uit de roadmap, per plateau. `lagen` is de
#: lezing van dit lab: in welke laag staat deze voorziening op dat plateau (zie de moduledocstring
#: en `HERKOMST`). `rol_2037` met `rol_open: True` betekent dat de bron daar een `?` zet.
VOORZIENINGEN = [
    {"id": "dso", "naam": "DSO-componenten in RWS-beheer",
     "toelichting": "Omgevingsloket, RTR, STAM, STTR",
     "w": ["W4", "W5"], "f": ["F1", "F4", "F8"],
     "lagen": {"p2026": "knooppunt", "p2027": "knooppunt", "p2830": "knooppunt",
                "p3133": "knooppunt", "p3437": "knooppunt"},
     "fasen": {
         "p2026": "Beheer en doorontwikkeling van loketfunctie, RTR, STAM en STTR",
         "p2027": "DSO-tenzij-afwegingskader vaststellen: welke aanleveringen kunnen via het "
                  "loket?",
         "p2830": "Thematische meldingen via loket en STAM waar de grondslag past; koppelvlak "
                  "met VTH-zaaksystemen",
         "p3133": "Loket is voorkeurskanaal voor initiatief en melding; vergunninginformatie "
                  "herbruikbaar uit DSO-LV",
         "p3437": "Stabiel beheer; samenwerkfunctie verbonden met toezichtinformatie"},
     "rol_2037": "Beheerder landelijke voorziening", "rol_open": False, "besluit": None},
    {"id": "iplo", "naam": "IPLO-kennisontsluiting",
     "toelichting": "inclusief ZZS-kennis en helpdesk",
     "w": ["W1", "W3"], "f": ["F8", "F9"],
     "lagen": {"p2026": "knooppunt", "p2027": "knooppunt", "p2830": "knooppunt",
                "p3133": "knooppunt", "p3437": "knooppunt"},
     "fasen": {
         "p2026": "Website, helpdesk en kennisnetwerken; schakel tussen beleid en uitvoering",
         "p2027": "IPLO-opdracht 2027 met ondersteuning D-VTH; gezaghebbend bronprofiel en "
                  "begrippenbeheer",
         "p2830": "Kennis als data: metadata, bronverwijzing, actualiteit. AI-patroon "
                  "gecontroleerd beproeven",
         "p3133": "Kennis machineleesbaar ontsloten voor loket, lokale systemen en AI-tools van "
                  "gebruikers",
         "p3437": "Regels en kennis als code; menselijke validatie geborgd"},
     "rol_2037": "Kennispartner voor mens en machine", "rol_open": False, "besluit": None},
    {"id": "rev", "naam": "REV",
     "toelichting": "Register Externe Veiligheidsrisico's",
     "w": ["W2", "W6", "W7"], "f": ["F1", "F2", "F3", "F4", "F5"],
     # De beweging die de bron beschrijft: van register mét aanleverportaal naar een dataspace
     # waar bronhouders zelf leveren. Dat is een verschuiving naar de aanbodlaag.
     "lagen": {"p2026": "knooppunt", "p2027": "knooppunt", "p2830": "knooppunt",
                "p3133": "knooppunt", "p3437": "aanbod"},
     "fasen": {
         "p2026": "Register met aanleverportaal, API's, kaarten en kwaliteitsdashboard",
         "p2027": "Registerprofiel opstellen als referentiecasus; informatiebehoefte toezicht "
                  "toevoegen",
         "p2830": "Validatie en kwaliteitsdashboard losmaken als generieke bouwsteen; API's als "
                  "beheerde gegevensdiensten",
         "p3133": "Bronhouders leveren via eigen gegevensdienst; REV wordt dataspace externe "
                  "veiligheid",
         "p3437": "Aanleverportaal afbouwen zodra bronnen federatief leveren"},
     "rol_2037": "Kwaliteitsbewaker en eigenaar informatieproducten", "rol_open": True,
     "besluit": None},
    {"id": "lma", "naam": "LMA (voorziening AMICE)",
     "toelichting": "inclusief afvalmonitor; raakvlak UPV en circulaire economie",
     "w": ["W4", "W6", "W7", "W8"], "f": ["F1", "F2", "F3", "F4", "F6", "F9"],
     "lagen": {"p2026": "knooppunt", "p2027": "knooppunt", "p2830": "knooppunt",
                "p3133": "knooppunt", "p3437": "knooppunt"},
     "fasen": {
         "p2026": "Wettelijke meldingen ontvangen, registreren en leveren; bron voor VTH en CE",
         "p2027": "Productvisie aanscherpen met BALO; koppelvlak met D-VTH; gevolgen EVOA en "
                  "DIWASS",
         "p2830": "Generieke validatie scheiden van afvalregels; meldgegevens als gegevensdienst "
                  "voor toezicht en CE",
         "p3133": "Dataspace afval en grondstoffen, gekoppeld aan product- en ketendata",
         "p3437": "Wettelijke melding blijft landelijk ontvangen; overige data federatief"},
     "rol_2037": "Registerdienst met wettelijke taak", "rol_open": False, "besluit": None},
    {"id": "gir", "naam": "GIR",
     "toelichting": "inspecties Seveso-bedrijven",
     "w": ["W7"], "f": ["F3", "F6", "F9"],
     # "Inspectieresultaten als gegevensdienst uit systemen van toezichthouders" -- de functie
     # verhuist naar de bronhouders, dus naar de aanbodlaag.
     "lagen": {"p2026": "knooppunt", "p2027": "knooppunt", "p2830": "knooppunt",
                "p3133": "aanbod", "p3437": "aanbod"},
     "fasen": {
         "p2026": "Inspectiemethodiek en ondersteunend zaaksysteem; rapportages",
         "p2027": "Verkenning samenloop GIR, Inspectieview Milieu en samenwerkfunctie DSO; "
                  "model mappen op eenheid van taal",
         "p2830": "Toezichtinformatiepatroon beproeven in D-TH",
         "p3133": "Inspectieresultaten als gegevensdienst uit systemen van toezichthouders",
         "p3437": "Tijdelijke route afbouwen waar DSO of dataspace de functie levert"},
     "rol_2037": "Methodiek en kennis blijven", "rol_open": True,
     "besluit": {"plateau": "p2830", "vraag": "blijft, koppelt, verandert of vervalt?"}},
    {"id": "atlas", "naam": "Atlas Leefomgeving",
     "toelichting": "publieke kaartviewer",
     "w": ["W2", "W8"], "f": ["F5", "F7"],
     # "Presentatie verschuift naar DSO-LV, lokale GIS en AI-tools" -- de presentatiefunctie gaat
     # naar de vraagkant; wat blijft is het maken van informatieproducten.
     "lagen": {"p2026": "vraag", "p2027": "vraag", "p2830": "knooppunt",
                "p3133": "knooppunt", "p3437": "knooppunt"},
     "fasen": {
         "p2026": "Kaartviewer en contentbeheer; kaartlagen onder meer uit REV",
         "p2027": "Positie bepalen naast viewer DSO-LV, Zicht op Nederland en PDOK: wat is "
                  "leidend voor wie?",
         "p2830": "Kaartlagen als OGC-gegevensdiensten volgens Geo-profiel Leefomgeving",
         "p3133": "Presentatie verschuift naar DSO-LV, lokale GIS en AI-tools; Atlas levert "
                  "informatieproducten",
         "p3437": "Eigen viewer afbouwen of behouden voor de publieksfunctie?"},
     "rol_2037": "Eigenaar publieke informatieproducten", "rol_open": True,
     "besluit": {"plateau": "p3437",
                  "vraag": "eigen viewer afbouwen of behouden voor de publieksfunctie?"}},
    {"id": "lavs", "naam": "LAVS, Bodem+ en lucht",
     "toelichting": "nog niet uitgewerkt in BALO (backlog H9)",
     "w": ["W2", "W6"], "f": [],
     "lagen": {"p2026": "aanbod", "p2027": "aanbod", "p2830": "aanbod",
                "p3133": "knooppunt", "p3437": "knooppunt"},
     "fasen": {
         "p2026": "Afzonderlijke registraties; deels grondslag Wet milieubeheer",
         "p2027": "Eerst uitwerken: opdrachten DGWB, Bodemrichtlijn, emissieregisters lucht",
         "p2830": "Aansluiten op de generieke bouwstenen in plaats van eigen oplossingen",
         "p3133": "Volgt het patroon van register naar dataspace, tenzij de grondslag anders "
                  "vraagt",
         "p3437": "Afbouw tijdelijke routes per thema"},
     "rol_2037": "Per thema te bepalen", "rol_open": True, "besluit": None},
    {"id": "bouwstenen", "naam": "Generieke bouwstenen Leefomgeving",
     "toelichting": "over de voorzieningen heen",
     "w": [], "f": ["F1", "F2", "F3", "F4", "F5", "F6", "F7", "F8", "F9"],
     "lagen": {"p2026": "knooppunt", "p2027": "knooppunt", "p2830": "knooppunt",
                "p3133": "knooppunt", "p3437": "knooppunt"},
     "fasen": {
         "p2026": "Elke voorziening lost intake, validatie, delen en terugmelden zelf op",
         "p2027": "Prioriteren op optimalisatie en vernieuwing; open bouwblokken invullen "
                  "(register, service bus, aanleverportaal)",
         "p2830": "Eerst: validatieframework, gegevensdelingsprofiel, terugmeldvoorziening, "
                  "registerprofiel",
         "p3133": "Bouwstenen als dataspace-functies aanbieden aan het stelsel; "
                  "vertrouwensprofiel stelselbreed",
         "p3437": "Beheer belegd; bouwstenen voor aanlevering uitgefaseerd"},
     "rol_2037": "Leverancier herbruikbare bouwstenen", "rol_open": True, "besluit": None},
    {"id": "ctd", "naam": "CTD en AI-infrastructuur",
     "toelichting": "vindbaarheid en verantwoord AI-gebruik",
     "w": [], "f": ["F4", "F6", "F8"],
     "lagen": {"p2026": "knooppunt", "p2027": "knooppunt", "p2830": "knooppunt",
                "p3133": "knooppunt", "p3437": "vraag"},
     "fasen": {
         "p2026": "CTD RWS-breed beschikbaar; AI-proeven versnipperd",
         "p2027": "Verkenning bijdrage CTD aan federatief stelsel; verhouding tot DataOD.nl",
         "p2830": "Dataproducten vindbaar via catalogus, met kwaliteitsinformatie; "
                  "AI-infrastructuur in proeftuin",
         "p3133": "Kwaliteit en herkomst meegeleverd met elke gegevensdienst; AI-robuustheid "
                  "getoetst",
         "p3437": "Gebruikers bevragen het stelsel met eigen AI-tools"},
     "rol_2037": "Catalogus- en kwaliteitsfunctie", "rol_open": True, "besluit": None},
    {"id": "tijdelijk", "naam": "Tijdelijke voorzieningen van anderen",
     "toelichting": "RMBA, DataOD.nl, Inspectieview Milieu — geen eigendom RWS",
     "w": [], "f": [],
     "lagen": {"p2026": "knooppunt", "p2027": "knooppunt", "p2830": "knooppunt",
                "p3133": "aanbod", "p3437": None},
     "fasen": {
         "p2026": "RMBA tijdelijk opgeleverd; kwaliteitsproces omgevingsdiensten loopt",
         "p2027": "Advies over RMBA; positie opnemen in doelarchitectuur om dubbele functies te "
                  "voorkomen",
         "p2830": "RMBA naar DSO-LV of naar dataspace VTH-kerninformatie?",
         "p3133": "Vergunningdata beschikbaar bij de bron of via landelijk knooppunt",
         "p3437": "Tijdelijke platformen afgebouwd"},
     "rol_2037": "Adviseur; beheerrol open", "rol_open": True,
     "besluit": {"plateau": "p2830",
                  "vraag": "RMBA naar DSO-LV of naar dataspace VTH-kerninformatie?"}},
]

#: De beslismomenten uit de roadmap, elk gekoppeld aan het plateau waarop zij vallen.
BESLISMOMENTEN = [
    {"nr": "I", "plateau": "p2027", "wanneer": "2027", "kop": "Rolkeuze per voorziening",
     "vraag": "Waar neemt RWS regie, waar kadert RWS mee, waar sluit RWS alleen aan?"},
    {"nr": "II", "plateau": "p2830", "wanneer": "uiterlijk 2030",
     "kop": "Blijft, koppelt, verandert of vervalt",
     "vraag": "Per voorziening: blijft, koppelt, verandert van functie of vervalt. Eigenaar per "
              "thematische dataspace."},
    {"nr": "III", "plateau": "p3133", "wanneer": "vanaf 2033", "kop": "Afbouw pas na bewijs",
     "vraag": "Afbouw van een tijdelijke route pas als bron en dataspace de functie aantoonbaar "
              "leveren."},
]

#: De vaste transitievragen die de roadmap per voorziening stelt. Dit is het
#: TOGAF-achtige raamwerk eronder: niet "wat wordt het" maar "wie draagt de overgang".
TRANSITIEVRAGEN = [
    "Welke functie vervult zij nu tijdelijk?",
    "Wie vervult die functie in 2037?",
    "Welke besluiten, standaarden en investeringen zijn nodig?",
    "Wie is eigenaar van de transitie?",
]

#: Wat er volgens de bron zelf **vaststaat**, tegenover al het andere. De bron zegt drie keer dat
#: de rest een voorstel is; dit houdt die drie apart zodat de pagina het verschil kan tonen in
#: plaats van het in een voetnoot te verstoppen.
VASTSTAAND = [
    "de offerteperiode D-VTH 2027-2030",
    "visie DSO 2032",
    "eindbeeld 2037",
]

#: Per onderdeel: komt het uit een bron, of is het een lezing van dit lab? Dezelfde discipline als
#: `/balo` en `/modellen`: structuur en begrippen uit het document, de koppeling van dit lab, en
#: dat onderscheid staat op de pagina en niet alleen in de code.
HERKOMST = [
    {"wat": "De vijf plateaus met hun jaren en namen",
     "van": "bron", "bron": "Doelarchitectuur stelsel LO 2037 en roadmap v0.1 (concept)"},
    {"wat": "De fasetekst per voorziening, woordelijk",
     "van": "bron", "bron": "idem, rij per voorziening"},
    {"wat": "De beslismomenten en de vaste transitievragen",
     "van": "bron", "bron": "idem"},
    {"wat": "De waardestromen en de informatiefuncties",
     "van": "bron", "bron": "BALO businessarchitectuur v1.0 (§6.3 en §8.4)"},
    {"wat": "De plaats van elke informatiefunctie in 2037",
     "van": "bron", "bron": "Doelarchitectuur, slide 1 — met de kanttekening van de bron zelf "
                             "dat die verdeling een werkhypothese is"},
    {"wat": "In welke laag een voorziening per plateau staat, en dus hoe zij door de maquette "
            "beweegt",
     "van": "lab", "bron": "lezing van dit lab op de geciteerde fasetekst: een REV waarvan "
                            "bronhouders zelf leveren schuift naar de aanbodlaag, een Atlas "
                            "waarvan de presentatie naar DSO-LV verschuift beweegt naar de "
                            "vraaglaag. De bron plaatst de voorzieningen niet in lagen."},
    {"wat": "De indeling van de functies in de drie lagen",
     "van": "lab", "bron": "afgeleid uit de plaatsbepaling van de bron ('bij de bron' → aanbod, "
                            "'dataspace' → knooppunt, 'eigen tools' → vraag)"},
]


def _plateau_ids() -> list[str]:
    return [p["id"] for p in PLATEAUS]


def gaps(voorziening: dict) -> list[dict]:
    """Wat er tussen twee opeenvolgende plateaus verandert voor één voorziening.

    **Waarom de gap een eigen ding is.** In ArchiMate en TOGAF is de `Gap` het object waartegen
    je plant: niet de toestand maar het verschil. Een architectuurplaat die alleen plateaus toont,
    laat weg waar het besluit over gaat. Hier wordt per overgang vastgelegd of de voorziening van
    laag wisselt (`verschuift`) en of zij ophoudt te bestaan (`vervalt`) -- beide afgeleid uit
    `lagen`, nooit apart ingetypt, zodat de gap niet uit de pas kan lopen met de plateaus.
    """
    uit = []
    ids = _plateau_ids()
    for vorige, volgende in zip(ids, ids[1:]):
        van, naar = voorziening["lagen"].get(vorige), voorziening["lagen"].get(volgende)
        uit.append({
            "van_plateau": vorige, "naar_plateau": volgende,
            "van_laag": van, "naar_laag": naar,
            "verschuift": bool(van and naar and van != naar),
            "vervalt": bool(van and naar is None),
            "tekst": voorziening["fasen"].get(volgende, ""),
        })
    return uit


def plateau_beeld(plateau_id: str) -> dict:
    """Eén plateau: welke voorzieningen staan er, in welke laag, en wat gebeurt er dat jaar.

    Een voorziening zonder laag op dit plateau is afgebouwd en staat **niet** in `per_laag` -- zij
    komt terug in `afgebouwd`, met de fasetekst erbij. Weglaten zonder meer zou de afbouw stil
    maken, en juist die afbouw is de kern van fase 4.
    """
    plateau = next(p for p in PLATEAUS if p["id"] == plateau_id)
    per_laag = {laag["id"]: [] for laag in LAGEN}
    afgebouwd = []
    for v in VOORZIENINGEN:
        laag = v["lagen"].get(plateau_id)
        post = {"id": v["id"], "naam": v["naam"], "toelichting": v["toelichting"],
                 "w": v["w"], "f": v["f"], "rol_2037": v["rol_2037"],
                 "rol_open": v["rol_open"],
                 "tekst": v["fasen"].get(plateau_id, ""),
                 "besluit": (v["besluit"]["vraag"]
                              if v["besluit"] and v["besluit"]["plateau"] == plateau_id else None)}
        if laag is None:
            afgebouwd.append(post)
        else:
            per_laag[laag].append(post)
    return {
        **plateau,
        "per_laag": per_laag,
        "afgebouwd": afgebouwd,
        "beslismoment": next((b for b in BESLISMOMENTEN if b["plateau"] == plateau_id), None),
        # Afgeleid, nooit getypt: hoeveel voorzieningen staan er dit plateau, en hoeveel van hun
        # rollen in 2037 zijn nog onbeslist.
        "aantal_voorzieningen": sum(len(v) for v in per_laag.values()),
        "aantal_rol_open": sum(1 for lijst in per_laag.values() for v in lijst if v["rol_open"]),
    }


def telling() -> dict:
    """Alles wat de pagina als aantal noemt, hier geteld."""
    beweegt = [v["id"] for v in VOORZIENINGEN if len(set(v["lagen"].values())) > 1]
    return {
        "plateaus": len(PLATEAUS),
        "lagen": len(LAGEN),
        "voorzieningen": len(VOORZIENINGEN),
        "functies": len(FUNCTIES),
        "waardestromen": len(WAARDESTROMEN),
        "stelselafspraken": len(STELSELAFSPRAKEN),
        "beslismomenten": len(BESLISMOMENTEN),
        "transitievragen": len(TRANSITIEVRAGEN),
        "vaststaand": len(VASTSTAAND),
        # Hoeveel voorzieningen van laag wisselen: dat is de maat voor hoeveel er in dit
        # transitiepad werkelijk beweegt, en dus of de maquette iets te tonen heeft.
        "voorzieningen_die_bewegen": len(beweegt),
        "beweegt": beweegt,
        "rollen_open_in_2037": sum(1 for v in VOORZIENINGEN if v["rol_open"]),
        "functies_per_laag": {laag["id"]: sum(1 for f in FUNCTIES if f["laag"] == laag["id"])
                               for laag in LAGEN},
    }


def maquette() -> dict:
    """Het hele model: de plateaus met hun beeld, de begrippen eromheen, en de herkomst."""
    return {
        "lagen": LAGEN,
        "plateaus": [plateau_beeld(p["id"]) for p in PLATEAUS],
        "voorzieningen": [{**v, "gaps": gaps(v)} for v in VOORZIENINGEN],
        "functies": FUNCTIES,
        "waardestromen": WAARDESTROMEN,
        "stelselafspraken": STELSELAFSPRAKEN,
        "beslismomenten": BESLISMOMENTEN,
        "transitievragen": TRANSITIEVRAGEN,
        "vaststaand": VASTSTAAND,
        "herkomst": HERKOMST,
        "telling": telling(),
    }
