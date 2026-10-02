"""De drie lagen van de DSO-folder, samengevoegd voor één meetpunt.

Kan — de regelingen die op het meetpunt gelden, live uit het DSO.
Mag — de vergunningen op dit waterlichaam en bovenstrooms, live uit de Atlas.
Gebeurt — de gemeten waarden uit de verdichte WKP-set.

En daarna de vraag die de folder stelt: ligt het gemeten boven de norm, welke vergunningen
kunnen dan bijdragen? Het antwoord daarop is een bovengrens, geen vaststelling — zie
`toerekening.py`.
"""
from concurrent.futures import ThreadPoolExecutor

from leefomgevinglab.usecases.gebruiksruimte import atlas_register, regels

from . import metingen, proclaimer, toerekening

# Straal voor de KRW-opzoeking per vergunning: klein, want het gaat om het waterlichaam ván die
# ene coördinaat, niet om een omgeving. Los te zien van `straal_m` in `beeld()`, dat de Atlas
# afzoekt naar vergunningen in de buurt van het meetpunt.
_WATERLICHAAM_STRAAL_M = 250
# Afronding voor het ontdubbelen van vergunningcoördinaten vóór de opzoeking ("op een paar
# meter"): vergunningen die vrijwel dezelfde locatie delen, delen ook hun opzoeking.
_ONTDUBBEL_METER = 5.0

# Jaarafvoer per Maas-waterlichaam, m3/s. Keuze van dit lab: de KRW-service levert geen
# afvoergegevens. Orde van grootte van de Maas bij gemiddelde afvoer.
DEBIET_M3_S = {
    "NL91BOM": 230.0, "NL91GM": 240.0, "NL91ZM": 250.0, "NL91BM": 260.0,
    "NL94_5": 270.0, "NL94_6": 280.0, "NL94_1": 300.0, "NL94_11": 310.0,
}
STANDAARD_DEBIET = 250.0

# Hoedanigheden waarvan een meting met een vergunde vracht te vergelijken is: de hele stof.
# `NVT` = niet van toepassing (de stof zelf), `N` = uitgedrukt in stikstof. Alles daarbuiten is
# een deelgrootheid — `nf` is de opgeloste fractie na filtratie — en daar rekenen we niet aan toe.
# Bewust een toelatende lijst en geen uitsluitende: een onbekende hoedanigheid levert dan géén
# toerekening in plaats van een stille vergelijking van twee verschillende grootheden.
HOEDANIGHEID_VERGELIJKBAAR = {"NVT", "N", ""}


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


def _vergunning_coordinaat(post: dict) -> tuple[float, float] | None:
    """De coördinaat van één vergunning: het eerste voorschrift met een bruikbare `rd`.

    `SmwkAtlasConnector.vergunningen_bij_punt()` vraagt zelf `returnGeometry: "false"` op de
    vestiging, dus op het register is géén geometrie meer te vinden. De enige coördinaat die
    overblijft staat op de voorschriften (`meetpunt_X/Y_Coordinaat`), vandaar dat dit op de
    **ruwe** Atlas-post moet werken, vóór `atlas_register.naar_register()` de voorschriften
    weggooit.
    """
    for v in post.get("voorschriften") or []:
        rd = v.get("rd") or [None, None]
        x, y = (list(rd) + [None, None])[:2]
        if x is None or y is None:
            continue
        try:
            return float(x), float(y)
        except (TypeError, ValueError):
            continue
    return None


def _waterlichaam_opzoeken(x: float, y: float, haal=None) -> str | None:
    """Het owl_id van het KRW-waterlichaam op dit punt, via het bestaande, geteste ketenpad."""
    from leefomgevinglab.usecases.lozing_keten.bronnen import contextset
    return contextset(x, y, straal_m=_WATERLICHAAM_STRAAL_M, live=True, haal=haal).get("owl_id")


