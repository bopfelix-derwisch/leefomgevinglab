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


# -- Het waterdossier: informatiemodel en kennisgraaf -------------------------------------------

def test_het_waterdossier_staat_op_een_eigen_eindpunt():
    """Apart van `/api/onderwater`, en met opzet: die is instant (YAML en constanten), deze heeft
    bronnen nodig. Ze samenvoegen zou de hele pagina laten wachten op iets wat onderaan staat."""
    d = _client().get("/api/onderwater/waterdossier").json()
    assert d["informatiemodel"]["zekerheden"], "de constanten horen er altijd te zijn"
    assert [g["id"] for g in d["grafen"]] == ["stoffen", "toezicht"]


def test_de_route_bouwt_de_toezichtgraaf_niet_om_een_uitlegpagina_te_vullen():
    """**De belangrijkste eigenschap van dit eindpunt.** Een uitlegpagina die een graaf van
    73.000 triples opbouwt omdat iemand haar opent, is zelf het probleem dat zij beschrijft -- en
    live kost dat ~9 s plus een coördinaatopzoeking per vergunning. Alleen wat al in het geheugen
    zit gaat mee; anders staat de sectie er met `nog_niet_geteld` aan."""
    import leefomgevinglab.geluidsmeter.api as api_mod
    api_mod._TOEZICHTGRAAF.update({"graaf": None, "gebouwd_op": 0.0, "bron": None, "telling": {}})
    d = _client().get("/api/onderwater/waterdossier").json()
    tz = next(g for g in d["grafen"] if g["id"] == "toezicht")
    assert tz["nog_niet_geteld"] is True
    assert not tz["telling"]
    # De klassen komen uit het model en zijn dus altijd bekend, ook zonder graaf.
    assert "Signaal" in tz["klassen"] and "Overschrijding" in tz["klassen"]


def test_een_onbereikbare_aquo_tabel_laat_de_sectie_staan(monkeypatch):
    """Zelfde regel als elders in dit lab: een bron die wegvalt maakt de uitleg niet onzichtbaar,
    hij maakt haar ongeteld."""
    import leefomgevinglab.geluidsmeter.api as api_mod

    def valt_om(*a, **k):
        raise OSError("aquo onbereikbaar")

    monkeypatch.setattr(api_mod.stoffengraaf_mod, "bouw", valt_om)
    d = _client().get("/api/onderwater/waterdossier").json()
    st = next(g for g in d["grafen"] if g["id"] == "stoffen")
    assert st["nog_niet_geteld"] is True
    assert st["wat"] and st["waarom_graaf"], "de uitleg blijft, de cijfers niet"


def test_de_pagina_rendert_het_informatiemodel_en_de_grafen_uit_de_api():
    """Zelfde eis als de rest van deze pagina: geen veldnaam, geen zekerheid en geen klasse
    hardgecodeerd in de HTML. Zou dat wel zo zijn, dan kan de pagina iets anders zeggen dan het
    model doet -- en dan is 'uitleggen wat er onder water gebeurt' een holle belofte."""
    r = _client().get("/onderwater")
    assert 'id="informatiemodel"' in r.text and 'id="grafen"' in r.text
    assert "/api/onderwater/waterdossier" in r.text
    # Wat deze test wél kan bewaken: dat de veldenlijst en de klassen niet in de HTML staan.
    # Twee dingen mogen er met opzet in voorkomen en zijn hier dus uitgezonderd: de zekerheden
    # verschijnen als CSS-klasse (afgeleid uit de waarde zelf, zodat kleur en model niet uit de
    # pas kunnen lopen), en "hoedanigheid" staat in één prozazin over de aanname die meereist --
    # die zin gaat over het veld en is geen tweede vastlegging ervan.
    for naam in ("lozingspunt", "bemonsteringstermen\"", "Gevaarlijke stof"):
        assert naam not in r.text, f"{naam} hoort uit de API te komen"
    assert "Stoffengraaf" not in r.text and "Toezichtgraaf" not in r.text, (
        "de graafnamen komen uit /api/onderwater/waterdossier")
    assert "t:Vestiging" not in r.text, "de klassen komen uit het model"
    assert "g.klassen" in r.text and "im.velden" in r.text, (
        "en de pagina moet ze wél uit de API lezen")


def test_de_pagina_laadt_het_waterdossier_apart_van_de_hoofdanatomie():
    """De hoofdanatomie is instant; deze sectie heeft bronnen nodig. In één fetch zou de hele
    pagina wachten op iets wat onderaan staat."""
    r = _client().get("/onderwater")
    assert "laadWaterdossier()" in r.text
    assert r.text.count("async function laad") >= 2, "twee aparte laadfuncties"
