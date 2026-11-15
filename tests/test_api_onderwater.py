"""De routes `/onderwater` en `/api/onderwater` -- de technische anatomie van de twee
signaalpagina's.

De inhoudelijke bewaking (alles afgeleid, geen ingetypte getallen, geen serverpad, witte lijst)
staat in `tests/test_onderwater.py`. Hier gaat het om de route: leest zij dezelfde bronnen als de
twee dossierroutes, en rendert de pagina de anatomie in plaats van haar in de HTML te herhalen?
"""
from fastapi.testclient import TestClient

from leefomgevinglab.geluidsmeter import api as api_mod
from leefomgevinglab.usecases.toezicht import signalen


def _client():
    return TestClient(api_mod.app)


def test_de_anatomie_leest_dezelfde_yaml_als_de_runner():
    """Geen tweede bron: zou deze route een eigen kopie van de configuratie lezen, dan kon de
    pagina iets anders vertellen dan er in een run gebeurt -- en dat is precies het tegendeel van
    waarvoor zij bestaat."""
    d = _client().get("/api/onderwater").json()
    assert {a["id"] for a in d["agents"]} == {"vergunninglezer", "signaalsteller",
                                               "dossiersteller", "uitlegger", "vraagsteller",
                                               "terugkoppelaar"}
    assert [t["id"] for t in d["taken"]] == ["lees_vergunning", "bepaal_signalen",
                                              "stel_dossier_samen", "leg_signalen_uit"]


def test_de_anatomie_noemt_alle_regels_uit_de_echte_catalogus():
    d = _client().get("/api/onderwater").json()
    assert [r["id"] for r in d["regels"]] == [r.id for r in signalen.REGELS]


def test_de_route_publiceert_geen_absoluut_serverpad():
    """Zelfde regel als op `/api/wasstraat/pijplijn` (eindreview, kleinere bevinding 7). Deze
    route is de gevaarlijkste van de twee, want zij toont paden als onderwerp."""
    tekst = _client().get("/api/onderwater").text
    assert "/mnt/nvme" not in tekst
    assert "/home/" not in tekst


def test_de_pagina_rendert_de_anatomie_en_herhaalt_haar_niet_in_de_html():
    """De aantallen en de regelnamen moeten uit de API komen. Stonden ze in de HTML, dan kan de
    pagina iets anders zeggen dan de code doet -- en dan is deze hele pagina waardeloos, want zij
    is het enige dat de lezer heeft om de rest te controleren."""
    r = _client().get("/onderwater")
    assert r.status_code == 200
    for regel_id in [x.id for x in signalen.REGELS]:
        assert regel_id not in r.text, (
            f"{regel_id} staat hardgecodeerd in de HTML; de regels komen uit /api/onderwater")
    for agent in ("vergunninglezer", "signaalsteller", "uitlegger"):
        assert agent not in r.text, f"{agent} hoort uit de API te komen"
    assert "/api/onderwater" in r.text, "de pagina moet de anatomie wel ophalen"


def test_de_pagina_draagt_de_waternav_van_het_dossier():
    r = _client().get("/onderwater")
    assert "__WATERNAV__" not in r.text, "de placeholder is niet vervangen"
    assert 'class="waternav"' in r.text
    assert 'aria-current="page"' in r.text, "dit lid hoort actief te zijn in de balk"


def test_de_openklapbare_agentrijen_gebruiken_details_en_geen_eigen_klikcode():
    """Een `<details>` is van zichzelf toetsenbordbereikbaar en open-/dichtklapbaar. Een eigen
    klikafhandeling op een `div` zou dat moeten nabouwen, en dat gaat in de praktijk mis -- hier
    is de eenvoudige oplossing ook de toegankelijke."""
    r = _client().get("/onderwater")
    assert "<details" in r.text and "<summary" in r.text
    assert "addEventListener(\"click\"" not in r.text


def test_er_is_geen_schrijfpad_op_de_onderwater_routes():
    """405, niet `in (404, 405)`: met 404 erbij slaagt deze test ook als de route helemaal weg
    is, en dan bewaakt zij niets meer."""
    client = _client()
    for pad in ("/onderwater", "/api/onderwater"):
        for methode in ("post", "put", "patch", "delete"):
            r = getattr(client, methode)(pad)
            assert r.status_code == 405, f"{methode.upper()} {pad} gaf {r.status_code}"


def test_de_anatomie_is_een_lid_van_het_waterdossier():
    """Bob's keuze: naast de twee pagina's in de dossierbalk, zodat wie doorklikt in hetzelfde
    dossier blijft."""
    leden = _client().get("/api/water/hub").json()["leden"]
    lid = next(l for l in leden if l["pad"] == "/onderwater")
    assert lid["label"] and lid["titel"] and lid["samenvatting"]
    assert lid["live"] and lid["synthetisch"]
