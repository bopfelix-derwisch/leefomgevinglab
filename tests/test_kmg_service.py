import json

import pytest

from leefomgevinglab.usecases.kmg import service

PUNT = {
    "code": "NL80_EIJSDPTN", "naam": "Eijsden ponton", "rd": [176000.0, 310000.0],
    "waterlichaam": "NL91BOM",
    "stoffen": [{"code": "Ntot", "naam": "stikstof totaal", "eenheid": "mg/l",
                 "n": 52, "mediaan": 3.3, "maximum": 20.0,
                 "onder_rapportagegrens": 0, "van": "2025-01-08", "tot": "2025-12-10"}],
}
SET = {"meetjaar": "2025", "opgehaald_op": "2026-10-01",
       "bron": {"naam": "Waterkwaliteitsportaal", "houder": "Informatiehuis Water"},
       "punten": [PUNT], "telling": {"meegeteld": 52, "hiaatwaarden": 0}}


def _pad(tmp_path):
    p = tmp_path / "m.json"
    p.write_text(json.dumps(SET), encoding="utf-8")
    return str(p)


def _atlas(x, y, straal_m):
    return [{"kenmerk": "K1", "naam": "Testfabriek BV", "plaats": "Maastricht",
             "locatie": None, "url": None, "besluitdatum": "2015-01-01",
             "locatiecode": None, "vestigingsnummer_kvk": None,
             "voorschriften": [
                 {"parameter": "stikstof totaal", "waarde": 10.0,
                  "eenheid": "milligram per liter", "bemonstering": None, "rd": [x, y]},
                 {"parameter": "Debiet", "waarde": 100.0,
                  "eenheid": "kubieke meter per uur", "bemonstering": None, "rd": [x, y]}]}]


def test_meetpunten_lijst(tmp_path):
    uit = service.meetpunten(_pad(tmp_path))
    assert [p["code"] for p in uit] == ["NL80_EIJSDPTN"]


def test_beeld_bevat_de_drie_lagen(tmp_path):
    b = service.beeld("NL80_EIJSDPTN", _pad(tmp_path), live=True,
                      _haal_regels=lambda rd: [], _haal_atlas=_atlas)
    assert "kan" in b and "mag" in b and "gebeurt" in b
    assert b["meetpunt"]["naam"] == "Eijsden ponton"


def test_gebeurt_draagt_de_gemeten_waarden(tmp_path):
    b = service.beeld("NL80_EIJSDPTN", _pad(tmp_path), live=True,
                      _haal_regels=lambda rd: [], _haal_atlas=_atlas)
    stof = b["gebeurt"]["stoffen"][0]
    assert stof["code"] == "Ntot"
    assert stof["mediaan"] == 3.3


def test_de_proclaimer_zit_in_het_antwoord(tmp_path):
    b = service.beeld("NL80_EIJSDPTN", _pad(tmp_path), live=True,
                      _haal_regels=lambda rd: [], _haal_atlas=_atlas)
    assert len(b["proclaimer"]["kopjes"]) == 4


def test_onbekend_meetpunt_faalt_luid(tmp_path):
    with pytest.raises(KeyError):
        service.beeld("NL80_BESTAATNIET", _pad(tmp_path), live=False)


def test_zonder_live_worden_de_bronnen_niet_bevraagd(tmp_path):
    b = service.beeld("NL80_EIJSDPTN", _pad(tmp_path), live=False)
    assert b["kan"]["status"] == "overgeslagen"
    assert b["mag"]["status"] == "overgeslagen"


def test_zonder_meetset_blijven_de_andere_lagen_staan(tmp_path):
    b = service.beeld("", str(tmp_path / "bestaat-niet.json"), live=False,
                      toestaan_zonder_meetpunt=True)
    assert b["gebeurt"]["beschikbaar"] is False
    assert b["proclaimer"]["kopjes"]


def test_een_stof_in_microgram_komt_in_microgram_terug(tmp_path):
    punt = {**PUNT, "stoffen": [{"code": "Zn", "naam": "zink", "eenheid": "ug/l",
                                 "n": 70, "mediaan": 7.4, "maximum": 20.0,
                                 "onder_rapportagegrens": 0,
                                 "van": "2025-01-08", "tot": "2025-12-10"}]}
    p = tmp_path / "m.json"
    p.write_text(json.dumps({**SET, "punten": [punt]}), encoding="utf-8")
    b = service.beeld("NL80_EIJSDPTN", str(p), live=True,
                      _haal_regels=lambda rd: [], _haal_atlas=_atlas)
    v = b["bijdragen"][0]
    assert v["eenheid"] == "ug/l"
    assert v["som_bovengrens"] + v["restant"] == pytest.approx(7.4, rel=1e-9)
