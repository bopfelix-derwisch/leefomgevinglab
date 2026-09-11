import pytest

from leefomgevinglab.usecases.evruimte import bronnen, gebied, oordeel, service


# ---------- gebied ----------

def test_locaties_omvatten_rotterdam_en_gouda():
    gemeenten = {l["gemeente"] for l in gebied.LOCATIES.values()}
    assert "Rotterdam" in gemeenten and "Gouda" in gemeenten
    # twee plekken in dezelfde gemeente, zodat zichtbaar wordt dat het per plek verschilt
    assert sum(1 for l in gebied.LOCATIES.values() if l["gemeente"] == "Rotterdam") >= 2


def test_drie_contouren_van_groot_naar_klein():
    stralen = [c["straal_m"] for c in gebied.CONTOUREN]
    assert stralen == sorted(stralen, reverse=True)
    assert gebied.grootste_straal() == max(stralen)


def test_elk_gebruiksdoel_zit_in_precies_een_klasse():
    alle = [d for doelen in gebied.KWETSBAARHEID.values() for d in doelen]
    assert len(alle) == len(set(alle))
    assert "onderwijsfunctie" in gebied.KWETSBAARHEID["zeer kwetsbaar"]
    assert "woonfunctie" in gebied.KWETSBAARHEID["kwetsbaar"]


def test_elke_klasse_wordt_uitgelegd():
    assert set(gebied.KLASSE_UITLEG) == set(gebied.KWETSBAARHEID)


# ---------- filters ----------

def test_fes_filter_bevat_dwithin_op_het_punt():
    f = bronnen.fes_filter(85500, 434500, 1500)
    assert "DWithin" in f and "85500 434500" in f and "1500" in f
    assert "EPSG::28992" in f


def test_fes_filter_kan_op_gebruiksdoel_filteren():
    f = bronnen.fes_filter(1, 2, 100, "onderwijsfunctie")
    assert "PropertyIsLike" in f and "*onderwijsfunctie*" in f and "fes:And" in f


def test_filter_zonder_gebruiksdoel_heeft_geen_and():
    assert "fes:And" not in bronnen.fes_filter(1, 2, 100)


# ---------- oordeel ----------

def _tel(zk_explosie=0, zk_gif=0, kw_gif=0):
    return {"explosieaandachtsgebied": {"zeer kwetsbaar": zk_explosie, "kwetsbaar": 0,
                                        "beperkt kwetsbaar": 0},
            "brandaandachtsgebied": {"zeer kwetsbaar": 0, "kwetsbaar": 0, "beperkt kwetsbaar": 0},
            "gifwolkaandachtsgebied": {"zeer kwetsbaar": zk_gif, "kwetsbaar": kw_gif,
                                       "beperkt kwetsbaar": 0}}


def test_zeer_kwetsbaar_in_het_explosiegebied_blokkeert():
    uit = oordeel.beoordeel(_tel(zk_explosie=1), {})
    assert uit["antwoord"] == "nee, tenzij" and uit["blokkades"]
    assert "explosieaandachtsgebied" in uit["blokkades"][0]["contour"]


def test_zeer_kwetsbaar_in_het_gifwolkgebied_weegt_maar_blokkeert_niet():
    uit = oordeel.beoordeel(_tel(zk_gif=4), {})
    assert uit["antwoord"] == "ja, mits" and not uit["blokkades"]
    assert any("gifwolk" in w["reden"] for w in uit["wegingen"])


def test_lege_omgeving_geeft_gewoon_ja():
    assert oordeel.beoordeel(_tel(), {})["antwoord"] == "ja"


def test_bestaande_risicobronnen_wegen_mee():
    uit = oordeel.beoordeel(_tel(), {"risicovolle activiteiten": 27})
    assert any("27" in w["reden"] for w in uit["wegingen"])
    assert any("stapelen" in w["toelichting"] for w in uit["wegingen"])


def test_oordeel_is_als_indicatief_gemarkeerd():
    assert oordeel.beoordeel(_tel(), {})["indicatief"] is True


# ---------- service ----------

