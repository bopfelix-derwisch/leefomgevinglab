"""/wasstraat -- de papierbevindingen van de vergunningverlener, afgeleid van hetzelfde dossier
als /toezicht (plan: `docs/superpowers/plans/2026-11-14-wasstraat-en-toezicht-splitsen.md`).

**Waarom deze module geen tweede `dossier()` bouwt.** `toezicht.dossier.dossier()` stelt het
volledige signaaldossier al samen (kaart, alle tien signalen, telling, voorbehouden, runlog) --
precies wat de standaardpijplijn (`toezicht.runner.Crew.draai`, dezelfde vier taken als
`/toezicht`) oplevert. Deze module herhaalt dat niet: zij neemt dat volledige dossier en
**filtert** het naar de zeven papiersignalen (`signalen.Regel.laag == "papier"`), voegt per
signaal de reparatie toe die uit die bevinding volgt (`_REPARATIE_PER_REGEL` -- in plaats van de
inspecteursvraag die `toezicht.dossier._WAT_TE_DOEN_PER_REGEL` voor `/toezicht` draagt), en leidt
`telling`/`voorbehouden` opnieuw af, uitsluitend uit de gefilterde lijst. Zonder dat zou het
dossier drie signalen meetellen die deze pagina niet toont.

**Twee assen, niet één (eindreview, must-fix 5+6).** `Regel.laag` zegt wie de lezer is (papier of
werkelijkheid); `signalen.is_voorbehoud` zegt of een regel iets over *dit* dossier beweert. Van de
zeven papierregels zijn er vijf een **bevinding** (met een reparatie) en twee een **voorbehoud**
(`niet_regime_zuiver`, `geen_geldigheidsduur`). Die tweede groep is afgeleid uit de
`ALTIJD_LAAG`-drempel in `signalen.DREMPELS`, niet uit een tweede lijst regel-id's, en landt in
het voorbehouden-blok in plaats van in de bevindingenlijst -- met de bewering (en haar getal)
intact, zie `_voorbehoud_zin`. Beide vuurden namelijk op vrijwel elke vergunning (69/69 en 68/69),
dus de bevindingenlijst droeg twee register-brede constanten die de vergunningverlener niet kan
oplossen, en een lezer die twee vergunningen vergeleek rekende die mee als verschil.

**De runlog zelf is ongewijzigd** (dezelfde stappen als `/toezicht` -- dit is dezelfde pijplijn),
maar krijgt hier de samenvatting die de taakbrief vraagt en die nergens anders bestaat: hoeveel
stappen, hoeveel rijen erin/eruit in totaal, de totale duur, en in welke stappen een taalmodel
*werkelijk* is aangeroepen -- niet alleen eligible was (zie `runner.py`, "Fix-ronde 2, bevinding
E": het `llm`-veld meet gebruik, niet gerechtigdheid, en die twee blijven in de samenvattingstekst
hier bewust uit elkaar). Plus per stap één vaste, menselijke zin over wat die stap doet
(`_STAP_UITLEG`), zodat een lezer de keten begrijpt zonder de code te openen.
"""
from collections import Counter

from leefomgevinglab.usecases.toezicht import dossier as toezicht_dossier
from leefomgevinglab.usecases.toezicht import signalen as signalen_mod

# Per papierregel: wat er aan de vergunning moet "rechtkomen" -- een reparatie-instructie voor
# wie de vergunning opstelt, niet de inspecteursvraag die `toezicht.dossier.
# _WAT_TE_DOEN_PER_REGEL` voor `/toezicht` draagt. Vaste catalogus, geen generatie: zelfde vorm
# als die tabel en als `signalen.DREMPELS`. Volledigheid (elke papierregel heeft een reparatie,
# geen werkelijkheidsregel staat hier) is een test in `tests/test_wasstraat_dossier.py`.
_REPARATIE_PER_REGEL: dict[str, str] = {
    "vervallen_code":
        "Vervang de ingetrokken Aquo-code door de code die de referentie nu voor deze stof "
        "voert, en controleer of de grenswaarde sindsdien is herzien.",
    "niet_in_referentie":
        "Benoem de parameter met de officiële Aquo-naam, zodat een latere koppeling niet "
        "opnieuw op raden aankomt.",
    "meerdere_grenswaarden":
        "Leg vast welk voorschrift hier leidend is, of maak expliciet dat de twee waarden een "
        "toegestane bandbreedte vormen in plaats van elkaar tegen te spreken.",
    "vracht_onbepaald":
        "Voeg een debietvoorschrift toe, zodat deze concentratiegrens naar een vracht is om te "
        "rekenen.",
    "vergunning_niet_te_vinden":
        "Vul het ontbrekende identificerende veld aan -- url, kenmerk of besluitdatum -- zodat "
        "deze vergunning op haar eigen document is terug te vinden.",
}

