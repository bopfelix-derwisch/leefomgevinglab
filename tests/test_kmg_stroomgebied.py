"""Het stroomgebied als afbakening, in plaats van een cirkel van 50 km.

De straal bepaalde eerst wát meetelde; nu bepaalt hij alleen nog wát opgehaald wordt. Een
stroomgebied is geen cirkel: hij pakte benedenstroomse lozingen mee en liet bovenstroomse liggen.
Wat deze tests vastleggen is vooral het onderscheid tussen de redenen om niet mee te tellen --
die drie mogen niet op één hoop.
"""
import json

import pytest

from leefomgevinglab.usecases.kmg import service, stroomgebied, toerekening

_REGISTER = {
    "beschikbaar": True,
    "opgehaald_op": "2026-10-29",
    "waterlichamen": {
        "NL91BOM": {"code": "NL91BOM", "naam": "Bovenmaas", "district": "Maas"},
        "NL91ZM": {"code": "NL91ZM", "naam": "Zandmaas", "district": "Maas"},
        "NL94_6": {"code": "NL94_6", "naam": "Bergsche Maas", "district": "Maas"},
        "NL90_1": {"code": "NL90_1", "naam": "Limburgse kanalen", "district": "Maas"},
        "NL93_IJSSEL": {"code": "NL93_IJSSEL", "naam": "IJssel", "district": "Rijn-Oost"},
    },
    "per_district": {"Maas": ["NL91BOM", "NL91ZM", "NL94_6", "NL90_1"],
                     "Rijn-Oost": ["NL93_IJSSEL"]},
    "reden": None,
}


# --- het register ------------------------------------------------------------------------

def test_lidmaatschap_kent_drie_uitkomsten_en_niet_twee():
    """"Ligt er niet in" en "we weten het niet" leiden tot verschillende teksten."""
    assert stroomgebied.in_district(_REGISTER, "NL91ZM", "Maas") is True
    assert stroomgebied.in_district(_REGISTER, "NL93_IJSSEL", "Maas") is False
    assert stroomgebied.in_district(_REGISTER, "NL99_ONBEKEND", "Maas") is None
    assert stroomgebied.in_district(_REGISTER, None, "Maas") is None


def test_zonder_register_is_niets_te_bepalen_en_hoort_niets_erbij():
    """Een ontbrekend bestand mag geen lozing de toerekening in praten."""
    leeg = stroomgebied.laad("/bestaat/niet/krw_waterlichamen.json")
    assert leeg["beschikbaar"] is False
    assert "scripts/18" in leeg["reden"]
    assert stroomgebied.in_district(leeg, "NL91ZM", "Maas") is None


def test_het_echte_register_plaatst_de_maas_waterlichamen():
    r = stroomgebied.laad()
    if not r["beschikbaar"]:
        pytest.skip(r["reden"])
    assert stroomgebied.district_van(r, "NL91BOM") == "Maas"
    assert len(stroomgebied.codes_in_district(r, "Maas")) > 100


# --- de redenen om niet mee te tellen -----------------------------------------------------

def test_bovenstrooms_en_hetzelfde_waterlichaam_tellen_mee():
    assert toerekening.reden_niet_bovenstrooms("NL91BOM", "NL91ZM", True) is None
    assert toerekening.reden_niet_bovenstrooms("NL91ZM", "NL91ZM", True) is None


def test_de_drie_redenen_om_niet_mee_te_tellen_zijn_verschillend():
    benedenstrooms = toerekening.reden_niet_bovenstrooms("NL94_6", "NL91ZM", True)
    onplaatsbaar = toerekening.reden_niet_bovenstrooms("NL90_1", "NL91ZM", True)
    erbuiten = toerekening.reden_niet_bovenstrooms("NL93_IJSSEL", "NL91ZM", False)
    assert "benedenstrooms" in benedenstrooms
    assert "stroomschema" in onplaatsbaar and "kanalen" in onplaatsbaar
    assert "buiten het stroomgebied" in erbuiten
    assert len({benedenstrooms, onplaatsbaar, erbuiten}) == 3


