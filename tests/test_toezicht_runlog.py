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


def test_de_uitlegger_draait_nu_echt_in_de_standaardpijplijn():
    """Taak 7 maakte `uitleg_genereren` een echte tool (vroeger stond hier
    `test_een_nog_niet_gebouwde_tool_krijgt_een_luide_nietbeschikbaar_stap_geen_stilte`, die
    precies het omgekeerde vastlegde). Een gewone run zonder `aquo_ref`/`normenset`/
    `stelselcatalogus` in de invoer kan de drie geïnjecteerde bronnen niet raadplegen -- maar de
    vierde (de /kmg-proclaimer, fix-ronde 1) is intrinsiek en altijd actief, en vuurt hier op het
    trefwoord 'regime' in de signaalkop 'toets niet regime-zuiver' (`niet_regime_zuiver`).
    `norm_overschreden_bovenstrooms` fireert in deze run niet eens (zonder `context` ontbreekt
    `context["waterlichaam"]`, zie `signalen.regel_norm_overschreden_bovenstrooms`), dus alleen
    `niet_regime_zuiver` krijgt hier een `waarom`. De stap zelf is een normale, uitgevoerde stap,
    geen `niet_beschikbaar`. Zie `test_de_uitlegger_vult_waarom_zodra_er_een_aquo_referentie_is`
    hieronder voor een run met `context` en een geïnjecteerde Aquo-referentie erbij."""
    crew, log = runner.laad(AGENTS, TASKS), runlog.Runlog()
    uitkomst = crew.draai({"vestiging": VESTIGING_FIXTURE}, runlog=log)
    stap = next(s for s in log.als_gegeven() if s["agent"] == "uitlegger")
    assert stap["niet_beschikbaar"] is False
    assert stap["uitgezet"] is False
    assert stap["tool"] == "uitleg_genereren"
    assert stap["llm"] is False, "deze run geeft draai() geen llm mee"
    assert uitkomst["dossier"]["signalen"], "de rest van de pijplijn moet toch doorlopen"
    met_waarom = {s["regel"] for s in uitkomst["dossier"]["signalen"] if s.get("waarom")}
    assert met_waarom == {"niet_regime_zuiver"}, (
        "alleen het proclaimer-trefwoord 'regime' in de signaalkop mag hier een waarom "
        "opleveren, zonder enige geïnjecteerde bron")


def test_de_uitlegger_vult_waarom_zodra_er_een_aquo_referentie_is():
    """Dezelfde run, nu mét een Aquo-referentie in de invoer -- de vestiging in deze fixture
    draagt een voorschrift op 'Zwevende stof' met `aquo_status: Vervallen` (zie
    `test_toezicht_signalen.VESTIGING_MET_ALLES`), dus een Aquo-referentie die diezelfde naam als
    ingetrokken kent, moet voor dat signaal een `waarom` opleveren."""
    crew, log = runner.laad(AGENTS, TASKS), runlog.Runlog()
    aquo_ref = {"geldig": {}, "vervallen": {"zwevende stof": "ZS"}, "vervangen_door": {}}
    uitkomst = crew.draai({"vestiging": VESTIGING_FIXTURE, "context": CONTEXT,
                           "aquo_ref": aquo_ref}, runlog=log)
    vervallen_signalen = [s for s in uitkomst["dossier"]["signalen"]
                          if s["regel"] == "vervallen_code"]
    assert vervallen_signalen, "de fixture moet dit signaal laten vuren"
    assert vervallen_signalen[0].get("waarom"), \
        "met een passende Aquo-referentie moet dit signaal een uitleg krijgen"
    for verboden in ("overtreding", "veroorzaakt door", "in strijd met"):
        assert verboden not in vervallen_signalen[0]["waarom"].lower()


# -- Fixronde 1, bevinding 1 (Important): args is een samenvatting, nooit leeg en nooit de payload

def test_elke_stap_draagt_een_samenvatting_van_zijn_argumenten_niet_de_hele_payload():
    """Een leeg `args`-veld is erger dan een afwezig veld: het beweert dat er niets te melden was,
    terwijl er gewoon niets is vastgelegd. Deze test controleert het omgekeerde ook -- `args` mag
    nooit de volledige vestiging, context of het register bevatten, want dat zou de runlog net zo
    onleesbaar maken als leegte hem onzichtbaar maakt."""
    crew, log = runner.laad(AGENTS, TASKS), runlog.Runlog()
    crew.draai({"vestiging": VESTIGING_FIXTURE, "context": CONTEXT}, runlog=log)
    stappen = {s["tool"]: s for s in log.als_gegeven() if s["tool"] and not s["niet_beschikbaar"]}

    lees_stap = stappen["atlas_vergunningen"]
    assert lees_stap["args"] == {"vestiging": VESTIGING_FIXTURE["naam"]}

    signaal_stap = stappen["signalen_stellen"]
    assert signaal_stap["args"]["vestiging"] == VESTIGING_FIXTURE["naam"]
    assert signaal_stap["args"]["regels"], "zonder regel-ID's is er niets om tegen het dossier te toetsen"

    dossier_stap = stappen["dossier_samenstellen"]
    assert dossier_stap["args"]["vestiging"] == VESTIGING_FIXTURE["naam"]
    assert dossier_stap["args"]["uitgezet"] == []

    # Geen van de args-dicts mag de volledige payload dragen: geen "voorschriften"-lijst, geen
    # ruwe context, geen bewijs -- alleen de kleine, identificerende velden hierboven.
    for stap in stappen.values():
        assert "voorschriften" not in stap["args"]
        assert "context" not in stap["args"]
        assert "bewijs" not in stap["args"]


