"""Het beeld op een locatie: regels, vergunningen en de ruimte die overblijft."""
from concurrent.futures import ThreadPoolExecutor

from leefomgevinglab.usecases.lozing_keten import bronnen as water_bronnen

from . import atlas_register, gebied, regels, ruimte, waterprofiel

MAX_DEBIET = 20_000          # m³/uur; begrenst wat de gebruiker kan vragen

# Concentraties van het voornemen (mg/l), gelijk aan de lozingscasus op /lozing.
VOORNEMEN_CONCENTRATIES = {
    "stikstof totaal": 2.47, "zink": 0.0125, "AOX": 0.084, "PFOA": 0.00024,
}

VERANTWOORDING = ("Regelingen live uit het DSO. Het register met bestaande vergunningen bestaat "
                  "landelijk niet; voor het Maasstroomgebied komt het live uit de Atlas voor een "
                  "Schone Maas, daarbuiten is het synthetisch. Normen en achtergrondconcentraties "
                  "zijn illustratief. Het mechanisme is echt, de cijfers niet.")

# Welke informatiefuncties deze case aantoont, en waaraan je dat ziet.
INFORMATIEFUNCTIES = [
    {"nr": 5, "naam": "Lokaliseren en ruimtelijk duiden",
     "hoe": "De regels worden op het RD-punt opgehaald en het ontvangende waterlichaam wordt "
            "afgeleid uit de KRW-service — beide live."},
    {"nr": 4, "naam": "Beschikbaar stellen en delen",
     "hoe": "De regelingen komen als API-antwoord uit het DSO in plaats van als pdf."},
    {"nr": 8, "naam": "Kennis ontsluiten en verklaren",
     "hoe": "Per regeling staat er wat hij voor dít voornemen betekent, inclusief de regelingen "
            "die hier wél gelden maar deze lozing niet raken."},
    {"nr": 3, "naam": "Registreren en beheren",
     "hoe": "De bestaande vergunningen komen uit een register dat niet bestaat; hier nagebootst "
            "om te laten zien wat het zou opleveren."},
    {"nr": 6, "naam": "Analyseren en signaleren",
     "hoe": "De cumulatie: de ruimte tot de norm afgezet tegen wat er al vergund is, per parameter."},
]


def voornemen(debiet_m3_per_uur: float) -> dict:
    debiet = max(1.0, min(float(debiet_m3_per_uur), MAX_DEBIET))
    return {"soort": "directe lozing van koel- en gezuiverd proceswater",
            "debiet_m3_per_uur": debiet, "concentraties": dict(VOORNEMEN_CONCENTRATIES)}


def _atlas_standaard(x: float, y: float, straal_m: int):
    """De echte Atlas-bevraging; los gehouden zodat de tests hem kunnen vervangen."""
    from leefomgevinglab.connectors.smwk_atlas import SmwkAtlasConnector
    from leefomgevinglab.geluidsmeter.config import load_config
    cfg = load_config().get("leefomgevinglab", {})
    at = cfg.get("smwk_atlas", {})
    c = SmwkAtlasConnector(cache_dir=cfg.get("cache_dir", "/tmp/llab_cache"),
                           cache_ttl=at.get("cache_ttl_s", 86400),
                           base_url=at.get("base_url") or None)
    return c.vergunningen_bij_punt(x, y, straal_m=straal_m)


def _register(x, y, owl_id, straal_m, live, haal) -> tuple[list, dict]:
    """Echte vergunningen waar ze bestaan, synthetische waar dat niet zo is."""
    if not live:
        return list(gebied.REGISTER), {
            "echt": False, "status": "overgeslagen",
            "reden": "zonder live-modus wordt de Atlas niet bevraagd",
            "bron": {"naam": "synthetisch register van dit lab"}}
    try:
        posten = (haal or _atlas_standaard)(x, y, straal_m)
    except Exception as exc:
        return list(gebied.REGISTER), {
            "echt": False, "status": "onbereikbaar", "fout": type(exc).__name__,
            "reden": "de Atlas was niet bereikbaar; teruggevallen op het synthetische register",
            "bron": {"naam": "synthetisch register van dit lab"}}

    if posten:
        d = atlas_register.naar_register(posten)
        return d["register"], {"echt": True, "status": "ok", "telling": d["telling"],
                               "bevinding": d["bevinding"], "bron": d["bron"]}

    if owl_id == "NL93_IJSSEL":
        return list(gebied.REGISTER), {
            "echt": False, "status": "ok",
            "reden": "geen vergunningen in de Atlas: die dekt alleen het Maasstroomgebied. Voor "
                     "de IJssel valt dit lab terug op een synthetisch register — precies het gat "
                     "dat een landelijk register zou vullen.",
            "bron": {"naam": "synthetisch register van dit lab"}}

    return [], {"echt": False, "status": "ok",
                "reden": "geen register voor dit waterlichaam. Buiten het Maasstroomgebied "
                         "bestaat er geen overzicht van wie hier al loost.",
                "bron": {"naam": "geen"}}


