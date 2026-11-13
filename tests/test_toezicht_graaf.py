"""`toezicht.graaf` -- register, metingen, normen en de Aquo-referentie als RDF-triples.

Geen netwerk: `bouw()` werkt uitsluitend op wat hij als argument krijgt (fixtures hieronder),
net als `signalen.py` en `dossier.py` al afdwingen voor hun eigen input.
"""
import rdflib

from leefomgevinglab.ld import store
from leefomgevinglab.usecases.toezicht import graaf

T = graaf.T

REGISTER_FIXTURE = [
    {
        "naam": "Lozer BV", "kenmerk": "WL-2020-001", "besluitdatum": "2020-01-01",
        "waterlichaam": "NL91BM", "url": "https://example.org/vergunning.pdf",
        "voorschriften": [
            {"parameter": "Zink", "waarde": 0.5, "eenheid": "milligram per liter",
             "bemonstering": "Steekmonster"},
            {"parameter": "Onbekend sulfiet-mengsel", "waarde": 1.0,
             "eenheid": "milligram per liter"},
        ],
    },
    {
        # Geen kenmerk, geen url -- precies het geval dat signaal 8 (vergunning_niet_te_vinden)
        # bedoelt, en hier als "ontbreekt" bevraagbaar moet zijn.
        "naam": "Lozer zonder kenmerk", "voorschriften": [],
    },
]

AQUO_FIXTURE = {
    "beschikbaar": True,
    "geldig": {"zink": "Zn"},
    "vervallen": {"zwevende stof": "ZS"},
    "aantal": {"Geldig": 1, "Vervallen": 1},
    "bron": {"naam": "Aquo-domeintabel Parameter"},
    "gelezen_op": "2026-11-13",
    "reden": None,
}

METINGEN_FIXTURE = {
    "beschikbaar": True, "meetjaar": 2025,
    "bron": {"naam": "Waterkwaliteitsportaal"},
    "punten": [
        {"code": "NL91_TESTPUNT", "waterlichaam": "NL91BM", "stoffen": [
            {"code": "Zn", "naam": "zink", "mediaan": 4.5, "maximum": 9.0, "eenheid": "ug/l"},
        ]},
    ],
}

NORMEN_FIXTURE = {
    "beschikbaar": True, "bron": {"naam": "KRW-toetsresultaten"},
    "normen": {
        "NL91_TESTPUNT": [
            {"parameter": "Zn", "eenheid": "ug/l", "grondslag": "jaargemiddelde", "norm": 7.8},
        ],
    },
}


# -- Stap 3 van het takenbrief, verbatim -----------------------------------------------------

def test_een_aangenomen_grenswaarde_is_als_aanname_te_bevragen():
    g = graaf.bouw(REGISTER_FIXTURE, {}, {}, AQUO_FIXTURE)
    rijen = store.run_sparql(g, """
        PREFIX t: <https://leefomgevinglab.felixisfelix.com/toezicht#>
        SELECT ?v WHERE { ?v t:zekerheid "aangenomen" } LIMIT 50""")
    assert rijen, "zonder dit is de graaf niet meer dan een database"


# -- bouw(): register -------------------------------------------------------------------------

def test_bouw_zonder_enige_bron_geeft_een_lege_graaf():
    g = graaf.bouw(None, None, None, None)
    assert len(g) == 0


def test_elke_vestiging_wordt_een_t_vestiging_knooppunt():
    g = graaf.bouw(REGISTER_FIXTURE, {}, {}, {})
    assert len(list(g.subjects(rdflib.RDF.type, T.Vestiging))) == 2


def test_elk_voorschrift_wordt_een_t_voorschrift_gekoppeld_aan_zijn_vestiging():
    g = graaf.bouw(REGISTER_FIXTURE, {}, {}, {})
    assert len(list(g.subjects(rdflib.RDF.type, T.Voorschrift))) == 2
    for vestiging in g.subjects(rdflib.RDF.type, T.Vestiging):
        voorschriften = list(g.objects(vestiging, T.heeftVoorschrift))
        if list(g.objects(vestiging, T.heeftVeld)):
            # Twee vestigingen: één met twee voorschriften, één zonder.
            assert len(voorschriften) in (0, 2)


def test_een_rechtstreeks_atlasveld_staat_direct_op_het_voorschrift_zonder_bewering():
    """`parameter`/`waarde`/`eenheid`/`bemonstering` zijn altijd een directe lezing -- geen
    Bewering-omweg, zie de moduledocstring."""
    g = graaf.bouw(REGISTER_FIXTURE, {}, {}, {})
    namen = {str(n) for n in g.objects(None, T.parameter)}
    assert "Zink" in namen
    waarden = {float(w) for w in g.objects(None, T.waarde) if _is_grenswaarde(w)}
    assert 0.5 in waarden


