"""De tien signaalregels op het vergunningenregister van de Atlas voor een Schone Maas.

Elke regel is een gewone functie `(vestiging, context) -> list[dict]`: geen netwerk, geen
taalmodel, alleen wat er in `vestiging` en `context` binnenkomt. Dat maakt een signaal
auditeerbaar -- het is terug te herleiden tot een regel en een bronrij, niet tot een taalmodel
dat "iets zag".

Zeven regels hebben aan de vergunning zelf genoeg:

- `vervallen_code` (2), `niet_in_referentie` (3), `meerdere_grenswaarden` (4),
  `vracht_onbepaald` (5), `vergunning_niet_te_vinden` (8), `niet_regime_zuiver` (9),
  `geen_geldigheidsduur` (10).

De overige drie hebben meetdata en stroomrichting nodig, en krijgen die via `context` aangeleverd
-- deze module blijft zelf vrij van connectors en netwerk, ook voor deze drie:

- `geen_onafhankelijke_meting` (1) -- `context["gemeten_codes"]` en, voor de zwaarte,
  `context["stoffen_met_norm"]` (de Aquo-codes met een KRW-norm; ontbreekt die sleutel, dan
  zwijgt het signaal niet maar blijft de zwaarte op `midden` staan).
- `norm_overschreden_bovenstrooms` (6) -- `context["overschrijdingen"]`,
  `context["waterlichaam"]` (van deze vestiging) en `context["is_bovenstrooms"]`
  (standaard `kmg.toerekening.is_bovenstrooms`, zelf ook pure logica, geen I/O).
- `stof_buiten_register` (7) -- `context["register_codes"]` en dezelfde `overschrijdingen`.

**Een signaal is nooit een vaststelling.** De woorden "overtreding", "veroorzaakt door" en "in
strijd met" komen in geen signaaltekst voor -- een regel vraagt aandacht, constateert geen
schending. Dat is dezelfde taalregel als `/kmg` (`usecases/kmg/proclaimer.py`), hier toegepast op
een vergunning in plaats van een meting. Voor `norm_overschreden_bovenstrooms` geldt die regel
extra scherp: het signaal zegt dat deze vestiging bovenstrooms ligt van een overschrijding, niet
dat zij haar veroorzaakt -- precies het voorbehoud dat `kmg.toerekening` voor dezelfde
toerekening al voert (`VOORBEHOUD`, `is_bovenstrooms`).
"""
from typing import Callable, NamedTuple

from leefomgevinglab.usecases.kmg import toerekening

# Een voorschrift met een van deze eenheden is een concentratiegrens. Zonder een debietvoorschrift
# (zie DEBIET_EENHEDEN) ergens in dezelfde vestiging is zo'n grens niet naar een vracht om te
# rekenen -- dat is regel 5.
CONCENTRATIE_EENHEDEN = {"milligram per liter", "microgram per liter"}

# Letterlijk overgenomen uit de eenhedentabellen die dit lab al heeft, niet opnieuw verzonnen:
# `usecases/kmg/lozingsmodel.py` (EENHEDEN, dimensie "debiet", incl. de schrijffout "kubieke met
# per etmaal" die daar bewust wordt herkend) en `usecases/gebruiksruimte/atlas_register.py`
# (_DEBIET, met "kubieke meter per etmaal", "... per week" en "... per seconde" erbij). Beide
# tabellen blijven ongeïmporteerd -- dit bestand mag niet van een connector of brontabel afhangen
# -- maar de spellingen moeten wel matchen, anders ontstaat hier een vals-positieve
# "vracht niet te bepalen" op een vestiging die wél een debietvoorschrift heeft.
# Expliciete opsomming, geen patroon op "kubieke meter per ...": niet elke eenheid met die vorm is
# een doorlopend debiet (atlas_register.py noemt "kubieke meter per schoonmaakactie" als
# tegenvoorbeeld), dus een onbekende spelling telt bewust niet mee.
DEBIET_EENHEDEN = {
    "kubieke meter per uur",
    "kubieke meter per dag",
    "kubieke meter per jaar",
    "kubieke meter per etmaal",
    "kubieke meter per week",
    "kubieke meter per seconde",
    "kubieke met per etmaal",  # schrijffout in de bron, zie lozingsmodel._EENHEID_NOTITIE
}

# Sentinel voor "nog niet opgezocht": ontbreekt de sleutel `aquo` op een voorschrift, dan heeft
# niemand geprobeerd deze naam aan een code te koppelen en is er niets te signaleren. Pas een
# expliciete waarde `None` (de koppeling is geprobeerd en mislukt) telt als signaal.
_NIET_OPGEZOCHT = object()

