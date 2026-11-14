"""Live smoke tegen de open REV WFS. Staat standaard uit (marker `live`, zie fix 3,
live-fixes-report.md -- aanzetten met `pytest --run-live`)."""
import pytest

pytestmark = pytest.mark.live

WFS = "https://rev-portaal.nl/geoserver/wfs"


def test_live_explosieaandachtsgebied_op_rd_punt(tmp_path):
    from leefomgevinglab.connectors.externe_veiligheid import ExterneVeiligheidConnector
    c = ExterneVeiligheidConnector(wfs_url=WFS, cache_dir=str(tmp_path))
    # RD-punt binnen een bekend explosieaandachtsgebied (Bungalowpark Hessenheem, propaan; geverifieerd 2026-06-24)
    treffers = c.aandachtsgebieden_op_punt("rev_public:ev_explosieaandachtsgebieden", (232003.1, 473064.6))
    assert len(treffers) >= 1
    assert treffers[0]["maatgevende_stof"] == "propaan"
