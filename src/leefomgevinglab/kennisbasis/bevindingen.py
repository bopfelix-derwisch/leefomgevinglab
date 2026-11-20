"""Het dossier *bevindingen VTH*: de bevindingen uit vier rapporten, met hun vindplaats.

**Waarom dit een dossier is en geen samenvatting.** Vier rapporten los naast elkaar leveren vier
samenvattingen; die kon je ook los lezen. Wat een kennisbasis toevoegt zijn de **verbanden**: de
ILT meet een achterstand, het Rli-advies noemt de oorzaak, de Evaluatiecommissie plaatst hem in
het stelsel, en de kabinetsreactie zegt welke oorzaak wel en welke niet wordt weggenomen. Die
vier uitspraken over hetzelfde onderwerp staan in `VERBANDEN` expliciet aan elkaar geknoopt, en
dat is de enige reden om ze in één dossier te zetten.

**Elke bevinding draagt een letterlijk citaat en een pagina.** Zie `vindplaats.py`: een test
controleert voor alle bevindingen dat de zinsnede werkelijk op die pagina van dat document staat.
Daarmee is het verschil tussen "dit rapport zegt" en "zo lees ik dit rapport" na te trekken in
plaats van te vertrouwen.

**Wat van dit lab is, staat als zodanig gemarkeerd.** De indeling in thema's, de verbanden, en de
aanknoping aan de maquette (`blokje`) zijn een lezing van dit lab -- de rapporten kennen elkaars
indeling niet en kennen de maquette al helemaal niet. `HERKOMST` zegt dat per onderdeel, zoals op
de andere architectuurpagina's van dit lab.

**De aanknoping aan de maquette is het antwoord op "wat betekenen de blokjes".** `/maquette`
toont het landschap van het eindbeeld als blokjes: een gebied bovenop, wat er met gegevens
gebeurt, waar het op past, en de bodem. Elk blokje is daar een plek in een plaat. Hier krijgt
datzelfde blokje een reden: *dit* is wat er volgens de rapporten vandaag op die plek misgaat. Een
blokje zonder bevinding is een plek waar dit dossier niets over zegt -- ook dat is informatie, en
`onbesproken()` maakt het zichtbaar in plaats van het weg te laten.
"""
from leefomgevinglab.usecases import eindbeeld_stelsel as eindbeeld_mod

#: De zeven thema's waarin dit lab de bevindingen indeelt. De rapporten gebruiken deze indeling
#: niet -- zij is gekozen omdat de vier bronnen elkaar hier raken, en staat als lezing in
#: `HERKOMST`. `vraag` is wat het thema aan een lezer vraagt; `blokje` is de plek in de maquette.
THEMAS = [
    {
        "id": "zicht",
        "naam": "Niemand weet precies wat er is",
        "vraag": "Welke vergunningen gelden er, en zijn ze nog actueel?",
        "blokje": "gebied/bedrijf",
        "kleur": "#e8674c",
    },
    {
        "id": "samenhang",
        "naam": "Het geheel valt in stukken",
        "vraag": "Wie houdt overzicht als één initiatief in losse aanvragen binnenkomt?",
        "blokje": "processen/aanvragen",
        "kleur": "#e8a33d",
    },
    {
        "id": "houvast",
        "naam": "De norm is minder hard geworden",
        "vraag": "Waaraan toets je, als de regel een zorgplicht of een open norm is?",
        "blokje": "aansluitingen/vergunning",
        "kleur": "#c9893f",
    },
    {
        "id": "verschillen",
        "naam": "Het verschilt per plek",
        "vraag": "Mag hetzelfde bedrijf in twee gemeenten iets anders?",
        "blokje": "processen/besluiten",
        "kleur": "#7fa05a",
    },
    {
        "id": "achteraf",
        "naam": "Bijsturen gebeurt pas achteraf",
        "vraag": "Wat doe je als de activiteit al heeft plaatsgevonden?",
        "blokje": "processen/toezicht",
        "kleur": "#5a9fa0",
    },
    {
        "id": "digitaal",
        "naam": "De digitale basis knelt",
        "vraag": "Komt het gegeven waar het nodig is, of werkt iedereen eromheen?",
        "blokje": "bodem/koppelvlakken",
        "kleur": "#5c82b8",
    },
    {
        "id": "leren",
        "naam": "Kennis blijft hangen waar ze ontstaat",
        "vraag": "Komt wat de uitvoering weet terug in beleid en regelgeving?",
        "blokje": "handelingen/terugmelden",
        "kleur": "#8e7ab5",
    },
]

OP_THEMA = {t["id"]: t for t in THEMAS}

#: De soorten bevinding. `signaal` en `conclusie` zijn wat een bron vaststelt, `kernoorzaak` is
#: waarom, `aanbeveling` is wat zij vraagt, en `reactie` is wat het kabinet ermee doet. De vier
#: bronnen gebruiken verschillende woorden; dit is de gemene noemer, en de keuze staat in
#: `HERKOMST`.
SOORTEN = ("signaal", "conclusie", "kernoorzaak", "aanbeveling", "reactie")

