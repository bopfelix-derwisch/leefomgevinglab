from fastapi.testclient import TestClient

import leefomgevinglab.geluidsmeter.api as api
from leefomgevinglab.usecases import water_hub as wh


def _client(monkeypatch):
    monkeypatch.setattr(api, "load_config", lambda *a, **k: api._config)
    return TestClient(api.app)


def test_meetpunten_endpoint(monkeypatch):
    r = _client(monkeypatch).get("/api/kmg/meetpunten")
    assert r.status_code == 200
    assert isinstance(r.json(), list)


def test_onbekend_meetpunt_geeft_404(monkeypatch):
    r = _client(monkeypatch).get("/api/kmg?meetpunt=BESTAAT_NIET&live=0")
    assert r.status_code == 404


def test_pagina_geeft_200_met_de_subnav(monkeypatch):
    r = _client(monkeypatch).get("/kmg")
    assert r.status_code == 200
    assert 'class="waternav"' in r.text
    assert r.text.count('aria-current="page"') == 1
    assert "__WATERNAV__" not in r.text
    assert "/api/kmg" in r.text


def test_de_pagina_stelt_niet_vast_wie_een_overschrijding_teweegbrengt(monkeypatch):
    """De harde regel uit spec 5.3, bewaakt op de plek waar de woorden bij een lezer komen.

    Deze test bestond niet terwijl CLAUDE.md beweerde van wel. De bestaande woordtests zitten op
    het toerekeningsmodel en op de proclaimertekst; de HTML -- de enige laag die de lezer echt
    ziet -- was onbewaakt.
    """
    h = _client(monkeypatch).get("/kmg").text.lower()
    assert "veroorzaakt door" not in h
    # Een ontkenning als "niet dat zij heeft bijgedragen" is juist gewenst, en met een deelstring
    # niet van een bewering te onderscheiden -- daarom toetsen we niet op die woorden, maar erop
    # dat de pagina het voorbehoud zélf uitspreekt. Vermijden is niet genoeg.
    assert "bovengrens" in h
    assert "kan bijdragen" in h
    assert "nooit een vaststelling" in h


def test_het_dossier_kent_de_twee_nieuwe_leden():
    """Niet alleen tellen maar benoemen: een telling blijft kloppen als een lid vervangen wordt."""
    assert wh.lid("kmg")["pad"] == "/kmg"
    assert wh.lid("model")["pad"] == "/watermodel"


def test_het_nieuwe_lid_verantwoordt_zijn_bronnen():
    l = wh.lid("kmg")
    assert "Waterkwaliteitsportaal" in " ".join(l["live"] + l["synthetisch"])


def test_de_informatiemodelpagina_geeft_200_met_de_subnav(monkeypatch):
    r = _client(monkeypatch).get("/watermodel")
    assert r.status_code == 200
    assert 'class="waternav"' in r.text
    assert r.text.count('aria-current="page"') == 1
    assert "__WATERNAV__" not in r.text
    # De cijfers worden live opgehaald; de pagina mag ze niet hardcoderen.
    assert "/api/kmg/overzicht" in r.text

