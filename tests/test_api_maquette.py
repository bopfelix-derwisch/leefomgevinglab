"""De routes `/maquette`, `/api/maquette` en `/api/maquette/transitie`.

De pagina toont **alleen het eindbeeld**, als gebouw. De eerste versie toonde ook de transitie
door de tijd en werd daarmee te druk voor wie geen architect is; die data is niet weg maar staat
op een eigen eindpunt. Deze tests bewaken dat onderscheid, en dat de pagina haar gebouw uit de
API haalt in plaats van het zelf te tekenen.
"""
import re

from fastapi.testclient import TestClient

from leefomgevinglab.geluidsmeter import api as api_mod
from leefomgevinglab.usecases import eindbeeld_stelsel as eb


def _client():
    return TestClient(api_mod.app)


def _plat(html: str) -> str:
    """Witruimte genormaliseerd -- de HTML breekt op leeslengte af, dus een zoekterm met enkele
    spaties matcht anders niets."""
    return re.sub(r"\s+", " ", html)


def test_de_api_levert_het_eindbeeld_als_gebouw():
    d = _client().get("/api/maquette").json()
    for sleutel in ("bodemplaat", "dak", "verdiepingen", "trappenhuis", "gevels",
                     "standpunten", "herkomst", "telling"):
        assert d[sleutel], sleutel
    assert "plateaus" not in d, (
        "de pagina gaat over het eindbeeld; de transitie heeft een eigen eindpunt")


def test_de_transitie_heeft_een_eigen_eindpunt_en_is_niet_weggegooid():
    """De plateau-data is echt en gecontroleerd. Zij hoort alleen niet op dezelfde pagina, want
    dan wordt het geheel onleesbaar -- dat was de reden om te splitsen."""
    d = _client().get("/api/maquette/transitie").json()
    assert len(d["plateaus"]) == 5
    assert d["telling"]["voorzieningen_die_bewegen"] >= 3


def test_de_route_raakt_geen_bron_en_is_dus_snel():
    """Een modelstuk uit BALO; er is niets op te halen. Zou deze route een bron bevragen, dan
    hing een architectuurplaat af van de bereikbaarheid van een dienst."""
    import time
    t0 = time.perf_counter()
    assert _client().get("/api/maquette").status_code == 200
    assert time.perf_counter() - t0 < 1.0


def test_de_pagina_haalt_het_gebouw_uit_de_api_en_typt_niets_zelf():
    """Geen verdiepingsnaam, geen vraag en geen onderdeel in de HTML. Zou dat wel zo zijn, dan
    kan het gebouw iets anders tonen dan BALO zegt."""
    r = _client().get("/maquette")
    assert r.status_code == 200
    assert "/api/maquette" in r.text
    for v in eb.VERDIEPINGEN:
        assert v["naam"] not in r.text, f"verdieping {v['naam']} hoort uit de API te komen"
        assert v["wat"] not in r.text
    for q in eb.VRAGEN:
        assert q["vraag"] not in r.text, "de vragen komen uit BALO via de API"
    for o in eb.DAK["onderdelen"] + eb.BODEMPLAAT["onderdelen"]:
        assert o not in r.text


def test_de_pagina_legt_het_gebouw_uit_in_gewone_woorden():
    """Het doel is dat iemand zonder architectuuropleiding het begrijpt. Dan moeten de woorden
    die de vorm dragen -- bodemplaat, verdiepingen, dak, gevels, vensters -- er ook staan."""
    plat = _plat(_client().get("/maquette").text)
    for woord in ("bodemplaat", "verdiepingen", "dak", "gevels", "vensters"):
        assert woord in plat.lower(), woord
    assert "links wordt geleverd, rechts wordt gehaald" in plat


def test_de_pagina_zegt_dat_dit_geen_vastgesteld_beleid_is():
    """BALO v1.0 draagt zelf de status concept en het eindbeeld is 'nog in bewerking'. Een plaat
    die dat weglaat leest als besloten beleid."""
    plat = _plat(_client().get("/maquette").text)
    assert "geen vastgesteld beleid" in plat.lower()
    assert "concept" in plat.lower()
    assert "nog in bewerking" in plat


def test_de_pagina_draagt_een_herkomsttabel_die_balo_en_lab_onderscheidt():
    r = _client().get("/maquette")
    assert 'id="herkomsttabel"' in r.text
    assert "h.van" in r.text, "de herkomst komt uit de API"
    plat = _plat(r.text)
    assert "Wat uit BALO komt, en wat dit lab erbij leest" in plat


def test_het_gebouw_is_zonder_muis_te_draaien():
    """Draaien is de kern van deze pagina. Kan het alleen met slepen, dan is zij voor een
    toetsenbordgebruiker niet te bedienen."""
    r = _client().get("/maquette")
    assert "ArrowLeft" in r.text and "ArrowUp" in r.text
    assert 'tabindex="0"' in r.text, "de scène moet focus kunnen krijgen"
    assert "focus-visible" in r.text
    assert "prefers-reduced-motion" in r.text


def test_een_standpunt_is_deelbaar_via_de_url():
    """'Kijk eens van onderen' moet een link kunnen zijn -- anders moet je uitleggen welke knop
    iemand moet indrukken."""
    r = _client().get("/maquette")
    assert "standpunt" in r.text
    assert "URLSearchParams" in r.text and "replaceState" in r.text
    assert _client().get("/maquette?standpunt=bodemplaat").status_code == 200


def test_de_pagina_laadt_geen_3d_bibliotheek():
    """CSS-transforms in plaats van WebGL: de vlakken blijven echte DOM-elementen, dus de teksten
    blijven scherp en de vensters zijn met het toetsenbord te bereiken."""
    r = _client().get("/maquette")
    assert "<script src=" not in r.text
    assert "preserve-3d" in r.text and "perspective" in r.text


def test_de_doelbeelden_verwijzen_naar_de_maquette():
    for pad in ("/dvth", "/lozing"):
        assert "/maquette" in _client().get(pad).text, f"{pad} verwijst niet naar de maquette"