#: De bevindingen. `citaat` is letterlijk uit het document op `pagina`; `kop` en `wat` zijn de
#: weergave van dit lab. `blokje` verwijst naar een element van `/maquette`.
BEVINDINGEN = [
    # -- Rli-advies: de signalen uit de praktijk ------------------------------------------------
    {
        "id": "rli-overzicht",
        "bron": "rli", "soort": "signaal", "thema": "samenhang", "blokje": "processen/aanvragen",
        "kop": "Toezicht ziet de samenhang niet meer",
        "wat": "Door veel losse milieubelastende activiteiten, meer algemene regels en vrije "
               "indiening heeft een toezichthouder geen beeld meer van wat er bij één bedrijf "
               "bij elkaar hoort.",
        "citaat": "Toezichthouders hebben minder overzicht over de samenhang tussen activiteiten "
                  "en de milieurisico's die daaruit voortvloeien.",
        "pagina": 2,
        "adressant": "stelsel",
    },
    {
        "id": "rli-houvast",
        "bron": "rli", "soort": "signaal", "thema": "houvast", "blokje": "aansluitingen/begrip",
        "kop": "Minder houvast bij de beoordeling",
        "wat": "Zorgplichten, doelvoorschriften en open normen vragen per geval een onderbouwing. "
               "Dat kost tijd en levert bij bedrijven onzekerheid op.",
        "citaat": "Toezichthouders hebben minder houvast bij de beoordeling van activiteiten en "
                  "de bijbehorende milieurisico's.",
        "pagina": 2,
        "adressant": "stelsel",
    },
    {
        "id": "rli-verschillen",
        "bron": "rli", "soort": "signaal", "thema": "verschillen", "blokje": "processen/besluiten",
        "kop": "Meer verschillen tussen plekken",
        "wat": "Bestuurlijke afwegingsruimte en lokaal maatwerk maken de regels per gebied anders. "
               "Bedrijven ervaren het toezicht daardoor als minder uniform.",
        "citaat": "Toezichthouders hebben te maken met meer verschillen in regels door de "
                  "toegenomen bestuurlijke afwegingsruimte en lokaal maatwerk.",
        "pagina": 2,
        "adressant": "stelsel",
    },
    {
        "id": "rli-achteraf",
        "bron": "rli", "soort": "signaal", "thema": "achteraf", "blokje": "handelingen/signaleren",
        "kop": "Vaker achteraf bijsturen",
        "wat": "Minder controle vooraf betekent dat een activiteit al heeft plaatsgevonden als "
               "blijkt dat zij niet mocht. De kans op onomkeerbare gevolgen neemt toe.",
        "citaat": "Toezichthouders moeten vaker achteraf bijsturen nu er minder controle vooraf "
                  "is door de verschuiving van vergunningen naar algemene regels en zorgplichten.",
        "pagina": 2,
        "adressant": "stelsel",
    },
    {
        "id": "rli-oranje",
        "bron": "rli", "soort": "conclusie", "thema": "achteraf", "blokje": "processen/toezicht",
        "kop": "Steeds meer seinen op oranje",
        "wat": "De raad waarschuwt voor een neerwaartse spiraal: oplopende werkdruk, dalende "
               "toezichtniveaus, lagere pakkans, afnemend vertrouwen.",
        "citaat": "Bij elkaar opgeteld staan steeds meer seinen op oranje.",
        "pagina": 3,
        "adressant": "stelsel",
    },
    # -- Rli-advies: de vijf kernoorzaken ------------------------------------------------------
    {
        "id": "rli-ko1",
        "bron": "rli", "soort": "kernoorzaak", "thema": "leren", "blokje": "handelingen/uitleggen",
        "kop": "De verschuiving van verantwoordelijkheden is onvoldoende begeleid",
        "wat": "De wet legt een centrale verantwoordelijkheid bij bedrijven en burgers, maar "
               "niemand heeft hen uitgelegd wat die inhoudt.",
        "citaat": "De fundamentele verschuiving van verantwoordelijkheden die de Omgevingswet "
                  "beoogt, is onvoldoende begeleid",
        "pagina": 3,
        "adressant": "stelsel",
    },
    {
        "id": "rli-ko2",
        "bron": "rli", "soort": "kernoorzaak", "thema": "houvast", "blokje": "aansluitingen/vergunning",
        "kop": "Wat 'werken in de geest van de wet' betekent voor toezicht is niet doordacht",
        "wat": "Het uitgangspunt is bedacht voor beleid en vergunningverlening. Wat het voor een "
               "handhaver betekent die een overtreding moet onderbouwen, is overgeslagen.",
        "citaat": "De gevolgen van wat werken in de geest van de Omgevingswet betekent voor "
                  "toezicht en handhaving zijn onvoldoende doordacht.",
        "pagina": 3,
        "adressant": "stelsel",
    },
    {
        "id": "rli-ko3",
        "bron": "rli", "soort": "kernoorzaak", "thema": "achteraf", "blokje": "processen/verantwoorden",
        "kop": "De stelselherziening valt samen met grote onvoorziene opgaven",
        "wat": "Woningbouw, energie, circulaire economie en nieuwe milieuproblemen vragen "
               "tegelijk ruimte, terwijl het stelsel zelf nog niet staat.",
        "citaat": "De stelselherziening van de Omgevingswet valt samen met een groeiend aantal "
                  "grote, complexe en (deels) onvoorziene opgaven in de leefomgeving en "
                  "maatschappij.",
        "pagina": 3,
        "adressant": "stelsel",
    },
    {
        "id": "rli-ko4",
        "bron": "rli", "soort": "kernoorzaak", "thema": "samenhang", "blokje": "aansluitingen/zaak",
        "kop": "De integratie van milieuregels verloopt moeizaam",
        "wat": "De milieuregels moeten landen in de nieuwe instrumenten. Het omgevingsplan is "
               "daarbij de grootste klus.",
        "citaat": "De integratie van milieuregels in de nieuwe instrumenten van de Omgevingswet "
                  "verloopt moeizaam, met de omgevingsplannen als grootste opgave.",
        "pagina": 3,
        "adressant": "stelsel",
    },
    {
        "id": "rli-ko5",
        "bron": "rli", "soort": "kernoorzaak", "thema": "verschillen", "blokje": "processen/oriënteren",
        "kop": "Vertrouwen rekent niet met verschillen in kundigheid",
        "wat": "Het stelsel gaat uit van een initiatiefnemer die weet wat hij moet doen en dat "
               "ook wil. Die aanname houdt niet overal.",
        "citaat": "Het uitgangspunt van vertrouwen houdt onvoldoende rekening met verschillen in "
                  "kundigheid en motivatie binnen de samenleving, zowel bij bedrijven als bij "
                  "burgers.",
        "pagina": 3,
        "adressant": "stelsel",
    },
    # -- Rli-advies: de aanbevelingen ----------------------------------------------------------
    {
        "id": "rli-ab0",
        "bron": "rli", "soort": "aanbeveling", "thema": "leren", "blokje": "handelingen/terugmelden",
        "kop": "Eén programma voor toezicht en handhaving onder de Omgevingswet",
        "wat": "Beleid, uitvoering en bedrijfsleven samen in één tijdelijk programma, met de "
               "minister van VRO als voorzitter en het bedrijfsleven als betalende deelnemer.",
        "citaat": "Geef met een Programma 'Toezicht en Handhaving onder de Omgevingswet' de "
                  "samenwerking tussen overheden, uitvoeringsorganisaties en het bedrijfsleven "
                  "een nieuwe impuls",
        "pagina": 4,
        "adressant": "minister van VRO",
    },
    {
        "id": "rli-ab1",
        "bron": "rli", "soort": "aanbeveling", "thema": "leren", "blokje": "handelingen/uitleggen",
        "kop": "Verklein de onzekerheid over de eigen verantwoordelijkheid",
        "wat": "Maak met beleid of afspraken concreet wat van een initiatiefnemer verwacht wordt, "
               "zodat 'eigen verantwoordelijkheid' hanteerbaar wordt.",
        "citaat": "Verklein de onzekerheid bij bedrijven, omgevingsdiensten en bevoegde gezagen "
                  "met beleid of afspraken over de invulling van de eigen verantwoordelijkheid "
                  "van initiatiefnemers.",
        "pagina": 5,
        "adressant": "minister van VRO, IPO, VNG, UvW, bedrijfsleven",
    },
    {
        "id": "rli-ab2",
        "bron": "rli", "soort": "aanbeveling", "thema": "verschillen", "blokje": "processen/besluiten",
        "kop": "Formuleer criteria voor 'tenzij-situaties'",
        "wat": "'Decentraal, tenzij' werkt alleen als op tijd te herkennen is wanneer de tenzij "
               "geldt. Die criteria bestaan nu niet.",
        "citaat": "Formuleer criteria om 'tenzij-situaties' bij het uitgangspunt 'decentraal, "
                  "tenzij'",
        "pagina": 5,
        "adressant": "minister van VRO, staatssecretaris van IenW",
    },
    {
        "id": "rli-ab3",
        "bron": "rli", "soort": "aanbeveling", "thema": "leren", "blokje": "handelingen/terugmelden",
        "kop": "Benut de praktijkkennis en signaalfunctie van omgevingsdiensten",
        "wat": "Wat de uitvoering ziet, komt nu niet terug in de beleidscyclus. Daardoor ontstaat "
               "regelgeving die niet uitvoerbaar of niet handhaafbaar is.",
        "citaat": "Benut de praktijkkennis en signaalfunctie van de omgevingsdiensten beter",
        "pagina": 6,
        "adressant": "minister van VRO, staatssecretaris van IenW, Omgevingsdienst NL",
    },
    # -- ILT: de conclusies --------------------------------------------------------------------
    {
        "id": "ilt-zicht",
        "bron": "ilt", "soort": "conclusie", "thema": "zicht", "blokje": "gebied/bedrijf",
        "kop": "Omgevingsdiensten weten niet of hun vergunningen actueel zijn",
        "wat": "Niet dat ze verouderd zijn -- dat ze het niet wéten. Het zicht op het eigen "
               "vergunningenbestand ontbreekt.",
        "citaat": "Omgevingsdiensten hebben onvoldoende zicht op de actualiteit van hun "
                  "vergunningenbestand.",
        "pagina": 5,
        "adressant": "omgevingsdiensten",
    },
    {
        "id": "ilt-achterstand",
        "bron": "ilt", "soort": "conclusie", "thema": "zicht", "blokje": "handelingen/bewaren",
        "kop": "De omvang van de achterstand is onbekend",
        "wat": "Bij vrijwel alle 26 omgevingsdiensten is er een achterstand. Hoe groot, is niet "
               "vast te stellen -- en dat is zelf de bevinding.",
        "citaat": "De precieze omvang van de achterstanden is onbekend, maar duidelijk is dat bij "
                  "vrijwel alle omgevingsdiensten achterstanden zijn.",
        "pagina": 5,
        "adressant": "omgevingsdiensten",
    },
    {
        "id": "ilt-seveso",
        "bron": "ilt", "soort": "conclusie", "thema": "zicht", "blokje": "gebied/bedrijf",
        "kop": "Bij de zwaarste bedrijven haalt geen enkele dienst de afspraak",
        "wat": "Voor Seveso- en Rie4-bedrijven is 100% actueel afgesproken. De praktijk ligt "
               "tussen 58% en 86%, gemiddeld 73% -- zo'n 150 majeure risicobedrijven wachten op "
               "een actualisatie.",
        "citaat": "haalt geen enkele Seveso-omgevingsdienst dit. In de praktijk variëren de "
                  "percentages tussen de 58% en 86%",
        "pagina": 16,
        "adressant": "omgevingsdiensten",
    },
    {
        "id": "ilt-emissies",
        "bron": "ilt", "soort": "conclusie", "thema": "houvast", "blokje": "aansluitingen/vergunning",
        "kop": "Een verouderde vergunning staat meer uitstoot toe",
        "wat": "Zolang de vergunning niet is bijgewerkt, mag het bedrijf produceren onder de oude "
               "voorwaarden. Die zijn meestal ruimer dan de huidige eisen.",
        "citaat": "Deze voorwaarden staan vaak meer emissies toe.",
        "pagina": 6,
        "adressant": "omgevingsdiensten",
    },
    {
        "id": "ilt-buitenbeeld",
        "bron": "ilt", "soort": "conclusie", "thema": "achteraf", "blokje": "processen/toezicht",
        "kop": "Bedrijven raken buiten beeld",
        "wat": "Een achterstand bij actualisatie werkt door in het toezicht: zonder actuele "
               "vergunning is er niets om op te handhaven.",
        "citaat": "Door achterstanden bij actualisatie raken bedrijven buiten beeld.",
        "pagina": 6,
        "adressant": "omgevingsdiensten",
    },
    {
        "id": "ilt-meten",
        "bron": "ilt", "soort": "conclusie", "thema": "zicht", "blokje": "gebied/meetpunt",
        "kop": "Er is geen meetreeks om de schade aan af te lezen",
        "wat": "Door het ontbreken van meet- en monitoringsgegevens weet niemand hoe groot de "
               "gevolgen van de achterstand werkelijk zijn.",
        "citaat": "Door een gebrek aan meet- en monitoringsgegevens over emissies, gezondheid en "
                  "milieukwaliteit hebben omgevingsdiensten geen inzicht in de omvang en ernst "
                  "van de mogelijke schade en gevolgen.",
        "pagina": 6,
        "adressant": "omgevingsdiensten",
    },
    {
        "id": "ilt-archief",
        "bron": "ilt", "soort": "conclusie", "thema": "digitaal", "blokje": "handelingen/bewaren",
        "kop": "Onleesbare pdf's en incomplete dossiers",
        "wat": "Een van de genoemde oorzaken is heel letterlijk: het archief zelf. Onleesbare "
               "bestanden en onvolledige dossiers maken dat niemand kan vaststellen wat geldt.",
        "citaat": "Gebrekkige archieven, databases en overzichten (zoals onleesbare pdf-bestanden "
                  "en incomplete vergunningendossiers)",
        "pagina": 6,
        "adressant": "omgevingsdiensten",
    },
    {
        "id": "ilt-verdringing",
        "bron": "ilt", "soort": "conclusie", "thema": "zicht", "blokje": "processen/aanvragen",
        "kop": "Nieuwe aanvragen verdringen het bijwerken van oude",
        "wat": "Een aanvraag heeft een termijn, een actualisatie niet. Dus wint de aanvraag, elke "
               "keer.",
        "citaat": "Nieuwe aanvragen verdringen de actualisatie van bestaande vergunningen.",
        "pagina": 6,
        "adressant": "omgevingsdiensten",
    },
    {
        "id": "ilt-hardnekkig",
        "bron": "ilt", "soort": "conclusie", "thema": "leren", "blokje": "processen/verantwoorden",
        "kop": "Het probleem is al lang bekend en blijft hardnekkig",
        "wat": "Diverse initiatieven zijn genomen sinds de commissie Van Aartsen in 2021. Het "
               "probleem is er nog.",
        "citaat": "blijken de problemen met actualisatie hardnekkig",
        "pagina": 6,
        "adressant": "ministerie van IenW",
    },
    # -- ILT: de aanbevelingen die over gegevens gaan -------------------------------------------
    {
        "id": "ilt-ab2",
        "bron": "ilt", "soort": "aanbeveling", "thema": "digitaal", "blokje": "handelingen/bewaren",
        "kop": "Maak archieven digitaal beschikbaar",
        "wat": "De meest basale aanbeveling van de elf, en daarmee de scherpste: het begint bij "
               "een leesbaar dossier.",
        "citaat": "Maak archieven beter (digitaal) beschikbaar.",
        "pagina": 6,
        "adressant": "gemeenten en provincies",
    },
    {
        "id": "ilt-ab4",
        "bron": "ilt", "soort": "aanbeveling", "thema": "digitaal", "blokje": "handelingen/innemen",
        "kop": "Verbeter de informatievoorziening voor actualisaties",
        "wat": "Om te kunnen bijwerken moet je eerst weten wat er is, voor welk bedrijf, onder "
               "welke regels.",
        "citaat": "Verbeter de informatievoorziening die nodig is voor actualisaties.",
        "pagina": 6,
        "adressant": "omgevingsdiensten en Omgevingsdienst NL",
    },
    {
        "id": "ilt-ab7",
        "bron": "ilt", "soort": "aanbeveling", "thema": "zicht", "blokje": "handelingen/delen",
        "kop": "Maak de actualiteit van vergunningen transparant",
        "wat": "Niet alleen intern weten, maar laten zien. Dat is wat een register zou kunnen "
               "doen en vandaag niet doet.",
        "citaat": "Verbeter de transparantie over de actualiteit van vergunningen.",
        "pagina": 6,
        "adressant": "omgevingsdiensten en Omgevingsdienst NL",
    },
    {
        "id": "ilt-ab11",
        "bron": "ilt", "soort": "aanbeveling", "thema": "zicht", "blokje": "handelingen/verantwoorden",
        "kop": "Zet de actualisatiegraad in de Staat van VTH",
        "wat": "Een getal in een jaarlijkse rapportage maakt het verschil tussen een bekend "
               "probleem en een gevolgd probleem.",
        "citaat": "Neem in de Staat van VTH ook kwantitatieve informatie op over de "
                  "actualisatiegraad van vergunningen.",
        "pagina": 7,
        "adressant": "ministerie van IenW",
    },
    # -- Evaluatiecommissie: de zorgpunten -----------------------------------------------------
    {
        "id": "ec-samenhang",
        "bron": "ec", "soort": "conclusie", "thema": "samenhang", "blokje": "processen/aanvragen",
        "kop": "De druk op de samenhang is groter geworden",
        "wat": "Samenhang was vijftien jaar geleden de aanleiding voor de hele stelselherziening. "
               "De commissie is er niet gerust op dat die van de grond komt.",
        "citaat": "de druk op de beoogde samenhangende benadering van de leefomgeving alleen maar "
                  "groter is geworden",
        "pagina": 29,
        "adressant": "overheden",
    },
    {
        "id": "ec-confetti",
        "bron": "ec", "soort": "conclusie", "thema": "samenhang", "blokje": "aansluitingen/zaak",
        "kop": "Het confettikanon",
        "wat": "Bevoegde gezagen gebruiken dit woord zelf: één initiatief komt binnen als een "
               "regen van losse aanvragen, en niemand houdt het totaalbeeld.",
        "citaat": "Hieraan ten grondslag ligt het zogeheten confettikanon",
        "pagina": 29,
        "adressant": "overheden",
    },
    {
        "id": "ec-ab1",
        "bron": "ec", "soort": "aanbeveling", "thema": "samenhang", "blokje": "processen/besluiten",
        "kop": "Ontwikkel werkwijzen voor losse aanvragen op één locatie",
        "wat": "De wet wordt niet teruggedraaid, dus moet de praktijk een manier vinden om het "
               "totaalbeeld terug te krijgen.",
        "citaat": "Voorkom afbreuk aan de samenhangende benadering van de leefomgeving door "
                  "ontwikkeling nieuwe werkwijzen voor omgang met losse vergunningaanvragen",
        "pagina": 29,
        "adressant": "overheden",
    },
    {
        "id": "ec-ab2",
        "bron": "ec", "soort": "aanbeveling", "thema": "samenhang", "blokje": "processen/verantwoorden",
        "kop": "Houd nieuwe sectorale wetten binnen de systematiek",
        "wat": "Defensiegereedheid, een nieuwe Crisis- en herstelwet, noodwetgeving drinkwater: "
               "elk haalt een belang buiten de integrale afweging.",
        "citaat": "Neem nieuwe (sectorale) wetsinitiatieven voor de leefomgeving op binnen de "
                  "systematiek van de Omgevingswet",
        "pagina": 30,
        "adressant": "minister van VRO",
    },
    {
        "id": "ec-ab3",
        "bron": "ec", "soort": "aanbeveling", "thema": "verschillen", "blokje": "processen/besluiten",
        "kop": "Waarborg de transitie van omgevingsplannen voor 2032",
        "wat": "Zolang het omgevingsplan niet staat, blijft de BOPA het instrument van voorkeur "
               "en blijft het beeld onoverzichtelijk.",
        "citaat": "Waarborg een tijdige transitie van omgevingsplannen voor 2032",
        "pagina": 31,
        "adressant": "gemeenten, VNG, minister van VRO",
    },
    {
        "id": "ec-ab5",
        "bron": "ec", "soort": "aanbeveling", "thema": "verschillen", "blokje": "processen/oriënteren",
        "kop": "Verken de afwegingsruimte die er is",
        "wat": "Decentrale overheden gebruiken hun ruimte nauwelijks. De commissie weet nog niet "
               "waarom, en wil dat in 2028 uitzoeken.",
        "citaat": "Verken de mogelijkheden van bestuurlijke afwegingsruimte en maatwerk",
        "pagina": 31,
        "adressant": "provincies, gemeenten en waterschappen",
    },
    {
        "id": "ec-bopa",
        "bron": "ec", "soort": "conclusie", "thema": "digitaal", "blokje": "handelingen/plaatsen",
        "kop": "De viewer toont dat er een BOPA is, niet wat erin staat",
        "wat": "Regels op de kaart geeft de aanvraag of verlening weer, maar niet de inhoud. Dus "
               "staat het afwijkende regime nergens leesbaar.",
        "citaat": "wel de aanvraag of gunning van een BOPA weergeeft in het DSO, maar niet de "
                  "inhoud ervan",
        "pagina": 30,
        "adressant": "minister van VRO",
    },
    {
        "id": "ec-workaround",
        "bron": "ec", "soort": "conclusie", "thema": "digitaal", "blokje": "bodem/koppelvlakken",
        "kop": "Bevoegde gezagen werken om het DSO heen",
        "wat": "Eigen formulieren, begeleiding aan de balie. Dienstbaar, maar het betekent dat de "
               "aanvraag buiten het stelsel om gaat.",
        "citaat": "bevoegde gezagen als gevolg van de knelpunten in het DSO er soms voor kiezen "
                  "om buiten het DSO om te werken",
        "pagina": 33,
        "adressant": "minister van VRO",
    },
    {
        "id": "ec-ab7",
        "bron": "ec", "soort": "aanbeveling", "thema": "digitaal", "blokje": "bodem/basis",
        "kop": "Vergroot de inzet op verbetering van het DSO",
        "wat": "Een werkend DSO is volgens de commissie een noodzakelijke basisvoorwaarde voor "
               "alle vier de verbeterdoelen van de wet.",
        "citaat": "Vergroot de inzet op verbetering DSO",
        "pagina": 32,
        "adressant": "minister van VRO",
    },
    {
        "id": "ec-ab8",
        "bron": "ec", "soort": "aanbeveling", "thema": "leren", "blokje": "handelingen/uitleggen",
        "kop": "Blijf inzetten op leren werken onder de wet",
        "wat": "Het ondersteuningsprogramma eindigde halverwege 2025. De verschillen tussen "
               "partijen zijn groot en leernetwerken blijken onmisbaar.",
        "citaat": "Blijf volop inzetten op ondersteuning van leren werken onder de Omgevingswet",
        "pagina": 33,
        "adressant": "minister van VRO, koepels, brancheorganisaties",
    },
    # -- Kabinetsreactie -----------------------------------------------------------------------
    {
        "id": "kab-inherent",
        "bron": "kabinet", "soort": "reactie", "thema": "samenhang", "blokje": "processen/aanvragen",
        "kop": "Versnippering is een inherent gevolg van de gekozen flexibiliteit",
        "wat": "Het kabinet onderschrijft de aanbeveling, maar noemt de oorzaak een gevolg van "
               "een bewuste keuze. De versnippering wordt gemitigeerd, niet weggenomen.",
        "citaat": "Die flexibiliteit heeft als inherent gevolg dat er versnippering optreedt",
        "pagina": 4,
        "adressant": "Tweede Kamer",
    },
    {
        "id": "kab-complex",
        "bron": "kabinet", "soort": "reactie", "thema": "samenhang", "blokje": "gebied/bedrijf",
        "kop": "Voor het complexe bedrijf geldt de versnippering niet",
        "wat": "Bij de zwaarste bedrijven blijft de vergunning voor het hele bedrijf gelden. Daar "
               "is het centrale instrument dus intact -- precies de categorie waar de ILT de "
               "grootste achterstand meet.",
        "citaat": "daar blijft de vergunning voor het hele bedrijf van kracht",
        "pagina": 14,
        "adressant": "Tweede Kamer",
    },
    {
        "id": "kab-dso",
        "bron": "kabinet", "soort": "reactie", "thema": "digitaal", "blokje": "handelingen/plaatsen",
        "kop": "Aandacht voor de inzichtelijkheid van BOPA's in Regels op de Kaart",
        "wat": "De minister zegt dit met de medeopdrachtgevers te bespreken. Een toezegging om "
               "te agenderen, geen toezegging om te bouwen.",
        "citaat": "specifiek aandacht zal vragen voor de inzichtelijkheid van BOPA-vergunningen "
                  "en vrijwillige programma's in Regels op de Kaart",
        "pagina": 12,
        "adressant": "Tweede Kamer",
    },
    {
        "id": "kab-ondersteuning",
        "bron": "kabinet", "soort": "reactie", "thema": "leren", "blokje": "handelingen/uitleggen",
        "kop": "Minimaal vijf jaar ondersteuning, via coaches in de regio",
        "wat": "Het meest concrete van de kabinetsreactie: ondersteuning blijft, met regionale "
               "implementatiecoaches als eerste aanspreekpunt.",
        "citaat": "bevoegde gezagen minimaal 5 jaar na inwerkingtreding blijf ondersteunen bij de "
                  "uitvoering van de Omgevingswet",
        "pagina": 12,
        "adressant": "Tweede Kamer",
    },
    {
        "id": "kab-iplo",
        "bron": "kabinet", "soort": "reactie", "thema": "leren", "blokje": "handelingen/uitleggen",
        "kop": "Het IPLO krijgt een sleutelrol",
        "wat": "Het kenniscentrum voor de fysieke leefomgeving is de plek waar de uitleg "
               "landt -- en dezelfde bron waarop de RAG van dit lab is gebouwd.",
        "citaat": "Het Informatiepunt Leefomgeving (IPLO) vervult een sleutelrol in de "
                  "ondersteuning van bevoegde gezagen",
        "pagina": 12,
        "adressant": "Tweede Kamer",
    },
]

