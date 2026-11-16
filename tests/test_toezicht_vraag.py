"""`toezicht.vraag` -- de bewaakte vraagweg over de toezichtgraaf.

Geen netwerk: het taalmodel is overal geïnjecteerd (een gewone functie `str -> str`), dus een
gewone test roept het nooit aan. `valideer_sparql` komt als eerste aan de beurt (brief, stap 1)
-- dat is de bewaking, en die moet onafhankelijk van `stel()` kloppen.
"""
import pytest
import rdflib

from leefomgevinglab.usecases.toezicht import graaf, vraag

T = graaf.T


# -- Stap 1 van het takenbrief, verbatim -------------------------------------------------------

@pytest.mark.parametrize("q", [
    "INSERT DATA { <a> <b> <c> }",
    "DELETE WHERE { ?s ?p ?o }",
    "LOAD <http://elders/data.ttl>",
    "DROP GRAPH <g>",
    "SELECT * WHERE { ?s ?p ?o }",            # geen LIMIT
])
def test_de_validator_weigert_alles_wat_niet_leest(q):
    with pytest.raises(vraag.OngeldigeSparql):
        vraag.valideer_sparql(q)


def test_een_leesquery_met_limiet_mag():
    assert "LIMIT" in vraag.valideer_sparql("SELECT ?s WHERE { ?s ?p ?o } LIMIT 10")


# -- Extra aanvallen die de validator ook moet weigeren ----------------------------------------

@pytest.mark.parametrize("q", [
    # CONSTRUCT/DESCRIBE lezen ook, maar zijn geen vraag-met-rijen -- het plan noemt alleen
    # SELECT/ASK.
    "CONSTRUCT { ?s ?p ?o } WHERE { ?s ?p ?o } LIMIT 10",
    "DESCRIBE <http://example.org/x>",
    # Een tweede statement na een puntkomma (geen geldige SPARQL-leesquery meer -- de grammatica
    # van een Query staat geen vervolgstatement toe, alleen een Update-sequence doet dat).
    "SELECT * WHERE { ?s ?p ?o } LIMIT 10 ; INSERT DATA { <a> <b> <c> }",
    # WITH/USING: alleen geldig in een Update (DELETE/INSERT WHERE), nooit in een Query.
    "WITH <http://g> DELETE { ?s ?p ?o } WHERE { ?s ?p ?o }",
    # Mixed case ontwijkt de validator niet -- de SPARQL-grammatica is zelf al case-insensitief,
    # dus dit faalt om precies dezelfde reden als de kleine letters.
    "InSeRt DaTa { <a> <b> <c> }",
    "cLeAr GrAph <g>",
    # CREATE/COPY/MOVE/ADD: de rest van de Update-keywoorden die het plan noemt.
    "CREATE GRAPH <g>",
    "COPY <a> TO <b>",
    "MOVE <a> TO <b>",
    "ADD <a> TO <b>",
    # Een SERVICE-clause haalt een extern SPARQL-endpoint aan -- exact het netwerkpad dat dit lab
    # bewust niet bouwt (zie `graaf.py`). Geneste variant: binnen een subquery.
    "SELECT * WHERE { SERVICE <http://elders/sparql> { ?s ?p ?o } } LIMIT 10",
    "SELECT * WHERE { { SELECT * WHERE { SERVICE <http://elders/sparql> { ?s ?p ?o } } } } "
    "LIMIT 10",
    # FROM / FROM NAMED trekt een extern gepubliceerde graaf in de query -- dit lab bouwt geen
    # federatie (zie `graaf.py`), dus ook deze dataset-clause is uit.
    "SELECT * FROM <http://elders/graph> WHERE { ?s ?p ?o } LIMIT 10",
    # Lege of alleen-commentaar input.
    "",
    "   ",
    "# alleen een commentaarregel",
])
def test_de_validator_weigert_ook_deze_aanvallen(q):
    with pytest.raises(vraag.OngeldigeSparql):
        vraag.valideer_sparql(q)


def test_een_commentaar_dat_op_een_verboden_keyword_lijkt_is_onschadelijk():
    """Een commentaarregel wordt door de SPARQL-tokenizer weggegooid vóór er geparseerd wordt --
    hij kan dus geen keyword "activeren". Dit is het spiegelbeeld van de aanval die de validator
    wél moet weigeren (keyword ín de query, niet in een commentaar erbuiten)."""
    q = "SELECT * WHERE { ?s ?p ?o } # INSERT DATA { <a> <b> <c> }\nLIMIT 10"
    assert "LIMIT" in vraag.valideer_sparql(q)