# Fix-ronde (eindreview, bevinding 2): parameters waarvoor twee grenswaarden een toegestane
# bandbreedte vormen, geen tegenstrijdige eis. Zuurgraad is het bekende geval: een vergunning
# vergunt pH altijd als venster (bv. 6,5-9,0), en dat venster is de normale, correcte vorm, niet
# een "welke grenswaarde geldt?"-vraag. Bovendien is pH logaritmisch, dus een verhouding tussen
# twee pH-waarden is sowieso betekenisloos -- live trof deze regel 36 van de 164 destijds
# getelde gevallen puur op dit patroon. Op naam, niet op eenheid ("dimensieloos" draagt in het
# register ook "Vervuilingswaarde", een gewone telling waarvoor een venster geen correcte lezing
# is). Lowercase-vergelijking: de bron schrijft zowel "Zuurgraad" als "zuurgraad".
_GEEN_DISCREPANTIE_PARAMETERS = {"zuurgraad"}


class Regel(NamedTuple):
    """Een rij uit de signaalcatalogus (plan, §6)."""
    id: str
    kop: str
    # Sleutel waarmee een latere `uitleg`-module de "waarom is dit erg?"-tekst opzoekt. Nu nog
    # ongebruikt binnen dit bestand; bestaat al zodat die koppeling straks niet op deze module
    # hoeft terug te komen.
    uitleg_sleutel: str
    functie: Callable[[dict, dict], list[dict]]


# Per regel: de drempel waarboven het signaal zwaar weegt, en wat `omvang` daar betekent.
# Eén tabel in plaats van zes if-takken, zodat de drempel te zien is zonder de code te lezen.
DREMPELS = {
    "geen_onafhankelijke_meting": (1, "aantal voorschriften zonder meting"),
    "vervallen_code":             (1, "aantal voorschriften op een ingetrokken code"),
    "niet_in_referentie":         (3, "aantal voorschriften met een onbekende naam"),
    "meerdere_grenswaarden":      (2, "verhouding hoogste / laagste grenswaarde"),
    "vracht_onbepaald":           (5, "aantal voorschriften zonder debietvoorschrift"),
    "norm_overschreden_bovenstrooms": (1, "aantal overschreden stoffen benedenstrooms"),
    "stof_buiten_register":       (1, "aantal gemeten stoffen zonder enig voorschrift"),
    "vergunning_niet_te_vinden":  (3, "aantal ontbrekende identificerende velden"),
    "niet_regime_zuiver":         (99, "altijd laag; dit is een voorbehoud, geen bevinding"),
    "geen_geldigheidsduur":       (99, "altijd laag; geldt voor het hele register"),
}


# Regels waarvan de zwaarte afhangt van het bestaan van een norm: zonder norm is er niets om de
# grenswaarde tegen te houden, en dan weegt het signaal lichter. Alleen `geen_onafhankelijke_meting`
# -- de rest van de regels weegt `hoog` zodra de drempel gehaald is, norm of geen norm (zie §6).
NORM_BEPAALT_ZWAARTE = {"geen_onafhankelijke_meting"}


def zwaarte(regel_id: str, omvang: float, norm_aanwezig: bool = False) -> str:
    """Afgeleid, nooit getypt.

    Wat `omvang` betekent verschilt per regel en staat in `DREMPELS` -- bij regel 4 is het de
    verhouding tussen de hoogste en de laagste grenswaarde, bij regel 1 een aantal
    voorschriften. Een onbekende regel werpt een KeyError in plaats van stil `laag` te geven:
    een nieuwe regel zonder drempel is een vergeten keuze, niet een lichte bevinding.

    Drempel `99` is geen telling om te halen maar een sentinel (zie `DREMPELS`,
    `niet_regime_zuiver` en `geen_geldigheidsduur`): zo'n regel weegt per ontwerp altijd `laag`,
    wat de werkelijke omvang ook is. Die garantie zit daarom hier, in de afleiding zelf, en niet
    in een nep-omvang die een aanroeper verzint om er toevallig op uit te komen -- anders stopt
    de garantie onopgemerkt zodra de rest van deze functie verandert.

    `norm_aanwezig` doet alleen iets voor de regels in `NORM_BEPAALT_ZWAARTE`: is de drempel
    gehaald maar bestaat er geen KRW-norm voor de stof, dan blijft het signaal op `midden` staan
    in plaats van door te schieten naar `hoog` -- er is dan niets om de grenswaarde tegen te
    houden. Voor elke andere regel is `hoog` het antwoord zodra de drempel gehaald is, los van
    `norm_aanwezig`.
    """
    drempel, _ = DREMPELS[regel_id]
    if drempel >= 99:
        return "laag"
    if omvang >= drempel:
        if regel_id in NORM_BEPAALT_ZWAARTE and not norm_aanwezig:
            return "midden"
        return "hoog"
    return "midden" if omvang > 0 else "laag"


