"""De KRW-doelen: liever geen oordeel dan een oordeel tegen de verkeerde meetlat."""
import json

import pytest

from leefomgevinglab.usecases.kmg import doelen

KLASSEN = [
    {"klasse": "goed", "onder_symbool": ">=", "onder": 0.0, "boven_symbool": "<=", "boven": 2.5},
    {"klasse": "matig", "onder_symbool": ">", "onder": 2.5, "boven_symbool": "<=", "boven": 5.0},
    {"klasse": "ontoereikend", "onder_symbool": ">", "onder": 5.0,
     "boven_symbool": "<=", "boven": 7.5},
    {"klasse": "slecht", "onder_symbool": ">", "onder": 7.5, "boven_symbool": "", "boven": None},
]
SET = {
    "beschikbaar": True,
    "bron": {"naam": "Waterkwaliteitsportaal — KRW-doelen"},
    "opgehaald_op": "2026-10-02",
    "waterlichamen": {
        "NL91ZM": {"naam": "Zandmaas", "watertype": "R7", "doelen": {
            "Ntot": {"code": "Ntot", "naam": "Stikstof totaal", "eenheid": "mg/l",
                     "grondslag": "zomergemiddelde", "goed_tot": 2.5, "klassen": KLASSEN}}},
        "NL94_11": {"naam": "Haringvliet-west", "watertype": "O2b", "doelen": {
            "Nanorg": {"code": "Nanorg", "naam": "Stikstof anorganisch", "eenheid": "mg/l",
                       "grondslag": "zomergemiddelde", "goed_tot": 2.57, "klassen": KLASSEN}}},
    },
}


def _stof(code="Ntot", zomer=2.97, n_zomer=6):
    return {"code": code, "naam": "stikstof totaal", "eenheid": "mg/l",
            "mediaan": 3.2, "zomergemiddelde": zomer, "n_zomer": n_zomer}


def test_een_doel_wordt_op_het_zomergemiddelde_getoetst_niet_op_de_mediaan():
    t = doelen.toets(SET, "NL91ZM", _stof(zomer=2.97))
    assert t["beschikbaar"] is True
    assert t["getoetste_waarde"] == 2.97, "de mediaan van 3,2 mag hier niet opduiken"
    assert t["grondslag"] == "zomergemiddelde"
    assert t["klasse"] == "matig"
    assert t["ruimte"] == pytest.approx(-0.47)


def test_onder_het_doel_levert_ruimte_op():
    t = doelen.toets(SET, "NL91ZM", _stof(zomer=2.0))
    assert t["klasse"] == "goed"
    assert t["ruimte"] == pytest.approx(0.5)


def test_zonder_zomergemiddelde_komt_er_geen_oordeel():
    """De belangrijkste weigering: zonder de juiste grondslag liever niets zeggen."""
    t = doelen.toets(SET, "NL91ZM", _stof(zomer=None))
    assert t["beschikbaar"] is False
    assert t["soort"] == "grondslag ontbreekt"
    assert "zomergemiddelde" in t["reden"]


NORMEN = {
    "beschikbaar": True, "opgehaald_op": "2026-10-21",
    "bron": {"naam": "Waterkwaliteitsportaal — KRW-toetsresultaten"},
    "normen": {"NL80_BELFBVN": [
        {"parameter": "Zn", "hoedanigheid": "nf", "eenheid": "ug/l",
         "grondslag": "jaargemiddelde", "norm": 7.8, "meetjaar": "2024",
         "normgroep": "KRW spec. verontr. stoffen SGBP 2022-2027 - zoet"},
        {"parameter": "Zn", "hoedanigheid": "nf", "eenheid": "ug/l",
         "grondslag": "maximum", "norm": 16.6, "meetjaar": "2024",
         "normgroep": "KRW spec. verontr. stoffen SGBP 2022-2027 - zoet"},
    ]},
}


def _zink(hoed="nf", jaargem=5.78, maximum=8.65):
    return {"code": "Zn", "naam": "zink", "hoedanigheid": hoed, "eenheid": "ug/l",
            "jaargemiddelde": jaargem, "maximum": maximum, "zomergemiddelde": 6.68, "n": 13}


