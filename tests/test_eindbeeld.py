"""Het synthetische eindbeeld: klopt het met zichzelf, en liegt het nergens over zijn aard?

Dit is de enige pagina in het dossier die niets van de werkelijkheid toont. Juist daarom staan
hier de strengste tests over presentatie: een verzonnen product dat zich niet als zodanig
aankondigt is geen illustratie maar een misleiding.
"""
import pytest
from fastapi.testclient import TestClient

from leefomgevinglab.geluidsmeter.api import app
from leefomgevinglab.usecases import eindbeeld as eb
from leefomgevinglab.usecases import water_hub as wh


@pytest.fixture(scope="module")
def p():
    return eb.product()


def _client(monkeypatch):
    monkeypatch.setattr("leefomgevinglab.geluidsmeter.api._config", {}, raising=False)
    return TestClient(app)


# --- eerlijk over zijn aard -----------------------------------------------------------------

def test_het_product_noemt_zichzelf_verzonnen(p):
    assert p["synthetisch"] is True
    assert "verzonnen" in p["waarschuwing"].lower()
    assert "bestaan niet" in p["waarschuwing"]


def test_geen_enkele_lozer_draagt_een_bestaande_bedrijfsnaam(p):
    """Met een echte naam zou hier een bewering over een bestaand bedrijf staan die nergens op
    berust. De namen die dit lab elders wél gebruikt komen uit het echte register."""
    from leefomgevinglab.usecases.kmg.koppeling import normaliseer

    echt = {"sappi", "solvay", "sitech", "chemelot", "tata", "enci", "johnson matthey",
            "afvalzorg", "rwe", "sibelco", "lawter", "pq silicas"}
    for naam in [l["naam"] for l in p["lozers"]] + [p["zuivering"]["naam"]]:
        k = normaliseer(naam)
        assert not any(e in k for e in echt), f"{naam} lijkt op een bestaand bedrijf"


def test_de_pagina_waarschuwt_bovenaan_en_blijft_waarschuwen(monkeypatch):
    h = _client(monkeypatch).get("/eindbeeld").text
    assert 'class="verzonnen"' in h
    assert "position:sticky" in h, "de waarschuwing moet meescrollen, niet wegvallen"


def test_het_dossier_merkt_dit_lid_als_volledig_synthetisch():
    lid = wh.lid("eindbeeld")
    assert lid["live"] == []
    assert any("alles" in s for s in lid["synthetisch"])


# --- klopt het met zichzelf? -----------------------------------------------------------------

def test_de_herkomsten_sluiten_aan_op_de_gemeten_vracht(p):
    """Niet exact: een balans die precies op nul uitkomt is gladgestreken, geen gemeten."""
    b = p["balans"]
    assert abs(b["sluitverschil_pct"]) < 2.0
    assert b["sluitverschil_kg"] != 0, "een perfect sluitende balans is ongeloofwaardig"
    assert sum(h["kg"] for h in b["herkomsten"]) == b["verdeeld_kg"]


def test_de_aandelen_tellen_op_tot_honderd(p):
    assert sum(h["pct"] for h in p["balans"]["herkomsten"]) == pytest.approx(100, abs=0.2)


def test_de_gemeten_vracht_volgt_uit_concentratie_en_debiet(p):
    b = p["balans"]
    verwacht = b["gemeten_ug_l"] * eb.DEBIET_M3_S * eb.SECONDEN_PER_JAAR / 1e6
    assert b["gemeten_kg"] == pytest.approx(round(verwacht))


def test_de_indirecte_lozers_tellen_op_tot_het_effluent(p):
    """Anders is de zuivering een doos waar meer uit komt dan erin gaat."""
    assert p["zuivering"]["sluit_aan_op_effluent"] is True


def test_huishoudens_tellen_niet_mee_als_bedrijf(p):
    """De eerste versie noemde drie 'bedrijven' en telde de huishoudens erbij."""
    z = p["zuivering"]
    assert len(z["top3_bedrijven"]) == 3
    assert all("huishoudens" not in n for n in z["top3_bedrijven"])


