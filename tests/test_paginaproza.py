"""De uitgeschreven aantallen in de proza van `/wasstraat` en `/toezicht`.

**Waar deze tests over gaan.** Dit lab leidt zijn getallen af in plaats van ze te typen, en
`/onderwater` is daar helemaal op gebouwd: een test scant die pagina's uitlegteksten zelfs op
losse cijfers. Maar de twee signaalpagina's schrijven hun aantallen in volzinnen uit -- "Zeven
deterministische regels ... Vijf daarvan leveren een bevinding op" -- want zo leest het beter.

Die uitzondering is precies waar een pagina stil kan gaan liegen. De eindreview van november 2026
liet dat tweemaal zien: de samenvatting van `/toezicht` in de waterhub beloofde nog tien regels
plus pijplijn en runlog nadat die pagina was herbouwd naar drie regels en geen van beide, en de
kop "De zeven bevindingen" bleef staan toen er vijf van over waren. In beide gevallen viel er
niets om; het stond alleen publiek verkeerd.

**Wat deze tests dus doen.** Elke uitgesproken aantalclaim op de twee pagina's wordt vergeleken
met het getal dat uit `signalen.REGELS` volgt. Herformuleren mag: past een zin niet meer op een
patroon, dan verdwijnt die claim uit de controle. Daarom staat er ook een ondergrens op het
aantal gevonden claims -- anders kan deze bewaking stil leeglopen, en dat is dezelfde fout in een
nieuwe jas.
"""
import re

import pytest
from fastapi.testclient import TestClient

from leefomgevinglab.geluidsmeter import api as api_mod
from leefomgevinglab.usecases.toezicht import signalen
from tests.telwoorden import claims


@pytest.fixture(scope="module")
def verwacht():
    """De vier aantallen waarover de twee pagina's iets zeggen, afgeleid uit de catalogus."""
    papier = [r for r in signalen.REGELS if r.laag == "papier"]
    return {
        "papier": len(papier),
        "bevinding": len([r for r in papier if not signalen.is_voorbehoud(r.id)]),
        "voorbehoud": len([r for r in papier if signalen.is_voorbehoud(r.id)]),
        "werkelijkheid": len([r for r in signalen.REGELS if r.laag == "werkelijkheid"]),
    }


def _html(pad: str) -> str:
    """De pagina, met alle witruimte genormaliseerd naar enkele spaties.

    Zonder dat raken de patronen niets: de HTML is op leesbare regellengte afgebroken, dus
    "Zeven\n        deterministische regels" staat er met een regeleinde middenin de zin. Een
    bewaking die daarop stilvalt is erger dan geen bewaking -- zij is groen en leeg."""
    r = TestClient(api_mod.app).get(pad)
    assert r.status_code == 200, pad
    return re.sub(r"\s+", " ", r.text)


# Per pagina: welke zinsvorm welk afgeleid aantal uitspreekt. De sleutel verwijst naar
# `verwacht`; het patroon heeft precies één groep en die vangt het telwoord.
_PATRONEN = {
    "/wasstraat": [
        ("papier", r"(\w+) deterministische regels"),
        ("papier", r"kijken (\w+) regels of de vergunning"),
        ("bevinding", r"<b>(\w+)(?: daarvan)? leveren een bevinding op"),
        ("voorbehoud", r"<b>(\w+) zijn een voorbehoud"),
        ("voorbehoud", r"andere (\w+) zijn een <b>voorbehoud"),
        ("werkelijkheid", r"De (\w+) regels die meetdata"),
    ],
    "/toezicht": [
        ("werkelijkheid", r"De (\w+) signalen"),
        ("werkelijkheid", r"(\w+) deterministische regels"),
    ],
}

#: Ondergrens per pagina. Zonder dit kan de bewaking stil leeglopen zodra alle zinnen worden
#: herschreven -- en dan is zij groen om precies de verkeerde reden.
_MINIMUM = {"/wasstraat": 6, "/toezicht": 2}   # gemeten: 7 en 3 (2026-11-15)


@pytest.mark.parametrize("pad", sorted(_PATRONEN))
def test_elke_uitgesproken_aantalclaim_klopt_met_de_regelcatalogus(pad, verwacht):
    html = _html(pad)
    gevonden = 0
    fouten = []
    for sleutel, patroon in _PATRONEN[pad]:
        for getal in claims(html, patroon):
            gevonden += 1
            if getal != verwacht[sleutel]:
                fouten.append(f"{pad}: proza zegt {getal} waar de catalogus "
                               f"{verwacht[sleutel]} geeft ({sleutel}) -- patroon {patroon!r}")
    assert not fouten, "\n".join(fouten)
    assert gevonden >= _MINIMUM[pad], (
        f"{pad}: maar {gevonden} aantalclaims gevonden, verwacht minstens {_MINIMUM[pad]}. "
        "Of de proza is herschreven en de patronen in deze test moeten mee, of de pagina noemt "
        "haar aantallen niet meer -- in beide gevallen is deze bewaking nu stil, en dat is "
        "dezelfde fout die zij hoort te vangen.")


def test_de_bewaking_valt_om_als_de_proza_een_verkeerd_getal_noemt(verwacht):
    """Een bewaking die je niet hebt zien falen, bewaakt niets. Hier wordt de proza van
    `/wasstraat` nagebootst met één verkeerd telwoord, en getoetst dat de vergelijking dat
    opmerkt -- zonder de echte pagina aan te raken."""
    nep = "Negen deterministische regels (geen taalmodel, geen netwerk) op het register."
    gevonden = claims(nep, r"(\w+) deterministische regels")
    assert gevonden == [9]
    assert gevonden[0] != verwacht["papier"], (
        "deze test gaat ervan uit dat negen niet het echte aantal papierregels is; "
        "klopt dat niet meer, kies een ander fout getal")


def test_een_niet_telwoord_voor_het_patroon_is_geen_claim():
    """"deze deterministische regels" is geen bewering over een aantal en mag de bewaking niet
    laten omvallen -- anders wordt elke herformulering een valse fout."""
    assert claims("deze deterministische regels doen het werk",
                   r"(\w+) deterministische regels") == []