def _signaal(regel_id: str, kop: str, omvang: float, bewijs: list[dict],
             norm_aanwezig: bool = False) -> dict:
    """Eén signaal in de vaste vorm. `omvang` bepaalt zowel wat er getoond wordt als -- via
    `zwaarte()` -- hoe zwaar het weegt, zodat de twee niet uit de pas kunnen lopen."""
    return {"regel": regel_id, "signaal": kop,
            "zwaarte": zwaarte(regel_id, omvang, norm_aanwezig),
            "omvang": omvang, "bewijs": bewijs}


def regel_meerdere_grenswaarden(vestiging: dict, context: dict) -> list[dict]:
    """Welke grenswaarde geldt? -- dezelfde parameter heeft binnen één vestiging meer dan één
    grenswaarde **in dezelfde eenheid**. `omvang` is de verhouding hoogste / laagste; daar is geen
    drempel op getallen voor nodig, de verhouding zelf is de maat.

    **Fix-ronde (eindreview, bevinding 2).** Vóór deze fix groepeerde deze regel alleen op
    `parameter`, en nam zij `max/min` over die groep zonder naar `eenheid` te kijken. Live gaf dat
    bij 53 van de 164 toen getelde gevallen (32%) een concentratiegrens (mg/l) en een vrachtgrens
    (kg/jaar) voor dezelfde stof tegen elkaar -- twee elkaar aanvullende voorwaarden, geen
    tegenstrijdigheid, met als zichtbaar gevolg een bewering als "een factor 35704419,9× verschil"
    (CORUSNB, Warmte: 220000 MJ/dag tegenover 2,508 MJ/seconde). Dat is precies de fout die
    `kmg.toerekening` elders in dit lab expliciet vermijdt (nooit stilzwijgend een eenheid
    aannemen). Groeperen op `(parameter, eenheid)` i.p.v. alleen `parameter` lost dit op: een
    concentratie- en een vrachtgrens voor dezelfde stof komen nu in twee aparte groepen terecht en
    worden niet meer tegen elkaar gedeeld. Zie ook `_GEEN_DISCREPANTIE_PARAMETERS` hierboven voor
    de tweede helft van deze fix (Zuurgraad/pH).

    **De deling wordt bewaakt.** Een grenswaarde van 0 naast een grenswaarde groter dan 0 zou
    `max/min` op een `ZeroDivisionError` laten stuklopen -- vandaag komt dat in het register niet
    voor, maar een regel die een live eindpunt bedient mag daar niet op vertrouwen (zie
    `kmg.toerekening`, die een afvoer van 0 ook expliciet afvangt in plaats van te laten crashen).
    Is de laagste waarde 0, dan is de verhouding per definitie onbegrensd: `omvang` wordt dan
    `float("inf")` (altijd `hoog`, zie `zwaarte()`) in plaats van dat de functie een 500 teruggeeft."""
    per_groep: dict[tuple, list[dict]] = {}
    for v in vestiging.get("voorschriften") or []:
        parameter = v.get("parameter")
        if (parameter or "").strip().lower() in _GEEN_DISCREPANTIE_PARAMETERS:
            continue
        per_groep.setdefault((parameter, v.get("eenheid")), []).append(v)

    uit = []
    for (_parameter, _eenheid), voorschriften in per_groep.items():
        waarden = {v["waarde"] for v in voorschriften if v.get("waarde") is not None}
        if len(waarden) < 2:
            continue
        laagste, hoogste = min(waarden), max(waarden)
        omvang = float("inf") if laagste == 0 else hoogste / laagste
        uit.append(_signaal("meerdere_grenswaarden", "welke grenswaarde geldt?", omvang,
                             voorschriften))
    return uit