def test_een_ask_query_zonder_limit_mag_wel():
    """ASK levert een boolean, geen rijenverzameling -- LIMIT is daar semantisch leeg en het plan
    eist hem alleen voor een SELECT. Dit is een eigen keuze van deze implementatie, geen letterlijk
    geëiste test uit het brief; zie het taakrapport."""
    assert vraag.valideer_sparql("ASK { ?s ?p ?o }") == "ASK { ?s ?p ?o }"


def test_een_te_groot_limiet_wordt_geweigerd_niet_teruggebracht():
    """Fix-ronde 1 (Important): een eerdere versie bracht een te grote LIMIT terug met een
    tekst-brede `re.sub`, en die trof ook stringliterals die op "limit <getal>" lijken (zie de
    volgende test). De geparste `limitoffset`-node draagt geen locatie om de herschrijving naar de
    echte clausule te richten, dus wordt een te grote LIMIT nu geweigerd -- net als een
    ontbrekende -- en genoemd in de boodschap."""
    with pytest.raises(vraag.OngeldigeSparql, match=str(vraag._MAX_LIMIT)):
        vraag.valideer_sparql("SELECT * WHERE { ?s ?p ?o } LIMIT 999999")


def test_een_limiet_boven_het_maximum_laat_een_stringliteral_dat_op_limit_lijkt_onaangeroerd():
    """De exacte reproductie uit fix-ronde 1 (Important): vóór de fix herschreef `re.sub` de hele
    querytekst, en trof daarmee ook het stringliteral `"limit 99999"` -- dat werd mee
    `"LIMIT 200"`, zodat de uitgevoerde query iets anders zocht dan wat de lezer op het scherm
    zag. Nu wordt de hele query in één keer geweigerd (zie de vorige test) in plaats van ergens
    herschreven te worden: er bestaat dus geen enkel pad meer waarop deze functie een string
    teruggeeft waarin dat literal is aangepast. Deze test legt dat vast door te bewijzen dat het
    enige wat gebeurt een `OngeldigeSparql` is, met de oorspronkelijke tekst nog volledig intact
    (geen enkele aanroep muteert `q` zelf, want Python-strings zijn immutable -- de garantie die
    hier telt is dat er geen teruggegeven, stilzwijgend herschreven waarde bestaat)."""
    q = 'SELECT ?s WHERE { ?s ?p "limit 99999" } LIMIT 999999'
    with pytest.raises(vraag.OngeldigeSparql, match=str(vraag._MAX_LIMIT)):
        resultaat = vraag.valideer_sparql(q)
        pytest.fail(f"had moeten weigeren, maar gaf terug: {resultaat!r}")
    assert q == 'SELECT ?s WHERE { ?s ?p "limit 99999" } LIMIT 999999'


def test_select_met_limiet_binnen_het_maximum_blijft_ongewijzigd():
    q = "SELECT ?s WHERE { ?s ?p ?o } LIMIT 10"
    assert vraag.valideer_sparql(q) == q


# -- stel(): de rondgang grounding -> genereren -> valideren -> uitvoeren ----------------------

def _graaf_met_een_aanname():
    return graaf.bouw(
        [{"naam": "Lozer BV", "kenmerk": "WL-1", "voorschriften": [
            {"parameter": "Zink", "waarde": 0.5, "eenheid": "milligram per liter"}]}],
        {}, {}, {})


def test_stel_voert_een_geldige_door_het_llm_gegenereerde_query_uit():
    g = _graaf_met_een_aanname()
    llm = lambda prompt: (  # noqa: E731 -- test-dubbel, geen productiecode
        "SELECT ?v WHERE { ?v <https://leefomgevinglab.felixisfelix.com/toezicht#zekerheid> "
        '"aangenomen" } LIMIT 10')
    uit = vraag.stel("welke grenswaarden zijn aangenomen?", g, llm)
    assert uit["beschikbaar"] is True
    assert uit["rijen"]
    assert "LIMIT" in uit["sparql"]
    assert uit["vraag"] == "welke grenswaarden zijn aangenomen?"


def test_stel_geeft_de_query_in_een_codeblok_ook_terug():
    g = _graaf_met_een_aanname()
    llm = lambda prompt: "```sparql\nSELECT ?s WHERE { ?s ?p ?o } LIMIT 5\n```"
    uit = vraag.stel("iets", g, llm)
    assert uit["beschikbaar"] is True
    assert "```" not in uit["sparql"]