def test_een_uitgezette_stap_en_een_nietbeschikbare_stap_dragen_ook_een_vestiging_in_args():
    """`args` is geen voorrecht van een normale toolaanroep -- ook de twee luide, niet-uitgevoerde
    soorten stappen (eis (d) en de GEPLAND-afhandeling) dragen welke vestiging het betrof."""
    crew, log = runner.laad(AGENTS, TASKS), runlog.Runlog()
    crew.draai({"vestiging": VESTIGING_FIXTURE, "uit": {"uitlegger"}}, runlog=log)
    stap = next(s for s in log.als_gegeven() if s["agent"] == "uitlegger")
    assert stap["args"] == {"vestiging": VESTIGING_FIXTURE["naam"]}


# -- Fixronde 1, bevinding 3: de eigenschap die deze taak moet vastleggen -----------------------

def test_de_signalen_in_de_runlog_stap_komen_overeen_met_het_uiteindelijke_dossier():
    """`tool_signalen_stellen` en `dossier_samenstellen` (via `dossier.dossier()`) berekenen de
    signalen vandaag elk apart, en kunnen vandaag niet uiteenlopen -- maar dat is een structureel
    toeval, door geen test bewaakt totdat deze test hier stond. Een latere filter in `dossier()`,
    of een mutatie van `context` tussen deze twee taken, zou de runlog iets anders laten beweren
    dan het dossier bevat; precies de traceerbaarheid waarvoor taak 6b bestaat. Deze test
    vergelijkt daarom niet alleen de aantallen maar de regel-ID's zelf, in twee richtingen."""
    crew, log = runner.laad(AGENTS, TASKS), runlog.Runlog()
    uitkomst = crew.draai({"vestiging": VESTIGING_FIXTURE, "context": CONTEXT}, runlog=log)
    stap = next(s for s in log.als_gegeven() if s["tool"] == "signalen_stellen")

    regels_in_runlog = sorted(stap["args"]["regels"])
    regels_in_dossier = sorted(s["regel"] for s in uitkomst["dossier"]["signalen"])
    assert regels_in_runlog == regels_in_dossier, \
        "de runlog-stap en het uiteindelijke dossier beweren niet meer hetzelfde"
    assert stap["rijen_uit"] == len(uitkomst["dossier"]["signalen"])


# -- Fix-ronde 1, bevinding 3: het GEPLAND/niet_beschikbaar-mechanisme behoudt dekking -----------

def test_een_toekomstig_geplande_maar_nog_niet_gebouwde_tool_geeft_nog_steeds_nietbeschikbaar(
        monkeypatch):
    """`GEPLAND` is sinds taak 7 leeg, omdat `uitleg_genereren`/`terugkoppeling_genereren` nu
    echte tools zijn -- maar het mechanisme zelf (een tool die verklaard is in de YAML en
    aangekondigd in `GEPLAND`, maar nog niet in `TOOLS` staat, moet het laden niet breken en bij
    uitvoering een luide `niet_beschikbaar`-stap geven) is daarmee dekkingsloos geworden: geen
    test construeerde nog een gevulde `GEPLAND`. Dit simuleert de volgende agent die hetzelfde
    tussenstadium doorloopt, met een tijdelijke, niet-bestaande toolnaam."""
    monkeypatch.setattr(runner, "GEPLAND", {"toekomstige_tool"})
    crew = runner.laad_uit_dict(
        {"toekomstagent": {"role": "x", "goal": "y", "tools": ["toekomstige_tool"]}},
        {"t1": {"description": "d", "expected_output": "e", "agent": "toekomstagent"}})

    # De eerste helft: de tool is verklaard (dus geen `OnbekendeTool` bij het laden), maar niet
    # gebouwd (dus `NietBeschikbaar` zodra iemand hem opvraagt).
    with pytest.raises(runner.NietBeschikbaar):
        crew.tools_voor("toekomstagent")["toekomstige_tool"]

    # De tweede helft: `Crew.draai()` registreert dat luid in de runlog, geen stille overslag.
    log = runlog.Runlog()
    crew.draai({}, runlog=log)
    stap = next(s for s in log.als_gegeven() if s["agent"] == "toekomstagent")
    assert stap["niet_beschikbaar"] is True
    assert stap["uitgezet"] is False
    assert stap["tool"] == "toekomstige_tool"
    assert stap["llm"] is False, "er is niets uitgevoerd, dus is er ook geen taalmodel gebruikt"


