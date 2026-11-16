"""Één bouwer voor de register-brede toezichtgraaf, met twee aanroepers.

**Waarom deze module bestaat.** De route `/api/toezicht/vraag` bouwde de graaf zelf, en
`scripts/22_bouw_toezichtgraaf.py` bouwde hem ook -- maar zonder `context`, dus zonder
`t:Signaal`, dus zonder de brug tussen de twee lezers. Twee bouwers die hetzelfde heten en iets
anders maken is precies het patroon waar dit project het meeste aan heeft verloren: het bestand
op schijf zou stil een andere graaf zijn dan de route in het geheugen heeft, en welk antwoord een
vraag kreeg zou afhangen van welke van de twee er die keer gebruikt werd.

**Wat deze module níet doet: bronnen ophalen.** Elke bron komt als argument binnen -- register,
metingen, normen, Aquo-referentie, overschrijdingen, gemeten codes, en een functie die het
waterlichaam per vergunning opzoekt. Zo raakt geen enkele test hier het netwerk, en kan het
script dezelfde graaf bouwen als de route zonder de configuratie van de webdienst te kennen.

**Het waterlichaam is per vestiging, en dat is geen detail.** Het wordt opgezocht uit de eigen
coördinaat van elke vergunning. Zou elke vestiging hetzelfde waterlichaam krijgen, dan vuurt
`signalen.regel_norm_overschreden_bovenstrooms` op het hele register met een richting die voor
vrijwel elke vergunning onjuist is -- de duurste fout die deze graaf kan maken. `graaf.bouw`
krijgt daarom een functie per vestiging in plaats van één dict.
"""
from rdflib import RDF

from leefomgevinglab.usecases.toezicht import aquo as aquo_mod
from leefomgevinglab.usecases.toezicht import graaf as graaf_mod


def bouw(register, metingen, normen, aquo_ref, overschrijdingen, gemeten_codes,
         stoffen_met_norm, waterlichaam_per_vergunning):
    """De graaf over het hele register, met de signalen van beide lagen erin.

    `waterlichaam_per_vergunning` is een functie `register -> {(kenmerk, locatiecode): owl_id}`.
    Die sleutelvorm is bewust niet `toerekening.sleutel_post`: die valt bij een ontbrekend
    kenmerk én locatiecode terug op de *positie* in de lijst, en die positie reist niet mee --
    `graaf.bouw` geeft aan de contextfunctie een door `aquo.verrijk` gemaakte kópie door, dus noch
    de index noch de objectidentiteit is daar nog beschikbaar. Het paar (kenmerk, locatiecode) zijn
    de twee velden die de verrijking ongemoeid laat. Een post zonder beide krijgt zo geen
    waterlichaam: dezelfde eerlijke uitkomst als `mag.buiten_toerekening` op `/kmg`, en in het
    Maasregister komt het niet voor (alle 69 posten dragen een locatiecode).
    """
    if not register:
        raise ValueError(
            "leeg register -- geen graaf gebouwd. Een lege graaf is het ergste antwoord dat deze "
            "laag kan geven: elke vraag levert dan 'geen resultaten', en dat leest als 'er is "
            "niets aan de hand' in plaats van 'de bron ontbreekt'.")

    gedeeld = {
        "stoffen_met_norm": stoffen_met_norm,
        "gemeten_codes": gemeten_codes,
        "overschrijdingen": overschrijdingen,
        "register_codes": aquo_mod.register_codes(
            [aquo_mod.verrijk(p, aquo_ref) for p in register]),
    }
    per_vergunning = waterlichaam_per_vergunning(register)

    def context_voor(vestiging: dict) -> dict:
        paar = (vestiging.get("kenmerk"), vestiging.get("locatiecode"))
        return {**gedeeld, "waterlichaam": per_vergunning.get(paar)}

    graaf = graaf_mod.bouw(register, metingen, normen, aquo_ref, context=context_voor)
    # Eén keer over het hele register, niet per vestiging: een overschrijding is een feit over een
    # meetpunt, niet over een vergunning. Zie `graaf.overschrijdingen_triples` voor waarom dit
    # niet als query over Meting en Norm wordt gelaten (119 s in rdflib).
    graaf_mod.overschrijdingen_triples(graaf, overschrijdingen)
    return graaf


def telling(graaf) -> dict:
    """Wat er in de graaf zit, **uitsluitend uit de graaf geteld** -- nooit uit het register
    ernaast en nooit door een aanroeper bijgehouden.

    Dat is geen stijlkeuze. Deze telling wordt gebruikt door twee paden: de route die de graaf
    live bouwt (en het register dus als lijst heeft) en de route die hem van schijf leest (waar
    dat register niet bestaat). Zou de telling het register nodig hebben, dan moest het tweede
    pad een getal verzinnen -- en dan staat er op de pagina een aantal vestigingen dat niet uit de
    graaf komt die de vragen beantwoordt."""
    def aantal(klasse):
        return sum(1 for _ in graaf.subjects(predicate=RDF.type, object=klasse))

    return {
        "triples": len(graaf),
        "vestigingen": aantal(graaf_mod.T.Vestiging),
        "voorschriften": aantal(graaf_mod.T.Voorschrift),
        "signalen": aantal(graaf_mod.T.Signaal),
        "overschrijdingen": aantal(graaf_mod.T.Overschrijding),
    }


def bouw_met_telling(**kwargs):
    """`bouw()` plus `telling()` in één aanroep -- de vorm die beide aanroepers nodig hebben."""
    graaf = bouw(**kwargs)
    return graaf, telling(graaf)