def regel_vervallen_code(vestiging: dict, context: dict) -> list[dict]:
    """Grenswaarde op een ingetrokken code -- de Aquo-code is er, maar `Vervallen`: er is geen
    geldige referentie meer om de grenswaarde tegen te toetsen. Eén signaal per vestiging, met
    alle getroffen voorschriften als bewijs."""
    getroffen = [v for v in (vestiging.get("voorschriften") or [])
                 if v.get("aquo_status") == "Vervallen"]
    if not getroffen:
        return []
    return [_signaal("vervallen_code", "grenswaarde op een ingetrokken code", len(getroffen),
                      getroffen)]


def regel_niet_in_referentie(vestiging: dict, context: dict) -> list[dict]:
    """Parameter niet in de referentie -- de naam koppelt aan geen enkele Aquo-code. Dat is iets
    anders dan `vervallen_code`: hier is er nooit een code geweest om op te vervallen."""
    getroffen = [v for v in (vestiging.get("voorschriften") or [])
                 if v.get("aquo", _NIET_OPGEZOCHT) is None]
    if not getroffen:
        return []
    return [_signaal("niet_in_referentie", "parameter niet in de referentie", len(getroffen),
                      getroffen)]


def regel_vracht_onbepaald(vestiging: dict, context: dict) -> list[dict]:
    """Vracht niet te bepalen -- een concentratiegrens zonder dat er ergens in de vestiging een
    debietvoorschrift staat om haar mee om te rekenen naar een vracht."""
    voorschriften = vestiging.get("voorschriften") or []
    debiet_aanwezig = any(v.get("eenheid") in DEBIET_EENHEDEN for v in voorschriften)
    if debiet_aanwezig:
        return []
    getroffen = [v for v in voorschriften if v.get("eenheid") in CONCENTRATIE_EENHEDEN]
    if not getroffen:
        return []
    return [_signaal("vracht_onbepaald", "vracht niet te bepalen", len(getroffen), getroffen)]


def regel_geen_onafhankelijke_meting(vestiging: dict, context: dict) -> list[dict]:
    """Geen onafhankelijke meting -- het voorschrift noemt een stof die op geen enkel meetpunt in
    `context["gemeten_codes"]` voorkomt, dus er is geen onafhankelijke meting in het watersysteem
    waartegen de grenswaarde te houden valt. Wie wil controleren, is dan afhankelijk van de
    zelfrapportage van de lozer.

    Eén signaal **per aquo-code**, niet één voor de hele vestiging: §6 maakt de zwaarte
    uitdrukkelijk afhankelijk van de stof ("hoog bij een stof met een KRW-norm, anders midden"),
    en die twee uitkomsten kunnen binnen één vestiging naast elkaar bestaan -- een vergunning kan
    tegelijk zink (met norm) en zuurgraad (zonder norm) ongemeten vergund hebben. `omvang` is per
    signaal het aantal voorschriften zonder meting op die ene code.

    `aquo` moet aanwezig en niet-`None` zijn om mee te tellen -- een voorschrift zonder geldige
    code hoort bij `niet_in_referentie` of `vervallen_code`, niet hier: zonder code is er geen
    stof om tegen `gemeten_codes` te vergelijken.

    Ontbreekt `gemeten_codes` zelf (de sleutel staat niet in `context`), dan zwijgt de regel --
    dat is "geen meetset aangeleverd", niet "geen enkele stof wordt gemeten". Een lege
    `set()` die wél is aangeleverd, blijft wel gelden: dan is bewust vastgesteld dat er niets
    gemeten is, en telt elke vergunde stof als onafhankelijk ongetoetst.

    `context["stoffen_met_norm"]` (Aquo-codes met een KRW-norm) bepaalt `norm_aanwezig` per code.
    Dit werkt **anders** dan `gemeten_codes`: ontbreekt deze sleutel, dan zwijgt de regel niet --
    het signaal blijft gewoon afgaan, alleen valt de zwaarte terug op het geen-norm-geval
    (`midden`), precies zoals wanneer de sleutel er wél is maar voor die code leeg blijft. Een
    ontbrekende norm-opgave mag een signaal dus nooit onderdrukken, want "we weten niet of er een
    norm is" is geen reden om te zwijgen over een stof die nergens onafhankelijk gemeten wordt --
    het is alleen een reden om niet naar `hoog` te escaleren."""
    gemeten_codes = context.get("gemeten_codes")
    if gemeten_codes is None:
        return []
    stoffen_met_norm = context.get("stoffen_met_norm") or set()

    per_code: dict[str, list[dict]] = {}
    for v in vestiging.get("voorschriften") or []:
        code = v.get("aquo")
        if code and code not in gemeten_codes:
            per_code.setdefault(code, []).append(v)

    uit = []
    for code, voorschriften in per_code.items():
        uit.append(_signaal("geen_onafhankelijke_meting", "geen onafhankelijke meting",
                             len(voorschriften), voorschriften,
                             norm_aanwezig=code in stoffen_met_norm))
    return uit


