"""Wat `/toezicht` toont — afgeleid van hetzelfde volledige signaaldossier als `/wasstraat`
(`toezicht.dossier.dossier()`), de spiegeling van `wasstraat.dossier.papier_dossier()` voor de
werkelijkheidslaag in plaats van de papierlaag (plan,
`docs/superpowers/plans/2026-11-14-wasstraat-en-toezicht-splitsen.md`).

**Waarom dit geen tweede dossier bouwt.** `toezicht.dossier.dossier()` berekent alle tien
signalen in één keer, met de context die `toezicht.context` heeft samengesteld (zie die module).
Deze module herhaalt die berekening niet: zij **filtert** het resultaat naar de drie
werkelijkheidssignalen (`signalen.Regel.laag == "werkelijkheid"`) en voegt twee dingen toe die
geen van de twee andere modules kan leveren:

- **`wasstraat`** — is het papier van déze vestiging op orde, en zo niet hoeveel bevindingen
  staan open. Geteld uit de **papierbevindingen** van datzelfde, al-berekende dossier (de vijf
  papierregels die geen sentinel zijn, zie `_is_papierbevinding`), niet door de
  wasstraat-pijplijn nog een keer te draaien: de zeven papierregels hebben geen context nodig
  (dat is precies waarom zij op `/wasstraat` staan) en vuren dus identiek, met of zonder de
  context die deze route voor de drie werkelijkheidsregels aanlevert. Dit is **context voor de
  inspecteur, geen opdracht** — een vergunning die niet handhaafbaar is opgeschreven, verandert
  wat een bezoek kan opleveren, en dat mag een inspecteur weten vóór hij gaat kijken.
- **`metingen`**/**`kaart.waterlichaam`** — komen niet uit `dossier()` maar worden door de
  aanroeper (`geluidsmeter.api.api_toezicht_dossier`) aangeleverd, want zij komen uit
  `toezicht.context`, niet uit de signaalmotor. `werkelijkheid_dossier()` voegt ze hier samen
  met de gefilterde signalen tot één antwoord, zodat de pagina niet drie aparte aanroepen nodig
  heeft.

**De runlog en de voorbehouden blijven ongewijzigd.** Anders dan `/wasstraat` (dat een
runlog-samenvatting en per-stap-uitleg toevoegt) vraagt de taakbrief voor `/toezicht` geen van
beide — de drie delen van deze pagina zijn de wasstraat-uitkomst, de metingen en de signalen, niet
een uitgelegde keten. `voorbehouden` komt ongewijzigd uit `dossier()` door: geen van die zinnen
noemt een papierregel bij naam (anders dan bij `/wasstraat`, waar `_voorbehouden_papier` net de
wérkelijkheidsgerelateerde zinnen moest wegfilteren), dus hier is niets te filteren.
"""
from collections import Counter

from leefomgevinglab.usecases.kmg.lozingsmodel import ZEKERHEDEN
from leefomgevinglab.usecases.toezicht import signalen as signalen_mod

_, AFGELEID, _AANGENOMEN, ONTBREEKT = ZEKERHEDEN


def _is_werkelijkheid(regel_id: str) -> bool:
    """Afgeleid uit `signalen.REGELS`, niet een tweede keer getypt — zie de moduledocstring van
    `signalen.py` en `Regel.laag`. Zelfde patroon als `wasstraat.dossier._is_papier`, hier voor
    de andere laag."""
    for regel in signalen_mod.REGELS:
        if regel.id == regel_id:
            return regel.laag == "werkelijkheid"
    return False


def _telling_werkelijkheid(signalen_lijst: list[dict], aantal_voorschriften: int | None) -> dict:
    """Zelfde vorm als `toezicht.dossier._telling`/`wasstraat.dossier._telling_papier`, maar
    uitsluitend over de gefilterde (werkelijkheids-)lijst — anders telt dit dossier zeven
    signalen mee die deze pagina niet toont."""
    per_zwaarte = Counter(s["zwaarte"] for s in signalen_lijst)
    per_regel = Counter(s["regel"] for s in signalen_lijst)
    return {
        "aantal_voorschriften": aantal_voorschriften,
        "aantal_signalen": len(signalen_lijst),
        "aantal_regels_die_vuurden": len(per_regel),
        "per_zwaarte": {z: per_zwaarte.get(z, 0) for z in ("hoog", "midden", "laag")},
        "per_regel": dict(per_regel),
    }