#: De verbanden tussen bevindingen: waar twee bronnen over hetzelfde gaan. **Dit is de reden dat
#: de vier rapporten in één dossier staan** -- zonder deze knopen is het vier samenvattingen.
#: `relatie` zegt wát de ene uitspraak met de andere doet.
RELATIES = ("bevestigt", "verdiept", "verklaart", "beantwoordt", "nuanceert", "blijft_open")

VERBANDEN = [
    {
        "van": "rli-overzicht", "naar": "ec-confetti", "relatie": "bevestigt",
        "wat": "Het Rli ziet bij de toezichthouder wat de Evaluatiecommissie bij het bevoegd "
               "gezag ziet: één initiatief, losse stukken, geen totaalbeeld. Twee adviesorganen, "
               "onafhankelijk van elkaar, hetzelfde verschijnsel.",
    },
    {
        "van": "kab-inherent", "naar": "ec-confetti", "relatie": "nuanceert",
        "wat": "Het kabinet bestrijdt de constatering niet maar noemt haar het gevolg van een "
               "gewilde keuze. Daarmee verschuift de vraag van 'hoe lossen we dit op' naar 'hoe "
               "gaan we ermee leven'.",
    },
    {
        "van": "kab-complex", "naar": "ilt-seveso", "relatie": "blijft_open",
        "wat": "De scherpste spanning in dit dossier. Het kabinet zegt dat bij complexe bedrijven "
               "de vergunning intact blijft -- en juist daar meet de ILT dat geen enkele dienst "
               "de afspraak haalt. Het instrument staat er; het is niet bij.",
    },
    {
        "van": "ilt-archief", "naar": "ilt-zicht", "relatie": "verklaart",
        "wat": "Waarom weet een dienst niet of zijn vergunningen actueel zijn? Omdat het dossier "
               "een onleesbare pdf is. Het zicht ontbreekt niet uit onwil maar uit opslagvorm.",
    },
    {
        "van": "ilt-zicht", "naar": "ilt-buitenbeeld", "relatie": "verklaart",
        "wat": "Geen zicht op de vergunning betekent geen grond voor toezicht. De keten van "
               "archief naar handhaving loopt via één gegeven dat niemand heeft.",
    },
    {
        "van": "rli-ko2", "naar": "rli-houvast", "relatie": "verklaart",
        "wat": "Het signaal (minder houvast) en de oorzaak (niemand heeft doordacht wat 'in de "
               "geest van de wet' voor een handhaver betekent) horen bij elkaar.",
    },
    {
        "van": "rli-achteraf", "naar": "ilt-emissies", "relatie": "verdiept",
        "wat": "Het Rli beschrijft achteraf bijsturen als mechanisme; de ILT laat zien wat het "
               "in de tussentijd kost: een ruimere norm blijft gelden zolang niemand hem "
               "bijwerkt.",
    },
    {
        "van": "ec-workaround", "naar": "ec-ab7", "relatie": "verklaart",
        "wat": "De commissie leidt haar aanbeveling niet af uit een oordeel over het DSO -- dat "
               "valt buiten haar opdracht -- maar uit het gedrag dat zij eromheen ziet ontstaan.",
    },
    {
        "van": "kab-dso", "naar": "ec-bopa", "relatie": "beantwoordt",
        "wat": "De commissie noemt het ontbreken van de BOPA-inhoud in de viewer; het kabinet "
               "zegt het te agenderen bij de medeopdrachtgevers. Agenderen is nog geen bouwen.",
    },
    {
        "van": "kab-ondersteuning", "naar": "ec-ab8", "relatie": "beantwoordt",
        "wat": "Hier is de reactie wél concreet: minimaal vijf jaar, met regionale coaches. Van "
               "de acht aanbevelingen is dit de enige met een termijn eraan.",
    },
    {
        "van": "rli-ab3", "naar": "ilt-hardnekkig", "relatie": "verklaart",
        "wat": "De ILT constateert dat het probleem hardnekkig is ondanks initiatieven; het Rli "
               "wijst aan waar het blijft hangen -- de praktijkkennis bereikt de beleidscyclus "
               "niet.",
    },
    {
        "van": "ilt-meten", "naar": "rli-oranje", "relatie": "verdiept",
        "wat": "De seinen staan op oranje, maar er is geen meetreeks om te zien of ze rood "
               "worden. De waarschuwing en het ontbreken van de meting horen bij elkaar.",
    },
]

