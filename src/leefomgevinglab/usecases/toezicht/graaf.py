"""De toezichtgraaf: register, metingen, normen en de Aquo-referentie als RDF-triples.

**Waarom een graaf en niet gewoon een tabel.** Een tabel kan een grenswaarde vastleggen; zij kan
niet vastleggen *hoe zeker* die grenswaarde is zonder een eigen kolom per veld te verzinnen, en
die kolom raakt dan los van de rij zodra iemand filtert of joint. In deze graaf is `herkomst` en
`zekerheid` een eigenschap van de **bewering zelf** -- niet van de vestiging, niet van het
voorschrift als geheel -- zodat een vraag als "welke grenswaarden zijn aangenomen in plaats van
uit de bron gelezen?" een gewone SPARQL-query is (zie de test bij stap 3 van het takenbrief, en
`vraag.py` die zo'n vraag via een taalmodel laat stellen).

**De ontwerpkeuze: een los knooppunt per bewering, geen RDF-reïficatie, geen named graphs.**
RDF-reïficatie (`rdf:Statement` met `rdf:subject`/`rdf:predicate`/`rdf:object`) kent precies dit
probleem op, maar in de praktijk is hij omslachtig te bevragen (vier triples om één bewering te
annoteren) en rdflib's eigen SPARQL-laag behandelt hem niet anders dan los drijvende triples --
er is geen voordeel tegenover het hier gekozen patroon. Named graphs (één graph per herkomst) was
het andere alternatief, maar `ld.store` werkt met een kale `rdflib.Graph`, niet met een
`Dataset`/`ConjunctiveGraph`; dat omzetten raakt een bestaande, geteste laag voor een voordeel dat
hier niet nodig is (we annoteren per veld, niet per hele graaf).

In plaats daarvan krijgt elk feit waarvan de zekerheid kan variëren zijn eigen knooppunt (een
"n-ary relation" in de gangbare RDF-terminologie, verwant aan het singleton-property-patroon):
een `t:Bewering`-node draagt `t:veld`, `t:waarde`, `t:zekerheid` en optioneel `t:herkomst`, en het
hoofdobject (`t:Vestiging` of `t:Voorschrift`) wijst daar met een eigen predicaat naar
(`t:heeftVeld`, `t:heeftHoedanigheid`, `t:heeftAquoKoppeling`). Zo kan één voorschrift twee
beweringen met uiteenlopende zekerheid dragen (de hoedanigheid "aangenomen", de Aquo-koppeling
"afgeleid") zonder dat die twee waarden op dezelfde triple-sleutel botsen.

**Wat wél en niet een eigen Bewering-node krijgt.** De rechtstreekse Atlas-velden van een
voorschrift (`parameter`, `waarde`, `eenheid`, `bemonstering`, `rd`) zijn altijd een directe
lezing van de bron -- daarover bestaat in dit lab geen gedocumenteerde onzekerheid, dus zij staan
als gewone literal-properties op het Voorschrift-knooppunt. De twee velden die
`usecases/kmg/lozingsmodel.py` en `toezicht/aquo.py` zelf al als onzeker documenteren --
de hoedanigheid (de Atlas geeft hem nooit, zie `HOEDANIGHEID_AANNAME`) en de Aquo-koppeling (een
naam-op-code-match, dus "afgeleid", niet "uit de bron") -- krijgen wel een Bewering. Dezelfde
negen kaartvelden van een vestiging als `dossier._KAART_VELDEN` (deel A van het signaaldossier)
krijgen elk een Bewering, zodat ook "welke vestiging mist een kenmerk?" een SPARQL-vraag wordt.
Deze module roept `dossier.dossier()` daarvoor niet aan -- dat zou de hele signaalmotor meetrekken
voor wat hier alleen een veldenlijst is -- en houdt die lijst zelfstandig (kleine, bewuste
duplicatie van een veldnaam-opsomming, niet van logica).

**Zekerheid komt uit één bron.** `kmg.lozingsmodel.ZEKERHEDEN` is het enige vocabulaire voor
"uit de bron"/"afgeleid"/"aangenomen"/"ontbreekt" in dit lab (R13); deze module importeert die
tuple in plaats van de woorden hier opnieuw te typen.
"""
from rdflib import BNode, Graph, Literal, Namespace, RDF

from leefomgevinglab.usecases.kmg.lozingsmodel import HOEDANIGHEID_AANNAME, ZEKERHEDEN
from leefomgevinglab.usecases.toezicht import aquo as aquo_mod