def test_stel_valt_zacht_terug_als_het_llm_een_ongeldige_query_genereert():
    g = _graaf_met_een_aanname()
    llm = lambda prompt: "INSERT DATA { <a> <b> <c> }"
    uit = vraag.stel("iets ongeldigs", g, llm)
    assert uit["beschikbaar"] is False
    assert uit["rijen"] == []


def test_stel_valt_zacht_terug_als_het_llm_faalt():
    def llm(prompt):
        raise RuntimeError("llm onbereikbaar")
    g = _graaf_met_een_aanname()
    uit = vraag.stel("iets", g, llm)
    assert uit["beschikbaar"] is False


def test_stel_zonder_graaf_is_niet_beschikbaar():
    uit = vraag.stel("iets", None, lambda prompt: "SELECT * WHERE { ?s ?p ?o } LIMIT 10")
    assert uit["beschikbaar"] is False
    assert uit["rijen"] == []


# -- De grounding moet de graaf beschrijven die er werkelijk is ---------------------------------

def test_de_grounding_beschrijft_elke_klasse_die_de_graaf_bouwt():
    """**Waarom dit een test is en geen afspraak.** De grounding is het enige wat het taalmodel
    van de graaf weet. Staat er een klasse in de graaf die de grounding niet noemt, dan bestaat
    zij wel maar is zij onvindbaar -- het model kan er geen query op maken, en de gebruiker krijgt
    "geen resultaten" op een vraag die prima te beantwoorden was. Dat is het stilste soort fout
    dat deze use-case kent, en precies de reden dat de signalen in de graaf gezet zijn.

    De lijst klassen wordt uit de gebouwde graaf gehaald, niet hier opgesomd: komt er een zesde
    klasse bij, dan valt deze test om in plaats van de grounding stil achter te laten."""
    from leefomgevinglab.usecases.toezicht import graaf as graaf_mod
    from tests.test_toezicht_graaf import AQUO_FIXTURE, REGISTER_FIXTURE, _CONTEXT

    g = graaf_mod.bouw(REGISTER_FIXTURE, None, None, AQUO_FIXTURE, context=_CONTEXT)
    klassen = {str(o).rsplit("#", 1)[-1]
               for o in g.objects(predicate=rdflib.RDF.type)}
    assert klassen, "lege graaf -- deze test kan niets toetsen"
    for klasse in sorted(klassen):
        assert klasse in vraag.GROUNDING, (
            f"de graaf bouwt t:{klasse}, maar de grounding noemt die klasse niet -- het "
            "taalmodel kan er dus geen query op maken en de gebruiker krijgt 'geen resultaten' "
            "op een vraag die te beantwoorden was")


def test_de_grounding_noemt_de_twee_assen_van_een_signaal():
    """`laag` en `rol` zijn wat een brugvraag mogelijk maakt ("papierbevinding én meting boven de
    norm"). Noemt de grounding ze niet, dan is de brug er maar onbelopen."""
    for veld in ("t:laag", "t:rol"):
        assert veld in vraag.GROUNDING, veld
    assert "papier" in vraag.GROUNDING and "werkelijkheid" in vraag.GROUNDING
    assert "bevinding" in vraag.GROUNDING and "voorbehoud" in vraag.GROUNDING


# -- De factory die het injectiecontract invult voor echt gebruik -------------------------------

def test_taalmodel_levert_een_aanroepbare_functie_zonder_meteen_te_bellen():
    """Het bouwen van de functie mag geen netwerk raken -- anders kan geen enkele route haar
    aanmaken zonder het model te wekken."""
    fn = vraag.taalmodel("http://localhost:9/v1", "test-model", timeout_s=0.01)
    assert callable(fn)


def test_een_onbereikbaar_model_laat_stel_netjes_antwoorden_in_plaats_van_te_crashen():
    """`stel()` moet een onbereikbaar model als "AI tijdelijk niet beschikbaar" melden. Een lege
    string teruggeven zou van een netwerkfout een lege query maken, en dat leest als "deze vraag
    kon niet veilig worden vertaald" -- de verkeerde diagnose."""
    g = graaf.bouw([], None, None, None)
    fn = vraag.taalmodel("http://127.0.0.1:1/v1", "test-model", timeout_s=0.05)
    uit = vraag.stel("wat dan ook", g, fn)
    assert uit["beschikbaar"] is False
    assert "niet beschikbaar" in uit["antwoord"].lower()
    assert uit["sparql"] is None
    assert uit["rijen"] == []


