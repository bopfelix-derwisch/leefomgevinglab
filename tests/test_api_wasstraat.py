"""`/wasstraat` -- de pagina en de eindpunten.

Splitsing van `/toezicht` (plan: `docs/superpowers/plans/2026-11-14-wasstraat-en-toezicht-
splitsen.md`): zelfde register, zelfde standaardpijplijn, andere lezer. Geen netwerk hier:
`_toezicht_register`/`_toezicht_aquo_ref`/`_toezicht_normenset`/`_stelselcatalogus` worden per
test gemonkeypatcht, exact zoals in `test_api_toezicht.py` -- dezelfde vier bronnen, nu bediend
via de wasstraat-routes.
"""
from fastapi.testclient import TestClient

import leefomgevinglab.geluidsmeter.api as api
from leefomgevinglab.usecases import water_hub as wh
from leefomgevinglab.usecases.toezicht import pijplijn
from tests.test_api_toezicht import (
    FIXTURE_AQUO_REF, FIXTURE_AQUO_REF_VERVALLEN, FIXTURE_NORMENSET, FIXTURE_VESTIGING,
    FIXTURE_VESTIGING_VERVALLEN,
)
from tests.test_toezicht_runner import AGENTS, TASKS


def _client(monkeypatch):
    monkeypatch.setattr(api, "load_config", lambda *a, **k: api._config)
    return TestClient(api.app)


def _monkeypatch_bronnen(monkeypatch, register=(FIXTURE_VESTIGING,)):
    monkeypatch.setattr(api, "_toezicht_register", lambda: list(register))
    monkeypatch.setattr(api, "_toezicht_aquo_ref", lambda: FIXTURE_AQUO_REF)
    monkeypatch.setattr(api, "_toezicht_normenset", lambda: FIXTURE_NORMENSET)
    monkeypatch.setattr(api, "_stelselcatalogus", lambda: None)


# -- De pagina: banner, taalregel, lid van het waterdossier, geen eigen kaart -------------------

def test_de_pagina_draagt_de_open_data_banner(monkeypatch):
    h = _client(monkeypatch).get("/wasstraat").text.lower()
    assert "open data" in h
    assert "geen bevoegdheid" in h
    assert "geen oordeel" in h
    assert "zonder authenticatie" in h
    assert "zonder logging" in h


def test_de_pagina_haalt_de_taalregel_op_de_echte_html(monkeypatch):
    h = _client(monkeypatch).get("/wasstraat").text.lower()
    assert "overtreding" not in h
    assert "veroorzaakt door" not in h
    assert "in strijd met" not in h


def test_de_pagina_noemt_het_alleen_lezen_ontwerpbesluit_als_een_regel(monkeypatch):
    """Geen schrijfpad, en dat staat uitgelegd bij de configuratie -- niet als los
    disclaimer-blok (plan, punt 3)."""
    h = _client(monkeypatch).get("/wasstraat").text.lower()
    assert "alleen-lezen" in h
    assert "schrijfpad" in h


def test_wasstraat_is_lid_van_het_waterdossier_en_krijgt_geen_eigen_kaart(monkeypatch):
    assert wh.lid("wasstraat")["pad"] == "/wasstraat"
    r = _client(monkeypatch).get("/")
    assert 'href="/wasstraat"' not in r.text


def test_wasstraatpagina_geeft_200_met_de_subnav(monkeypatch):
    r = _client(monkeypatch).get("/wasstraat")
    assert r.status_code == 200
    assert 'class="waternav"' in r.text
    assert r.text.count('aria-current="page"') == 1
    assert "__WATERNAV__" not in r.text


# -- De pijplijn komt uit dezelfde configuratie als /toezicht -----------------------------------

def test_de_pijplijn_komt_uit_dezelfde_configuratie_als_de_runner(monkeypatch):
    """`/api/toezicht/pijplijn` bestaat niet meer (de configuratie verhuisde volledig naar
    `/wasstraat`, zie de taakbrief van `/toezicht`'s herbouw) -- deze test vergelijkt daarom
    alleen nog tegen de module zelf, niet tegen een tweede route die dezelfde bron toonde."""
    uit_api = _client(monkeypatch).get("/api/wasstraat/pijplijn").json()
    uit_module = pijplijn.als_gegeven(AGENTS, TASKS)
    assert [a["id"] for a in uit_api["agents"]] == [a["id"] for a in uit_module["agents"]]
    assert [t["id"] for t in uit_api["tasks"]] == [t["id"] for t in uit_module["tasks"]]
    assert uit_api["bron"].endswith("agents.yaml")


