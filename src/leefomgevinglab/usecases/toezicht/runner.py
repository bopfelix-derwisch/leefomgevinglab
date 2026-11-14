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

**Een derde, tussenliggend geval: verklaard, maar nog niet gebouwd.** Tot taak 7 stonden
`uitlegger` en `terugkoppelaar` al met hun échte tools in `agents.yaml`, zodat de configuratie het
volledige procesplaatje toonde (R4/§5) terwijl die tools nog niet als Python-functie bestonden.
`GEPLAND` was de plek waar dat *aangekondigd* stond: een naam die hier of in `TOOLS` voorkomt,
laadt gewoon; alleen een naam in geen van beide is een tikfout of een vergeten registratie en
breekt het laden (`OnbekendeTool`). Riep de pijplijn zo'n geplande tool toch aan (`Crew.draai`),
dan kreeg die stap een luide `niet_beschikbaar`-vlag in de runlog in plaats van een stille
`continue` of een crash -- de opdracht vroeg expliciet om dat zichtbaar te maken, en koos niet
voor een startfout, want dat zou het laden van de hele configuratie blokkeren zolang taak 7 niet
klaar was, en precies dát (een configuratie die wél leesbaar is maar niet draait) moest deze
module voorkomen.

Sinds taak 7 zijn `uitleg_genereren` en `terugkoppeling_genereren` echte, aanroepbare tools in
`TOOLS` (zie `tool_uitleg_genereren`/`tool_terugkoppeling_genereren` hieronder) en staan ze niet
meer in `GEPLAND` -- een gewone run van de standaardpijplijn voert `leg_signalen_uit` nu dus echt
uit in plaats van er een luide `niet_beschikbaar`-stap van te maken (zie
`tests/test_toezicht_runlog.py::test_de_uitlegger_draait_nu_echt_in_de_standaardpijplijn`).
`GEPLAND` blijft bestaan als mechanisme voor een toekomstige agent die hetzelfde tussenstadium
doorloopt -- hij is vandaag alleen leeg.

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

**Let op: twee dingen heten hier `context`.** CrewAI's `context` in `tasks.yaml` is een lijst
taak-ID's (de afhankelijkheden van een taak). Het domein-`context`-dict uit `signalen.signalen`
en `dossier.dossier` (metingen, normen, stroomrichting) reist hier als `staat["context"]` --
dezelfde naam, een andere laag. Deze module en `dossier.py` gebruiken het woord correct, elk in
zijn eigen betekenis; de valkuil zit in het vergelijken van de twee bestanden, niet in de code
zelf.

