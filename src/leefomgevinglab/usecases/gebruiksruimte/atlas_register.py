"""Atlas-voorschriften omzetten naar registerposten met een vracht in kg/jaar.

De rekensom in `ruimte.py` wil per vergunning weten hoeveel kilo per jaar er van een stof in
het water gaat. De Atlas geeft `Waarde` + `Eenheid` in 21 verschillende eenheden. Drie lagen,
in volgorde:

  1. de eenheid is al een vracht (kg/jaar, ton/jaar, kg/dag, kg/week) — direct omrekenen;
  2. de eenheid is een concentratie (mg/l, µg/l) — vracht = concentratie × debiet, mits bij
     hetzelfde kenmerk een bruikbaar Debiet-voorschrift staat. Dat is zo bij 28 van de 69
     posten (posten ná ontdubbeling, niet de 72 ruwe features uit de bron). Een Debiet-voorschrift in een eenheid die dit lab niet kent (bijvoorbeeld
     "kubieke meter per schoonmaakactie") is géén ontbrekend debiet — dat krijgt een eigen
     reden, niet 'geen debiet-voorschrift';
  3. anders — de vergunning wordt wél getoond, maar zonder vracht en mét een reden.

Die derde categorie is geen tekortkoming om weg te poetsen. Van een vergunning waarin alleen
een concentratie-eis staat en geen debiet, valt de vracht niet te bepalen — en dus valt hij
ook niet op te tellen. Precies het soort bevinding dat /wfs-kwaliteit voor het REV doet.

Eén stof heeft vaak méér dan één regel in de brontabel: 196 van de 368 combinaties kenmerk +
parameter dragen meer dan één waarde, soms met dooreenlopende eenheden (concentratie én vracht
voor dezelfde stof), soms met letterlijk gedupliceerde rijen. Sommeren zou dat allemaal als
losse, optelbare eisen behandelen — en dat is het niet: het zijn *alternatieve* grenswaarden
voor dezelfde vergunning (bijvoorbeeld voor verschillende bedrijfssituaties of lozingspunten).
Daarom wordt hier eerst ontdubbeld (een identieke rij — zelfde parameter, waarde én eenheid —
telt maar één keer) en wordt per stof niet gesommeerd maar het **maximum** genomen over alle
afleidbare kandidaat-vrachten, met steeds het hoogste bij de vergunning gevonden debiet voor de
concentratie-kandidaten. "Hoeveel staat hier al vergund" is een bovengrensvraag: de vergunning
staat toe wat de ruimste van haar eigen grenswaarden toestaat, niet de som van alle grenswaarden
die ooit voor die stof zijn opgeschreven. Waar dat maximum uit meerdere, onderling verschillende
grenswaarden komt, blijft dat zichtbaar via `meerdere_grenswaarden` — op de post en in de
telling — in plaats van stilzwijgend te worden gladgestreken.
"""
from .gebied import vracht_kg_jaar

# De labparameters waar de rekensom mee werkt; alles daarbuiten telt niet mee in de som.
CROSSWALK = {
    "stikstof totaal": "stikstof totaal",
    "zink": "zink",
    "aox": "AOX",
    "som extraheerbare organische halogeenverbindingen": "AOX",
    "extraheerbaar organisch chloor": "AOX",
}

CROSSWALK_BEVINDING = (
    "PFOA komt in de Atlas niet voor als vergunde parameter. De opgenomen vergunningen dateren "
    "deels van vóór de aandacht voor deze stofgroep — kenmerken als DLB2006/8811 en "
    "DLB2007/10829 — terwijl PFOA juist de stof is waar de norm al overschreden wordt. "
    "Een register dat de ZZS niet kent, kan er ook niet op sturen."
)

# Eenheid → factor naar kilogram per jaar.
_VRACHT = {
    "kilogram per jaar": 1.0,
    "ton per jaar": 1000.0,
    "kilogram per dag": 365.0,
    "kilogram per week": 52.0,
}

