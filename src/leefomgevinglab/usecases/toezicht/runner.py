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
`rijen_uit`, gemeten, nooit getypt) en of er een taalmodel **gebruikt** is -- demand (b) van §4.2
vraagt letterlijk "of er een taalmodel aan te pas kwam", en dat is gebruik, geen aanbod. Een agent
zonder `llm`-sleutel in zijn configuratie krijgt het meegegeven `llm` hier nooit doorgegeven, ook
niet als de aanroeper er een aan `draai()` geeft -- zie `_llm_voor_deze_agent`. Dat maakt de
belofte "signaalsteller en vergunninglezer gebruiken nooit een taalmodel" per run aantoonbaar (de
runlog zegt het), niet alleen een statische eigenschap van de YAML (die ook bewaakt wordt, zie de
tests, maar op zichzelf niets zou bewijzen over een werkelijke run).

**Fix-ronde 2, bevinding E: eligibility is niet gebruik.** Tot deze fix registreerde het
`llm`-veld alleen of een agent een taalmodel *mocht* krijgen (`llm_voor_deze_agent is not None`),
niet of zijn tool het ook echt heeft *aangeroepen*. Dat verschil was voor `signaalsteller`/
`vergunninglezer` onzichtbaar (voor hen is "mocht" altijd al `False`, dus "gebruikte" ook), maar
voor `uitlegger` niet: `uitleg.waarom()` roept de llm alleen aan als er een treffer is om te
herformuleren, en een stap zonder treffer logde vóór deze fix toch `llm: True`. `draai()` wikkelt
`llm_voor_deze_agent` nu in `_AangeroepenLlm`, een dunne, transparante telproxy, en registreert
`proxy.aangeroepen` in plaats van de kale eligibility-check.

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
    """Het kleinste identificerende veld van de vestiging in `staat` -- `naam` (plus `kenmerk`
    als dat er is), anders `locatiecode`, anders `None`. Dit is wat elke `args`-samenvatting over
    de vestiging draagt in plaats van de vestiging zelf (met al haar voorschriften).

    Eindreview, bevinding 1: twee vergunningen van dezelfde vestiging delen hun `naam` (bv.
    CORUSNB/Tata Steel Nederland Tubes B.V., live twee kenmerken onder één locatiecode) -- zonder
    `kenmerk` erbij zou de runlog van zo'n dossier niet laten zien welke van de twee draaide. Dit
    is geen vervanging van de registerbrede identiteit uit `toezicht_register.identiteiten`
    (die kent het hele register, deze functie ziet maar één `vestiging`-dict), maar wel genoeg om
    de runlog van de andere te onderscheiden zodra `kenmerk` gevuld is."""
    vestiging = staat.get("vestiging") or {}
    naam = vestiging.get("naam")
    kenmerk = vestiging.get("kenmerk")
    if naam and kenmerk:
        return f"{naam} ({kenmerk})"
    return naam or vestiging.get("locatiecode")


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


#: Regels wiens vraag letterlijk over de stof/code zelf gaat -- is deze naam een geldige
#: Aquo-referentie, en wat is de KRW-norm ervoor. Alleen déze regels mogen de parameternamen uit
#: hun bewijs in de uitlegvraag meesturen (fix-ronde 2, bevinding B). Voor de rest zou dat de
#: vraag naar de verkeerde bron sturen: "vracht niet te bepalen" gaat over een ontbrekend
#: debietvoorschrift, niet over of "Minerale olie" een geldige Aquo-naam is, en met `n=3` vulden
#: de Aquo-treffers op die naam élke beschikbare plek op -- vóór de proclaimer-bron (fix-ronde 1)
#: ooit de kans kreeg te vuren op het eigen, juiste trefwoord van het signaal ("regime",
#: "bovenstrooms"). Live geprobeerd: `niet_regime_zuiver` en `vracht_onbepaald` kregen zo
#: woordelijk dezelfde drie Aquo-zinnen als uitleg, geen van beide over hun eigen onderwerp.
_STOF_GEBONDEN_REGELS = {"geen_onafhankelijke_meting", "vervallen_code", "niet_in_referentie"}


