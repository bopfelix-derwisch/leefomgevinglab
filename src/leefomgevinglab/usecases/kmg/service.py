"""De drie lagen van de DSO-folder, samengevoegd voor één meetpunt.

Kan — de regelingen die op het meetpunt gelden, live uit het DSO.
Mag — de vergunningen op dit waterlichaam en bovenstrooms, live uit de Atlas.
Gebeurt — de gemeten waarden uit de verdichte WKP-set.

En daarna de vraag die de folder stelt: ligt het gemeten boven de norm, welke vergunningen
kunnen dan bijdragen? Het antwoord daarop is een bovengrens, geen vaststelling — zie
`toerekening.py`.
"""
from leefomgevinglab.usecases.gebruiksruimte import atlas_register, regels

from . import metingen, proclaimer, toerekening

# Jaarafvoer per Maas-waterlichaam, m3/s. Keuze van dit lab: de KRW-service levert geen
# afvoergegevens. Orde van grootte van de Maas bij gemiddelde afvoer.
DEBIET_M3_S = {
    "NL91BOM": 230.0, "NL91GM": 240.0, "NL91ZM": 250.0, "NL91BM": 260.0,
    "NL94_5": 270.0, "NL94_6": 280.0, "NL94_1": 300.0, "NL94_11": 310.0,
}
STANDAARD_DEBIET = 250.0


def meetpunten(pad: str) -> list[dict]:
    """De beschikbare meetpunten, stroomafwaarts gesorteerd."""
    set_ = metingen.laad(pad)
    volgorde = {c: i for i, (c, _n) in enumerate(toerekening.STROOMVOLGORDE)}
    punten = metingen.punten(set_, waterlichamen=list(volgorde))
    namen = dict(toerekening.STROOMVOLGORDE)
    for p in punten:
        p["waterlichaam_naam"] = namen.get(p.get("waterlichaam"), "")
    punten.sort(key=lambda p: (volgorde.get(p.get("waterlichaam"), 99), p["code"]))
    return punten


def _atlas_standaard(x: float, y: float, straal_m: int):
    from leefomgevinglab.connectors.smwk_atlas import SmwkAtlasConnector
    from leefomgevinglab.geluidsmeter.config import load_config
    cfg = load_config().get("leefomgevinglab", {})
    at = cfg.get("smwk_atlas", {})
    c = SmwkAtlasConnector(cache_dir=cfg.get("cache_dir", "/tmp/llab_cache"),
                           cache_ttl=at.get("cache_ttl_s", 86400),
                           base_url=at.get("base_url") or None)
    return c.vergunningen_bij_punt(x, y, straal_m=straal_m)


def beeld(code: str, pad: str, live: bool = True, straal_m: int = 50000,
          _haal_regels=None, _haal_atlas=None,
          toestaan_zonder_meetpunt: bool = False) -> dict:
    """Kan, mag en gebeurt op één meetpunt."""
    set_ = metingen.laad(pad)
    if set_.get("beschikbaar"):
        punt = metingen.punt(set_, code)        # KeyError bij onbekende code
    elif toestaan_zonder_meetpunt:
        punt = {"code": code, "naam": "(geen meetset)", "rd": None,
                "waterlichaam": None, "stoffen": []}
    else:
        raise KeyError(code)

    x, y = (punt.get("rd") or [None, None])
    wl = punt.get("waterlichaam")

    # Kan — de regels op het meetpunt
    if live and x is not None:
        kan = regels.regels_op_locatie(x, y, rijkswater=True, live=True, _haal=_haal_regels)
    else:
        kan = {"live": False, "status": "overgeslagen", "regelingen": [],
               "bron": regels.BRON, "telling": {}}

    # Mag — de vergunningen in de buurt, omgerekend naar vrachten
    if live and x is not None:
        try:
            posten = (_haal_atlas or _atlas_standaard)(x, y, straal_m)
            reg = atlas_register.naar_register(posten)
            mag = {"status": "ok", **reg}
        except Exception as exc:                 # noqa: BLE001 — bron mag wegvallen
            mag = {"status": "onbereikbaar", "fout": type(exc).__name__,
                   "register": [], "telling": {}, "bron": {}, "echt": False}
    else:
        mag = {"status": "overgeslagen", "register": [], "telling": {},
               "bron": {}, "echt": False}

    # Gebeurt — de metingen
    gebeurt = {"beschikbaar": bool(set_.get("beschikbaar")),
               "reden": set_.get("reden", ""), "meetjaar": set_.get("meetjaar"),
               "stoffen": punt.get("stoffen") or []}

    # De vraag: wie kan bijdragen? Alleen zinvol met een meting én vergunningen.
    debiet = DEBIET_M3_S.get(wl, STANDAARD_DEBIET)
    wl_per_post = {p.get("kenmerk"): wl for p in (mag.get("register") or []) if p.get("kenmerk")}
    vraag = []
    for stof in gebeurt["stoffen"]:
        naam = stof.get("naam")
        d = toerekening.bijdragen(stof.get("mediaan") or 0.0, naam,
                                  mag.get("register") or [], wl or "", wl_per_post, debiet,
                                  eenheid=stof.get("eenheid") or "mg/l")
        vraag.append({"stof": stof.get("code"), "naam": naam, **d})

    # Hoeveel van de meetset daadwerkelijk in deze keuzelijst staat (zie meetpunten()) — de
    # proclaimer mag niet een hoger aantal beweren dan wat er na filtering overblijft.
    in_beeld = len(metingen.punten(
        set_, waterlichamen=[c for c, _n in toerekening.STROOMVOLGORDE])
    ) if set_.get("beschikbaar") else 0

    return {
        "meetpunt": {**punt,
                     "waterlichaam_naam": dict(toerekening.STROOMVOLGORDE).get(wl, "")},
        "kan": kan,
        "mag": mag,
        "gebeurt": gebeurt,
        "bijdragen": vraag,
        "proclaimer": proclaimer.bouw(set_, mag, regels.BRON, doelen_beschikbaar=False,
                                      punten_in_beeld=in_beeld),
    }
