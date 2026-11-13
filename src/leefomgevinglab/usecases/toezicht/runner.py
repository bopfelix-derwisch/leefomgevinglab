"""De agentrunner -- CrewAI-compatibele configuratie die het proces bestuurt, niet beschrijft.

**Waarom CrewAI-compatibel.** `config/agents.yaml` gebruikt `role`/`goal`/`backstory`/`tools`,
`config/tasks.yaml` gebruikt `description`/`expected_output`/`agent`/`context` -- precies de
velden van een CrewAI-configuratie. Niet om ooit naar iemand anders' CrewAI-opstelling te
verhuizen, maar omdat een gedocumenteerde, extern bestaande vorm beter te controleren is dan een
configuratietaal die dit lab er zelf bij verzint (zie `test_agents_yaml_gebruikt_de_crewai_velden`
en de pendant voor taken).

**Eis (a), de twee helften.** Een agent krijgt van de runner uitsluitend de tools die zijn eigen
`tools`-lijst noemt:

1. Een tool die *nergens* bestaat (niet in `TOOLS`, niet in `GEPLAND`) laat `laad_uit_dict` al
   breken met `OnbekendeTool` -- vóór er iets draait, niet pas als de agent hem voor het eerst
   probeert te gebruiken.
2. Een tool die wél bestaat, maar niet voor déze agent is verklaard, geeft `NietVerklaardeTool`
   zodra iemand hem via `tools_voor(agent)[...]` opvraagt. Dit is de scherpere helft: zonder deze
   check zou de YAML het proces alleen *beschrijven*, en kon een agent alsnog bij het gereedschap
   van een ander. Zie `VerklaardeTools.__getitem__`.

**Een derde, tussenliggend geval: verklaard, maar nog niet gebouwd.** `uitlegger` en
`terugkoppelaar` (taak 7) staan al met hun échte tools in `agents.yaml`, zodat de configuratie nu
al het volledige procesplaatje toont (R4/§5) -- maar die tools bestaan nog niet als Python-functie.
`GEPLAND` is de plek waar dat *aangekondigd* staat: een naam die hier of in `TOOLS` voorkomt, laadt
gewoon; alleen een naam in geen van beide is een tikfout of een vergeten registratie en breekt het
laden (`OnbekendeTool`). Roept de pijplijn zo'n geplande tool toch aan (`Crew.draai`), dan krijgt
die stap een luide `niet_beschikbaar`-vlag in de runlog in plaats van een stille `continue` of een
crash -- de opdracht vroeg expliciet om dat zichtbaar te maken, en koos niet voor een startfout,
want dat zou het laden van de hele configuratie blokkeren zolang taak 7 niet klaar is, en precies
dát (een configuratie die wél leesbaar is maar niet draait) is wat deze module moet voorkomen.

**Eis (d), uitgezet versus niet beschikbaar.** Beide zijn "luid, nooit stil", maar om een andere
reden: `uitgezet` is een bewuste keuze van de aanroeper (`invoer["uit"]`), `niet_beschikbaar` is
een eigenschap van de configuratie zelf. De runlog onderscheidt ze met eigen vlaggen (zie
`runlog.py`) in plaats van ze onder één "overgeslagen" te laten samenvallen -- een inspecteur die
leest waaróm een stap ontbreekt, moet dat verschil kunnen zien.

**Eis (b), de runlog als deel D.** `Crew.draai(invoer, llm=None, runlog=None)` vult, als er een
`Runlog` is meegegeven, per stap wie (`agent`), wat (`taak`, `tool`), hoeveel (`rijen_in`,
`rijen_uit`, gemeten, nooit getypt) en of er een taalmodel bij was. Dat laatste is de harde grens
uit §4.4: een agent zonder `llm`-sleutel in zijn configuratie krijgt het meegegeven `llm` hier
nooit doorgegeven, ook niet als de aanroeper er een aan `draai()` geeft -- zie
`_llm_voor_deze_agent`. Dat maakt de belofte "signaalsteller en vergunninglezer gebruiken nooit
een taalmodel" per run aantoonbaar (de runlog zegt het), niet alleen een statische eigenschap van
de YAML (die ook bewaakt wordt, zie de tests, maar op zichzelf niets zou bewijzen over een
werkelijke run).

**Sequentieel, met doorgegeven staat.** `draai()` doorloopt de taken in de volgorde van
`tasks.yaml` (een gewoon dict, en dict-volgorde is sinds Python 3.7 invoervolgorde) en geeft
dezelfde `staat`-dict van taak naar taak door -- elke tool leest en schrijft op die staat, zodat
`context` in `tasks.yaml` (welke eerdere taken deze voedt) een documentatie is van wat er al
feitelijk gebeurt, niet een los-van-de-uitvoering intentieverklaring.
"""
import time
from collections.abc import Callable, Mapping
from typing import Any, NamedTuple