def _uitlegvraag(signaal: dict) -> str:
    """De vrije-tekstvraag voor `uitleg.waarom()` bij één signaal: de kop van het signaal, en
    alleen voor de regels in `_STOF_GEBONDEN_REGELS` ook de parameternamen uit zijn bewijs --
    niet het hele bewijs (dat zou de vraag net zo onleesbaar maken als een `args`-veld met de hele
    vestiging erin, zie de moduledocstring 'eis (b), vervolg'). Voor de overige regels is de kop
    zelf de vraag: dat is wat het signaal *is*, en precies waarop de /kmg-proclaimer-bron
    woordgrens-matcht (`niet_regime_zuiver` op "regime", `norm_overschreden_bovenstrooms` op
    "bovenstrooms"). Levert dat voor zo'n regel ook niets op, dan blijft `waarom` afwezig -- geen
    verklaring is hier de juiste uitkomst, geen verklaring over de verkeerde vraag."""
    kop = signaal.get("signaal") or ""
    if signaal.get("regel") not in _STOF_GEBONDEN_REGELS:
        return kop
    namen = sorted({b.get("parameter") for b in (signaal.get("bewijs") or []) if b.get("parameter")})
    return " ".join([kop] + namen)


def tool_uitleg_genereren(staat: dict, *, llm=None, runlog=None) -> Uitkomst:
    """Vult per signaal in `staat['dossier']` het veld `waarom`, via `uitleg.waarom()`. Drie van
    de vier bronnen komen uit wat `staat` meegeeft (`aquo_ref`, `normenset`, `stelselcatalogus`);
    ontbreekt dat, dan vinden die drie niets, net zoals `tool_atlas_vergunningen` een vestiging
    onaangeroerd laat zonder `aquo_ref` -- deze tool laadt zelf geen bestand en doet zelf geen
    netwerk, dat is aan wie `staat` samenstelt. De vierde bron (de /kmg-proclaimer, fix-ronde 1)
    is intrinsiek en vraagt geen `staat`-sleutel: zij kan dus ook zonder enige geïnjecteerde
    referentie een signaal als `niet_regime_zuiver` of `norm_overschreden_bovenstrooms` uitleggen.

    `waarom` wordt alleen gezet als `uitleg.waarom()` `beschikbaar=True` teruggeeft én de tekst
    nog niet door een eerder, zwaarder signaal geclaimd is -- anders blijft de sleutel afwezig
    (zie `dossier._signaal_deel_b`, die `stap` op dezelfde manier optioneel houdt). Vóór de
    eindreview betekende dat afwezige veld op de pagina altijd hetzelfde: niets te zien, alsof er
    geen `waarom` bestond. **Fix-ronde (eindreview, bevinding 5):** dat verstopte zowel de eerlijke
    "geen van de vier bronnen heeft hier een treffer" als de bewuste onderdrukking van een
    gevonden-maar-dubbele tekst (bevinding B hieronder) achter hetzelfde niets, en het product se
    eigen stelling is nu juist dat een gat zelf een signaal is (zie `dossier._voorbehouden`). Elk
    signaal zonder `waarom` draagt daarom nu altijd een `waarom_reden` (de tekst die uitlegt
    waaróm er niets staat) plus, waar van toepassing, `waarom_gedupliceerd=True` om de twee
    oorzaken van elkaar te onderscheiden -- `uitleg.waarom()`'s eigen `_GEEN_TREFFER`-tekst noemt
    bovendien zelf alle vier de bronnen (zie die module), dus deze tool verzint niets, zij geeft
    alleen door wat `uitleg.waarom()` al zei maar eerder nergens landde.

    **Fix-ronde 2, bevinding A.** `waarom_vindplaatsen` gaat er sinds deze fix altijd naast
    `waarom` mee -- de harde regel ("elke uitleg draagt minstens één benoemde vindplaats") hield
    binnen `uitleg.waarom()` stand, maar deze tool liet `uit["vindplaatsen"]` eerder op de vloer
    vallen en zette alleen `uit["tekst"]` door. Een inspecteur die de pagina of het werkblad leest
    zag dus een uitleg zonder bron, precies de situatie die het plan "erger dan geen uitleg" noemt.
    `waarom` blijft zelf een platte string (de taalregel-test concateneert hem rechtstreeks met
    `+`, zie `test_toezicht_signalen.py`); de vindplaatsen staan ernaast, niet erin verweven."""
    dossier = staat.get("dossier") or {}
    signalen_lijst = dossier.get("signalen") or []
    aquo_ref = staat.get("aquo_ref")
    normenset = staat.get("normenset")
    catalogus = staat.get("stelselcatalogus")

    def _zoek(vraag, n):
        return uitleg_mod.zoek_bronnen(vraag, n, aquo_ref=aquo_ref, normenset=normenset,
                                        catalogus=catalogus)

    # Fix-ronde 2, bevinding B (tweede helft): twee signalen mogen nooit letterlijk dezelfde
    # `waarom`-tekst dragen. Dat gebeurt legitiem -- `vervallen_code` en `geen_onafhankelijke_
    # meting` kunnen voor dezelfde stof (bv. 'Zwevende stof') allebei op dezelfde Aquo-treffer
    # uitkomen -- maar twee identieke verklaringen naast elkaar op de pagina lezen als een
    # kopieerfout, niet als twee keer een overwogen, eigen antwoord. `signalen_lijst` is al
    # gerangschikt op zwaarte en omvang (zie `signalen.signalen`), dus het eerste signaal dat een
    # tekst claimt (het zwaarst wegende) houdt hem; een latere, lichtere herhaling krijgt in plaats
    # daarvan geen verklaring -- de constante uit de taakbrief: geen verklaring is hier de juiste
    # uitkomst, niet een herhaalde. Fix-ronde (eindreview, bevinding 5): die herhaling krijgt nu
    # wel een eigen `waarom_reden`, zodat zij niet hetzelfde "niets" oplevert als een signaal
    # zonder enige bron.
    _GEDUPLICEERDE_REDEN = (
        "Deze verklaring is woordelijk gelijk aan die van een eerder, zwaarder wegend signaal in "
        "dit dossier en wordt daarom hier niet herhaald -- niet omdat er geen bron voor is."
    )
    bijgewerkt, aantal_beschikbaar, gebruikte_teksten = [], 0, set()
    for s in signalen_lijst:
        nieuw = dict(s)
        uit = uitleg_mod.waarom(_uitlegvraag(s), _zoek=_zoek, llm=llm)
        if uit["beschikbaar"] and uit["tekst"] not in gebruikte_teksten:
            nieuw["waarom"] = uit["tekst"]
            nieuw["waarom_vindplaatsen"] = uit["vindplaatsen"]
            gebruikte_teksten.add(uit["tekst"])
            aantal_beschikbaar += 1
        elif uit["beschikbaar"]:
            nieuw["waarom_reden"] = _GEDUPLICEERDE_REDEN
            nieuw["waarom_gedupliceerd"] = True
        else:
            nieuw["waarom_reden"] = uit["reden"]
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


