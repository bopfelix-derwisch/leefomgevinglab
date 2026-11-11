"""De vergelijking van drie modellen: kloppen de tellingen, en blijft het onderscheid staan?

De kern van deze pagina is één stelling — een informatiemodel is geen datamodel — en die
stelling valt zodra de drie lagen als varianten van elkaar worden gepresenteerd. Deze tests
bewaken dat onderscheid, en dat elk getal op de pagina uit een bron komt die genoemd wordt.
"""
import pytest
from fastapi.testclient import TestClient

from leefomgevinglab.geluidsmeter.api import app
from leefomgevinglab.usecases import modellen as mo


@pytest.fixture(scope="module")
def a():
    return mo.analyse()


def _client(monkeypatch):
    monkeypatch.setattr("leefomgevinglab.geluidsmeter.api._config", {}, raising=False)
    return TestClient(app)


# --- het onderscheid ------------------------------------------------------------------------

def test_de_drie_lagen_zijn_van_verschillende_soort(a):
    """Zodra twee lagen dezelfde soort krijgen, is de stelling van deze pagina weg."""
    soorten = [l["soort"] for l in a["lagen"]]
    assert len(set(soorten)) == 3
    assert "conceptueel" in soorten and "fysiek" in soorten


def test_elke_laag_zegt_ook_waar_zij_niets_over_zegt(a):
    """Dát is wat een laag van een andere soort onderscheidt, niet wat zij wél vastlegt."""
    for l in a["lagen"]:
        assert l["legt_vast"] and l["zegt_niets_over"] and l["vorm"] and l["toetsbaar"]


def test_alleen_het_conceptuele_model_is_niet_toetsbaar(a):
    cim = next(l for l in a["lagen"] if l["id"] == "cim")
    assert cim["toetsbaar"].startswith("nee")
    assert all(l["toetsbaar"].startswith("ja") for l in a["lagen"] if l["id"] != "cim")


def test_elke_laag_heeft_een_bron_met_houder_en_versie(a):
    for l in a["lagen"]:
        b = a["bronnen"][l["id"]]
        assert b["naam"] and b["houder"] and b["versie"] and b["voluit"]


# --- de vertalingen -------------------------------------------------------------------------

def test_elk_begrip_wordt_in_alle_drie_de_modellen_geplaatst(a):
    for v in a["vertalingen"]:
        assert v["begrip"] and v["cim"] and v["imev"] and v["gir"]
        assert v["les"], f"{v['begrip']} zonder les is een tabelrij zonder punt"


def test_de_vergunning_is_in_geen_van_beide_een_entiteit_maar_wel_in_een_een_gegeven(a):
    """Deze rij stond eerst fout op de pagina: IMEV zou de vergunning niet kennen.

    Natellen in het schema wees uit dat 44 objecttypen het vergunningnummer, de datum en de
    plicht als veld dragen. De bevinding is dus niet "het begrip ontbreekt in beide" maar de
    asymmetrie: IMEV bewaart de identificatie, GIR laat hem vallen. De test bewaakt dat de
    oude, te stellige formulering niet terugkomt.
    """
    v = next(x for x in a["vertalingen"] if "mag dit bedrijf" in x["begrip"])
    assert "komt niet voor" not in v["imev"], "de weerlegde bewering staat terug op de pagina"
    assert "basisVergunningNummer" in v["imev"]
    assert str(a["telling"]["imev_met_vergunningnummer"]) in v["imev"]
    assert "buiten scope" in v["gir"]


def test_bevoegd_gezag_is_in_gir_een_query_en_geen_relatie(a):
    v = next(x for x in a["vertalingen"] if "bevoegd gezag" in x["begrip"])
    assert "GEO-query" in v["gir"]
    assert "niet op historie" in v["les"] or "reproduceerbaar" in v["les"]


# --- de overlap tussen de twee registers ----------------------------------------------------

def test_elk_overlapbegrip_zegt_wat_beide_registers_ervan_vastleggen(a):
    for o in a["overlap"]:
        assert o["begrip"] and o["gir"] and o["imev"]
        assert o["waarom"], f"{o['begrip']} zonder onderbouwing is een oordeel zonder grond"


def test_joinbaarheid_is_een_van_drie_uitkomsten(a):
    """`deels` is geen `ja`: te verbinden via een tussentabel is geen gedeelde sleutel."""
    for o in a["overlap"]:
        assert o["join"] in ("ja", "deels", "nee"), o["begrip"]


def test_de_joinbare_begrippen_leunen_alle_op_een_basisregistratie(a):
    """Dit is de bevinding. Niets wat de twee registers zelf afspraken, verbindt ze."""
    buiten = ("KvK", "handelsregister", "BAG")
    joinbaar = [o for o in a["overlap"] if o["join"] == "ja"]
    assert joinbaar, "zonder joinbare begrippen is de analyse leeg"
    for o in joinbaar:
        tekst = o["gir"] + o["imev"] + o["waarom"]
        assert any(x in tekst for x in buiten), \
            f"{o['begrip']} heet joinbaar zonder sleutel van buiten te noemen"


