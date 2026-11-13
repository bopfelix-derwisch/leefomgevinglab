"""`toezicht.aquo` -- de Aquo-domeintabel met geldige én ingetrokken codes.

Leest een lokale CSV en raakt dus het bestandssysteem, maar nooit de echte 7000-rijige bron en
nooit het netwerk: elke test schrijft zijn eigen kleine CSV in `tmp_path`.
"""
import csv

from leefomgevinglab.usecases.toezicht import aquo

_KOP = ["Id", "Codes", "Omschrijving", "Groep", "CASnummer", "Alternatieve term",
        "Begin geldigheid", "Eind geldigheid", "Status", "Vervangen door", "Gerelateerd",
        "Wijzigingsnummer"]


def _schrijf_csv(pad, rijen):
    with open(pad, "w", encoding="utf-8-sig", newline="") as f:
        w = csv.writer(f, delimiter=";")
        w.writerow(_KOP)
        for rij in rijen:
            w.writerow(rij)


def _rij(id_, code, naam, status, cas="NVT", vervangen_door=""):
    return [id_, code, naam, "ChemischeStof", cas, "", "2011-06-08", "2100-01-01", status,
            vervangen_door, "", ""]


def test_laad_scheidt_geldige_en_ingetrokken_codes(tmp_path):
    pad = tmp_path / "aquo_Parameter.csv"
    _schrijf_csv(pad, [
        _rij(1, "Zn", "Zink", "Geldig"),
        _rij(2, "ZS", "Zwevende stof", "Vervallen"),
        _rij(3, "ZS", "Zwevende stof", "Vervallen"),
    ])
    ref = aquo.laad(str(pad))
    assert ref["beschikbaar"] is True
    assert ref["geldig"] == {"zink": "Zn"}
    assert ref["vervallen"] == {"zwevende stof": "ZS"}
    assert ref["aantal"]["Geldig"] == 1
    assert ref["aantal"]["Vervallen"] == 2


def test_laad_telt_concept_geldig_ook_als_geldig(tmp_path):
    """Fix-ronde 1, bevinding 3 (Minor): `_GELDIGE_STATUSSEN` bevat ook "Concept, Geldig" (7 van
    de 7109 rijen in de echte bron), maar niets testte dat -- een stille regressie die die status
    uit de tuple liet vallen, zou onopgemerkt blijven."""
    pad = tmp_path / "aquo_Parameter.csv"
    _schrijf_csv(pad, [_rij(1, "Hg", "kwik", "Concept, Geldig")])
    ref = aquo.laad(str(pad))
    assert ref["geldig"] == {"kwik": "Hg"}
    assert ref["vervallen"] == {}
    assert ref["aantal"]["Concept, Geldig"] == 1


def test_laad_zonder_bestand_faalt_zacht_met_een_reden(tmp_path):
    ref = aquo.laad(str(tmp_path / "bestaat_niet.csv"))
    assert ref["beschikbaar"] is False
    assert ref["geldig"] == {}
    assert ref["vervallen"] == {}
    assert "geen Aquo-domeintabel" in ref["reden"]


def test_een_naam_met_zowel_een_geldige_als_een_ingetrokken_rij_telt_als_geldig(tmp_path):
    """745 van de 7109 rijen in de echte bron hebben dit patroon (bv. "minerale olie"): de oude
    code is vervallen, een nieuwe is geldig. De geldige code is dan de referentie."""
    pad = tmp_path / "aquo_Parameter.csv"
    _schrijf_csv(pad, [
        _rij(1, "MINOL_OUD", "minerale olie", "Vervallen"),
        _rij(2, "MINOL", "minerale olie", "Geldig"),
    ])
    ref = aquo.laad(str(pad))
    assert ref["geldig"]["minerale olie"] == "MINOL"
    # Opzoektabel bewaart hem ook als vervallen -- `verrijk()` bepaalt zelf de voorrang.
    assert ref["vervallen"]["minerale olie"] == "MINOL_OUD"


