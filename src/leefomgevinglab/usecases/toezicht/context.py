"""De context die de drie werkelijkheidsregels nodig hebben (`signalen.
regel_geen_onafhankelijke_meting`, `regel_norm_overschreden_bovenstrooms`,
`regel_stof_buiten_register`), en de meetgegevens die `/toezicht` naast die drie signalen toont.

Vóór deze module gaf `/api/toezicht/dossier` die drie regels `context: {}` mee (afgezien van
`stoffen_met_norm`, zie `graaf.stoffen_met_norm`): geen van de drie kon ooit vuren, want
`gemeten_codes`, `waterlichaam`, `overschrijdingen` en `register_codes` ontbraken stuk voor stuk.
Deze module vult ze, allemaal uit bronnen die dit lab al elders gebruikt (`/kmg`) — er wordt hier
niets nieuws bevraagd, alleen samengebracht.

**`gemeten_codes`** komt uit `kmg.metingen.laad_codes()` (`scripts/21_fetch_wkp_gemeten_codes.py`)
— een verdichting van de Aquo-codes die voorkomen op de meetpunten die dit lab al kent, niet de
**waarden** van drie stoffen die `kmg.metingen.laad()` (`scripts/13`) levert. Dat onderscheid is
de valkuil die deze module expliciet vermijdt: die verdichte waardenset bevat maar drie stoffen
(Ntot/Zn/PFOA), dus daaruit lezen zou bijna elke andere stof onterecht "nooit gemeten" noemen —
precies de valkuil die de taakbrief voor deze pagina benoemde.

**`waterlichaam`** van de gekozen vestiging komt uit haar eigen coördinaat
(`kmg.service._waterlichaam_per_vergunning`), met één vestiging in een lijst van één — exact
dezelfde functie die `/kmg` gebruikt om elke vergunning in het hele register haar waterlichaam te
geven, hergebruikt in plaats van opnieuw geschreven.

**`overschrijdingen`** toetst elke gemeten stof op elk meetpunt tegen haar norm (`kmg.doelen.
toets`, die zelf al kiest tussen het jaargemiddelde (chemische norm, zink) en het zomergemiddelde
(ecologisch doel, stikstof) — deze module voegt daar geen eigen keuze van grootheid aan toe, zij
roept `toets()` aan zoals `/kmg` dat al doet, en leest de uitkomst af in plaats van zelf te
toetsen. "Overschreden" betekent hier `oordeel["ruimte"] < 0` — hetzelfde teken dat `doelen.py`
zelf al gebruikt ("positief: nog ruimte tot de norm, negatief: de waarde zit daar al boven").

**Eén toetsing, twee weergaven.** `toetsing()` berekent dit voor elk meetpunt en elke stof,
ongefilterd. `overschrijdingen()` filtert die tabel voor de context van de signalen;
`metingen_bij_waterlichaam()` filtert ze voor de metingensectie van de pagina (alle metingen bij
het waterlichaam van déze vestiging, niet alleen de overschreden). Zo kunnen de twee weergaven
nooit tegen elkaar in lopen — er is maar één berekening om tegen te lezen."""
from leefomgevinglab.usecases.kmg import doelen as doelen_mod
from leefomgevinglab.usecases.kmg import service as kmg_service
from leefomgevinglab.usecases.kmg import toerekening


def is_overschreden(oordeel: dict | None) -> bool:
    """`True` als dit oordeel een overschrijding is — `ruimte < 0`, hetzelfde teken dat
    `doelen.chemisch`/`doelen.toets` al gebruiken. Geen oordeel (`beschikbaar` onwaar), of een
    oordeel zonder `ruimte`, is geen overschrijding maar een ontbrekend gegeven — niet gokken."""
    if not oordeel or not oordeel.get("beschikbaar"):
        return False
    ruimte = oordeel.get("ruimte")
    return ruimte is not None and ruimte < 0


