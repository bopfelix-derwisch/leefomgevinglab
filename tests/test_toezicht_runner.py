"""`toezicht.runner` -- de agentrunner en de CrewAI-compatibele configuratie (taak 6).

Geen netwerk, geen taalmodel: de drie agents die vandaag een echte taak hebben (vergunninglezer,
signaalsteller, dossiersteller) zijn stuk voor stuk deterministisch, en draaien hier met
`llm=None`. `AGENTS`/`TASKS` wijzen naar de echte configuratie in
`src/leefomgevinglab/usecases/toezicht/config/` -- dezelfde bestanden die de productie-pijplijn
gebruikt, niet een test-kopie.
"""
import os

import pytest
import yaml

from leefomgevinglab.usecases.toezicht import runner
from tests.test_toezicht_signalen import CONTEXT_MET_ALLES, VESTIGING_MET_ALLES

_CONFIG_DIR = os.path.join(os.path.dirname(runner.__file__), "config")
AGENTS = os.path.join(_CONFIG_DIR, "agents.yaml")
TASKS = os.path.join(_CONFIG_DIR, "tasks.yaml")

# Gedeeld met `test_toezicht_runlog.py` -- dezelfde fixture als `test_toezicht_dossier.py` al
# gebruikt, hier onder de naam die de brief voor taak 6b aanhoudt.
VESTIGING_FIXTURE = VESTIGING_MET_ALLES
CONTEXT = CONTEXT_MET_ALLES


# -- Stap 1: een onbekende tool faalt bij het laden ---------------------------------------------

def test_een_agent_die_een_onbekende_tool_vraagt_faalt_bij_het_laden():
    with pytest.raises(runner.OnbekendeTool) as f:
        runner.laad_uit_dict({"a": {"role": "x", "goal": "y", "tools": ["bestaat_niet"]}}, {})
    assert "bestaat_niet" in str(f.value)


# -- Stap 2: alleen het eigen verklaarde gereedschap, eis (a), de scherpere helft ----------------

def test_een_agent_mag_alleen_zijn_eigen_verklaarde_gereedschap_gebruiken():
    """Een onbekende tool weigeren is niet genoeg. Zou een agent een bestaande tool mogen
    aanroepen die niet in zijn `tools` staat, dan beschrijft de YAML het proces in plaats van
    het te besturen -- en dan is de transparantie die zij belooft niet waar."""
    crew = runner.laad_uit_dict(
        {"leesagent": {"role": "x", "goal": "y", "tools": ["atlas_vergunningen"]}},
        {"t1": {"description": "d", "expected_output": "e", "agent": "leesagent"}})
    with pytest.raises(runner.NietVerklaardeTool) as f:
        crew.tools_voor("leesagent")["signalen_stellen"]
    assert "signalen_stellen" in str(f.value)
    assert "leesagent" in str(f.value)


# -- Stap 3: zonder llm voor de deterministische agents ------------------------------------------

def test_de_standaardpijplijn_draait_zonder_llm_en_levert_een_dossier():
    """De deterministische agents (vergunninglezer, signaalsteller, dossiersteller) hebben geen
    taalmodel nodig -- `llm=None` (de standaard van `draai()`) moet het volledige dossier
    opleveren."""
    crew = runner.laad(AGENTS, TASKS)
    uitkomst = crew.draai({"vestiging": VESTIGING_FIXTURE, "context": CONTEXT})
    dossier = uitkomst["dossier"]
    assert dossier["signalen"], "de fixture laat alle regels vuren, dus hier moeten signalen staan"
    assert dossier["kaart"]["naam"]["waarde"] == VESTIGING_FIXTURE["naam"]


def test_agents_zonder_llm_sleutel_krijgen_nooit_een_taalmodel_ook_als_de_run_er_een_meekrijgt():
    """De §4.4-grens, nu met een llm die wél is meegegeven aan `draai()`: signaalsteller en
    vergunninglezer mogen hem alsnog niet krijgen, want hun agent-configuratie draagt geen
    `llm`-sleutel. Dit is de grens zelf, niet alleen het gevolg ervan (zie
    `test_toezicht_runlog.test_tijdens_de_signaalbepaling_komt_er_geen_taalmodel_aan_te_pas` voor
    het gevolg)."""
    crew = runner.laad(AGENTS, TASKS)
    aangeroepen_met_llm = []

    def spion_llm(prompt):
        aangeroepen_met_llm.append(prompt)
        return "SELECT * WHERE { ?s ?p ?o } LIMIT 1"

    crew.draai({"vestiging": VESTIGING_FIXTURE, "context": CONTEXT}, llm=spion_llm)
    assert aangeroepen_met_llm == [], \
        "geen van de taken in de standaardpijplijn mag het taalmodel aanroepen"


# -- Stap 5: de YAML gebruikt de CrewAI-velden ---------------------------------------------------

def test_agents_yaml_gebruikt_de_crewai_velden_en_telt_zes_agents():
    with open(AGENTS, encoding="utf-8") as f:
        agents = yaml.safe_load(f)
    assert set(agents) == {"vergunninglezer", "signaalsteller", "dossiersteller", "uitlegger",
                            "vraagsteller", "terugkoppelaar"}
    for naam, cfg in agents.items():
        for veld in ("role", "goal", "backstory", "tools"):
            assert veld in cfg, (naam, veld)


