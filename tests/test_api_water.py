import pytest
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


@pytest.mark.parametrize("pad,actief_label", [
    ("/gebruiksruimte", "Ruimte"),
    ("/balo", "Knelpunten"),
    ("/lozing", "Keten"),
])
def test_waterpaginas_dragen_dezelfde_subnav(monkeypatch, pad, actief_label):
    r = _client(monkeypatch).get(pad)
    assert r.status_code == 200
    assert 'class="waternav"' in r.text
    assert r.text.count('aria-current="page"') == 1
    assert f'aria-current="page">{actief_label}</a>' in r.text, (
        f"niet {actief_label!r} maar een ander lid staat op actief"
    )
    assert "__WATERNAV__" not in r.text


def test_dvth_is_geen_waterpagina_en_krijgt_de_balk_niet(monkeypatch):
    """keten-tab.html bedient ook /dvth; die hoort niet in het waterdossier."""
    r = _client(monkeypatch).get("/dvth")
    assert r.status_code == 200
    assert 'class="waternav"' not in r.text
    assert "__WATERNAV__" not in r.text, "placeholder moet leeg worden vervangen, niet blijven staan"


def test_hoofdnav_heeft_een_ingang_naar_het_waterdossier(monkeypatch):
    r = _client(monkeypatch).get("/")
    assert 'href="/water"' in r.text
    assert 'href="/gebruiksruimte"' not in r.text, "opgegaan in het dossier"


@pytest.mark.parametrize("pad", ["/water", "/waterruimte", "/gebruiksruimte", "/lozing", "/balo"])
def test_alle_waterpaginas_delen_hetzelfde_kleurenpalet(monkeypatch, pad):
    """Bevinding 11 van de eindreview: /water en /waterruimte draaiden op `--bg:#0a1420` met
    `--paneel`/`--tekst`, de rest op `--bg:#080c14` met `--panel`/`--text` — klikken van
    Overzicht naar Ruimte in dezelfde subnav veranderde zo de achtergrondkleur van de site."""
    r = _client(monkeypatch).get(pad)
    assert r.status_code == 200
    assert "--bg:#080c14" in r.text, f"{pad} gebruikt niet de meerderheidsachtergrond"
    assert "--paneel" not in r.text and "--tekst" not in r.text, (
        f"{pad} gebruikt nog het oude palet")
    assert "#0a1420" not in r.text, f"{pad} gebruikt nog de oude achtergrondkleur"
