from fastapi.testclient import TestClient

import leefomgevinglab.geluidsmeter.api as api
from leefomgevinglab.usecases import dvth


def _client(monkeypatch):
    monkeypatch.setattr(api, "load_config", lambda *a, **k: api._config)
    return TestClient(api.app)


def test_architectuur_api(monkeypatch):
    d = _client(monkeypatch).get("/api/dvth/architectuur").json()
    assert len(d["componenten"]) == len(dvth.COMPONENTEN)
    assert len(d["flows"]) == len(dvth.FLOWS)
    assert len(d["stappen"]) == 8
    assert d["casus"]["rd"] == list(dvth.CASUS["rd"])


def test_dvth_pagina(monkeypatch):
    r = _client(monkeypatch).get("/dvth")
    assert r.status_code == 200
    assert "dvth/architectuur" in r.text