import yaml

from leefomgevinglab.usecases.toezicht import aquo as aquo_mod
from leefomgevinglab.usecases.toezicht import dossier as dossier_mod
from leefomgevinglab.usecases.toezicht import graaf as graaf_mod
from leefomgevinglab.usecases.toezicht import signalen as signalen_mod
from leefomgevinglab.usecases.toezicht import vraag as vraag_mod


class OnbekendeTool(Exception):
    """Een agent in de configuratie vraagt een tool die nergens bestaat -- niet in `TOOLS`, en
    ook niet aangekondigd in `GEPLAND`. Dat is een tikfout of een vergeten registratie en moet
    daarom bij het laden breken, vóór er iets draait."""


class NietVerklaardeTool(Exception):
    """Een tool bestaat (in `TOOLS` of `GEPLAND`), maar niet voor déze agent: hij staat niet in
    zijn eigen `tools`-lijst. De scherpere helft van eis (a) -- zie de moduledocstring."""


class NietBeschikbaar(Exception):
    """De tool is verklaard voor deze agent en staat in `GEPLAND`, maar is nog niet gebouwd.
    Wordt opgeworpen door `VerklaardeTools.__getitem__`; `Crew.draai` vangt deze situatie zelf af
    en zet er een luide runlog-stap voor in de plaats (zie de moduledocstring)."""


# -- De tools: dunne, deterministische wrappers om de modules van taak 1-5 -----------------------

class Uitkomst(NamedTuple):
    """Wat een tool teruggeeft aan de runner: de staat-sleutels die hij bijwerkt, en de omvang
    erin en eruit -- gemeten door de tool zelf, nooit door de runner verzonnen (huisregel 'geen
    getal wordt getypt')."""
    updates: dict
    rijen_in: int
    rijen_uit: int


def _tel(waarde) -> int:
    """Eén plek voor 'hoeveel rijen is dit' -- een vestiging telt haar voorschriften, een
    lijst/set/dict telt haar eigen lengte, en al het andere telt als 1 (aanwezig) of 0 (leeg)."""
    if waarde is None:
        return 0
    if isinstance(waarde, dict) and "voorschriften" in waarde:
        return len(waarde.get("voorschriften") or [])
    if isinstance(waarde, (list, tuple, set, dict)):
        return len(waarde)
    return 1


def tool_atlas_vergunningen(staat: dict, *, llm=None, runlog=None) -> Uitkomst:
    """Leest de vestiging en verrijkt haar voorschriften met de Aquo-referentie uit
    `staat['aquo_ref']`. Ontbreekt die referentie, dan blijft de vestiging onaangeroerd (zie
    `aquo.verrijk`) -- geen netwerk, geen bestand hier, dat levert wie `aquo_ref` aanlevert."""
    vestiging = staat.get("vestiging") or {}
    ref = staat.get("aquo_ref") or {"beschikbaar": False}
    verrijkt = aquo_mod.verrijk(vestiging, ref)
    return Uitkomst({"vestiging": verrijkt}, _tel(vestiging), _tel(verrijkt))


def tool_signalen_stellen(staat: dict, *, llm=None, runlog=None) -> Uitkomst:
    """Past de tien deterministische signaalregels toe -- geen netwerk, geen taalmodel, zie
    `signalen.signalen`."""
    vestiging = staat.get("vestiging") or {}
    context = staat.get("context") or {}
    ruw = signalen_mod.signalen(vestiging, context)
    return Uitkomst({"signalen_ruw": ruw}, _tel(vestiging), _tel(ruw))


def tool_dossier_samenstellen(staat: dict, *, llm=None, runlog=None) -> Uitkomst:
    """Stelt het volledige signaaldossier samen, met de meegekregen `runlog` als deel D (R14) --
    op het moment van deze aanroep bevat die runlog al elke stap die ervóór liep (vergunninglezer,
    signaalsteller), dus `dossier()` kan precies de signaalsteller-stap terugvinden."""
    vestiging = staat.get("vestiging") or {}
    context = staat.get("context") or {}
    uitgezet = staat.get("uit")
    d = dossier_mod.dossier(vestiging, context, uit=uitgezet, runlog=runlog)
    return Uitkomst({"dossier": d}, _tel(vestiging), 1)


