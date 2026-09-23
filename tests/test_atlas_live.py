"""Live smoke tegen de Atlas voor een Schone Maas. Skipt zonder live-test-vlag.

De Atlas vraagt zelf geen sleutel; DSO_API_KEY is in deze repo de generieke vlag die
live-tests aanzet — test_ev_live.py doet hetzelfde voor de REV-WFS.
"""
import os
import pytest

from leefomgevinglab.connectors.smwk_atlas import SmwkAtlasConnector

pytestmark = pytest.mark.skipif(not os.environ.get("DSO_API_KEY"),
                                reason="live-tests uit (DSO_API_KEY niet gezet)")


def test_maastricht_geeft_echte_vergunningen(tmp_path):
    c = SmwkAtlasConnector(cache_dir=str(tmp_path))
    uit = c.vergunningen_bij_punt(177748.0, 321314.0, straal_m=5000)
    assert len(uit) >= 5, "verwacht ~11 vestigingen bij Maastricht"
    assert any(v["voorschriften"] for v in uit)
    # Niet elke vestiging heeft een vergunningkenmerk (bv. de RWZI's van Waterschapsbedrijf
    # Limburg, ontdubbeld op Locatiecode) — smwk_atlas.py laat dat bewust zichtbaar met
    # kenmerk: None in plaats van te filteren. Dus `any`, niet `all`.
    assert any(v["kenmerk"] for v in uit)


def test_deventer_ligt_buiten_het_maasstroomgebied(tmp_path):
    c = SmwkAtlasConnector(cache_dir=str(tmp_path))
    assert c.vergunningen_bij_punt(206800.0, 474000.0, straal_m=5000) == []


def test_de_velden_uit_de_spec_bestaan_nog(tmp_path):
    """Faalt luid als de Atlas zijn schema wijzigt."""
    c = SmwkAtlasConnector(cache_dir=str(tmp_path))
    uit = c.vergunningen_bij_punt(177748.0, 321314.0, straal_m=5000)
    v = next(v for v in uit if v["voorschriften"])["voorschriften"][0]
    assert {"parameter", "waarde", "eenheid"} <= set(v)


def test_posten_zonder_kenmerk_krijgen_hun_voorschriften_via_locatiecode(tmp_path):
    """Bevinding 1 van de eindreview: tabel 2 draagt 29 rijen met een leeg/NULL Kenmerk, verdeeld
    over zes Locatiecodes (HAVENS 7, RWZIB/RWZIL/RWZIW 5, RWZIV 4, JWMAAS 3) — geverifieerd
    2026-09-23. Zonder een koppeling op Locatiecode blijven die posten, waaronder vier
    rioolwaterzuiveringen, zonder voorschrift en dus zonder vracht."""
    c = SmwkAtlasConnector(cache_dir=str(tmp_path))
    uit = c.vergunningen_bij_punt(177748.0, 321314.0, straal_m=5000)
    gevonden = {v["locatiecode"] for v in uit if v["locatiecode"]}
    verwacht = {"HAVENS", "RWZIB", "RWZIL", "RWZIW", "RWZIV", "JWMAAS"}
    aanwezig = verwacht & gevonden
    assert aanwezig, "geen van de zes bekende locatiecodes binnen dit punt gevonden"
    for locatiecode in aanwezig:
        post = next(v for v in uit if v["locatiecode"] == locatiecode)
        assert post["voorschriften"], f"{locatiecode} heeft geen voorschriften gekregen"


def test_rwzib_en_rwzil_krijgen_een_stikstofmelding_in_plaats_van_stilzwijgend_niets():
    """De kernregressie uit de eindreview: RWZIB en RWZIL dragen een stikstof-grenswaarde van
    15 mg/l, maar zonder de Locatiecode-koppeling kregen ze helemaal geen voorschriften en dus
    ook geen 'onbepaald'-vermelding — ze telden stilzwijgend als 0 kg/jaar mee in
    `vergund_kg_jaar`. Geverifieerd 2026-09-23: geen van beide draagt een Debiet-voorschrift, dus
    een vracht is (terecht) niet te berekenen — maar dat moet nu als 'onbepaald' zichtbaar zijn,
    niet als niets."""
    import tempfile

    from leefomgevinglab.usecases.gebruiksruimte import atlas_register

    with tempfile.TemporaryDirectory() as td:
        c = SmwkAtlasConnector(cache_dir=td)
        posten = c.vergunningen_bij_punt(177748.0, 321314.0, straal_m=5000)
    d = atlas_register.naar_register(posten)
    register = {p["locatiecode"]: p for p in d["register"] if p["locatiecode"] in ("RWZIB", "RWZIL")}
    assert set(register) == {"RWZIB", "RWZIL"}, "RWZIB/RWZIL niet binnen dit punt gevonden"
    for locatiecode, post in register.items():
        stoffen_onbepaald = {o["parameter"] for o in post["onbepaald"]}
        heeft_vracht = "stikstof totaal" in post["vrachten"]
        heeft_onbepaald = "stikstof totaal" in stoffen_onbepaald
        assert heeft_vracht or heeft_onbepaald, (
            f"{locatiecode} draagt geen enkele stikstofmelding — nog steeds stilzwijgend 0")