def test_beeld_zonder_live_telt_niets_maar_valt_niet_om():
    b = service.beeld("gouda", live=False)
    assert b["live"] is False
    assert all(v is None for k in b["tellingen"] for v in b["tellingen"][k].values())
    assert b["oordeel"]["antwoord"]
    assert all(x["status"] == "overgeslagen" for x in b["bronnen"])


def test_beeld_geeft_wgs84_voor_de_kaart():
    b = service.beeld("botlek", live=False)
    lon, lat = b["locatie"]["wgs84"]
    assert 3 < lon < 8 and 50 < lat < 54
    assert all(len(l["wgs84"]) == 2 for l in b["locaties"])


def test_onbekende_locatie_faalt_luid():
    with pytest.raises(KeyError):
        service.beeld("atlantis", live=False)


def test_beeld_degradeert_als_de_bronnen_wegvallen():
    def kapot(*a, **kw):
        raise OSError("geen netwerk")

    b = service.beeld("botlek", live=True, _post=kapot, _get=kapot, _haal_regels=kapot)
    assert b["oordeel"]["antwoord"]
    assert any(x["status"] == "onbereikbaar" for x in b["bronnen"])
    assert b["regels"]["status"] == "onbereikbaar"


def test_regelduiding_is_voor_externe_veiligheid_en_niet_voor_water():
    tekst = service.DUIDING_EV["Waterschapsverordening"][0]
    assert "lozing" in tekst and service.DUIDING_EV["Waterschapsverordening"][1] is False
    assert "aandachtsgebied" in service.DUIDING_EV["Omgevingsplan"][0]


def test_de_gedeelde_regelsmodule_gebruikt_de_meegegeven_tabel():
    from leefomgevinglab.usecases.gebruiksruimte import regels as gr
    uit = gr.duiding({"type": "Omgevingsplan", "titel": "x"}, rijkswater=True,
                     tabel=service.DUIDING_EV)
    assert "aandachtsgebied" in uit["betekenis"]
    water = gr.duiding({"type": "Omgevingsplan", "titel": "x"}, rijkswater=True)
    assert uit["betekenis"] != water["betekenis"]


# ---------- API ----------

def _client(monkeypatch):
    from fastapi.testclient import TestClient
    import leefomgevinglab.geluidsmeter.api as api
    monkeypatch.setattr(api, "load_config", lambda *a, **k: api._config)
    return TestClient(api.app)


def test_api_geeft_het_beeld(monkeypatch):
    d = _client(monkeypatch).get("/api/evruimte?locatie=europoort&live=0").json()
    assert d["locatie"]["gemeente"] == "Rotterdam" and d["oordeel"]["antwoord"]
    assert len(d["contouren"]) == 3


def test_api_onbekende_locatie(monkeypatch):
    assert _client(monkeypatch).get("/api/evruimte?locatie=atlantis&live=0").status_code == 404


def test_api_pagina(monkeypatch):
    r = _client(monkeypatch).get("/evruimte")
    assert r.status_code == 200 and "api/evruimte" in r.text


def test_er_is_een_locatie_die_de_harde_grens_laat_zien():
    """Zonder zo'n voorbeeld blijft de blokkade een tak code die nooit wordt getoond."""
    assert "gouda_school" in gebied.LOCATIES
    assert "illustratie" in gebied.LOCATIES["gouda_school"]["naam"].lower()


def test_kaartlagen_zijn_gesleuteld_op_de_contoursoort():
    """De viewer zoekt de REV-laag op de soort van de contour; anders blijft de kaart leeg."""
    assert set(bronnen.REV_AANDACHTSGEBIEDEN) == {c["soort"] for c in gebied.CONTOUREN}


def test_live_beeld_levert_een_laag_per_contour():
    def nep_get(url, params, **kw):
        if "outputFormat" in params:
            return '{"type":"FeatureCollection","features":[]}'
        return '<x numberMatched="0"/>'

    b = service.beeld("botlek", live=True, _post=lambda *a, **k: '<x numberMatched="0"/>',
                      _get=nep_get, _haal_regels=lambda rd: [])
    assert set(b["lagen"]) == {c["soort"] for c in gebied.CONTOUREN}
