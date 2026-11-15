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
als gewone literal-properties op het Voorschrift-knooppunt. Twee andere velden krijgen wel een
Bewering, elk gedocumenteerd als onzeker in de module die hem invoert: de hoedanigheid (de Atlas
geeft hem nooit, zie `usecases/kmg/lozingsmodel.py`, `HOEDANIGHEID_AANNAME`) en de Aquo-koppeling
(een naam-op-code-match, dus "afgeleid", niet "uit de bron", zie `toezicht/aquo.py`). Dezelfde
negen kaartvelden van een vestiging als `dossier._KAART_VELDEN` (deel A van het signaaldossier)
krijgen elk een Bewering, zodat ook "welke vestiging mist een kenmerk?" een SPARQL-vraag wordt.
Deze module roept `dossier.dossier()` daarvoor niet aan -- dat zou de hele signaalmotor meetrekken
voor wat hier alleen een veldenlijst is -- en houdt die lijst zelfstandig (kleine, bewuste
duplicatie van een veldnaam-opsomming, niet van logica).

**Wat bewust géén Bewering krijgt: de geldigheidsperiode.** `lozingsmodel.py` noemt de
geldigheidsperiode naast de hoedanigheid als het andere veld dat de Atlas niet geeft -- maar dat
is hier niet als derde Bewering gemodelleerd, en dat is geen omissie.
`signalen.regel_geen_geldigheidsduur` behandelt het al als een vaststaand gegeven voor het hele
register (elke vergunning mist hem, zonder uitzondering), niet als iets dat per voorschrift
verschilt; een Bewering per voorschrift zou daar niets aan toevoegen boven die ene registerbrede
constatering.