def tool_toezichtgraaf_bouwen(staat: dict, *, llm=None, runlog=None) -> Uitkomst:
    """Bouwt de bevraagbare graaf uit het register, de metingen en de normen (`graaf.bouw`)."""
    register = staat.get("register") or []
    g = graaf_mod.bouw(register, staat.get("metingen"), staat.get("normen"), staat.get("aquo_ref"))
    return Uitkomst({"graaf": g}, _tel(register), 1)


def tool_vraag_stellen(staat: dict, *, llm=None, runlog=None) -> Uitkomst:
    """Beantwoordt `staat['vraag']` via de toezichtgraaf (`vraag.stel`) -- de enige tool hier die
    een taalmodel gebruikt, en dus alleen zinvol voor een agent die `llm` wél in zijn configuratie
    heeft staan."""
    antwoord = vraag_mod.stel(staat.get("vraag"), staat.get("graaf"), llm)
    return Uitkomst({"antwoord": antwoord}, 1, _tel(antwoord.get("rijen")))


#: Echte, aanroepbare tools -- de enige namen die een agent zonder meer mag gebruiken.
TOOLS: dict[str, Callable[..., Uitkomst]] = {
    "atlas_vergunningen": tool_atlas_vergunningen,
    "signalen_stellen": tool_signalen_stellen,
    "dossier_samenstellen": tool_dossier_samenstellen,
    "toezichtgraaf_bouwen": tool_toezichtgraaf_bouwen,
    "vraag_stellen": tool_vraag_stellen,
}

#: Namen die taak 7 nog moet bouwen. Aangekondigd, geen tikfout -- zie de moduledocstring. Een
#: naam die hier wél en in `TOOLS` níet staat, laadt (`laad_uit_dict`) maar levert bij uitvoering
#: (`Crew.draai`) een luide `niet_beschikbaar`-stap op, geen crash.
GEPLAND: set[str] = {"uitleg_genereren", "terugkoppeling_genereren"}


# -- De configuratie: laden en bewaken -----------------------------------------------------------

_VERPLICHTE_AGENT_VELDEN = ("role", "goal")
_VERPLICHTE_TAAK_VELDEN = ("description", "expected_output", "agent")


class VerklaardeTools(Mapping):
    """Het gereedschap van precies één agent -- `Crew.tools_voor(agent)` geeft dit terug, nooit
    de globale `TOOLS`-registry zelf. Alleen namen uit de eigen `tools`-lijst van de agent zijn
    hier op te vragen; alles anders is `NietVerklaardeTool`, ook als die naam elders wél bestaat.
    Dat is precies de scherpere helft van eis (a): bestaan is niet voldoende, verklaard-zijn-voor-
    déze-agent is de maat."""

    def __init__(self, agent_naam: str, verklaard: list[str]) -> None:
        self._agent = agent_naam
        self._verklaard = list(verklaard)

    def __getitem__(self, naam: str) -> Callable[..., Uitkomst]:
        if naam not in self._verklaard:
            raise NietVerklaardeTool(
                f"tool '{naam}' is niet verklaard voor agent '{self._agent}' "
                f"(verklaard: {sorted(self._verklaard)})")
        if naam in TOOLS:
            return TOOLS[naam]
        raise NietBeschikbaar(
            f"tool '{naam}' is verklaard voor agent '{self._agent}' maar nog niet gebouwd "
            "(staat in runner.GEPLAND)")

    def __iter__(self):
        return iter(self._verklaard)

    def __len__(self) -> int:
        return len(self._verklaard)


def _valideer_agenten(agents: dict) -> None:
    for naam, cfg in agents.items():
        for veld in _VERPLICHTE_AGENT_VELDEN:
            if veld not in cfg:
                raise ValueError(f"agent '{naam}' mist het verplichte CrewAI-veld '{veld}'")
        for tool_naam in cfg.get("tools") or []:
            if tool_naam not in TOOLS and tool_naam not in GEPLAND:
                raise OnbekendeTool(
                    f"agent '{naam}' vraagt de onbekende tool '{tool_naam}' -- die staat niet "
                    "in runner.TOOLS en ook niet aangekondigd in runner.GEPLAND")


def _valideer_taken(tasks: dict, agents: dict) -> None:
    for naam, cfg in tasks.items():
        for veld in _VERPLICHTE_TAAK_VELDEN:
            if veld not in cfg:
                raise ValueError(f"taak '{naam}' mist het verplichte CrewAI-veld '{veld}'")
        if cfg["agent"] not in agents:
            raise ValueError(f"taak '{naam}' verwijst naar de onbekende agent '{cfg['agent']}'")


