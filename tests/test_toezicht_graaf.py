"""`toezicht.graaf` -- register, metingen, normen en de Aquo-referentie als RDF-triples.

Geen netwerk: `bouw()` werkt uitsluitend op wat hij als argument krijgt (fixtures hieronder),
net als `signalen.py` en `dossier.py` al afdwingen voor hun eigen input.
"""
import rdflib

from leefomgevinglab.ld import store
from leefomgevinglab.usecases.toezicht import graaf, signalen

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


# -- De signalen in de graaf: de brug tussen de twee lezers --------------------------------------
#
# Een context die de drie werkelijkheidsregels laat vuren op `REGISTER_FIXTURE`: zink is vergund,
# wordt gemeten en overschrijdt benedenstrooms, en er is een gemeten stof zonder voorschrift.
_CONTEXT = {
    "stoffen_met_norm": {"Zn"},
    "gemeten_codes": {"Zn"},
    "waterlichaam": "NL91BM",
    "overschrijdingen": [{"meetpunt": "NL91_TESTPUNT", "waterlichaam": "NL91BM", "stof": "Zn",
                           "gemeten": 9.0, "norm": 7.8, "eenheid": "ug/l"}],
    "register_codes": {"Zn"},
}

def _rijen(g, waar: str):
    from leefomgevinglab.ld.store import run_sparql
    return run_sparql(g, f"PREFIX t: <{graaf.T}>\nSELECT * WHERE {{ {waar} }} LIMIT 200")


def test_de_graaf_draagt_de_signalen_per_vestiging():
    """**Waarom dit erin moet.** Zonder de signalen kan de graaf wel zeggen welke grenswaarde
    aangenomen is, maar niet welke vergunning een open wasstraatbevinding heeft. De vraag die
    waarde heeft loopt juist over de twee lezers heen -- "welke vergunningen hebben een
    papierbevinding én een meting boven de norm" -- en die is onbeantwoordbaar zolang de
    bevindingen buiten de graaf blijven."""
    g = graaf.bouw(REGISTER_FIXTURE, None, None, AQUO_FIXTURE, context={})
    rijen = _rijen(g, "?v a t:Vestiging ; t:heeftSignaal ?s . ?s t:regel ?regel")
    assert rijen, "geen enkel signaal in de graaf"
    assert {str(r["regel"]) for r in rijen}, "de regel-id hoort op het signaalknooppunt"


def test_elk_signaal_draagt_zijn_laag_en_zijn_rol():
    """De twee assen moeten in de graaf te bevragen zijn, anders kan een vraag niet onderscheiden
    tussen "wat moet recht" en "waar moet ik kijken" -- en dan is de brug er alleen in naam.
    Afgeleid uit `signalen`, niet hier opnieuw getypt."""
    g = graaf.bouw(REGISTER_FIXTURE, None, None, AQUO_FIXTURE, context={})
    rijen = _rijen(g, "?s a t:Signaal ; t:regel ?regel ; t:laag ?laag ; t:rol ?rol")
    assert rijen
    lagen = {r.id: r.laag for r in signalen.REGELS}
    for r in rijen:
        regel = str(r["regel"])
        assert str(r["laag"]) == lagen[regel], regel
        verwacht = "voorbehoud" if signalen.is_voorbehoud(regel) else "bevinding"
        assert str(r["rol"]) == verwacht, regel


