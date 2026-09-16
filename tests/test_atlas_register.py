import pytest

from leefomgevinglab.usecases.gebruiksruimte import atlas_register as ar


def _post(kenmerk="K1", **kw):
    return {"kenmerk": kenmerk, "naam": "Testfabriek BV", "plaats": "Maastricht",
            "locatie": None, "url": None, "besluitdatum": "2015-01-01",
            "locatiecode": kw.get("locatiecode"),
            "voorschriften": kw.get("voorschriften", [])}


def _v(parameter, waarde, eenheid):
    return {"parameter": parameter, "waarde": waarde, "eenheid": eenheid,
            "bemonstering": None, "rd": [None, None]}


# ---------- laag 1: de eenheid is al een vracht ----------

def test_vracht_in_kilogram_per_jaar_wordt_overgenomen():
    d = ar.naar_register([_post(voorschriften=[_v("zink", 120.0, "kilogram per jaar")])])
    assert d["register"][0]["vrachten"]["zink"] == pytest.approx(120.0)


def test_ton_per_jaar_wordt_omgerekend():
    d = ar.naar_register([_post(voorschriften=[_v("stikstof totaal", 1.2, "ton per jaar")])])
    assert d["register"][0]["vrachten"]["stikstof totaal"] == pytest.approx(1200.0)


def test_kilogram_per_dag_en_per_week():
    d = ar.naar_register([_post(voorschriften=[
        _v("zink", 1.0, "kilogram per dag"),
        _v("AOX", 1.0, "kilogram per week")])])
    v = d["register"][0]["vrachten"]
    assert v["zink"] == pytest.approx(365.0)
    assert v["AOX"] == pytest.approx(52.0)


# ---------- laag 2: concentratie × debiet ----------

def test_concentratie_maal_debiet_geeft_een_vracht():
    """0,3 mg/l bij 25 m3/uur = 0,3 * 25 * 24 * 365 / 1000 = 65,7 kg/jaar."""
    d = ar.naar_register([_post(voorschriften=[
        _v("zink", 0.3, "milligram per liter"),
        _v("Debiet", 25.0, "kubieke meter per uur")])])
    assert d["register"][0]["vrachten"]["zink"] == pytest.approx(65.7, rel=1e-3)


def test_microgram_per_liter_wordt_eerst_milligram():
    d = ar.naar_register([_post(voorschriften=[
        _v("zink", 300.0, "microgram per liter"),
        _v("Debiet", 25.0, "kubieke meter per uur")])])
    assert d["register"][0]["vrachten"]["zink"] == pytest.approx(65.7, rel=1e-3)


@pytest.mark.parametrize("eenheid,factor_naar_uur", [
    ("kubieke meter per uur", 1.0),
    ("kubieke meter per dag", 1 / 24),
    ("kubieke met per etmaal", 1 / 24),      # let op: tikfout staat zo in de bron
    ("kubieke meter per seconde", 3600.0),
])
def test_debiet_eenheden_worden_naar_m3_per_uur_gebracht(eenheid, factor_naar_uur):
    d = ar.naar_register([_post(voorschriften=[
        _v("zink", 1.0, "milligram per liter"), _v("Debiet", 24.0, eenheid)])])
    verwacht = 24.0 * factor_naar_uur * 24 * 365 / 1000.0
    assert d["register"][0]["vrachten"]["zink"] == pytest.approx(verwacht, rel=1e-3)


# ---------- laag 3: niet af te leiden ----------

def test_concentratie_zonder_debiet_levert_geen_vracht_maar_wel_een_reden():
    d = ar.naar_register([_post(voorschriften=[_v("zink", 0.3, "milligram per liter")])])
    post = d["register"][0]
    assert "zink" not in post["vrachten"]
    assert post["onbepaald"][0]["parameter"] == "zink"
    assert "debiet" in post["onbepaald"][0]["reden"].lower()


def test_onbruikbare_eenheid_valt_netjes_in_onbepaald():
    d = ar.naar_register([_post(voorschriften=[
        _v("Zuurgraad", 6.5, "dimensieloos"),
        _v("Warmte", 0.5, "megajoule per seconde")])])
    post = d["register"][0]
    assert post["vrachten"] == {}
    assert {o["parameter"] for o in post["onbepaald"]} == {"Zuurgraad", "Warmte"}


def test_lege_waarde_knalt_niet():
    d = ar.naar_register([_post(voorschriften=[_v("zink", None, "kilogram per jaar")])])
    assert d["register"][0]["vrachten"] == {}


# ---------- crosswalk naar de labparameters ----------

def test_aox_synoniemen_landen_op_de_labparameter():
    for naam in ("som extraheerbare organische halogeenverbindingen",
                 "Extraheerbaar organisch chloor"):
        d = ar.naar_register([_post(voorschriften=[_v(naam, 10.0, "kilogram per jaar")])])
        assert "AOX" in d["register"][0]["vrachten"], naam


def test_parameters_buiten_de_crosswalk_tellen_niet_mee_in_de_som():
    d = ar.naar_register([_post(voorschriften=[_v("barium", 10.0, "kilogram per jaar")])])
    assert d["register"][0]["vrachten"] == {}
    assert d["telling"]["buiten_crosswalk"] >= 1


def test_pfoa_komt_niet_voor_in_de_atlas_en_dat_is_de_bevinding():
    assert "PFOA" not in ar.CROSSWALK.values() or ar.CROSSWALK_BEVINDING
    assert "PFOA" in ar.CROSSWALK_BEVINDING


# ---------- telling ----------

def test_telling_laat_zien_hoeveel_er_niet_af_te_leiden_was():
    d = ar.naar_register([
        _post("K1", voorschriften=[_v("zink", 120.0, "kilogram per jaar")]),
        _post("K2", voorschriften=[_v("zink", 0.3, "milligram per liter")]),
    ])
    assert d["telling"]["vracht_direct"] == 1
    assert d["telling"]["onbepaald"] == 1
    assert d["bron"]["naam"] == "Atlas voor een Schone Maas"


# ---------- controller-ruling 9: locatiecode blijft zichtbaar in het register ----------

def test_twee_naamgenoten_zonder_kenmerk_blijven_onderscheidbaar_via_locatiecode():
    """RWZIB en RWZIL bij Maastricht: zelfde naam, zelfde plaats, geen kenmerk — maar wél
    een verschillende locatiecode, en die moet ná naar_register nog terug te vinden zijn."""
    posten = [
        _post(kenmerk=None, locatiecode="RWZIB"),
        _post(kenmerk=None, locatiecode="RWZIL"),
    ]
    d = ar.naar_register(posten)
    locatiecodes = {p["locatiecode"] for p in d["register"]}
    assert locatiecodes == {"RWZIB", "RWZIL"}
