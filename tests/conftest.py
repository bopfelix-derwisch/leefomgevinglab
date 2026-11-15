import sys
from pathlib import Path

import pytest

# Add src to Python path so tests can import leefomgevinglab
src_path = Path(__file__).parent.parent / "src"
sys.path.insert(0, str(src_path))

# -- `.env` expliciet laden, hier en niet per ongeluk ------------------------------------------
#
# De live-tests lezen hun sleutel rechtstreeks uit `os.environ` (`os.environ["DSO_API_KEY"]`).
# Die stond daar tot nu toe alleen omdat `geluidsmeter/api.py` bij import `load_dotenv()`
# aanroept en bijna elk testbestand `api` importeert -- een **zijeffect van de
# collectievolgorde**. Gevolg: `pytest --run-live tests/test_dso_live.py` alleen faalde met
# `KeyError: 'DSO_API_KEY'` terwijl die sleutel in `.env` staat, en in een volledige run slaagde
# hij omdat een alfabetisch eerder bestand `api` al had geïmporteerd. Een test die om die reden
# groen is, is precies het defect dat dit project het meeste heeft gekost.
#
# **Dit schakelt de live-gate niet aan.** Die gate is sinds fix 3 losgekoppeld van elke
# omgevingsvariabele en hangt uitsluitend aan `--run-live` (zie `pytest_collection_modifyitems`
# hieronder). Hier wordt alleen gezorgd dat een sleutel die in `.env` staat ook bereikbaar is
# zodra je die vlag zet, ongeacht welke bestanden je selecteert.
_env = Path(__file__).parent.parent / ".env"
if _env.exists():                                   # pragma: no cover -- infrastructuur
    from dotenv import load_dotenv

    load_dotenv(_env)


def pytest_addoption(parser):
    parser.addoption(
        "--run-live", action="store_true", default=False,
        help=("voer ook de met `@pytest.mark.live` gemarkeerde tests uit -- die raken een "
              "echte externe bron over het netwerk of een zware lokale bron (zie "
              "live-fixes-report.md, fix 3). Standaard uit, ook als .env gesourcet is."),
    )


def pytest_collection_modifyitems(config, items):
    """Skipt elke `live`-gemarkeerde test, behalve met `--run-live`.

    Fix 3 (taakrapport): de oude gate was `skipif(not os.environ.get("DSO_API_KEY"))`, maar
    `geluidsmeter/api.py` roept `load_dotenv()` aan bij import, en bijna elk testbestand
    importeert `api` -- dus stond die sleutel altijd al in `os.environ` zodra de suite met
    `.env` gesourcet draaide, wat net het geval moet zijn waarin de rest van de suite werkt. Dit
    is losgekoppeld van elke omgevingsvariabele: alleen de expliciete vlag telt."""
    if config.getoption("--run-live"):
        return
    skip_live = pytest.mark.skip(
        reason="live-test: staat standaard uit, voer uit met `pytest --run-live` "
               "(DSO_API_KEY in .env schakelt dit niet meer aan, zie live-fixes-report.md fix 3)")
    for item in items:
        if "live" in item.keywords:
            item.add_marker(skip_live)
