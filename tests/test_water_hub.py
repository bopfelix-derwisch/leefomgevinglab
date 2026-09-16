import re

from leefomgevinglab.usecases import water_hub as wh


def test_elk_lid_heeft_een_pad_een_label_en_een_verantwoording():
    assert len(wh.LEDEN) == 5
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


def test_overzicht_levert_alles_wat_de_pagina_nodig_heeft():
    o = wh.overzicht()
    assert o["leden"] == wh.LEDEN
    assert o["lijnen"] == wh.LIJNEN
    assert o["dekking"] == wh.dekking()
    assert "atlas" in o and o["atlas"]["url"].startswith("https://")
    assert o["atlas"]["licentie"], "de licentiepositie hoort expliciet op de pagina"