# Eenheid → factor naar milligram per liter.
_CONCENTRATIE = {
    "milligram per liter": 1.0,
    "microgram per liter": 0.001,
}

# Eenheid → factor naar kubieke meter per uur. "kubieke met per etmaal" is een tikfout in de
# bron; hij staat er echt zo in, dus hij wordt hier ook zo herkend.
_DEBIET = {
    "kubieke meter per uur": 1.0,
    "kubieke meter per dag": 1 / 24,
    "kubieke met per etmaal": 1 / 24,
    "kubieke meter per etmaal": 1 / 24,
    "kubieke meter per week": 1 / 168,
    "kubieke meter per jaar": 1 / 8760,
    "kubieke meter per seconde": 3600.0,
}


def _norm(s) -> str:
    return (s or "").strip().lower()


def _dedupe(voorschriften: list[dict]) -> list[dict]:
    """Een identieke regel (zelfde parameter, waarde én eenheid) telt als één voorschrift.

    De brontabel bevat letterlijke duplicaatrijen — dezelfde eis, tweemaal opgeslagen. Zonder
    ontdubbelen telt zo'n rij dubbel mee in de kandidaat-vrachten hieronder.
    """
    gezien, uniek = set(), []
    for v in voorschriften:
        sleutel = (_norm(v.get("parameter")), v.get("waarde"), _norm(v.get("eenheid")))
        if sleutel in gezien:
            continue
        gezien.add(sleutel)
        uniek.append(v)
    return uniek


def _debiet_m3_per_uur(voorschriften: list[dict]) -> float | None:
    """Het hoogste bruikbare debiet-voorschrift bij deze vergunning, in m³/uur.

    Eén vergunning draagt vaak meerdere Debiet-regels (andere bedrijfssituaties, andere
    lozingspunten). Voor de vracht is het hoogste bepalend: dat is de bovengrens die de
    vergunning toestaat.
    """
    waarden = []
    for v in voorschriften:
        if _norm(v.get("parameter")) == "debiet" and v.get("waarde") is not None:
            factor = _DEBIET.get(_norm(v.get("eenheid")))
            if factor:
                waarden.append(float(v["waarde"]) * factor)
    return max(waarden) if waarden else None


def _debiet_onherkende_eenheden(voorschriften: list[dict]) -> list[str]:
    """De originele eenheden van Debiet-voorschriften die er wél zijn, maar niet worden herkend.

    Onderscheidt 'geen debiet-voorschrift' van 'een debiet-voorschrift met een eenheid die dit
    lab niet kent' (bijvoorbeeld "kubieke meter per schoonmaakactie", zo aangetroffen bij
    RWS-2016/22336). Dat laatste is geen ontbrekend debiet — er ís een grens gesteld, hij is
    alleen niet om te rekenen — en verdient dus een andere reden dan 'geen debiet-voorschrift'.

    Een lege eenheid (None of "") gaat er hier al uit: die is inhoudelijk hetzelfde als 'geen
    bruikbaar debiet' en zou `sorted()` verderop laten klappen op een None-versus-str-vergelijking
    zodra ook maar één andere, wél gevulde onherkende eenheid meekomt. Het resultaat is al
    gesorteerd en ontdubbeld, zodat de aanroeper het zo in de meldingstekst kan zetten.
    """
    return sorted({v.get("eenheid") for v in voorschriften
                   if _norm(v.get("parameter")) == "debiet" and v.get("waarde") is not None
                   and _DEBIET.get(_norm(v.get("eenheid"))) is None and v.get("eenheid")})


