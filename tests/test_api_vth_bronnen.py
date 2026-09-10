from fastapi.testclient import TestClient

import leefomgevinglab.geluidsmeter.api as api
from leefomgevinglab.usecases import vth_bronnen as vb


def _client(monkeypatch):
    monkeypatch.setattr(api, "load_config", lambda *a, **k: api._config)
    return TestClient(api.app)


def test_bronnen_api_geeft_de_hele_catalogus(monkeypatch):
    d = _client(monkeypatch).get("/api/vth/bronnen").json()
    assert len(d["bronnen"]) == len(vb.BRONNEN)
    assert len(d["views"]) == 7
    assert d["overlap"] and d["dekking"] and d["lagen"]


def test_bronnen_pagina_geeft_200(monkeypatch):
    r = _client(monkeypatch).get("/vth-bronnen")
    assert r.status_code == 200
    assert "vth/bronnen" in r.text


def test_check_api_geeft_status_per_bron(monkeypatch):
    async def fake_check(bronnen=None, timeout_s=12.0, _get=None):
        return {"rev": {"status": 200, "ok": True}, "bag": {"status": None, "ok": False}}

    monkeypatch.setattr(vb, "check_endpoints", fake_check)
    d = _client(monkeypatch).get("/api/vth/bronnen/check").json()
    assert d["resultaat"]["rev"]["ok"] is True
    assert d["resultaat"]["bag"]["ok"] is False
    assert d["gecontroleerd_op"]
