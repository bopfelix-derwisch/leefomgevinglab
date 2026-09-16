import pytest
from fastapi.testclient import TestClient

import leefomgevinglab.geluidsmeter.api as api


def _client(monkeypatch):
    monkeypatch.setattr(api, "load_config", lambda *a, **k: api._config)
    return TestClient(api.app)


def test_prik_zonder_live_geeft_een_reproduceerbaar_antwoord(monkeypatch):
    r = _client(monkeypatch).get("/api/waterruimte?x=206800&y=474000&live=0")
    assert r.status_code == 200
    d = r.json()
    assert d["locatie"]["rd"] == [206800.0, 474000.0]
    assert d["regels"]["status"] == "overgeslagen"


def test_coordinaten_buiten_nederland_geven_400(monkeypatch):
    c = _client(monkeypatch)
    for x, y in [(-50000, 400000), (400000, 400000), (150000, 200000), (150000, 700000)]:
        r = c.get(f"/api/waterruimte?x={x}&y={y}&live=0")
        assert r.status_code == 400, f"({x},{y}) had geweigerd moeten worden"
        assert "rd" in r.json()["detail"].lower()


def test_debiet_wordt_begrensd(monkeypatch):
    d = _client(monkeypatch).get("/api/waterruimte?x=206800&y=474000&debiet=999999&live=0").json()
    assert d["voornemen"]["debiet_m3_per_uur"] == d["max_debiet"]


def test_ontbrekende_coordinaten_geven_422(monkeypatch):
    assert _client(monkeypatch).get("/api/waterruimte").status_code == 422


@pytest.mark.xfail(reason="pagina volgt in Task 10")
def test_kaartpagina_geeft_200_met_de_subnav(monkeypatch):
    r = _client(monkeypatch).get("/waterruimte")
    assert r.status_code == 200
    assert 'class="waternav"' in r.text
    assert r.text.count('aria-current="page"') == 1
    assert "/api/waterruimte" in r.text


# ---------- her-duiding op regionaal water (controller-ruling 2) ----------

def _haal_reeks(antwoorden):
    it = iter(antwoorden)

    def haal(url, params, timeout_s=25.0):
        return next(it)
    return haal


_GEEN = '{"features":[]}'
_GEM_EEN = """{"features":[{"properties":{"naam":"Brummen","ligtInProvincieNaam":"Gelderland"}}]}"""


def test_punt_op_regionaal_water_telt_de_waterschapsverordening_als_direct_werkend():
    """De regels worden vast met rijkswater=True opgehaald (voor de parallellisatie) en pas
    daarna, als het toch regionaal water blijkt, opnieuw geduid. De telling moet dan bij die
    her-duiding passen: de waterschapsverordening telt mee als 'direct', niet als 'niet van
    toepassing'."""
    from leefomgevinglab.usecases.gebruiksruimte import service

    ruw = [{"titel": "Waterschapsverordening Rijn en IJssel", "type": "Waterschapsverordening",
           "bevoegd_gezag": "Waterschap Rijn en IJssel"}]

    b = service.beeld_op_punt(210500.0, 458500.0, live=True,
                              _haal_water=_haal_reeks([_GEEN, _GEEN, _GEM_EEN]),
                              _haal_regels=lambda rd: ruw,
                              _haal_atlas=lambda x, y, straal_m: [])

    assert b["rijkswater"] is False
    regelingen = b["regels"]["regelingen"]
    assert len(regelingen) == 1
    assert regelingen[0]["type"] == "Waterschapsverordening"
    assert regelingen[0]["van_toepassing"] is True
    assert regelingen[0]["werking"] == "direct"
    assert b["regels"]["telling"] == {"direct": 1}
    assert "niet van toepassing" not in b["regels"]["telling"]