def test_zink_krijgt_zijn_echte_norm_op_het_jaargemiddelde():
    """De KRW-norm voor zink is een JG-MKN; de bron zegt dat zelf via de bewerkingsmethode."""
    t = doelen.toets(SET, "NL91ZM", _zink(), normenset=NORMEN, meetpunt="NL80_BELFBVN")
    assert t["beschikbaar"] is True
    assert t["soort"] == "chemische norm"
    assert t["grondslag"] == "jaargemiddelde"
    assert t["goed_tot"] == 7.8
    assert t["getoetste_waarde"] == 5.78
    assert t["klasse"] == "voldoet"
    assert t["ruimte"] == pytest.approx(2.02)


def test_de_tweede_grens_reist_mee():
    t = doelen.toets(SET, "NL91ZM", _zink(), normenset=NORMEN, meetpunt="NL80_BELFBVN")
    neven = {n["grondslag"]: n for n in t["nevengrenzen"]}
    assert neven["maximum"]["norm"] == 16.6
    assert neven["maximum"]["waarde"] == 8.65


def test_de_zinknorm_geldt_alleen_voor_de_opgeloste_fractie():
    """Tegen de totaalreeks leggen zou de verkeerde grootheid toetsen."""
    t = doelen.toets(SET, "NL91ZM", _zink(hoed="NVT"), normenset=NORMEN, meetpunt="NL80_BELFBVN")
    assert t["beschikbaar"] is False, "NVT is de totaalreeks; daar hoort deze norm niet bij"


def test_een_meetpunt_zonder_toets_krijgt_geen_oordeel():
    t = doelen.toets(SET, "NL91ZM", _zink(), normenset=NORMEN, meetpunt="NL80_HEEL")
    assert t["beschikbaar"] is False
    assert t["soort"] == "geen norm gevonden"


def test_zonder_normenbestand_blijft_stikstof_gewoon_werken():
    t = doelen.toets(SET, "NL91ZM", _stof(zomer=2.97))
    assert t["beschikbaar"] is True and t["klasse"] == "matig"


def test_pfoa_krijgt_geen_oordeel():
    t = doelen.toets(SET, "NL91ZM", {"code": "PFOA", "naam": "perfluoroctaanzuur",
                                     "zomergemiddelde": 0.004})
    assert t["beschikbaar"] is False
    assert t["soort"] == "geen doel per waterlichaam"


def test_een_ander_watertype_gebruikt_een_ander_element():
    t = doelen.toets(SET, "NL94_11", _stof(zomer=2.0))
    assert t["beschikbaar"] is True
    assert t["element"] == "Nanorg", "Haringvliet-west heeft geen Ntot"
    assert t["goed_tot"] == 2.57


def test_een_onbekend_waterlichaam_levert_geen_oordeel():
    t = doelen.toets(SET, "NL99_ONZIN", _stof())
    assert t["beschikbaar"] is False
    assert t["soort"] == "waterlichaam onbekend"


def test_zonder_geladen_doelen_komt_er_geen_oordeel():
    t = doelen.toets({"beschikbaar": False, "reden": "niet geladen", "waterlichamen": {}},
                     "NL91ZM", _stof())
    assert t["beschikbaar"] is False
    assert t["soort"] == "niet geladen"


def test_een_ontbrekend_bestand_faalt_zacht(tmp_path):
    d = doelen.laad(str(tmp_path / "bestaat-niet.json"))
    assert d["beschikbaar"] is False
    assert "scripts/15" in d["reden"]


def test_een_beschadigd_bestand_faalt_zacht_met_een_eigen_reden(tmp_path):
    p = tmp_path / "stuk.json"
    p.write_text("{dit is geen json", encoding="utf-8")
    d = doelen.laad(str(p))
    assert d["beschikbaar"] is False
    assert "onleesbaar" in d["reden"]


def test_een_geldig_bestand_wordt_gelezen(tmp_path):
    p = tmp_path / "doelen.json"
    p.write_text(json.dumps(SET), encoding="utf-8")
    d = doelen.laad(str(p))
    assert d["beschikbaar"] is True
    assert "NL91ZM" in d["waterlichamen"]