def test_een_signaal_draagt_zijn_kop_zwaarte_en_omvang():
    """**Wat er bewust NIET in staat: de bewering.** Dat is de volzin met het getal erin ("...
    draagt meer dan één grenswaarde, met een factor 62,5x verschil"), en die wordt pas door
    `dossier._bewering` gemaakt uit het signaal plus de vestiging. Hem hier opnemen zou de hele
    dossierlaag in deze module trekken voor een geformuleerde zin -- precies wat de
    moduledocstring van `graaf.py` al weigert te doen voor `dossier.dossier()`. De graaf bewaart
    de feiten (regel, laag, rol, kop, zwaarte, omvang); de formulering hoort bij de presentatie.
    Een antwoord uit de chatbox noemt dus regel en omvang, en voor de volzin is er het dossier."""
    g = graaf.bouw(REGISTER_FIXTURE, None, None, AQUO_FIXTURE, context={})
    rijen = _rijen(g, "?s a t:Signaal ; t:kop ?kop ; t:zwaarte ?zw ; t:omvang ?om")
    assert rijen, "zonder deze velden is een signaal in de graaf niet te wegen of te lezen"
    for r in rijen:
        assert str(r["zw"]) in ("hoog", "midden", "laag")
        assert str(r["kop"]).strip()
    assert not _rijen(g, "?s a t:Signaal ; t:bewering ?be"), (
        "de geformuleerde bewering hoort niet in de graaf -- zie de docstring hierboven")


def test_zonder_context_komen_alleen_de_papiersignalen_in_de_graaf():
    """Eerlijk afwezig in plaats van stil leeg: de drie werkelijkheidsregels hebben meetdata of
    stroomrichting nodig, dus zonder context kunnen ze niet vuren. Dat is geen fout van de graaf,
    maar het mag ook niet lijken alsof die vergunning geen meetkant heeft."""
    g = graaf.bouw(REGISTER_FIXTURE, None, None, AQUO_FIXTURE, context={})
    lagen = {str(r["laag"]) for r in _rijen(g, "?s a t:Signaal ; t:laag ?laag")}
    assert lagen == {"papier"}, f"onverwachte lagen zonder context: {lagen}"


def test_context_doorgeven_levert_ook_de_werkelijkheidssignalen():
    g = graaf.bouw(REGISTER_FIXTURE, None, None, AQUO_FIXTURE, context=_CONTEXT)
    lagen = {str(r["laag"]) for r in _rijen(g, "?s a t:Signaal ; t:laag ?laag")}
    assert "werkelijkheid" in lagen, (
        "met een volledige context horen de drie meetregels mee in de graaf -- anders kan de "
        "brugvraag nooit beide kanten raken")


def test_zonder_context_argument_blijft_de_graaf_werken_zoals_voorheen():
    """`bouw()` wordt ook aangeroepen zonder signalen (de oudere aanroepen, en `stoffen_met_norm`
    heeft ze niet nodig). Een ontbrekend `context`-argument mag dus geen signalen opleveren en al
    helemaal niet crashen."""
    g = graaf.bouw(REGISTER_FIXTURE, None, None, AQUO_FIXTURE)
    assert not _rijen(g, "?s a t:Signaal")


def test_de_brugvraag_is_een_gewone_sparql_query():
    """De vraag waar het Bob om gaat, als query: welke vestigingen dragen zowel een
    papierbevinding als een werkelijkheidssignaal? Dit is de test die bewijst dat de brug niet
    alleen bestaat maar ook te belopen is."""
    from leefomgevinglab.ld.store import run_sparql
    g = graaf.bouw(REGISTER_FIXTURE, None, None, AQUO_FIXTURE, context=_CONTEXT)
    rijen = run_sparql(g, f"""
        PREFIX t: <{graaf.T}>
        SELECT ?naam WHERE {{
          ?v a t:Vestiging ; t:heeftVeld ?nv ; t:heeftSignaal ?p ; t:heeftSignaal ?w .
          ?nv t:veld "naam" ; t:waarde ?naam .
          ?p t:laag "papier" ; t:rol "bevinding" .
          ?w t:laag "werkelijkheid" .
        }} LIMIT 50""")
    assert rijen, "de brugvraag levert niets -- dan is de koppeling er niet echt"


