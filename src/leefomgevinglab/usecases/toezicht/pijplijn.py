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

**Wat "hetzelfde tonen" hier betekent.** `heeft_llm` is afgeleid van de aan- of afwezigheid van de
`llm`-sleutel in de agent-configuratie -- exact de sleutel die `runner.Crew._llm_voor_deze_agent`
gebruikt om de §4.4-grens te trekken. Zo kan de pagina "2 agents met taalmodel" tonen zonder dat
getal ooit apart te typen: het is precies wat de runner ook leest.
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
            "heeft_llm": "llm" in cfg,
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
