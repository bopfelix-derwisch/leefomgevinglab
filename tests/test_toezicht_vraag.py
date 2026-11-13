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


def test_een_te_groot_limiet_wordt_teruggebracht():
    q = vraag.valideer_sparql("SELECT * WHERE { ?s ?p ?o } LIMIT 999999")
    assert "LIMIT 200" in q
    assert "999999" not in q


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