#: Wat dit lab zelf op echte data heeft gezien bij een thema, met de pagina waar het staat.
#: **Dit is een lezing van dit lab, geen bevinding uit een rapport** -- en staat dus apart van
#: `BEVINDINGEN`, met een eigen herkomstregel. Elke `waar` moet een bestaande route zijn; een
#: test dwingt dat af.
LABLIJN = [
    {
        "thema": "zicht",
        "wat": "In het enige publieke vergunningenregister dat dit lab live kan bevragen -- de "
               "Atlas voor een Schone Maas -- draagt geen enkel voorschrift een "
               "geldigheidsperiode. De vraag 'is deze vergunning actueel' is er niet te stellen, "
               "laat staan te beantwoorden.",
        "waar": "/toezicht",
        "hoe": "Tien deterministische signaalregels over 69 vergunde vestigingen; de regel over "
               "de geldigheidsduur vuurt registerbreed.",
    },
    {
        "thema": "zicht",
        "wat": "Hetzelfde register levert 69 regels op 61 verschillende locatiecodes. De "
               "locatiecode is dus geen sleutel, en acht vergunningen waren daardoor "
               "onbereikbaar tot de identiteit werd uitgebreid.",
        "waar": "/toezicht",
        "hoe": "Gevonden door de draaiende dienst te bevragen, niet door de code te lezen.",
    },
    {
        "thema": "samenhang",
        "wat": "Van twaalf begrippen die het REV en het GIR delen, zijn er drie waarop je kunt "
               "joinen -- en alle drie leunen op een basisregistratie buiten beide registers. "
               "Niets wat de twee registers zelf afspraken verbindt ze.",
        "waar": "/modellen",
        "hoe": "Afgeleid uit de vier gepubliceerde IMEV-bestanden en het GIR-informatiemodel.",
    },
    {
        "thema": "houvast",
        "wat": "De Aquo-code voor 'zwevende stof' is vervallen, terwijl dat met 83 voorschriften "
               "de meest voorkomende parameter in het hele register is. De domeintabel biedt geen "
               "opvolger. Een norm zonder geldige code is niet machinaal te toetsen.",
        "waar": "/kennisgraaf",
        "hoe": "Aquo-domeintabel Parameter, 5630 geldige en 1479 vervallen codes.",
    },
    {
        "thema": "achteraf",
        "wat": "Het vergunde deel verklaart 0 tot 14% van wat er in de rivier gemeten wordt -- op "
               "de meeste meetpunten niets. Wie alleen naar vergunningen kijkt, kijkt naar een "
               "zevende van het probleem.",
        "waar": "/kmg",
        "hoe": "Vergunde vrachten uit de Atlas tegen gemeten waarden uit het "
               "Waterkwaliteitsportaal, met de stroomvolgorde als labkeuze.",
    },
    {
        "thema": "digitaal",
        "wat": "Een gepubliceerd IMEV-schema bevat op regel 449 een tab en is daardoor geen "
               "geldige YAML -- PyYAML weigert het hele bestand. Een koppelvlak dat niet parseert "
               "is geen koppelvlak.",
        "waar": "/modellen",
        "hoe": "Alle vier de bestanden live opgehaald en nagerekend.",
    },
    {
        "thema": "digitaal",
        "wat": "PDOK negeert een cql_filter op de BAG volledig: een ruimtelijke vraag levert "
               "stilzwijgend de hele dataset terug. Geen foutmelding, wel een verkeerd antwoord.",
        "waar": "/evruimte",
        "hoe": "Live vergelijking van cql_filter tegen een FES-filter via POST.",
    },
    {
        "thema": "verschillen",
        "wat": "Drie locaties aan hetzelfde KRW-waterlichaam, in twee provincies: de regels op "
               "het punt verschillen per locatie, de gebruiksruimte is gedeeld. De "
               "waterschapsverordening geldt er wel maar raakt het voornemen niet.",
        "waar": "/gebruiksruimte",
        "hoe": "Regels live uit het DSO (Ozon), ongeveer twintig per punt, geclassificeerd naar "
               "werking.",
    },
    {
        "thema": "leren",
        "wat": "Van zestien informatiebehoeften in twee ketens zijn er twee voldaan, zes deels "
               "en acht niet. Waardestroom W5 is het zwartste gat met vijf onvervulde behoeften.",
        "waar": "/balo",
        "hoe": "De redeneerlijnen van de BALO-businessarchitectuur toegepast op de twee "
               "doelbeeldcasussen van dit lab.",
    },
]

