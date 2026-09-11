"""Lozingsdossier: bindt casus, stappen en annotatieset aan de gedeelde ketenmotor."""
from types import SimpleNamespace

from ..ketenkern import motor as kern
from . import aquo, stappen
from .casus import CASUS

DOSSIER = {"id": "lozing", "naam": "Directe lozing op een rijkswater",
           "afgeleid_van": "Aquo", "register": "Register Lozingen (bestaat niet)"}

_dossier = SimpleNamespace(DOSSIER=DOSSIER, CASUS=CASUS, STAPPEN=stappen.ALLE,
                           ANNOTATIES=aquo.ANNOTATIES)


def run_keten(live: bool = True, straal_m: int = 1000, _haal=None) -> dict:
    return kern.run(_dossier, live=live, straal_m=straal_m, _haal=_haal)
