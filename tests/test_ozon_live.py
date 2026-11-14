"""Live smoke tegen Ozon pre-prod. Staat standaard uit (marker `live`, zie fix 3,
live-fixes-report.md -- aanzetten met `pytest --run-live`; vereist dan nog steeds een echte
`DSO_API_KEY` in de omgeving, want die wordt hier als auth-sleutel gebruikt)."""
import os
import pytest

pytestmark = pytest.mark.live

OZON = "https://service.pre.omgevingswet.overheid.nl/publiek/omgevingsdocumenten/api/presenteren/v8"


def test_live_regelingen_op_punt(tmp_path):
    from leefomgevinglab.connectors.ozon import OzonConnector
    c = OzonConnector(base_url=OZON, api_key=os.environ["DSO_API_KEY"], cache_dir=str(tmp_path))
    regelingen = c.regelingen_op_punt((139784.0, 442870.0))
    assert len(regelingen) >= 1
    assert all("type" in r and "titel" in r for r in regelingen)