# Per sentinelregel (`signalen.is_voorbehoud`): waarom haar uitkomst een **voorbehoud** is en
# geen bevinding met een reparatie. Zelfde vorm als `_REPARATIE_PER_REGEL`, en de twee catalogi
# dekken samen precies de zeven papierregels zonder overlap -- een test dwingt dat af, afgeleid
# uit de drempel, zodat een derde sentinelregel niet stil zonder tekst kan vallen.
#
# **Eindreview, must-fix 5+6.** Beide stonden eerder in `_REPARATIE_PER_REGEL`, met een
# instructie die de vergunningverlener niet kan of niet hoeft uit te voeren:
#   - `niet_regime_zuiver` zei "vermeld het bemonsteringsregime bij het voorschrift zelf" terwijl
#     de regel juist alléén vuurt als dat regime er al staat (`signalen.py`: `if
#     v.get("bemonstering")`). Op 68 van de 69 vergunningen opende de lezer de vergunning, zag
#     het regime staan, en concludeerde dat de wasstraat niet klopt.
#   - `geen_geldigheidsduur` zei "voeg een geldigheidsperiode toe" terwijl het tekort in de Atlas
#     zit: die bron kent geen geldigheidsperiode per voorschrift. 69 van de 69 kregen die
#     instructie.
# Omdat beide op vrijwel elke vergunning vuren, bestond de bodem van `aantal_open` op `/toezicht`
# uit twee register-brede constanten en kon `wasstraat.op_orde` nooit waar zijn (gemeten: minimum
# 1 papiersignaal over alle 69). Ze landen daarom nu in het voorbehouden-blok, wat de regels zelf
# in hun docstring al over zich zeggen.
_VOORBEHOUD_PER_REGEL: dict[str, str] = {
    "niet_regime_zuiver":
        "Dit is een voorbehoud bij elke vergelijking op deze pagina, geen bevinding over deze "
        "vergunning: de regel vuurt juist omdat het bemonsteringsregime er staat, en een meting "
        "in het watersysteem meldt haar eigen regime niet. Aan het papier valt hier niets te "
        "repareren.",
    "geen_geldigheidsduur":
        "Dit tekort zit in de bron, niet in deze vergunning: de Atlas voor een Schone Maas voert "
        "geen geldigheidsperiode per voorschrift, alleen een besluitdatum per vergunning. Het "
        "geldt daarmee voor elke vergunning in het register in één keer.",
}

# Per taak-id uit `tasks.yaml`: één zin die uitlegt wat die stap doet, voor wie de keten wil
# begrijpen zonder de code te openen. `vraagsteller`/`terugkoppelaar` hebben geen taak in de
# standaardpijplijn (zie `tasks.yaml`) en komen dus nooit in een gewone runlog voor; deze tabel
# dekt daarom precies de vier taken die `/wasstraat` (en `/toezicht`) echt draaien.
_STAP_UITLEG: dict[str, str] = {
    "lees_vergunning":
        "Leest de vergunning uit het register en koppelt elk voorschrift aan een Aquo-code, "
        "waar die te vinden is.",
    "bepaal_signalen":
        "Toetst de vergunning tegen de tien vaste regels -- rekenen en vergelijken, geen "
        "taalmodel.",
    "stel_dossier_samen":
        "Voegt de kaart, de signalen, de telling en de voorbehouden samen tot één dossier, met "
        "deze log als vierde deel.",
    "leg_signalen_uit":
        "Zoekt bij elk signaal een vindplaats in de Aquo-tabel, de KRW-normen of de "
        "Stelselcatalogus Omgevingswet.",
}
_GEEN_UITLEG = "Onbekende stap -- geen vaste uitleg beschikbaar voor deze taak."


def _is_papier(regel_id: str) -> bool:
    """Afgeleid uit `signalen.REGELS`, niet een tweede keer getypt -- zie de moduledocstring van
    `signalen.py` en `Regel.laag`."""
    for regel in signalen_mod.REGELS:
        if regel.id == regel_id:
            return regel.laag == "papier"
    return False


# Kaartvelden die op de papierpagina niet thuishoren. Het waterlichaam is een feit over de
# werkelijkheid, niet over het papier: het staat in geen van de vijf papierbevindingen en de
# vergunningverlener kan er niets mee. `toezicht.dossier._kaart` leest het rechtstreeks van de
# Atlas-vestiging, en die draagt het veld nooit -- dus stond hier voor alle 69 vergunningen
# `{"waarde": None, "zekerheid": "ontbreekt"}`, met het rode ontbrekend-signaal van de kaart
# erop, terwijl `/toezicht` het via een coördinaatopzoeking wél weet (zekerheid `afgeleid`). Twee
# publieke pagina's die elkaar tegenspreken over hetzelfde feit (eindreview, must-fix 3). De
# opzoeking hier kopiëren zou deze pagina een netwerkronde kosten voor een veld dat zij niet
# nodig heeft; daarom laten we het veld weg in plaats van het te vullen.
_NIET_OP_DE_PAPIERKAART = ("waterlichaam",)


