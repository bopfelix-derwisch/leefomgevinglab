"""`toezicht.context` -- de context die de drie werkelijkheidsregels nodig hebben, en de
metingentabel van `/toezicht`. Geen netwerk: `waterlichaam_van_vestiging` wordt met
`_haal_waterlichaam` getest, het injectiepunt dat `kmg_service._waterlichaam_per_vergunning`
daarvoor al biedt (zie die module)."""
import pytest

from leefomgevinglab.usecases.toezicht import context
from tests.test_kmg_doelen import NORMEN, SET as DOELEN, _stof, _zink

# De norm van Belfeld boven ook laten gelden op "Heel" -- zink heeft op een eigen meetpunt
# zonder vermelding in `normen` geen enkele norm (chemisch én ecologisch, zie `doelen.py`), dus
# zonder dit zou geen van de twee testpunten een overschrijding kunnen tonen.
NORMEN_TWEE_PUNTEN = {**NORMEN, "normen": {**NORMEN["normen"],
                                            "NL80_HEEL": NORMEN["normen"]["NL80_BELFBVN"]}}


def _punt(code, naam, waterlichaam, stoffen):
    return {"code": code, "naam": naam, "waterlichaam": waterlichaam, "stoffen": stoffen}


PUNTEN = [
    _punt("NL80_BELFBVN", "Belfeld boven", "NL91ZM",
          [_zink(jaargem=5.78), _stof(zomer=2.97)]),  # zink binnen de norm, Ntot erboven
    _punt("NL80_HEEL", "Heel", "NL91ZM", [_zink(jaargem=12.0)]),  # zink boven de norm
    _punt("NL94_11PUNT", "Haringvliet", "NL94_11", [_stof(code="Nanorg", zomer=1.0)]),
]


# -- is_overschreden -------------------------------------------------------------------------

def test_is_overschreden_is_waar_bij_negatieve_ruimte():
    assert context.is_overschreden({"beschikbaar": True, "ruimte": -0.1}) is True


def test_is_overschreden_is_onwaar_bij_positieve_ruimte():
    assert context.is_overschreden({"beschikbaar": True, "ruimte": 0.1}) is False


def test_is_overschreden_is_onwaar_zonder_oordeel():
    assert context.is_overschreden(None) is False
    assert context.is_overschreden({"beschikbaar": False, "ruimte": -1.0}) is False


def test_is_overschreden_is_onwaar_zonder_ruimte():
    """Een oordeel zonder `ruimte` is een ontbrekend gegeven, geen overschrijding -- niet gokken."""
    assert context.is_overschreden({"beschikbaar": True, "ruimte": None}) is False


# -- toetsing/overschrijdingen ----------------------------------------------------------------

def test_toetsing_levert_een_rij_per_meetpunt_en_stof():
    getoetst = context.toetsing(PUNTEN, DOELEN, NORMEN_TWEE_PUNTEN)
    assert len(getoetst) == 4  # 2 + 1 + 1 stoffen over de drie punten
    assert {r["meetpunt"] for r in getoetst} == {"NL80_BELFBVN", "NL80_HEEL", "NL94_11PUNT"}


def test_overschrijdingen_bevat_alleen_de_overschreden_stoffen():
    getoetst = context.toetsing(PUNTEN, DOELEN, NORMEN_TWEE_PUNTEN)
    over = context.overschrijdingen(getoetst)
    stoffen = {(o["meetpunt"], o["stof"]) for o in over}
    assert ("NL80_BELFBVN", "Ntot") in stoffen, "Ntot op Belfeld boven zit boven de norm (ruimte -0,47)"
    assert ("NL80_HEEL", "Zn") in stoffen, "zink op Heel (jaargemiddelde 12,0) zit boven de norm 7,8"
    assert ("NL80_BELFBVN", "Zn") not in stoffen, "zink op Belfeld boven (5,78) zit onder de norm"


def test_overschrijdingen_draagt_de_vorm_die_de_signalen_verwachten():
    getoetst = context.toetsing(PUNTEN, DOELEN, NORMEN_TWEE_PUNTEN)
    over = context.overschrijdingen(getoetst)
    for o in over:
        for veld in ("meetpunt", "waterlichaam", "stof", "gemeten", "norm", "eenheid"):
            assert veld in o, f"veld {veld} ontbreekt -- signalen.py verwacht hem"


def test_overschrijdingen_is_leeg_zonder_getoetste_rijen():
    assert context.overschrijdingen([]) == []


# -- metingen_bij_waterlichaam ------------------------------------------------------------------

def test_metingen_bij_waterlichaam_filtert_op_het_opgegeven_waterlichaam():
    getoetst = context.toetsing(PUNTEN, DOELEN, NORMEN_TWEE_PUNTEN)
    rijen = context.metingen_bij_waterlichaam(getoetst, "NL91ZM")
    assert {r["meetpunt"] for r in rijen} == {"NL80_BELFBVN", "NL80_HEEL"}
    assert all(r["waterlichaam"] == "NL91ZM" for r in rijen)


def test_metingen_bij_waterlichaam_toont_ook_niet_overschreden_rijen():
    """De pagina toont de metingen zelf, niet alleen de signalen die erop vuren."""
    getoetst = context.toetsing(PUNTEN, DOELEN, NORMEN_TWEE_PUNTEN)
    rijen = context.metingen_bij_waterlichaam(getoetst, "NL91ZM")
    codes = [r["stof"]["code"] for r in rijen]
    assert "Zn" in codes and "Ntot" in codes


def test_metingen_bij_waterlichaam_zonder_waterlichaam_is_leeg():
    getoetst = context.toetsing(PUNTEN, DOELEN, NORMEN_TWEE_PUNTEN)
    assert context.metingen_bij_waterlichaam(getoetst, None) == []


# -- waterlichaam_van_vestiging -----------------------------------------------------------------

VESTIGING = {
    "naam": "Test BV", "kenmerk": "ABC/1", "locatiecode": "LOC1",
    "voorschriften": [
        {"parameter": "Zink", "waarde": 1.0, "eenheid": "microgram per liter",
         "rd": [190000.0, 350000.0]},
    ],
}

VESTIGING_ZONDER_COORDINAAT = {
    "naam": "Geen Coordinaat BV", "kenmerk": "XYZ/1", "locatiecode": "LOC2",
    "voorschriften": [{"parameter": "Zink", "waarde": 1.0, "eenheid": "microgram per liter"}],
}


def test_waterlichaam_van_vestiging_met_geinjecteerde_opzoeking():
    owl_id, reden = context.waterlichaam_van_vestiging(
        VESTIGING, live=True, _haal_waterlichaam=lambda x, y: "NL91ZM")
    assert owl_id == "NL91ZM"
    assert reden is None


def test_waterlichaam_van_vestiging_zonder_coordinaat_geeft_een_reden():
    owl_id, reden = context.waterlichaam_van_vestiging(
        VESTIGING_ZONDER_COORDINAAT, live=True, _haal_waterlichaam=lambda x, y: "NL91ZM")
    assert owl_id is None
    assert "coördinaat" in reden


def test_waterlichaam_van_vestiging_zonder_treffer_geeft_een_reden():
    owl_id, reden = context.waterlichaam_van_vestiging(
        VESTIGING, live=True, _haal_waterlichaam=lambda x, y: None)
    assert owl_id is None
    assert "waterlichaam" in reden