def test_de_pagina_rendert_de_takenorde(monkeypatch):
    """Toetst de *inhoud*, niet het element-id (eindreview, kleinere bevinding 5). `"takentabel"
    in r.text` bewees alleen dat er een `<table id="takentabel">` in de HTML staat -- een tabel
    die nooit gevuld wordt, of een JS-functie die stilletjes weg is, liet die assertie net zo
    goed slagen. Wat deze pagina moet doen is de takenorde uit de API renderen, dus toets dat de
    tabel bestaat én dat de code die hem vult de velden van de API gebruikt.

    De tweede assertie blijft de belangrijkste: geen enkele taaknaam staat hardgecodeerd in de
    HTML. Zou dat wel zo zijn, dan kan de pagina een andere orde tonen dan de pijplijn draait --
    en juist dát is wat deze tab belooft te laten zien."""
    r = _client(monkeypatch).get("/wasstraat")
    assert 'id="takentabel"' in r.text, "de tabel zelf"
    assert "tekenTaken" in r.text, "en de functie die hem uit de API vult"
    for veld in ("t.id", "t.agent", "t.context"):
        assert veld in r.text, f"de takentabel leest {veld} uit /api/wasstraat/pijplijn"
    for taaknaam in ("bepaal_signalen", "lees_vergunning", "stel_dossier_samen"):
        assert taaknaam not in r.text, (
            f"{taaknaam} staat hardgecodeerd in de HTML; de orde moet uit de API komen")


# -- Vestigingen/vergunningen -------------------------------------------------------------------

def test_vergunningen_endpoint_geeft_een_lijst(monkeypatch):
    _monkeypatch_bronnen(monkeypatch)
    r = _client(monkeypatch).get("/api/wasstraat/vestigingen")
    assert r.status_code == 200
    d = r.json()
    assert d == [{"id": "TEST01", "locatiecode": "TEST01", "naam": "Testvestiging BV",
                  "plaats": "Venlo", "kenmerk": None}]


def test_onbekende_vergunning_geeft_404(monkeypatch):
    _monkeypatch_bronnen(monkeypatch)
    r = _client(monkeypatch).get("/api/wasstraat/dossier?vergunning=BESTAAT_NIET")
    assert r.status_code == 404


def test_de_pagina_vraagt_het_waterlichaam_niet_op_in_de_kaart(monkeypatch):
    """Must-fix 3 van de eindreview: het waterlichaam is geen papierfeit. Niet in het antwoord en
    niet in de veldenlijst van de pagina -- stond het er alleen in de API, dan zou de volgende
    lezer het weer renderen."""
    _monkeypatch_bronnen(monkeypatch)
    client = _client(monkeypatch)
    d = client.get("/api/wasstraat/dossier?vergunning=TEST01").json()
    assert "waterlichaam" not in d["kaart"]
    # Op de veldenlijst van de pagina, niet op het woord: de HTML legt in een commentaar uit
    # waarom het veld er níet staat, en dat commentaar hoort te blijven.
    assert '["waterlichaam"' not in client.get("/wasstraat").text


# -- Het dossier bevat alleen de zeven papierbevindingen ----------------------------------------