**Eis (b), vervolg: `args` is een samenvatting, nooit de payload.** Elke stap in de runlog draagt
ook `args` -- klein genoeg om te lezen, groot genoeg om te herleiden tegen welke vestiging, welke
vraag of welke uitgezette agents een stap draaide. Nooit de hele `vestiging` (met al haar
voorschriften), nooit `context` (metingen/normen) en nooit het register: dat zou de runlog net zo
onleesbaar maken als een leeg `args`-veld de herkomst onzichtbaar maakt. Zie de `_args_*`-functies
en `_vestiging_id` hieronder voor wat er precies in gaat -- en waarom dat genoeg is.
"""
import time
from collections.abc import Callable, Mapping
from typing import Any, NamedTuple

import yaml

from leefomgevinglab.usecases.toezicht import aquo as aquo_mod
from leefomgevinglab.usecases.toezicht import dossier as dossier_mod
from leefomgevinglab.usecases.toezicht import graaf as graaf_mod
from leefomgevinglab.usecases.toezicht import signalen as signalen_mod
from leefomgevinglab.usecases.toezicht import terugkoppeling as terugkoppeling_mod
from leefomgevinglab.usecases.toezicht import uitleg as uitleg_mod
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
    """Wat een tool teruggeeft aan de runner: de staat-sleutels die hij bijwerkt, de omvang erin
    en eruit -- gemeten door de tool zelf, nooit door de runner verzonnen (huisregel 'geen getal
    wordt getypt') -- en `args`: een kleine, menselijk leesbare samenvatting van waarmee de tool
    draaide (zie de moduledocstring, 'eis (b), vervolg'). Geen van de drie tools die vandaag
    `args` vullen, stopt er de volledige `vestiging`, `context` of `register` in."""
    updates: dict
    rijen_in: int
    rijen_uit: int
    args: dict


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


def _vestiging_id(staat: dict) -> str | None:
    """Het kleinste identificerende veld van de vestiging in `staat` -- `naam`, anders
    `locatiecode`, anders `None`. Dit is wat elke `args`-samenvatting over de vestiging draagt in
    plaats van de vestiging zelf (met al haar voorschriften)."""
    vestiging = staat.get("vestiging") or {}
    return vestiging.get("naam") or vestiging.get("locatiecode")


def tool_atlas_vergunningen(staat: dict, *, llm=None, runlog=None) -> Uitkomst:
    """Leest de vestiging en verrijkt haar voorschriften met de Aquo-referentie uit
    `staat['aquo_ref']`. Ontbreekt die referentie, dan blijft de vestiging onaangeroerd (zie
    `aquo.verrijk`) -- geen netwerk, geen bestand hier, dat levert wie `aquo_ref` aanlevert."""
    vestiging = staat.get("vestiging") or {}
    ref = staat.get("aquo_ref") or {"beschikbaar": False}
    verrijkt = aquo_mod.verrijk(vestiging, ref)
    return Uitkomst({"vestiging": verrijkt}, _tel(vestiging), _tel(verrijkt),
                     args={"vestiging": _vestiging_id(staat)})


def tool_signalen_stellen(staat: dict, *, llm=None, runlog=None) -> Uitkomst:
    """Past de tien deterministische signaalregels toe -- geen netwerk, geen taalmodel, zie
    `signalen.signalen`. `args["regels"]` draagt welke regel-ID's vuurden (niet het bewijs zelf)
    -- klein genoeg voor de runlog, en genoeg om later tegen het uiteindelijke dossier te
    vergelijken (zie `test_de_signalen_in_de_runlog_stap_komen_overeen_met_het_dossier`)."""
    vestiging = staat.get("vestiging") or {}
    context = staat.get("context") or {}
    ruw = signalen_mod.signalen(vestiging, context)
    return Uitkomst({"signalen_ruw": ruw}, _tel(vestiging), _tel(ruw),
                     args={"vestiging": _vestiging_id(staat), "regels": [s["regel"] for s in ruw]})


def tool_dossier_samenstellen(staat: dict, *, llm=None, runlog=None) -> Uitkomst:
    """Stelt het volledige signaaldossier samen, met de meegekregen `runlog` als deel D (R14) --
    op het moment van deze aanroep bevat die runlog al elke stap die ervóór liep (vergunninglezer,
    signaalsteller), dus `dossier()` kan precies de signaalsteller-stap terugvinden."""
    vestiging = staat.get("vestiging") or {}
    context = staat.get("context") or {}
    uitgezet = staat.get("uit")
    d = dossier_mod.dossier(vestiging, context, uit=uitgezet, runlog=runlog)
    return Uitkomst({"dossier": d}, _tel(vestiging), 1,
                     args={"vestiging": _vestiging_id(staat),
                           "uitgezet": sorted(uitgezet) if uitgezet else []})


def tool_toezichtgraaf_bouwen(staat: dict, *, llm=None, runlog=None) -> Uitkomst:
    """Bouwt de bevraagbare graaf uit het register, de metingen en de normen (`graaf.bouw`)."""
    register = staat.get("register") or []
    g = graaf_mod.bouw(register, staat.get("metingen"), staat.get("normen"), staat.get("aquo_ref"))
    return Uitkomst({"graaf": g}, _tel(register), 1, args={"aantal_vestigingen": len(register)})


def tool_vraag_stellen(staat: dict, *, llm=None, runlog=None) -> Uitkomst:
    """Beantwoordt `staat['vraag']` via de toezichtgraaf (`vraag.stel`) -- de enige tool hier die
    een taalmodel gebruikt, en dus alleen zinvol voor een agent die `llm` wél in zijn configuratie
    heeft staan. `args["vraag"]` draagt de vraagtekst zelf (klein), nooit de graaf of de rijen."""
    antwoord = vraag_mod.stel(staat.get("vraag"), staat.get("graaf"), llm)
    return Uitkomst({"antwoord": antwoord}, 1, _tel(antwoord.get("rijen")),
                     args={"vraag": staat.get("vraag")})


def _uitlegvraag(signaal: dict) -> str:
    """De vrije-tekstvraag voor `uitleg.waarom()` bij één signaal: de kop van het signaal plus de
    parameternamen uit zijn bewijs -- niet het hele bewijs (dat zou de vraag net zo onleesbaar
    maken als een `args`-veld met de hele vestiging erin, zie de moduledocstring 'eis (b),
    vervolg'). De namen zijn precies waarop `uitleg.zoek_bronnen` woordgrens-matcht."""
    namen = sorted({b.get("parameter") for b in (signaal.get("bewijs") or []) if b.get("parameter")})
    return " ".join([signaal.get("signaal") or ""] + namen)


def tool_uitleg_genereren(staat: dict, *, llm=None, runlog=None) -> Uitkomst:
    """Vult per signaal in `staat['dossier']` het veld `waarom`, via `uitleg.waarom()` --
    uitsluitend uit wat `staat` meegeeft (`aquo_ref`, `normenset`, `stelselcatalogus`). Ontbreekt
    dat, dan vindt `uitleg.zoek_bronnen` niets en blijft `waarom` afwezig op elk signaal, net zoals
    `tool_atlas_vergunningen` een vestiging onaangeroerd laat zonder `aquo_ref`: deze tool laadt
    zelf geen bestand en doet zelf geen netwerk, dat is aan wie `staat` samenstelt.

    `waarom` wordt alleen gezet als `uitleg.waarom()` `beschikbaar=True` teruggeeft -- anders
    blijft de sleutel afwezig (zie `dossier._signaal_deel_b`, die `stap` op dezelfde manier
    optioneel houdt): een afwezig veld is hier "geen bron gevonden", geen leeg maar aanwezig veld
    dat een poging suggereert die niets opleverde."""
    dossier = staat.get("dossier") or {}
    signalen_lijst = dossier.get("signalen") or []
    aquo_ref = staat.get("aquo_ref")
    normenset = staat.get("normenset")
    catalogus = staat.get("stelselcatalogus")

    def _zoek(vraag, n):
        return uitleg_mod.zoek_bronnen(vraag, n, aquo_ref=aquo_ref, normenset=normenset,
                                        catalogus=catalogus)

    bijgewerkt, aantal_beschikbaar = [], 0
    for s in signalen_lijst:
        nieuw = dict(s)
        uit = uitleg_mod.waarom(_uitlegvraag(s), _zoek=_zoek, llm=llm)
        if uit["beschikbaar"]:
            nieuw["waarom"] = uit["tekst"]
            aantal_beschikbaar += 1
        bijgewerkt.append(nieuw)
    nieuw_dossier = {**dossier, "signalen": bijgewerkt}
    return Uitkomst({"dossier": nieuw_dossier}, len(signalen_lijst), aantal_beschikbaar,
                     args={"vestiging": _vestiging_id(staat), "signalen": len(signalen_lijst),
                           "met_uitleg": aantal_beschikbaar})


def tool_terugkoppeling_genereren(staat: dict, *, llm=None, runlog=None) -> Uitkomst:
    """Registreert één beoordeling (`terugkoppeling.registreer`) -- `staat` draagt `vestiging`
    (voor de id), `regel_id`, `oordeel` en optioneel `opmerking`. Geen netwerk, geen taalmodel:
    dit is boekhouden, geen generatie. Geen taak in de standaardpijplijn roept deze tool aan (zie
    `tasks.yaml`) -- net als `toezichtgraaf_bouwen`/`vraag_stellen` is dit een los te starten
    actie, rechtstreeks via `TOOLS['terugkoppeling_genereren']` of een latere eigen taak."""
    oordeel = terugkoppeling_mod.registreer(
        _vestiging_id(staat), staat.get("regel_id"), staat.get("oordeel"),
        opmerking=staat.get("opmerking"))
    bestaand = staat.get("beoordelingen") or []
    bijgewerkt = bestaand + [oordeel]
    return Uitkomst({"beoordelingen": bijgewerkt}, len(bestaand), len(bijgewerkt),
                     args={"vestiging": _vestiging_id(staat), "regel_id": staat.get("regel_id"),
                           "oordeel": staat.get("oordeel")})


#: Echte, aanroepbare tools -- de enige namen die een agent zonder meer mag gebruiken.
TOOLS: dict[str, Callable[..., Uitkomst]] = {
    "atlas_vergunningen": tool_atlas_vergunningen,
    "signalen_stellen": tool_signalen_stellen,
    "dossier_samenstellen": tool_dossier_samenstellen,
    "toezichtgraaf_bouwen": tool_toezichtgraaf_bouwen,
    "vraag_stellen": tool_vraag_stellen,
    "uitleg_genereren": tool_uitleg_genereren,
    "terugkoppeling_genereren": tool_terugkoppeling_genereren,
}

#: Namen die wel verklaard zijn in `agents.yaml` maar nog niet gebouwd -- zie de moduledocstring.
#: Sinds taak 7 leeg: `uitleg_genereren` en `terugkoppeling_genereren` zijn nu echte `TOOLS`.
#: Blijft bestaan als mechanisme voor een volgende agent die hetzelfde tussenstadium doorloopt.
GEPLAND: set[str] = set()


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
        toolnaam staat er wél bij). Geen van de drie is stil: elke taak levert een stap op.

        **De callable komt altijd via `tools_voor(agent_naam)`, nooit rechtstreeks uit `TOOLS`.**
        Dat is eis (a) in de uitvoering, niet alleen in de loopstructuur: zou deze methode ooit
        veranderen in iets dat niet meer per se over de eigen `tools`-lijst van de agent itereert,
        dan vangt `tools_voor` een onverklaarde tool nog steeds af (`NietVerklaardeTool`). Een tool
        die wél verklaard is maar nog niet gebouwd (`GEPLAND`) geeft via diezelfde weg
        `NietBeschikbaar` -- dat is hier geen fout om door te laten, maar het signaal om de luide
        `niet_beschikbaar`-stap te registreren in plaats van de tool aan te roepen."""
        staat = dict(invoer)
        uitgezet = set(staat.get("uit") or ())
        for taak_id, taak in self.tasks.items():
            agent_naam = taak["agent"]
            agent = self.agents[agent_naam]

            if agent_naam in uitgezet:
                if runlog is not None:
                    runlog.stap(agent_naam, taak_id, None, 0, 0, False, uitgezet=True,
                                 args={"vestiging": _vestiging_id(staat)})
                continue

            for tool_naam in agent.get("tools") or []:
                try:
                    fn = self.tools_voor(agent_naam)[tool_naam]
                except NietBeschikbaar:
                    # Verklaard (anders was dit al bij het laden geweigerd), maar nog niet
                    # gebouwd -- `GEPLAND`. Luid registreren, niet stil overslaan en niet crashen:
                    # de rest van de pijplijn moet kunnen doorlopen zolang taak 7 niet klaar is.
                    if runlog is not None:
                        runlog.stap(agent_naam, taak_id, tool_naam, 0, 0, False,
                                     niet_beschikbaar=True,
                                     args={"vestiging": _vestiging_id(staat)})
                    continue

                llm_voor_deze_agent = self._llm_voor_deze_agent(agent, llm)
                begin = time.monotonic()
                uitkomst = fn(staat, llm=llm_voor_deze_agent, runlog=runlog)
                duur = time.monotonic() - begin
                staat.update(uitkomst.updates)
                if runlog is not None:
                    runlog.stap(agent_naam, taak_id, tool_naam, uitkomst.rijen_in,
                                 uitkomst.rijen_uit, llm_voor_deze_agent is not None, duur=duur,
                                 args=uitkomst.args)
        return staat
