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


def test_de_api_levert_het_eindbeeld_als_doorsnede():
    d = _client().get("/api/maquette").json()
    for sleutel in ("lagen", "gebied", "processen", "handelingen", "aansluitingen", "bodem",
                     "stromen", "waarde", "herkomst", "telling"):
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


def test_de_pagina_haalt_de_doorsnede_uit_de_api_en_typt_niets_zelf():
    """Geen laagnaam, geen handeling en geen standaard in de HTML. Zou dat wel zo zijn, dan kan
    de maquette iets anders tonen dan het model zegt."""
    r = _client().get("/maquette")
    assert r.status_code == 200
    assert "/api/maquette" in r.text
    for e in eb._alle_elementen():
        naam = e.get("naam") or e.get("object")
        assert naam not in r.text, f"{naam} hoort uit de API te komen"
        assert e["architectuur"] not in r.text, "ook de uitleg komt uit de API"
    for l in eb.LAGEN:
        assert l["wat"] not in r.text


def test_de_pagina_opent_in_gewone_woorden():
    """Het doel is dat iemand zonder architectuuropleiding het begrijpt. De inleiding noemt dus
    het gebied, de gegevens, de doorsnede en de stekkerdozen -- geen informatiefuncties."""
    plat = _plat(_client().get("/maquette").text)
    for woord in ("gebied", "gegevens", "doorsnede", "stekkerdozen"):
        assert woord in plat.lower(), woord
    assert "informatiefunctie" not in plat.lower().split("in architectuurtaal")[0], (
        "de vaktaal hoort in de uitlegvelden, niet in de inleiding")


def test_de_pagina_tekent_een_herkenbaar_gebied():
    """De bovenste laag is geen tekstpaneel maar een kaart: een bedrijf, een rivier, een
    woonwijk, een meetpunt. Dat is wat de maquette concreet maakt."""
    r = _client().get("/maquette")
    for ding in ("chemiebedrijf", "lozingspunt", "woonwijk", "meetpunt", "de rivier"):
        assert ding in r.text, f"{ding} ontbreekt op de kaart"
    assert "<svg" in r.text and "viewBox" in r.text


def test_het_blok_is_uit_elkaar_te_trekken():
    """De schuif is wat de doorsnede zichtbaar maakt -- zonder haar zie je alleen de buitenkant,
    en dan is de laag met de standaarden precies zo onzichtbaar als in de werkelijkheid."""
    r = _client().get("/maquette")
    assert 'id="uitelkaar"' in r.text and 'type="range"' in r.text
    assert "Toon de doorsnede" in r.text


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


def test_elke_doorkijk_op_de_pagina_wijst_naar_een_bestaande_route():
    """De pagina belooft dat elk ding naar werkende code leidt. Een dode link breekt die belofte
    stiller dan een foutmelding."""
    routes = {r.path for r in api_mod.app.routes if hasattr(r, "path")}
    dood = sorted({e["waar"] for e in eb._alle_elementen() if e["waar"] not in routes})
    assert not dood, dood


def test_het_blok_is_zonder_muis_te_draaien():
    """Draaien is de kern van deze pagina. Kan het alleen met slepen, dan is zij voor een
    toetsenbordgebruiker niet te bedienen."""
    r = _client().get("/maquette")
    assert "ArrowLeft" in r.text and "ArrowUp" in r.text
    assert 'tabindex="0"' in r.text, "de scène moet focus kunnen krijgen"
    assert "focus-visible" in r.text
    assert "prefers-reduced-motion" in r.text


def test_een_blik_is_deelbaar_via_de_url():
    """'Kijk eens naar de doorsnede' moet een link kunnen zijn -- anders moet je uitleggen welke
    knop iemand moet indrukken."""
    r = _client().get("/maquette")
    assert "blik" in r.text and "URLSearchParams" in r.text
    for blik in ("boven", "doorsnede"):
        assert _client().get(f"/maquette?blik={blik}").status_code == 200


def test_de_pagina_laadt_geen_3d_bibliotheek():
    """CSS-transforms in plaats van WebGL: de vlakken blijven echte DOM-elementen, dus de teksten
    blijven scherp en de vensters zijn met het toetsenbord te bereiken."""
    r = _client().get("/maquette")
    assert "<script src=" not in r.text
    assert "preserve-3d" in r.text and "perspective" in r.text


def test_de_doelbeelden_verwijzen_naar_de_maquette():
    for pad in ("/dvth", "/lozing"):
        assert "/maquette" in _client().get(pad).text, f"{pad} verwijst niet naar de maquette"


def test_een_klik_op_een_veld_wordt_niet_door_de_scene_afgevangen():
    """**De bug die alle velden stilletjes brak.** De scène riep bij elke `pointerdown` meteen
    `setPointerCapture` aan om te kunnen slepen. Met een actieve pointer-capture gaat óók het
    `click`-event naar het vangende element -- de scène -- en niet naar de tegel waarop je
    drukte. Gevolg: niets in de maquette reageerde, zonder enige foutmelding.

    Niet met een test te vangen die alleen HTML leest? Jawel, op de twee eigenschappen die de
    reparatie uitmaken: vangen gebeurt pas ná een sleepdrempel, en een pointerdown op iets
    klikbaars start helemaal geen sleep. Beide zijn in de bron te zien, en als iemand ze
    weghaalt valt dit om.
    """
    r = _client().get("/maquette")
    pointerdown = r.text.split('addEventListener("pointerdown"')[1].split("});")[0]
    assert "setPointerCapture" not in pointerdown, (
        "vangen in pointerdown stuurt de klik naar de scène; vang pas als er echt gesleept wordt")
    assert ".tegel" in pointerdown and "return" in pointerdown, (
        "een pointerdown op iets klikbaars hoort geen sleep te starten")
    assert "DREMPEL" in r.text, "er hoort een sleepdrempel te zijn"


def test_de_zijkanten_tonen_wie_levert_en_wie_haalt():
    """De zijkanten stonden leeg. Links hoort te zeggen wie de gegevens maakt, rechts wie ze
    gebruikt — dat is de horizontale richting uit de doelarchitectuur."""
    r = _client().get("/maquette")
    assert "kantHtml" in r.text
    assert '"aanbod"' in r.text and '"vraag"' in r.text
    d = _client().get("/api/maquette").json()
    assert [k["id"] for k in d["kanten"]] == ["aanbod", "knooppunt", "vraag"]


def test_de_route_wordt_binnenin_het_blok_getekend():
    """De vraag was om aan de binnenkant zichtbaar te maken hoe de stroompjes door de lagen gaan
    en waar de verbindingen liggen. Dat is een snijvlak door het midden met de route erop."""
    r = _client().get("/maquette")
    assert "binnenvlakHtml" in r.text
    assert 'class="binnen"' in r.text or 'class="binnen ' in r.text
    assert "huidigeRoute" in r.text, "de route hangt aan het gekozen ding uit het gebied"


def test_de_ingang_is_het_gebied():
    """"De ingang is het gebied, een van de blokjes." Het beginpaneel moet dus naar de kaart
    wijzen en niet naar een willekeurig onderdeel."""
    plat = _plat(_client().get("/maquette").text)
    assert "Begin op de kaart" in plat
    assert "bedrijf, het lozingspunt, het meetpunt" in plat
