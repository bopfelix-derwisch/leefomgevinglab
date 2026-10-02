"""Wat de regelingen op een meetpunt betekenen voor de waterkwaliteit daar.

De gedeelde tabel in `gebruiksruimte/regels.py` is geschreven voor een *lozingsvoornemen*: iemand
wil hier iets bouwen en lozen, dus het omgevingsplan telt mee — dat bepaalt of de inrichting er
überhaupt mag komen. Deze pagina stelt een andere vraag. Hier staat geen voornemen; hier staat een
meetpunt in de rivier, en de vraag is wat de waterkwaliteit op dat punt normeert.

Daarmee valt het grootste deel van wat het DSO op zo'n punt teruggeeft af. Gemeten op 2026-10-02
leverde Belfeld boven twintig regelingen, waaronder het Omgevingsprogramma Retail Venlo, het
Warmteprogramma Venlo, het Limburgs actieplan geluid, Voorbeschermingsregels hyperscale datacentra
en het Programma Mariene Strategie. Geen daarvan zegt iets over de waterkwaliteit van een lozing op
de Maas, terwijl de gedeelde tabel ze alle als van toepassing aanmerkt.

**En de norm zit er principieel niet tussen.** Van de vier AMvB's op dat punt zijn het Bal
(activiteiten) en het Bbl (bouwwerken) aanwezig, maar het **Bkl** niet — en juist daarin staan de
omgevingswaarden voor waterkwaliteit (bijlage III voor prioritaire stoffen, bijlage IIIa voor de
Nederlandse specifieke verontreinigende stoffen zoals zink). Dat is geen gebrek in de bevraging: die
omgevingswaarden hangen aan een *waterlichaam* via het waterprogramma, niet aan een *punt* in een
omgevingsplan. Een locatiebevraging kan ze dus niet vinden, hoe goed je ook bevraagt.

Classificeren op type alleen is bovendien te grof voor `Programma`. Het Warmteprogramma van een
gemeente raakt dit niet; het Nationaal Waterprogramma wél, en dat is precies het instrument waarin
de KRW-doelen per waterlichaam staan. Daarom verfijnt `verfijn_programma()` op de titel.
"""

# Of een regelingtype de waterkwaliteit op een meetpunt in rijkswater normeert.
DUIDING_KMG = {
    "AMvB": ("Rijksregels, en de enige laag hier die de lozing zelf raakt: het Bal maakt lozen op "
             "een oppervlaktewaterlichaam een vergunningplichtige activiteit, met de waterbeheerder "
             "als bevoegd gezag. Let op wat ontbreekt — het Bkl, met de omgevingswaarden voor "
             "waterkwaliteit, staat hier niet tussen. Die normen hangen aan een waterlichaam via "
             "het waterprogramma, niet aan een punt in een omgevingsplan.", True),
    "Omgevingsplan": ("Geldt hier, maar normeert de waterkwaliteit niet: het omgevingsplan bindt de "
                      "landzijde — wat er mag staan en gebeuren. Over een lozing op rijkswater gaat "
                      "niet de gemeente maar de minister van IenW. Dit is dezelfde knip die het "
                      "lozingsdossier beschrijft.", False),
    "Omgevingsverordening": ("Provinciale regels op de landzijde. De waterkwaliteit van een "
                             "rijkswater wordt niet provinciaal genormeerd.", False),
    "Waterschapsverordening": ("Geldt hier, maar raakt dit niet: het gaat om rijkswater, en daarvoor "
                               "is niet het waterschap maar de minister van IenW bevoegd gezag.",
                               False),
    "Voorbeschermingsregels": ("Tijdelijke bescherming vooruitlopend op een planwijziging: "
                               "landzijde. Normeert de waterkwaliteit hier niet.", False),
    "Voorbeschermingsregels Omgevingsplan": ("Tijdelijke bescherming vooruitlopend op een wijziging "
                                             "van het omgevingsplan: landzijde. Normeert de "
                                             "waterkwaliteit hier niet.", False),
    "Projectbesluit": ("Kan het waterlichaam zélf veranderen — een stuw of keersluis verandert "
                       "stroming en verblijftijd, en daarmee de concentraties die hier gemeten "
                       "worden. Werkt indirect door, maar is geen norm.", True),
    "Omgevingsvisie": ("Beleid, geen norm. Zegt niets over de waterkwaliteit op dit punt.", False),
    "Programma": ("Beleidsprogramma. Of dit de waterkwaliteit raakt, hangt niet van het type af "
                  "maar van het programma — zie de titel.", False),
    "Aanwijzingsbesluit N2000": ("Natura 2000: instandhoudingsdoelen kunnen strenger uitpakken dan "
                                 "de KRW-norm en werken hard door in een lozingsvergunning.", True),
}

# Titelwoorden waaraan een programma te herkennen is dat wél over water gaat. Bewust ruim: een
# programma ten onrechte als relevant aanmerken kost een regel op de pagina, het ten onrechte
# wegfilteren verbergt juist het instrument waarin de doelen staan.
_WATERWOORDEN = ("water", "rivier", "krw", "stroomgebied", "maas", "delta", "kust", "zee")


def verfijn_programma(regeling: dict) -> dict:
    """Een `Programma` op zijn titel beoordelen in plaats van op zijn type.

    `DUIDING_KMG` zet elk programma op niet-van-toepassing, want dat is het meestal. Gaat de titel
    over water, dan is het omgekeerd: dan is dit juist de plek waar de doelen per waterlichaam
    vandaan komen, en dat is precies wat deze pagina mist.
    """
    if (regeling.get("type") or "") != "Programma":
        return regeling
    titel = (regeling.get("titel") or "").lower()
    if not any(w in titel for w in _WATERWOORDEN):
        return regeling
    return {**regeling, "van_toepassing": True,
            "betekenis": ("Een waterprogramma, en daarmee de enige laag hier die wél iets over de "
                          "waterkwaliteit zegt: in het Nationaal Waterprogramma zijn de "
                          "KRW-waterlichamen aangewezen en staan de doelen per waterlichaam. Dit "
                          "lab heeft die doelen nog niet geladen, dus de pagina toont de metingen "
                          "zonder normoordeel.")}


def duid_regelingen(kan: dict) -> dict:
    """De regelingen in een KAN-laag naverwerken: programma's op titel beoordelen, dan hertellen.

    Draait ná `regels.regels_op_locatie(..., tabel=DUIDING_KMG)`. Het hertellen gaat door
    `regels.samenvatten()` en niet met een eigen som: die functie bestaat precies voor zo'n
    her-duiding, en hij levert dezelfde sleutels als de eerste telling. Zelf tellen zou een tweede
    paar getallen in hetzelfde woordenboek opleveren dat het eerste tegenspreekt — en een telling
    die niet bij de regels past is erger dan geen telling. Het sorteren loopt zo ook mee, zodat een
    verfijnd programma tussen de relevante regelingen komt te staan in plaats van onderaan.
    """
    from leefomgevinglab.usecases.gebruiksruimte import regels

    regelingen = kan.get("regelingen") or []
    if not regelingen:
        return kan
    uit, telling = regels.samenvatten([verfijn_programma(r) for r in regelingen])
    return {**kan, "regelingen": uit, "telling": telling}