def test_zonder_register_wordt_dat_gezegd_en_niet_stil_uitgesloten():
    r = toerekening.reden_niet_bovenstrooms("NL99_X", "NL91ZM", None)
    assert "niet te bepalen" in r and "register" in r


def test_een_vergunning_zonder_waterlichaam_houdt_haar_eigen_reden():
    assert "geen waterlichaam" in toerekening.reden_niet_bovenstrooms(None, "NL91ZM", True)


# --- het filter ---------------------------------------------------------------------------

def _filter(per_sleutel, wl_meetpunt="NL91ZM", redenen=None):
    return service._filter_op_stroomgebied(per_sleutel, redenen or {}, wl_meetpunt, _REGISTER)


def test_benedenstroomse_vergunningen_worden_geteld_maar_niet_opgesomd():
    """Anders staat bij het bovenste meetpunt zestig keer dezelfde zin in de uitsluitlijst."""
    houden, redenen, telling = _filter({"A": "NL91BOM", "B": "NL94_6", "C": "NL94_6"})
    assert list(houden) == ["A"]
    assert redenen == {}, "benedenstrooms hoort in de telling, niet in de lijst"
    assert telling["benedenstrooms"] == 2
    assert telling["meegerekend"] == 1


def test_een_onplaatsbare_of_buitenlandse_vergunning_krijgt_wel_een_reden():
    houden, redenen, telling = _filter({"A": "NL90_1", "B": "NL93_IJSSEL"})
    assert houden == {}
    assert set(redenen) == {"A", "B"}
    assert telling["zonder_positie"] == 1 and telling["buiten_stroomgebied"] == 1


def test_bestaande_redenen_blijven_staan_en_worden_geteld():
    houden, redenen, telling = _filter({"A": "NL91BOM"},
                                       redenen={"Z": "geen coördinaat in de bron"})
    assert houden == {"A"} if isinstance(houden, set) else list(houden) == ["A"]
    assert redenen["Z"] == "geen coördinaat in de bron"
    assert telling["zonder_waterlichaam"] == 1


# --- de stroomvolgorde ---------------------------------------------------------------------

def test_het_julianakanaal_ligt_bovenstrooms_van_de_zandmaas():
    """Het kanaal loopt langs de Grensmaas en komt bij Maasbracht op de Maas uit."""
    assert toerekening.is_bovenstrooms("NL91JK", "NL91ZM") is True
    assert toerekening.is_bovenstrooms("NL91ZM", "NL91JK") is False


def test_de_twee_onplaatsbare_waterlichamen_tellen_nergens_mee():
    for code in toerekening.ZONDER_POSITIE:
        assert toerekening.is_bovenstrooms(code, "NL94_11") is False, code


def test_de_volgorde_is_nog_steeds_een_keten_zonder_dubbele_codes():
    codes = [c for c, _n in toerekening.STROOMVOLGORDE]
    assert len(codes) == len(set(codes))
    assert codes[0] == "NL91BOM", "de Bovenmaas is het bovenste waterlichaam"


# --- wat de pagina erover kan zeggen --------------------------------------------------------

def test_het_beeld_verantwoordt_zijn_afbakening(tmp_path):
    """De pagina moet kunnen zeggen waarop de afbakening berust, niet alleen wat eruit kwam."""
    from tests.test_kmg_service import PUNT, SET, _atlas

    p = tmp_path / "m.json"
    p.write_text(json.dumps({**SET, "punten": [PUNT]}), encoding="utf-8")
    b = service.beeld(PUNT["code"], str(p), live=True, _haal_regels=lambda rd: [],
                      _haal_atlas=_atlas, _haal_waterlichaam=lambda x, y: "NL91BOM")
    sg = b["stroomgebied"]
    assert sg["geplaatst"] == len(toerekening.STROOMVOLGORDE)
    assert [z["code"] for z in sg["zonder_positie"]] == sorted(toerekening.ZONDER_POSITIE)
    assert all(z["reden"] for z in sg["zonder_positie"])
    assert sg["straal_m"] > 50_000, "de straal haalt op, het district bepaalt wat meetelt"