def test_de_grounding_wijst_het_model_naar_de_leesbare_ingang():
    """Live bewees dit zijn nut: zonder deze aanwijzing selecteerde het model het
    vestigingsknooppunt en kreeg de gebruiker 100 blank-node-id's te zien. De grounding noemt nu
    expliciet welke velden leesbaar zijn en dat het knooppunt zelf dat niet is."""
    assert "t:naam" in vraag.GROUNDING
    laag = vraag.GROUNDING.lower()
    assert "blank node" in laag, "zeg waarom het knooppunt zelf niet bruikbaar is"
    assert "distinct" in laag, (
        "zonder DISTINCT levert een dubbel pad het kruisproduct op, en dan zegt het aantal rijen "
        "niets over het aantal vergunningen -- live gezien: 100 rijen over 69 vergunningen")


# -- De voorbeelden in de grounding zijn uitvoerbare documentatie -------------------------------

@pytest.mark.parametrize("beschrijving,query",
                          [(v[:40], q) for v, q in vraag.VOORBEELDEN])
def test_elk_voorbeeld_in_de_grounding_komt_langs_de_validator(beschrijving, query):
    """Een voorbeeld dat de validator zelf zou weigeren, onderwijst het model een patroon dat
    nooit uitgevoerd wordt -- en de lezer krijgt dan "kon niet veilig worden vertaald" op een
    vraag die wij hem hebben voorgedaan."""
    assert vraag.valideer_sparql(query) == query.strip()


def test_de_voorbeelden_staan_ook_echt_in_de_grounding():
    """Een lijst die niet in het prompt belandt, helpt het model niet."""
    for v, q in vraag.VOORBEELDEN:
        assert v in vraag.GROUNDING, v
        assert q.splitlines()[0] in vraag.GROUNDING, v


def test_de_grounding_waarschuwt_tegen_de_twee_fouten_die_het_model_echt_maakte():
    """Beide live gezien, beide met "Geen resultaten" als uitkomst -- wat leest als "er is niets
    aan de hand" in plaats van "de vraag is verkeerd gesteld":

    * `?vestiging t:heeftMeting ?meting` -- een predicaat dat niet bestaat. Een vergunning hangt
      aan een meting via het waterlichaam, en vóór deze ronde had de vestiging dat veld niet eens.
    * `FILTER(!BOUND(?kenmerk))` op een variabele die een triple pattern al bond: per definitie
      leeg. Afwezigheid is in deze graaf een positief feit (`t:zekerheid "ontbreekt"`).
    """
    g = vraag.GROUNDING
    assert "GEEN t:heeftMeting" in g
    assert "t:waterlichaam ?wl" in g, "zeg hóe je dan koppelt, niet alleen wat niet bestaat"
    assert "FILTER(!BOUND" in g and "nooit" in g.lower()
    assert 't:zekerheid "ontbreekt"' in g


# -- De deadline op de uitvoering ---------------------------------------------------------------

def test_een_te_zware_query_geeft_een_eigen_boodschap_in_plaats_van_te_blijven_hangen():
    """**`LIMIT` begrenst de uitvoer, niet het werk.** Dat verschil kostte deze use-case de
    melding "de vraag werkt niet meer": een geldige query met `LIMIT 100` liep in rdflib 119
    seconden. De boodschap is bewust een andere dan "kon niet worden uitgevoerd" -- die zou
    suggereren dat de query fout was, terwijl zij juist goed was en alleen te zwaar. En de query
    blijft zichtbaar, zodat te zien is wát er te zwaar was."""
    import time as _t

    g = graaf.bouw([], None, None, None)
    traag = f"SELECT ?s WHERE {{ ?s ?p ?o }} LIMIT 10"
    monkey = vraag.QUERY_DEADLINE_S
    try:
        vraag.QUERY_DEADLINE_S = 0.05
        # Een "graaf" waarvan het uitvoeren opzettelijk lang duurt.
        class Traag:
            def query(self, *a, **k):
                _t.sleep(5)
                return []
        uit = vraag.stel("wat dan ook", Traag(), lambda p: traag)
    finally:
        vraag.QUERY_DEADLINE_S = monkey
    assert uit["beschikbaar"] is False
    assert uit["te_zwaar"] is True
    assert uit["sparql"] == traag, "de query hoort zichtbaar te blijven"
    assert "niet binnen" in uit["antwoord"]
    assert "smaller" in uit["antwoord"], "zeg wat de lezer eraan kan doen"


def test_de_deadline_laat_een_normale_query_ongemoeid():
    g = graaf.bouw([], None, None, None)
    uit = vraag.stel("x", g, lambda p: "SELECT ?s WHERE { ?s ?p ?o } LIMIT 10")
    assert uit["beschikbaar"] is True
    assert "te_zwaar" not in uit
