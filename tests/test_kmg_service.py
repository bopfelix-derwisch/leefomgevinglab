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


def _wl_nl91bom(x, y):
    """Standaard-injectie voor de bestaande tests: de ene vergunning in `_atlas()` zit op het
    meetpunt zelf, dus haar waterlichaam is hier simpelweg dat van het meetpunt (NL91BOM) —
    zonder deze injectie zou `_waterlichaam_per_vergunning()` écht het netwerk op gaan."""
    return "NL91BOM"


def test_meetpunten_lijst(tmp_path):
    uit = service.meetpunten(_pad(tmp_path))
    assert [p["code"] for p in uit] == ["NL80_EIJSDPTN"]


def test_beeld_bevat_de_drie_lagen(tmp_path):
    b = service.beeld("NL80_EIJSDPTN", _pad(tmp_path), live=True,
                      _haal_regels=lambda rd: [], _haal_atlas=_atlas,
                      _haal_waterlichaam=_wl_nl91bom)
    assert "kan" in b and "mag" in b and "gebeurt" in b
    assert b["meetpunt"]["naam"] == "Eijsden ponton"


def test_gebeurt_draagt_de_gemeten_waarden(tmp_path):
    b = service.beeld("NL80_EIJSDPTN", _pad(tmp_path), live=True,
                      _haal_regels=lambda rd: [], _haal_atlas=_atlas,
                      _haal_waterlichaam=_wl_nl91bom)
    stof = b["gebeurt"]["stoffen"][0]
    assert stof["code"] == "Ntot"
    assert stof["mediaan"] == 3.3


def test_de_proclaimer_zit_in_het_antwoord(tmp_path):
    b = service.beeld("NL80_EIJSDPTN", _pad(tmp_path), live=True,
                      _haal_regels=lambda rd: [], _haal_atlas=_atlas,
                      _haal_waterlichaam=_wl_nl91bom)
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
                      _haal_regels=lambda rd: [], _haal_atlas=_atlas,
                      _haal_waterlichaam=_wl_nl91bom)
    v = b["bijdragen"][0]
    assert v["eenheid"] == "ug/l"
    assert v["som_bovengrens"] + v["restant"] == pytest.approx(7.4, rel=1e-9)


def _voorschriften_op(x, y):
    return [{"parameter": "stikstof totaal", "waarde": 10.0,
             "eenheid": "milligram per liter", "bemonstering": None, "rd": [x, y]},
            {"parameter": "Debiet", "waarde": 100.0,
             "eenheid": "kubieke meter per uur", "bemonstering": None, "rd": [x, y]}]


def test_een_benedenstroomse_vergunning_telt_niet_mee(tmp_path):
    """De kern van C1: het meetpunt op de Zandmaas, een vergunning op de Bergsche Maas.

    Twee vergunningen op twee verschillende coördinaten (en dus — via de geïnjecteerde
    opzoeking — twee verschillende waterlichamen) zijn precies de situatie waarin de oude code
    faalde: ze kreeg allebei het waterlichaam van het meetpunt mee, dus telden allebei mee.
    """
    punt = {**PUNT, "waterlichaam": "NL91ZM"}
    p = tmp_path / "m.json"
    p.write_text(json.dumps({**SET, "punten": [punt]}), encoding="utf-8")

    def _atlas_twee(x, y, straal_m):
        return [
            {"kenmerk": "K-BOVEN", "naam": "Boven BV", "plaats": "Boven", "locatie": None,
             "url": None, "besluitdatum": "2015-01-01", "locatiecode": None,
             "vestigingsnummer_kvk": None,
             "voorschriften": _voorschriften_op(100000.0, 400000.0)},
            {"kenmerk": "K-BENEDEN", "naam": "Beneden BV", "plaats": "Beneden", "locatie": None,
             "url": None, "besluitdatum": "2015-01-01", "locatiecode": None,
             "vestigingsnummer_kvk": None,
             "voorschriften": _voorschriften_op(200000.0, 400000.0)},
        ]

    def _wl_twee(x, y):
        return "NL91BOM" if x == 100000.0 else "NL94_6"          # Bergsche Maas: benedenstrooms

    b = service.beeld(PUNT["code"], str(p), live=True, _haal_regels=lambda rd: [],
                      _haal_atlas=_atlas_twee, _haal_waterlichaam=_wl_twee)

    posten = b["bijdragen"][0]["posten"]
    assert [po["kenmerk"] for po in posten] == ["K-BOVEN"]
    # Gekozen implementatie: een vergunning met een bekend maar benedenstrooms waterlichaam is
    # gewoon afwezig uit `posten` (dat doet `toerekening.bijdragen()` zelf via `is_bovenstrooms`).
    # `buiten_toerekening` is voorbehouden aan vergunningen waarvan het waterlichaam onbekend
    # bleef — die vraag is hier voor geen van beide posten aan de orde.
    assert b["mag"]["buiten_toerekening"] == []


def test_een_vergunning_zonder_waterlichaam_blijft_buiten_de_toerekening_met_een_reden(tmp_path):
    """Een opzoeking die niets oplevert, is geen gok: de vergunning telt niet mee, mét reden."""
    b = service.beeld("NL80_EIJSDPTN", _pad(tmp_path), live=True,
                      _haal_regels=lambda rd: [], _haal_atlas=_atlas,
                      _haal_waterlichaam=lambda x, y: None)
    assert b["bijdragen"][0]["posten"] == []
    uit = b["mag"]["buiten_toerekening"]
    assert len(uit) == 1
    assert uit[0]["kenmerk"] == "K1"
    assert uit[0]["reden"]


def test_een_vergunning_zonder_kenmerk_valt_niet_stil_weg(tmp_path):
    """I2: de RWZI's zonder kenmerk vallen terug op locatiecode, niet op een lege sleutel."""
    def _atlas_zonder_kenmerk(x, y, straal_m):
        return [{"kenmerk": None, "naam": "RWZI Testwijk", "plaats": "Maastricht",
                 "locatie": None, "url": None, "besluitdatum": "2015-01-01",
                 "locatiecode": "LOC1", "vestigingsnummer_kvk": None,
                 "voorschriften": _voorschriften_op(x, y)}]

    b = service.beeld("NL80_EIJSDPTN", _pad(tmp_path), live=True,
                      _haal_regels=lambda rd: [], _haal_atlas=_atlas_zonder_kenmerk,
                      _haal_waterlichaam=_wl_nl91bom)

    posten = b["bijdragen"][0]["posten"]
    assert [po["naam"] for po in posten] == ["RWZI Testwijk"]
    assert b["mag"]["buiten_toerekening"] == []


def test_zonder_live_wordt_er_geen_waterlichaam_opgezocht(tmp_path):
    """live=False betekent geen enkele opzoeking: elke post krijgt dezelfde, vaste reden."""
    posten = _atlas(176000.0, 310000.0, 1000)       # de ene post uit _atlas(), kenmerk K1

    def _nooit(x, y):
        raise AssertionError("de opzoeking mag niet aangeroepen worden als live=False")

    per_sleutel, redenen = service._waterlichaam_per_vergunning(
        posten, live=False, _haal_waterlichaam=_nooit)
    assert per_sleutel == {}
    assert redenen == {"K1": "niet opgezocht (live staat uit)"}