#: Wat uit de bronnen komt en wat dit lab erbij leest -- dezelfde scheiding als op `/maquette`
#: en `/balo`.
HERKOMST = [
    {
        "van": "bron",
        "wat": "De bevindingen, kernoorzaken, conclusies en aanbevelingen",
        "bron": "Letterlijk uit de vier documenten, elk met een citaat en een pagina die een test "
                "tegen de tekstextractie natrekt.",
    },
    {
        "van": "bron",
        "wat": "De adressant per aanbeveling",
        "bron": "Zoals de documenten hem zelf noemen -- het Rli in de aanbeveling, de ILT in de "
                "kopjes boven haar elf aanbevelingen, de Evaluatiecommissie in haar tabel 1.",
    },
    {
        "van": "lab",
        "wat": "De indeling in zeven thema's",
        "bron": "Een keuze van dit lab. De vier rapporten gebruiken elk een eigen indeling; deze "
                "zeven zijn gekozen omdat de bronnen elkaar daar raken. Geen enkel document kent "
                "deze thema's.",
    },
    {
        "van": "lab",
        "wat": "De verbanden tussen bevindingen uit verschillende bronnen",
        "bron": "Een lezing van dit lab. De bronnen verwijzen deels naar elkaar -- het Rli noemt "
                "de Evaluatiecommissie, het kabinet reageert op haar -- maar de specifieke knopen "
                "hier zijn niet in een document gelegd.",
    },
    {
        "van": "lab",
        "wat": "De aanknoping van een bevinding aan een blokje van de maquette",
        "bron": "Volledig van dit lab. De maquette is een eigen verbeelding van het eindbeeld uit "
                "de BALO-businessarchitectuur; geen van de vier rapporten kent haar.",
    },
    {
        "van": "lab",
        "wat": "De lablijn: wat hier op echte data gemeten is",
        "bron": "Metingen van dit lab op publieke bronnen, elk met een eigen pagina waar de "
                "afleiding staat. Zij bevestigen geen rapport en worden door geen rapport "
                "bevestigd -- zij staan ernaast.",
    },
]