def test_context_mag_ook_een_functie_per_vestiging_zijn():
    """**Waarom dit nodig is.** `context["waterlichaam"]` is een eigenschap van de vestiging zelf,
    niet van het register: elke vergunning ligt aan haar eigen waterlichaam, opgezocht uit haar
    eigen coördinaat. Eén context voor alle vestigingen zou dus óf één waterlichaam aan alle 69
    toekennen, óf het veld leeg laten -- en in het eerste geval zou
    `norm_overschreden_bovenstrooms` op het hele register vuren met een richting die voor vrijwel
    elke vergunning onjuist is. Dat is de ergste fout die deze graaf kan maken, dus mag `context`
    ook een functie zijn die per vestiging het juiste dict geeft."""
    gezien = []

    def context_voor(vestiging):
        gezien.append(vestiging.get("naam"))
        return {**_CONTEXT, "waterlichaam": vestiging.get("waterlichaam")}

    g = graaf.bouw(REGISTER_FIXTURE, None, None, AQUO_FIXTURE, context=context_voor)
    assert gezien == [v["naam"] for v in REGISTER_FIXTURE], (
        "de functie hoort precies één keer per vestiging aangeroepen te worden")
    assert _rijen(g, "?s a t:Signaal")


def test_een_vestiging_draagt_haar_naam_ook_als_gewone_literal():
    """**Gevonden door de draaiende dienst te bevragen, niet door de code te lezen.** Het model
    schreef een correcte brugvraag en selecteerde `?vestiging` -- en kreeg 100 rijen met
    blank-node-id's (`Na5f43702f94c...`) terug. Onbruikbaar voor een mens.

    De naam stond alleen achter `t:heeftVeld` -> Bewering -> `t:waarde`: drie stappen diep, met
    een filter op `t:veld "naam"`. Dat is prima voor een vraag over zekerheid, maar het is een
    val voor elke vraag die gewoon wil weten *welke* vergunning het is -- en dat is de meeste.
    De identificerende velden staan daarom nu óók als gewone literal op de vestiging. De
    Bewering blijft bestaan: die draagt de zekerheid, en dat is een ander verhaal."""
    g = graaf.bouw(REGISTER_FIXTURE, None, None, AQUO_FIXTURE)
    rijen = _rijen(g, "?v a t:Vestiging ; t:naam ?naam")
    namen = {str(r["naam"]) for r in rijen}
    assert namen == {v["naam"] for v in REGISTER_FIXTURE}, namen


def test_de_brugvraag_levert_leesbare_namen_in_plaats_van_knooppunten():
    """Dezelfde query die het model live schreef, maar nu met `t:naam` erbij: een mens kan het
    antwoord lezen."""
    from leefomgevinglab.ld.store import run_sparql
    g = graaf.bouw(REGISTER_FIXTURE, None, None, AQUO_FIXTURE, context=_CONTEXT)
    rijen = run_sparql(g, f"""
        PREFIX t: <{graaf.T}>
        SELECT DISTINCT ?naam WHERE {{
          ?v a t:Vestiging ; t:naam ?naam ; t:heeftSignaal ?p, ?w .
          ?p t:laag "papier" ; t:rol "bevinding" .
          ?w t:laag "werkelijkheid" .
        }} LIMIT 50""")
    assert rijen
    for r in rijen:
        assert not str(r["naam"]).startswith("N"), "nog steeds een knooppunt-id"
        assert str(r["naam"]) in {v["naam"] for v in REGISTER_FIXTURE}


def test_de_identificerende_velden_staan_direct_op_de_vestiging():
    """Niet alleen de naam: wie een vergunning wil terugvinden heeft haar kenmerk of locatiecode
    nodig. Een vestiging zonder zo'n veld draagt het niet -- afwezig blijft afwezig."""
    g = graaf.bouw(REGISTER_FIXTURE, None, None, AQUO_FIXTURE)
    rijen = _rijen(g, '?v a t:Vestiging ; t:naam ?naam . OPTIONAL { ?v t:kenmerk ?k }')
    per_naam = {str(r["naam"]): (str(r["k"]) if r["k"] is not None else None) for r in rijen}
    assert per_naam["Lozer BV"] == "WL-2020-001"
    assert per_naam["Lozer zonder kenmerk"] is None
