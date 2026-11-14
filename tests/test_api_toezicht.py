"""`/toezicht` -- de pagina en de eindpunten (taak 8).

Geen netwerk hier: `_toezicht_register`/`_toezicht_aquo_ref`/`_toezicht_normenset`/
`_stelselcatalogus` worden per test gemonkeypatcht, net zoals `load_config` dat al overal in
`test_api_water.py`/`test_api_kmg.py` is. De vier stappen uit de taakbrief staan hier letterlijk
terug, met twee aanpassingen die de controller al als planfout had benoemd (R4/R19): de
pijplijnvergelijking gebruikt `pijplijn.als_gegeven(...)`, niet `runner.laad(...).als_gegeven()`
(dat bestaat niet -- `als_gegeven` hoort bij de module, niet bij `Crew`), en de `heeft_llm`-test
toetst eligibility, niet gebruik (zie de correctie van de controller: het runlog-veld `llm`
betekent vandaag "mocht een taalmodel krijgen", niet "heeft er een gebruikt").
"""
from fastapi.testclient import TestClient

import leefomgevinglab.geluidsmeter.api as api
from leefomgevinglab.usecases import water_hub as wh
from leefomgevinglab.usecases.toezicht import pijplijn
from tests.test_toezicht_runner import AGENTS, TASKS


def _client(monkeypatch):
    monkeypatch.setattr(api, "load_config", lambda *a, **k: api._config)
    return TestClient(api.app)


FIXTURE_VESTIGING = {
    "naam": "Testvestiging BV", "plaats": "Venlo", "locatie": None,
    "locatiecode": "TEST01", "vestigingsnummer_kvk": "000012345678",
    "kenmerk": None, "besluitdatum": "2020-01-01", "url": "https://example.org/vergunning",
    "voorschriften": [
        {"parameter": "Zink", "waarde": 0.5, "eenheid": "milligram per liter",
         "bemonstering": "Steekmonster"},
        {"parameter": "Zink", "waarde": 2.0, "eenheid": "milligram per liter",
         "bemonstering": "Steekmonster"},
    ],
}

FIXTURE_AQUO_REF = {"beschikbaar": True, "geldig": {"zink": "Zn"}, "vervallen": {},
                     "vervangen_door": {}, "aantal": {}}
FIXTURE_NORMENSET = {"beschikbaar": False, "normen": {}}


def _monkeypatch_bronnen(monkeypatch, register=(FIXTURE_VESTIGING,)):
    """De vier live bronnen van `/api/toezicht/dossier` vervangen door vaste data -- precies de
    drie die R20 bekabelt (`aquo_ref`, `normenset`, `stelselcatalogus`) plus het register zelf."""
    monkeypatch.setattr(api, "_toezicht_register", lambda: list(register))
    monkeypatch.setattr(api, "_toezicht_aquo_ref", lambda: FIXTURE_AQUO_REF)
    monkeypatch.setattr(api, "_toezicht_normenset", lambda: FIXTURE_NORMENSET)
    monkeypatch.setattr(api, "_stelselcatalogus", lambda: None)


# -- Stap 1: de open-data-banner --------------------------------------------------------------

def test_de_pagina_draagt_de_open_data_banner(monkeypatch):
    """Zonder deze banner suggereert de pagina een bevoegdheid die dit lab niet heeft."""
    h = _client(monkeypatch).get("/toezicht").text.lower()
    assert "open data" in h
    assert "geen bevoegdheid" in h
    assert "geen oordeel" in h
    assert "zonder authenticatie" in h
    assert "zonder logging" in h


# -- Stap 2: de taalregel op de echte HTML -----------------------------------------------------

def test_de_pagina_haalt_de_taalregel_op_de_echte_html(monkeypatch):
    h = _client(monkeypatch).get("/toezicht").text.lower()
    assert "overtreding" not in h
    assert "veroorzaakt door" not in h
    assert "in strijd met" not in h


# -- Stap 3: de pijplijn op de pagina komt uit dezelfde configuratie als de runner --------------

def test_de_pijplijn_op_de_pagina_komt_uit_dezelfde_configuratie_als_de_runner(monkeypatch):
    """Een getekende keten naast een draaiende keten gaat uiteenlopen; dan toont de pagina een
    proces dat niet meer bestaat. Daarom één bron voor beide.

    Aangepast t.o.v. de letterlijke testcode in de brief (R4): die riep
    `runner.laad(AGENTS_PAD, TASKS_PAD).als_gegeven()` aan, en die methode bestaat niet op
    `Crew` -- `als_gegeven` hoort bij `pijplijn.py` (zie de moduledocstring daar). Verder is het
    veld `naam` in de brief in werkelijkheid `id` (zie `test_toezicht_pijplijn.py`)."""
    uit_api = _client(monkeypatch).get("/api/toezicht/pijplijn").json()
    uit_module = pijplijn.als_gegeven(AGENTS, TASKS)
    assert [a["id"] for a in uit_api["agents"]] == [a["id"] for a in uit_module["agents"]]
    assert uit_api["bron"].endswith("agents.yaml")


