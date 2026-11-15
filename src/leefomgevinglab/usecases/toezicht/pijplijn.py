"""De pijplijngegevens voor de pagina (taak 8) -- gelezen uit dezelfde YAML als `runner.laad`,
zonder een `Crew` te starten (R4).

**Waarom een eigen module in plaats van `Crew.als_gegeven()`.** De pagina moet de configuratie
kunnen tonen (welke agents, welke tools, welke taalmodellen, welke taken in welke volgorde) zonder
dat daarvoor een pijplijn draait. `runner.laad()` valideert bij het laden al tegen `TOOLS`/
`GEPLAND` (`OnbekendeTool`) -- geen netwerk, geen taalmodel, dus op zichzelf niet gevaarlijk, maar
het is wél een uitvoeringsstap die met een toekomstige, strengere validatie zou kunnen groeien.
Een diagram tekenen moet daar nooit van afhangen: deze module leest de twee YAML-bestanden zelf,
rechtstreeks, en projecteert alleen de velden die een pagina nodig heeft. Een tool-naam die nergens
bestaat (een tikfout, of een agent die wacht op een latere taak) mag de pagina daarom nooit laten
crashen -- zie `test_als_gegeven_start_geen_crew_en_valideert_dus_geen_tools`.

**Wat "hetzelfde tonen" hier betekent.** `mag_llm` is afgeleid van de aan- of afwezigheid van de
`llm`-sleutel in de agent-configuratie -- exact de sleutel die `runner.Crew._llm_voor_deze_agent`
gebruikt om de §4.4-grens te trekken. Zo kan de pagina "2 agents met taalmodel" tonen zonder dat
getal ooit apart te typen: het is precies wat de runner ook leest.

**De naam is `mag_llm`, niet `heeft_llm` (eindreview, kleinere bevinding 6).** Dit veld meet
*gerechtigdheid*: of deze agent een taalmodel toegewezen krijgt als er één wordt meegegeven. Het
meet geen gebruik -- `/api/wasstraat/pijplijn` gaf `uitlegger: true` terwijl die route `llm=None`
doorgeeft en er dus nooit één is. De pagina deed het al goed (kolomkop "mag taalmodel"); de
API-sleutel zei "heeft", en precies die verwarring heeft dit dossier eerder duur betaald (zie
`runner.py`, "Fix-ronde 2, bevinding E"). Wat er in een run werkelijk is aangeroepen staat in de
runlog (`llm` per stap), nergens anders.
"""
from pathlib import Path

import yaml


def _laad_yaml(pad: str) -> dict:
    with Path(pad).open(encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


def als_gegeven(agents_pad: str, tasks_pad: str) -> dict:
    """De agents en taken uit de configuratie, als platte lijsten dicts -- de vorm die de pagina
    (taak 8) rechtstreeks kan renderen. Geen validatie: een onbekende tool, een taak zonder
    `context` of een ontbrekend veld komt hier gewoon door, precies zoals de YAML het zegt."""
    agents = _laad_yaml(agents_pad)
    tasks = _laad_yaml(tasks_pad)

    agents_uit = [
        {
            "id": naam,
            "role": cfg.get("role"),
            "goal": cfg.get("goal"),
            "backstory": cfg.get("backstory"),
            "tools": list(cfg.get("tools") or []),
            "mag_llm": "llm" in cfg,
            # De `llm`-regel zelf, niet alleen het feit dat zij bestaat. Zij noemt welk model,
            # waar het draait en dat de runner het injecteert ("geen eigen verbinding") -- en dat
            # is precies het antwoord op "wat gebeurt hier onder water". `None` bij een agent
            # zonder de sleutel, want afwezig en leeg zijn hier twee verschillende dingen: de
            # §4.4-grens staat in `agents.yaml` als een *afwezig veld*.
            "llm": cfg.get("llm"),
        }
        for naam, cfg in agents.items()
    ]
    tasks_uit = [
        {
            "id": naam,
            "description": cfg.get("description"),
            "expected_output": cfg.get("expected_output"),
            "agent": cfg.get("agent"),
            "context": list(cfg.get("context") or []),
        }
        for naam, cfg in tasks.items()
    ]
    return {"agents": agents_uit, "tasks": tasks_uit}


def gedraaide_agents(stappen: list[dict], agents_pad: str) -> list[dict]:
    """De agents die in **deze** run echt hebben gedraaid, in de volgorde waarin zij voor het
    eerst voorkwamen, elk met de uitleg uit de configuratie erbij.

    **De runlog is de bron, niet `agents.yaml`.** Dat is het hele punt van deze functie: zes
    agents staan in de configuratie, vier draaien in de standaardpijplijn, en `vraagsteller` en
    `terugkoppelaar` hebben geen taak. Zou de configuratie de bron zijn, dan beweerde `/toezicht`
    dat er zes hebben gedraaid -- precies de mocht/heeft-verwarring die dit dossier duur heeft
    betaald (zie `runner.py`, "Fix-ronde 2, bevinding E", en `mag_llm` hierboven).

    Daarom staan `mag_llm` (gerechtigdheid, uit de configuratie) en `llm_aangeroepen` (gebruik,
    uit de runlog) náást elkaar in het antwoord, niet in plaats van elkaar. Draaide een agent
    twee keer, dan staat hij één keer met al zijn stapnummers, en is één echte aanroep genoeg om
    `llm_aangeroepen` waar te maken.

    Een agent in de runlog die niet in de configuratie staat, krijgt `onbekend: True` en blijft
    staan in plaats van stil weg te vallen: configuratie en run zijn dan uit de pas, en dat is
    een afwijking die de pagina hoort te laten zien.
    """
    cfgs = _laad_yaml(agents_pad)
    uit: dict[str, dict] = {}
    for stap in stappen:
        naam = stap.get("agent")
        if naam is None:
            continue
        if naam not in uit:
            cfg = cfgs.get(naam)
            uit[naam] = {
                "id": naam,
                "role": (cfg or {}).get("role"),
                "goal": (cfg or {}).get("goal"),
                "backstory": (cfg or {}).get("backstory"),
                "tools": list((cfg or {}).get("tools") or []),
                "mag_llm": cfg is not None and "llm" in cfg,
                "llm": (cfg or {}).get("llm"),
                "onbekend": cfg is None,
                "stappen": [],
                "taken": [],
                "llm_aangeroepen": False,
            }
        post = uit[naam]
        if stap.get("nr") is not None:
            post["stappen"].append(stap["nr"])
        if stap.get("taak") and stap["taak"] not in post["taken"]:
            post["taken"].append(stap["taak"])
        if stap.get("llm"):
            post["llm_aangeroepen"] = True
    return list(uit.values())
