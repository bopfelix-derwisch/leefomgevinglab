"""De rekensom: hoeveel ruimte is er nog, en van wie is die?

Per parameter:
  ruimte tot de norm = (norm − achtergrondconcentratie) × debiet van het waterlichaam

De achtergrond is de gemeten concentratie en bevat dus al wat er vandaag geloosd wordt. De
vergunde vracht uit het register wordt daarom niet van de ruimte afgetrokken — dat zou dubbel
tellen — maar apart getoond: hoeveel van de huidige belasting komt uit vergunningen, en is dus
in menselijke hand, tegenover wat diffuus of van bovenstrooms komt.

Is de achtergrond hoger dan de norm, dan is er geen ruimte. Voor een zeer zorgwekkende stof is
dat geen randgeval maar het normale geval, en dan is 'hoe klein is mijn lozing' niet de vraag.

Een registerpost kan voor een stof geen vracht dragen maar wél een 'onbepaald'-vermelding (zie
`atlas_register.py`) — de vracht valt niet af te leiden, niet dat hij nul is. Die posten tellen
in `vergund_kg_jaar` daarom niet mee als nul zonder iets te melden: `vergund_onbepaald` telt ze
per parameter, en zodra dat aantal boven nul ligt is `vergund_kg_jaar` een ondergrens — dat staat
dan ook zo in de conclusie.
"""
from .gebied import SECONDEN_PER_JAAR, vracht_kg_jaar


def _ruimte_kg_jaar(ruimte_mg_l: float, debiet_m3_s: float) -> float:
    """mg/l × m³/s → kg/jaar."""
    return ruimte_mg_l * debiet_m3_s * SECONDEN_PER_JAAR / 1000.0


def _vracht_van(post: dict, parameter: str) -> float:
    """De vracht van één vergunning voor één parameter.

    Het synthetische register geeft debiet + concentratie; de Atlas geeft soms rechtstreeks een
    vergunde vracht. Beide vormen komen hier binnen.
    """
    if "vrachten" in post:
        return post["vrachten"].get(parameter, 0.0)
    return vracht_kg_jaar(post["debiet_m3_per_uur"], post["concentraties"].get(parameter, 0.0))


def _onbepaald_voor(post: dict, parameter: str) -> bool:
    """Draagt deze registerpost een 'onbepaald'-vermelding voor deze stof?

    Alleen Atlas-posten kunnen dat (`_vracht_van` geeft voor zo'n stof 0.0 terug, niet omdat er
    niets vergund is maar omdat het niet valt af te leiden). Het synthetische register kent het
    veld `onbepaald` niet, dus `.get(..., [])` levert daar altijd False op — het bestaat en
    gedraagt zich exact als voorheen.
    """
    return any(o.get("parameter") == parameter for o in post.get("onbepaald", []))


def bereken(voornemen: dict, register: list, waterlichaam: dict) -> dict:
    q = waterlichaam["debiet_m3_s"]
    uit = []
    for p in waterlichaam["parameters"]:
        naam = p["naam"]
        ruimte_mg_l = p["norm_mg_l"] - p["achtergrond_mg_l"]
        vrij = _ruimte_kg_jaar(ruimte_mg_l, q)

        bijdragen = [(v["naam"], _vracht_van(v, naam)) for v in register]
        bijdragen = [(n, kg) for n, kg in bijdragen if kg > 0]
        vergund = sum(kg for _, kg in bijdragen)
        vergund_onbepaald = sum(1 for v in register if _onbepaald_voor(v, naam))

        gevraagd = vracht_kg_jaar(voornemen["debiet_m3_per_uur"],
                                  voornemen["concentraties"].get(naam, 0.0))

        if ruimte_mg_l <= 0:
            oordeel = "geen ruimte"
        elif gevraagd <= 0:
            oordeel = "past"
        elif gevraagd <= vrij:
            oordeel = "past"
        else:
            oordeel = "past niet"

        uit.append({
            "naam": naam, "zzs": p["zzs"], "toelichting": p["toelichting"],
            "norm_mg_l": p["norm_mg_l"], "achtergrond_mg_l": p["achtergrond_mg_l"],
            "ruimte_mg_l": ruimte_mg_l,
            "vrij_kg_jaar": round(vrij, 1),
            "gevraagd_kg_jaar": round(gevraagd, 3),
            # let op: deze vracht zit al ín de achtergrondconcentratie verwerkt en wordt dus
            # niet van de ruimte afgetrokken; hij laat zien hoeveel van de huidige belasting
            # uit vergunningen komt en dus in menselijke hand is.
            "vergund_kg_jaar": round(vergund, 1),
            "vergund_onbepaald": vergund_onbepaald,
            "vergunningen": len(bijdragen),
            "grootste_vergunde": max(bijdragen, key=lambda b: b[1])[0] if bijdragen else None,
            "benutting_pct": round(100 * gevraagd / vrij, 1) if vrij > 0 else None,
            "oordeel": oordeel,
        })

    blokkerend = [p for p in uit if p["oordeel"] == "geen ruimte"]
    knellend = [p for p in uit if p["oordeel"] == "past niet"]
    register_leeg = not register

    if blokkerend:
        bepalend = blokkerend[0]
        antwoord = "nee, tenzij"
        waarom = (f"Voor {bepalend['naam']} ligt de achtergrondconcentratie al boven de norm. Elke "
                  "extra vracht is achteruitgang" + (" van een zeer zorgwekkende stof, waarvoor "
                  "bovendien een minimalisatieplicht geldt" if bepalend["zzs"] else "") +
                  ". Toestaan kan alleen als er elders even veel af gaat.")
    elif knellend:
        bepalend = knellend[0]
        antwoord = "nee, tenzij"
        waarom = (f"{bepalend['naam']} is bepalend: gevraagd {bepalend['gevraagd_kg_jaar']} kg/jaar "
                  f"tegenover {bepalend['vrij_kg_jaar']} kg/jaar ruimte tot de norm.")
    else:
        bepalend = max((p for p in uit if p["benutting_pct"] is not None),
                       key=lambda p: p["benutting_pct"], default=None)
        antwoord = "ja, mits"
        waarom = ("Alle parameters passen binnen de ruimte tot de norm" +
                  (f"; {bepalend['naam']} is het krapst met "
                   f"{bepalend['benutting_pct']}% van de vrije ruimte." if bepalend else "."))

    kanttekeningen = []
    if register_leeg:
        kanttekeningen.append(
            "Het register is leeg: zonder zicht op bestaande vergunningen valt niet te zien van "
            "wie de ruimte is, en dus ook niet wie hem zou kunnen vrijmaken.")
    onbepaald_parameters = [p for p in uit if p["vergund_onbepaald"] > 0]
    if onbepaald_parameters:
        delen = "; ".join(
            f"{p['naam']} ({p['vergund_onbepaald']} vergunning"
            f"{'en' if p['vergund_onbepaald'] != 1 else ''})" for p in onbepaald_parameters)
        kanttekeningen.append(
            f"Het vergunde totaal is voor sommige parameters een ondergrens: van {delen} viel "
            "de vracht niet te bepalen, en die telt dus niet mee in vergund_kg_jaar.")

    conclusie = {"antwoord": antwoord, "waarom": waarom,
                 "bepalend": bepalend["naam"] if bepalend else None,
                 "kanttekening": " ".join(kanttekeningen)}
    return {"parameters": uit, "conclusie": conclusie, "register_leeg": register_leeg,
            "debiet_waterlichaam_m3_s": q, "indicatief": True}