def blokjes() -> list[dict]:
    """De tegels van de maquette: de dingen in het gebied, de handelingen, de aansluitingen en de
    bodem.

    **Niet `_alle_elementen()`**, en dat is het verschil tussen een zinnige en een misleidende
    telling. Die functie draagt ook de stromen, de kanten en de routes mee -- richtingen en paden,
    geen plekken. Zou `onbesproken()` daarop rekenen, dan stonden er twintig "onbesproken blokjes"
    waarvan de helft nooit een bevinding kon dragen, en leek de dekking van dit dossier de helft
    van wat zij is."""
    return list(_op_sleutel().values())


#: De vijf lijsten waaruit de tegels komen, in de volgorde waarin de maquette ze stapelt. De
#: laag is geen veld op de tegel maar volgt uit de lijst waarin zij staat -- daarom staat de
#: toewijzing hier en niet in `eindbeeld_stelsel`.
LAGEN_VAN_BLOKJES = ("gebied", "processen", "handelingen", "aansluitingen", "bodem")


def _op_sleutel() -> dict:
    """De blokjes op `laag/id`.

    **Waarom niet op `id` alleen -- en dit viel pas op bij het tellen.** `verantwoorden` bestaat
    twee keer in de maquette: als proces ("Beleid kijkt of het werkt") en als handeling ("Laten
    zien hoe het gaat"). Een opzoeking op id liet er stil één van wegvallen, zodat vier
    bevindingen bij het verkeerde blokje hingen en de dekking één tegel te laag uitkwam. De
    sleutel is daarom de laag erbij, en een botsing *binnen* een laag valt luid om."""
    uit = {}
    for laag, lijst in zip(LAGEN_VAN_BLOKJES, (
            eindbeeld_mod.GEBIED, eindbeeld_mod.PROCESSEN, eindbeeld_mod.HANDELINGEN,
            eindbeeld_mod.AANSLUITINGEN, eindbeeld_mod.BODEM)):
        for e in lijst:
            sleutel = f"{laag}/{e['id']}"
            if sleutel in uit:
                raise ValueError(f"twee blokjes met dezelfde sleutel {sleutel}")
            uit[sleutel] = {**e, "laag": laag, "sleutel": sleutel}
    return uit


