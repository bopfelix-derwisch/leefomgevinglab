"""De kennisgraaf van het dossier: bronnen, bevindingen, thema's, blokjes en verbanden als RDF.

**Waarom hier een graaf bij een lijst van 42 bevindingen.** Niet om de lijst op te slaan -- dat
doet `bevindingen.py` beter. De winst zit in één eigenschap die een tabel niet heeft: **elke
bewering draagt wie haar doet**. Een bevinding komt uit een document (`k:van "bron"`), een thema
en een verband zijn een lezing van dit lab (`k:van "lab"`). Daarmee is "geef me alleen wat de
rapporten zelf zeggen" een gewone SPARQL-vraag in plaats van een discipline bij het lezen van de
pagina. Dat is dezelfde keuze als in `toezicht/graaf.py`, waar `zekerheid` per bewering
meegevoerd wordt in plaats van per kolom.

De tweede winst is dat de interessante vragen van dit dossier **joins over bronnen** zijn, en
daar is een graaf het natuurlijke gereedschap voor:

- Welk blokje van het eindbeeld draagt bevindingen uit de meeste verschillende rapporten?
- Welke aanbeveling van de Evaluatiecommissie heeft in de kabinetsreactie geen tegenhanger?
- Welke thema's draagt dit lab een eigen meting bij, en welke niet?

`VRAGEN` draagt die drie als uitvoerbare queries, zodat de pagina ze kan tonen mét hun uitkomst
in plaats van ze te beloven.

**Het verband is een knooppunt, geen triple.** `rli-overzicht bevestigt ec-confetti` zou als één
triple kunnen, maar dan kan er geen toelichting bij en is niet vast te leggen dat de relatie van
dit lab is en de twee bevindingen van hun bronnen. Een `k:Verband`-knooppunt met `k:van`,
`k:naar`, `k:relatie`, `k:toelichting` en `k:van` (de herkomst) houdt die drie dingen apart.
"""
from rdflib import Graph, Literal, Namespace, RDF, RDFS, XSD

from leefomgevinglab.kennisbasis import bevindingen as bevindingen_mod
from leefomgevinglab.kennisbasis import bronnen as bronnen_mod

#: Het namespace van de kennisbasis.
K = Namespace("https://leefomgevinglab.felixisfelix.com/kennisbasis#")

#: De twee herkomsten. Dezelfde twee woorden als `HERKOMST` in `bevindingen.py` en als de
#: herkomsttabel op `/maquette` -- één vocabulaire voor het hele lab.
BRON, LAB = "bron", "lab"


def _uri(soort: str, sleutel: str):
    return K[f"{soort}/{sleutel}"]


def bouw() -> Graph:
    """De hele kennisbasis als graaf. Raakt geen netwerk en geen bron -- alles komt uit
    `bevindingen.py` en `bronnen.py`, dus dit is reproduceerbaar en snel."""
    g = Graph()
    g.bind("k", K)

    for b in bronnen_mod.BRONNEN:
        s = _uri("bron", b["id"])
        g.add((s, RDF.type, K.Bron))
        g.add((s, RDFS.label, Literal(b["titel"])))
        g.add((s, K.uitgever, Literal(b["uitgever"])))
        g.add((s, K.soort, Literal(b["soort"])))
        g.add((s, K.datum, Literal(b["datum"], datatype=XSD.date)))
        g.add((s, K.kenmerk, Literal(b["kenmerk"])))
        g.add((s, K.url, Literal(b["url"])))
        g.add((s, K.van, Literal(BRON)))
        paginas = bronnen_mod.paginas(b)
        if paginas:
            g.add((s, K.paginas, Literal(paginas, datatype=XSD.integer)))

    for t in bevindingen_mod.THEMAS:
        s = _uri("thema", t["id"])
        g.add((s, RDF.type, K.Thema))
        g.add((s, RDFS.label, Literal(t["naam"])))
        g.add((s, K.vraag, Literal(t["vraag"])))
        # Het thema is een indeling van dit lab; de rapporten kennen haar niet.
        g.add((s, K.van, Literal(LAB)))
        g.add((s, K.blokje, _uri("blokje", t["blokje"])))

    for b in bevindingen_mod.bevindingen():
        s = _uri("bevinding", b["id"])
        g.add((s, RDF.type, K.Bevinding))
        g.add((s, RDFS.label, Literal(b["kop"])))
        g.add((s, K.uitBron, _uri("bron", b["bron"])))
        g.add((s, K.soort, Literal(b["soort"])))
        g.add((s, K.citaat, Literal(b["citaat"])))
        g.add((s, K.pagina, Literal(b["pagina"], datatype=XSD.integer)))
        g.add((s, K.adressant, Literal(b["adressant"])))
        # De bevinding zelf staat in het document; haar plaatsing in een thema en bij een blokje
        # is een lezing van dit lab. Daarom twee verschillende predicaten met elk hun herkomst.
        g.add((s, K.van, Literal(BRON)))
        g.add((s, K.inThema, _uri("thema", b["thema"])))
        g.add((s, K.overBlokje, _uri("blokje", b["blokje"])))

        blok = _uri("blokje", b["blokje"])
        g.add((blok, RDF.type, K.Blokje))
        g.add((blok, RDFS.label, Literal(b["blokje_naam"])))
        g.add((blok, K.route, Literal(b["waar"])))
        if b.get("blokje_laag"):
            g.add((blok, K.laag, Literal(b["blokje_laag"])))

    for v in bevindingen_mod.verbanden():
        s = _uri("verband", f"{v['van']}--{v['naar']}")
        g.add((s, RDF.type, K.Verband))
        g.add((s, K.vanBevinding, _uri("bevinding", v["van"])))
        g.add((s, K.naarBevinding, _uri("bevinding", v["naar"])))
        g.add((s, K.relatie, Literal(v["relatie"])))
        g.add((s, K.toelichting, Literal(v["wat"])))
        g.add((s, K.van, Literal(LAB)))

    for i, l in enumerate(bevindingen_mod.LABLIJN):
        s = _uri("labmeting", str(i))
        g.add((s, RDF.type, K.Labmeting))
        g.add((s, RDFS.label, Literal(l["wat"])))
        g.add((s, K.inThema, _uri("thema", l["thema"])))
        g.add((s, K.route, Literal(l["waar"])))
        g.add((s, K.hoe, Literal(l["hoe"])))
        g.add((s, K.van, Literal(LAB)))

    return g


