"""Nederlandse telwoorden, en het vinden van uitgeschreven aantallen in een tekst.

**Waarom dit bestaat.** Dit lab leidt zijn getallen af in plaats van ze te typen -- behalve in
proza, want "vijf bevindingen" leest beter dan "5 bevindingen". Die uitzondering is precies waar
een pagina stil kan gaan liegen: de code verschuift, de volzin blijft staan, en niets valt om.
`/onderwater` bestaat juist om de lezer de code te laten controleren, dus mag een zin op de
zusterpagina's niet iets anders beweren dan de catalogus zegt.

Eén tabel voor de hele suite, niet per testbestand opnieuw: twee lijsten die uit de pas kunnen
lopen is in dit project al duur geweest.
"""
import re

#: Uitgeschreven telwoorden, lowercase. Loopt tot twaalf -- hoger dan dat schrijft dit lab in
#: cijfers, en een onbekend telwoord hoort luid te falen in plaats van stil over te worden
#: geslagen (zie `getal`).
TELWOORD = {"een": 1, "één": 1, "twee": 2, "drie": 3, "vier": 4, "vijf": 5, "zes": 6,
            "zeven": 7, "acht": 8, "negen": 9, "tien": 10, "elf": 11, "twaalf": 12}


def getal(woord: str) -> int:
    """Het getal achter een uitgeschreven telwoord. Werpt een `KeyError` bij een onbekend woord:
    een bewaking die een telwoord niet kent moet omvallen, niet de claim overslaan."""
    return TELWOORD[woord.lower()]


def claims(tekst: str, patroon: str) -> list[int]:
    """Alle aantallen die `tekst` uitspreekt volgens `patroon`, als getallen.

    `patroon` is een reguliere expressie met precies één groep, en die groep vangt het telwoord
    -- bijvoorbeeld `r"(\\w+) deterministische regels"`. Een treffer waarvan het woord geen
    telwoord is (`"deze deterministische regels"`) wordt overgeslagen: dat is geen claim over een
    aantal. Een treffer die wél een telwoord is, levert een getal dat de aanroeper moet
    vergelijken met de afgeleide waarde.
    """
    uit = []
    for woord in re.findall(patroon, tekst, re.IGNORECASE):
        if woord.lower() in TELWOORD:
            uit.append(getal(woord))
    return uit
