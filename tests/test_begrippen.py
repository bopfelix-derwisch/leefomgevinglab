import pytest

from leefomgevinglab.connectors.base import ConnectorError
from leefomgevinglab.connectors.stelselcatalogus import StelselcatalogusConnector
from leefomgevinglab.usecases import begrippen


# ---------- connector ----------

def _conn(tmp_path, antwoord):
    c = StelselcatalogusConnector(base_url="https://x/v3", api_key="k", cache_dir=str(tmp_path))
    c.get_json = lambda url, params=None, headers=None: antwoord
    return c


_BEGRIP = {
    "_embedded": {"begrippen": [
        {"term": "Zeer kwetsbaar gebouw", "definitie": "Gebouw als bedoeld in bijlage VI, onder E.",
         "conceptschema": "http://regelgeving.omgevingswet.overheid.nl/id/conceptscheme/Regelgeving",
         "type": "http://www.w3.org/2004/02/skos/core#Concept",
         "metadata": "http://regelgeving.omgevingswet.overheid.nl/doc/2024",
         "isGerelateerd": None, "isEngerDan": None, "uitleg": None},
        {"term": "Kwetsbaar gebouw", "definitie": "Kwetsbaar gebouw als bedoeld in bijlage I Bkl.",
         "conceptschema": "http://regelgeving.omgevingswet.overheid.nl/id/conceptscheme/Regelgeving",
         "type": "http://www.w3.org/2004/02/skos/core#Concept"},
    ]},
    "page": {"number": 1, "size": 10},
}


def test_zoek_geeft_genormaliseerde_begrippen(tmp_path):
    uit = _conn(tmp_path, _BEGRIP).zoek("kwetsbaar gebouw")
    assert len(uit) == 2
    b = uit[0]
    assert b["term"] == "Zeer kwetsbaar gebouw"
    assert b["definitie"].startswith("Gebouw als bedoeld")
    assert b["conceptschema_naam"] == "Regelgeving"
    assert b["is_skos_concept"] is True


def test_relaties_worden_meegenomen_als_ze_er_zijn(tmp_path):
    antwoord = {"_embedded": {"begrippen": [
        {"term": "AandachtsgebiedExterneVeiligheid", "definitie": "x",
         "conceptschema": "http://standaarden.omgevingswet.overheid.nl/id/conceptscheme/ExterneVeiligheid",
         "isGerelateerd": ["http://x/concept/ls011", "http://x/concept/pr111"]}]}}
    b = _conn(tmp_path, antwoord).zoek("aandachtsgebied")[0]
    assert b["relaties"]["isGerelateerd"] == 2
    assert b["aantal_relaties"] == 2


def test_zonder_sleutel_faalt_de_connector_luid(tmp_path):
    c = StelselcatalogusConnector(base_url="https://x/v3", api_key=None, cache_dir=str(tmp_path))
    with pytest.raises(ConnectorError):
        c.zoek("iets")


def test_lege_uitkomst_is_gewoon_een_lege_lijst(tmp_path):
    assert _conn(tmp_path, {"_embedded": {"begrippen": []}}).zoek("bestaatniet") == []


def test_de_api_kent_geen_pageSize_bij_zoeken(tmp_path):
    """De catalogus weigert pageSize samen met zoekTerm met een 400 — niet meesturen dus."""
    gezien = {}
    c = StelselcatalogusConnector(base_url="https://x/v3", api_key="k", cache_dir=str(tmp_path))
    c.get_json = lambda url, params=None, headers=None: (gezien.update(params or {}), _BEGRIP)[1]
    c.zoek("kwetsbaar gebouw")
    assert set(gezien) == {"zoekTerm"}


# ---------- termenregister ----------

def test_elke_labterm_zegt_waar_hij_gebruikt_wordt():
    assert begrippen.TERMEN
    for t in begrippen.TERMEN:
        assert t["term"] and t["zoekterm"] and t["gebruikt_in"]
        assert t["waarom"], f"{t['term']}: geen reden waarom dit begrip ertoe doet"


def test_termen_zijn_uniek():
    ids = [t["id"] for t in begrippen.TERMEN]
    assert len(ids) == len(set(ids))


def test_de_hardgecodeerde_termen_uit_de_ketens_staan_erin():
    zoektermen = {t["zoekterm"].lower() for t in begrippen.TERMEN}
    for nodig in ("seveso-inrichting", "lozingsactiviteit", "zeer kwetsbaar gebouw"):
        assert nodig in zoektermen