def test_tasks_yaml_gebruikt_de_crewai_velden():
    with open(TASKS, encoding="utf-8") as f:
        tasks = yaml.safe_load(f)
    assert len(tasks) >= 3
    for naam, cfg in tasks.items():
        for veld in ("description", "expected_output", "agent", "context"):
            assert veld in cfg, (naam, veld)
        assert cfg["agent"] in {"vergunninglezer", "signaalsteller", "dossiersteller",
                                 "uitlegger", "vraagsteller", "terugkoppelaar"}


def test_signaalsteller_en_vergunninglezer_dragen_geen_llm_sleutel():
    """De §4.4-belofte ook statisch gecontroleerd: deze twee agents mogen de sleutel `llm` niet
    eens hebben staan, los van wat een run ermee zou doen (zie de dynamische pendant hierboven en
    in `test_toezicht_runlog.py`)."""
    with open(AGENTS, encoding="utf-8") as f:
        agents = yaml.safe_load(f)
    assert "llm" not in agents["signaalsteller"]
    assert "llm" not in agents["vergunninglezer"]


# -- Een verklaarde, nog niet gebouwde tool laadt gewoon; aanroepen is een andere zaak -----------

def test_een_verklaarde_maar_nog_niet_gebouwde_tool_laadt_zonder_te_falen():
    """`uitlegger` staat al in de configuratie met zijn echte, toekomstige tool (taak 7) -- het
    laden mag daar niet op stuklopen, want dat zou de hele configuratie onbruikbaar maken zolang
    taak 7 niet klaar is."""
    crew = runner.laad(AGENTS, TASKS)
    assert "uitleg_genereren" in crew.agents["uitlegger"]["tools"]
    assert "uitleg_genereren" in runner.GEPLAND
    assert "uitleg_genereren" not in runner.TOOLS


def test_het_opvragen_van_een_nog_niet_gebouwde_tool_geeft_nietbeschikbaar():
    crew = runner.laad(AGENTS, TASKS)
    with pytest.raises(runner.NietBeschikbaar):
        crew.tools_voor("uitlegger")["uitleg_genereren"]


# -- Fixronde 1, bevinding 2 (Important): de guard moet dragend zijn, niet alleen de loopstructuur

def test_draai_haalt_elke_callable_op_via_tools_voor_niet_rechtstreeks_uit_tools():
    """Eis (a) moet afgedwongen worden door `tools_voor()` zelf, niet alleen doordat `draai()`
    toevallig over de eigen `tools`-lijst van de agent itereert. Deze test bewijst dat `draai()`
    `tools_voor` ook echt aanroept, voor elke taak die een tool draait, door de methode te
    bespieden -- geen gedragstest op de uitkomst (die was al groen), maar op het mechanisme."""
    crew = runner.laad(AGENTS, TASKS)
    aangeroepen_voor: list[str] = []
    origineel = crew.tools_voor

    def spion(agent_naam: str):
        aangeroepen_voor.append(agent_naam)
        return origineel(agent_naam)

    crew.tools_voor = spion
    crew.draai({"vestiging": VESTIGING_FIXTURE})
    # De drie deterministische agents draaien allemaal een tool in de standaardpijplijn, en
    # `uitlegger` ook (zijn tool is alleen nog niet gebouwd) -- `tools_voor` moet voor elk van hen
    # zijn aangeroepen, niet alleen voor de agents waarvan de tool toevallig al bestaat.
    assert aangeroepen_voor.count("vergunninglezer") == 1
    assert aangeroepen_voor.count("signaalsteller") == 1
    assert aangeroepen_voor.count("dossiersteller") == 1
    assert aangeroepen_voor.count("uitlegger") == 1


# -- De twee tools van `vraagsteller`: nog zonder taak in de standaardpijplijn, maar wél echt en
# dus hier rechtstreeks getoetst, los van een draaiende crew. ------------------------------------

def test_toezichtgraaf_bouwen_bouwt_een_graaf_zonder_netwerk():
    uitkomst = runner.TOOLS["toezichtgraaf_bouwen"]({"register": [VESTIGING_FIXTURE]})
    assert "graaf" in uitkomst.updates
    assert uitkomst.rijen_in == 1


def test_vraag_stellen_gebruikt_alleen_de_meegegeven_llm_nooit_een_echte_verbinding():
    def nep_llm(prompt: str) -> str:
        return "SELECT ?s WHERE { ?s a <https://leefomgevinglab.felixisfelix.com/toezicht#Vestiging> } LIMIT 1"

    graaf_uitkomst = runner.TOOLS["toezichtgraaf_bouwen"]({"register": [VESTIGING_FIXTURE]})
    staat = {"vraag": "Welke vestigingen staan er?", "graaf": graaf_uitkomst.updates["graaf"]}
    uitkomst = runner.TOOLS["vraag_stellen"](staat, llm=nep_llm)
    assert uitkomst.updates["antwoord"]["beschikbaar"] is True
    assert uitkomst.updates["antwoord"]["sparql"] is not None