#: Het namespace van de toezichtgraaf -- letterlijk zoals het plan het vastlegt.
T = Namespace("https://leefomgevinglab.felixisfelix.com/toezicht#")

UIT_DE_BRON, AFGELEID, AANGENOMEN, ONTBREEKT = ZEKERHEDEN

# Dezelfde negen velden als `dossier._KAART_VELDEN` (deel A van het signaaldossier), hier
# zelfstandig gehouden -- zie de moduledocstring voor de reden.
VESTIGING_VELDEN = ("naam", "plaats", "locatie", "locatiecode", "vestigingsnummer_kvk",
                    "kenmerk", "besluitdatum", "waterlichaam", "url")


def _bewering(graph: Graph, veld: str, waarde, zekerheid: str, herkomst: str | None = None):
    """Eén `t:Bewering`-knooppunt: een feit met zijn eigen herkomst en zekerheid, los van het
    object waarover het gaat. `waarde` mag `None` zijn (het veld ontbreekt) -- dan blijft
    `t:waarde` weg, net als `dossier._kaartveld` voor een ontbrekend veld geen waarde toont."""
    node = BNode()
    graph.add((node, RDF.type, T.Bewering))
    graph.add((node, T.veld, Literal(veld)))
    if waarde is not None:
        graph.add((node, T.waarde, Literal(waarde)))
    graph.add((node, T.zekerheid, Literal(zekerheid)))
    if herkomst:
        graph.add((node, T.herkomst, Literal(herkomst)))
    return node


def _vestiging_triples(graph: Graph, vestiging: dict):
    v = BNode()
    graph.add((v, RDF.type, T.Vestiging))
    for veld in VESTIGING_VELDEN:
        waarde = vestiging.get(veld)
        aanwezig = waarde not in (None, "", [])
        bewering = _bewering(graph, veld, waarde, UIT_DE_BRON if aanwezig else ONTBREEKT)
        graph.add((v, T.heeftVeld, bewering))
    return v


def _voorschrift_triples(graph: Graph, vestiging_node, voorschrift: dict):
    vn = BNode()
    graph.add((vn, RDF.type, T.Voorschrift))
    graph.add((vestiging_node, T.heeftVoorschrift, vn))

    # De rechtstreekse Atlas-velden: altijd een directe lezing, geen afgeleid of aangenomen feit
    # over te bevragen, dus gewone literal-properties op het voorschrift zelf.
    for veld in ("parameter", "waarde", "eenheid", "bemonstering", "rd"):
        waarde = voorschrift.get(veld)
        if waarde is not None:
            graph.add((vn, T[veld], Literal(waarde)))

    # De hoedanigheid: de Atlas geeft dit veld nooit (zie `lozingsmodel`-moduledocstring), dus elk
    # voorschrift draagt hier de aanname van dit lab. De grenswaarde zelf is "uit de bron"; de
    # hoedanigheid waarmee zij gelezen wordt, is dat niet -- dat verschil is precies waarom deze
    # twee dingen niet op hetzelfde knooppunt-veld kunnen staan.
    hoedanigheid = _bewering(graph, "hoedanigheid", HOEDANIGHEID_AANNAME["code"],
                             HOEDANIGHEID_AANNAME["zekerheid"], HOEDANIGHEID_AANNAME["herkomst"])
    graph.add((vn, T.heeftHoedanigheid, hoedanigheid))

    # De Aquo-koppeling: alleen een bewering als er echt gezocht is. `toezicht.aquo.verrijk` laat
    # de sleutel `aquo` weg wanneer de referentie niet beschikbaar was (niet gezocht); dat is geen
    # bewering om vast te leggen, dus dan komt er ook geen Bewering-node.
    if "aquo" in voorschrift:
        code = voorschrift.get("aquo")
        status = voorschrift.get("aquo_status")
        if code is None:
            zekerheid, herkomst = ONTBREEKT, "geen Aquo-code gevonden voor deze parameternaam"
        else:
            zekerheid = AFGELEID
            herkomst = ("Aquo-domeintabel Parameter (status Vervallen)" if status == "Vervallen"
                       else "Aquo-domeintabel Parameter")
        koppeling = _bewering(graph, "aquo", code, zekerheid, herkomst)
        graph.add((vn, T.heeftAquoKoppeling, koppeling))
    return vn


