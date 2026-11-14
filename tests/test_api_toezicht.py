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
# Minor (R20-review): import uit een ander testbestand. Bewust zo gelaten -- `tests/
# test_toezicht_pijplijn.py` doet exact hetzelfde (`from tests.test_toezicht_runner import
# AGENTS, TASKS`), dus dit volgt het bestaande patroon van dit lab (één bron voor de paden naar
# de echte configuratie) in plaats van een derde kopie van diezelfde twee regels te maken.
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

# Fix-ronde 1 (R20-review, finding "task 7 re-review"): `meerdere_grenswaarden` (de regel die
# FIXTURE_VESTIGING triggert) heeft geen stofnaam nodig om een `waarom` te krijgen -- de
# /kmg-proclaimer-bron kan op een heel ander trefwoord vuren en draagt zelf, in haar eigen
# illustratieve zin, de tekst "opgelost zink". Een test die alleen controleert dat "zink"
# ergens in de `waarom`-tekst staat, slaagt dus ook met nul bekabelde bronnen -- precies het
# gat dat de review vond. Deze vestiging triggert in plaats daarvan `vervallen_code`, een regel
# uit `_STOF_GEBONDEN_REGELS` (`runner._uitlegvraag`) die zonder een geïnjecteerde `aquo_ref`
# niet eens kan vuren (`aquo.verrijk` zet `aquo_status` alleen als `ref["beschikbaar"]`), dus
# "het signaal bestaat en draagt een waarom" is hier pas waar als de bron echt werkt.
FIXTURE_VESTIGING_VERVALLEN = {
    "naam": "Zwevende-stof BV", "plaats": "Venlo", "locatie": None,
    "locatiecode": "TEST02", "vestigingsnummer_kvk": "000098765432",
    "kenmerk": "ABC/123", "besluitdatum": "2019-01-01", "url": "https://example.org/zwevend",
    "voorschriften": [
        {"parameter": "Zwevende stof", "waarde": 30.0, "eenheid": "milligram per liter"},
    ],
}
# Dezelfde naam ("zwevende stof") staat zowel in `vervallen` als -- in de echte bron -- soms in
# `geldig`; hier bewust alléén `vervallen`, zodat `aquo.verrijk` geen andere tak kan kiezen.
FIXTURE_AQUO_REF_VERVALLEN = {"beschikbaar": True, "geldig": {},
                              "vervallen": {"zwevende stof": "ZS"}, "vervangen_door": {}}


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

def test_het_dossier_endpoint_bekabelt_de_aquo_bron_en_vervallen_code_krijgt_een_waarom(monkeypatch):
    """Vóór taak 8 zette `pijplijn`/de runner-aanroep geen van `aquo_ref`, `normenset` of
    `stelselcatalogus` -- dus kreeg geen signaal in een echte run een `waarom` (R20). Deze test
    draait de echte pijplijn (geen gemockte `dossier()`) met `aquo_ref` bekabeld en toont dat
    `vervallen_code` -- een regel die zonder die bron niet eens kan vuren, zie de fixture-
    toelichting hierboven -- een `waarom` krijgt die expliciet naar de Aquo-domeintabel
    terugwijst, niet alleen toevallig het woord "zink" ergens bevat (de fout die de vorige
    versie van deze test maakte, gevonden in de re-review van taak 7)."""
    monkeypatch.setattr(api, "_toezicht_register", lambda: [FIXTURE_VESTIGING_VERVALLEN])
    monkeypatch.setattr(api, "_toezicht_aquo_ref", lambda: FIXTURE_AQUO_REF_VERVALLEN)
    monkeypatch.setattr(api, "_toezicht_normenset", lambda: FIXTURE_NORMENSET)
    monkeypatch.setattr(api, "_stelselcatalogus", lambda: None)
    r = _client(monkeypatch).get("/api/toezicht/dossier?vestiging=TEST02")
    assert r.status_code == 200
    d = r.json()
    s = next((x for x in d["signalen"] if x["regel"] == "vervallen_code"), None)
    assert s is not None, "vervallen_code vuurt niet -- de fixture of aquo.verrijk is gewijzigd"
    assert s.get("waarom"), "vervallen_code draagt geen waarom -- de aquo_ref-bron is niet bekabeld"
    assert "Aquo-domeintabel Parameter" in s["waarom"]
    assert any("Aquo-domeintabel Parameter" in v for v in (s.get("waarom_vindplaatsen") or [])), (
        "geen vindplaats naar de Aquo-domeintabel -- de harde regel vraagt een benoemde bron")