def bevindingen() -> list[dict]:
    """De bevindingen, elk verrijkt met haar thema, haar blokje en de doorkijk naar dit lab."""
    op_sleutel = _op_sleutel()
    uit = []
    for b in BEVINDINGEN:
        blok = op_sleutel[b["blokje"]]
        uit.append({
            **b,
            "thema_naam": OP_THEMA[b["thema"]]["naam"],
            "kleur": OP_THEMA[b["thema"]]["kleur"],
            "blokje_naam": blok.get("naam") or blok.get("object"),
            "blokje_laag": blok["laag"],
            "waar": blok["waar"],
        })
    return uit


def per_thema() -> list[dict]:
    """De thema's met hun bevindingen, hun bronnen en de lablijn eronder.

    Dit is de vorm waarin de pagina het dossier leest: een thema is een blokje met bevindingen
    uit meerdere bronnen eraan."""
    alle = bevindingen()
    uit = []
    for t in THEMAS:
        mijn = [b for b in alle if b["thema"] == t["id"]]
        uit.append({
            **t,
            "bevindingen": mijn,
            "bronnen": sorted({b["bron"] for b in mijn}),
            "lablijn": [l for l in LABLIJN if l["thema"] == t["id"]],
        })
    return uit


def verbanden() -> list[dict]:
    """De verbanden met de koppen van beide kanten erbij, zodat de pagina ze kan tonen zonder
    zelf te hoeven opzoeken wat `rli-ko2` is."""
    op_id = {b["id"]: b for b in BEVINDINGEN}
    return [{
        **v,
        "van_kop": op_id[v["van"]]["kop"],
        "van_bron": op_id[v["van"]]["bron"],
        "naar_kop": op_id[v["naar"]]["kop"],
        "naar_bron": op_id[v["naar"]]["bron"],
        "over_bronnen": op_id[v["van"]]["bron"] != op_id[v["naar"]]["bron"],
    } for v in VERBANDEN]