# -- Stap 4: per agent zichtbaar of een taalmodel mag meedoen -----------------------------------

def test_de_pijplijn_toont_per_agent_of_een_taalmodel_mag_meedoen(monkeypatch):
    """Dat is wat een lezer het eerst wil weten en wat in code onzichtbaar is.

    `heeft_llm` is hier eligibility (staat de `llm`-sleutel in de agentconfiguratie), niet "heeft
    in deze run een taalmodel gebruikt" -- dat tweede kan de runlog alleen per stap zeggen (zie
    `test_het_dossier_endpoint_draait_zonder_taalmodel_en_toont_dat_ook_zo` hieronder), en de
    twee mogen op deze pagina niet door elkaar heen gelezen worden (correctie van de controller)."""
    d = _client(monkeypatch).get("/api/toezicht/pijplijn").json()
    heeft_llm = {a["id"]: a["heeft_llm"] for a in d["agents"]}
    assert heeft_llm["signaalsteller"] is False
    assert heeft_llm["vergunninglezer"] is False
    assert heeft_llm["uitlegger"] is True
    r = _client(monkeypatch).get("/toezicht")
    assert "heeft_llm" in r.text, "de pagina rendert het veld niet"
    assert "mag taalmodel" in r.text, "de pagina labelt het veld niet als eligibility"


# -- Route, hub-lid, pagina ----------------------------------------------------------------------

def test_toezicht_is_lid_van_het_waterdossier_en_krijgt_geen_eigen_kaart(monkeypatch):
    """R6: géén apart lid op de homepagina -- de hub zegt wat erbij hoort."""
    assert wh.lid("toezicht")["pad"] == "/toezicht"
    r = _client(monkeypatch).get("/")
    assert 'href="/toezicht"' not in r.text


def test_toezichtpagina_geeft_200_met_de_subnav(monkeypatch):
    r = _client(monkeypatch).get("/toezicht")
    assert r.status_code == 200
    assert 'class="waternav"' in r.text
    assert r.text.count('aria-current="page"') == 1
    assert "__WATERNAV__" not in r.text


def test_vestigingen_endpoint_geeft_een_lijst(monkeypatch):
    _monkeypatch_bronnen(monkeypatch)
    r = _client(monkeypatch).get("/api/toezicht/vestigingen")
    assert r.status_code == 200
    d = r.json()
    assert d == [{"locatiecode": "TEST01", "naam": "Testvestiging BV", "plaats": "Venlo"}]


def test_onbekende_vestiging_geeft_404(monkeypatch):
    _monkeypatch_bronnen(monkeypatch)
    r = _client(monkeypatch).get("/api/toezicht/dossier?vestiging=BESTAAT_NIET")
    assert r.status_code == 404


# -- R20: de drie bronnen voor de uitlegger zijn echt bekabeld -----------------------------------

def test_het_dossier_endpoint_bekabelt_de_drie_bronnen_en_een_signaal_krijgt_een_waarom(monkeypatch):
    """Vóór taak 8 zette `pijplijn`/de runner-aanroep geen van `aquo_ref`, `normenset` of
    `stelselcatalogus` -- dus kreeg geen signaal in een echte run een `waarom` (R20). Deze test
    draait de echte pijplijn (geen gemockte `dossier()`) met de drie bronnen bekabeld en toont
    dat het wél gebeurt."""
    _monkeypatch_bronnen(monkeypatch)
    r = _client(monkeypatch).get("/api/toezicht/dossier?vestiging=TEST01")
    assert r.status_code == 200
    d = r.json()
    signalen = d["signalen"]
    assert signalen, "geen signalen -- de fixture triggert geen regel"
    assert any(s.get("waarom") for s in signalen), (
        "geen signaal draagt een waarom -- de drie bronnen zijn niet bekabeld")
    gevonden = next(s for s in signalen if s.get("waarom"))
    assert "Zn" in gevonden["waarom"] or "zink" in gevonden["waarom"].lower()


def test_het_dossier_endpoint_draait_zonder_taalmodel_en_toont_dat_ook_zo(monkeypatch):
    """De dossier-aanroep geeft `llm=None` mee (geen externe aanroep op de paginalading) --
    elke stap in de echte runlog van deze run draagt dus `llm: False`, ook de stappen van
    agents die wél een `llm`-sleutel in hun configuratie hebben (eligible, maar hier niet
    gebruikt). Dat onderscheid is precies de correctie van de controller."""
    _monkeypatch_bronnen(monkeypatch)
    d = _client(monkeypatch).get("/api/toezicht/dossier?vestiging=TEST01").json()
    stappen = d["runlog"]["stappen"]
    assert stappen, "de runlog van deze run is leeg"
    assert all(s["llm"] is False for s in stappen)
    # De volledige run, niet het tussentijdse snapshot dat `dossier()` zelf nam vóór haar eigen
    # stap en vóór de uitlegger erna.
    agenten = [s["agent"] for s in stappen]
    assert "uitlegger" in agenten, "de runlog mist de uitlegger-stap -- is het snapshot gebruikt?"