def _kaart_papier(kaart: dict | None) -> dict | None:
    """De kaart van het volledige dossier, minus de velden die geen papierfeit zijn (zie
    `_NIET_OP_DE_PAPIERKAART`). `None` blijft `None`."""
    if kaart is None:
        return None
    return {k: v for k, v in kaart.items() if k not in _NIET_OP_DE_PAPIERKAART}


def _is_bevinding(regel_id: str) -> bool:
    """Een papierregel die iets over **deze** vergunning beweert -- dus niet een sentinelregel.
    Afgeleid uit `signalen.is_voorbehoud` (en daarmee uit `signalen.DREMPELS`), nooit uit een
    tweede lijst regel-id's: dezelfde les als bij `Regel.laag`, die precies daarom één
    `frozenset` is."""
    return not signalen_mod.is_voorbehoud(regel_id)


def _werkelijkheid_kops() -> set[str]:
    """De koppen van de drie werkelijkheidsregels -- voor het filteren van de voorbehouden die
    alleen over hén gaan (zie `_voorbehouden_papier`), afgeleid uit `signalen.REGELS`."""
    return {r.kop for r in signalen_mod.REGELS if r.laag == "werkelijkheid"}


def _telling_papier(signalen_lijst: list[dict], aantal_voorschriften: int | None,
                     aantal_voorbehouden: int = 0) -> dict:
    """Zelfde vorm als `toezicht.dossier._telling`, maar uitsluitend over de gefilterde
    (papier-)lijst -- anders telt dit dossier drie signalen mee die de pagina niet toont.
    `aantal_voorschriften` komt ongewijzigd over uit het volledige dossier (dat telt de hele
    vestiging, niet een laag): er is geen aparte "papiertelling" van voorschriften, alleen van
    signalen."""
    per_zwaarte = Counter(s["zwaarte"] for s in signalen_lijst)
    per_regel = Counter(s["regel"] for s in signalen_lijst)
    return {
        "aantal_voorschriften": aantal_voorschriften,
        "aantal_signalen": len(signalen_lijst),
        "aantal_regels_die_vuurden": len(per_regel),
        "aantal_voorbehouden": aantal_voorbehouden,
        "per_zwaarte": {z: per_zwaarte.get(z, 0) for z in ("hoog", "midden", "laag")},
        "per_regel": dict(per_regel),
    }


def _voorbehoud_zin(signaal: dict) -> str:
    """Eén sentinelsignaal als voorbehoudzin: de bewering die het signaal al droeg (met haar
    getal erin -- dat verdwijnt niet, het verhuist alleen van de bevindingenlijst naar het
    voorbehoud) plus de uitleg waarom zij geen bevinding is."""
    bewering = signaal.get("bewering") or signaal.get("signaal") or ""
    return f"{bewering} {_VOORBEHOUD_PER_REGEL[signaal['regel']]}".strip()


def _voorbehouden_papier(voorbehouden: list[str], eigen: list[str] | None = None) -> list[str]:
    """Laat alleen de voorbehouden staan die ook over het papier gaan. Een voorbehoud dat een van
    de drie werkelijkheidssignalen noemt (de ontbrekende meetset, het ontbrekende waterlichaam,
    de ontbrekende registercodes, de ontbrekende normenset -- zie `toezicht.dossier.
    _voorbehouden`) hoort bij een signaal dat deze pagina niet toont en zou hier alleen
    verwarren. Herkend op de kop van het signaal, tussen aanhalingstekens in de brontekst van
    `_voorbehouden` zelf -- geen tweede, eigen lijst contextsleutels."""
    kops = _werkelijkheid_kops()
    overgebleven = [v for v in voorbehouden if not any(f"'{kop}'" in v for kop in kops)]
    eigen = eigen or []
    if not eigen:
        return overgebleven
    # De generieke slotzin (`toezicht.dossier.SLOTZIN`) hoort altijd achteraan te blijven staan;
    # de eigen voorbehouden van deze pagina komen er net vóór. Herkend op de constante zelf, niet
    # op een tekstfragment.
    if overgebleven and overgebleven[-1] == toezicht_dossier.SLOTZIN:
        return overgebleven[:-1] + eigen + [overgebleven[-1]]
    return overgebleven + eigen


