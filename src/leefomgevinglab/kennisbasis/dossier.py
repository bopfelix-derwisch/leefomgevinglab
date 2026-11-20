"""Het dossier als geheel: wat de kennisbasis is, wat erin zit, en hoe betrouwbaar dat is.

**De enige plek waar staat wat dit dossier is.** Dezelfde regel als `usecases/water_hub.py`: de
pagina haalt haar inhoudsopgave hier op in plaats van haar zelf te dragen, zodat lidmaatschap op
één plek staat en niet uit de pas kan lopen.

**Waarom de betrouwbaarheid van de eigen pagina erbij staat.** Dit is een kennisbasis over vier
rapporten die alle vier over hetzelfde onderwerp zeggen: niemand weet precies wat er is. Een
pagina die dat onderwerp behandelt en zelf niet zegt waar haar getallen op rusten, doet precies
waar de rapporten over klagen. `gezondheid()` meldt daarom of elk citaat op zijn pagina staat, of
de documenten op schijf staan en of de index gebouwd is -- niet in een logregel maar in het
antwoord van de API, zodat het op de pagina terechtkomt.
"""
from leefomgevinglab.kennisbasis import bevindingen as bevindingen_mod
from leefomgevinglab.kennisbasis import bronnen as bronnen_mod
from leefomgevinglab.kennisbasis import graaf as graaf_mod
from leefomgevinglab.kennisbasis import index as index_mod
from leefomgevinglab.kennisbasis import vindplaats as vindplaats_mod

#: Het dossier. Eén onderwerp, bewust klein gehouden: dit is de eerste van wat meer dossiers
#: kunnen worden, en een kennisbasis met één goed dossier is meer waard dan vijf halve.
DOSSIER = {
    "id": "bevindingen-vth",
    "naam": "Bevindingen VTH",
    "ondertitel": "Wat vier rapporten in 2026 vaststelden over vergunningverlening, toezicht en "
                  "handhaving onder de Omgevingswet",
    "vraag": "Waarom weet niemand precies welke vergunningen gelden, en wat betekent dat?",
    "status": "eerste MVP",
}

#: Waarvoor deze kennisbasis gebouwd is, en waarvoor niet. Hoort op de pagina: een instrument dat
#: zijn eigen grens niet noemt, wordt gebruikt buiten die grens.
GESCHIKT = [
    {"ja": True, "wat": "Nalezen wat een rapport letterlijk zegt, met de pagina erbij"},
    {"ja": True, "wat": "Zien waar vier rapporten hetzelfde zeggen, en waar ze elkaar aanvullen"},
    {"ja": True, "wat": "Een passage zoeken in 740 chunks over vier documenten"},
    {"ja": False, "wat": "Een volledig beeld van het VTH-stelsel -- dit zijn vier rapporten, "
                         "geen literatuuroverzicht"},
    {"ja": False, "wat": "Een juridisch oordeel; geen van de rapporten is regelgeving"},
    {"ja": False, "wat": "Actuele stand van zaken -- de jongste bron is van oktober 2026"},
]

#: De bouwstenen uit de architectuur van dit lab die dit dossier hergebruikt, met waarom. Dit
#: was de opdracht: geen nieuw instrument naast de bestaande, maar de bestaande toepassen op een
#: nieuw onderwerp.
BOUWSTENEN = [
    {
        "component": "VectorStore + bge-m3 embeddings",
        "waar": "/chatbot",
        "bestond": "voor de IPLO-index van de vergunningen-chatbot",
        "hier": "dezelfde store en dezelfde embedding-server, nu over vier pdf's in plaats van "
                "webpagina's -- en per pagina gechunkt, zodat elk fragment een deeplink heeft",
    },
    {
        "component": "rdflib triple-store",
        "waar": "/kennisgraaf",
        "bestond": "voor de Aquo-stoffengraaf en de toezichtgraaf",
        "hier": "een graaf waarin elke bewering meevoert of zij uit een document komt of een "
                "lezing van dit lab is",
    },
    {
        "component": "Het eindbeeld als blokjes",
        "waar": "/maquette",
        "bestond": "als verbeelding van de BALO-businessarchitectuur",
        "hier": "elk blokje krijgt een reden: dit is wat er volgens de rapporten vandaag op die "
                "plek misgaat",
    },
    {
        "component": "Herkomst per bewering",
        "waar": "/balo",
        "bestond": "als scheiding tussen wat een document zegt en wat dit lab eruit leest",
        "hier": "hetzelfde, maar nu met een citaat en een paginanummer die een test natrekt",
    },
]


def gezondheid() -> dict:
    """Of de kennisbasis klopt: citaten, documenten, index.

    Werpt niets. Een ontbrekend document is een toestand om te melden, niet een fout die de
    pagina moet breken -- de bevindingen en de graaf werken zonder de pdf's."""
    try:
        fout = vindplaats_mod.controleer_alles(bevindingen_mod.BEVINDINGEN)
        gecontroleerd = True
    except FileNotFoundError as exc:
        fout, gecontroleerd = [], False
        reden = str(exc)
    else:
        reden = None
    op_schijf = [bronnen_mod.beschikbaar(b) for b in bronnen_mod.BRONNEN]
    return {
        "citaten_gecontroleerd": gecontroleerd,
        "citaten": len(bevindingen_mod.BEVINDINGEN),
        "citaten_fout": len(fout),
        "citaten_reden": reden,
        "documenten_op_schijf": sum(1 for o in op_schijf if o["pdf"]),
        "documenten": len(op_schijf),
        "index": index_mod.status(),
    }


def dossier() -> dict:
    """Het hele dossier, zoals de pagina het leest. Raakt geen netwerk: de bevindingen, de
    thema's en de graaf komen uit de code, de citaatcontrole en de indexstatus van schijf."""
    graaf = graaf_mod.bouw()
    return {
        "dossier": DOSSIER,
        "bronnen": bronnen_mod.overzicht(),
        "themas": bevindingen_mod.per_thema(),
        "verbanden": bevindingen_mod.verbanden(),
        "onbesproken": bevindingen_mod.onbesproken(),
        "herkomst": bevindingen_mod.HERKOMST,
        "bouwstenen": BOUWSTENEN,
        "geschikt": GESCHIKT,
        "graafvragen": graaf_mod.uitslagen(graaf),
        "graaf": graaf_mod.telling(graaf),
        "gezondheid": gezondheid(),
        "telling": bevindingen_mod.telling(),
    }
