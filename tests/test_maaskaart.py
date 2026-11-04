"""De kaart: klopt de geometrie, en blijft zichtbaar waaróp elke koppeling rust?

Het tweede is waarom deze pagina bestaat. Vier lagen op één kaart ziet er overtuigender uit dan
de werkelijkheid is; wat haar eerlijk houdt is dat elke stip meedraagt hoe zij aan haar plek en
haar identiteit komt.
"""
import json
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from leefomgevinglab.geluidsmeter.api import app
from leefomgevinglab.usecases import maaskaart as mk
from leefomgevinglab.usecases import water_hub as wh
from leefomgevinglab.usecases.kmg import toerekening

D = Path("/mnt/nvme/geluidsmeter/data/external/wkp")
# Grenzen van het RD-stelsel binnen Nederland; een coördinaat erbuiten is geen RD maar iets anders.
RD = (0, 280_000, 300_000, 630_000)


@pytest.fixture(scope="module")
def kaart():
    k = mk.laad_kaart()
    if not k.get("beschikbaar"):
        pytest.skip(k["reden"])
    return k


@pytest.fixture(scope="module")
def b(kaart):
    return mk.beeld(overzicht_pad=str(D / "kmg_overzicht.json"),
                    metingen_pad=str(D / "metingen_2025.json"))


def _client(monkeypatch):
    monkeypatch.setattr("leefomgevinglab.geluidsmeter.api._config", {}, raising=False)
    return TestClient(app)


# --- de geometrie --------------------------------------------------------------------------

def test_de_kaart_ligt_in_rd_en_niet_in_graden(kaart):
    x0, y0, x1, y1 = kaart["bbox"]
    assert RD[0] <= x0 < x1 <= RD[1]
    assert RD[2] <= y0 < y1 <= RD[3]


def test_kust_en_territoriaal_water_staan_niet_op_de_kaart(kaart):
    """Met het territoriale water erbij wordt de rivier zelf een streepje: dat blok is
    tientallen kilometers breed en rekt het kader tot de kaart onleesbaar is."""
    categorieen = {str(w.get("categorie")) for w in kaart["vlakken"] + kaart["lijnen"]}
    assert not (categorieen & {"3", "5"})


def test_de_kaart_is_klein_genoeg_voor_een_browser():
    p = D / "maaskaart.json"
    if not p.exists():
        pytest.skip("kaartbestand ontbreekt")
    assert p.stat().st_size < 400_000, "de volle geometrie is ruim 10 MB; dit hoort vereenvoudigd"


def test_elke_vorm_draagt_haar_code_en_naam(kaart):
    for w in kaart["vlakken"] + kaart["lijnen"]:
        assert w["code"] and w["naam"]
        assert w["geometrie"]["type"] in (
            "Polygon", "MultiPolygon", "LineString", "MultiLineString")


# --- de stroomrichting ---------------------------------------------------------------------

def test_bovenstrooms_bevat_het_waterlichaam_zelf():
    """Een lozing op hetzelfde waterlichaam telt mee; dat is dezelfde grofmazigheid als in
    het toerekeningsmodel, en de kaart hoort hem niet stilletjes anders te doen."""
    assert "NL91ZM" in mk.bovenstrooms_van("NL91ZM")


def test_bovenstrooms_volgt_exact_het_toerekeningsmodel():
    for code, _naam in toerekening.STROOMVOLGORDE:
        verwacht = [c for c, _n in toerekening.STROOMVOLGORDE
                    if toerekening.is_bovenstrooms(c, code)]
        assert mk.bovenstrooms_van(code) == verwacht


def test_het_bovenste_waterlichaam_heeft_alleen_zichzelf():
    assert mk.bovenstrooms_van("NL91BOM") == ["NL91BOM"]


# --- de lagen en hun grondslag ----------------------------------------------------------------

def test_elke_stip_zegt_waarop_haar_koppeling_rust(b):
    for rij in b["meetpunten"] + b["vergunningen"] + b["zuiveringen"]:
        assert rij["grondslag"] in mk.GRONDSLAG, rij


def test_alleen_de_meetpunten_hangen_op_een_code(b):
    """Dat is de bevinding van dit hele dossier, hier als eigenschap van de kaart."""
    assert all(m["grondslag"] == "code" for m in b["meetpunten"])
    assert all(v["grondslag"] != "code" for v in b["vergunningen"] + b["zuiveringen"])


def test_zuiveringen_staan_apart_van_de_vergunningen(b):
    """Achter zo'n punt zit een hele lozingsroute die nergens geregistreerd staat."""
    assert b["zuiveringen"], "het Maasregister bevat rioolwaterzuiveringen"
    namen = " ".join(z["naam"] or "" for z in b["zuiveringen"]).upper()
    assert "WATERSCHAP" in namen
    assert not any("WATERSCHAPSBEDRIJF" in (v["naam"] or "").upper() for v in b["vergunningen"])


def test_de_meetpunten_dragen_een_coordinaat_en_hun_uitkomst(b):
    assert b["meetpunten"]
    for m in b["meetpunten"]:
        assert m["rd"] and RD[0] <= m["rd"][0] <= RD[1]
        assert m["waterlichaam"]
        assert isinstance(m["stoffen"], list)


def test_elke_vergunning_ligt_binnen_rd_of_heeft_geen_plek(b):
    for v in b["vergunningen"] + b["zuiveringen"]:
        if v["rd"] is None:
            assert v["grondslag"] == "geen"
        else:
            assert RD[0] <= v["rd"][0] <= RD[1] and RD[2] <= v["rd"][1] <= RD[3]


# --- wat de kaart over zichzelf zegt ------------------------------------------------------------

def test_het_voorbehoud_komt_uit_de_data_en_niet_uit_een_vaste_zin(b, kaart):
    v = b["voorbehoud"]
    assert str(kaart["telling"]["in_district"]) in v["geometrie"]
    assert str(kaart["telling"]["vlakken"] + kaart["telling"]["lijnen"]) in v["geometrie"]
    assert str(int(kaart["tolerantie_m"])) in v["vereenvoudigd"]


def test_de_kaart_zegt_dat_de_stroomvolgorde_een_labkeuze_is(b):
    assert "keuze van dit lab" in b["voorbehoud"]["stroomvolgorde"]


def test_het_dossier_verantwoordt_deze_pagina():
    lid = wh.lid("kaartvier")
    assert lid["pad"] == "/maaskaart"
    assert any("stroomvolgorde" in s for s in lid["synthetisch"])


# --- de pagina ---------------------------------------------------------------------------------

def test_de_pagina_geeft_200_met_de_subnav(monkeypatch):
    r = _client(monkeypatch).get("/maaskaart")
    assert r.status_code == 200
    assert 'class="waternav"' in r.text
    assert r.text.count('aria-current="page"') == 1
    assert "__WATERNAV__" not in r.text
    assert "/api/maaskaart" in r.text


def test_de_pagina_gebruikt_geen_achtergrondkaart(monkeypatch):
    """Alleen tekenen wat uit een benoemde bron komt: geen tegellaag, geen externe kaartscripts."""
    h = _client(monkeypatch).get("/maaskaart").text.lower()
    for vreemd in ("maplibre", "leaflet", "openstreetmap", "tile", "basemap"):
        assert vreemd not in h, f"onverwachte kaartafhankelijkheid: {vreemd}"


def test_een_ontbrekend_kaartbestand_zegt_hoe_je_het_bouwt():
    d = mk.beeld(kaart_pad="/bestaat/niet/maaskaart.json")
    assert d["beschikbaar"] is False and "scripts/20" in d["reden"]
