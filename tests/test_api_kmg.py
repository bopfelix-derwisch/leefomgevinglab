import pytest
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


@pytest.mark.xfail(reason="pagina volgt in Task 7", strict=True)
def test_pagina_geeft_200_met_de_subnav(monkeypatch):
    r = _client(monkeypatch).get("/kmg")
    assert r.status_code == 200
    assert 'class="waternav"' in r.text
    assert r.text.count('aria-current="page"') == 1
    assert "__WATERNAV__" not in r.text
    assert "/api/kmg" in r.text


def test_het_dossier_heeft_nu_zes_leden():
    assert len(wh.LEDEN) == 6
    assert wh.lid("kmg")["pad"] == "/kmg"


def test_het_nieuwe_lid_verantwoordt_zijn_bronnen():
    l = wh.lid("kmg")
    assert "Waterkwaliteitsportaal" in " ".join(l["live"] + l["synthetisch"])
