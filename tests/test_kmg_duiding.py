"""De duiding op een meetpunt: het meeste wat het DSO teruggeeft raakt de waterkwaliteit niet."""
from leefomgevinglab.usecases.gebruiksruimte import regels
from leefomgevinglab.usecases.kmg import duiding


def _duid(type_, titel="Een document"):
    return regels.duiding({"type": type_, "titel": titel}, rijkswater=True,
                          tabel=duiding.DUIDING_KMG)


def test_het_omgevingsplan_normeert_de_waterkwaliteit_niet():
    d = _duid("Omgevingsplan")
    assert d["van_toepassing"] is False
    assert "landzijde" in d["betekenis"]


def test_de_waterschapsverordening_blijft_buiten_beeld_op_rijkswater():
    assert _duid("Waterschapsverordening")["van_toepassing"] is False


def test_de_amvb_telt_wel_en_benoemt_dat_het_bkl_ontbreekt():
    d = _duid("AMvB")
    assert d["van_toepassing"] is True
    assert "Bkl" in d["betekenis"]


def test_een_warmteprogramma_raakt_de_waterkwaliteit_niet():
    r = duiding.verfijn_programma(_duid("Programma", "Warmteprogramma gemeente Venlo"))
    assert r["van_toepassing"] is False


def test_een_waterprogramma_wel_en_wijst_naar_de_doelen():
    r = duiding.verfijn_programma(_duid("Programma", "Nationaal Waterprogramma 2022-2027"))
    assert r["van_toepassing"] is True
    assert "doelen" in r["betekenis"]


def test_de_verfijning_raakt_andere_typen_niet():
    plan = _duid("Omgevingsplan", "Omgevingsplan gemeente Waterland")
    assert duiding.verfijn_programma(plan) == plan, "alleen Programma mag verfijnd worden"


def test_de_telling_loopt_mee_met_de_verfijning():
    """En spreekt zichzelf niet tegen: de hertelling gebruikt dezelfde sleutels als de eerste."""
    kan = {"regelingen": [_duid("Programma", "Nationaal Waterprogramma"),
                          _duid("Programma", "Warmteprogramma Venlo"),
                          _duid("Omgevingsplan")],
           "telling": {"indirect": 2, "niet van toepassing": 1}}
    uit = duiding.duid_regelingen(kan)
    assert uit["telling"]["niet van toepassing"] == 2, "warmteprogramma + omgevingsplan"
    assert uit["telling"]["indirect"] == 1, "het waterprogramma, indirect werkend"
    assert sum(uit["telling"].values()) == 3, "elke regeling precies een keer geteld"


def test_een_lege_kan_laag_blijft_ongemoeid():
    kan = {"status": "onbereikbaar", "regelingen": [], "telling": {}}
    assert duiding.duid_regelingen(kan) == kan