# -- Fix-ronde 2, bevinding D (R21) — de "mag een taalmodel" kant is nu ook runtime bewezen ------

def test_een_agent_met_llm_sleutel_kan_het_taalmodel_ook_echt_ontvangen_in_een_run():
    """`test_toezicht_pijplijn.py` toetst alleen de YAML (`mag_llm`) -- niets bewees dat
    `_llm_voor_deze_agent` een eligible agent ook werkelijk een aanroepbaar taalmodel geeft in
    een echte `draai()`. Een regressie die hem altijd `None` laat teruggeven (te voorzichtig,
    blokkeert iedereen) zou de rest van de suite ongemerkt laten slagen, want alle bestaande
    `llm`-tests toetsen alleen de agents *zonder* de sleutel. Deze test geeft `uitlegger` een
    fixture met een echte proclaimer-treffer (`niet_regime_zuiver`, zie fix-ronde 1) en bewijst
    dat de spion ook echt is aangeroepen -- niet alleen dat de runlog `llm: True` zegt."""
    aangeroepen = []

    def spion_llm(prompt):
        aangeroepen.append(prompt)
        return "nette tekst"

    log = runlog.Runlog()
    crew = runner.laad(AGENTS, TASKS)
    crew.draai({"vestiging": VESTIGING_FIXTURE, "context": CONTEXT}, llm=spion_llm, runlog=log)
    assert aangeroepen, \
        "uitlegger kreeg geen aanroepbaar taalmodel -- _llm_voor_deze_agent is kapot of te streng"
    stap = next(s for s in log.als_gegeven() if s["agent"] == "uitlegger")
    assert stap["llm"] is True


# -- Fix-ronde 2, bevinding E (R21) — het runlog-veld `llm` meet gebruik, niet eligibility --------

def test_runlog_llm_veld_is_false_als_uitlegger_eligible_is_maar_niets_aanroept():
    """De kern van bevinding E: `uitlegger` draagt een `llm`-sleutel (eligible) maar roept het
    model alleen aan als `uitleg.waarom()` iets vindt om te herformuleren. Met een vestiging die
    geen van de vier bronnen raakt, is hij eligible én ongebruikt -- en dát moet de runlog nu
    zeggen, niet `llm: True` omdat hij het hád mogen gebruiken."""
    def spion_llm(prompt):
        return "nette tekst"

    vestiging = {"naam": "Niets te verklaren", "kenmerk": "K1", "url": "https://x",
                 "besluitdatum": "2020-01-01", "voorschriften": []}
    log = runlog.Runlog()
    crew = runner.laad(AGENTS, TASKS)
    uitkomst = crew.draai({"vestiging": vestiging, "context": {}}, llm=spion_llm, runlog=log)
    assert uitkomst["dossier"]["signalen"] == [], "deze vestiging mag geen signaal opleveren"
    stap = next(s for s in log.als_gegeven() if s["agent"] == "uitlegger")
    assert stap["llm"] is False, \
        "uitlegger was eligible maar riep niets aan -- het veld moet gebruik meten, geen aanbod"


def test_runlog_llm_veld_contrasteert_eligible_ongebruikt_met_eligible_gebruikt():
    """Dezelfde agent, dezelfde eligibility, twee runs die alleen verschillen in of er iets te
    verklaren is -- het `llm`-veld moet daadwerkelijk meebewegen met gebruik, niet een vaste
    eigenschap van de configuratie zijn die toevallig op `True` staat."""
    def spion_llm(prompt):
        return "nette tekst"

    leeg = {"naam": "Niets te verklaren", "kenmerk": "K1", "url": "https://x",
            "besluitdatum": "2020-01-01", "voorschriften": []}
    crew = runner.laad(AGENTS, TASKS)

    log_zonder = runlog.Runlog()
    crew.draai({"vestiging": leeg, "context": {}}, llm=spion_llm, runlog=log_zonder)
    stap_zonder = next(s for s in log_zonder.als_gegeven() if s["agent"] == "uitlegger")

    log_met = runlog.Runlog()
    crew.draai({"vestiging": VESTIGING_FIXTURE, "context": CONTEXT}, llm=spion_llm,
               runlog=log_met)
    stap_met = next(s for s in log_met.als_gegeven() if s["agent"] == "uitlegger")

    assert stap_zonder["llm"] is False
    assert stap_met["llm"] is True
