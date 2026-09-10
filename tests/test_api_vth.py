from fastapi.testclient import TestClient

import leefomgevinglab.geluidsmeter.api as api

VIEWS = ["Activiteit-view", "Betrokkene-view", "Verzoek-view", "Toezicht- en handhaving-view",
         "Incident-view", "Locatie-view", "Zaak- en Document-view"]


def _client(monkeypatch):
    monkeypatch.setattr(api, "load_config", lambda *a, **k: api._config)
    return TestClient(api.app)


def test_vth_pagina_geeft_200(monkeypatch):
    assert _client(monkeypatch).get("/vth").status_code == 200


def test_vth_pagina_bevat_alle_zeven_views(monkeypatch):
    html = _client(monkeypatch).get("/vth").text
    ontbreekt = [v for v in VIEWS if v not in html]
    assert ontbreekt == []


def test_vth_pagina_verwijst_naar_de_bron(monkeypatch):
    html = _client(monkeypatch).get("/vth").text
    assert "geonovum.github.io/vth-cim-flo" in html
    assert "github.com/Geonovum/vth-cim-flo" in html
