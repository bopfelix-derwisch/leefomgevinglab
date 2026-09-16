"""Het waterdossier: welke pagina's er bij horen, en wat ze delen.

Het lozingsverhaal stond verspreid over vier tabs die elkaar nauwelijks kenden — elke pagina
had een eigen handgeschreven nav met een willekeurige greep uit de andere. Deze module is de
enige plek waar staat wat het dossier is; de subnavigatie wordt eruit gegenereerd.

Per lid staat expliciet wat er live wordt opgehaald en wat synthetisch is. Dat paar dwingt af
dat elke waterpagina zich op één plek verantwoordt.
"""
from html import escape

LEDEN = [
    {"id": "overzicht", "pad": "/water", "label": "Overzicht",
     "titel": "Het dossier in één beeld",
     "samenvatting": "Wat er speelt bij één directe lozing op een rijkswater, en waar in dit lab "
                     "je elk stuk daarvan terugvindt.",
     "live": [], "synthetisch": []},
    {"id": "keten", "pad": "/lozing", "label": "Keten",
     "titel": "Doelbeeld: de keten in 8 stappen",
     "samenvatting": "Van aanvraag via het DSO-loket tot handhaving volgens de LHSO, met de knip "
                     "tussen twee bevoegde gezagen en het register dat niet bestaat.",
     "live": ["REV-WFS", "RWS KRW-service", "PDOK bestuurlijke gebieden"],
     "synthetisch": ["het bedrijf", "Register Lozingen"]},
    {"id": "ruimte", "pad": "/gebruiksruimte", "label": "Ruimte",
     "titel": "Wat kan hier nog? — drie locaties aan de IJssel",
     "samenvatting": "Drie gemeenten, twee provincies, één waterlichaam: de regels verschillen per "
                     "locatie, de gebruiksruimte is gedeeld.",
     "live": ["DSO Ozon (regelingen op punt)", "RWS KRW-service"],
     "synthetisch": ["vergunningregister", "normen", "achtergrondconcentraties"]},
    {"id": "kaart", "pad": "/waterruimte", "label": "Kaart",
     "titel": "Wat kan hier nog? — prik op de kaart",
     "samenvatting": "Dezelfde vraag op een willekeurig punt. Op de Maas met echte vergunningen "
                     "uit de Atlas voor een Schone Maas, elders met een synthetisch register.",
     "live": ["DSO Ozon", "RWS KRW-service", "PDOK bestuurlijke gebieden",
              "Atlas voor een Schone Maas"],
     "synthetisch": ["normen", "achtergrondconcentraties", "debiet per waterlichaam"]},
    {"id": "knelpunten", "pad": "/balo", "label": "Knelpunten",
     "titel": "Waar de keten vastloopt",
     "samenvatting": "Beide doelbeeld-casussen langs de BALO-redeneerlijnen: 16 informatiebehoeften, "
                     "waarvan 8 onvervuld.",
     "live": [], "synthetisch": ["de koppeling van BALO aan deze casussen"]},
]

LIJNEN = [
    {"id": "knip", "kop": "De knip",
     "tekst": "Twee bevoegde gezagen over één fabriek: de lozingsactiviteit gaat naar de "
              "waterbeheerder, het milieudeel blijft bij de gemeente. Er is geen koppelvlak dat "
              "afdwingt dat beide besluiten op elkaar aansluiten, terwijl een emissiebeperking in "
              "het ene spoor de vracht in het andere verandert.",
     "leden": ["keten", "ruimte", "kaart", "knelpunten"]},
    {"id": "register", "kop": "Het register dat niet bestaat",
     "tekst": "Er is geen landelijk beeld van wie wat waar loost, en dus geen optelsom per "
              "waterlichaam. Voor het Maasstroomgebied is er wél een regionaal initiatief — de "
              "Atlas voor een Schone Maas — en juist het contrast met de rest van Nederland laat "
              "zien wat een landelijk register zou opleveren.",
     "leden": ["keten", "ruimte", "kaart", "knelpunten"]},
    {"id": "stroomafwaarts", "kop": "Het effect ligt stroomafwaarts",
     "tekst": "Een lozing is geen contour om een punt. Hij werkt door in een watersysteem en telt "
              "op bij alles wat verder stroomopwaarts al geloosd wordt. Het CIM-VTH-Flo kent geen "
              "relatie tussen een lozing en het water dat hem ontvangt.",
     "leden": ["keten", "ruimte", "kaart"]},
]

ATLAS = {
    "naam": "Atlas voor een Schone Maas",
    "url": "https://atlas-smwk.hub.arcgis.com/",
    "houder": "Schone Maaswaterketen — waterschappen Aa en Maas, Brabantse Delta, De Dommel en "
              "Limburg, met Rijkswaterstaat en de drinkwaterbedrijven",
    "wat_er_al_is": [
        "72 vestigingen met een directe lozingsvergunning, als punt op de kaart",
        "782 vergunde voorschriften over 68 parameters, met kenmerk en besluitdatum",
        "meetgegevens van 38 stoffen, vier keer per jaar sinds 2023",
    ],
    "wat_dit_lab_toevoegt": [
        "de optelsom: vergunde vrachten bij elkaar, afgezet tegen de norm van het waterlichaam",
        "de regels op de plek, live uit het DSO, met onderscheid direct/indirect werkend",
        "de vraag vooruit: niet wat er vergund is, maar wat er nog bij kan",
        "het bevoegd gezag op een willekeurig punt, ook waar nog niets ligt",
    ],
    "licentie": "De lagen staan publiek open maar dragen geen expliciete licentie. Dit lab "
                "bevraagt ze live met bronvermelding en neemt geen kopie van de dataset op.",
}


def lid(id: str) -> dict:
    """Het lid met dit id; KeyError als het niet bestaat — luid falen."""
    for l in LEDEN:
        if l["id"] == id:
            return l
    raise KeyError(id)


def dekking() -> list[dict]:
    """Per lijn de leden die hem raken, met hun labels — voor de matrix op de landingspagina."""
    return [{"lijn": lijn["kop"], "id": lijn["id"],
             "leden": [{"id": i, "label": lid(i)["label"], "pad": lid(i)["pad"]}
                       for i in lijn["leden"]]}
            for lijn in LIJNEN]


def subnav_html(actief: str | None) -> str:
    """De balk die op elke waterpagina terugkomt. Eén bron, dus overal dezelfde."""
    items = []
    for l in LEDEN:
        huidig = ' aria-current="page"' if l["id"] == actief else ""
        items.append(f'<a href="{escape(l["pad"])}"{huidig}>{escape(l["label"])}</a>')
    return ('<nav class="waternav" aria-label="Waterdossier">'
            '<span class="waternav-kop">Waterdossier</span>' + "".join(items) + "</nav>")


def overzicht() -> dict:
    return {"leden": LEDEN, "lijnen": LIJNEN, "dekking": dekking(), "atlas": ATLAS}