def toetsing(punten: list[dict], doelenset: dict, normenset: dict) -> list[dict]:
    """Elke gemeten stof op elk meetpunt getoetst tegen haar norm (`doelen.toets`) — de ruwe
    tabel waaruit zowel `overschrijdingen()` als `metingen_bij_waterlichaam()` worden afgeleid.
    Geen filter hier: filteren is de taak van die twee functies, niet van deze."""
    uit = []
    for punt in punten or []:
        for stof in punt.get("stoffen") or []:
            oordeel = doelen_mod.toets(doelenset, punt.get("waterlichaam"), stof,
                                        normenset=normenset, meetpunt=punt.get("code"))
            uit.append({"meetpunt": punt.get("code"), "meetpunt_naam": punt.get("naam"),
                        "waterlichaam": punt.get("waterlichaam"), "stof": stof,
                        "oordeel": oordeel})
    return uit


def overschrijdingen(getoetst: list[dict]) -> list[dict]:
    """De vorm die `signalen.regel_norm_overschreden_bovenstrooms` en
    `signalen.regel_stof_buiten_register` verwachten: minstens `meetpunt`, `waterlichaam`,
    `stof`, `gemeten`, `norm`, `eenheid` (zie die regels' eigen docstrings)."""
    uit = []
    for r in getoetst:
        oordeel = r["oordeel"]
        if not is_overschreden(oordeel):
            continue
        stof = r["stof"]
        uit.append({
            "meetpunt": r["meetpunt"], "waterlichaam": r["waterlichaam"],
            "stof": stof.get("code"), "stof_naam": stof.get("naam"),
            "hoedanigheid": stof.get("hoedanigheid"),
            "gemeten": oordeel.get("getoetste_waarde"), "norm": oordeel.get("goed_tot"),
            "eenheid": oordeel.get("eenheid"), "grondslag": oordeel.get("grondslag"),
            "soort": oordeel.get("soort"),
        })
    return uit


def metingen_bij_waterlichaam(getoetst: list[dict], waterlichaam: str | None) -> list[dict]:
    """De getoetste rijen die bij dit waterlichaam horen — alle, niet alleen de overschreden: de
    metingensectie van de pagina toont de metingen zelf, niet alleen de signalen die erop
    vuren. Zonder bekend waterlichaam (`waterlichaam` is `None`) is er niets te tonen."""
    if not waterlichaam:
        return []
    return [r for r in getoetst if r.get("waterlichaam") == waterlichaam]


def waterlichaam_van_vestiging(vestiging: dict, live: bool = True, haal=None,
                                _haal_waterlichaam=None) -> tuple[str | None, str | None]:
    """owl_id van déze ene vestiging (of `None`), en als er geen is, de reden — hergebruikt
    `kmg_service._waterlichaam_per_vergunning` met een lijst van één vestiging. Dezelfde functie
    die `/kmg` gebruikt om elke vergunning in het hele register haar waterlichaam te geven (zie
    `kmg.service.stroomprofiel`), hier toegepast op één vestiging in plaats van op het register.

    Twee testinjectiepunten, allebei rechtstreeks doorgegeven aan
    `_waterlichaam_per_vergunning` zonder hier een nieuw mechanisme te verzinnen: `haal` is de
    lage-niveau fetch die `kmg_service._waterlichaam_opzoeken` gebruikt, `_haal_waterlichaam`
    vervangt de hele opzoeking `(x, y) -> owl_id | None` en slaat WFS/`contextset` helemaal
    over — dat tweede is voor deze module het handigste injectiepunt, want het bewijst alleen
    dat de sleutel- en resultaatroute klopt, niet of het WFS-pad bereikbaar is."""
    per_sleutel, redenen = kmg_service._waterlichaam_per_vergunning(
        [vestiging], live, haal=haal, _haal_waterlichaam=_haal_waterlichaam)
    sleutel = toerekening.sleutel_post(vestiging, 0)
    return per_sleutel.get(sleutel), redenen.get(sleutel)
