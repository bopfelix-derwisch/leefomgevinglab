"""De stoffengraaf: wat een gedeeld nummer doet dat een handtabel niet doet.

De kern van deze testset is niet dat de graaf "klopt" maar dat zij haar eigen beperking blijft
dragen. CAS lost de specifieke stoffen op en de somparameters niet, en zodra die nuance uit de
uitkomst verdwijnt is de pagina een reclamepraatje geworden in plaats van een bevinding.
"""
import pytest

from leefomgevinglab.usecases import stoffengraaf as sg
from leefomgevinglab.usecases.kmg.koppeling import PRTR_NAAR_AQUO


@pytest.fixture(scope="module")
def aquo():
    d = sg.laad_aquo()
    if not d["beschikbaar"]:
        pytest.skip(d["reden"])
    return d


@pytest.fixture(scope="module")
def graaf(aquo):
    return sg.bouw()


# --- de domeintabel als graafbron ----------------------------------------------------------

def test_vervallen_codes_doen_niet_mee(aquo):
    """Een vervallen code is geen sleutel om op te koppelen."""
    assert aquo["telling"]["vervallen"] > 0
    assert "Ntot" in aquo["parameters"]
    assert aquo["parameters"]["Ntot"]["naam"] == "stikstof totaal"


def test_de_cas_sentinel_nvt_wordt_geen_sleutel(aquo):
    """NVT betekent 'niet van toepassing'. Als tekst zou het 1500 parameters aan elkaar knopen."""
    assert "NVT" not in aquo["per_cas"]
    assert all(v["cas"] != "NVT" for v in aquo["parameters"].values())


def test_cas_is_in_deze_tabel_vrijwel_een_sleutel(aquo):
    """Als bijna elk nummer naar één code wijst, is het bruikbaar als join."""
    assert aquo["telling"]["met_cas"] > 4000
    assert aquo["telling"]["cas_niet_uniek"] <= 5


def test_het_veld_gerelateerd_bestaat_en_is_gevuld(aquo):
    """Dit is de kolom die de huidige ingest weggooit."""
    assert aquo["telling"]["met_relatie"] > 500
    assert aquo["parameters"]["smetln6"]["gerelateerd"]


# --- de koppeling ---------------------------------------------------------------------------

def test_elke_prtr_stof_krijgt_precies_een_uitkomst(graaf):
    soorten = {"cas_en_hand", "alleen_cas", "alleen_hand", "geen_brug", "cas_wijkt_af"}
    assert len(graaf["koppelingen"]) == len(sg.PRTR_STOFFEN)
    assert all(k["soort"] in soorten for k in graaf["koppelingen"])


def test_cas_spreekt_de_handtabel_nergens_tegen(graaf):
    """Dit is de belangrijkste uitkomst: de handtabel is niet fout, alleen incompleet.

    Zou dit omslaan, dan is er iets veranderd aan een van beide bronnen en moet een mens kijken
    welke van de twee gelijk heeft -- niet de graaf stilzwijgend een kant kiezen.
    """
    assert graaf["telling"]["cas_wijkt_af"] == 0


def test_cas_vindt_meer_dan_de_handtabel(graaf):
    """Het argument van deze pagina: een gedeeld nummer doet werk dat niemand hoeft te doen."""
    assert graaf["telling"]["alleen_cas"] >= 2
    alleen = [k["code"] for k in graaf["koppelingen"] if k["soort"] == "alleen_cas"]
    assert all(c not in PRTR_NAAR_AQUO for c in alleen)


def test_somparameters_hebben_geen_cas_en_dat_is_geen_omissie(graaf):
    """Een grootheid die door een meetmethode wordt gedefinieerd heeft geen molecuulnummer."""
    som = [k for k in graaf["koppelingen"] if k["som"]]
    assert som, "zonder somparameters mist de pagina haar nuance"
    assert all(k["cas"] is None for k in som)
    assert all(k["aquo_via_cas"] is None for k in som)


def test_de_stoffen_zonder_brug_zijn_allemaal_somparameters(graaf):
    """Zodra hier een specifieke stof in opduikt, is er een CAS-nummer dat wij niet kennen."""
    zonder = [k for k in graaf["koppelingen"] if k["soort"] == "geen_brug"]
    assert zonder
    assert all(k["som"] for k in zonder), [k["code"] for k in zonder if not k["som"]]


def test_zink_koppelt_langs_beide_wegen_naar_dezelfde_code(graaf):
    zn = next(k for k in graaf["koppelingen"] if k["code"] == "ZNANDCOMPOUNDS")
    assert zn["aquo_via_cas"] == zn["aquo_via_hand"] == "Zn"
    assert zn["cas"] == "7440-66-6"


# --- de dubbeltelling -------------------------------------------------------------------------

def test_de_som_en_haar_delen_bestaan_allebei_als_code(graaf):
    s = graaf["dubbeltelling"]
    assert s["beschikbaar"]
    assert set(s["delen_als_code"]) == {"Zn", "Cu", "Pb", "Ni", "Cr", "As"}


def test_de_samenstelling_komt_uit_tekst_en_niet_uit_een_relatie(graaf):
    """Dát is het verschil tussen een tabel met velden en een graaf met relaties."""
    s = graaf["dubbeltelling"]
    assert s["heeft_relatie"] is True, "de tabel weet dát er een relatie is"
    assert s["relatie_resolvabaar"] is False, "maar zegt niet welke"
    assert "omschrijving" in s["les"]


# --- de graaf en de pagina ---------------------------------------------------------------------

def test_elke_rand_zegt_waar_zij_vandaan_komt(graaf):
    """Een koppeling zonder herkomst is een bewering; met herkomst is het data."""
    assert graaf["randen"]
    for r in graaf["randen"]:
        assert r["herkomst"], r
        assert r["soort"] in {"cas", "hand"}


