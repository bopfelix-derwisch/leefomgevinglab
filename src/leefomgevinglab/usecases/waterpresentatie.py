"""Het waterdossier in een kwartier: de presentatie als data, niet als dia's.

Waarom dit een module is en geen stapel HTML. Een presentatie veroudert sneller dan de POC
eronder: iemand past een getal aan op `/kmg` en de dia blijft het oude getal vertellen, met een
publiek erbij. Door de inhoud hier vast te leggen kan `tests/test_waterpresentatie.py` de
kerncijfers tégen de voorberekende momentopname houden — dezelfde die de pagina's gebruiken.
Loopt er iets uit de pas, dan valt de test om in plaats van de spreker.

De timing is onderdeel van de inhoud. `DUUR_S` staat vast en een test bewaakt dat de dia's
er samen precies op uitkomen: de duur in de titel is geen schatting maar een afspraak, want
de dia's lopen vanzelf door. Hij stond eerst op 600 seconden; met het hoofdstuk over de POC
zelf erbij zou dat 180 woorden per minuut vergen, en dat is geen presenteren meer maar
haasten. Liever de duur aanpassen dan de inhoud uitkleden of de spreker opjagen.

Elke dia draagt haar eigen bron en een `link` naar de labpagina die haar bewijst. Een bewering
zonder vindplaats hoort niet in een demo thuis — na afloop wil iemand kunnen doorklikken.

De cijfers van het eindbeeld worden hier niet overgetypt maar uit `eindbeeld.py` gehaald. Dat is
dezelfde regel als elders in dit lab: wat je typt veroudert, wat je afleidt valt om. Verandert
daar een aanname, dan verandert de dia mee in plaats van stil te gaan liegen.
"""
from . import eindbeeld as _eb

_EB = _eb.product()


def _nl(getal: float) -> str:
    """Een getal met een punt als duizendtalscheiding.

    Dit staat hier als functie en niet als `.replace(",", ".")` op een hele zin, want zo ging het
    al twee keer mis: die vervanging raakt ook de zinskomma, en dan staat er "van de Zandmaas.
    één stof" op een dia.
    """
    return f"{getal:,.0f}".replace(",", ".")

DUUR_S = 900

# De kerncijfers, op één plek. Ze staan hier als letterlijke waarden en niet als berekening uit de
# momentopname: de pagina moet ook werken als dat bestand er niet is, en een presentatie hoort niet
# halverwege een zin stil te vallen. De test houdt ze tegen de momentopname aan.
CIJFERS = {
    "voorschriften_totaal": 7038,
    "voorschriften_bruikbaar": 5967,
    "voorschriften_bruikbaar_pct": 84.8,
    "voorschriften_volledig": 0,
    "voorschriften_zonder_geldigheid": 7038,
    "meetpunten": 9,
    "aandeel_max_pct": 28.5,
    "aandeel_nul": 6,
    "aandeel_gevallen": 22,
    "register_maas": 69,
    "rwzi_in_register": 7,
    "rwzi_voorschriften": 30,
    "rwzi_grootheden": 5,
    "kvk_gevuld": 69,
    # De afbakening sinds 29 oktober 2026: het stroomgebieddistrict in plaats van een cirkel van
    # 50 km. Van de 163 Maas-waterlichamen plaatst dit lab er tien in een volgorde; vier blijven
    # uitdrukkelijk ongeplaatst.
    "waterlichamen_maas": 163,
    "waterlichamen_geplaatst": 10,
    "waterlichamen_zonder_positie": 4,
}


def _dia(nr, deel, titel, kern, beeld, spreektekst, bron, link, seconden):
    return {"nr": nr, "deel": deel, "titel": titel, "kern": kern, "beeld": beeld,
            "spreektekst": spreektekst, "bron": bron, "link": link, "seconden": seconden}