def _waterlichaam_per_vergunning(posten_ruw: list[dict], live: bool, haal=None,
                                  _haal_waterlichaam=None) -> tuple[dict, dict]:
    """Het KRW-waterlichaam van elke vergunning, uit haar eigen coördinaat.

    Levert (per_sleutel, redenen): per_sleutel mapt de sleutel uit `toerekening.sleutel_post`
    naar een owl_id, redenen mapt diezelfde sleutel naar een leesbare reden waarom er géén
    waterlichaam gevonden is. Zonder waterlichaam kan niet bepaald worden of een lozing
    bovenstrooms ligt, en dan hoort zij — met reden — buiten de toerekening te blijven: een
    mislukte of lege opzoeking is nooit een reden om te gokken, en nooit een reden om de post
    stilzwijgend weg te laten.

    `_haal_waterlichaam(x, y) -> str | None` is het injectiepunt voor tests: standaard wordt
    `lozing_keten.bronnen.contextset()` bevraagd, maar tests kunnen dit vervangen zonder zelf
    WFS-antwoorden te hoeven bouwen.
    """
    opzoeken = _haal_waterlichaam or (lambda x, y: _waterlichaam_opzoeken(x, y, haal))

    per_sleutel: dict[str, str] = {}
    redenen: dict[str, str] = {}

    if not live:
        for i, post in enumerate(posten_ruw):
            redenen[toerekening.sleutel_post(post, i)] = "niet opgezocht (live staat uit)"
        return per_sleutel, redenen

    coord_per_sleutel: dict[str, tuple[float, float]] = {}
    for i, post in enumerate(posten_ruw):
        sleutel = toerekening.sleutel_post(post, i)
        coord = _vergunning_coordinaat(post)
        if coord is None:
            redenen[sleutel] = "geen coördinaat in de bron"
        else:
            coord_per_sleutel[sleutel] = coord

    # Ontdubbelen op coördinaat vóór de opzoeking: meerdere vergunningen delen vaak eenzelfde
    # locatie, en elke opzoeking is een losse WFS-aanroep.
    def _rond(c: tuple[float, float]) -> tuple[float, float]:
        return (round(c[0] / _ONTDUBBEL_METER) * _ONTDUBBEL_METER,
                round(c[1] / _ONTDUBBEL_METER) * _ONTDUBBEL_METER)

    sleutels_per_punt: dict[tuple[float, float], list[str]] = {}
    for sleutel, coord in coord_per_sleutel.items():
        sleutels_per_punt.setdefault(_rond(coord), []).append(sleutel)

    def _per_punt(item: tuple[tuple[float, float], list[str]]):
        punt, sleutels = item
        x, y = coord_per_sleutel[sleutels[0]]
        try:
            owl_id = opzoeken(x, y)
        except Exception:                          # noqa: BLE001 — een storing is geen gok
            owl_id = None
        return sleutels, owl_id

    with ThreadPoolExecutor(max_workers=8) as pool:
        resultaten = list(pool.map(_per_punt, sleutels_per_punt.items()))

    for sleutels, owl_id in resultaten:
        for sleutel in sleutels:
            if owl_id:
                per_sleutel[sleutel] = owl_id
            else:
                redenen[sleutel] = "geen waterlichaam gevonden bij deze coördinaat"

    return per_sleutel, redenen


def _buiten_toerekening(register: list[dict], redenen: dict[str, str]) -> list[dict]:
    """De posten zonder bekend waterlichaam, met hun reden — nooit stilzwijgend verdwenen."""
    uit = []
    for i, post in enumerate(register):
        reden = redenen.get(toerekening.sleutel_post(post, i))
        if reden:
            uit.append({"naam": post.get("naam"), "kenmerk": post.get("kenmerk"), "reden": reden})
    return uit


def stroomprofiel(register: list[dict], wl_per_vergunning: dict[str, str],
                  redenen: dict[str, str], wl_meetpunt: str | None) -> dict:
    """De Maas als reeks waterlichamen, met de vergunningen in de band waar zij liggen.

    De band is de eenheid waarop het toerekeningsmodel rekent, en daarom ook de eenheid van deze
    verbeelding: binnen een waterlichaam kent het model geen posities, dus de plaat mag die ook
    niet suggereren. Dat is geen vereenvoudiging maar de waarheid over wat wij weten — waar een
    lozing precies binnen een waterlichaam zit, zou een stromingsmodel vergen.

    Bovenstrooms staat vóór het meetpunt in de lijst, benedenstrooms erna; `bovenstrooms` zegt per
    band of de vergunningen erin meegerekend zijn. Let op dat de band van het meetpunt zelf
    bovenstrooms heet: een lozing op hetzelfde waterlichaam telt mee, ook als zij daarbinnen
    stroomafwaarts ligt (zie `toerekening.is_bovenstrooms`).

    Vergunningen zonder vindbaar waterlichaam horen in geen enkele band en komen apart terug, met
    hun reden: wie ze zou weglaten, laat de lezer een plaat zien die volledig lijkt.
    """
    in_band: dict[str, list[dict]] = {code: [] for code, _n in toerekening.STROOMVOLGORDE}
    zonder: list[dict] = []
    for i, post in enumerate(register):
        sleutel = toerekening.sleutel_post(post, i)
        wl = wl_per_vergunning.get(sleutel)
        item = {"naam": post.get("naam"), "kenmerk": post.get("kenmerk"),
                "plaats": post.get("plaats"), "vrachten": post.get("vrachten") or {}}
        if wl and wl in in_band:
            item["toegerekend"] = bool(wl_meetpunt) and toerekening.is_bovenstrooms(wl, wl_meetpunt)
            in_band[wl].append(item)
        else:
            zonder.append({**item,
                           "reden": redenen.get(sleutel) or "waterlichaam valt buiten de Maas-reeks"})

    banden = []
    for code, naam in toerekening.STROOMVOLGORDE:
        banden.append({
            "code": code, "naam": naam,
            "meetpunt": code == wl_meetpunt,
            "bovenstrooms": bool(wl_meetpunt) and toerekening.is_bovenstrooms(code, wl_meetpunt),
            "vergunningen": in_band[code],
        })
    return {"banden": banden, "zonder_waterlichaam": zonder,
            "waterlichaam_meetpunt": wl_meetpunt}