def _stap_uitleg(taak: str | None) -> str:
    return _STAP_UITLEG.get(taak, _GEEN_UITLEG)


def _samenvatting(stappen: list[dict]) -> dict:
    """Eén uitgelegde samenvatting van de runlog: afgeleide aantallen (nooit getypt) plus een
    zin die ze in gewone taal samenvoegt, zodat de pagina niet alleen de tabel herhaalt.

    **Ontwerp.** De taakbrief liet de vorm bewust open. Drie dingen wil een lezer weten zonder de
    tabel rij voor rij te lezen: hoeveel er gebeurde, hoeveel data erin en eruit ging, en of daar
    een taalmodel bij was. Dat laatste wordt met de namen van de betrokken agents genoemd, niet
    alleen een getal: de belofte van dit lab is dat `llm` in de runlog *gebruik* meet, niet
    *gerechtigdheid* (zie `runner.py`, "Fix-ronde 2, bevinding E"), en een samenvattingszin die
    dat verschil weer laat verdwijnen zou de duur betaalde correctie ongedaan maken."""
    n = len(stappen)
    rijen_in = sum(s.get("rijen_in") or 0 for s in stappen)
    rijen_uit = sum(s.get("rijen_uit") or 0 for s in stappen)
    duur = sum(s["duur"] for s in stappen if s.get("duur") is not None)
    met_taalmodel = sorted({s["agent"] for s in stappen if s.get("llm")})

    if not n:
        zin = "Nog geen dossier opgevraagd."
    else:
        kern = (f"Deze run doorliep {n} {'stap' if n == 1 else 'stappen'}: {rijen_in} "
                f"{'rij' if rijen_in == 1 else 'rijen'} in, {rijen_uit} "
                f"{'rij' if rijen_uit == 1 else 'rijen'} uit, in {duur * 1000:.0f} ms.")
        if met_taalmodel:
            zin = kern + f" Een taalmodel is echt aangeroepen bij: {', '.join(met_taalmodel)}."
        else:
            zin = kern + " Geen van de stappen heeft een taalmodel aangeroepen."

    return {
        "aantal_stappen": n,
        "rijen_in_totaal": rijen_in,
        "rijen_uit_totaal": rijen_uit,
        "totale_duur": duur,
        "stappen_met_taalmodel": met_taalmodel,
        "zin": zin,
    }


def papier_dossier(volledig: dict) -> dict:
    """Het papierdossier: hetzelfde signaaldossier als `/toezicht`
    (`toezicht.dossier.dossier()`, na een echte run van de standaardpijplijn), gefilterd naar de
    zeven papiersignalen en verrijkt met de reparatie per signaal en de samenvatting/uitleg van
    de runlog.

    `kaart` komt door op `waterlichaam` na (zie `_NIET_OP_DE_PAPIERKAART`) -- de identiteit van
    de vestiging is voor beide lezers dezelfde, haar waterlichaam is geen papierfeit. `signalen` bevat alleen de signalen met `laag == "papier"`, elk met een extra
    `reparatie`-veld (`wat_te_doen`, de inspecteursvraag van `/toezicht`, blijft op het signaal
    staan maar is niet wat deze pagina toont). `telling` en `voorbehouden` zijn opnieuw afgeleid
    uit de gefilterde lijst. `runlog` krijgt, naast de ongewijzigde `stappen` (nu elk met een
    `uitleg`-zin erbij), een `samenvatting`."""
    papier_signalen, eigen_voorbehouden = [], []
    for s in volledig.get("signalen") or []:
        if not _is_papier(s["regel"]):
            continue
        if not _is_bevinding(s["regel"]):
            eigen_voorbehouden.append(_voorbehoud_zin(s))
            continue
        nieuw = dict(s)
        nieuw["reparatie"] = _REPARATIE_PER_REGEL[s["regel"]]
        papier_signalen.append(nieuw)

    runlog = volledig.get("runlog") or {}
    stappen = runlog.get("stappen") or []
    stappen_met_uitleg = [{**stap, "uitleg": _stap_uitleg(stap.get("taak"))} for stap in stappen]
    aantal_voorschriften = (volledig.get("telling") or {}).get("aantal_voorschriften")

    return {
        "kaart": _kaart_papier(volledig.get("kaart")),
        "signalen": papier_signalen,
        "telling": _telling_papier(papier_signalen, aantal_voorschriften,
                                    len(eigen_voorbehouden)),
        "voorbehouden": _voorbehouden_papier(volledig.get("voorbehouden") or [],
                                              eigen_voorbehouden),
        "runlog": {
            "uitgezet": runlog.get("uitgezet", []),
            "stappen": stappen_met_uitleg,
            "samenvatting": _samenvatting(stappen),
        },
    }