def test_de_lozerstotalen_kloppen_met_de_ruimteberekening(p):
    r = p["ruimte"]
    assert r["vergund_kg"] == round(sum(l["vergund_kg"] for l in p["lozers"]))
    assert r["gemeld_kg"] == round(sum(l["gemeld_kg"] for l in p["lozers"]))
    assert r["onbenut_kg"] == r["vergund_kg"] - r["gemeld_kg"]


def test_de_signaalgetallen_worden_berekend_en_niet_overgetypt(p):
    """De eerste versie zei '70 procent' en '6.190 kg' terwijl de som 7.150 en 76 procent was."""
    z, sig = p["zuivering"], next(s for s in p["signalen"] if s["soort"] == "indirect")
    assert f"{z['top3_pct']:.0f} procent" in sig["kop"]
    assert "6.190" in sig["wat"] and z["top3_kg"] == 6190


# --- de bevinding die het eindbeeld oplevert ---------------------------------------------------

def test_de_onbenutte_ruimte_is_groter_dan_de_ruimte_tot_de_norm(p):
    """Dit is waarom dit product meer is dan een mooie pagina: niemand overtreedt iets, en toch
    kan de norm worden overschreden zonder dat er een besluit aan te pas komt."""
    r = p["ruimte"]
    assert r["past_binnen_de_norm"] is False
    assert r["onbenut_maal_vrij"] > 1.0
    assert "zonder dat iemand een regel overtreedt" in r["les"]


# --- de afstand tot vandaag --------------------------------------------------------------------

def test_elk_veld_zegt_of_het_vandaag_al_kan(p):
    for v in p["velden"]:
        assert v["vandaag"] in ("ja", "deels", "nee"), v
        assert v["hoe"]
        if v["vandaag"] != "ja":
            assert v["gat"] in p["gaten"], f"{v['veld']} noemt geen bestaand gat"


def test_er_blijft_werk_over_en_dat_is_het_punt(p):
    t = p["veld_telling"]
    assert sum(t.values()) == len(p["velden"])
    assert t["nee"] > 0, "een eindbeeld dat vandaag al kan, is geen eindbeeld"
    assert t["ja"] > 0, "en een dat nergens begint, is geen opdrachtenlijst"


def test_elk_gat_wordt_ergens_aangehaald(p):
    """Een gat dat nergens op de pagina terugkomt, is een losse bewering."""
    gebruikt = {v["gat"] for v in p["velden"] if v["gat"]}
    gebruikt |= {h["gat"] for h in p["balans"]["herkomsten"] if h["gat"]}
    gebruikt |= {s["gat"] for s in p["signalen"] if s["gat"]}
    assert set(p["gaten"]) == gebruikt


def test_elke_aanname_zegt_waarom(p):
    for a in p["aannames"]:
        assert a["wat"] and a["waarde"] and a["waarom"], a


def test_de_norm_wordt_niet_als_aanname_gepresenteerd(p):
    """Die is echt, en dat onderscheid gaat verloren als alles op één hoop gaat."""
    norm = next(a for a in p["aannames"] if a["id"] == "norm")
    assert "geen aanname" in norm["waarom"].replace("é", "e")


# --- de pagina ------------------------------------------------------------------------------

def test_de_pagina_geeft_200_met_de_subnav(monkeypatch):
    r = _client(monkeypatch).get("/eindbeeld")
    assert r.status_code == 200
    assert 'class="waternav"' in r.text
    assert r.text.count('aria-current="page"') == 1
    assert "__WATERNAV__" not in r.text


def test_het_eindpunt_levert_het_hele_product(monkeypatch):
    d = _client(monkeypatch).get("/api/eindbeeld").json()
    assert d["synthetisch"] is True
    for sleutel in ("balans", "ruimte", "lozers", "zuivering", "signalen", "velden", "aannames"):
        assert d[sleutel], sleutel
