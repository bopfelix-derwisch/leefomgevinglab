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
