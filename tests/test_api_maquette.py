"""De routes `/maquette` en `/api/maquette`.

De inhoudelijke bewaking (bron tegenover lezing, afgeleide tellingen, gaps) staat in
`tests/test_maquette.py`. Hier gaat het om de pagina: haalt zij haar model uit de API, en maakt
zij het verschil tussen bron en eigen lezing zichtbaar in plaats van het in de code te laten?
"""
import re

from fastapi.testclient import TestClient

from leefomgevinglab.geluidsmeter import api as api_mod
from leefomgevinglab.usecases import maquette as mq


def _client():
    return TestClient(api_mod.app)


def _plat(html: str) -> str:
    """Witruimte genormaliseerd -- de HTML breekt op leeslengte af, dus een zoekterm met enkele
    spaties matcht anders niets. Dezelfde valkuil als bij de proza-bewaking op `/toezicht`."""
    return re.sub(r"\s+", " ", html)


def test_het_model_komt_volledig_uit_de_api():
    d = _client().get("/api/maquette").json()
    for sleutel in ("lagen", "plateaus", "voorzieningen", "functies", "waardestromen",
                     "beslismomenten", "transitievragen", "vaststaand", "herkomst", "telling"):
        assert d[sleutel], sleutel


def test_de_route_raakt_geen_bron_en_is_dus_snel():
    """Dit is een modelstuk uit twee documenten; er is niets op te halen. Zou deze route een bron
    bevragen, dan zou een architectuurplaat afhangen van de bereikbaarheid van een dienst."""
    import time
    t0 = time.perf_counter()
    assert _client().get("/api/maquette").status_code == 200
    assert time.perf_counter() - t0 < 1.0


def test_de_pagina_haalt_alles_uit_de_api_en_typt_niets_zelf():
    """Geen voorzieningnaam, geen fasetekst en geen jaartal van een plateau in de HTML. Zou dat
    wel zo zijn, dan kan de plaat iets anders tonen dan het model zegt -- en op een pagina die
    bron en lezing uit elkaar houdt is dat precies de fout die zij wil voorkomen."""
    r = _client().get("/maquette")
    assert r.status_code == 200
    assert "/api/maquette" in r.text
    for v in mq.VOORZIENINGEN:
        assert v["naam"] not in r.text, f"{v['naam']} hoort uit de API te komen"
    for p in mq.PLATEAUS:
        assert p["stelselstand"] not in r.text, f"de stand van {p['jaren']} hoort uit de API"
    for f in mq.FUNCTIES:
        assert f["plek_2037"] not in r.text, f"{f['id']} hoort uit de API te komen"


def test_de_pagina_noemt_de_architectuurbegrippen_waar_de_vorm_op_rust():
    """Plateau en gap zijn geen zelfbedachte beelden maar de staande woordenschat van ArchiMate
    en TOGAF. Een lezer uit die wereld moet dat herkennen, anders lijkt de 3D versiering."""
    plat = _plat(_client().get("/maquette").text)
    assert "ArchiMate" in plat and "TOGAF" in plat
    assert "Plateau" in plat and "Gap" in plat
    assert "transitiearchitectuur" in plat


def test_de_pagina_zegt_dat_dit_geen_vastgesteld_beleid_is():
    """De bron zegt het drie keer; een plaat die dat weglaat leest als besloten beleid. Op een
    publieke pagina over andermans architectuur is dat het ergste wat zij kan doen."""
    plat = _plat(_client().get("/maquette").text)
    assert "geen vastgesteld beleid" in plat.lower()
    assert "werkhypothese" in plat
    assert "voorstel ter toetsing" in plat
    assert "nog te besluiten" in plat


def test_de_pagina_draagt_een_herkomsttabel_die_bron_en_lab_onderscheidt():
    r = _client().get("/maquette")
    assert 'id="herkomsttabel"' in r.text
    assert "h.van" in r.text, "de herkomst komt uit de API"
    plat = _plat(r.text)
    assert "Wat uit de bron komt, en wat dit lab erbij leest" in plat


def test_de_maquette_is_zonder_muis_te_gebruiken():
    """De tijdas is de kern van de pagina. Zou reizen alleen met slepen kunnen, dan is zij voor
    een toetsenbordgebruiker niet te bedienen -- en de tijdbalk is dan decoratie."""
    r = _client().get("/maquette")
    assert "ArrowRight" in r.text and "ArrowLeft" in r.text
    assert "focus-visible" in r.text
    assert 'aria-current="step"' in r.text, "de tijdbalk hoort te zeggen waar je staat"
    assert "prefers-reduced-motion" in r.text


def test_de_pagina_laadt_geen_3d_bibliotheek():
    """CSS-transforms in plaats van WebGL: de blokken blijven echte DOM-elementen, dus de labels
    blijven scherp en zijn met het toetsenbord te bereiken. Een bibliotheek zou dat alle drie
    opgeven voor een beeld dat niet beter wordt."""
    r = _client().get("/maquette")
    assert "<script src=" not in r.text, "geen externe bibliotheek op deze pagina"
    assert "preserve-3d" in r.text and "perspective" in r.text


def test_de_doelbeelden_verwijzen_naar_de_maquette():
    """Bob's vraag was om dit bij doelbeeld VTH te zetten. Zonder link vanaf /dvth is de pagina
    niet te vinden."""
    for pad in ("/dvth", "/lozing"):
        r = _client().get(pad)
        assert '/maquette' in r.text, f"{pad} verwijst niet naar de maquette"