def laad_uit_dict(agents: dict, tasks: dict) -> "Crew":
    """Bouwt een `Crew` uit al-ingelezen dicts -- `laad()` is een dunne schil hieromheen die de
    YAML-bestanden erbij leest. Apart gehouden zodat de tests (en `pijplijn.py`'s buurfunctie)
    geen bestanden op schijf nodig hebben om de validatie te toetsen."""
    _valideer_agenten(agents)
    _valideer_taken(tasks, agents)
    return Crew(agents, tasks)


def laad(agents_pad: str, tasks_pad: str) -> "Crew":
    """Leest `agents.yaml` en `tasks.yaml` van schijf en bouwt daar een `Crew` uit."""
    with open(agents_pad, encoding="utf-8") as f:
        agents = yaml.safe_load(f) or {}
    with open(tasks_pad, encoding="utf-8") as f:
        tasks = yaml.safe_load(f) or {}
    return laad_uit_dict(agents, tasks)


class Crew(object):
    """De geladen configuratie, uitvoerbaar. `agents` en `tasks` zijn de rauwe dicts (dezelfde
    vorm als de YAML) -- geen eigen objectmodel eromheen, zodat wie de configuratie wil lezen
    (`pijplijn.py`, of een test) niets anders dan gewone dicts tegenkomt."""

    def __init__(self, agents: dict, tasks: dict) -> None:
        self.agents = agents
        self.tasks = tasks

    def tools_voor(self, agent_naam: str) -> VerklaardeTools:
        agent = self.agents[agent_naam]
        return VerklaardeTools(agent_naam, agent.get("tools") or [])

    def verwachte_tools(self) -> set[str]:
        """Alle tools die een onbelemmerde run (geen agent uitgezet) zou aanroepen: de unie van
        de tools van elke agent die ergens een taak heeft. Dit is de maat waarmee de runlog-test
        vergelijkt -- loopt die set uiteen met wat er echt gebeurde, dan is er een stap die
        onder water bleef."""
        tools: set[str] = set()
        for taak in self.tasks.values():
            agent = self.agents[taak["agent"]]
            tools.update(agent.get("tools") or [])
        return tools

    def _llm_voor_deze_agent(self, agent: dict, llm) -> Any:
        """De §4.4-grens: zonder `llm`-sleutel in de agent-configuratie krijgt deze agent nooit
        een taalmodel, ook niet als de aanroeper er een aan `draai()` meegeeft."""
        return llm if "llm" in agent else None

    def draai(self, invoer: dict, llm=None, runlog=None) -> dict:
        """Doorloopt de taken in `tasks.yaml`-volgorde, geeft één `staat`-dict door van taak naar
        taak, en registreert -- als er een `Runlog` is meegegeven -- per taak precies één stap:
        een normale toolaanroep, een bewust uitgezette agent (`uitgezet=True`, geen tool
        aangeroepen), of een verklaarde maar nog niet gebouwde tool (`niet_beschikbaar=True`, de
        toolnaam staat er wél bij). Geen van de drie is stil: elke taak levert een stap op."""
        staat = dict(invoer)
        uitgezet = set(staat.get("uit") or ())
        for taak_id, taak in self.tasks.items():
            agent_naam = taak["agent"]
            agent = self.agents[agent_naam]

            if agent_naam in uitgezet:
                if runlog is not None:
                    runlog.stap(agent_naam, taak_id, None, 0, 0, False, uitgezet=True)
                continue

            for tool_naam in agent.get("tools") or []:
                if tool_naam not in TOOLS:
                    # Verklaard (anders was dit al bij het laden geweigerd), maar nog niet
                    # gebouwd -- `GEPLAND`. Luid registreren, niet stil overslaan en niet crashen:
                    # de rest van de pijplijn moet kunnen doorlopen zolang taak 7 niet klaar is.
                    if runlog is not None:
                        runlog.stap(agent_naam, taak_id, tool_naam, 0, 0, False,
                                     niet_beschikbaar=True)
                    continue

                fn = TOOLS[tool_naam]
                llm_voor_deze_agent = self._llm_voor_deze_agent(agent, llm)
                begin = time.monotonic()
                uitkomst = fn(staat, llm=llm_voor_deze_agent, runlog=runlog)
                duur = time.monotonic() - begin
                staat.update(uitkomst.updates)
                if runlog is not None:
                    runlog.stap(agent_naam, taak_id, tool_naam, uitkomst.rijen_in,
                                 uitkomst.rijen_uit, llm_voor_deze_agent is not None, duur=duur)
        return staat