def test_het_dossier_endpoint_laat_alleen_papierbevindingen_zien(monkeypatch):
    """`FIXTURE_VESTIGING` triggert `meerdere_grenswaarden` en `niet_regime_zuiver` (twee
    Zink-voorschriften met verschillende waarden, allebei met een bemonsteringsregime) -- beide
    papierregels. Geen van de drie werkelijkheidsregels kan hier vuren: de route geeft geen
    `gemeten_codes`/`waterlichaam`/`register_codes` mee."""
    _monkeypatch_bronnen(monkeypatch)
    d = _client(monkeypatch).get("/api/wasstraat/dossier?vergunning=TEST01").json()
    regel_ids = {s["regel"] for s in d["signalen"]}
    assert regel_ids, "geen signalen -- de fixture triggert normaal gesproken twee papierregels"
    assert regel_ids <= {"vervallen_code", "niet_in_referentie", "meerdere_grenswaarden",
                          "vracht_onbepaald", "vergunning_niet_te_vinden", "niet_regime_zuiver",
                          "geen_geldigheidsduur"}
    for s in d["signalen"]:
        assert s.get("reparatie"), s["regel"]


def test_het_dossier_endpoint_bekabelt_de_aquo_bron_en_vervallen_code_krijgt_een_reparatie(
        monkeypatch):
    monkeypatch.setattr(api, "_toezicht_register", lambda: [FIXTURE_VESTIGING_VERVALLEN])
    monkeypatch.setattr(api, "_toezicht_aquo_ref", lambda: FIXTURE_AQUO_REF_VERVALLEN)
    monkeypatch.setattr(api, "_toezicht_normenset", lambda: FIXTURE_NORMENSET)
    monkeypatch.setattr(api, "_stelselcatalogus", lambda: None)
    d = _client(monkeypatch).get("/api/wasstraat/dossier?vergunning=TEST02").json()
    s = next((x for x in d["signalen"] if x["regel"] == "vervallen_code"), None)
    assert s is not None, "vervallen_code vuurt niet -- de fixture of aquo.verrijk is gewijzigd"
    assert s.get("reparatie")


def test_het_dossier_endpoint_draait_zonder_taalmodel(monkeypatch):
    _monkeypatch_bronnen(monkeypatch)
    d = _client(monkeypatch).get("/api/wasstraat/dossier?vergunning=TEST01").json()
    stappen = d["runlog"]["stappen"]
    assert stappen, "de runlog van deze run is leeg"
    assert all(s["llm"] is False for s in stappen)
    agenten = [s["agent"] for s in stappen]
    assert "uitlegger" in agenten, "de runlog mist de uitlegger-stap"


def test_elke_stap_in_het_dossier_draagt_een_uitleg(monkeypatch):
    _monkeypatch_bronnen(monkeypatch)
    d = _client(monkeypatch).get("/api/wasstraat/dossier?vergunning=TEST01").json()
    for s in d["runlog"]["stappen"]:
        assert s.get("uitleg"), s["taak"]


def test_de_runlog_draagt_een_samenvatting(monkeypatch):
    _monkeypatch_bronnen(monkeypatch)
    d = _client(monkeypatch).get("/api/wasstraat/dossier?vergunning=TEST01").json()
    samenvatting = d["runlog"]["samenvatting"]
    assert samenvatting["aantal_stappen"] == len(d["runlog"]["stappen"])
    assert len(samenvatting["rijen_per_stap"]) == len(d["runlog"]["stappen"])
    assert samenvatting["stappen_met_taalmodel"] == []
    assert "Geen van de stappen heeft een taalmodel aangeroepen" in samenvatting["zin"]


# -- De uitleg per bevinding (must-fix 4) --------------------------------------------------------

def test_het_dossier_endpoint_levert_de_uitleg_per_bevinding(monkeypatch):
    """De vierde pijplijnstap (`leg_signalen_uit`) is de duurste van de vier -- live bij NATRON
    7,378 van de 7,378 seconden -- en leverde `waarom`/`waarom_vindplaatsen`/`waarom_reden` per
    signaal op. Elk signaal draagt óf een uitleg mét vindplaats, óf een reden waarom die er niet
    is; nooit niets (eindreview, must-fix 4)."""
    _monkeypatch_bronnen(monkeypatch)
    d = _client(monkeypatch).get("/api/wasstraat/dossier?vergunning=TEST01").json()
    assert d["signalen"], "geen bevindingen -- deze test kan niets toetsen"
    for s in d["signalen"]:
        if s.get("waarom"):
            assert s.get("waarom_vindplaatsen"), f"{s['regel']}: uitleg zonder vindplaats"
        else:
            assert s.get("waarom_reden"), f"{s['regel']}: geen uitleg en geen reden"


