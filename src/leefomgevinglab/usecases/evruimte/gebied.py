"""Locaties, contouren en de vertaling van BAG-gebruiksdoel naar kwetsbaarheid.

De aandachtsgebieden komen uit dezelfde indicatieve tabel als het Seveso-doelbeeld (/dvth):
een gifwolkaandachtsgebied van 1500 m bij een acuut toxisch gas, en een brand- en
explosieaandachtsgebied bij een brandbaar gas. Geen QRA — zie de verantwoording.

De kwetsbaarheidsindeling is afgeleid van het BAG-gebruiksdoel. Dat is een benadering: het Bkl
kijkt naar de functie én naar de aanwezigheid van verminderd zelfredzame personen, en dat staat
niet in de BAG. Wat hier 'zeer kwetsbaar' heet, is dus een signaal om naar te kijken, geen
juridische kwalificatie.
"""

LOCATIES = {
    "europoort": {"id": "europoort", "naam": "Europoort — westelijk havengebied",
                  "rd": (72000.0, 441000.0), "gemeente": "Rotterdam",
                  "karakter": "diep havengebied, nauwelijks bewoning"},
    "botlek": {"id": "botlek", "naam": "Botlek — chemiecluster",
               "rd": (85500.0, 434500.0), "gemeente": "Rotterdam",
               "karakter": "vol industriegebied tegen woonkernen aan"},
    "gouda": {"id": "gouda", "naam": "Gouda — Gouwe-oever",
              "rd": (105800.0, 447000.0), "gemeente": "Gouda",
              "karakter": "stedelijk, bedrijvigheid verweven met wonen"},
    "gouda_school": {"id": "gouda_school",
                     "naam": "Gouda — pal naast een school (ter illustratie)",
                     "rd": (105900.0, 446690.0), "gemeente": "Gouda",
                     "karakter": "bewust zó gekozen dat een school binnen het "
                                 "brandaandachtsgebied valt — om te laten zien hoe de harde "
                                 "grens uitpakt"},
    "zutphen": {"id": "zutphen", "naam": "Zutphen — bedrijventerrein aan de IJssel",
                "rd": (211500.0, 464500.0), "gemeente": "Lochem",
                "karakter": "regionaal bedrijventerrein"},
}

# Voorgenomen inrichting: dezelfde casus als op /dvth.
VOORNEMEN = {
    "naam": "voorgenomen Seveso-inrichting (hogedrempel)",
    "stoffen": ["ammoniak", "propaan"],
    "toelichting": "Opslag van tot vloeistof verdicht ammoniak met een propaaninstallatie — "
                   "dezelfde casus als in het Seveso-doelbeeld.",
}

CONTOUREN = [
    {"soort": "gifwolkaandachtsgebied", "straal_m": 1500, "kleur": "#c792ea",
     "grond": "acuut toxisch gas, tot vloeistof verdicht"},
    {"soort": "brandaandachtsgebied", "straal_m": 90, "kleur": "#ffb74d",
     "grond": "brandbaar gas in drukhouder"},
    {"soort": "explosieaandachtsgebied", "straal_m": 60, "kleur": "#ff7a6b",
     "grond": "brandbaar gas in drukhouder"},
]

# BAG-gebruiksdoel → kwetsbaarheidsklasse. Indicatief; zie de moduletoelichting.
KWETSBAARHEID = {
    "zeer kwetsbaar": ["onderwijsfunctie", "gezondheidszorgfunctie", "celfunctie"],
    "kwetsbaar": ["woonfunctie", "logiesfunctie", "bijeenkomstfunctie", "winkelfunctie",
                  "sportfunctie"],
    "beperkt kwetsbaar": ["kantoorfunctie", "industriefunctie", "overige gebruiksfunctie"],
}

KLASSE_UITLEG = {
    "zeer kwetsbaar": "Gebouwen waar groepen verminderd zelfredzame personen verblijven — scholen, "
                      "kinderopvang, zorg met bedgebied, justitiële inrichtingen.",
    "kwetsbaar": "Woningen en gebouwen waar veel mensen verblijven.",
    "beperkt kwetsbaar": "Kantoren en bedrijfsgebouwen met beperkte aanwezigheid.",
}


def contour(soort: str) -> dict:
    return next(c for c in CONTOUREN if c["soort"] == soort)


def grootste_straal() -> int:
    return max(c["straal_m"] for c in CONTOUREN)