def test_verrijk_zet_aquo_op_een_voorschrift_met_een_geldige_naam(tmp_path):
    pad = tmp_path / "aquo_Parameter.csv"
    _schrijf_csv(pad, [_rij(1, "Zn", "Zink", "Geldig")])
    ref = aquo.laad(str(pad))
    v = {"voorschriften": [{"parameter": "Zink", "waarde": 0.5,
                             "eenheid": "milligram per liter"}]}
    uit = aquo.verrijk(v, ref)
    assert uit["voorschriften"][0]["aquo"] == "Zn"
    assert "aquo_status" not in uit["voorschriften"][0]


def test_verrijk_zet_aquo_en_vervallen_status_op_een_ingetrokken_naam(tmp_path):
    """Dit is de reparatie uit de review: "Zwevende stof" moet `aquo_status: Vervallen` krijgen,
    niet `aquo: None` -- anders vuurt `regel_vervallen_code` nooit en misclassificeert elk
    voorschrift op die naam als `niet_in_referentie`."""
    pad = tmp_path / "aquo_Parameter.csv"
    _schrijf_csv(pad, [
        _rij(1, "ZS", "Zwevende stof", "Vervallen"),
        _rij(2, "ZS", "Zwevende stof", "Vervallen"),
    ])
    ref = aquo.laad(str(pad))
    v = {"voorschriften": [{"parameter": "Zwevende stof", "waarde": 30.0,
                             "eenheid": "milligram per liter"}]}
    uit = aquo.verrijk(v, ref)
    assert uit["voorschriften"][0]["aquo"] == "ZS"
    assert uit["voorschriften"][0]["aquo_status"] == "Vervallen"


def test_verrijk_zet_aquo_op_none_voor_een_onbekende_naam(tmp_path):
    """Aanwezig én `None`: er is gezocht, zonder resultaat -- de sentinel die
    `regel_niet_in_referentie` nodig heeft."""
    pad = tmp_path / "aquo_Parameter.csv"
    _schrijf_csv(pad, [_rij(1, "Zn", "Zink", "Geldig")])
    ref = aquo.laad(str(pad))
    v = {"voorschriften": [{"parameter": "Onbekend sulfiet-mengsel", "waarde": 1.0,
                             "eenheid": "milligram per liter"}]}
    uit = aquo.verrijk(v, ref)
    assert "aquo" in uit["voorschriften"][0]
    assert uit["voorschriften"][0]["aquo"] is None


def test_verrijk_geeft_voorrang_aan_de_geldige_code_bij_een_dubbele_naam(tmp_path):
    pad = tmp_path / "aquo_Parameter.csv"
    _schrijf_csv(pad, [
        _rij(1, "MINOL_OUD", "minerale olie", "Vervallen"),
        _rij(2, "MINOL", "minerale olie", "Geldig"),
    ])
    ref = aquo.laad(str(pad))
    v = {"voorschriften": [{"parameter": "minerale olie", "waarde": 5.0,
                             "eenheid": "milligram per liter"}]}
    uit = aquo.verrijk(v, ref)
    assert uit["voorschriften"][0]["aquo"] == "MINOL"
    assert "aquo_status" not in uit["voorschriften"][0]


def test_verrijk_laat_de_vestiging_onaangeroerd_zonder_beschikbare_referentie():
    """Geen bestand, dus niet gezocht -- `aquo` moet dan afwezig blijven, niet `None`."""
    ref = {"beschikbaar": False, "geldig": {}, "vervallen": {}}
    v = {"voorschriften": [{"parameter": "Zink", "waarde": 0.5,
                             "eenheid": "milligram per liter"}]}
    uit = aquo.verrijk(v, ref)
    assert "aquo" not in uit["voorschriften"][0]


def test_register_codes_verzamelt_alle_echte_codes_over_meerdere_vestigingen():
    vestigingen = [
        {"voorschriften": [{"parameter": "Zink", "aquo": "Zn"},
                            {"parameter": "Onbekend", "aquo": None}]},
        {"voorschriften": [{"parameter": "Zwevende stof", "aquo": "ZS",
                             "aquo_status": "Vervallen"}]},
    ]
    assert aquo.register_codes(vestigingen) == {"Zn", "ZS"}


def test_register_codes_op_een_lege_lijst_geeft_een_lege_set():
    assert aquo.register_codes([]) == set()