**Zekerheid komt uit één bron.** `kmg.lozingsmodel.ZEKERHEDEN` is het enige vocabulaire voor
"uit de bron"/"afgeleid"/"aangenomen"/"ontbreekt" in dit lab (R13); deze module importeert die
tuple in plaats van de woorden hier opnieuw te typen.
"""
from rdflib import BNode, Graph, Literal, Namespace, RDF

from leefomgevinglab.usecases.kmg.lozingsmodel import HOEDANIGHEID_AANNAME, ZEKERHEDEN
from leefomgevinglab.usecases.toezicht import aquo as aquo_mod
from leefomgevinglab.usecases.toezicht import signalen as signalen_mod

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


#: De velden die een mens nodig heeft om te weten *welke* vergunning hij voor zich heeft. Deze
#: staan óók als gewone literal op de vestiging, naast hun Bewering.
#:
#: **Waarom die dubbeling er is -- gevonden door de draaiende dienst te bevragen.** Het taalmodel
#: schreef een correcte brugvraag en selecteerde `?vestiging`; het antwoord was 100 rijen met
#: blank-node-id's (`Na5f43702f94c...`), onbruikbaar voor een lezer. De naam stond namelijk alleen
#: achter `t:heeftVeld` -> Bewering -> `t:waarde`, met een filter op `t:veld "naam"`: drie stappen
#: diep. Dat is de juiste vorm voor een vraag over zekerheid, maar een val voor elke vraag die
#: gewoon wil weten welke vergunning het is -- en dat is de meeste. De Bewering blijft bestaan en
#: blijft de zekerheid dragen; dit is de leesbare ingang ernaast.
IDENTIFICERENDE_VELDEN = ("naam", "locatiecode", "kenmerk")


def _vestiging_triples(graph: Graph, vestiging: dict, waterlichaam: str | None = None):
    """De vestiging als knooppunt.

    `waterlichaam` is het **afgeleide** waterlichaam van deze vergunning, uit haar eigen
    coördinaat opgezocht (zie `graafbouw`). Het staat apart omdat de Atlas dat veld nooit levert:
    het zit niet in `vestiging` maar in de context. Twee dingen hangen eraan:

    1. **De schakel naar een meting.** Een `t:Meting` draagt `t:waterlichaam`; de vestiging deed
       dat niet, en daarmee was er geen enkel pad van een vergunning naar een gemeten waarde. Het
       taalmodel verzon op de brugvraag `?vestiging t:heeftMeting ?meting` -- een predicaat dat
       niet bestaat -- en had ook geen alternatief. De vraag "een papierbevinding én een meting
       boven de norm" was dus onuitdrukbaar, hoe goed het model ook zou raden.
    2. **De zekerheid klopt nu.** De Bewering over `waterlichaam` zei voor élke vergunning
       `"ontbreekt"`, terwijl de route het wél wist -- dezelfde tegenspraak die op `/wasstraat`
       al moest wijken. Met een afgeleide waarde staat er `"afgeleid"`; zonder blijft het
       `"ontbreekt"`, want afwezig moet afwezig blijven.
    """
    v = BNode()
    graph.add((v, RDF.type, T.Vestiging))
    for veld in VESTIGING_VELDEN:
        waarde = vestiging.get(veld)
        if veld == "waterlichaam" and waarde in (None, "", []) and waterlichaam:
            bewering = _bewering(graph, veld, waterlichaam, AFGELEID,
                                  "opgezocht uit de coördinaat van deze vergunning")
            graph.add((v, T.heeftVeld, bewering))
            graph.add((v, T.waterlichaam, Literal(waterlichaam)))
            continue
        aanwezig = waarde not in (None, "", [])
        bewering = _bewering(graph, veld, waarde, UIT_DE_BRON if aanwezig else ONTBREEKT)
        graph.add((v, T.heeftVeld, bewering))
        if veld == "waterlichaam" and aanwezig:
            graph.add((v, T.waterlichaam, Literal(waarde)))
    for veld in IDENTIFICERENDE_VELDEN:
        waarde = vestiging.get(veld)
        if waarde not in (None, "", []):
            graph.add((v, getattr(T, veld), Literal(waarde)))
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


def _signaal_triples(graph: Graph, vestiging_node, signaal: dict):
    """Eén `t:Signaal`-knooppunt aan een vestiging: de brug tussen de twee lezers.

    **Waarom de signalen in de graaf horen.** Zonder hen kan deze graaf wel zeggen welke
    grenswaarde aangenomen is, maar niet welke vergunning een open wasstraatbevinding heeft -- en
    de vraag die waarde heeft loopt juist over de twee lezers heen: "welke vergunningen hebben
    een papierbevinding én een meting boven de norm". Die vraag was onbeantwoordbaar zolang de
    bevindingen buiten de graaf bleven.

    **`laag` en `rol` worden hier afgeleid, niet overgenomen.** Een signaal-dict draagt ze niet
    (zie `signalen._signaal`), en ze opnieuw intypen zou een tweede lijst maken naast
    `_WERKELIJKHEID_REGELS` en `DREMPELS` -- precies wat dit project al eens duur heeft betaald.
    `laag` zegt op welke pagina de regel landt, `rol` of een papierregel een bevinding is of een
    voorbehoud; die twee zijn verschillende vragen en moeten dus apart te bevragen zijn."""
    sn = BNode()
    graph.add((sn, RDF.type, T.Signaal))
    graph.add((vestiging_node, T.heeftSignaal, sn))
    regel_id = signaal["regel"]
    graph.add((sn, T.regel, Literal(regel_id)))
    graph.add((sn, T.laag, Literal(signalen_mod._laag(regel_id))))
    graph.add((sn, T.rol, Literal(
        "voorbehoud" if signalen_mod.is_voorbehoud(regel_id) else "bevinding")))
    # Wat er bewust níet bij staat: de geformuleerde `bewering`. Die volzin maakt
    # `dossier._bewering` uit het signaal plus de vestiging, en hem hier opnemen zou de hele
    # dossierlaag deze module in trekken voor een stuk formulering -- precies wat de
    # moduledocstring hierboven al weigert te doen voor `dossier.dossier()`. De graaf bewaart de
    # feiten; de zin hoort bij de presentatie.
    for veld, sleutel in (("kop", "signaal"), ("zwaarte", "zwaarte"), ("omvang", "omvang")):
        waarde = signaal.get(sleutel)
        if waarde is not None:
            graph.add((sn, getattr(T, veld), Literal(waarde)))
    return sn


def overschrijdingen_triples(graph: Graph, overschrijdingen: list[dict] | None) -> None:
    """De al vastgestelde overschrijdingen als `t:Overschrijding`-knooppunten.

    **Waarom dit een eigen klasse is en geen query over Meting en Norm.** Die query is in rdflib
    onbruikbaar traag: 350 `t:Meting`-knopen tegen 6143 `t:Norm`-knopen is een nested loop van
    ruim twee miljoen combinaties, en live gemeten duurde zij **119 seconden** voor 21 rijen. Een
    gegenereerde query die dat probeert, laat de vraagweg minuten hangen -- en dat was precies de
    melding "de vraag werkt niet meer".

    De vergelijking hoeft ook niet in de query: `kmg.doelen` plus `toezicht.context.toetsing`
    hebben haar al gemaakt, mét de juiste sleutel (meetpunt **en** stof -- een KRW-norm geldt per
    meetpunt, zink is per punt gecorrigeerd voor biobeschikbaarheid). Haar hier vastleggen maakt
    de vraag "welke vergunning ligt aan een waterlichaam met een overschrijding" een opzoeking in
    plaats van een rekenpartij, en voorkomt dat het taalmodel die join zelf -- en dan op de
    verkeerde sleutel -- moet verzinnen."""
    for o in overschrijdingen or []:
        node = BNode()
        graph.add((node, RDF.type, T.Overschrijding))
        for veld, sleutel in (("meetpunt", "meetpunt"), ("waterlichaam", "waterlichaam"),
                               ("stof", "stof"), ("eenheid", "eenheid")):
            if o.get(sleutel) is not None:
                graph.add((node, getattr(T, veld), Literal(o[sleutel])))
        if o.get("gemeten") is not None:
            graph.add((node, T.gemeten, Literal(o["gemeten"])))
        if o.get("norm") is not None:
            graph.add((node, T.norm, Literal(o["norm"])))


def bouw(register: list[dict] | None, metingen: dict | None, normen: dict | None,
         aquo: dict | None, context=None) -> Graph:
    """Het register, de metingen, de normen en de Aquo-referentie als één bevraagbare graaf.

    `register` mag ongeverrijkt binnenkomen (zonder `aquo`-sleutel op de voorschriften) -- deze
    functie verrijkt elke vestiging zelf via `toezicht.aquo.verrijk`, met dezelfde referentie die
    zij meekrijgt. Is `aquo` niet beschikbaar, dan blijft een vestiging ongewijzigd (zie
    `verrijk()`) en komt er voor die vestiging geen Aquo-koppeling-bewering.

    **`context` schakelt de signalen in** (zie `_signaal_triples`) en mag een dict zijn of een
    functie `vestiging -> dict`; dat laatste omdat `waterlichaam` per vestiging verschilt. Laat je hem weg, dan draagt de
    graaf geen `t:Signaal` -- dat is de vorm die de oudere aanroepen kennen en die nodig blijft
    waar alleen de velden en metingen gevraagd worden. Geef je een leeg dict mee, dan komen de
    zeven papierregels erin maar de drie werkelijkheidsregels niet: die hebben meetdata of
    stroomrichting nodig en kunnen zonder context niet vuren. Dat is eerlijk afwezig in plaats van
    stil leeg, maar wie de brugvraag wil stellen moet de volle context meegeven -- dezelfde vijf
    sleutels die `api_toezicht_dossier` samenstelt."""
    graph = Graph()
    graph.bind("t", T)
    for vestiging in register or []:
        verrijkt = aquo_mod.verrijk(vestiging, aquo or {})
        # De context eerst: zij draagt het afgeleide waterlichaam, en dat hoort op het
        # vestigingsknooppunt zelf (zie `_vestiging_triples`) zodat een vraag van een vergunning
        # naar een meting kan lopen.
        eigen = None
        if context is not None:
            eigen = context(verrijkt) if callable(context) else context
        vn = _vestiging_triples(graph, verrijkt,
                                 waterlichaam=(eigen or {}).get("waterlichaam"))
        for voorschrift in verrijkt.get("voorschriften") or []:
            _voorschrift_triples(graph, vn, voorschrift)
        if eigen is not None:
            # `context` mag een dict zijn (dezelfde voor elke vestiging) of een functie
            # `vestiging -> dict`. Dat tweede is geen gemak maar noodzaak: `waterlichaam` is een
            # eigenschap van de vestiging zelf, opgezocht uit haar eigen coördinaat. Eén
            # waterlichaam aan het hele register toekennen zou
            # `regel_norm_overschreden_bovenstrooms` laten vuren met een richting die voor
            # vrijwel elke vergunning onjuist is -- de ergste fout die deze graaf kan maken.
            for signaal in signalen_mod.signalen(verrijkt, eigen):
                _signaal_triples(graph, vn, signaal)

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