def _metingen_triples(graph: Graph, metingen: dict | None):
    """Metingen uit het Waterkwaliteitsportaal (vorm: `kmg.metingen.laad()`) -- een gemeten
    waarde is altijd "uit de bron", er is hier niets af te leiden of aan te nemen."""
    metingen = metingen or {}
    bron_naam = (metingen.get("bron") or {}).get("naam") or "Waterkwaliteitsportaal"
    meetjaar = metingen.get("meetjaar")
    herkomst = f"{bron_naam}, meetjaar {meetjaar}" if meetjaar else bron_naam
    for punt in metingen.get("punten") or []:
        for stof in punt.get("stoffen") or []:
            node = BNode()
            graph.add((node, RDF.type, T.Meting))
            if punt.get("code"):
                graph.add((node, T.meetpunt, Literal(punt["code"])))
            if punt.get("waterlichaam"):
                graph.add((node, T.waterlichaam, Literal(punt["waterlichaam"])))
            if stof.get("code"):
                graph.add((node, T.stof, Literal(stof["code"])))
            if stof.get("mediaan") is not None:
                graph.add((node, T.mediaan, Literal(stof["mediaan"])))
            if stof.get("maximum") is not None:
                graph.add((node, T.maximum, Literal(stof["maximum"])))
            if stof.get("eenheid"):
                graph.add((node, T.eenheid, Literal(stof["eenheid"])))
            graph.add((node, T.zekerheid, Literal(UIT_DE_BRON)))
            graph.add((node, T.herkomst, Literal(herkomst)))


def _normen_triples(graph: Graph, normen: dict | None):
    """KRW-normen (vorm: `kmg.doelen.laad_normen()`) -- idem, een gepubliceerde norm is "uit de
    bron"."""
    normen = normen or {}
    bron_naam = (normen.get("bron") or {}).get("naam") or "KRW-toetsresultaten"
    for meetpunt, rijen in (normen.get("normen") or {}).items():
        for rij in rijen or []:
            node = BNode()
            graph.add((node, RDF.type, T.Norm))
            graph.add((node, T.meetpunt, Literal(meetpunt)))
            if rij.get("parameter"):
                graph.add((node, T.stof, Literal(rij["parameter"])))
            if rij.get("norm") is not None:
                graph.add((node, T.waarde, Literal(rij["norm"])))
            if rij.get("eenheid"):
                graph.add((node, T.eenheid, Literal(rij["eenheid"])))
            if rij.get("grondslag"):
                graph.add((node, T.grondslag, Literal(rij["grondslag"])))
            graph.add((node, T.zekerheid, Literal(UIT_DE_BRON)))
            graph.add((node, T.herkomst, Literal(bron_naam)))


def bouw(register: list[dict] | None, metingen: dict | None, normen: dict | None,
         aquo: dict | None) -> Graph:
    """Het register, de metingen, de normen en de Aquo-referentie als één bevraagbare graaf.

    `register` mag ongeverrijkt binnenkomen (zonder `aquo`-sleutel op de voorschriften) -- deze
    functie verrijkt elke vestiging zelf via `toezicht.aquo.verrijk`, met dezelfde referentie die
    zij meekrijgt. Is `aquo` niet beschikbaar, dan blijft een vestiging ongewijzigd (zie
    `verrijk()`) en komt er voor die vestiging geen Aquo-koppeling-bewering."""
    graph = Graph()
    graph.bind("t", T)
    for vestiging in register or []:
        verrijkt = aquo_mod.verrijk(vestiging, aquo or {})
        vn = _vestiging_triples(graph, verrijkt)
        for voorschrift in verrijkt.get("voorschriften") or []:
            _voorschrift_triples(graph, vn, voorschrift)

    _metingen_triples(graph, metingen)
    _normen_triples(graph, normen)
    return graph


def stoffen_met_norm(normen: dict | None) -> set[str]:
    """De Aquo-codes die in `normen` een KRW-norm hebben -- dezelfde set die
    `signalen.regel_geen_onafhankelijke_meting` nodig heeft als `context["stoffen_met_norm"]`
    (plan, zie `signalen.py`). Tot nu toe (taak 2/4) bleef die sleutel overal ongevuld; omdat deze
    module de normen al in exact deze vorm leest, is dit de plek waar hij voor het eerst ergens
    vanzelf uitkomt, in plaats van los opnieuw opgezocht te worden."""
    codes: set[str] = set()
    for rijen in (normen or {}).get("normen", {}).values():
        for rij in rijen or []:
            code = rij.get("parameter")
            if code:
                codes.add(code)
    return codes
