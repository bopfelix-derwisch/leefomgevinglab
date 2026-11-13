"""De tien signaalregels op het vergunningenregister van de Atlas voor een Schone Maas.

Elke regel is een gewone functie `(vestiging, context) -> list[dict]`: geen netwerk, geen
taalmodel, alleen wat er in `vestiging` (en voor de drie regels uit taak 2: `context`) binnenkomt.
Dat maakt een signaal auditeerbaar -- het is terug te herleiden tot een regel en een bronrij, niet
tot een taalmodel dat "iets zag".

Dit bestand bouwt de zeven regels die aan de vergunning zelf genoeg hebben:

- `vervallen_code` (2), `niet_in_referentie` (3), `meerdere_grenswaarden` (4),
  `vracht_onbepaald` (5), `vergunning_niet_te_vinden` (8), `niet_regime_zuiver` (9),
  `geen_geldigheidsduur` (10).

De drie regels die meetdata en stroomrichting nodig hebben (`geen_onafhankelijke_meting`,
`norm_overschreden_bovenstrooms`, `stof_buiten_register`) komen er in een volgende taak bij --
`DREMPELS` heeft hun drempel al klaarstaan en `REGELS` is de plek waar hun `Regel` bij komt.

**Een signaal is nooit een vaststelling.** De woorden "overtreding", "veroorzaakt door" en "in
strijd met" komen in geen signaaltekst voor -- een regel vraagt aandacht, constateert geen
schending. Dat is dezelfde taalregel als `/kmg` (`usecases/kmg/proclaimer.py`), hier toegepast op
een vergunning in plaats van een meting.
"""
from typing import Callable, NamedTuple

# Een voorschrift met een van deze eenheden is een concentratiegrens. Zonder een debietvoorschrift
# (zie DEBIET_EENHEDEN) ergens in dezelfde vestiging is zo'n grens niet naar een vracht om te
# rekenen -- dat is regel 5.
CONCENTRATIE_EENHEDEN = {"milligram per liter", "microgram per liter"}
DEBIET_EENHEDEN = {"kubieke meter per uur", "kubieke meter per dag"}

# Sentinel voor "nog niet opgezocht": ontbreekt de sleutel `aquo` op een voorschrift, dan heeft
# niemand geprobeerd deze naam aan een code te koppelen en is er niets te signaleren. Pas een
# expliciete waarde `None` (de koppeling is geprobeerd en mislukt) telt als signaal.
_NIET_OPGEZOCHT = object()


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


def zwaarte(regel_id: str, omvang: float, norm_aanwezig: bool = False) -> str:
    """Afgeleid, nooit getypt.

    Wat `omvang` betekent verschilt per regel en staat in `DREMPELS` -- bij regel 4 is het de
    verhouding tussen de hoogste en de laagste grenswaarde, bij regel 1 een aantal
    voorschriften. Een onbekende regel werpt een KeyError in plaats van stil `laag` te geven:
    een nieuwe regel zonder drempel is een vergeten keuze, niet een lichte bevinding.
    """
    drempel, _ = DREMPELS[regel_id]
    if omvang >= drempel:
        return "hoog" if norm_aanwezig or drempel < 99 else "midden"
    return "midden" if omvang > 0 else "laag"


def _signaal(regel_id: str, kop: str, omvang: float, bewijs: list[dict],
             norm_aanwezig: bool = False, omvang_voor_zwaarte: float | None = None) -> dict:
    """Eén signaal in de vaste vorm. `omvang` bepaalt wat er getoond en op gerangschikt wordt.

    Voor de meeste regels bepaalt die omvang ook de zwaarte via `zwaarte()`. Voor de twee regels
    met drempel 99 (`niet_regime_zuiver`, `geen_geldigheidsduur`) is de telling zelf niet de maat
    -- zij wegen per ontwerp altijd `laag` -- en geeft `omvang_voor_zwaarte=0` dat door aan
    `zwaarte()`, zonder de getoonde `omvang` te veranderen.
    """
    maat = omvang if omvang_voor_zwaarte is None else omvang_voor_zwaarte
    return {"regel": regel_id, "signaal": kop,
            "zwaarte": zwaarte(regel_id, maat, norm_aanwezig),
            "omvang": omvang, "bewijs": bewijs}


def regel_meerdere_grenswaarden(vestiging: dict, context: dict) -> list[dict]:
    """Welke grenswaarde geldt? -- dezelfde parameter met meer dan één grenswaarde in één
    vestiging. `omvang` is de verhouding hoogste / laagste; daar is geen drempel op getallen voor
    nodig, de verhouding zelf is de maat."""
    per_parameter: dict[str, list[dict]] = {}
    for v in vestiging.get("voorschriften") or []:
        per_parameter.setdefault(v.get("parameter"), []).append(v)

    uit = []
    for parameter, voorschriften in per_parameter.items():
        waarden = {v["waarde"] for v in voorschriften if v.get("waarde") is not None}
        if len(waarden) < 2:
            continue
        omvang = max(waarden) / min(waarden)
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
    op zichzelf. Daarom gaat niet de telling maar een vaste `0` de zwaarte-afleiding in; de
    telling zelf blijft wel zichtbaar in `omvang`."""
    getroffen = [v for v in (vestiging.get("voorschriften") or []) if v.get("bemonstering")]
    if not getroffen:
        return []
    return [_signaal("niet_regime_zuiver", "toets niet regime-zuiver", len(getroffen), getroffen,
                      omvang_voor_zwaarte=0)]


def regel_geen_geldigheidsduur(vestiging: dict, context: dict) -> list[dict]:
    """Geen geldigheidsduur -- de Atlas kent geen geldigheidsperiode per voorschrift, alleen een
    besluitdatum per vergunning (zie `kmg.lozingsmodel`). Dat geldt voor het hele dossier in één
    keer, dus precies één signaal per vestiging, nooit één per voorschrift. Ook hier gaat een
    vaste `0` de zwaarte-afleiding in: het is geen telling die ergens boven een drempel kan
    uitkomen -- `omvang` toont wel hoeveel voorschriften het betreft."""
    voorschriften = vestiging.get("voorschriften") or []
    if not voorschriften:
        return []
    return [_signaal("geen_geldigheidsduur", "geen geldigheidsduur", len(voorschriften), [],
                      omvang_voor_zwaarte=0)]


REGELS: list[Regel] = [
    Regel("vervallen_code", "grenswaarde op een ingetrokken code", "vervallen_code",
          regel_vervallen_code),
    Regel("niet_in_referentie", "parameter niet in de referentie", "niet_in_referentie",
          regel_niet_in_referentie),
    Regel("meerdere_grenswaarden", "welke grenswaarde geldt?", "meerdere_grenswaarden",
          regel_meerdere_grenswaarden),
    Regel("vracht_onbepaald", "vracht niet te bepalen", "vracht_onbepaald",
          regel_vracht_onbepaald),
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
