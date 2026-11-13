"""`toezicht.runlog` -- de procesherkomst als onderdeel van het product (taak 6b).

Verbatim uit de taakbrief: de eerste twee tests hieronder zijn letterlijk overgenomen (stap 1 en
2 van taak 6b) en dragen de zwaarste last van deze use-case -- zij bewijzen per run, niet in
proza, dat de signaalbepaling zonder taalmodel gebeurt en dat geen toolaanroep onder water blijft.
"""
import pytest

from leefomgevinglab.usecases.toezicht import dossier, runlog, runner
from tests.test_toezicht_runner import AGENTS, CONTEXT, TASKS, VESTIGING_FIXTURE


# -- Stap 1 (brief, verbatim): elke toolaanroep komt in de runlog -------------------------------

def test_elke_toolaanroep_komt_in_de_runlog():
    """Een stap die niet gelogd wordt, is een stap die onder water gebeurt."""
    crew, log = runner.laad(AGENTS, TASKS), runlog.Runlog()
    crew.draai({"vestiging": VESTIGING_FIXTURE}, runlog=log)
    aangeroepen = {s["tool"] for s in log.als_gegeven() if s["tool"]}
    assert aangeroepen == crew.verwachte_tools(), \
        "de runlog en de configuratie lopen uiteen"


# -- Stap 2 (brief, verbatim): de LLM-grens van §4.4, per run bewezen ----------------------------

def test_tijdens_de_signaalbepaling_komt_er_geen_taalmodel_aan_te_pas():
    """De belofte uit §4.4, per run bewezen in plaats van in proza beloofd.

    Dit is de test die de hele transparantieclaim draagt: wie hem weghaalt, houdt een
    configuratie over die iets zegt wat niemand meer narekent.
    """
    log = runlog.Runlog()
    runner.laad(AGENTS, TASKS).draai({"vestiging": VESTIGING_FIXTURE}, runlog=log)
    for s in log.als_gegeven():
        if s["agent"] in ("vergunninglezer", "signaalsteller"):
            assert s["llm"] is False, f"{s['agent']} gebruikte een taalmodel in stap {s['nr']}"


# -- Stap 3 (brief, verbatim): een uitgezette agent staat als uitgezet in het dossier ------------

def test_een_uitgezette_agent_staat_als_uitgezet_in_het_dossier():
    d = dossier.dossier(VESTIGING_FIXTURE, CONTEXT, uit={"uitlegger"})
    assert d["runlog"]["uitgezet"] == ["uitlegger"]
    assert all(not s.get("waarom") for s in d["signalen"])
    assert "uitlegger stond uit" in d["voorbehouden"][0]


# -- Eigen tests: de rest van de demands (b)/(d), en de `Runlog`-klasse zelf ---------------------

def test_runlog_nummert_telt_llm_gebruik_en_totale_duur():
    log = runlog.Runlog()
    log.stap("a", "t1", "tool1", 3, 2, False, duur=0.01)
    log.stap("b", "t2", "tool2", 2, 2, True, duur=0.02)
    stappen = log.als_gegeven()
    assert [s["nr"] for s in stappen] == [1, 2]
    telling = log.telling()
    assert telling["aantal_stappen"] == 2
    assert telling["met_taalmodel"] == 1
    assert telling["totale_duur"] == pytest.approx(0.03)


def test_elk_signaal_draagt_de_stap_die_hem_opleverde():
    """R14: de dossier-runlog is niet alleen een platte lijst -- elk signaal wijst terug naar de
    stap (agent, tool, stapnummer) die het opleverde, zodat navraagbaar is wélke stap dit signaal
    gaf zonder de code te lezen."""
    log = runlog.Runlog()
    log.stap("vergunninglezer", "lees_vergunning", "atlas_vergunningen", 5, 5, False)
    log.stap("signaalsteller", "bepaal_signalen", "signalen_stellen", 5, 3, False)
    d = dossier.dossier(VESTIGING_FIXTURE, CONTEXT, runlog=log)
    assert d["signalen"], "de fixture moet signalen opleveren om dit te kunnen toetsen"
    for s in d["signalen"]:
        assert s["stap"] == {"agent": "signaalsteller", "tool": "signalen_stellen", "nr": 2}


def test_zonder_runlog_draagt_geen_signaal_een_stap():
    """De keerzijde: zonder meegegeven runlog blijft `stap` afwezig, niet per ongeluk `None` --
    bewaakt al in `test_toezicht_dossier.test_elk_signaal_draagt_de_zes_velden_van_deel_b`, hier
    herhaald vanuit het runlog-perspectief."""
    d = dossier.dossier(VESTIGING_FIXTURE, CONTEXT)
    for s in d["signalen"]:
        assert "stap" not in s


def test_een_uitgezette_agent_met_een_taak_krijgt_een_luide_stap_geen_stilte():
    """Eis (d), nu op crew-niveau: `uitlegger` heeft een echte taak in de standaardpijplijn
    (`leg_signalen_uit` in `tasks.yaml`). Zet je hem uit, dan moet de runlog dat expliciet zeggen
    -- een eigen vlag, geen weggelaten stap."""
    crew, log = runner.laad(AGENTS, TASKS), runlog.Runlog()
    crew.draai({"vestiging": VESTIGING_FIXTURE, "uit": {"uitlegger"}}, runlog=log)
    stap = next(s for s in log.als_gegeven() if s["agent"] == "uitlegger")
    assert stap["uitgezet"] is True
    assert stap["niet_beschikbaar"] is False
    assert stap["tool"] is None, "uitgezet betekent: geen tool is aangeroepen, niet eens geprobeerd"


def test_een_nog_niet_gebouwde_tool_krijgt_een_luide_nietbeschikbaar_stap_geen_stilte():
    """Open vraag 1 uit de taakopdracht, hier als test vastgelegd: `uitlegger`s tool bestaat nog
    niet (taak 7), maar wordt wel aangeroepen door de standaardpijplijn. De runlog meldt dat met
    een eigen vlag én de naam van de tool, en de rest van de pijplijn loopt gewoon door."""
    crew, log = runner.laad(AGENTS, TASKS), runlog.Runlog()
    uitkomst = crew.draai({"vestiging": VESTIGING_FIXTURE}, runlog=log)
    stap = next(s for s in log.als_gegeven() if s["agent"] == "uitlegger")
    assert stap["niet_beschikbaar"] is True
    assert stap["uitgezet"] is False
    assert stap["tool"] == "uitleg_genereren"
    assert stap["llm"] is False, "er is niets uitgevoerd, dus is er ook geen taalmodel gebruikt"
    assert uitkomst["dossier"]["signalen"], "de rest van de pijplijn moet toch doorlopen"