def _post(post: dict, telling: dict) -> dict:
    voors = _dedupe(post.get("voorschriften") or [])
    debiet = _debiet_m3_per_uur(voors)
    debiet_onherkend = _debiet_onherkende_eenheden(voors) if debiet is None else []
    kandidaten: dict[str, list[float]] = {}
    onbepaald = []

    for v in voors:
        parameter, waarde, eenheid = v.get("parameter"), v.get("waarde"), _norm(v.get("eenheid"))
        if _norm(parameter) == "debiet":
            continue

        # Eerst de crosswalk: een parameter die dit lab niet volgt telt niet mee, ook niet als
        # 'onbepaald' — die emmer is een bevinding over de vrácht van gevolgde parameters, geen
        # verzamelbak voor alles wat geen kg/jaar heeft (een zuurgraad bijvoorbeeld nooit).
        lab = CROSSWALK.get(_norm(parameter))
        if lab is None:
            telling["buiten_crosswalk"] += 1
            continue
        if waarde is None:
            onbepaald.append({"parameter": lab, "eenheid": v.get("eenheid"),
                              "reden": "geen waarde in de vergunning"})
            telling["onbepaald"] += 1
            continue

        if eenheid in _VRACHT:
            kandidaten.setdefault(lab, []).append(float(waarde) * _VRACHT[eenheid])
            telling["vracht_direct"] += 1
        elif eenheid in _CONCENTRATIE:
            if debiet is None:
                if debiet_onherkend:
                    eenheden = ", ".join(debiet_onherkend)
                    reden = (f"debiet-voorschrift aanwezig maar in een niet-herkende eenheid "
                              f"('{eenheden}'); zonder een bruikbaar debiet is de vracht niet "
                              "te bepalen")
                else:
                    reden = ("concentratie-eis zonder debiet-voorschrift; zonder debiet is de "
                              "vracht niet te bepalen")
                onbepaald.append({"parameter": lab, "eenheid": v.get("eenheid"), "reden": reden})
                telling["onbepaald"] += 1
                continue
            mg_l = float(waarde) * _CONCENTRATIE[eenheid]
            kandidaten.setdefault(lab, []).append(vracht_kg_jaar(debiet, mg_l))
            telling["vracht_uit_concentratie"] += 1
        else:
            onbepaald.append({"parameter": lab, "eenheid": v.get("eenheid"),
                              "reden": f"eenheid '{v.get('eenheid')}' is geen vracht en geen "
                                       "concentratie"})
            telling["onbepaald"] += 1

    # Per stof niet sommeren maar het maximum van de kandidaten: de bovengrens die de vergunning
    # zelf toestaat, niet de som van al haar (soms onderling verschillende) grenswaarden.
    vrachten = {lab: max(waarden) for lab, waarden in kandidaten.items()}
    meerdere_grenswaarden = sorted(lab for lab, waarden in kandidaten.items() if len(waarden) > 1)
    telling["meerdere_grenswaarden"] += len(meerdere_grenswaarden)

    return {"naam": post.get("naam"), "plaats": post.get("plaats"),
            "kenmerk": post.get("kenmerk"), "locatiecode": post.get("locatiecode"),
            "besluitdatum": post.get("besluitdatum"),
            "locatie": post.get("locatie"), "url": post.get("url"),
            "debiet_m3_per_uur": debiet, "vrachten": vrachten,
            "meerdere_grenswaarden": meerdere_grenswaarden, "onbepaald": onbepaald}


def naar_register(posten: list[dict]) -> dict:
    """De Atlas-posten als register, in het formaat dat `ruimte.bereken()` verwacht."""
    telling = {"vestigingen": len(posten), "vracht_direct": 0, "vracht_uit_concentratie": 0,
               "onbepaald": 0, "buiten_crosswalk": 0, "meerdere_grenswaarden": 0}
    register = [_post(p, telling) for p in posten]
    return {"register": register, "telling": telling, "echt": True,
            "bevinding": CROSSWALK_BEVINDING,
            "bron": {"naam": "Atlas voor een Schone Maas",
                     "url": "https://atlas-smwk.hub.arcgis.com/",
                     "houder": "Schone Maaswaterketen",
                     "licentie": "publiek toegankelijk, geen expliciete licentie; live bevraagd "
                                 "met bronvermelding"}}
