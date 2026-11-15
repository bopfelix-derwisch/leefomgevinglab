"""`toezicht.woordvorm.hoofdletter_bij_zinsbegin` -- de ij-digraaf, en wat `.capitalize()`
daarin verkeerd deed (fix-ronde 2, publieke review op `/toezicht`, 2026-11-14)."""
from leefomgevinglab.usecases.toezicht.woordvorm import hoofdletter_bij_zinsbegin


def test_de_ij_digraaf_wordt_als_geheel_een_hoofdletter():
    assert hoofdletter_bij_zinsbegin("ijzer") == "IJzer"


def test_een_gewoon_woord_krijgt_gewoon_de_eerste_letter_een_hoofdletter():
    assert hoofdletter_bij_zinsbegin("zink") == "Zink"


def test_een_al_hoofdletterige_naam_blijft_ongewijzigd():
    assert hoofdletter_bij_zinsbegin("Zink") == "Zink"
    assert hoofdletter_bij_zinsbegin("IJzer") == "IJzer"


def test_de_rest_van_het_woord_wordt_nooit_verlaagd():
    """Het verschil met `str.capitalize()`: een naam met een interne hoofdletter (een
    samengestelde naam of afkorting) mag niet een tweede keer verminkt worden."""
    assert hoofdletter_bij_zinsbegin("stikstof Kjeldahl") == "Stikstof Kjeldahl"
    assert "stikstof Kjeldahl".capitalize() == "Stikstof kjeldahl", (
        "deze test zou zinloos zijn als .capitalize() hier toevallig ook goed ging")


def test_een_leeg_woord_blijft_leeg():
    assert hoofdletter_bij_zinsbegin("") == ""


def test_een_woord_dat_met_ij_begint_maar_korter_is_dan_de_digraaf_crasht_niet():
    assert hoofdletter_bij_zinsbegin("i") == "I"
    assert hoofdletter_bij_zinsbegin("j") == "J"
