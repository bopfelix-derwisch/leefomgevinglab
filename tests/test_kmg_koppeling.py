"""De koppeling vergunning ↔ E-PRTR: een heuristiek die zegt waarop zij berust."""
import pytest

from leefomgevinglab.usecases.kmg import koppeling as kp


def _melding(naam="Sappi Maastricht BV", stof="ZNANDCOMPOUNDS", kg=105.0, jaar=2022,
             medium="WATER", rd=(176620.0, 318700.0), nid="000000060"):
    return {"productionsite_name": naam, "pollutant": stof, "totalpollutantquantitykg": kg,
            "year": jaar, "mediumcode": medium, "rd": list(rd), "nationalid": nid}


def test_rechtsvormen_tellen_niet_mee_in_de_vergelijking():
    """B.V. tegen BV hoort 1,00 te geven; anders zakt een identiek paar naar 0,91."""
    assert kp.gelijkenis("Sappi Maastricht B.V.", "Sappi Maastricht BV") == pytest.approx(1.0)
    assert kp.gelijkenis("Solvay Chemie B.V.", "Solvay Chemie BV") == pytest.approx(1.0)
    assert kp.normaliseer("Sappi Maastricht B.V.") == "sappi maastricht"


def test_een_ander_bedrijf_op_hetzelfde_terrein_haalt_de_drempel_niet():
    """Sitech zit op Chemelot; dat is dezelfde plek maar niet dezelfde rechtspersoon."""
    assert kp.gelijkenis("Sitech Services B.V.", "Chemelot Site Permit BV") < kp.DREMPEL
    assert kp.gelijkenis("PQ Silicas B.V.", "Bowie Recycling BV") < kp.DREMPEL


def test_een_passende_naam_dichtbij_wordt_gekoppeld_met_de_grondslag_erbij():
    k = kp.koppel("Sappi Maastricht B.V.", (176600.0, 318700.0), [_melding()])
    assert k["gekoppeld"] is True
    assert k["nationalid"] == "000000060"
    assert k["gelijkenis"] == pytest.approx(1.0)
    assert k["afstand_m"] == 20
    assert "geen gedeelde identificatie" in k["grondslag"]


def test_niets_in_de_buurt_en_naam_wijkt_af_zijn_verschillende_uitspraken():
    leeg = kp.koppel("Sappi Maastricht B.V.", (176600.0, 318700.0), [])
    assert leeg["gekoppeld"] is False and leeg["soort"] == "niets in de buurt"

    anders = kp.koppel("PQ Silicas B.V.", (176600.0, 318700.0),
                       [_melding(naam="Bowie Recycling BV")])
    assert anders["gekoppeld"] is False and anders["soort"] == "naam wijkt af"
    assert "Bowie Recycling BV" in anders["nabij"]


def test_de_prtr_stofnaam_wordt_naar_een_aquo_code_vertaald():
    k = kp.koppel("Sappi Maastricht B.V.", (176600.0, 318700.0), [_melding()])
    st = kp.gemeld_per_stof(k)
    assert st["Zn"]["kg_jaar"] == 105.0
    assert st["Zn"]["jaar"] == 2022
    assert st["Zn"]["prtr_stof"] == "ZNANDCOMPOUNDS"


def test_een_onbekende_stof_verdwijnt_niet_maar_houdt_haar_eigen_naam():
    k = kp.koppel("X B.V.", (0.0, 0.0), [_melding(naam="X BV", stof="TOC", kg=63200.0)])
    st = kp.gemeld_per_stof(k)
    assert "TOC" in st and st["TOC"]["aquo"] is False


def test_alleen_het_gevraagde_medium_telt_mee():
    """Lucht- en watermeldingen staan door elkaar in dezelfde laag."""
    k = kp.koppel("X B.V.", (0.0, 0.0), [
        _melding(naam="X BV", stof="ZNANDCOMPOUNDS", kg=9.0, medium="AIR"),
        _melding(naam="X BV", stof="ZNANDCOMPOUNDS", kg=105.0, medium="WATER"),
    ])
    assert kp.gemeld_per_stof(k)["Zn"]["kg_jaar"] == 105.0


def test_een_inrichting_zonder_watermelding_is_iets_anders_dan_geen_inrichting():
    """Johnson Matthey en Solvay zijn precies dit geval — de koppeling slaagt, de melding ontbreekt."""
    k = kp.koppel("Johnson Matthey B.V.", (0.0, 0.0),
                  [_melding(naam="Johnson Matthey BV", medium="AIR")])
    assert k["gekoppeld"] is True, "de inrichting bestaat en ligt hier"
    assert kp.gemeld_per_stof(k) == {}, "maar zij meldt niets naar water"


def test_de_meest_recente_jaargang_wint():
    k = kp.koppel("X B.V.", (0.0, 0.0), [
        _melding(naam="X BV", kg=685.0, jaar=2019),
        _melding(naam="X BV", kg=105.0, jaar=2022),
    ])
    assert kp.gemeld_per_stof(k)["Zn"]["jaar"] == 2022


def test_benutting_rekent_alleen_met_beide_helften():
    assert kp.benutting(7008.0, 105.0)["benut_pct"] == pytest.approx(1.5, abs=0.01)
    assert kp.benutting(7008.0, 105.0)["onbenut_kg"] == pytest.approx(6903.0)
    assert kp.benutting(7008.0, None) is None, "geen melding is geen nul"
    assert kp.benutting(None, 105.0) is None
    assert kp.benutting(0.0, 105.0) is None, "geen percentage van nul vergunde ruimte"
