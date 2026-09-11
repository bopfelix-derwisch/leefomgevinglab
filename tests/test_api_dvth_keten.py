from fastapi.testclient import TestClient

import leefomgevinglab.geluidsmeter.api as api


def _client(monkeypatch):
    monkeypatch.setattr(api, "load_config", lambda *a, **k: api._config)
    return TestClient(api.app)


def test_keten_api_zonder_live(monkeypatch):
    d = _client(monkeypatch).get("/api/dvth/keten?live=0").json()
    assert [s["nr"] for s in d["stappen"]] == list(range(1, 9))
    assert d["live"] is False
    assert d["dekking"]["geraakt"] > 0
    assert d["document"]["kenmerk"]


def test_keten_api_geeft_straal_door(monkeypatch):
    d = _client(monkeypatch).get("/api/dvth/keten?live=0&straal=2500").json()
    assert d["straal_m"] == 2500


def test_keten_api_begrenst_de_straal(monkeypatch):
    # niet ongelimiteerd de publieke bronnen laten bevragen
    d = _client(monkeypatch).get("/api/dvth/keten?live=0&straal=999999").json()
    assert d["straal_m"] <= 5000