def _is_papierbevinding(regel_id: str) -> bool:
    """Een papierregel die iets over **deze** vergunning beweert.

    **Eindreview, must-fix 5+6.** Hier stond eerder alleen `not _is_werkelijkheid(...)`, en
    daardoor telden twee sentinelregels mee die op bijna elke vergunning in het register vuren:
    `geen_geldigheidsduur` op 69 van de 69 (de Atlas kent geen geldigheidsperiode per voorschrift)
    en `niet_regime_zuiver` op 68 van de 69 (de regel vuurt juist als het regime er staat). Het
    minimum over het hele register was daarmee 1 en `op_orde` was onbereikbaar — de True-tak op
    `toezicht.html` was dode code. Erger: een inspecteur die "13 open" tegen "5 open" legde, las
    een rangorde waarvan 2 van elk getal een register-brede constante was en dus niets over die
    vergunning zei. De tweede as (`signalen.is_voorbehoud`, afgeleid uit de `ALTIJD_LAAG`-drempel)
    houdt die twee er nu buiten; zij staan op `/wasstraat` in het voorbehouden-blok, zie
    `wasstraat.dossier`."""
    return not _is_werkelijkheid(regel_id) and not signalen_mod.is_voorbehoud(regel_id)


def wasstraat_samenvatting(alle_signalen: list[dict]) -> dict:
    """Is het papier van deze vestiging op orde, en zo niet hoeveel bevindingen staan open —
    geteld uit de **papierbevindingen** van het al-berekende volledige dossier (`alle_signalen`,
    alle tien), niet door de wasstraat-pijplijn nog een keer te draaien. Context voor de
    inspecteur, geen opdracht: de pagina presenteert dit als één regel met een link, nooit als een
    oordeel over of er bezocht moet worden.

    De twee sentinelregels tellen hier niet mee — zie `_is_papierbevinding` voor waarom dat het
    verschil maakt tussen een getal dat over deze vergunning gaat en een getal dat over het
    register gaat."""
    aantal_open = sum(1 for s in alle_signalen if _is_papierbevinding(s["regel"]))
    return {"op_orde": aantal_open == 0, "aantal_open": aantal_open, "pad": "/wasstraat"}


def werkelijkheid_dossier(volledig: dict, waterlichaam: str | None = None,
                           waterlichaam_reden: str | None = None,
                           metingen_rijen: list[dict] | None = None) -> dict:
    """Het dossier voor `/toezicht`: het volledige signaaldossier
    (`toezicht.dossier.dossier()`, na een echte run van de standaardpijplijn met de context uit
    `toezicht.context`), gefilterd naar de drie werkelijkheidssignalen en aangevuld met de
    wasstraat-uitkomst en de metingen bij het waterlichaam van deze vestiging.

    `kaart` komt ongewijzigd door, behalve het veld `waterlichaam`: `dossier()` zelf kan dat veld
    alleen rechtstreeks van `vestiging` lezen (en de Atlas draagt dat veld nooit, zie
    `dossier._kaart`), dus deze functie zet het hier op `waterlichaam`/`waterlichaam_reden` met
    zekerheid `afgeleid` — het is geen directe lezing van de bron maar het resultaat van een
    coördinaatopzoeking (`toezicht.context.waterlichaam_van_vestiging`)."""
    signalen_lijst = [s for s in (volledig.get("signalen") or []) if _is_werkelijkheid(s["regel"])]
    aantal_voorschriften = (volledig.get("telling") or {}).get("aantal_voorschriften")

    kaart = dict(volledig.get("kaart") or {})
    kaart["waterlichaam"] = ({"waarde": waterlichaam, "zekerheid": AFGELEID} if waterlichaam
                              else {"waarde": None, "zekerheid": ONTBREEKT})

    return {
        "kaart": kaart,
        "wasstraat": wasstraat_samenvatting(volledig.get("signalen") or []),
        "signalen": signalen_lijst,
        "telling": _telling_werkelijkheid(signalen_lijst, aantal_voorschriften),
        "voorbehouden": volledig.get("voorbehouden") or [],
        "runlog": volledig.get("runlog") or {"uitgezet": [], "stappen": []},
        "metingen": {
            "waterlichaam": waterlichaam,
            "reden_geen_waterlichaam": None if waterlichaam else waterlichaam_reden,
            "rijen": metingen_rijen or [],
        },
    }