def _is_grenswaarde(literal) -> bool:
    try:
        float(literal)
        return True
    except (TypeError, ValueError):
        return False


def test_een_ontbrekend_vestigingsveld_is_bevraagbaar_als_ontbreekt():
    g = graaf.bouw(REGISTER_FIXTURE, {}, {}, {})
    rijen = store.run_sparql(g, f"""
        PREFIX t: <{T}>
        SELECT ?veld WHERE {{
            ?v a t:Vestiging ; t:heeftVeld ?b .
            ?b t:veld ?veld ; t:zekerheid "ontbreekt" .
        }} LIMIT 200""")
    gevonden = {r["veld"] for r in rijen}
    assert "kenmerk" in gevonden and "url" in gevonden


def test_een_gevonden_aquo_code_draagt_zekerheid_afgeleid():
    g = graaf.bouw(REGISTER_FIXTURE, {}, {}, AQUO_FIXTURE)
    rijen = store.run_sparql(g, f"""
        PREFIX t: <{T}>
        SELECT ?code WHERE {{
            ?v a t:Voorschrift ; t:heeftAquoKoppeling ?b .
            ?b t:waarde ?code ; t:zekerheid "afgeleid" .
        }} LIMIT 50""")
    assert {r["code"] for r in rijen} == {"Zn"}


def test_een_niet_gevonden_naam_draagt_een_aquokoppeling_die_ontbreekt():
    """"Onbekend sulfiet-mengsel" staat in geen van beide Aquo-tabellen -- er is gezocht, maar
    niets gevonden; dat is een andere uitkomst dan "niet gezocht" (zie `aquo.verrijk`)."""
    g = graaf.bouw(REGISTER_FIXTURE, {}, {}, AQUO_FIXTURE)
    rijen = store.run_sparql(g, f"""
        PREFIX t: <{T}>
        SELECT ?b WHERE {{
            ?v a t:Voorschrift ; t:parameter "Onbekend sulfiet-mengsel" ;
               t:heeftAquoKoppeling ?b .
            ?b t:zekerheid "ontbreekt" .
        }} LIMIT 10""")
    assert rijen


def test_zonder_beschikbare_aquoreferentie_komt_er_geen_aquokoppeling_bewering():
    """Geen referentie beschikbaar betekent "niet gezocht", niet "niets gevonden" -- dus geen
    Bewering, zie `aquo.verrijk` en de moduledocstring van `toezicht.aquo`."""
    g = graaf.bouw(REGISTER_FIXTURE, {}, {}, {"beschikbaar": False})
    assert list(g.subjects(T.heeftAquoKoppeling, None)) == []


# -- bouw(): metingen en normen -----------------------------------------------------------------

def test_een_meting_is_altijd_uit_de_bron():
    g = graaf.bouw([], METINGEN_FIXTURE, {}, {})
    metingen = list(g.subjects(rdflib.RDF.type, T.Meting))
    assert len(metingen) == 1
    assert (metingen[0], T.zekerheid, rdflib.Literal(graaf.UIT_DE_BRON)) in g
    assert (metingen[0], T.mediaan, rdflib.Literal(4.5)) in g


def test_een_norm_is_altijd_uit_de_bron():
    g = graaf.bouw([], {}, NORMEN_FIXTURE, {})
    normen = list(g.subjects(rdflib.RDF.type, T.Norm))
    assert len(normen) == 1
    assert (normen[0], T.zekerheid, rdflib.Literal(graaf.UIT_DE_BRON)) in g
    assert (normen[0], T.waarde, rdflib.Literal(7.8)) in g


# -- stoffen_met_norm() -------------------------------------------------------------------------

def test_stoffen_met_norm_haalt_de_parametercodes_uit_de_normen():
    assert graaf.stoffen_met_norm(NORMEN_FIXTURE) == {"Zn"}


def test_stoffen_met_norm_zonder_normen_is_leeg():
    assert graaf.stoffen_met_norm({}) == set()
    assert graaf.stoffen_met_norm(None) == set()


# -- de graaf blijft bevraagbaar na een schijf-rondje (ld.store) -------------------------------

def test_de_graaf_overleeft_een_save_load_rondje_via_ld_store(tmp_path):
    g = graaf.bouw(REGISTER_FIXTURE, METINGEN_FIXTURE, NORMEN_FIXTURE, AQUO_FIXTURE)
    store.save_graph(g, str(tmp_path), naam="toezicht.ttl")
    g2 = store.load_graph(str(tmp_path), naam="toezicht.ttl")
    assert g2 is not None
    rijen = store.run_sparql(g2, f"""
        PREFIX t: <{T}>
        SELECT ?v WHERE {{ ?v t:zekerheid "aangenomen" }} LIMIT 50""")
    assert rijen
