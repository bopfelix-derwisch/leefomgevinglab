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

from leefomgevinglab.usecases.toezicht import runlog, runner
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
    """De §4.4-grens, nu met een llm die wél is meegegeven aan `draai()`: signaalsteller,
    vergunninglezer en dossiersteller mogen hem alsnog niet krijgen, want hun agent-configuratie
    draagt geen `llm`-sleutel.

    **Herschreven in fix-ronde 1 van taak 7.** Vóór taak 7 was "geen enkele taak roept het
    taalmodel aan" toevallig ook waar voor `uitlegger`, simpelweg omdat zijn tool nog niet
    bestond (`GEPLAND`). Sinds taak 7 heeft `uitlegger` wél een echte tool én een `llm`-sleutel in
    zijn configuratie, en met deze fixture (die `norm_overschreden_bovenstrooms` laat vuren, wat
    de /kmg-proclaimer-bron activeert) gebruikt hij die ook echt -- dat is geen schending van
    §4.4, want die grens gaat juist over agents *zonder* de sleutel. Deze test kijkt daarom per
    agent naar het `llm`-veld in de runlog, niet naar één globaal spion-logboek dat niet
    onderscheidt wie het taalmodel aanriep."""
    log = runlog.Runlog()
    crew = runner.laad(AGENTS, TASKS)

    def spion_llm(prompt):
        return "nette tekst"

    crew.draai({"vestiging": VESTIGING_FIXTURE, "context": CONTEXT}, llm=spion_llm, runlog=log)
    gecontroleerd = {"vergunninglezer", "signaalsteller", "dossiersteller"}
    geziene_agents = set()
    for s in log.als_gegeven():
        if s["agent"] in gecontroleerd:
            geziene_agents.add(s["agent"])
            assert s["llm"] is False, f"{s['agent']} gebruikte een taalmodel in stap {s['nr']}"
    # Fix-ronde 2, bevinding C (R21): zonder deze assertie zou de lus hierboven ook slagen als
    # géén van de drie ooit een stap logde -- een hernoemde agent of een geschrapte taak zou de
    # scherpste grens van het plan ongemerkt ontwapenen terwijl de test groen bleef.
    assert geziene_agents == gecontroleerd, (
        f"niet alle drie de agents zonder llm-sleutel logden een stap: gezien {geziene_agents}, "
        f"verwacht {gecontroleerd} -- de toets hierboven is dan vacuüm")


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

def test_uitleg_en_terugkoppeling_zijn_sinds_taak_7_echte_tools_geen_geplande():
    """Tot taak 7 stonden `uitleg_genereren`/`terugkoppeling_genereren` alleen aangekondigd in
    `runner.GEPLAND` (zie de git-geschiedenis van deze test). Nu zijn het echte `TOOLS`, en
    `GEPLAND` draagt geen van beide meer -- het laden mocht toen al niet stuklopen op een
    aangekondigde-maar-nog-niet-gebouwde tool, en dat blijft zo getest zodra er weer zo'n tool
    bijkomt (zie `test_een_onbekende_tool_...` hierboven voor dat mechanisme zelf)."""
    crew = runner.laad(AGENTS, TASKS)
    assert "uitleg_genereren" in crew.agents["uitlegger"]["tools"]
    assert "terugkoppeling_genereren" in crew.agents["terugkoppelaar"]["tools"]
    assert "uitleg_genereren" in runner.TOOLS
    assert "terugkoppeling_genereren" in runner.TOOLS
    assert "uitleg_genereren" not in runner.GEPLAND
    assert "terugkoppeling_genereren" not in runner.GEPLAND


def test_het_opvragen_van_de_uitleg_tool_geeft_de_echte_callable():
    """De pendant van de oude `NietBeschikbaar`-test: nu de tool gebouwd is, geeft `tools_voor`
    de echte functie terug, niet langer een fout."""
    crew = runner.laad(AGENTS, TASKS)
    assert crew.tools_voor("uitlegger")["uitleg_genereren"] is runner.tool_uitleg_genereren
    assert (crew.tools_voor("terugkoppelaar")["terugkoppeling_genereren"]
            is runner.tool_terugkoppeling_genereren)


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


# -- Een losse actie buiten de pijplijn (de vraagweg) -------------------------------------------

def test_los_uitvoeren_draait_de_tool_van_die_agent_met_zijn_eigen_llm_grens():
    """`vraagsteller` en `terugkoppelaar` hebben géén taak in `tasks.yaml`: hun werk is een los
    te starten actie, niet een vaste stap in elke dossier-run (zo staat het ook in `agents.yaml`).
    Die actie moet toch door de agentconfiguratie heen lopen, anders is die configuratie voor dit
    pad decoratie -- en dan doet een route het werk van een agent achter zijn rug om, precies de
    toestand waarvoor `gedraaide_agents` een 'onbekend'-melding kent."""
    crew = runner.laad(AGENTS, TASKS)
    log = runlog.Runlog()
    gezien = {}

    def nep_tool(staat, *, llm=None, runlog=None):
        gezien["llm"] = llm
        if llm is not None:
            llm("prompt")
        return runner.Uitkomst({"antwoord": "ok"}, 1, 1, args={})

    uit = crew.los_uitvoeren("uitlegger", "uitleg_genereren", {"x": 1},
                              llm=lambda p: "antwoord", runlog=log, tool=nep_tool)
    assert uit["antwoord"] == "ok"
    assert gezien["llm"] is not None, "de uitlegger heeft een llm-sleutel, dus mag er een"
    stappen = log.als_gegeven()
    assert len(stappen) == 1
    assert stappen[0]["agent"] == "uitlegger"
    assert stappen[0]["llm"] is True, "het model is echt aangeroepen, dus staat dat in de log"


def test_los_uitvoeren_geeft_een_agent_zonder_llm_sleutel_nooit_een_model():
    """De §4.4-grens geldt ook buiten de pijplijn. Zou een losse actie die grens omzeilen, dan is
    de hele belofte van dit lab via één route te ontlopen."""
    crew = runner.laad(AGENTS, TASKS)
    gezien = {}

    def nep_tool(staat, *, llm=None, runlog=None):
        gezien["llm"] = llm
        return runner.Uitkomst({"antwoord": None}, 0, 0, args={})

    crew.los_uitvoeren("signaalsteller", "signalen_stellen", {},
                        llm=lambda p: "x", tool=nep_tool)
    assert gezien["llm"] is None, (
        "signaalsteller heeft geen llm-sleutel en mag er dus ook in een losse actie geen krijgen")


def test_los_uitvoeren_weigert_een_tool_die_deze_agent_niet_verklaard_heeft():
    """Zelfde eis als in de pijplijn: de tool komt via de eigen `tools`-lijst van de agent."""
    crew = runner.laad(AGENTS, TASKS)
    with pytest.raises(runner.NietVerklaardeTool):
        crew.los_uitvoeren("signaalsteller", "vraag_stellen", {})