def test_de_pagina_rendert_de_uitleg_op_dezelfde_manier_als_toezicht(monkeypatch):
    """De uitlegstap werd betaald en weggegooid: `wasstraat.html` rendeerde van `waarom` niets
    (`grep -c waarom` = 0, tegen 6 op `toezicht.html`), terwijl de per-stap-uitleg op diezelfde
    pagina belooft dat er bij elk signaal een vindplaats wordt gezocht.

    Eén manier, niet twee: deze test eist dat beide pagina's dezelfde drie velden en dezelfde
    CSS-klassen gebruiken, zodat een latere wijziging aan de ene vorm niet stil een tweede vorm
    naast de eerste zet."""
    client = _client(monkeypatch)
    wasstraat = client.get("/wasstraat").text
    toezicht = client.get("/toezicht").text
    for stuk in ("s.waarom", "s.waarom_vindplaatsen", "s.waarom_reden", "s.waarom_gedupliceerd",
                 'class="herkomst"', 'class="vindplaats"'):
        assert stuk in toezicht, f"{stuk} staat niet (meer) op /toezicht"
        assert stuk in wasstraat, f"{stuk} staat niet op /wasstraat"


# -- Taalregel op het echte dossier, niet alleen op de pagina ------------------------------------

def test_een_bevinding_is_nooit_een_vaststelling(monkeypatch):
    _monkeypatch_bronnen(monkeypatch)
    d = _client(monkeypatch).get("/api/wasstraat/dossier?vergunning=TEST01").json()
    for s in d["signalen"]:
        tekst = (s["signaal"] + s.get("reparatie", "")).lower()
        for verboden in ("overtreding", "veroorzaakt door", "in strijd met"):
            assert verboden not in tekst, f"{s['signaal']}: {verboden}"


# -- Geen schrijfpaden ---------------------------------------------------------------------------

def test_er_is_geen_schrijfpad_op_de_wasstraat_routes(monkeypatch):
    """**405, niet `in (405, 404)`** (eindreview, kleinere bevinding 5). Deze test bewaakt twee
    dingen tegelijk: dat de route bestaat, en dat zij alleen leest. Met 404 erbij slaagt hij ook
    als de route helemaal verdwenen is -- dan bewaakt hij niets meer, en een test die groen blijft
    om de verkeerde reden is precies het defect dat dit project het meeste heeft gekost. 405
    bewijst beide helften: de padoplossing vond de route, en de methode is geweigerd."""
    client = _client(monkeypatch)
    for pad in ("/api/wasstraat/pijplijn", "/api/wasstraat/vestigingen",
                "/api/wasstraat/dossier?vergunning=X"):
        for methode in ("post", "put", "patch", "delete"):
            r = getattr(client, methode)(pad)
            assert r.status_code == 405, (
                f"{methode.upper()} {pad} gaf {r.status_code}; 405 = route bestaat en weigert de "
                "methode, 404 zou ook slagen als de route weg was")


# -- Must-fix 2 van de eindreview: de gekozen vergunning staat in de URL ----------------------

def test_de_link_naar_de_zusterpagina_draagt_de_gekozen_id(monkeypatch):
    """De link droeg alleen `/toezicht`, zonder id, en geen van beide pagina's las een
    queryparameter: wie bij Solvay las dat er bevindingen openstaan "voor deze vergunning" en
    doorklikte, kreeg de eerste vergunning uit de lijst (Mebin BV) te zien en dacht dat het
    Solvay was.

    Deze test staat op de geserveerde HTML, want de keuze gebeurt in de browser. Wat zij vastlegt
    is het mechanisme: er is een `data-zuster`-link, er is één plek die daar de id in zet, en die
    gebruikt de parameternaam van de zuster-API (`vestiging`) -- niet een derde vocabulaire."""
    html = _client(monkeypatch).get("/wasstraat").text
    assert 'data-zuster="/toezicht"' in html, "geen enkele link naar de zusterpagina is gemarkeerd"
    assert "function werkZusterLinks(" in html
    assert 'const ZUSTER_PARAM = "vestiging";' in html
    assert "${ZUSTER_PARAM}=${encodeURIComponent(id)}" in html