def test_zonder_de_aquo_bron_vuurt_vervallen_code_niet_en_dus_ook_geen_waarom(monkeypatch):
    """De negatieve controle die bij de vorige test hoort: dezelfde vestiging, maar nu zonder
    `aquo_ref` (`beschikbaar: False`, zoals een echte niet-gevonden referentie dat zelf al
    teruggeeft). `aquo.verrijk()` laat de vestiging dan onaangeroerd, dus `vervallen_code` kan
    niet vuren -- het signaal verdwijnt helemaal, niet alleen zijn `waarom`. Dat bewijst dat de
    vorige test écht van de bekabeling afhangt, en niet van iets dat altijd waar is."""
    monkeypatch.setattr(api, "_toezicht_register", lambda: [FIXTURE_VESTIGING_VERVALLEN])
    monkeypatch.setattr(api, "_toezicht_aquo_ref", lambda: {"beschikbaar": False})
    monkeypatch.setattr(api, "_toezicht_normenset", lambda: FIXTURE_NORMENSET)
    monkeypatch.setattr(api, "_stelselcatalogus", lambda: None)
    d = _client(monkeypatch).get("/api/toezicht/dossier?vestiging=TEST02").json()
    assert not any(s["regel"] == "vervallen_code" for s in d["signalen"]), (
        "vervallen_code vuurt ook zonder aquo_ref -- dat zou de vorige test leeg laten slagen"
    )


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


# -- Fix-ronde 1 (R20-review, bevinding 3): `uitgezet` moet meereizen, niet hardgecodeerd [] ------

class _FakeCrew:
    """Een crew die net genoeg doet om `api_toezicht_dossier` te laten denken dat `dossier()`
    een niet-lege `uitgezet`-lijst had berekend -- zonder dat de route zelf al een `uit`-sleutel
    in `invoer` moet zetten. Dat laatste gebeurt vandaag nergens (vandaar dat de bug onschadelijk
    was), maar de route moet de lijst die `dossier()` teruggeeft wél doorgeven, niet overschrijven
    met een hardgecodeerde `[]`."""

    def draai(self, invoer, llm=None, runlog=None):
        if runlog is not None:
            runlog.stap("vergunninglezer", "lees_vergunning", "atlas_vergunningen", 0, 0, False)
        return {"dossier": {"kaart": {}, "signalen": [], "telling": {}, "voorbehouden": [],
                             "runlog": {"uitgezet": ["uitlegger"], "stappen": []}}}


def test_de_api_behoudt_de_uitgezette_agenten_die_dossier_teruggeeft(monkeypatch):
    """`api_toezicht_dossier` zette `runlog["uitgezet"]` eerder altijd op `[]` in plaats van door
    te geven wat `dossier()` zelf berekende uit `invoer["uit"]` -- harmless vandaag (de route
    vult `uit` nergens), maar de lijst zou stilzwijgend verdwijnen zodra dat ooit wél gebeurt.
    Deze test monkeypatcht de crew zelf, zodat hij bewijst dat de route doorgeeft wat `dossier()`
    teruggeeft, los van of de route vandaag al een `uit`-sleutel vult."""
    _monkeypatch_bronnen(monkeypatch)
    monkeypatch.setattr(api.toezicht_runner, "laad", lambda *a, **k: _FakeCrew())
    r = _client(monkeypatch).get("/api/toezicht/dossier?vestiging=TEST01")
    assert r.status_code == 200
    assert r.json()["runlog"]["uitgezet"] == ["uitlegger"]
