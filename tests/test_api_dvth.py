import re

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


def _header_nav(html: str) -> str:
    """De kale header-<nav> (geen class) — de waterspecifieke subnav heeft class="waternav"
    en staat er los van; die moet deze check niet raken."""
    m = re.search(r"<nav>(.*?)</nav>", html, re.S)
    assert m, "geen kale <nav> gevonden in de header"
    return m.group(1)


def test_keten_tabs_wijzen_naar_elkaars_tegenhanger_niet_naar_zichzelf(monkeypatch):
    """/dvth en /lozing zijn elkaars spiegeldossier; de header moet naar de ander wijzen,
    nooit naar de eigen pagina, en de waterspecifieke nav hoort hier niet thuis."""
    c = _client(monkeypatch)
    dv, lz = _header_nav(c.get("/dvth").text), _header_nav(c.get("/lozing").text)

    assert 'href="/lozing">Doelbeeld lozing</a>' in dv
    assert 'href="/dvth">Doelbeeld D-VTH</a>' not in dv

    assert 'href="/dvth">Doelbeeld D-VTH</a>' in lz
    assert 'href="/lozing">Doelbeeld lozing</a>' not in lz

    for header in (dv, lz):
        assert 'href="/water"' not in header
        assert 'href="/gebruiksruimte"' not in header
        assert "__KRUISNAV__" not in header