def test_de_meeste_begrippen_zijn_niet_te_joinen(a):
    """Zou dit kantelen, dan is de boodschap van de sectie omgekeerd."""
    t = a["telling"]
    assert t["join_nee"] > t["join_ja"]
    assert t["join_ja"] + t["join_deels"] + t["join_nee"] == len(a["overlap"])


def test_bevoegd_gezag_is_in_beide_registers_iets_anders(a):
    o = next(x for x in a["overlap"] if "bevoegd gezag" in x["begrip"])
    assert o["join"] == "nee"
    assert "OIN" in o["gir"] and "enum" in o["imev"]


def test_de_vergunning_is_eenzijdig_vastgelegd(a):
    o = next(x for x in a["overlap"] if x["begrip"] == "De vergunning")
    assert o["join"] == "nee"
    assert "basisVergunningNummer" in o["imev"]
    assert "niets" in o["gir"] or "buiten scope" in o["gir"]


def test_imev_eist_een_reden_bij_een_ontbrekende_waarde_en_gir_niet(a):
    """De zekerheid-per-veld uit het waterdossier, hier als standaard aangetroffen."""
    o = next(x for x in a["overlap"] if "ontbrekende waarde" in x["begrip"])
    assert "geenWaardeReden" in o["imev"]
    assert o["gir"].strip() == "NULL"
    for reden in ("gegevenInTransitie", "nietVanToepassing", "waardeOnbekend"):
        assert reden in o["imev"], reden


def test_de_pagina_toont_de_overlap_en_de_joinbaarheid(monkeypatch):
    h = _client(monkeypatch).get("/modellen").text
    assert 'id="overlap"' in h and 'id="joinbalk"' in h
    assert "joinen" in h, "de sectie moet de vraag benoemen die zij beantwoordt"


# --- de bevindingen en hun herkomst ----------------------------------------------------------

def test_elke_bevinding_noemt_waar_zij_op_berust(a):
    for b in a["bevindingen"]:
        assert b["kop"] and b["wat"] and b["bron"]


def test_de_analyse_scheidt_wat_nagekeken_is_van_wat_uit_een_document_komt(a):
    h = a["herkomst"]
    assert h["live"] and h["document"]
    assert any("rev-portaal" in x for x in h["live"])
    assert any("ICTU" in x or "niet publiek" in x for x in h["document"])


def test_het_gir_document_wordt_niet_als_publieke_bron_gepresenteerd(a):
    """Het is een intern document; een URL suggereren die er niet is, is een valse vindplaats."""
    assert a["bronnen"]["gir"]["url"] is None
    assert a["bronnen"]["imev"]["url"].startswith("https://rev-portaal.nl/")


# --- de tellingen ----------------------------------------------------------------------------

def test_de_imev_tellingen_zijn_onderling_consistent(a):
    t = a["telling"]
    assert t["imev_objecttypen"] + t["imev_referentietypen"] + t["imev_enumeraties"] < t["imev_definities"]
    assert t["rev_resources"] < t["imev_objecttypen"], \
        "de API ontsluit minder dan het schema beschrijft -- dat is de bevinding"


def test_het_aantal_niet_gebouwde_tabellen_past_in_het_totaal(a):
    t = a["telling"]
    assert 0 < t["gir_niet_gebouwd"] < t["gir_tabellen"]


def test_de_tellingen_dekken_de_inhoud(a):
    t = a["telling"]
    assert t["lagen"] == len(a["lagen"])
    assert t["vertalingen"] == len(a["vertalingen"])
    assert t["bevindingen"] == len(a["bevindingen"])
    assert t["overlap"] == len(a["overlap"])


# --- de pagina --------------------------------------------------------------------------------

def test_de_pagina_geeft_200(monkeypatch):
    r = _client(monkeypatch).get("/modellen")
    assert r.status_code == 200
    assert "/api/modellen" in r.text


def test_de_pagina_staat_niet_in_het_waterdossier(monkeypatch):
    """Dit is een VTH-analyse; de waternav hoort er niet op."""
    h = _client(monkeypatch).get("/modellen").text
    assert 'class="waternav"' not in h
    assert "__WATERNAV__" not in h


def test_de_vth_paginas_wijzen_naar_de_analyse(monkeypatch):
    c = _client(monkeypatch)
    for pad in ("/vth", "/vth-bronnen"):
        assert "/modellen" in c.get(pad).text, f"{pad} linkt niet naar de analyse"


def test_het_eindpunt_levert_de_hele_analyse(monkeypatch):
    d = _client(monkeypatch).get("/api/modellen").json()
    for sleutel in ("bronnen", "lagen", "vertalingen", "overlap", "bevindingen",
                    "herkomst", "telling"):
        assert d[sleutel], sleutel