def beeld(code: str, pad: str, live: bool = True, straal_m: int = 50000,
          _haal_regels=None, _haal_atlas=None, _haal_waterlichaam=None,
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
            wl_per_vergunning, redenen = _waterlichaam_per_vergunning(
                posten, live=True, _haal_waterlichaam=_haal_waterlichaam)
            redenen_vergunning = redenen
            mag = {"status": "ok", **reg,
                   "buiten_toerekening": _buiten_toerekening(reg["register"], redenen)}
        except Exception as exc:                 # noqa: BLE001 — bron mag wegvallen
            mag = {"status": "onbereikbaar", "fout": type(exc).__name__,
                   "register": [], "telling": {}, "bron": {}, "echt": False,
                   "buiten_toerekening": []}
            wl_per_vergunning = {}
            redenen_vergunning = {}
    else:
        mag = {"status": "overgeslagen", "register": [], "telling": {},
               "bron": {}, "echt": False, "buiten_toerekening": []}
        wl_per_vergunning = {}
        redenen_vergunning = {}

    # Gebeurt — de metingen
    gebeurt = {"beschikbaar": bool(set_.get("beschikbaar")),
               "reden": set_.get("reden", ""), "meetjaar": set_.get("meetjaar"),
               "stoffen": punt.get("stoffen") or []}

    # De vraag: wie kan bijdragen? Alleen zinvol met een meting én vergunningen. Het
    # waterlichaam per vergunning komt uit haar eigen coördinaat (`wl_per_vergunning`
    # hierboven) — niet uit het waterlichaam van het meetpunt, anders is elke vergunning
    # binnen de zoekstraal per definitie "bovenstrooms".
    debiet = DEBIET_M3_S.get(wl, STANDAARD_DEBIET)
    vraag = []
    for stof in gebeurt["stoffen"]:
        naam = stof.get("naam")
        hoed = (stof.get("hoedanigheid") or "").strip()
        basis = {"stof": stof.get("code"), "naam": naam,
                 "hoedanigheid": hoed, "hoedanigheid_naam": stof.get("hoedanigheid_naam") or ""}
        if hoed not in HOEDANIGHEID_VERGELIJKBAAR:
            # Een vergunning begrenst de totale vracht van een stof. Een meting van een deel
            # daarvan — opgelost zink na filtratie bijvoorbeeld — is een andere grootheid, en de
            # vergunde vracht eraan toerekenen zou een bijdrage opleveren die groter is dan de
            # fractie zelf kan dragen. Dan rekenen we niet toe, en zeggen we waarom.
            vraag.append({**basis, "posten": [], "som_bovengrens": 0.0,
                          "restant": stof.get("mediaan") or 0.0,
                          "restant_label": "niet toe te rekenen",
                          "eenheid": stof.get("eenheid") or "mg/l",
                          "toerekenbaar": False,
                          "reden": f"de meting betreft {stof.get('hoedanigheid_naam') or hoed}, "
                                   f"terwijl een vergunning de totale vracht begrenst; die twee "
                                   f"zijn niet met elkaar te vergelijken",
                          "voorbehoud": toerekening.VOORBEHOUD})
            continue
        d = toerekening.bijdragen(stof.get("mediaan") or 0.0, naam,
                                  mag.get("register") or [], wl or "", wl_per_vergunning, debiet,
                                  eenheid=stof.get("eenheid") or "mg/l")
        vraag.append({**basis, "toerekenbaar": True, "reden": None, **d})

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
        "stroomprofiel": stroomprofiel(mag.get("register") or [], wl_per_vergunning,
                                       redenen_vergunning, wl),
        "gebeurt": gebeurt,
        "bijdragen": vraag,
        "proclaimer": proclaimer.bouw(set_, mag, regels.BRON, doelen_beschikbaar=False,
                                      punten_in_beeld=in_beeld),
    }