def test_termen_verwijzen_naar_bestaande_pagina_s():
    geldig = {"/dvth", "/lozing", "/evruimte", "/gebruiksruimte", "/vth", "/vth-bronnen", "/balo"}
    for t in begrippen.TERMEN:
        onbekend = set(t["gebruikt_in"]) - geldig
        assert onbekend == set(), f"{t['id']}: {onbekend}"


# ---------- oplossen ----------

class _NepConnector:
    def __init__(self, treffers=None, stuk=False):
        self.treffers, self.stuk, self.aanroepen = treffers or [], stuk, []

    def zoek(self, term):
        self.aanroepen.append(term)
        if self.stuk:
            raise ConnectorError("bron plat")
        return [t for t in self.treffers if term.lower() in t["term"].lower()]


def test_oplossen_koppelt_labtermen_aan_catalogusbegrippen():
    treffers = [{"term": "Seveso-inrichting", "definitie": "d", "conceptschema_naam": "Regelgeving",
                 "relaties": {}, "aantal_relaties": 0, "is_skos_concept": True, "vindplaats": None}]
    uit = begrippen.los_op(_NepConnector(treffers), alleen=["seveso"])
    assert len(uit["begrippen"]) == 1
    b = uit["begrippen"][0]
    assert b["gevonden"] is True and b["treffers"][0]["term"] == "Seveso-inrichting"
    assert uit["telling"]["gevonden"] == 1


def test_niet_gevonden_term_wordt_als_zodanig_gemeld():
    uit = begrippen.los_op(_NepConnector([]), alleen=["seveso"])
    assert uit["begrippen"][0]["gevonden"] is False
    assert uit["telling"]["gevonden"] == 0


def test_oplossen_degradeert_als_de_catalogus_plat_ligt():
    uit = begrippen.los_op(_NepConnector(stuk=True), alleen=["seveso"])
    assert uit["status"] == "onbereikbaar"
    assert uit["begrippen"][0]["gevonden"] is False


def test_het_gat_tussen_bag_en_bkl_wordt_benoemd():
    """De kern van de integratie: onze eigen afleiding is niet de juridische definitie."""
    g = begrippen.KLOOF
    assert "BAG" in g["onze_afleiding"] and "bijlage" in g["juridisch"].lower()
    assert g["waarom_het_uitmaakt"]


# ---------- API ----------

def _client(monkeypatch):
    from fastapi.testclient import TestClient
    import leefomgevinglab.geluidsmeter.api as api
    monkeypatch.setattr(api, "load_config", lambda *a, **k: api._config)
    return TestClient(api.app)


def test_api_begrippen(monkeypatch):
    import leefomgevinglab.geluidsmeter.api as api
    monkeypatch.setattr(api, "_stelselcatalogus", lambda: _NepConnector([]))
    d = _client(monkeypatch).get("/api/begrippen").json()
    assert len(d["begrippen"]) == len(begrippen.TERMEN)
    assert d["kloof"]["waarom_het_uitmaakt"]


def test_api_enkel_begrip(monkeypatch):
    import leefomgevinglab.geluidsmeter.api as api
    treffers = [{"term": "Kwetsbaar gebouw", "definitie": "d", "conceptschema_naam": "Regelgeving",
                 "relaties": {}, "aantal_relaties": 0, "is_skos_concept": True, "vindplaats": None}]
    monkeypatch.setattr(api, "_stelselcatalogus", lambda: _NepConnector(treffers))
    d = _client(monkeypatch).get("/api/begrip?term=kwetsbaar").json()
    assert d["treffers"] and d["treffers"][0]["term"] == "Kwetsbaar gebouw"


def test_api_begrip_zonder_term(monkeypatch):
    assert _client(monkeypatch).get("/api/begrip").status_code == 422


def test_begrippen_pagina(monkeypatch):
    r = _client(monkeypatch).get("/begrippen")
    assert r.status_code == 200 and "api/begrippen" in r.text


def test_de_connector_vraagt_om_hal_en_niet_om_gewone_json(tmp_path):
    """application/json geeft een 406 bij deze API; dat mag niet stilletjes terugsluipen."""
    from leefomgevinglab.connectors import stelselcatalogus as sc
    gezien = {}
    c = sc.StelselcatalogusConnector(base_url="https://x/v3", api_key="k", cache_dir=str(tmp_path))
    c.get_json = lambda url, params=None, headers=None: (gezien.update(headers or {}), _BEGRIP)[1]
    c.zoek("x")
    assert gezien["Accept"] == "application/hal+json" == sc.ACCEPT
