"""`toezicht.pijplijn` -- de pijplijngegevens voor de pagina, zonder een crew te starten (R4,
onderdeel van taak 6/6b: de pagina van taak 8 leest hiervan, maar bouwt niets zelf)."""
from leefomgevinglab.usecases.toezicht import pijplijn
from tests.test_toezicht_runner import AGENTS, TASKS


def test_als_gegeven_leest_de_zes_agents_met_hun_llm_gerechtigdheid():
    """De sleutel heet `mag_llm`, niet `heeft_llm` (eindreview, kleinere bevinding 6): hij meet
    of deze agent een taalmodel krijgt als er één wordt meegegeven, niet of er in een run echt
    één is aangeroepen -- dat laatste staat per stap in de runlog."""
    gegeven = pijplijn.als_gegeven(AGENTS, TASKS)
    namen = {a["id"] for a in gegeven["agents"]}
    assert namen == {"vergunninglezer", "signaalsteller", "dossiersteller", "uitlegger",
                      "vraagsteller", "terugkoppelaar"}
    assert not any("heeft_llm" in a for a in gegeven["agents"]), (
        "`heeft_llm` suggereert gebruik; deze API publiceert gerechtigdheid")
    mag_llm = {a["id"]: a["mag_llm"] for a in gegeven["agents"]}
    assert mag_llm["signaalsteller"] is False
    assert mag_llm["vergunninglezer"] is False
    assert mag_llm["dossiersteller"] is False
    assert mag_llm["uitlegger"] is True
    assert mag_llm["vraagsteller"] is True
    assert mag_llm["terugkoppelaar"] is True


def test_als_gegeven_leest_de_taken_met_hun_eigen_context_en_agent():
    gegeven = pijplijn.als_gegeven(AGENTS, TASKS)
    taken = {t["id"]: t for t in gegeven["tasks"]}
    assert taken["bepaal_signalen"]["context"] == ["lees_vergunning"]
    assert taken["bepaal_signalen"]["agent"] == "signaalsteller"
    assert taken["stel_dossier_samen"]["context"] == ["lees_vergunning", "bepaal_signalen"]


def test_als_gegeven_start_geen_crew_en_valideert_dus_geen_tools(tmp_path):
    """Een agent met een tool die helemaal niet bestaat (geen tikfout-detectie hier, dat is
    `runner.laad`'s taak) mag deze module niet laten crashen -- dat is precies waarom de pagina
    niet via `runner.laad` loopt (R4): een diagram tekenen mag nooit van die validatie afhangen."""
    agents_pad = tmp_path / "agents.yaml"
    agents_pad.write_text("x:\n  role: r\n  goal: g\n  tools: [bestaat_helemaal_niet]\n")
    tasks_pad = tmp_path / "tasks.yaml"
    tasks_pad.write_text("{}\n")

    gegeven = pijplijn.als_gegeven(str(agents_pad), str(tasks_pad))
    assert gegeven["agents"][0]["tools"] == ["bestaat_helemaal_niet"]
    assert gegeven["tasks"] == []


# -- De instellingen die de pagina klikbaar moet kunnen tonen -----------------------------------

def test_als_gegeven_draagt_de_llm_regel_zelf_en_niet_alleen_een_boolean():
    """`mag_llm` zegt dát een agent een taalmodel mag krijgen; de `llm`-regel in de YAML zegt
    *welk* model, *waar* het draait en dat de runner het injecteert. Die regel werd weggegooid,
    terwijl zij juist het antwoord is op "wat gebeurt hier onder water" -- en dat is de vraag
    waarom deze configuratie op de pagina staat.

    Een agent zonder de sleutel draagt `None`, niet een lege string: afwezig en leeg zijn hier
    twee verschillende dingen (de §4.4-grens is een *afwezig veld*, zie `agents.yaml`)."""
    agents = {a["id"]: a for a in pijplijn.als_gegeven(AGENTS, TASKS)["agents"]}
    assert agents["signaalsteller"]["llm"] is None
    assert agents["vergunninglezer"]["llm"] is None
    assert agents["uitlegger"]["llm"], "de uitlegger mag er een, dus de regel hoort hier te staan"
    assert "8080" in agents["uitlegger"]["llm"], "welk endpoint, niet alleen ja/nee"