def test_knopen_zijn_ontdubbeld(graaf):
    ids = [n["id"] for n in graaf["knopen"]]
    assert len(ids) == len(set(ids))


def test_zonder_domeintabel_valt_het_luid_maar_niet_om():
    d = sg.bouw("/bestaat/niet/Parameter.csv")
    assert d["beschikbaar"] is False
    assert "scripts/16" in d["reden"]
    assert d["knopen"] == [] and d["randen"] == []


# --- de pagina ---------------------------------------------------------------------------

def _client(monkeypatch):
    from fastapi.testclient import TestClient

    from leefomgevinglab.geluidsmeter.api import app
    monkeypatch.setattr("leefomgevinglab.geluidsmeter.api._config", {}, raising=False)
    return TestClient(app)


def test_de_pagina_geeft_200_met_de_subnav(monkeypatch):
    r = _client(monkeypatch).get("/kennisgraaf")
    assert r.status_code == 200
    assert 'class="waternav"' in r.text
    assert r.text.count('aria-current="page"') == 1
    assert "__WATERNAV__" not in r.text
    assert "/api/stoffengraaf" in r.text


def test_de_pagina_zegt_ook_wat_een_graaf_niet_oplost(monkeypatch):
    """Zonder die alinea is dit een reclamepraatje in plaats van een bevinding."""
    h = _client(monkeypatch).get("/kennisgraaf").text.lower()
    assert "vult geen lege velden" in h
    assert "vervangt het informatiemodel niet" in h
    assert "geen rdf" in h


def test_het_eindpunt_levert_de_graaf(monkeypatch):
    d = _client(monkeypatch).get("/api/stoffengraaf").json()
    if not d.get("beschikbaar"):
        pytest.skip(d.get("reden"))
    assert d["telling"]["prtr_stoffen"] == len(sg.PRTR_STOFFEN)
    assert d["knopen"] and d["randen"]


def test_de_kennisgraaf_is_lid_van_het_waterdossier():
    from leefomgevinglab.usecases import water_hub as wh

    lid = wh.lid("kennisgraaf")
    assert lid["pad"] == "/kennisgraaf"
    assert any("bijlage II" in s for s in lid["synthetisch"]), \
        "dat de CAS-nummers met de hand zijn overgenomen hoort in de verantwoording"


# --- de controle over een echt register -----------------------------------------------------

_REG = [
    {"naam": "Zwevend BV", "kenmerk": "K-1", "voorschriften": [
        {"parameter": "Zwevende stof"}, {"parameter": "zink"}]},
    {"naam": "Som BV", "kenmerk": "K-2", "voorschriften": [
        {"parameter": "som 6 metalen (Zn, Cu, Pb, Ni, Cr, As)"},
        {"parameter": "arseen"}, {"parameter": "zink"}]},
    {"naam": "Nieuw BV", "kenmerk": "K-3", "voorschriften": [
        {"parameter": "melamine"}, {"parameter": "melamine"}]},
]


@pytest.fixture(scope="module")
def controle():
    d = sg.controleer(_REG)
    if not d["beschikbaar"]:
        pytest.skip(d["reden"])
    return d


def test_een_ingetrokken_code_is_iets_anders_dan_een_onbekende_naam(controle):
    """Dat onderscheid is de hele waarde van deze controle: onderhoud tegenover standaardisatie."""
    vervallen = {x["naam"] for x in controle["vervallen"]}
    onbekend = {x["naam"] for x in controle["onbekend"]}
    assert "Zwevende stof" in vervallen
    assert "melamine" in onbekend
    assert not (vervallen & onbekend)


def test_de_telling_gaat_over_voorschriften_en_niet_over_namen(controle):
    """Vier namen kunnen negentig voorschriften zijn; dat verschil bepaalt of het ertoe doet."""
    t = controle["telling"]
    assert t["niet_in_aquo"] == 2 and t["namen_onbekend"] == 1, "melamine staat er twee keer in"


def test_een_som_naast_haar_delen_wordt_gevonden(controle):
    d = controle["dubbeltelling"]
    assert len(d) == 1
    assert d[0]["som"] == "smetln6"
    assert set(d[0]["ook_apart"]) == {"Zn", "As"}


def test_een_vergunning_zonder_som_levert_geen_treffer(controle):
    assert all(x["kenmerk"] != "K-1" for x in controle["dubbeltelling"])


def test_de_sommen_komen_uit_de_omschrijving_en_zijn_er_genoeg(controle):
    """Als dit terugvalt naar nul, is het ontleden van de omschrijving stukgelopen."""
    assert controle["telling"]["sommen_met_delen"] > 20


def test_zonder_domeintabel_meldt_de_controle_dat(tmp_path):
    d = sg.controleer(_REG, str(tmp_path / "weg.csv"))
    assert d["beschikbaar"] is False and "scripts/16" in d["reden"]


def test_het_echte_maasregister_levert_bevindingen_op():
    """Een controle die nooit iets vindt, bewijst niets. Deze vindt wél iets."""
    from leefomgevinglab.usecases.kmg import service

    try:
        reg = service._atlas_standaard(*sg.MAASPUNT, 250000)
    except Exception as exc:                       # noqa: BLE001
        pytest.skip(f"Atlas niet bereikbaar: {type(exc).__name__}")
    d = sg.controleer(reg)
    if not d["beschikbaar"]:
        pytest.skip(d["reden"])
    t = d["telling"]
    assert t["voorschriften"] > 500
    assert t["op_vervallen_code"] > 0, "als dit nul wordt, is Aquo bijgewerkt — mooi nieuws"
    assert t["namen_onbekend"] > 0
