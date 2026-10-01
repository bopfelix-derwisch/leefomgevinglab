import pytest

from leefomgevinglab.usecases.kmg import toerekening as t


def test_de_stroomvolgorde_loopt_van_bovenmaas_naar_haringvliet():
    codes = [c for c, _naam in t.STROOMVOLGORDE]
    assert codes[0] == "NL91BOM"
    assert codes.index("NL91GM") < codes.index("NL91ZM")
    assert codes.index("NL91ZM") < codes.index("NL94_5")
    assert len(codes) == len(set(codes)), "geen dubbele codes"


def test_elke_code_heeft_een_echte_naam():
    namen = dict(t.STROOMVOLGORDE)
    assert namen["NL91BOM"] == "Bovenmaas"
    assert namen["NL91GM"] == "Grensmaas"
    assert namen["NL91ZM"] == "Zandmaas"


def test_bovenstrooms_herkent_de_richting():
    assert t.is_bovenstrooms("NL91BOM", "NL91ZM") is True
    assert t.is_bovenstrooms("NL91ZM", "NL91BOM") is False


def test_hetzelfde_waterlichaam_telt_mee():
    assert t.is_bovenstrooms("NL91BOM", "NL91BOM") is True


def test_onbekend_waterlichaam_telt_niet_mee():
    assert t.is_bovenstrooms("NL00_ONBEKEND", "NL91ZM") is False


def _post(naam, vracht, parameter="stikstof totaal"):
    return {"naam": naam, "kenmerk": f"K-{naam}", "vrachten": {parameter: vracht}}


def test_alleen_bovenstroomse_vergunningen_dragen_bij():
    reg = [_post("Boven", 1000.0), _post("Beneden", 1000.0)]
    wl = {"K-Boven": "NL91BOM", "K-Beneden": "NL94_5"}
    d = t.bijdragen(3.3, "stikstof totaal", reg, "NL91ZM", wl, debiet_m3_s=250.0)
    namen = [p["naam"] for p in d["posten"]]
    assert namen == ["Boven"]


def test_de_som_van_bijdragen_en_restant_is_de_gemeten_waarde():
    reg = [_post("A", 1_000_000.0), _post("B", 500_000.0)]
    wl = {"K-A": "NL91BOM", "K-B": "NL91GM"}
    d = t.bijdragen(3.3, "stikstof totaal", reg, "NL91ZM", wl, debiet_m3_s=250.0)
    assert d["som_bijdragen_mg_l"] + d["restant_mg_l"] == pytest.approx(3.3, rel=1e-9)


def test_zonder_bovenstroomse_vergunningen_is_het_restant_alles():
    reg = [_post("Beneden", 1000.0)]
    wl = {"K-Beneden": "NL94_6"}
    d = t.bijdragen(3.3, "stikstof totaal", reg, "NL91BOM", wl, debiet_m3_s=250.0)
    assert d["posten"] == []
    assert d["restant_mg_l"] == pytest.approx(3.3)


def test_een_vergunning_zonder_deze_stof_draagt_niet_bij():
    reg = [_post("A", 1000.0, parameter="zink")]
    wl = {"K-A": "NL91BOM"}
    d = t.bijdragen(3.3, "stikstof totaal", reg, "NL91ZM", wl, debiet_m3_s=250.0)
    assert d["posten"] == []


def test_de_bijdrage_is_vracht_gedeeld_door_de_jaarafvoer():
    """1.000.000 kg/jaar in 250 m3/s = 250 * 31.536.000 * 1000 liter."""
    reg = [_post("A", 1_000_000.0)]
    wl = {"K-A": "NL91BOM"}
    d = t.bijdragen(10.0, "stikstof totaal", reg, "NL91ZM", wl, debiet_m3_s=250.0)
    liters = 250.0 * 31_536_000 * 1000
    verwacht = 1_000_000.0 * 1e6 / liters          # kg -> mg, gedeeld door liters
    assert d["posten"][0]["bijdrage_mg_l"] == pytest.approx(verwacht, rel=1e-6)


def test_het_voorbehoud_staat_altijd_in_de_uitkomst():
    d = t.bijdragen(3.3, "stikstof totaal", [], "NL91BOM", {}, debiet_m3_s=250.0)
    assert d["voorbehoud"]
    assert "bovengrens" in d["voorbehoud"].lower()


def test_de_uitkomst_bevat_het_woord_veroorzaakt_niet():
    """Spec 5.3: dit is een meetlat, geen vaststelling."""
    reg = [_post("A", 1000.0)]
    wl = {"K-A": "NL91BOM"}
    d = t.bijdragen(3.3, "stikstof totaal", reg, "NL91ZM", wl, debiet_m3_s=250.0)
    tekst = repr(d).lower()
    assert "veroorzaakt" not in tekst