def test_elke_agent_draagt_alles_wat_een_openklappende_rij_nodig_heeft():
    """De pagina klapt een agentrij open; wat daarin staat moet uit de configuratie komen en niet
    uit de HTML. Deze test is de afspraak tussen de twee."""
    for a in pijplijn.als_gegeven(AGENTS, TASKS)["agents"]:
        for veld in ("id", "role", "goal", "backstory", "tools", "mag_llm", "llm"):
            assert veld in a, f"{a['id']} mist {veld}"
        assert a["role"] and a["goal"] and a["backstory"], a["id"]


# -- Welke agents hebben in DEZE run echt gedraaid (voor /toezicht) ----------------------------

def test_gedraaide_agents_leidt_de_lijst_uit_de_runlog_af_en_niet_uit_de_configuratie():
    """`/toezicht` toont de agents die in deze run hebben gedraaid -- gebruik, niet
    gerechtigdheid. Zes agents staan in `agents.yaml`, vier draaien in de standaardpijplijn, en
    `vraagsteller`/`terugkoppelaar` hebben geen taak. Zou deze functie de configuratie als bron
    nemen, dan beweerde de pagina dat er zes hebben gedraaid."""
    stappen = [
        {"nr": 1, "agent": "vergunninglezer", "taak": "lees_vergunning", "llm": False},
        {"nr": 2, "agent": "signaalsteller", "taak": "bepaal_signalen", "llm": False},
        {"nr": 3, "agent": "uitlegger", "taak": "leg_signalen_uit", "llm": True},
    ]
    uit = pijplijn.gedraaide_agents(stappen, AGENTS)
    assert [a["id"] for a in uit] == ["vergunninglezer", "signaalsteller", "uitlegger"]
    assert [a["stappen"] for a in uit] == [[1], [2], [3]]
    # Gebruik en gerechtigdheid staan naast elkaar, niet in plaats van elkaar.
    assert uit[2]["llm_aangeroepen"] is True and uit[2]["mag_llm"] is True
    assert uit[0]["llm_aangeroepen"] is False and uit[0]["mag_llm"] is False
    assert uit[2]["llm"] and "8080" in uit[2]["llm"]
    assert uit[0]["goal"], "de uitleg per agent komt uit de configuratie"


def test_een_agent_die_twee_keer_draaide_staat_een_keer_met_beide_stappen():
    stappen = [{"nr": 1, "agent": "uitlegger", "taak": "a", "llm": False},
               {"nr": 2, "agent": "uitlegger", "taak": "b", "llm": True}]
    uit = pijplijn.gedraaide_agents(stappen, AGENTS)
    assert len(uit) == 1
    assert uit[0]["stappen"] == [1, 2]
    assert uit[0]["llm_aangeroepen"] is True, "één echte aanroep is genoeg"


def test_een_agent_in_de_runlog_die_niet_in_de_configuratie_staat_valt_niet_stil_weg():
    """Een onbekende agent is een echte afwijking -- configuratie en run zijn dan uit de pas.
    Hem overslaan zou dat verbergen; hij blijft staan, met de reden in plaats van een rol."""
    uit = pijplijn.gedraaide_agents([{"nr": 1, "agent": "spook", "taak": "x", "llm": False}],
                                     AGENTS)
    assert [a["id"] for a in uit] == ["spook"]
    assert uit[0]["role"] is None
    assert uit[0]["onbekend"] is True


def test_gedraaide_agents_op_een_lege_runlog_geeft_een_lege_lijst():
    assert pijplijn.gedraaide_agents([], AGENTS) == []