def regel_norm_overschreden_bovenstrooms(vestiging: dict, context: dict) -> list[dict]:
    """Meting boven de norm, lozer bovenstrooms -- op een meetpunt benedenstrooms (of op dezelfde
    plek) is een KRW-norm overschreden, en deze vestiging ligt daar bovenstrooms van.

    Dit stelt niet vast dat deze vestiging de overschrijding veroorzaakt -- alleen dat haar
    positie aandacht verdient als het toezicht nagaat waar een overschrijding vandaan kan komen.
    Hetzelfde voorbehoud als `kmg.toerekening` voert over de toerekening van een vracht.

    `context["overschrijdingen"]` is de kant-en-klare lijst reeds-geconstateerde overschrijdingen
    (elk met minstens `meetpunt`, `waterlichaam`, `stof`, `gemeten`, `norm`, `eenheid`) -- deze
    regel toetst zelf geen norm, dat is al gedaan. `context["waterlichaam"]` is het waterlichaam
    van déze vestiging; zonder dat gegeven is de richting niet te bepalen en zwijgt de regel.
    `context["is_bovenstrooms"]` is injecteerbaar voor de tests en valt terug op
    `kmg.toerekening.is_bovenstrooms` -- pure logica, geen bron, dus veilig te importeren.

    `omvang` is het aantal **verschillende stoffen** in `bewijs` (zie `DREMPELS`: "aantal
    overschreden stoffen benedenstrooms"), niet het aantal overschrijdingsrijen -- dezelfde stof
    kan op twee meetpunten benedenstrooms overschreden zijn en telt dan als één stof, al blijven
    beide rijen in `bewijs` staan."""
    waterlichaam = context.get("waterlichaam")
    if not waterlichaam:
        return []
    is_bovenstrooms = context.get("is_bovenstrooms") or toerekening.is_bovenstrooms
    getroffen = [o for o in (context.get("overschrijdingen") or [])
                 if is_bovenstrooms(waterlichaam, o.get("waterlichaam"))]
    if not getroffen:
        return []
    omvang = len({o.get("stof") for o in getroffen})
    return [_signaal("norm_overschreden_bovenstrooms",
                      "meting boven de norm, lozer bovenstrooms", omvang, getroffen)]


def regel_stof_buiten_register(vestiging: dict, context: dict) -> list[dict]:
    """Gemeten stof die in geen vergunning staat -- een stof die de norm nadert of overschrijdt
    (`context["overschrijdingen"]`) komt in het hele register (`context["register_codes"]`)
    helemaal niet voor, dus geen enkele vergunning begrenst haar. PFOA is het bekende geval.

    Dit is een bevinding over het register als geheel, niet over het papier van déze vestiging --
    zelfde patroon als `geen_geldigheidsduur`: precies één signaal per dossier, nooit één per
    voorschrift, met alle betrokken stoffen samen als bewijs.

    Ontbreekt `register_codes` zelf, dan zwijgt de regel -- net als bij `gemeten_codes` in
    `regel_geen_onafhankelijke_meting` is "geen register aangeleverd" iets anders dan "het
    register is leeg".

    `omvang` is het aantal **verschillende stoffen** in `bewijs` (zie `DREMPELS`: "aantal
    gemeten stoffen zonder enig voorschrift"), niet het aantal overschrijdingsrijen -- dezelfde
    stof kan op twee meetpunten de norm overschrijden en telt dan als één stof, al blijven beide
    rijen in `bewijs` staan."""
    register_codes = context.get("register_codes")
    if register_codes is None:
        return []
    getroffen = [o for o in (context.get("overschrijdingen") or [])
                 if o.get("stof") not in register_codes]
    if not getroffen:
        return []
    omvang = len({o.get("stof") for o in getroffen})
    return [_signaal("stof_buiten_register", "gemeten stof die in geen vergunning staat",
                      omvang, getroffen)]


