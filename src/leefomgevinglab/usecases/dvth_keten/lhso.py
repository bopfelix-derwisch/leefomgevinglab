"""LHSO — Landelijke Handhavingsstrategie Omgevingsrecht: de interventiematrix.

De matrix zet het gedrag van de overtreder (kolommen A–D) af tegen de mogelijke gevolgen
van de overtreding (rijen 1–4) en wijst zo de interventie aan. Omgevingsdiensten zijn
verplicht ermee te werken: híér zit de uniformering van de handhaving, niet in de systemen.

Vereenvoudiging: de echte LHSO laat de toezichthouder binnen een segment kiezen uit een
reeks interventies en vraagt om motivering bij afwijken. Deze implementatie kiest per cel
één passende interventie, zodat de keten een uitkomst heeft. Dat staat ook zo in de uitvoer.
"""

GEDRAG = ("goedwillend", "onverschillig", "calculerend", "bewust en structureel")
GEVOLGEN = ("vrijwel nihil", "beperkt", "van belang", "aanzienlijk")

_LETTER = dict(zip(GEDRAG, "ABCD"))

# zwaarte (2..8) → interventie. Loopt van licht naar zwaar over de diagonaal van de matrix.
_TRAP = [
    (2, "aanspreken en informeren", "bestuurlijk"),
    (3, "waarschuwen — bestuurlijk gesprek", "bestuurlijk"),
    (4, "waarschuwen met hersteltermijn", "bestuurlijk"),
    (5, "last onder dwangsom", "bestuursrechtelijk herstellend"),
    (6, "last onder dwangsom en bestuurlijke boete", "bestuursrechtelijk herstellend en bestraffend"),
    (7, "last onder bestuursdwang, bestuurlijke boete, proces-verbaal",
     "bestuursrechtelijk en strafrechtelijk"),
    (8, "stilleggen, intrekken vergunning, proces-verbaal", "bestuursrechtelijk en strafrechtelijk"),
]


def interventie(gedrag: str, gevolgen: str) -> dict:
    """De cel in de matrix, met de interventie die daarbij hoort."""
    if gedrag not in GEDRAG:
        raise ValueError(f"onbekend gedrag: {gedrag!r} — kies uit {GEDRAG}")
    if gevolgen not in GEVOLGEN:
        raise ValueError(f"onbekende gevolgklasse: {gevolgen!r} — kies uit {GEVOLGEN}")
    g, v = GEDRAG.index(gedrag) + 1, GEVOLGEN.index(gevolgen) + 1
    zwaarte = g + v
    keuze, spoor = next((k, s) for drempel, k, s in _TRAP if drempel >= zwaarte)
    return {"cel": f"{_LETTER[gedrag]}{v}", "gedrag": gedrag, "gevolgen": gevolgen,
            "zwaarte": zwaarte, "interventie": keuze, "spoor": spoor,
            "toelichting": "Vereenvoudigde toepassing van de LHSO-interventiematrix: één "
                           "interventie per cel. De LHSO zelf laat binnen een segment ruimte "
                           "voor een gemotiveerde keuze."}


def matrix() -> list:
    """De hele matrix, voor weergave."""
    return [{"gevolgen": v, "cellen": [interventie(g, v) for g in GEDRAG]}
            for v in reversed(GEVOLGEN)]
