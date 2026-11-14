"""Optionele live smoke-test tegen DSO pre-productie. Staat standaard uit (marker `live`, zie
fix 3, live-fixes-report.md -- aanzetten met `pytest --run-live`; vereist dan nog steeds een
echte `DSO_API_KEY` in de omgeving, want die wordt hier als auth-sleutel gebruikt)."""
import os

import pytest

pytestmark = pytest.mark.live

ZOEK = "https://service.pre.omgevingswet.overheid.nl/publiek/toepasbare-regels/api/zoekinterface/v2"
RTR = ("https://service.pre.omgevingswet.overheid.nl/publiek/toepasbare-regels/api/"
       "samengestelderegistratietoepasbareregelsservices/v2")
UITVOEREN = ("https://service.pre.omgevingswet.overheid.nl/publiek/toepasbare-regels/api/"
             "toepasbareregelsuitvoerenservices/v3")


def test_live_dakkapel_keten(tmp_path):
    from leefomgevinglab.connectors.dso_zoek import ZoekConnector
    from leefomgevinglab.connectors.dso import DsoConnector

    key = os.environ["DSO_API_KEY"]
    zoek = ZoekConnector(base_url=ZOEK, api_key=key, cache_dir=str(tmp_path))
    kand = zoek.zoek_werkzaamheden("dakkapel")
    assert any(k["urn"] == "DakkapelPlaatsen" for k in kand)

    ref = next(k["functioneleStructuurRef"] for k in kand if k["urn"] == "DakkapelPlaatsen")
    dso = DsoConnector(rtr_base_url=RTR, uitvoeren_base_url=UITVOEREN,
                       rtr_api_key=key, uitvoeren_api_key=key, cache_dir=str(tmp_path))
    typ = dso.bepaal_typeringen([ref], (155000.0, 463000.0))
    assert typ and "regelbeheerobjecten" in typ[0]