def regel_vergunning_niet_te_vinden(vestiging: dict, context: dict) -> list[dict]:
    """Vergunning niet te vinden -- `url`, `kenmerk` of `besluitdatum` ontbreekt. `omvang` is
    hoeveel van de drie het zijn; pas als alle drie ontbreken is de vestiging niet meer te
    herleiden tot haar vergunningdocument, en weegt het signaal zwaar."""
    ontbrekend = [veld for veld in ("url", "kenmerk", "besluitdatum") if not vestiging.get(veld)]
    if not ontbrekend:
        return []
    bewijs = [{"veld": veld, "waarde": vestiging.get(veld)} for veld in ontbrekend]
    return [_signaal("vergunning_niet_te_vinden", "vergunning niet te vinden", len(ontbrekend),
                      bewijs)]


def regel_niet_regime_zuiver(vestiging: dict, context: dict) -> list[dict]:
    """Toets niet regime-zuiver -- de vergunning schrijft een bemonsteringsregime voor dat een
    meting niet meldt, dus een vergelijking van meting tegen deze grenswaarde is niet
    regime-zuiver. Dat is altijd zo zodra een voorschrift een regime draagt (de meting meldt het
    regime nooit, geverifieerd in het plan), en dus altijd `laag`: een voorbehoud, geen bevinding
    op zichzelf. Die `laag` komt uit de drempel-99-sentinel in `zwaarte()` zelf; hier gaat de
    echte telling de afleiding in, er wordt niets gefabriceerd."""
    getroffen = [v for v in (vestiging.get("voorschriften") or []) if v.get("bemonstering")]
    if not getroffen:
        return []
    return [_signaal("niet_regime_zuiver", "toets niet regime-zuiver", len(getroffen), getroffen)]


def regel_geen_geldigheidsduur(vestiging: dict, context: dict) -> list[dict]:
    """Geen geldigheidsduur -- de Atlas kent geen geldigheidsperiode per voorschrift, alleen een
    besluitdatum per vergunning (zie `kmg.lozingsmodel`). Dat geldt voor het hele dossier in één
    keer, dus precies één signaal per vestiging, nooit één per voorschrift. Ook deze regel weegt
    altijd `laag` via de drempel-99-sentinel in `zwaarte()`; `omvang` draagt hier gewoon de
    echte telling, hoeveel voorschriften het betreft."""
    voorschriften = vestiging.get("voorschriften") or []
    if not voorschriften:
        return []
    return [_signaal("geen_geldigheidsduur", "geen geldigheidsduur", len(voorschriften), [])]


REGELS: list[Regel] = [
    Regel("geen_onafhankelijke_meting", "geen onafhankelijke meting", "geen_onafhankelijke_meting",
          regel_geen_onafhankelijke_meting),
    Regel("vervallen_code", "grenswaarde op een ingetrokken code", "vervallen_code",
          regel_vervallen_code),
    Regel("niet_in_referentie", "parameter niet in de referentie", "niet_in_referentie",
          regel_niet_in_referentie),
    Regel("meerdere_grenswaarden", "welke grenswaarde geldt?", "meerdere_grenswaarden",
          regel_meerdere_grenswaarden),
    Regel("vracht_onbepaald", "vracht niet te bepalen", "vracht_onbepaald",
          regel_vracht_onbepaald),
    Regel("norm_overschreden_bovenstrooms", "meting boven de norm, lozer bovenstrooms",
          "norm_overschreden_bovenstrooms", regel_norm_overschreden_bovenstrooms),
    Regel("stof_buiten_register", "gemeten stof die in geen vergunning staat",
          "stof_buiten_register", regel_stof_buiten_register),
    Regel("vergunning_niet_te_vinden", "vergunning niet te vinden", "vergunning_niet_te_vinden",
          regel_vergunning_niet_te_vinden),
    Regel("niet_regime_zuiver", "toets niet regime-zuiver", "niet_regime_zuiver",
          regel_niet_regime_zuiver),
    Regel("geen_geldigheidsduur", "geen geldigheidsduur", "geen_geldigheidsduur",
          regel_geen_geldigheidsduur),
]

# Zwaarte-volgorde voor het rangschikken in `signalen()`. Oplopend, zodat "hoog" vooraan komt.
_ZWAARTE_RANG = {"hoog": 0, "midden": 1, "laag": 2}


def signalen(vestiging: dict, context: dict) -> list[dict]:
    """Alle regels op één vestiging, gerangschikt op zwaarte en dan op omvang (beide aflopend in
    ernst: hoog voor midden voor laag, en binnen een zwaarte de grootste omvang eerst)."""
    uit = []
    for regel in REGELS:
        uit.extend(regel.functie(vestiging, context))
    uit.sort(key=lambda s: (_ZWAARTE_RANG[s["zwaarte"]], -s["omvang"]))
    return uit
