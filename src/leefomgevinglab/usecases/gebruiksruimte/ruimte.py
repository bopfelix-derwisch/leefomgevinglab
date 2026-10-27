"""De rekensom: hoeveel ruimte is er nog, en van wie is die?

Per parameter:
  ruimte tot de norm = (norm − achtergrondconcentratie) × debiet van het waterlichaam

**Wat deze rekensom is, en wat zij niet is.** Zij is de *immissietoets*, en die is de derde en
laatste stap in de beoordeling van een lozing — niet de eerste en niet de enige. Daarvóór komen
de bronaanpak met de voorkeursvolgorde (art. 10.29a Wm: voorkómen, dan hergebruiken, dan pas
lozen) en de beste beschikbare technieken volgens de ABM (art. 8.9 en 8.10 Bkl), met voor een
zeer zorgwekkende stof bovendien een minimalisatieplicht. Die twee gelden **ongeacht** hoeveel
ruimte er is.

Dat onderscheid is het verschil tussen twee heel verschillende lezingen van deze pagina. "Er is
nog ruimte" leest makkelijk als een voorraad die te vergeven valt, en zo werkt het niet: ruimte
is geen recht om haar te gebruiken, en een ruime rivier is geen argument om een bronmaatregel
achterwege te laten. Andersom is "past niet" geen eindoordeel maar de aanleiding voor strengere
voorwaarden dan BBT — BBT+ (art. 8.30 Bkl). Weigeren komt pas in beeld als ook dat niet volstaat
(art. 8.22, lid 1 Bkl), met onevenredige kosten als nauwe uitzondering.

`BEOORDELINGSVOLGORDE` legt die drie stappen vast en `_vervolg()` zet per uitkomst wat de wet
er dan van vraagt. Beide reizen mee in het antwoord, zodat de pagina de rekensom niet kan tonen
zonder haar plaats in de volgorde erbij.

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

# De drie stappen waarin een lozing wordt beoordeeld, in de volgorde van de wet. Alleen de derde
# wordt op deze pagina gerekend; `in_dit_lab` zegt dat per stap, zodat de lezer niet hoeft aan te
# nemen dat wat hier staat de hele beoordeling is.
BEOORDELINGSVOLGORDE = [
    {"nr": 1, "naam": "Bronaanpak en voorkeursvolgorde", "grondslag": "art. 10.29a Wm",
     "wat": "Kan het gebruik van de stof worden voorkomen of beperkt, en kan het afvalwater worden "
            "hergebruikt? Lozen is de laatste optie in die volgorde, niet de eerste vraag.",
     "in_dit_lab": False},
    {"nr": 2, "naam": "Beste beschikbare technieken (ABM)", "grondslag": "art. 8.9 en 8.10 Bkl",
     "wat": "De waterbezwaarlijkheid van de stof bepaalt welke techniek als BBT geldt; voor een "
            "zeer zorgwekkende stof geldt daarbovenop een minimalisatieplicht. Dit staat los van "
            "de vraag hoeveel ruimte het water nog heeft.",
     "in_dit_lab": False},
    {"nr": 3, "naam": "Immissietoets", "grondslag": "art. 8.30 Bkl, Handboek Immissietoets",
     "wat": "Wat de restlozing — dus ná BBT — doet met de kwaliteit van het ontvangende "
            "waterlichaam. Dit is de rekensom op deze pagina.",
     "in_dit_lab": True},
]

# Wat de wet vraagt bij elke uitkomst van die derde stap. Bewust geen van drieën een eindoordeel:
# ook "past" laat de eerste twee stappen onverlet, en ook "past niet" is nog geen weigering.
_VERVOLG = {
    "past": ("Passen binnen de ruimte is niet hetzelfde als toegestaan. De bronaanpak en BBT "
             "(stap 1 en 2) gelden ongeacht de uitkomst hier; een ruim waterlichaam is geen "
             "argument om een bronmaatregel achterwege te laten."),
    "past niet": ("Dit is geen eindoordeel maar de aanleiding voor BBT+ (art. 8.30 Bkl): verder "
                  "gaande voorwaarden dan uit de ABM volgen. Pas als ook dat de lozing niet "
                  "aanvaardbaar maakt, komt weigeren in beeld (art. 8.22, lid 1 Bkl)."),
    "geen ruimte": ("Is de lozing onverenigbaar met de doelen voor het watersysteem, dan moet de "
                    "vergunning worden geweigerd (art. 8.22, lid 1 Bkl). De enige uitweg is een "
                    "maatregel die onevenredig kostbaar is in verhouding tot wat zij oplevert — "
                    "een nauwe uitzondering, geen hoofdregel."),
}


def _vervolg(oordeel: str, zzs: bool = False) -> str:
    """Wat er na deze uitkomst volgens de wet gebeurt.

    Een onbekend oordeel levert liever niets op dan een plausibel klinkende zin: deze tekst gaat
    over wat een bevoegd gezag moet doen, en dat is geen plek om iets te verzinnen.
    """
    tekst = _VERVOLG.get(oordeel)
    if tekst and zzs and oordeel != "past":
        tekst += (" Voor een zeer zorgwekkende stof komt daar de minimalisatieplicht bovenop: "
                  "de lozing moet worden teruggebracht met als streven nul.")
    return tekst or ""


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


def _opsomming(delen: list[str]) -> str:
    """Een nette Nederlandse opsomming: komma's, met 'en' vóór het laatste item.

    Zonder dit werd een lijst van drie of meer stoffen een rij met puntkomma's — leesbaar voor
    wie de code kent, maar geen Nederlands voor wie de pagina leest.
    """
    if len(delen) <= 1:
        return delen[0] if delen else ""
    return ", ".join(delen[:-1]) + " en " + delen[-1]


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
            # Het oordeel is de uitkomst van de immissietoets, niet van de hele beoordeling.
            # Wat de wet er dan van vraagt reist ernaast mee.
            "vervolg": _vervolg(oordeel, p["zzs"]),
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
        delen = [f"{p['naam']} ({p['vergund_onbepaald']} vergunning"
                 f"{'en' if p['vergund_onbepaald'] != 1 else ''})" for p in onbepaald_parameters]
        meervoud = len(delen) > 1
        kanttekeningen.append(
            f"Het vergunde totaal is voor sommige parameters een ondergrens: van "
            f"{_opsomming(delen)} "
            + ("vielen de vrachten" if meervoud else "viel de vracht") +
            " niet te bepalen, en die "
            + ("tellen" if meervoud else "telt") +
            " dus niet mee in vergund_kg_jaar.")

    # Het antwoord hierboven is de uitkomst van stap 3. Welke vervolgplicht daarbij hoort hangt
    # af van de parameter die bepalend was; is er geen bepalende parameter, dan is de uitkomst
    # "past" en geldt de tekst die zegt dat passen nog geen toestemming is.
    conclusie = {"antwoord": antwoord, "waarom": waarom,
                 "bepalend": bepalend["naam"] if bepalend else None,
                 "toets": "immissietoets",
                 "vervolg": _vervolg(bepalend["oordeel"] if bepalend else "past",
                                     bool(bepalend and bepalend["zzs"])),
                 "kanttekening": " ".join(kanttekeningen)}
    return {"parameters": uit, "conclusie": conclusie, "register_leeg": register_leeg,
            "debiet_waterlichaam_m3_s": q, "indicatief": True,
            "beoordeling": {"stap": 3, "van": len(BEOORDELINGSVOLGORDE),
                            "toets": "immissietoets", "volgorde": BEOORDELINGSVOLGORDE}}
