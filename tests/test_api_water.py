from fastapi.testclient import TestClient

import leefomgevinglab.geluidsmeter.api as api
from leefomgevinglab.usecases import water_hub as wh


def _client(monkeypatch):
    monkeypatch.setattr(api, "load_config", lambda *a, **k: api._config)
    return TestClient(api.app)


def test_hub_api_geeft_leden_lijnen_en_dekking(monkeypatch):
    d = _client(monkeypatch).get("/api/water/hub").json()
    assert len(d["leden"]) == len(wh.LEDEN)
    assert len(d["lijnen"]) == 3
    assert d["dekking"]
    assert d["atlas"]["url"].startswith("https://")


def test_waterpagina_geeft_200_en_haalt_de_hub_op(monkeypatch):
    r = _client(monkeypatch).get("/water")
    assert r.status_code == 200
    assert "/api/water/hub" in r.text


def test_waterpagina_bevat_de_subnav_met_actief_overzicht(monkeypatch):
    r = _client(monkeypatch).get("/water")
    assert 'class="waternav"' in r.text
    assert r.text.count('aria-current="page"') == 1
    assert "__WATERNAV__" not in r.text, "placeholder is niet vervangen"