#: Drie vragen die de lijst niet kan beantwoorden maar de graaf wel, elk met de reden dat zij er
#: staat. De pagina voert ze uit en toont de uitkomst -- een belofte zonder uitkomst is geen
#: bevraagbare laag.
VRAGEN = [
    {
        "id": "blokjes_meeste_bronnen",
        "vraag": "Welke plek in het eindbeeld wordt door de meeste rapporten geraakt?",
        "waarom": "Een blokje waar drie of vier onafhankelijke rapporten iets over zeggen, is "
                  "geen mening meer.",
        "sparql": """
            PREFIX k: <https://leefomgevinglab.felixisfelix.com/kennisbasis#>
            PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
            SELECT ?blokje ?naam (COUNT(DISTINCT ?bron) AS ?bronnen)
                   (COUNT(DISTINCT ?bevinding) AS ?bevindingen)
            WHERE {
              ?bevinding a k:Bevinding ;
                         k:overBlokje ?blokje ;
                         k:uitBron ?bron .
              ?blokje rdfs:label ?naam .
            }
            GROUP BY ?blokje ?naam
            ORDER BY DESC(?bronnen) DESC(?bevindingen)
            LIMIT 10
        """,
    },
    {
        "id": "aanbevelingen_zonder_reactie",
        "vraag": "Op welke thema's doet een rapport een aanbeveling waar de kabinetsreactie "
                 "niets tegenover zet?",
        "waarom": "Dit is de vraag waarvoor het dossier de kabinetsreactie binnenhaalde. Een "
                  "aanbeveling zonder reactie is geen fout van het kabinet -- de reactie gaat "
                  "alleen over het reflectierapport -- maar wel een open eind in dit dossier.",
        "sparql": """
            PREFIX k: <https://leefomgevinglab.felixisfelix.com/kennisbasis#>
            PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
            SELECT ?thema ?naam (COUNT(DISTINCT ?aanbeveling) AS ?aanbevelingen)
            WHERE {
              ?aanbeveling a k:Bevinding ;
                           k:soort "aanbeveling" ;
                           k:inThema ?thema .
              ?thema rdfs:label ?naam .
              FILTER NOT EXISTS {
                ?reactie k:soort "reactie" ; k:inThema ?thema .
              }
            }
            GROUP BY ?thema ?naam
            ORDER BY DESC(?aanbevelingen)
            LIMIT 10
        """,
    },
    {
        "id": "alleen_de_bronnen",
        "vraag": "Hoeveel van de graaf komt uit de documenten, en hoeveel is een lezing van dit "
                 "lab?",
        "waarom": "De eigenschap waarvoor hier een graaf staat. Zonder `k:van` per knooppunt is "
                  "dit onderscheid alleen met de hand te maken.",
        "sparql": """
            PREFIX k: <https://leefomgevinglab.felixisfelix.com/kennisbasis#>
            SELECT ?van ?soort (COUNT(?s) AS ?aantal)
            WHERE {
              ?s k:van ?van ; a ?soort .
            }
            GROUP BY ?van ?soort
            ORDER BY ?van DESC(?aantal)
            LIMIT 20
        """,
    },
]


def stel(graaf: Graph, vraag_id: str) -> list[dict]:
    """Eén van de `VRAGEN` uitvoeren. Een onbekende id valt luid om in plaats van een lege lijst
    terug te geven -- een stil leeg antwoord leest als 'er is niets', en dat is iets anders dan
    'die vraag bestaat niet'."""
    vraag = next((v for v in VRAGEN if v["id"] == vraag_id), None)
    if vraag is None:
        raise KeyError(f"onbekende vraag: {vraag_id}")
    res = graaf.query(vraag["sparql"])
    return [{str(var): (str(row[var]) if row[var] is not None else None) for var in res.vars}
            for row in res]


def uitslagen(graaf: Graph) -> list[dict]:
    """Alle vragen met hun uitkomst, voor de pagina."""
    return [{**{k: v for k, v in vraag.items() if k != "sparql"},
             "sparql": " ".join(vraag["sparql"].split()),
             "rijen": stel(graaf, vraag["id"])}
            for vraag in VRAGEN]


def telling(graaf: Graph) -> dict:
    """Wat er in de graaf staat, geteld uit de graaf zelf."""
    def tel(klasse):
        return len(set(graaf.subjects(RDF.type, klasse)))
    return {
        "triples": len(graaf),
        "bronnen": tel(K.Bron),
        "bevindingen": tel(K.Bevinding),
        "themas": tel(K.Thema),
        "blokjes": tel(K.Blokje),
        "verbanden": tel(K.Verband),
        "labmetingen": tel(K.Labmeting),
    }