DIAS = [
    _dia(
        1, "De vraag", "Een meting is hoger dan het doel. En dan?",
        ["De vraag is niet „wie is de dader”",
         "maar: welke vergunde lozingen bovenstrooms kunnen hieraan bijdragen,",
         "en hoeveel ruimte is er nog tot het doel?"],
        {"soort": "drieluik", "kolommen": [
            {"kop": "Kan", "groot": "de regels", "bij": "wat hier geldt", "kleur": "kan"},
            {"kop": "Mag", "groot": "de vergunningen", "bij": "wat hier is toegestaan", "kleur": "mag"},
            {"kop": "Gebeurt", "groot": "de metingen", "bij": "wat er werkelijk in zit", "kleur": "gebeurt"},
        ]},
        "Het waterdossier van het LeefomgevingLab begint bij één vraag. Een meting op de "
        "Maas ligt boven het doel. Een waterbeheerder wil dan niet weten wie de dader is — dat "
        "is een handhavingsvraag, en meestal onbeantwoordbaar. Hij wil weten: welke vergunde "
        "lozingen bovenstrooms kúnnen hieraan bijdragen, en hoeveel ruimte is er nog tot het "
        "doel? Die ene vraag raakt drie werelden met elk hun eigen bron en eigen beheerder. We "
        "lopen ze langs, aan de Maas, met echte data.",
        "LeefomgevingLab, waterdossier", "/waterverhaal", 30),

    _dia(
        2, "Juridisch", "Waar de norm vandaan komt — en waar niet",
        ["De Kaderrichtlijn Water kent 122 chemische stoffen:",
         "45 prioritaire stoffen (Europees) en 77 specifieke verontreinigende stoffen (nationaal)",
         "Die staan in bijlage III en IIIa van het Besluit kwaliteit leefomgeving",
         "Ze hangen aan een wáterlichaam via het waterprogramma — niet aan een punt in een omgevingsplan"],
        {"soort": "stappen", "stappen": [
            {"nr": "EU", "naam": "Kaderrichtlijn Water", "sub": "doelen per waterlichaam", "actief": False},
            {"nr": "NL", "naam": "Bkl bijlage III / IIIa", "sub": "45 prioritair + 77 SVS", "actief": True},
            {"nr": "↓", "naam": "Waterprogramma", "sub": "norm wordt aan een waterlichaam gehangen", "actief": False},
            {"nr": "?", "naam": "Omgevingsplan", "sub": "zegt niets over waterkwaliteit", "actief": False},
        ]},
        "Eerst het juridische fundament, want daar zit meteen de eerste verrassing. De normen voor "
        "waterkwaliteit zijn landelijk. De Kaderrichtlijn Water onderscheidt honderdtweeëntwintig "
        "chemische stoffen: vijfenveertig prioritaire en zevenenzeventig die Nederland zelf heeft "
        "aangewezen. Die staan in bijlage drie en drie-a van het Besluit kwaliteit leefomgeving. "
        "En ze hangen aan een waterlichaam, via het waterprogramma — niet aan een punt op de "
        "kaart. Dat betekent iets praktisch: je kunt de norm principieel niet vinden door op een "
        "coördinaat te bevragen. Hoe goed je het ook doet.",
        "Bkl bijlage III en IIIa; STOWA 2025-46 voetnoot 16", "/waterverhaal", 30),

    _dia(
        3, "Juridisch", "Wie gaat waarover — en de route die niemand ziet",
        ["Direct op het water: de waterbeheerder is bevoegd gezag",
         "Op het riool: de gemeente, via de omgevingsdienst",
         "Het waterschap beheert dan de zuivering, maar heeft géén bevoegd gezag",
         "en zijn advies is sinds 2024 niet meer bindend"],
        {"soort": "stappen", "stappen": [
            {"nr": "1", "naam": "Directe lozing", "sub": "bedrijf → oppervlaktewater · waterbeheerder beslist", "actief": True},
            {"nr": "2", "naam": "Indirecte lozing", "sub": "bedrijf → riool · gemeente beslist", "actief": False},
            {"nr": "3", "naam": "Zuivering", "sub": "RWZI → oppervlaktewater · waterbeheerder weer", "actief": False},
        ]},
        "Tweede stuk fundament: wie gaat waarover. Loost een bedrijf rechtstreeks op de rivier, "
        "dan is de waterbeheerder bevoegd gezag. Maar loost datzelfde bedrijf op het riool, dan is "
        "de gemeente dat, uitgevoerd door de omgevingsdienst. Het waterschap beheert dan wel de "
        "zuivering en ontvangt het water, maar heeft er geen bevoegd gezag over, geen "
        "handhavingsbevoegdheid, en zijn advies is sinds tweeduizendvierentwintig niet eens meer "
        "bindend. Onthoud die tweede route — halverwege blijkt zij een gat in het hele beeld.",
        "STOWA 2025-46, tabel 2; art. 4.34 en 4.35 Omgevingsbesluit", "/kmg", 30),

    _dia(
        4, "De aanpak", "Drie lagen over elkaar, plus een vierde",
        ["Kan — de regels op de locatie, live uit het DSO",
         "Mag — de vergunningen, live uit de Atlas voor een Schone Maas",
         "Gebeurt — de metingen uit het Waterkwaliteitsportaal",
         "Gemeld — wat een bedrijf zelf rapporteert (E-PRTR)"],
        {"soort": "lagen", "lagen": [
            {"naam": "Kan", "sub": "regels · DSO Ozon · live", "kleur": "kan"},
            {"naam": "Mag", "sub": "vergunningen · Atlas voor een Schone Maas · live", "kleur": "mag"},
            {"naam": "Gebeurt", "sub": "metingen · Waterkwaliteitsportaal · momentopname", "kleur": "gebeurt"},
            {"naam": "Gemeld", "sub": "E-PRTR · RIVM · live", "kleur": "gemeld"},
        ]},
        "De aanpak komt uit een voorlichtingsfolder van het Digitaal Stelsel Omgevingswet: leg kan, "
        "mag en gebeurt over elkaar heen. Kan zijn de regels die op deze plek gelden. Mag zijn de "
        "vergunningen die er al liggen. Gebeurt is wat er werkelijk gemeten wordt. Wij hebben er een "
        "vierde laag bij gezet: gemeld — wat een bedrijf zelf jaarlijks rapporteert te hebben "
        "geloosd. Vier lagen, vier bronnen, vier beheerders. We halen ze nu één voor "
        "één op, echt, aan de Maas.",
        "DSO-folder kan · mag · gebeurt", "/kmg", 30),

    _dia(
        5, "Kan", "De regels: het DSO antwoordt, maar niet over water",
        ["20 regelingen op de coördinaat van het meetpunt, live opgehaald",
         "8 daarvan raken de waterkwaliteit",
         "De rest: Omgevingsprogramma Retail, Warmteprogramma, actieplan geluid",
         "De norm zit er principieel niet bij"],
        {"soort": "balken", "balken": [
            {"label": "regelingen op het punt", "waarde": 20, "max": 20, "kleur": "kan", "bij": "live uit DSO Ozon"},
            {"label": "raken de waterkwaliteit", "waarde": 8, "max": 20, "kleur": "kan", "bij": "na classificatie"},
            {"label": "bevatten de norm", "waarde": 0, "max": 20, "kleur": "weg", "bij": "principieel onvindbaar op een punt"},
        ]},
        "Laag één: de regels. Dit werkt. We bevragen het Digitaal Stelsel live op de "
        "coördinaat van het meetpunt en krijgen twintig regelingen terug. Maar als je ze "
        "classificeert, raken er acht de waterkwaliteit. De rest is het Omgevingsprogramma Retail, "
        "het Warmteprogramma, een actieplan geluid, voorbeschermingsregels voor datacentra. Ook het "
        "omgevingsplan valt af: over een lozing op rijkswater gaat niet de gemeente maar de "
        "minister. En de norm zelf komt er principieel niet uit, om de reden die we net zagen. De "
        "machine antwoordt keurig; alleen niet op deze vraag.",
        "DSO Ozon, regelingen op punt (Belfeld boven)", "/kmg", 30),

    _dia(
        6, "Mag", "De vergunningen: een voorschrift is tekst, geen grootheid",
        ["Landelijk bestaat er geen register van wie wat waar loost",
         "Voor de Maas wél: de Atlas voor een Schone Maas — 69 vergunningen, live bevraagbaar",
         "Soms staat er een vracht in, vaker een concentratie plus een debiet,",
         "en vaak iets wat zich niet laat omrekenen"],
        {"soort": "balken", "balken": [
            {"label": "voorschrift-treffers over 9 meetpunten", "waarde": 2550, "max": 2550,
             "kleur": "mag", "bij": "live uit de Atlas"},
            {"label": "bruikbaar na het informatiemodel", "waarde": 2163, "max": 2550,
             "kleur": "mag", "bij": "84,8 procent"},
            {"label": "volledig", "waarde": 0, "max": 2550, "kleur": "weg",
             "bij": "geen enkele draagt een geldigheidsperiode"},
        ]},
        "Laag twee: de vergunningen. En hier begint het schuren. Landelijk bestaat er geen register "
        "van wie wat waar loost. Voor het Maasstroomgebied bestaat het wél — de Atlas voor "
        "een Schone Maas, een regionaal initiatief, negenenzestig vergunningen, ruimtelijk "
        "bevraagbaar. Over negen meetpunten levert dat tweeduizend vijfhonderdvijftig "
        "voorschrift-treffers op. Daarvan zijn er tweeduizend honderddrieënzestig bruikbaar, "
        "bijna vijfentachtig procent. Maar vólledig is er geen één. Nul van "
        "tweeduizend vijfhonderdvijftig. Geen enkel voorschrift draagt een geldigheidsperiode, dus "
        "een vervallen voorschrift is niet van een geldend te onderscheiden.",
        "Atlas voor een Schone Maas (live) · informatiemodel lozingsvoorschriften",
        "/watermodel", 30),

    _dia(
        7, "Gebeurt", "De metingen: goed op orde, maar met de hand opgehaald",
        ["Waterkwaliteitsportaal, meetjaar 2025: 384.259 rijen → 4822 metingen op 92 meetpunten",
         "Elke meting draagt een parametercode, een hoedanigheid en een eenheid — Aquo",
         "Zink staat op elk punt in twee reeksen: totaal én opgelost",
         "De API geeft 401; de machine-ingang komt begin 2027"],
        {"soort": "drieluik", "kolommen": [
            {"kop": "Zink totaal", "groot": "7,15", "bij": "µg/l · Eijsden ponton", "kleur": "gebeurt"},
            {"kop": "Zink opgelost", "groot": "2,80", "bij": "µg/l · zelfde punt, zelfde jaar", "kleur": "gebeurt"},
            {"kop": "Gepoold", "groot": "4,54", "bij": "een waarde die niemand heeft gemeten", "kleur": "weg"},
        ]},
        "Laag drie: de metingen — de best verzorgde bron van de vier. Elke meting volgt de "
        "Aquo-standaard: parametercode, hoedanigheid, eenheid. Dat klinkt als een detail tot je "
        "het mist. Zink staat op elk Maas-punt in twee reeksen, totaal en opgelost: bij Eijsden "
        "zeven komma vijftien tegen twee komma tachtig. Trek je die samen, dan krijg je een "
        "concentratie die niemand ooit heeft gemeten — terwijl de norm alleen over de opgeloste "
        "fractie gaat. Het pijnlijke: deze bron heeft geen machine-ingang. De API geeft een "
        "vier-nul-een; de module die dat oplost komt begin tweeduizendzevenentwintig.",
        "Waterkwaliteitsportaal, Informatiehuis Water, meetjaar 2025", "/kmg", 35),

    _dia(
        8, "Gemeld", "De vierde laag: wat een bedrijf zelf rapporteert",
        ["E-PRTR via het RIVM — als enige bron in deze keten machinaal bevraagbaar",
         "Sappi Maastricht: 7008 kg zink per jaar vergund, 105 kg gemeld — 1,5 procent",
         "Stikstof: 525.600 kg vergund tegen 52.600 gemeld — 10 procent",
         "Een ontbrekende melding is géén nul: E-PRTR kent alleen de grote lozers"],
        {"soort": "balken", "balken": [
            {"label": "zink vergund", "waarde": 7008, "max": 7008, "kleur": "mag", "bij": "kg per jaar"},
            {"label": "zink gemeld", "waarde": 105, "max": 7008, "kleur": "gemeld", "bij": "1,5 procent benut"},
            {"label": "stikstof vergund", "waarde": 525600, "max": 525600, "kleur": "mag", "bij": "kg per jaar"},
            {"label": "stikstof gemeld", "waarde": 52600, "max": 525600, "kleur": "gemeld", "bij": "10 procent benut"},
        ]},
        "De vierde laag is onze toevoeging: wat een bedrijf zelf meldt. Het RIVM publiceert dat "
        "als E-PRTR — machinaal bevraagbaar, als enige bron in deze hele keten. Daarmee kun je wat "
        "mag naast wat gemeld wordt leggen. Bij Sappi Maastricht: zevenduizend acht kilo zink per "
        "jaar vergund, honderdvijf kilo gemeld. Anderhalve procent. Voor stikstof tien procent. Dat "
        "verschil is vergunde ruimte die niet gebruikt wordt, en het staat nergens geregistreerd. "
        "Eén waarschuwing: een ontbrekende melding is geen nul — E-PRTR kent alleen de grote "
        "lozers.",
        "E-PRTR, RIVM (live) · Atlas voor een Schone Maas", "/kmg", 30),

    _dia(
        9, "Het voorbeeld", "Zink van begin tot eind",
        ["Alle vier de lagen zijn gevuld — en het loopt tóch spaak",
         "Vergund: een concentratie in mg/l, zonder hoedanigheid",
         "Gemeten: 7,15 totaal én 2,80 opgelost, in µg/l",
         "Norm: 7,80 µg/l, jaargemiddelde, opgeloste fractie"],
        {"soort": "drieluik", "kolommen": [
            {"kop": "Mag", "groot": "? µg/l", "bij": "hoedanigheid ontbreekt — totaal of opgelost?", "kleur": "mag"},
            {"kop": "Gebeurt", "groot": "2,80", "bij": "µg/l opgelost · de fractie waar de norm op slaat", "kleur": "gebeurt"},
            {"kop": "Norm", "groot": "7,80", "bij": "µg/l · jaargemiddelde, opgelost", "kleur": "weg"},
        ]},
        "Laten we één stof door alle vier de lagen volgen: zink, het leerzaamste geval, want hier "
        "is elke laag gevuld. De vergunning geeft een concentratie, maar zegt niet of die over de "
        "totale of de opgeloste fractie gaat — dat veld bestaat niet in het voorschrift. De meting "
        "geeft beide netjes apart. De norm is zeven komma tachtig microgram per liter, "
        "jaargemiddeld, op de opgeloste fractie. We hebben dus een vergunde waarde, een gemeten "
        "waarde en een norm, en we kunnen ze niet met zekerheid naast elkaar leggen. Niet omdat de "
        "data ontbreekt, maar omdat één veld niet wordt ingevuld.",
        "Aquo · KRW-toetsresultaten · Atlas", "/watermodel", 35),

    _dia(
        10, "Het resultaat", "Het register verklaart hoogstens een kwart",
        ["Per stof en meetpunt: welk deel van de gemeten waarde is vergund?",
         "Hoogste uitkomst: 28,5 procent (zink bij Brakel)",
         "De enige nullen die overblijven zijn PFOA — die stof staat in géén vergunning",
         "Keizersveer stond op 0 procent zolang wij in een cirkel van 50 km zochten"],
        {"soort": "rivier", "punten": [
            {"naam": "Eijsden ponton", "pct": 2.1, "wl": "Bovenmaas"},
            {"naam": "Stevensweert", "pct": 0.0, "wl": "Grensmaas"},
            {"naam": "Belfeld boven", "pct": 14.4, "wl": "Zandmaas"},
            {"naam": "Heel (innamewerk)", "pct": 15.9, "wl": "Zandmaas"},
            {"naam": "Brakel", "pct": 28.5, "wl": "Beneden Maas"},
            {"naam": "Keizersveer", "pct": 13.3, "wl": "Bergsche Maas"},
            {"naam": "Bovensluis", "pct": 15.4, "wl": "Haringvliet-oost"},
            {"naam": "Haringvlietsluis", "pct": 24.6, "wl": "Haringvliet-west"},
        ]},
        "Nu de uitkomst. We rekenen per stof en per meetpunt uit welk deel van de gemeten waarde "
        "toe te rekenen is aan vergunningen bovenstrooms. Uitdrukkelijk een bovengrens, nooit een "
        "vaststelling — wij zeggen niet wie iets veroorzaakt. De hoogste uitkomst is achtentwintig "
        "komma vijf procent, voor zink bij Brakel. De enige nullen die overblijven zijn PFOA, en "
        "die stof staat in geen enkele vergunning. Eén getal is leerzamer dan de rest: Keizersveer "
        "stond tot deze week op nul. Niet omdat daar niets bovenstrooms ligt, maar omdat wij "
        "zochten in een cirkel van vijftig kilometer, en de Maas is tweehonderd kilometer lang. "
        "Sinds we het stroomgebieddistrict gebruiken telt Keizersveer vierenveertig vergunningen "
        "mee in plaats van geen.",
        "Toerekeningsmodel van dit lab — bovengrens, geen vaststelling", "/kmg", 40),

    _dia(
        11, "De blinde vlek", "Een hele route staat in geen enkel register",
        ["Ruim 99% van 8,4 miljoen huishoudens loost op het riool, plus een half miljoen bedrijven",
         "7 van de 69 Maas-vergunningen zijn van een rioolwaterzuivering",
         "Hun 30 voorschriften begrenzen vijf grootheden: CZV, BZV, stikstof, fosfor, zwevende stof",
         "Geen metaal, geen PFAS, geen ZZS"],
        {"soort": "chips",
         "wel": ["chemisch zuurstofverbruik", "biochemisch zuurstofverbruik", "stikstof totaal",
                 "fosfor totaal", "zwevende stof"],
         "niet": ["zink", "koper", "PFOA", "medicijnresten", "elke ZZS"]},
        "Hier komt die tweede route terug. Een bedrijf dat niet op de Maas loost maar op het riool, "
        "komt in dit register niet voor. Zijn stoffen komen er wel — via de zuivering. En kijk "
        "wat een zuiveringsvergunning begrenst: zeven van de negenenzestig Maas-vergunningen zijn "
        "van een rioolwaterzuivering, samen dertig voorschriften, over precies vijf grootheden. "
        "Zuurstofverbruik, stikstof, fosfor, zwevende stof. Geen enkel metaal, geen PFAS, geen zeer "
        "zorgwekkende stof. Wat de zuivering niet wegneemt gaat via het effluent de rivier in, en "
        "daarvoor staat nergens een grenswaarde. Voor zink dat via het riool binnenkomt is in dit "
        "hele register geen vergunde ruimte te vinden.",
        "Atlas voor een Schone Maas (live) · STOWA 2025-46", "/waterverhaal", 35),

    _dia(
        12, "De diagnose", "Drie keer hetzelfde ontbrekende veld",
        ["De stofnaam die geen code is — „zink” moet letterlijk matchen",
         "De hoedanigheid die in geen enkel voorschrift staat — totaal of opgelost?",
         "Het bedrijf zonder gedeelde sleutel — koppelen gaat op naam en afstand",
         "Elke keer bestaat het veld. Elke keer is het leeg of onvertaald."],
        {"soort": "stappen", "stappen": [
            {"nr": "1", "naam": "Stof", "sub": "naam in plaats van Aquo-code → opgelost met de domeintabel", "actief": True},
            {"nr": "2", "naam": "Hoedanigheid", "sub": "veld bestaat, wordt nooit ingevuld", "actief": False},
            {"nr": "3", "naam": "Inrichting", "sub": "KvK-nummer gevuld in 69 van 69, maar E-PRTR heeft een eigen nummer", "actief": False},
        ]},
        "Een stap terug: het is drie keer hetzelfde probleem op een ander niveau. Eén, de "
        "stof — de koppeling draaide op de Nederlandse stofnaam, „zink” moest "
        "letterlijk gelijk zijn aan „zink”. Twee, de hoedanigheid: dat veld bestaat in de "
        "standaard, maar is in geen enkel voorschrift ingevuld. Drie, het bedrijf: een vergunning "
        "en een milieujaarverslag gaan over dezelfde fabriek, en wij koppelen ze op nabijheid plus "
        "naamgelijkenis. Interessant detail — het KvK-nummer in de vergunning is wél "
        "gevuld, negenenzestig van negenenzestig. Alleen draagt de melding een eigen "
        "inrichtingsnummer, en er is geen vertaling tussen die twee. Dat is één "
        "kruistabel, geen stelselwijziging.",
        "koppeling.py · lozingsmodel.py", "/watermodel", 35),

    _dia(
        13, "De kennisgraaf", "Eén gedeeld nummer tegen één handtabel",
        ["Een informatiemodel beschrijft vélden; een graaf beschrijft relaties",
         "Aquo draagt bij 4104 van 5623 parameters een CAS-nummer — de E-PRTR-verordening ook",
         "Van 16 gemelde stoffen koppelen er 9 vanzelf, waarvan 2 die onze handtabel mist",
         "Nul keer spreken CAS en handtabel elkaar tegen"],
        {"soort": "balken", "balken": [
            {"label": "koppelen via CAS én handtabel, identiek", "waarde": 7, "max": 16,
             "kleur": "accent", "bij": "de handtabel was correct, maar overbodig"},
            {"label": "alleen via CAS", "waarde": 2, "max": 16, "kleur": "gemeld",
             "bij": "trichloormethaan en chlooralkanen"},
            {"label": "alleen met de hand — geen CAS bestaat", "waarde": 4, "max": 16,
             "kleur": "mag", "bij": "somparameters"},
            {"label": "geen brug", "waarde": 3, "max": 16, "kleur": "weg",
             "bij": "TOC, AOX, cyaniden"},
        ]},
        "Nu de kennisgraaf, want die lost een ander soort probleem op. Een informatiemodel "
        "beschrijft vélden; een graaf beschrijft relaties tussen dingen die hun eigen identiteit "
        "houden. Concreet: Aquo draagt bij ruim vierduizend parameters een CAS-nummer, en de "
        "E-PRTR-verordening doet dat ook. Twee bronnen met hetzelfde nummer hoeven niet met de "
        "hand aan elkaar geknoopt te worden. Van de zestien gemelde stoffen koppelen er negen "
        "vanzelf, waaronder twee die onze handtabel mist. En nul keer spreken de twee wegen "
        "elkaar tegen: onze tabel was nergens fout, alleen incompleet. De somparameters hebben "
        "per definitie geen CAS — dat zijn grootheden uit een meetmethode, niet uit een molecuul.",
        "Aquo-domeintabel · E-PRTR bijlage II", "/kennisgraaf", 40),

    _dia(
        14, "De kennisgraaf", "En dan vindt die graaf iets",
        ["Dezelfde graaf als controle over alle 69 Maas-vergunningen, 781 voorschriften",
         "90 voorschriften hangen aan een ingetrokken Aquo-code",
         "Waarvan 83 „Zwevende stof” — de meest voorkomende parameter in het register",
         "14 dragen een naam die Aquo niet kent; 2 vergunningen tellen een som én haar delen"],
        {"soort": "balken", "balken": [
            {"label": "voorschriften in het Maasregister", "waarde": 781, "max": 781,
             "kleur": "mag", "bij": "69 vergunningen"},
            {"label": "op een ingetrokken code", "waarde": 90, "max": 781, "kleur": "weg",
             "bij": "4 namen, waarvan Zwevende stof 83×"},
            {"label": "naam die Aquo niet kent", "waarde": 14, "max": 781, "kleur": "weg",
             "bij": "melamine, AMPA, pyrazool"},
        ]},
        "En dan kun je die graaf als controle over het echte register draaien. Over alle "
        "negenenzestig Maas-vergunningen: negentig voorschriften hangen aan een Aquo-code die is "
        "ingetrokken. Drieëntachtig daarvan zijn zwevende stof — de meest voorkomende parameter "
        "in het hele register, en de code is vervallen zonder opvolger. Die koppelt dus niet, "
        "terwijl onze eigen documentatie beweerde van wel. Veertien voorschriften dragen een naam "
        "die Aquo helemaal niet kent: melamine, AMPA, pyrazool — daar loopt de standaard achter "
        "op wat er vergund wordt. En twee vergunningen begrenzen een somparameter én een paar van "
        "haar delen apart, dus wie optelt telt dubbel.",
        "/kennisgraaf, live over het Maasregister", "/kennisgraaf", 35),

    _dia(
        15, "De valkuil", "Ruimte tot de norm is geen voorraad",
        ["De rekensom „ruimte = norm − achtergrond” is de immissietoets",
         "en die is de dérde en laatste stap, niet de eerste",
         "Bronaanpak en beste beschikbare technieken gaan eraan vooraf — ongeacht de ruimte",
         "„Past niet” is geen weigering maar de aanleiding voor strengere voorwaarden"],
        {"soort": "stappen", "stappen": [
            {"nr": "1", "naam": "Bronaanpak", "sub": "art. 10.29a Wm · voorkomen, hergebruiken, pas dan lozen", "actief": False},
            {"nr": "2", "naam": "BBT via de ABM", "sub": "art. 8.9 en 8.10 Bkl · geldt ongeacht de ruimte", "actief": False},
            {"nr": "3", "naam": "Immissietoets", "sub": "art. 8.30 Bkl · dít is onze rekensom", "actief": True},
        ]},
        "Eén valkuil die we zelf in deze POC hadden zitten. Wij rekenen ruimte tot de norm "
        "uit: norm min achtergrond, maal het debiet. Die som klopt, maar de richting niet. Dit is "
        "namelijk de immissietoets, en die is de derde en laatste stap. Daarvóór komen de "
        "bronaanpak — voorkomen, hergebruiken, lozen als laatste optie — en de beste "
        "beschikbare technieken. Die twee gelden ongeacht hoeveel ruimte er is. Een ruime rivier is "
        "geen argument om een bronmaatregel achterwege te laten. En andersom: past niet is geen "
        "eindoordeel maar de aanleiding voor strengere voorwaarden. Weigeren komt pas daarna.",
        "STOWA 2025-46 §6 · art. 8.22 en 8.30 Bkl", "/gebruiksruimte", 35),

    _dia(
        16, "De oplossing", "Wat een informatiemodel hier oplost",
        ["De Aquo-domeintabel als parameterreferentie: 5630 geldige codes",
         "Bruikbare voorschriften: van 57 naar 84 procent",
         "Gekoppelde stoffen per register: van 3 naar 42",
         "De winst zit in alledaagse begrippen: Zuurgraad → pH, Zwevende stof → ZS, Debiet → Q"],
        {"soort": "balken", "balken": [
            {"label": "bruikbaar — afgeleid uit één meetbestand", "waarde": 57, "max": 100,
             "kleur": "weg", "bij": "492 codes"},
            {"label": "bruikbaar — met de echte Aquo-domeintabel", "waarde": 84, "max": 100,
             "kleur": "accent", "bij": "5630 codes"},
            {"label": "gekoppelde stoffen — vóór", "waarde": 3, "max": 42, "kleur": "weg", "bij": ""},
            {"label": "gekoppelde stoffen — ná", "waarde": 42, "max": 42, "kleur": "accent", "bij": ""},
        ]},
        "Wat lost een informatiemodel hiervan op? De grootste enkele winst kwam van de echte "
        "Aquo-domeintabel, die gewoon als CSV op aquo punt nl staat. Daarmee gaat het aandeel "
        "bruikbare voorschriften van zevenenvijftig naar vierentachtig procent, en het aantal "
        "gekoppelde stoffen van drie naar tweeënveertig. Het tweede deel is belangrijker: elk veld "
        "draagt een zekerheid — uit de bron, afgeleid, aangenomen of ontbrekend. Zo maakt het "
        "model zichtbaar wat er mist, in plaats van een onvolledige vergunning er netjes uit te "
        "laten zien.",
        "Aquo-domeintabel Parameter · lozingsmodel.py", "/watermodel", 30),

    _dia(
        17, "Over deze POC", "Wat dit eigenlijk is: een zolderkamerproject",
        ["Eén persoon met waterkennis, een taalmodel als bouwer, een Jetson onder de trap",
         "336 commits sinds mei, 11.822 regels code, 8.811 regels test — één auteur",
         "Geen team, geen review, geen opdrachtgever, geen budget",
         "Het ziet er af uit. Dat is precies het risico."],
        {"soort": "drieluik", "kolommen": [
            {"kop": "Wat het wél is", "groot": "een bewijs", "bij": "dat deze vragen met open "
             "bronnen te stellen zijn", "kleur": "kan"},
            {"kop": "Wat het níét is", "groot": "een product", "bij": "geen beheer, geen SLA, "
             "geen tweede paar ogen", "kleur": "mag"},
            {"kop": "Wat het kost", "groot": "tijd", "bij": "de infrastructuur is bijna gratis; "
             "de domeinkennis niet", "kleur": "gebeurt"},
        ]},
        "Nu iets ongemakkelijks, en ik wil het liever zelf zeggen dan dat u het denkt. Dit is een "
        "zolderkamerproject. Eén persoon met waterkennis, een taalmodel dat de code schrijft, en "
        "een computertje onder de trap. Driehonderdzesendertig commits sinds mei, bijna twaalfduizend "
        "regels code en negenduizend regels test — allemaal van één auteur. Geen team, geen "
        "collegiale toets, geen opdrachtgever. Wat u gezien heeft ziet er af uit, en dat is "
        "precies het risico: een verzorgde pagina suggereert dat iemand het gevalideerd heeft. "
        "Dat is hier niet gebeurd. Laat me daarom laten zien wat de kwaliteit werkelijk is.",
        "git log van dit project", "/water", 35),

    _dia(
        18, "Over deze POC", "Wat is de kwaliteit? Kijk naar de fouten",
        ["804 tests stonden groen terwijl de uitkomst fout was",
         "Zink een factor 1000 te laag: het model rekende in mg/l, de meting staat in µg/l",
         "Het bovenstroomsfilter stond er, maar deed niets — elke vergunning telde mee",
         "90 procent toegerekend bij Goeree: een rivierformule losgelaten op kustwater",
         "Elke fout gevonden tegen de échte bron. Geen enkele door een test."],
        {"soort": "stappen", "stappen": [
            {"nr": "✗", "naam": "Tests op verzonnen data", "sub": "alle fixtures stonden in mg/l, "
             "dus de eenheidsfout was onzichtbaar", "actief": False},
            {"nr": "✗", "naam": "Eigen documentatie", "sub": "beweerde weken dat „Zwevende stof” "
             "koppelt; die Aquo-code is vervallen", "actief": False},
            {"nr": "✓", "naam": "Live tegen de bron", "sub": "elke consequente fout is zó aan het "
             "licht gekomen", "actief": True},
        ]},
        "Wat is de kwaliteit? Daar kan ik beter de fouten voor laten spreken dan het aantal tests. "
        "Zink stond een factor duizend te laag omdat het model in milligram rekende en de meting in "
        "microgram staat — alle tests gebruikten milligram-voorbeelden, dus ze stonden groen. Het "
        "filter dat benedenstroomse vergunningen eruit moest halen stond er wel, maar deed niets. "
        "En vorige week kwam er negentig procent toegerekende stikstof uit bij Goeree: een "
        "rivierformule losgelaten op kustwater, waar geen jaarafvoer bestaat. Allemaal gevonden "
        "door het tegen de echte bron te houden. Geen enkele door een test. De eerlijke conclusie "
        "is dus niet dat het nu klopt, maar dat er vermoedelijk nog meer in zit.",
        "de fouten uit deze POC, alle vier live gevonden", "/kmg", 40),

    _dia(
        19, "Over deze POC", "Wat kan er nú al, met open data?",
        ["Acht bronnen live bevraagbaar, zonder contract, project of aanbesteding",
         "DSO Ozon · Atlas voor een Schone Maas · RWS KRW · PDOK · RIVM E-PRTR · Aquo · WKP",
         "Alleen het DSO vraagt een sleutel; de rest is open",
         "Wat niet kan: de Digitale Delta API geeft 401, en een landelijk lozingenregister bestaat niet"],
        {"soort": "balken", "balken": [
            {"label": "bronnen live bevraagbaar", "waarde": 8, "max": 10, "kleur": "accent",
             "bij": "vandaag, zonder toestemming vooraf"},
            {"label": "handmatige momentopname", "waarde": 1, "max": 10, "kleur": "mag",
             "bij": "de metingen — geen machine-ingang tot 2027"},
            {"label": "landelijk register van lozingen", "waarde": 0, "max": 10, "kleur": "weg",
             "bij": "bestaat niet; de Maas heeft een regionaal initiatief"},
        ]},
        "Dan de vraag die er praktisch toe doet: wat kan er nú al? Meer dan je zou denken. Acht "
        "bronnen zijn vandaag live te bevragen, zonder contract en zonder project: het Digitaal "
        "Stelsel, de Atlas voor een Schone Maas, de waterlichamen van Rijkswaterstaat, PDOK, de "
        "emissiemeldingen bij het RIVM, de Aquo-domeintabellen, en de downloadmodule van het "
        "Waterkwaliteitsportaal. Alleen het DSO vraagt een sleutel; de rest is gewoon open. Wat "
        "niet kan is net zo leerzaam: de meetwaarden hebben geen machine-ingang tot "
        "tweeduizendzevenentwintig, en een landelijk register van wie wat waar loost bestaat "
        "domweg niet. De drempel is dus niet de techniek.",
        "connectors in dit lab, alle acht live geverifieerd", "/water", 35),

    _dia(
        20, "Over deze POC", "De risico's — vier, en de eerste is de ergste",
        ["Vloeiend en fout: een model schrijft een overtuigende zin om een verzonnen getal",
         "Bronnen falen stil: PDOK negeert het filter en geeft de héle dataset terug, met status 200",
         "Geen licentie: de Atlas-lagen staan open maar dragen geen gebruiksvoorwaarden",
         "Eén paar ogen — en het ziet eruit alsof het gevalideerd is"],
        {"soort": "chips",
         "wel": ["fouten die luid falen", "bronnen met een contract", "herkomst per veld"],
         "niet": ["plausibel klinkende onzin", "status 200 op verkeerde data",
                  "een pagina die af lijkt"]},
        "De risico's, en de eerste is de ergste. Een taalmodel schrijft een overtuigende zin om "
        "een verzonnen getal heen; het klinkt nergens onzeker. In deze POC stond op enig moment "
        "een berekende zin met een factor honderddrieënveertig erin die nergens op sloeg. Twee: "
        "bronnen falen stil. PDOK negeert een ruimtelijk filter en geeft de hele landelijke "
        "dataset terug, met een nette status tweehonderd — dat is het ergste soort fout, want "
        "niets gaat stuk. Drie: de Atlas-lagen staan open maar dragen geen enkele "
        "gebruiksvoorwaarde, dus wat je ermee mag is onduidelijk. En vier: één paar ogen, terwijl "
        "het resultaat eruitziet alsof iemand het heeft gevalideerd.",
        "waarnemingen uit deze POC", "/kennisgraaf", 35),

    _dia(
        21, "Over deze POC", "Wat is minimaal nodig om dit serieus te doen?",
        ["Niet de hardware. Dit draait op een Jetson, maar een laptop volstaat.",
         "Wel: een domeinexpert die een fout getal rúikt — dat is de bindende beperking",
         "Tests die tegen de échte bron draaien, niet tegen verzonnen voorbeelden",
         "Elk getal op een pagina afgeleid uit data, nooit ingetypt",
         "Herkomst per veld: uit de bron, afgeleid, aangenomen of ontbrekend"],
        {"soort": "stappen", "stappen": [
            {"nr": "1", "naam": "Domeinexpert in de lus", "sub": "elke fout hier was een "
             "domeinfout, geen programmeerfout", "actief": True},
            {"nr": "2", "naam": "Tests tegen de bron", "sub": "een fixture bevestigt alleen je "
             "eigen aanname", "actief": False},
            {"nr": "3", "naam": "Geen getal met de hand", "sub": "wat je typt veroudert; wat je "
             "afleidt valt om", "actief": False},
            {"nr": "4", "naam": "Herkomst per veld", "sub": "zodat zichtbaar blijft wat je niet "
             "weet", "actief": False},
        ]},
        "Wat is er dan minimaal nodig om dit serieus te doen? Niet de hardware: dit draait "
        "toevallig op een Jetson, maar een laptop volstaat en de infrastructuur kost bijna niets. "
        "Vier andere dingen wél. Eén, en veruit het belangrijkste: een domeinexpert in de lus. "
        "Elke fout die ik net liet zien was een waterfout, geen programmeerfout — eenheden, "
        "fracties, stroomgebieden, kustwater. Iemand zonder waterkennis had ze alle vier "
        "gepubliceerd. Twee: tests die tegen de echte bron draaien, want een verzonnen voorbeeld "
        "bevestigt alleen je eigen aanname. Drie: geen enkel getal met de hand op een pagina. En "
        "vier: herkomst per veld, zodat zichtbaar blijft wat je níét weet.",
        "de werkwijze die uit deze POC is gegroeid", "/watermodel", 40),

    _dia(
        22, "Het eindbeeld", "Hoe ziet het product eruit als de gaten dicht zijn?",
        [f"Eén traject van de Zandmaas, één stof: {_nl(_EB['balans']['gemeten_kg'])} kg zink per jaar",
         "Verdeeld over vier herkomsten, elk met zijn eigen onderbouwing",
         "En achter de zuivering: 23 aangesloten lozers met hun regime",
         "Die vergunning begrenst CZV, BZV, stikstof, fosfor en zwevende stof — géén zink",
         "Alles verzonnen. Echt is de vórm, en de lijst met wat ervoor nodig is."],
        {"soort": "balken", "balken": [
            {"label": h["naam"], "waarde": h["kg"], "max": _EB["balans"]["verdeeld_kg"],
             "kleur": {"mag": "mag", "gemeld": "gemeld", "gebeurt": "gebeurt",
                       "dim": "dim"}.get(h["kleur"], "mag"),
             "bij": f"{h['pct']:.1f}%".replace(".", ",") +
                    ("" if h["vandaag"] == "ja" else
                     " · vandaag " + ("deels" if h["vandaag"] == "deels" else "niet te maken"))}
            for h in _EB["balans"]["herkomsten"]
        ]},
        "Tot slot: hoe ziet het eruit als het wél lukt? We hebben één traject van de Zandmaas "
        "doorgerekend met verzonnen cijfers, om de vórm te laten zien. Vijftigduizend kilo zink "
        "per jaar, verdeeld over vier herkomsten: de directe lozers, het effluent van de "
        "zuivering, wat bovenstrooms de grens over komt, en diffuus. Het interessantste blok is "
        "de zuivering. Die vergunning begrenst zuurstofverbruik, stikstof, fosfor en zwevende "
        "stof — geen zink. In het eindbeeld zie je wie erachter zit: drieëntwintig aangesloten "
        "lozers, met hun regime erbij, en de derde daarvan valt onder algemene regels en heeft "
        "dus helemaal geen vergunning. Vandaag is dat één anonieme post.",
        "/eindbeeld — volledig synthetisch", "/eindbeeld", 35),

    _dia(
        23, "Het eindbeeld", "En dan zie je iets dat nu onzichtbaar is",
        [f"Ruimte tot de norm: {_nl(_EB['ruimte']['vrij_kg'])} kg per jaar",
         f"Vergunde ruimte die stilligt: {_nl(_EB['ruimte']['onbenut_kg'])} kg",
         f"Dat is {str(_EB['ruimte']['onbenut_maal_vrij']).replace('.', ',')} keer zoveel",
         "Benutten alle houders hun vergunning, dan wordt de norm overschreden —",
         "zonder dat iemand een regel overtreedt, en zonder dat er een besluit aan te pas komt"],
        {"soort": "balken", "balken": [
            {"label": "ruimte tot de norm", "waarde": _EB["ruimte"]["vrij_kg"],
             "max": _EB["ruimte"]["vergund_kg"], "kleur": "accent",
             "bij": "wat er nog bij mag voordat de norm wordt geraakt"},
            {"label": "nu gemeld", "waarde": _EB["ruimte"]["gemeld_kg"],
             "max": _EB["ruimte"]["vergund_kg"], "kleur": "gemeld",
             "bij": f"{str(_EB['ruimte']['benut_pct']).replace('.', ',')}% van het vergunde"},
            {"label": "vergunde ruimte die stilligt", "waarde": _EB["ruimte"]["onbenut_kg"],
             "max": _EB["ruimte"]["vergund_kg"], "kleur": "weg",
             "bij": "mag worden gebruikt, vandaag en morgen"},
        ]},
        "En dan komt er iets uit dat vandaag niet te berekenen is. De ruimte tot de norm is elfduizend "
        "kilo per jaar. De vergunde ruimte die stilligt — het verschil tussen wat de vier houders "
        "mogen en wat ze melden — is vijfendertigduizend kilo. Ruim drie keer zoveel. Zouden ze "
        "alle vier hun vergunning volledig benutten, dan wordt de norm overschreden zonder dat "
        "iemand een regel overtreedt en zonder dat er één besluit aan te pas komt. Dat is geen "
        "rekentruc maar een eigenschap van het stelsel, en je ziet hem pas als je de gemelde en "
        "de vergunde vracht naast elkaar kunt leggen. Precies de kruistabel die nu ontbreekt.",
        "/eindbeeld, doorgerekend uit de aannames daar", "/eindbeeld", 40),

    _dia(
        24, "Voor datamensen", "Wat dit project aantoont — en wat ik u zou aanraden",
        ["Vier lagen, vier bronhouders, vier informatiemodellen — en nergens een gebrek aan data",
         "Wat telkens ontbreekt is een sleutel of een relatie, niet een gegeven",
         f"Een veld dat in de standaard staat maar nooit wordt ingevuld, is geen veld: "
         f"0 van {_nl(CIJFERS['voorschriften_totaal'])} voorschriften is volledig",
         "Twee registraties over hetzelfde object zonder gedeelde sleutel zijn twee registraties "
         "over niets",
         "Geen van de oplossingen vraagt een nieuw stelsel — een veld, een kruistabel, een relatie"],
        {"soort": "stappen", "stappen": [
            {"nr": "1", "naam": "Sleutel op een code, nooit op een naam",
             "sub": "de echte Aquo-domeintabel bracht de bruikbaarheid van 57 naar 84 procent",
             "actief": True},
            {"nr": "2", "naam": "Voer de herkomst per veld mee",
             "sub": "uit de bron, afgeleid, aangenomen of ontbrekend", "actief": True},
            {"nr": "3", "naam": "Toets tegen de bron, niet tegen fixtures",
             "sub": "804 tests stonden groen terwijl zink een factor 1000 te laag stond",
             "actief": True},
            {"nr": "4", "naam": "Publiceer de kruistabel",
             "sub": "KvK gevuld in 69 van 69; de melding heeft een eigen nummer en er is "
                    "geen vertaling", "actief": True},
        ]},
        "Voor wie met data werkt, zou ik het zo samenvatten. Vier lagen, vier bronhouders, vier "
        "informatiemodellen — en nergens een gebrek aan gegevens. Wat telkens ontbreekt is een "
        "sleutel of een relatie. Daaruit volgen vier aanbevelingen. Eén: sleutel op een code en "
        "nooit op een naam; dat tilde de bruikbaarheid hier van zevenenvijftig naar vierentachtig "
        "procent. Twee: voer de herkomst per veld mee, want zonder dat ziet een onvolledige "
        "vergunning er netjes uit. Drie: toets tegen de bron en niet tegen zelfbedachte "
        "voorbeelden — achthonderd tests stonden groen terwijl zink een factor duizend te laag "
        "stond. En vier: als twee registers allebei een identificatie hebben, publiceer dan de "
        "vertaling ertussen in plaats van een derde nummer te verzinnen.",
        "de vier lagen van dit dossier, samengevat", "/watermodel", 40),

    _dia(
        25, "Hoe verder", "Wat nog mist — en een datum",
        ["De Aquo-drieslag als sleutel in het voorschrift: parameter, hoedanigheid, eenheid",
         "Een geldigheidsperiode per voorschrift",
         "Een kruistabel eMJV ↔ KvK-vestiging",
         "En een stroomvolgorde: het register kent 163 Maas-waterlichamen en géén relatie ertussen",
         "Geen van vier vraagt een nieuw register"],
        {"soort": "tijdlijn", "items": [
            {"jaar": "gedaan", "wat": "de cirkel van 50 km vervangen door het stroomgebieddistrict, uit het waterlichaamregister van het WKP"},
            {"jaar": "nu", "wat": "drie velden, één kruistabel en een stroomvolgorde — geen nieuw register nodig"},
            {"jaar": "2027", "wat": "herziene Richtlijn Stedelijk Afvalwater in NL-wetgeving: monitoring van niet-huishoudelijke lozingen verplicht"},
            {"jaar": "2027", "wat": "machine-ingang van het Waterkwaliteitsportaal"},
        ]},
        "Hoe verder? Eén ding is net af: de cirkel van vijftig kilometer is vervangen door het "
        "stroomgebieddistrict, uit het waterlichaamregister. Wat nog mist zijn er vier. De "
        "Aquo-drieslag als sleutel aan de vergunningkant. Een geldigheidsperiode per voorschrift. "
        "Een kruistabel tussen het milieujaarverslag en de KvK-vestiging. En een stroomvolgorde: "
        "het register kent honderddrieënzestig Maas-waterlichamen en geen enkele relatie ertussen, "
        "dus welke bovenstrooms van welke ligt hebben wij zelf moeten bedenken. Geen van vier "
        "vraagt een nieuw register. En er is een datum bij: de herziene Richtlijn Stedelijk "
        "Afvalwater verplicht lidstaten om relevante niet-huishoudelijke lozingen te monitoren. "
        "Nederlandse implementatie: tweeduizendzevenentwintig.",
        "Richtlijn (EU) 2024/3019 art. 14 · STOWA 2025-46 · WKP-waterlichaamregister",
        "/waterverhaal", 35),

    _dia(
        26, "Slot", "Waar dit op neerkomt",
        ["Vier lagen opgehaald uit vier bronnen, drie ervan live",
         "Het register verklaart hoogstens een kwart van wat gemeten wordt",
         "Niet door gebrek aan data, maar door lege velden en ontbrekende relaties",
         "Alles op deze dia's staat als werkende pagina online"],
        {"soort": "lagen", "lagen": [
            {"naam": "/waterverhaal", "sub": "het dossier in vijf vragen — de korte doorloop", "kleur": "accent"},
            {"naam": "/kmg", "sub": "de vier lagen op negen Maas-meetpunten", "kleur": "mag"},
            {"naam": "/watermodel", "sub": "het informatiemodel en tien user stories", "kleur": "gebeurt"},
            {"naam": "/gebruiksruimte", "sub": "wat kan hier nog — in de juiste volgorde", "kleur": "kan"},
        ]},
        "Waar komt dit op neer? Vier lagen uit vier bronnen, drie ervan live, over elkaar gelegd "
        "op negen meetpunten in de Maas. Het vergunningenregister verklaart hoogstens een kwart "
        "van wat er gemeten wordt. Dat ligt niet aan een gebrek aan data — het ligt aan velden die "
        "bestaan maar leeg blijven, een kruistabel die niemand publiceert, een stroomvolgorde die "
        "in geen register staat, en een hele lozingsroute die er evenmin in staat. Alles wat u "
        "hier gezien heeft staat als werkende pagina online, met een proclaimer die uit de data "
        "zelf wordt opgebouwd. Dank u wel.",
        "LeefomgevingLab · leefomgevinglab.felixisfelix.com", "/water", 35),
]


def dias() -> list[dict]:
    """De dia's met hun begintijd erbij, zodat een speler er direct naartoe kan springen."""
    uit, t = [], 0
    for d in DIAS:
        uit.append({**d, "start_s": t})
        t += d["seconden"]
    return uit


def duur_s() -> int:
    return sum(d["seconden"] for d in DIAS)


def presentatie() -> dict:
    return {"titel": "Het waterdossier in een kwartier",
            "ondertitel": "Van juridische uitgangspunten tot wat er nodig is — "
                          "met de cijfers uit de proof of concept aan de Maas",
            "duur_s": duur_s(), "aantal": len(DIAS), "cijfers": CIJFERS, "dias": dias()}