def beeld_op_punt(x: float, y: float, debiet_m3_per_uur: float = 420, live: bool = True,
                  naam: str | None = None, straal_m: int = 5000,
                  _haal_regels=None, _haal_water=None, _haal_atlas=None) -> dict:
    """Alles bij elkaar op één punt: waar ben ik, wat geldt hier, wat ligt er al, wat kan er nog?"""
    # Drie sporen die niets van elkaar nodig hebben; serieel zou elke prik seconden kosten.
    # De regels hebben `rijkswater` alleen nodig voor hun duiding, niet voor de bevraging —
    # ze worden daarom vast met rijkswater=True opgehaald en, als dat straks niet blijkt te
    # kloppen, hieronder opnieuw geduid. `regels.duiding()` raakt geen netwerk, dus die
    # her-duiding is goedkoop; zou dat ooit veranderen, dan moet deze parallellisatie om.
    with ThreadPoolExecutor(max_workers=3) as pool:
        f_water = pool.submit(water_bronnen.contextset, x, y, straal_m=1000, live=live,
                              haal=_haal_water)
        f_regels = pool.submit(regels.regels_op_locatie, x, y, rijkswater=True, live=live,
                               _haal=_haal_regels)
        water = f_water.result()
        rijkswater = bool(water.get("rijkswater")) if live else True
        f_register = pool.submit(_register, x, y, water.get("owl_id"), straal_m, live, _haal_atlas)
        r = f_regels.result()
        register, register_bron = f_register.result()

    if not rijkswater:
        # De duiding van de waterschapsverordening kantelt op regionaal water: van "niet van
        # toepassing" naar "direct werkend". De regelingen worden opnieuw geduid en de telling
        # via dezelfde functie als `regels_op_locatie` opnieuw bepaald, zodat de getoonde
        # telling weer bij de getoonde regelingen past.
        geduid = [regels.duiding({"titel": g["titel"], "type": g["type"],
                                  "bevoegd_gezag": g["bevoegd_gezag"]}, rijkswater)
                 for g in r.get("regelingen", [])]
        regelingen, telling = regels.samenvatten(geduid)
        r = {**r, "regelingen": regelingen, "telling": telling}

    v = voornemen(debiet_m3_per_uur)
    p = waterprofiel.profiel(water)

    if p.get("afgeleid"):
        u = ruimte.bereken(v, register, waterprofiel.als_waterlichaam(p))
        geen_ruimte_reden = None
    else:
        u = None
        geen_ruimte_reden = p.get("reden")

    return {
        "locatie": {"naam": naam or "gekozen punt", "rd": [x, y],
                    "gemeente": water.get("gemeente"), "provincie": water.get("provincie")},
        "water": {**p["echt"], "profiel": p, "live": water},
        "rijkswater": rijkswater,
        "bevoegd_gezag": water_bronnen.bevoegd_gezag(water),
        "regels": r,
        "register": register,
        "register_bron": register_bron,
        "voornemen": v,
        "ruimte": u,
        "geen_ruimte_reden": geen_ruimte_reden,
        "informatiefuncties": INFORMATIEFUNCTIES,
        "max_debiet": MAX_DEBIET,
        "verantwoording": VERANTWOORDING,
    }


def beeld(locatie_id: str, debiet_m3_per_uur: float = 420, live: bool = True,
          _haal_regels=None, _haal_water=None) -> dict:
    """De gecureerde drieluik-variant: een vaste locatie aan de IJssel.

    Dunne wrapper om `beeld_op_punt`, met het vaste IJssel-waterlichaam en -register in plaats
    van een afgeleid profiel — zodat /gebruiksruimte precies blijft antwoorden wat hij altijd al
    antwoordde.
    """
    loc = gebied.LOCATIES[locatie_id]                 # KeyError bij onbekende locatie: luid falen
    x, y = loc["rd"]

    water = water_bronnen.contextset(x, y, straal_m=1000, live=live, haal=_haal_water)
    rijkswater = bool(water.get("rijkswater")) if live else True
    r = regels.regels_op_locatie(x, y, rijkswater=rijkswater, live=live, _haal=_haal_regels)
    v = voornemen(debiet_m3_per_uur)
    u = ruimte.bereken(v, gebied.REGISTER, gebied.WATERLICHAAM)

    return {
        "locatie": {**loc, "rd": list(loc["rd"])},
        "water": {**gebied.WATERLICHAAM, "live": water},
        "rijkswater": rijkswater,
        "bevoegd_gezag": water_bronnen.bevoegd_gezag(water),
        "regels": r,
        "register": gebied.REGISTER,
        "voornemen": v,
        "ruimte": u,
        "informatiefuncties": INFORMATIEFUNCTIES,
        "locaties": list(gebied.LOCATIES.values()),
        "max_debiet": MAX_DEBIET,
        "verantwoording": VERANTWOORDING,
    }
