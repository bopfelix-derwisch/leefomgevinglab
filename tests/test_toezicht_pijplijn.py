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
