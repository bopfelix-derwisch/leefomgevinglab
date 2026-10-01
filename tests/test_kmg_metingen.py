import json

import pytest

from leefomgevinglab.usecases.kmg import metingen

SET = {
    "meetjaar": "2025",
    "bron": {"naam": "Waterkwaliteitsportaal", "houder": "Informatiehuis Water"},
    "opgehaald_op": "2026-10-01",
    "punten": [
        {"code": "NL80_EIJSDPTN", "naam": "Eijsden ponton", "rd": [176000.0, 310000.0],
         "waterlichaam": "NL91BOM",
         "stoffen": [{"code": "Ntot", "naam": "stikstof totaal", "eenheid": "mg/l",
                      "n": 52, "mediaan": 3.3, "maximum": 20.0,
                      "onder_rapportagegrens": 0, "van": "2025-01-08", "tot": "2025-12-10"}]},
        {"code": "NL80_HEEL", "naam": "Heel", "rd": [190000.0, 350000.0],
         "waterlichaam": "NL91ZM",
         "stoffen": [{"code": "Zn", "naam": "zink", "eenheid": "ug/l",
                      "n": 26, "mediaan": 6.02, "maximum": 17.7,
                      "onder_rapportagegrens": 2, "van": "2025-02-01", "tot": "2025-11-01"}]},
    ],
    "telling": {"rijen": 100, "meegeteld": 78, "hiaatwaarden": 20, "onleesbaar": 2},
}


def test_laden_van_een_bestand(tmp_path):
    p = tmp_path / "m.json"
    p.write_text(json.dumps(SET), encoding="utf-8")
    d = metingen.laad(str(p))
    assert d["meetjaar"] == "2025"
    assert len(d["punten"]) == 2


def test_ontbrekend_bestand_geeft_een_lege_set(tmp_path):
    """De pagina moet het zonder meetset ook doen, met opgaaf van reden."""
    d = metingen.laad(str(tmp_path / "bestaat-niet.json"))
    assert d["punten"] == []
    assert d["beschikbaar"] is False
    assert d["reden"]


def test_punten_filteren_op_waterlichaam():
    uit = metingen.punten(SET, waterlichamen=["NL91BOM"])
    assert [p["code"] for p in uit] == ["NL80_EIJSDPTN"]


def test_punten_zonder_filter_geeft_alles():
    assert len(metingen.punten(SET)) == 2


def test_een_punt_opzoeken():
    p = metingen.punt(SET, "NL80_HEEL")
    assert p["naam"] == "Heel"
    assert p["stoffen"][0]["code"] == "Zn"


def test_onbekend_punt_faalt_luid():
    with pytest.raises(KeyError):
        metingen.punt(SET, "NL80_BESTAATNIET")