def test_een_onbekende_id_in_de_url_valt_terug_op_de_eerste(monkeypatch):
    """`?vergunning=` wordt gelezen, maar alleen als de id in de lijst voorkomt -- een
    verouderde of verzonnen link mag geen lege pagina en geen 404 opleveren. De keuze staat in
    `kiesId`, één plek, met de lidmaatschapstoets erin.

    De terugval zelf is in deze omgeving met Node nagelopen op de uit de pagina geknipte functie:
    bekend -> die id, onbekend -> de eerste, afwezig -> de eerste."""
    html = _client(monkeypatch).get("/wasstraat").text
    assert 'const PARAM = "vergunning";' in html
    assert "new URLSearchParams(location.search).get(PARAM)" in html
    assert "function kiesId(lijst, gevraagd)" in html
    # De lidmaatschapstoets én de terugval, in één regel -- zonder de `.some(...)` zou een
    # onbekende id gewoon doorgegeven worden aan de API en een 404 opleveren.
    assert "lijst.some(v => v.id === gevraagd)) ? gevraagd : lijst[0].id" in html
    assert "const gekozen = kiesId(" in html


def test_de_kiezer_schrijft_de_keuze_terug_in_de_url(monkeypatch):
    """Wisselen in de kiezer maakt de link deelbaar: `replaceState`, geen `pushState` -- een
    keuze in een kiezer is geen navigatie."""
    html = _client(monkeypatch).get("/wasstraat").text
    assert "history.replaceState(" in html
    assert "history.pushState(" not in html
    assert "u.searchParams.set(PARAM, id)" in html


# -- De agents als openklapbare rijen ------------------------------------------------------------

def test_de_agents_staan_als_openklapbare_rijen_en_niet_als_platte_tabel(monkeypatch):
    """Vraag van Bob: de agents transparanter maken -- klikken en dan zie je de instellingen.
    `goal` en `backstory` zaten al in `/api/wasstraat/pijplijn` en werden door de pagina
    weggegooid; dat is hetzelfde patroon als de uitlegger-bevinding uit de eindreview, waar de
    pijplijn zeven seconden rekende voor velden die de pagina niet toonde.

    Een `<details>` en niet een eigen klikafhandeling op een `div`: dan is de rij van zichzelf
    toetsenbordbereikbaar en open-/dichtklapbaar, zonder dat dat nagebouwd hoeft te worden."""
    r = _client(monkeypatch).get("/wasstraat")
    assert "<details" in r.text and "<summary" in r.text
    assert 'id="agentstabel"' not in r.text, "de platte tabel is vervangen"
    # De instellingen komen uit de API, niet uit de HTML.
    for veld in ("a.goal", "a.backstory", "a.llm"):
        assert veld in r.text, f"de agentrij toont {veld} uit /api/wasstraat/pijplijn"


def test_geen_agentnaam_of_rol_staat_hardgecodeerd_in_de_wasstraatpagina(monkeypatch):
    """Zelfde reden als bij de regels: staat een naam in de HTML, dan kan de pagina iets anders
    tonen dan de configuratie zegt -- en dan is "alleen-lezen inzicht in de configuratie" een
    holle belofte."""
    r = _client(monkeypatch).get("/wasstraat")
    for agent in ("vergunninglezer", "signaalsteller", "dossiersteller", "uitlegger",
                   "vraagsteller", "terugkoppelaar"):
        assert agent not in r.text, f"{agent} hoort uit de API te komen"


def test_de_pagina_wijst_naar_de_anatomie_voor_de_rest_van_de_techniek(monkeypatch):
    """De configuratiesectie toont de agents en taken; de drempels, bronnen en
    configuratiesleutels staan op `/onderwater`. Zonder die verwijzing is dat tweede niet te
    vinden."""
    r = _client(monkeypatch).get("/wasstraat")
    # Niet alleen via de dossierbalk (die noemt elk lid): een expliciete verwijzing vanuit de
    # configuratiesectie zelf, anders is het tweede deel van de techniek niet te vinden voor wie
    # hier staat te kijken.
    assert 'data-anatomie="/onderwater"' in r.text