class _AangeroepenLlm:
    """Dunne telproxy om een geïnjecteerde `llm` heen (fix-ronde 2, bevinding E). `Crew.draai`
    moet per stap twee verschillende dingen kunnen zeggen: mocht deze agent een taalmodel krijgen
    (eligibility, bepaald door `_llm_voor_deze_agent` via de `llm`-sleutel in de configuratie) én
    heeft zijn tool het ook echt aangeroepen (gebruik). Die twee liepen tot deze fix door elkaar:
    de runlog registreerde `llm=True` zodra een agent er een *mocht* krijgen, ook als zijn tool
    die aanroep nooit deed -- precies het geval van `uitlegger` zonder treffer (`uitleg.waarom()`
    roept de llm alleen aan als er iets te herformuleren is).

    Transparant voor de tool: deze proxy is zelf aanroepbaar en geeft de aanroep ongewijzigd door
    aan de echte `llm`, dus geen tool (`uitleg.py`, `vraag.py`) hoeft hier iets van te weten."""

    def __init__(self, echte_llm) -> None:
        self._echte_llm = echte_llm
        self.aangeroepen = False

    def __call__(self, *args, **kwargs):
        self.aangeroepen = True
        return self._echte_llm(*args, **kwargs)


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
                # Fix-ronde 2, bevinding E: de proxy meet gebruik, los van eligibility. Zonder
                # eligibility (`llm_voor_deze_agent is None`) is er niets om in te pakken en blijft
                # `llm` gewoon `None` -- een tool die `llm is None` toetst (zoals `uitleg.waarom`)
                # moet dat onderscheid onveranderd blijven zien.
                proxy = _AangeroepenLlm(llm_voor_deze_agent) if llm_voor_deze_agent is not None \
                    else None
                begin = time.monotonic()
                uitkomst = fn(staat, llm=proxy, runlog=runlog)
                duur = time.monotonic() - begin
                staat.update(uitkomst.updates)
                if runlog is not None:
                    runlog.stap(agent_naam, taak_id, tool_naam, uitkomst.rijen_in,
                                 uitkomst.rijen_uit, proxy.aangeroepen if proxy is not None
                                 else False, duur=duur, args=uitkomst.args)
        return staat
