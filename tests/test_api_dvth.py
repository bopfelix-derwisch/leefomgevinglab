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


def test_lozing_architectuur_api(monkeypatch):
    from leefomgevinglab.usecases import lozing
    d = _client(monkeypatch).get("/api/lozing/architectuur").json()
    assert len(d["componenten"]) == len(lozing.COMPONENTEN)
    assert d["presentatie"]["api"] == "lozing"


def test_beide_tabs_delen_het_sjabloon_met_eigen_dossier(monkeypatch):
    c = _client(monkeypatch)
    dv, lz = c.get("/dvth").text, c.get("/lozing").text
    assert "/api/dvth/architectuur" in dv and "/api/lozing/architectuur" not in dv
    assert "/api/lozing/architectuur" in lz and "/api/dvth/architectuur" not in lz
    assert "__DOSSIER__" not in dv and "__DOSSIER__" not in lz


def test_lozing_keten_api(monkeypatch):
    d = _client(monkeypatch).get("/api/lozing/keten?live=0").json()
    assert len(d["stappen"]) == 8 and d["dossier"]["id"] == "lozing"