def onbesproken() -> list[dict]:
    """De blokjes van de maquette waar dit dossier niets over zegt.

    **Dit hoort op de pagina en niet in een logregel.** Een plaat waarin elk blokje een bevinding
    draagt suggereert dat de rapporten het hele landschap dekken. Dat doen ze niet: vier
    rapporten over VTH zeggen niets over, bijvoorbeeld, de sleutel of de fundering. Dat gat is
    zelf een bevinding over de kennisbasis -- hier is nog geen bron voor."""
    besproken = {b["blokje"] for b in BEVINDINGEN}
    return [{"id": e["sleutel"], "naam": e.get("naam") or e.get("object"), "laag": e["laag"],
             "waar": e["waar"]}
            for e in blokjes() if e["sleutel"] not in besproken]


def telling() -> dict:
    """Alles geteld uit de lijsten, nooit getypt -- zie `/maquette` en `/balo` voor dezelfde
    regel."""
    alle = bevindingen()
    per_bron = {}
    per_soort = {}
    for b in alle:
        per_bron[b["bron"]] = per_bron.get(b["bron"], 0) + 1
        per_soort[b["soort"]] = per_soort.get(b["soort"], 0) + 1
    vb = verbanden()
    return {
        "bevindingen": len(alle),
        "themas": len(THEMAS),
        "verbanden": len(vb),
        "verbanden_over_bronnen": sum(1 for v in vb if v["over_bronnen"]),
        "per_bron": per_bron,
        "per_soort": per_soort,
        "blokjes": len(blokjes()),
        "blokjes_met_bevinding": len({b["blokje"] for b in BEVINDINGEN}),
        "blokjes_onbesproken": len(onbesproken()),
        "lablijnen": len(LABLIJN),
    }
