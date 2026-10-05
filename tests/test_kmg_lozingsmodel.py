"""Het voorgestelde informatiemodel: een voorschrift codificeren én zeggen hoe zeker dat is."""
import json

import pytest

from leefomgevinglab.usecases.kmg import lozingsmodel as lm

REF = {"beschikbaar": True,
       "op_naam": {"zink": "Zn", "stikstof totaal": "Ntot", "nikkel": "Ni"},
       "telling": {"codes": 3}}


def _vs(parameter="zink", waarde=0.7, eenheid="milligram per liter",
        bemonstering="Verzamelmonster gedurende 24 uur", rd=(180000.0, 330000.0)):
    return {"parameter": parameter, "waarde": waarde, "eenheid": eenheid,
            "bemonstering": bemonstering, "rd": list(rd) if rd else None}


def test_een_voorschrift_krijgt_een_aquo_code_uit_de_referentie():
    d = lm.dataficeer(_vs(), REF)
    assert d["parameter"]["waarde"] == "Zn"
    assert d["parameter"]["zekerheid"] == "afgeleid"
    assert d["parameter"]["naam_bron"] == "zink"


def test_een_onbekende_stof_wordt_niet_gegokt():
    d = lm.dataficeer(_vs(parameter="Zwevende stof"), REF)
    assert d["parameter"]["waarde"] is None
    assert d["parameter"]["zekerheid"] == "ontbreekt"
    assert "parameterreferentie" in d["parameter"]["herkomst"]
    assert d["toerekenbaar"] is False


def test_de_koppeling_trekt_zich_niets_aan_van_hoofdletters():
    assert lm.dataficeer(_vs(parameter="Zink"), REF)["parameter"]["waarde"] == "Zn"


def test_de_eenheid_krijgt_een_code_en_een_dimensie():
    d = lm.dataficeer(_vs(eenheid="kilogram per jaar"), REF)
    assert d["eenheid"]["waarde"] == "kg/jaar"
    assert d["eenheid"]["dimensie"] == "vracht"


def test_grondslagen_worden_herkend():
    """Het veld dat bepaalt welke grenswaarde geldt als een stof er meerdere heeft."""
    assert lm.dataficeer(_vs(), REF)["grondslag"]["waarde"] == "etmaalgemiddelde"
    assert lm.dataficeer(_vs(bemonstering="Steekmonster"), REF)["grondslag"]["waarde"] == "momentaan"
    assert lm.dataficeer(_vs(bemonstering="weekmengmonster"), REF)["grondslag"]["waarde"] == "weekgemiddelde"


def test_de_hoedanigheid_is_altijd_een_aanname_en_zegt_dat():
    """De bron kent het veld niet; het model mag dat niet verstoppen."""
    h = lm.dataficeer(_vs(), REF)["hoedanigheid"]
    assert h["waarde"] == "NVT"
    assert h["zekerheid"] == "aangenomen"
    assert "totale fractie" in h["herkomst"]
    assert "hoedanigheid" in lm.dataficeer(_vs(), REF)["aangenomen"]


def test_de_geldigheidsperiode_ontbreekt_altijd_en_staat_er_wel_in():
    d = lm.dataficeer(_vs(), REF)
    assert d["geldigheid"]["waarde"] is None
    assert "geldigheid" in d["ontbreekt"]
    assert d["volledigheid"] != "volledig", "geen enkel Atlas-voorschrift kan volledig zijn"


def test_een_bruikbaar_voorschrift_is_toerekenbaar_ook_al_is_het_niet_volledig():
    d = lm.dataficeer(_vs(), REF)
    assert d["toerekenbaar"] is True
    assert d["volledigheid"] == "bruikbaar"


def test_de_schrijffout_in_de_bron_wordt_gekoppeld_maar_benoemd():
    d = lm.dataficeer(_vs(eenheid="kubieke met per etmaal"), REF)
    assert d["eenheid"]["waarde"] == "m3/d"
    assert "schrijffout" in d["eenheid"]["herkomst"]


def test_zonder_referentie_blijft_dataficeren_mogelijk_maar_zonder_code():
    d = lm.dataficeer(_vs(), {"beschikbaar": False, "op_naam": {}})
    assert d["parameter"]["waarde"] is None
    assert d["eenheid"]["waarde"] == "mg/l", "de eenhedentabel zit in het model zelf"


def test_de_telling_maakt_twee_registers_vergelijkbaar():
    vs = [lm.dataficeer(_vs(), REF),
          lm.dataficeer(_vs(parameter="Debiet"), REF),
          lm.dataficeer(_vs(parameter="nikkel", eenheid="kilogram per jaar"), REF)]
    t = lm.tel(vs)
    assert t["totaal"] == 3
    assert t["bruikbaar"] == 2
    assert t["onbruikbaar"] == 1
    assert t["zonder_geldigheid"] == 3
    assert t["aangenomen_hoedanigheid"] == 3


def test_een_vracht_in_kilogram_per_dag_wordt_een_jaarvracht():
    post = {"voorschriften": [_vs(parameter="nikkel", waarde=2.0, eenheid="kilogram per dag")]}
    g = lm.dataficeer_post(post, REF)
    v = lm.vrachten_op_code(g, debiet_m3_per_uur=None)
    assert v["Ni"]["kg_jaar"] == pytest.approx(730.0)


def test_een_concentratie_wordt_pas_een_vracht_met_een_debiet():
    post = {"voorschriften": [_vs(parameter="zink", waarde=1.0, eenheid="milligram per liter")]}
    g = lm.dataficeer_post(post, REF)
    assert lm.vrachten_op_code(g, debiet_m3_per_uur=None) == {}
    # 1 mg/l bij 100 m3/u: 1 g per m3 -> 100 g/u -> 876 kg/jaar
    v = lm.vrachten_op_code(g, debiet_m3_per_uur=100.0)
    assert v["Zn"]["kg_jaar"] == pytest.approx(876.0)


def test_bij_meerdere_grenswaarden_wordt_het_maximum_genomen_niet_de_som():
    post = {"voorschriften": [
        _vs(parameter="nikkel", waarde=1.0, eenheid="kilogram per dag"),
        _vs(parameter="nikkel", waarde=3.0, eenheid="kilogram per dag", bemonstering="Steekmonster"),
    ]}
    v = lm.vrachten_op_code(lm.dataficeer_post(post, REF), debiet_m3_per_uur=None)
    assert v["Ni"]["kg_jaar"] == pytest.approx(1095.0), "3 kg/d, niet 1+3"


def test_de_vracht_draagt_de_herkomst_van_de_hoedanigheid_mee():
    post = {"voorschriften": [_vs(parameter="zink", waarde=1.0, eenheid="kilogram per jaar")]}
    v = lm.vrachten_op_code(lm.dataficeer_post(post, REF), debiet_m3_per_uur=None)
    assert v["Zn"]["hoedanigheid_zekerheid"] == "aangenomen"


def test_een_ontbrekende_referentie_faalt_zacht(tmp_path):
    r = lm.laad_parameters(str(tmp_path / "weg.json"))
    assert r["beschikbaar"] is False
    assert "scripts/16" in r["reden"]


def test_een_beschadigde_referentie_faalt_zacht(tmp_path):
    p = tmp_path / "stuk.json"
    p.write_text("{geen json", encoding="utf-8")
    assert lm.laad_parameters(str(p))["beschikbaar"] is False


def test_een_geldige_referentie_wordt_gelezen(tmp_path):
    p = tmp_path / "ref.json"
    p.write_text(json.dumps(REF), encoding="utf-8")
    assert lm.laad_parameters(str(p))["op_naam"]["zink"] == "Zn"
