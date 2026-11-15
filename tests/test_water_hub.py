import re

from fastapi.testclient import TestClient

import leefomgevinglab.geluidsmeter.api as api
from leefomgevinglab.usecases import water_hub as wh
from leefomgevinglab.usecases.toezicht import signalen
from tests import telwoorden


def _client(monkeypatch):
    monkeypatch.setattr(api, "load_config", lambda *a, **k: api._config)
    return TestClient(api.app)


# Nederlandse telwoorden, voor de samenvattingen die een aantal regels claimen. Alleen de getallen
# die in dit dossier voorkomen; een nieuw telwoord valt luid om in plaats van stil over te slaan.
# Eén telwoordtabel voor de hele suite (`tests/telwoorden.py`), niet hier een tweede: twee
# lijsten die uit de pas kunnen lopen is in dit project al duur geweest.
_TELWOORD = telwoorden.TELWOORD


def test_elk_lid_heeft_een_pad_een_label_en_een_verantwoording():
    assert len(wh.LEDEN) == 15
    for l in wh.LEDEN:
        assert l["pad"].startswith("/")
        assert l["label"] and l["titel"] and l["samenvatting"]
        # het paar dat afdwingt dat elke waterpagina zich verantwoordt
        assert isinstance(l["live"], list) and isinstance(l["synthetisch"], list)


def test_lid_ids_zijn_uniek_en_opzoekbaar():
    ids = [l["id"] for l in wh.LEDEN]
    assert len(ids) == len(set(ids))
    assert wh.lid("kaart")["pad"] == "/waterruimte"


def test_de_drie_lijnen_lopen_door_het_hele_dossier():
    assert len(wh.LIJNEN) == 3
    for lijn in wh.LIJNEN:
        assert lijn["kop"] and lijn["tekst"]
        assert lijn["leden"], "een lijn zonder leden is geen doorsnijdende lijn"
        for lid_id in lijn["leden"]:
            assert wh.lid(lid_id), f"onbekend lid: {lid_id}"


def test_dekking_geeft_per_lijn_de_leden_die_hem_raken():
    d = wh.dekking()
    assert len(d) == 3
    for rij in d:
        assert rij["lijn"] and rij["leden"]
        assert len(rij["leden"]) >= 2, "een lijn die maar één pagina raakt is geen rode draad"


def test_subnav_markeert_precies_een_actief_item():
    html = wh.subnav_html("ruimte")
    assert html.count('aria-current="page"') == 1
    assert '/gebruiksruimte' in html
    for l in wh.LEDEN:
        assert l["pad"] in html, f"{l['pad']} ontbreekt in de subnav"


def test_subnav_zonder_actief_item_markeert_niets():
    assert wh.subnav_html(None).count('aria-current="page"') == 0


def test_subnav_ontsnapt_geen_html_uit_de_labels():
    """De labels zijn van ons, maar de balk mag geen ruwe < of > doorlaten."""
    html = wh.subnav_html("keten")
    assert "<script" not in html.lower()
    assert re.search(r'<nav[^>]*class="waternav"', html)


def test_atlas_cijfers_zijn_gemeten_niet_overdreven():
    """Bevinding 6 van de eindreview: laag 0 telt 72 rúwe features, maar 7 daarvan dragen geen
    vergunningkenmerk en één is een letterlijk duplicaat; na ontdubbeling zijn het 69 posten met
    63 vergunningen (gemeten tegen de bron, 2026-09-23). De ongeverifieerde bewering over
    meetgegevens ('38 stoffen, vier keer per jaar sinds 2023') stond als feit over andermans
    dataset op een publieke pagina en is geschrapt."""
    tekst = " ".join(wh.ATLAS["wat_er_al_is"])
    assert "69 posten" in tekst and "63" in tekst
    assert "72 vestigingen" not in tekst
    assert "38 stoffen" not in tekst


def test_overzicht_levert_alles_wat_de_pagina_nodig_heeft():
    o = wh.overzicht()
    assert o["leden"] == wh.LEDEN
    assert o["lijnen"] == wh.LIJNEN
    assert o["dekking"] == wh.dekking()
    assert "atlas" in o and o["atlas"]["url"].startswith("https://")
    assert o["atlas"]["licentie"], "de licentiepositie hoort expliciet op de pagina"


# -- Must-fix 1 van de eindreview: een samenvatting mag niets beloven wat de route niet heeft ----
#
# `tests/test_water_hub.py` raakte vóór deze fixronde geen enkele samenvatting (de leden-test ging
# alleen van 13 naar 14), en daardoor bleef op `/api/water/hub` maanden publiek staan dat
# `/toezicht` "tien deterministische regels ... plus de pijplijn en de runlog" toont -- terwijl de
# herbouwde pagina drie regels toont, geen pijplijnsectie heeft (`/api/toezicht/pijplijn` is
# verwijderd) en geen runlog. De twee tests hieronder vangen precies die twee soorten belofte.

def test_een_samenvatting_die_regels_telt_noemt_het_aantal_van_haar_eigen_route():
    """Het aantal komt uit `signalen.REGELS` via `Regel.laag`, niet uit een getal in deze test:
    verschuift de papier/werkelijkheid-splitsing, dan verschuift de verwachting mee en moet de
    samenvatting mee veranderen."""
    per_pad = {
        "/wasstraat": len([r for r in signalen.REGELS if r.laag == "papier"]),
        "/toezicht": len([r for r in signalen.REGELS if r.laag == "werkelijkheid"]),
    }
    geteld = 0
    for lid in wh.LEDEN:
        for m in re.finditer(r"\b(\w+)\s+deterministische\s+regels", lid["samenvatting"]):
            woord = m.group(1).lower()
            assert woord in _TELWOORD, f"{lid['id']}: onbekend telwoord {woord!r}"
            assert lid["pad"] in per_pad, (
                f"{lid['id']} claimt een aantal regels, maar deze test weet niet hoeveel regels "
                f"{lid['pad']} draagt -- vul `per_pad` aan in plaats van de bewaking te omzeilen")
            assert _TELWOORD[woord] == per_pad[lid["pad"]], (
                f"{lid['id']}: de samenvatting zegt {woord} ({_TELWOORD[woord]}) regels, "
                f"{lid['pad']} draagt er {per_pad[lid['pad']]}")
            geteld += 1
    assert geteld >= 2, "geen enkele samenvatting claimt een aantal regels -- test is stil geworden"


def test_een_samenvatting_die_pijplijn_of_runlog_belooft_wijst_naar_een_pagina_die_ze_heeft(
        monkeypatch):
    """Eén richting, met opzet: een pagina mag meer tonen dan haar samenvatting belooft, maar
    nooit minder. Gemeten op de echt geserveerde HTML, niet op een lijst in deze test."""
    client = _client(monkeypatch)
    for lid in wh.LEDEN:
        beloofd = [w for w in ("pijplijn", "runlog") if w in lid["samenvatting"].lower()]
        if not beloofd:
            continue
        html = client.get(lid["pad"]).text.lower()
        for woord in beloofd:
            assert woord in html, f"{lid['id']} belooft de {woord}, maar {lid['pad']} toont er geen"
