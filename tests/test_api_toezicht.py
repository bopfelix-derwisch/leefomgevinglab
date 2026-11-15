"""`/toezicht` -- herbouwd als de tweede pagina van de wasstraat/toezicht-splitsing (plan:
`docs/superpowers/plans/2026-11-14-wasstraat-en-toezicht-splitsen.md`). Drie delen: de uitkomst
van de wasstraat voor deze vergunning, de metingen bij haar waterlichaam, en de drie
werkelijkheidssignalen -- die laatste krijgen hier voor het eerst een echte context (`gemeten_
codes`, `waterlichaam`, `overschrijdingen`, `register_codes`); vóór deze taak gaf de route
`context: {}` op die vier sleutels na, en kon geen van de drie ooit vuren.

Geen netwerk hier: alle bronnen (`_toezicht_register`/`_toezicht_aquo_ref`/
`_toezicht_normenset`/`_toezicht_doelenset`/`_toezicht_metingen`/`_toezicht_gemeten_codes`/
`_stelselcatalogus`/`toezicht_context.waterlichaam_van_vestiging`) worden per test gemonkeypatcht,
net zoals in `test_api_wasstraat.py`.
"""
import time

from fastapi.testclient import TestClient

import leefomgevinglab.geluidsmeter.api as api
from leefomgevinglab.usecases import water_hub as wh
from tests.test_kmg_doelen import NORMEN, SET as DOELEN, _stof, _zink


def _client(monkeypatch):
    monkeypatch.setattr(api, "load_config", lambda *a, **k: api._config)
    return TestClient(api.app)


FIXTURE_VESTIGING = {
    "naam": "Testvestiging BV", "plaats": "Venlo", "locatie": None,
    "locatiecode": "TEST01", "vestigingsnummer_kvk": "000012345678",
    "kenmerk": None, "besluitdatum": "2020-01-01", "url": "https://example.org/vergunning",
    "voorschriften": [
        {"parameter": "Zink", "waarde": 0.5, "eenheid": "milligram per liter",
         "bemonstering": "Steekmonster", "rd": [190000.0, 350000.0]},
    ],
}

FIXTURE_AQUO_REF = {"beschikbaar": True, "geldig": {"zink": "Zn"}, "vervallen": {},
                     "vervangen_door": {}, "aantal": {}}
FIXTURE_NORMENSET_LEEG = {"beschikbaar": False, "normen": {}}
FIXTURE_DOELENSET_LEEG = {"beschikbaar": False, "waterlichamen": {}}
FIXTURE_METINGEN_LEEG = {"beschikbaar": False, "punten": []}

# Alias en twee fixtures die `test_api_wasstraat.py` hergebruikt (`/wasstraat` draait dezelfde
# standaardpijplijn, niet een tweede). `FIXTURE_NORMENSET` is de oude naam, vóór deze taak de
# normenset voor de uitlegger gaf; `/wasstraat` heeft geen van de nieuwe sleutels nodig (haar
# zeven regels vragen geen context), dus de lege normenset is daar genoeg.
FIXTURE_NORMENSET = FIXTURE_NORMENSET_LEEG

FIXTURE_VESTIGING_VERVALLEN = {
    "naam": "Zwevende-stof BV", "plaats": "Venlo", "locatie": None,
    "locatiecode": "TEST02", "vestigingsnummer_kvk": "000098765432",
    "kenmerk": "ABC/123", "besluitdatum": "2019-01-01", "url": "https://example.org/zwevend",
    "voorschriften": [
        {"parameter": "Zwevende stof", "waarde": 30.0, "eenheid": "milligram per liter"},
    ],
}
# Dezelfde naam ("zwevende stof") staat zowel in `vervallen` als -- in de echte bron -- soms in
# `geldig`; hier bewust alléén `vervallen`, zodat `aquo.verrijk` geen andere tak kan kiezen.
FIXTURE_AQUO_REF_VERVALLEN = {"beschikbaar": True, "geldig": {},
                              "vervallen": {"zwevende stof": "ZS"}, "vervangen_door": {}}

# Een vergunning waarop géén van de vijf papierbevindingen vuurt: alle drie de identificerende
# velden aanwezig (`vergunning_niet_te_vinden` zwijgt), één voorschrift met een geldige Aquo-code
# (`niet_in_referentie`/`vervallen_code` zwijgen), geen tweede grenswaarde voor dezelfde stof
# (`meerdere_grenswaarden` zwijgt) en een vrachteenheid in plaats van een concentratie
# (`vracht_onbepaald` zwijgt). De twee sentinelregels vuren wél -- `geen_geldigheidsduur` altijd,
# `niet_regime_zuiver` omdat het voorschrift een bemonsteringsregime draagt -- en dat is precies
# de toestand die `wasstraat.op_orde` waar hoort te maken (eindreview, must-fix 5+6).
FIXTURE_VESTIGING_PAPIER_OP_ORDE = {
    "naam": "Schoonpapier BV", "plaats": "Roermond", "locatie": None,
    "locatiecode": "TEST03", "vestigingsnummer_kvk": "000011112222",
    "kenmerk": "RWS-2021/1", "besluitdatum": "2021-01-01",
    "url": "https://example.org/schoonpapier",
    "voorschriften": [
        {"parameter": "Zink", "waarde": 120.0, "eenheid": "kilogram per jaar",
         "bemonstering": "Steekmonster", "rd": [190000.0, 350000.0]},
    ],
}

# Eén meetpunt op het waterlichaam van FIXTURE_VESTIGING, met zowel zink als stikstof boven de
# norm -- zink via de chemische norm (NORMEN, jaargemiddelde 7,8 ug/l), stikstof via het
# ecologische doel (DOELEN, zomergemiddelde 2,5 mg/l). Beide waarden en fixtures komen letterlijk
# uit `tests.test_kmg_doelen`, niet opnieuw verzonnen -- zie die module voor de rekensom.
_PUNT_OVERSCHREDEN = {"code": "NL80_BELFBVN", "naam": "Belfeld boven", "waterlichaam": "NL91ZM",
                      "stoffen": [_zink(jaargem=12.0), _stof(zomer=2.97)]}
FIXTURE_METINGEN_OVERSCHREDEN = {"beschikbaar": True, "punten": [_PUNT_OVERSCHREDEN]}


def _monkeypatch_bronnen(monkeypatch, register=(FIXTURE_VESTIGING,), aquo_ref=FIXTURE_AQUO_REF,
                          normenset=FIXTURE_NORMENSET_LEEG, doelenset=FIXTURE_DOELENSET_LEEG,
                          metingen=FIXTURE_METINGEN_LEEG, gemeten_codes=frozenset({"Zn"}),
                          waterlichaam=(None, None)):
    """Alle bronnen die `/api/toezicht/dossier` samen bekabelt. `gemeten_codes` bevat
    standaard de eigen stof van `FIXTURE_VESTIGING` ("Zn") -- zonder expliciete tegenbewijzen
    moet geen van de drie werkelijkheidsregels vuren, zie de negatieve controle hieronder."""
    monkeypatch.setattr(api, "_toezicht_register", lambda: list(register))
    monkeypatch.setattr(api, "_toezicht_aquo_ref", lambda: aquo_ref)
    monkeypatch.setattr(api, "_toezicht_normenset", lambda: normenset)
    monkeypatch.setattr(api, "_toezicht_doelenset", lambda: doelenset)
    monkeypatch.setattr(api, "_toezicht_metingen", lambda: metingen)
    monkeypatch.setattr(api, "_toezicht_gemeten_codes", lambda: set(gemeten_codes))
    monkeypatch.setattr(api, "_stelselcatalogus", lambda: None)
    monkeypatch.setattr(api.toezicht_context, "waterlichaam_van_vestiging",
                         lambda v, live=True, **kw: waterlichaam)


# -- Banner en taalregel (ongewijzigd t.o.v. vóór de splitsing) --------------------------------

def test_de_pagina_draagt_de_open_data_banner(monkeypatch):
    h = _client(monkeypatch).get("/toezicht").text.lower()
    assert "open data" in h
    assert "geen bevoegdheid" in h
    assert "geen oordeel" in h
    assert "zonder authenticatie" in h
    assert "zonder logging" in h


def test_de_pagina_haalt_de_taalregel_op_de_echte_html(monkeypatch):
    h = _client(monkeypatch).get("/toezicht").text.lower()
    assert "overtreding" not in h
    assert "veroorzaakt door" not in h
    assert "in strijd met" not in h


def test_een_echt_dossier_respecteert_ook_de_taalregel(monkeypatch):
    """De taalregel geldt op de data, niet alleen op de statische HTML -- vooral belangrijk voor
    `norm_overschreden_bovenstrooms`, die uitdrukkelijk niet mag zeggen dat deze vestiging de
    overschrijding veroorzaakt."""
    _monkeypatch_bronnen(monkeypatch, normenset=NORMEN, doelenset=DOELEN,
                          metingen=FIXTURE_METINGEN_OVERSCHREDEN, waterlichaam=("NL91ZM", None))
    d = _client(monkeypatch).get("/api/toezicht/dossier?vestiging=TEST01").json()
    tekst = " ".join(s.get("bewering", "") + " " + (s.get("waarom") or "") for s in d["signalen"])
    tekst_laag = tekst.lower()
    assert "overtreding" not in tekst_laag
    assert "veroorzaakt door" not in tekst_laag
    assert "in strijd met" not in tekst_laag


# -- Route, hub-lid, pagina ----------------------------------------------------------------------

def test_toezicht_is_lid_van_het_waterdossier_en_krijgt_geen_eigen_kaart(monkeypatch):
    assert wh.lid("toezicht")["pad"] == "/toezicht"
    r = _client(monkeypatch).get("/")
    assert 'href="/toezicht"' not in r.text


def test_toezichtpagina_geeft_200_met_de_subnav(monkeypatch):
    r = _client(monkeypatch).get("/toezicht")
    assert r.status_code == 200
    assert 'class="waternav"' in r.text
    assert r.text.count('aria-current="page"') == 1
    assert "__WATERNAV__" not in r.text


def test_de_configuratie_staat_niet_meer_op_toezicht(monkeypatch):
    """De pijplijn/agents-configuratie verhuisde naar `/wasstraat` (plan); `/api/toezicht/
    pijplijn` bestaat niet meer en de pagina draagt geen agententabel."""
    r = _client(monkeypatch).get("/api/toezicht/pijplijn")
    assert r.status_code == 404
    pagina = _client(monkeypatch).get("/toezicht").text.lower()
    assert "mag taalmodel" not in pagina


def test_vestigingen_endpoint_geeft_een_lijst(monkeypatch):
    _monkeypatch_bronnen(monkeypatch)
    r = _client(monkeypatch).get("/api/toezicht/vestigingen")
    assert r.status_code == 200
    d = r.json()
    assert d == [{"id": "TEST01", "locatiecode": "TEST01", "naam": "Testvestiging BV",
                  "plaats": "Venlo", "kenmerk": None}]


def test_onbekende_vestiging_geeft_404(monkeypatch):
    _monkeypatch_bronnen(monkeypatch)
    r = _client(monkeypatch).get("/api/toezicht/dossier?vestiging=BESTAAT_NIET")
    assert r.status_code == 404


# -- Alleen GET, nergens een schrijfpad -----------------------------------------------------------
#
# **405, niet `in (404, 405)`** (eindreview, kleinere bevinding 5). Deze drie tests bewaken dat de
# route bestaat én alleen leest. Met 404 erbij slaagt een test ook als de route helemaal weg is --
# dan bewaakt zij niets meer, en precies die vorm (een test die groen blijft om de verkeerde
# reden) is het defect dat dit project het meeste heeft gekost. 405 bewijst beide helften: de
# padoplossing vond de route, en FastAPI weigerde de methode.

def test_geen_post_op_vestigingen(monkeypatch):
    _monkeypatch_bronnen(monkeypatch)
    r = _client(monkeypatch).post("/api/toezicht/vestigingen")
    assert r.status_code == 405, "405 = route bestaat, methode geweigerd; 404 zou ook slagen als de route weg was"


def test_geen_post_op_dossier(monkeypatch):
    _monkeypatch_bronnen(monkeypatch)
    r = _client(monkeypatch).post("/api/toezicht/dossier?vestiging=TEST01")
    assert r.status_code == 405


def test_geen_put_nergens(monkeypatch):
    _monkeypatch_bronnen(monkeypatch)
    client = _client(monkeypatch)
    assert client.put("/api/toezicht/vestigingen").status_code == 405
    assert client.put("/api/toezicht/dossier?vestiging=TEST01").status_code == 405


# -- Context werkelijk gevuld: de kern van deze taak ---------------------------------------------

def test_zonder_context_vuurt_geen_van_de_drie_werkelijkheidsregels(monkeypatch):
    """De negatieve controle: lege metingen/doelen/normen, geen waterlichaam gevonden, en de
    eigen stof van de vestiging ("Zn") wél in `gemeten_codes` -- geen van de drie regels heeft
    dan iets om op te vuren. Dit bewijst dat de volgende test's resultaat echt van de bekabeling
    afhangt, en niet van regels die altijd vuren zodra er een vestiging is."""
    _monkeypatch_bronnen(monkeypatch)
    d = _client(monkeypatch).get("/api/toezicht/dossier?vestiging=TEST01").json()
    assert d["signalen"] == []


def test_de_drie_werkelijkheidsregels_vuren_met_een_echte_context(monkeypatch):
    """De hoofdtest van deze taak: met een echt waterlichaam, een echte toetsing en echte
    registercodes vuren alle drie de werkelijkheidsregels voor dezelfde vestiging."""
    _monkeypatch_bronnen(monkeypatch, normenset=NORMEN, doelenset=DOELEN,
                          metingen=FIXTURE_METINGEN_OVERSCHREDEN, waterlichaam=("NL91ZM", None),
                          gemeten_codes={"Ntot"})  # "Zn" zit er niet in
    d = _client(monkeypatch).get("/api/toezicht/dossier?vestiging=TEST01").json()
    regels = {s["regel"] for s in d["signalen"]}
    assert regels == {"geen_onafhankelijke_meting", "norm_overschreden_bovenstrooms",
                       "stof_buiten_register"}, f"niet alle drie vuren: {regels}"

    overschreden = next(s for s in d["signalen"] if s["regel"] == "norm_overschreden_bovenstrooms")
    stoffen_in_bewijs = {b["stof"] for b in overschreden["bewijs"]}
    assert stoffen_in_bewijs == {"Zn", "Ntot"}

    register_signaal = next(s for s in d["signalen"] if s["regel"] == "stof_buiten_register")
    # "Zn" staat wél in het register (de vestiging heeft een zinkvoorschrift) -- alleen "Ntot"
    # (stikstof) komt in geen enkele vergunning voor, dus alleen die hoort in dit bewijs.
    assert {b["stof"] for b in register_signaal["bewijs"]} == {"Ntot"}

    meting_signaal = next(s for s in d["signalen"] if s["regel"] == "geen_onafhankelijke_meting")
    assert all(b.get("aquo") == "Zn" or b.get("parameter") == "Zink"
               for b in meting_signaal["bewijs"])


def test_de_context_komt_niet_meer_terug_als_voorbehoud_als_zij_gevuld_is(monkeypatch):
    _monkeypatch_bronnen(monkeypatch, normenset=NORMEN, doelenset=DOELEN,
                          metingen=FIXTURE_METINGEN_OVERSCHREDEN, waterlichaam=("NL91ZM", None),
                          gemeten_codes={"Ntot"})
    d = _client(monkeypatch).get("/api/toezicht/dossier?vestiging=TEST01").json()
    voorbehouden_tekst = " ".join(d["voorbehouden"])
    assert "gemeten_codes" not in voorbehouden_tekst
    assert "register_codes" not in voorbehouden_tekst
    assert "lozer bovenstrooms' is niet getoetst" not in voorbehouden_tekst


# -- De wasstraat-uitkomst: context, geen opdracht -----------------------------------------------

def test_de_wasstraat_uitkomst_telt_de_papierbevindingen_van_dezelfde_vestiging(monkeypatch):
    """`FIXTURE_VESTIGING` draagt een concentratiegrens zonder debietvoorschrift (regel 5) en
    mist haar `kenmerk` (regel 8) -- precies twee papierbevindingen, puur uit het papier, los van
    de context die deze route voor de drie werkelijkheidsregels aanlevert.

    **Eindreview, must-fix 5+6.** Deze test toetste eerder `aantal_open >= 1`, en dat was op elke
    vergunning in het register waar: `geen_geldigheidsduur` vuurt op 69 van de 69. Een exact
    getal legt nu vast welke regels echt meetellen -- de twee sentinelregels vuren hier óók (het
    voorschrift draagt een bemonsteringsregime) en mogen er niet bij opgeteld worden."""
    _monkeypatch_bronnen(monkeypatch)
    d = _client(monkeypatch).get("/api/toezicht/dossier?vestiging=TEST01").json()
    assert d["wasstraat"]["pad"] == "/wasstraat"
    assert d["wasstraat"]["aantal_open"] == 2
    assert d["wasstraat"]["op_orde"] is False


def test_de_wasstraat_uitkomst_kan_op_orde_zijn_op_een_echte_vergunning(monkeypatch):
    """De True-tak van `op_orde`, op een vergunning die de twee sentinelvoorbehouden wél draagt.

    Vóór must-fix 5+6 was deze tak onbereikbaar en dus dode code op `toezicht.html`: de bodem van
    `aantal_open` bestond uit `geen_geldigheidsduur` (69/69) en `niet_regime_zuiver` (68/69).
    Hier vuren beide -- de assertie eronder bewijst dat -- en toch is het papier op orde, want
    geen van de vijf papierbevindingen vuurt."""
    _monkeypatch_bronnen(monkeypatch, register=(FIXTURE_VESTIGING_PAPIER_OP_ORDE,))
    d = _client(monkeypatch).get("/api/toezicht/dossier?vestiging=TEST03").json()
    assert d["wasstraat"]["aantal_open"] == 0
    assert d["wasstraat"]["op_orde"] is True

    # Controle dat de twee sentinelregels hier echt vuren -- anders zou deze test de True-tak op
    # een lege signaallijst toetsen, precies de toestand die het register niet kent.
    papier = _client(monkeypatch).get("/api/wasstraat/dossier?vergunning=TEST03").json()
    assert papier["signalen"] == []
    assert papier["telling"]["aantal_voorbehouden"] == 2


# -- De twee voorbehouden over de richting (must-fix 7 en 8) -------------------------------------

def test_het_dossier_benoemt_dat_de_richting_binnen_een_waterlichaam_niet_vaststaat(monkeypatch):
    """Must-fix 7: het meetpunt van `FIXTURE_METINGEN_OVERSCHREDEN` ligt in NL91ZM, net als de
    vestiging zelf -- dan is de bewering "met deze vestiging bovenstrooms" niet vastgesteld, want
    `toerekening.is_bovenstrooms(X, X)` is per definitie waar."""
    _monkeypatch_bronnen(monkeypatch, normenset=NORMEN, doelenset=DOELEN,
                          metingen=FIXTURE_METINGEN_OVERSCHREDEN, waterlichaam=("NL91ZM", None),
                          gemeten_codes={"Ntot"})
    d = _client(monkeypatch).get("/api/toezicht/dossier?vestiging=TEST01").json()
    assert any(s["regel"] == "norm_overschreden_bovenstrooms" for s in d["signalen"])
    treffers = [v for v in d["voorbehouden"] if "NL91ZM" in v and "niet vastgesteld" in v]
    assert len(treffers) == 1, d["voorbehouden"]
    assert "NL80_BELFBVN" in treffers[0]


def test_het_dossier_benoemt_een_waterlichaam_zonder_plaats_in_de_stroomvolgorde(monkeypatch):
    """Must-fix 8: `NL90_1` draagt live 18 van de 62 vergunningen en staat in
    `toerekening.ZONDER_POSITIE`. De regel kan daar niet vuren, en dat is iets anders dan geen
    signaal -- het dossier zei er niets over zolang het waterlichaam gevuld was."""
    _monkeypatch_bronnen(monkeypatch, normenset=NORMEN, doelenset=DOELEN,
                          metingen=FIXTURE_METINGEN_OVERSCHREDEN, waterlichaam=("NL90_1", None),
                          gemeten_codes={"Ntot"})
    d = _client(monkeypatch).get("/api/toezicht/dossier?vestiging=TEST01").json()
    assert not any(s["regel"] == "norm_overschreden_bovenstrooms" for s in d["signalen"])
    treffers = [v for v in d["voorbehouden"] if "NL90_1" in v]
    assert len(treffers) == 1, d["voorbehouden"]
    assert "niet te bepalen" in treffers[0]
    assert "zonder stroomschema niet te plaatsen" in treffers[0], "de reden komt uit toerekening"


# -- De metingen bij het waterlichaam -------------------------------------------------------------

def test_metingen_zonder_waterlichaam_is_leeg_met_reden(monkeypatch):
    _monkeypatch_bronnen(monkeypatch, waterlichaam=(None, "geen coördinaat in de bron"))
    d = _client(monkeypatch).get("/api/toezicht/dossier?vestiging=TEST01").json()
    assert d["metingen"]["waterlichaam"] is None
    assert d["metingen"]["rijen"] == []
    assert d["metingen"]["reden_geen_waterlichaam"] == "geen coördinaat in de bron"


def test_metingen_bij_een_bekend_waterlichaam_toont_de_rijen(monkeypatch):
    _monkeypatch_bronnen(monkeypatch, normenset=NORMEN, doelenset=DOELEN,
                          metingen=FIXTURE_METINGEN_OVERSCHREDEN, waterlichaam=("NL91ZM", None))
    d = _client(monkeypatch).get("/api/toezicht/dossier?vestiging=TEST01").json()
    assert d["metingen"]["waterlichaam"] == "NL91ZM"
    codes = {r["stof"]["code"] for r in d["metingen"]["rijen"]}
    assert codes == {"Zn", "Ntot"}
    assert d["kaart"]["waterlichaam"] == {"waarde": "NL91ZM", "zekerheid": "afgeleid"}


# -- Must-fix 2 van de eindreview: de gekozen vestiging staat in de URL ----------------------

def test_de_link_naar_de_zusterpagina_draagt_de_gekozen_id(monkeypatch):
    """De link droeg alleen `/wasstraat`, zonder id, en geen van beide pagina's las een
    queryparameter: wie bij Solvay las dat er bevindingen openstaan "voor deze vergunning" en
    doorklikte, kreeg de eerste vergunning uit de lijst (Mebin BV) te zien en dacht dat het
    Solvay was.

    Deze test staat op de geserveerde HTML, want de keuze gebeurt in de browser. Wat zij vastlegt
    is het mechanisme: er is een `data-zuster`-link, er is één plek die daar de id in zet, en die
    gebruikt de parameternaam van de zuster-API (`vergunning`) -- niet een derde vocabulaire."""
    html = _client(monkeypatch).get("/toezicht").text
    assert 'data-zuster="/wasstraat"' in html, "geen enkele link naar de zusterpagina is gemarkeerd"
    assert "function werkZusterLinks(" in html
    assert 'const ZUSTER_PARAM = "vergunning";' in html
    assert "${ZUSTER_PARAM}=${encodeURIComponent(id)}" in html


def test_een_onbekende_id_in_de_url_valt_terug_op_de_eerste(monkeypatch):
    """`?vestiging=` wordt gelezen, maar alleen als de id in de lijst voorkomt -- een
    verouderde of verzonnen link mag geen lege pagina en geen 404 opleveren. De keuze staat in
    `kiesId`, één plek, met de lidmaatschapstoets erin.

    De terugval zelf is in deze omgeving met Node nagelopen op de uit de pagina geknipte functie:
    bekend -> die id, onbekend -> de eerste, afwezig -> de eerste."""
    html = _client(monkeypatch).get("/toezicht").text
    assert 'const PARAM = "vestiging";' in html
    assert "new URLSearchParams(location.search).get(PARAM)" in html
    assert "function kiesId(lijst, gevraagd)" in html
    # De lidmaatschapstoets én de terugval, in één regel -- zonder de `.some(...)` zou een
    # onbekende id gewoon doorgegeven worden aan de API en een 404 opleveren.
    assert "lijst.some(v => v.id === gevraagd)) ? gevraagd : lijst[0].id" in html
    assert "const gekozen = kiesId(" in html


def test_de_kiezer_schrijft_de_keuze_terug_in_de_url(monkeypatch):
    """Wisselen in de kiezer maakt de link deelbaar: `replaceState`, geen `pushState` -- een
    keuze in een kiezer is geen navigatie."""
    html = _client(monkeypatch).get("/toezicht").text
    assert "history.replaceState(" in html
    assert "history.pushState(" not in html
    assert "u.searchParams.set(PARAM, id)" in html


# -- De agents die deze run echt hebben gedraaid -------------------------------------------------

def test_het_dossier_noemt_de_agents_die_in_deze_run_hebben_gedraaid(monkeypatch):
    """`/toezicht` legt de agents uit die hebben gedraaid, niet de agents die er zijn. Zes staan
    in `agents.yaml`, vier draaien in de standaardpijplijn -- en `vraagsteller` en
    `terugkoppelaar` hebben geen taak, dus die mogen hier niet opduiken. Zou de route de
    configuratie als bron nemen in plaats van de runlog, dan beweerde de pagina dat er zes hebben
    gedraaid: precies de mocht/heeft-verwarring die dit dossier duur heeft betaald."""
    _monkeypatch_bronnen(monkeypatch)
    d = _client(monkeypatch).get("/api/toezicht/dossier?vestiging=TEST01").json()
    agents = d["agents_gedraaid"]
    assert [a["id"] for a in agents] == [s["agent"] for s in d["runlog"]["stappen"]], (
        "de lijst moet de runlog volgen, in dezelfde volgorde")
    assert {"vraagsteller", "terugkoppelaar"}.isdisjoint({a["id"] for a in agents}), (
        "deze twee hebben geen taak in de standaardpijplijn en kunnen dus niet gedraaid hebben")
    for a in agents:
        assert a["role"] and a["goal"], f"{a['id']} mist zijn uitleg uit de configuratie"
        assert a["stappen"], f"{a['id']} draaide, dus hij heeft een stapnummer"


def test_geen_enkele_gedraaide_agent_heeft_het_taalmodel_echt_aangeroepen(monkeypatch):
    """De route geeft `llm=None` door, dus `llm_aangeroepen` is overal False -- terwijl `mag_llm`
    bij de uitlegger True is. Dat die twee verschillen is de bedoeling en niet een fout: het is
    het verschil tussen mogen en doen, op één pagina naast elkaar leesbaar."""
    _monkeypatch_bronnen(monkeypatch)
    d = _client(monkeypatch).get("/api/toezicht/dossier?vestiging=TEST01").json()
    agents = {a["id"]: a for a in d["agents_gedraaid"]}
    assert all(not a["llm_aangeroepen"] for a in agents.values())
    assert agents["uitlegger"]["mag_llm"] is True, (
        "mocht wel, deed niet -- verdwijnt dit onderscheid, dan is de bewaking weg")
    assert agents["signaalsteller"]["mag_llm"] is False


# -- De gedraaide agents op de pagina ------------------------------------------------------------

def test_de_pagina_toont_de_agents_die_gedraaid_hebben_en_typt_ze_niet(monkeypatch):
    """Vraag van Bob: op `/toezicht` ook uitleg van de agents, "als die gebruikt zijn". Dat is
    precies de goede formulering, want gebruik en gerechtigdheid zijn hier twee dingen:
    `/wasstraat` toont de configuratie (wat mág), deze pagina alleen wat in déze run werkelijk is
    gebeurd. De lijst komt uit de runlog, dus staat geen enkele agentnaam in de HTML."""
    r = _client(monkeypatch).get("/toezicht")
    assert "<details" in r.text and "<summary" in r.text
    assert "a.goal" in r.text, "de opengeklapte rij toont het doel uit de configuratie"
    assert "llm_aangeroepen" in r.text, "gebruik hoort zichtbaar, niet alleen gerechtigdheid"
    for agent in ("vergunninglezer", "signaalsteller", "dossiersteller", "uitlegger"):
        assert agent not in r.text, f"{agent} hoort uit /api/toezicht/dossier te komen"


def test_de_pagina_wijst_naar_de_anatomie(monkeypatch):
    """De volledige configuratie staat niet op deze pagina (die is voor de toezichthouder), maar
    moet wel te vinden zijn."""
    r = _client(monkeypatch).get("/toezicht")
    assert 'data-anatomie="/onderwater"' in r.text


# -- /api/toezicht/vraag: de brug tussen de twee lezers ------------------------------------------
#
# Geen enkele test hier roept een taalmodel aan: `vraag.stel` neemt `llm` als geïnjecteerde
# functie, en de route bouwt die met `vraag.taalmodel`. Die ene regel wordt gemonkeypatcht, zodat
# de SPARQL vastligt en de rest van het pad (validatie, uitvoering, antwoordvorm) echt draait.

def _monkeypatch_graaf(monkeypatch, sparql: str):
    """Alle bronnen voor de register-brede graaf, plus een 'taalmodel' dat één vaste query geeft.
    Ook de cache wordt leeggemaakt: anders bepaalt de testvolgorde wat er in de graaf zit."""
    _monkeypatch_bronnen(monkeypatch)
    monkeypatch.setattr(api.kmg_service, "_waterlichaam_per_vergunning",
                        lambda *a, **k: ({}, {}))
    monkeypatch.setattr(api.toezicht_vraag, "taalmodel",
                        lambda *a, **k: (lambda prompt: sparql))
    api._TOEZICHTGRAAF.update({"graaf": None, "gebouwd_op": 0.0, "triples": 0,
                                "vestigingen": 0})
    return _client(monkeypatch)


_VRAAG_SPARQL = (
    "PREFIX t: <https://leefomgevinglab.felixisfelix.com/toezicht#> "
    "SELECT ?regel WHERE { ?s a t:Signaal ; t:regel ?regel } LIMIT 50")


def test_een_vraag_levert_de_uitgevoerde_query_en_de_rijen(monkeypatch):
    client = _monkeypatch_graaf(monkeypatch, _VRAAG_SPARQL)
    d = client.post("/api/toezicht/vraag", json={"vraag": "welke signalen zijn er?"}).json()
    assert d["beschikbaar"] is True
    assert d["sparql"] == _VRAAG_SPARQL, (
        "de uitgevoerde query moet letterlijk zijn wat de lezer te zien krijgt")
    assert d["rijen"], "de graaf draagt signalen, dus deze query hoort rijen te geven"
    assert d["disclaimer"] and d["vangnet"] and d["bron"]


def test_de_graafmeta_is_afgeleid_en_niet_getypt(monkeypatch):
    """De pagina mag vertellen hoe groot de graaf is; dat getal komt uit de graaf zelf, zodat zij
    niet kan beweren dat er meer in zit dan er in zit."""
    client = _monkeypatch_graaf(monkeypatch, _VRAAG_SPARQL)
    d = client.post("/api/toezicht/vraag", json={"vraag": "x"}).json()
    assert d["graaf"]["triples"] > 0
    assert d["graaf"]["vestigingen"] > 0


def test_de_brugvraag_over_de_twee_lezers_werkt_echt(monkeypatch):
    """**De vraag waar dit hele stuk om begonnen is.** Papier en werkelijkheid in één query, op
    dezelfde vestiging. Lukt dit niet, dan is de brug er alleen in naam."""
    brug = ("PREFIX t: <https://leefomgevinglab.felixisfelix.com/toezicht#> "
            "SELECT ?regel WHERE { ?v a t:Vestiging ; t:heeftSignaal ?p . "
            "?p t:laag \"papier\" ; t:rol \"bevinding\" ; t:regel ?regel } LIMIT 50")
    client = _monkeypatch_graaf(monkeypatch, brug)
    d = client.post("/api/toezicht/vraag", json={"vraag": "welke papierbevindingen?"}).json()
    assert d["beschikbaar"] is True, d
    assert d["rijen"], "geen papierbevinding in de register-brede graaf"


def test_een_schrijfquery_wordt_geweigerd_voordat_er_iets_wordt_uitgevoerd(monkeypatch):
    """De validator is het hele punt van deze route. Een taalmodel dat een UPDATE voorstelt mag
    niet tot uitvoering komen, en de gebruiker hoort te zien wat er geweigerd is -- niet een
    stille 500 en niet een leeg antwoord dat op "geen resultaten" lijkt."""
    kwaad = "INSERT DATA { <a> <b> <c> }"
    client = _monkeypatch_graaf(monkeypatch, kwaad)
    d = client.post("/api/toezicht/vraag", json={"vraag": "verwijder alles"}).json()
    assert d["beschikbaar"] is False
    assert d["rijen"] == []
    assert d["sparql"] == kwaad, "de geweigerde query hoort zichtbaar te zijn"
    assert "niet veilig" in d["antwoord"].lower()


def test_een_select_zonder_limit_wordt_geweigerd(monkeypatch):
    client = _monkeypatch_graaf(monkeypatch, "SELECT * WHERE { ?s ?p ?o }")
    d = client.post("/api/toezicht/vraag", json={"vraag": "alles"}).json()
    assert d["beschikbaar"] is False and d["rijen"] == []


def test_een_lege_vraag_geeft_422_en_raakt_het_model_niet(monkeypatch):
    client = _monkeypatch_graaf(monkeypatch, _VRAAG_SPARQL)
    assert client.post("/api/toezicht/vraag", json={"vraag": "   "}).status_code == 422


def test_de_graaf_wordt_hergebruikt_en_niet_per_vraag_opnieuw_gebouwd(monkeypatch):
    """Het bouwen kost live ~8 s, bijna helemaal aan het opzoeken van het waterlichaam per
    vergunning. Zonder cache betaalt elke vraag die rekening opnieuw."""
    client = _monkeypatch_graaf(monkeypatch, _VRAAG_SPARQL)
    gebouwd = []
    echte_bouw = api.toezicht_graaf.bouw
    monkeypatch.setattr(api.toezicht_graaf, "bouw",
                        lambda *a, **k: (gebouwd.append(1), echte_bouw(*a, **k))[1])
    for _ in range(3):
        assert client.post("/api/toezicht/vraag", json={"vraag": "x"}).status_code == 200
    assert len(gebouwd) == 1, f"graaf {len(gebouwd)} keer gebouwd in plaats van één keer"


def test_de_pagina_labelt_een_geweigerde_query_niet_als_uitgevoerd(monkeypatch):
    """Een query die de validator weigert, heeft niets op de graaf gedaan. Hem "Uitgevoerde
    query" noemen zou de lezer precies het omgekeerde vertellen van wat er gebeurde -- en op een
    pagina die haar transparantie als belofte voert is dat geen cosmetisch verschil."""
    r = _client(monkeypatch).get("/toezicht")
    assert "Geweigerde query" in r.text
    assert "d.beschikbaar === false" in r.text, "het label hangt aan het echte veld"


def test_de_vraagbox_toont_de_uitgevoerde_query_en_het_voorbehoud(monkeypatch):
    """Dezelfde transparantie als /afval en /datavraag: de query zichtbaar, en het antwoord
    uitdrukkelijk indicatief."""
    r = _client(monkeypatch).get("/toezicht")
    assert "/api/toezicht/vraag" in r.text
    for veld in ("d.sparql", "d.disclaimer", "d.vangnet", "d.rijen"):
        assert veld in r.text, veld


def test_de_pagina_zegt_dat_de_vraagbox_de_enige_plek_met_een_taalmodel_is(monkeypatch):
    """De dossierroutes geven `llm=None` door en de rest van deze pagina is deterministisch. Die
    grens is de kern van dit lab, dus moet de pagina zeggen waar zij ligt zodra er één plek is
    waar wél een model draait -- anders wordt "geen taalmodel" stil onwaar."""
    r = _client(monkeypatch).get("/toezicht")
    assert "enige plek op deze pagina waar een taalmodel draait" in r.text


def test_de_vraag_loopt_door_de_vraagsteller_agent_en_niet_om_hem_heen(monkeypatch):
    """**Waarom dit telt.** `vraagsteller` heeft geen taak in `tasks.yaml`, dus kon deze route
    `vraag.stel` ook rechtstreeks aanroepen. Dan zou `agents.yaml` voor dit pad niets bepalen:
    de route gaf een taalmodel door ongeacht wat er in de configuratie staat, en de runlog zou de
    stap niet zien. Op een pagina die haar configuratie als transparantie presenteert, is dat het
    verschil tussen bindend en decoratief."""
    client = _monkeypatch_graaf(monkeypatch, _VRAAG_SPARQL)
    d = client.post("/api/toezicht/vraag", json={"vraag": "welke signalen?"}).json()
    stappen = d["runlog"]["stappen"]
    assert [s["agent"] for s in stappen] == ["vraagsteller"]
    assert stappen[0]["tool"] == "vraag_stellen"
    assert stappen[0]["llm"] is True, (
        "de vraagsteller heeft een llm-sleutel en de query is door het model gemaakt, dus de "
        "runlog hoort gebruik te melden")
    assert [a["id"] for a in d["agents_gedraaid"]] == ["vraagsteller"]
    assert d["agents_gedraaid"][0]["mag_llm"] is True


def test_de_vraagsteller_krijgt_geen_model_als_zijn_configuratie_er_geen_noemt(monkeypatch,
                                                                                tmp_path):
    """De §4.4-grens geldt ook hier. Haal de `llm`-sleutel uit de configuratie en er mag geen
    model meer aan te pas komen -- de vraag levert dan geen query op in plaats van stil toch het
    model te gebruiken. Zonder deze bewaking is de belofte van dit lab via één route te
    ontlopen."""
    import yaml
    agents = yaml.safe_load(open(api.TOEZICHT_AGENTS_PAD, encoding="utf-8"))
    agents["vraagsteller"].pop("llm", None)
    pad = tmp_path / "agents.yaml"
    pad.write_text(yaml.safe_dump(agents), encoding="utf-8")
    monkeypatch.setattr(api, "TOEZICHT_AGENTS_PAD", str(pad))

    client = _monkeypatch_graaf(monkeypatch, _VRAAG_SPARQL)
    d = client.post("/api/toezicht/vraag", json={"vraag": "welke signalen?"}).json()
    assert d["runlog"]["stappen"][0]["llm"] is False, "geen sleutel, dus geen model"
    assert d["beschikbaar"] is False, (
        "zonder model kan er geen query gemaakt worden; dat hoort eerlijk 'niet beschikbaar' te "
        "zijn in plaats van een stille lege uitkomst")


def test_de_vraagbox_toont_voortgang_tijdens_het_wachten(monkeypatch):
    """Het lokale taalmodel doet er ~10 s over, en de eerste vraag na een herstart bouwt
    bovendien de graaf op (~8 s extra). Eén stilstaande regel tekst is in die tijd niet van
    kapot te onderscheiden -- en dat was precies de melding: "de vraag werkt niet". De status
    tikt daarom mee en zegt bij de eerste vraag expliciet dat die het langst duurt."""
    r = _client(monkeypatch).get("/toezicht")
    assert "setInterval" in r.text, "een stilstaande status leest als vastgelopen"
    assert "eerste vraag duurt het langst" in r.text
    assert 'textContent = "Bezig…"' in r.text, "de knop hoort ook te laten zien dat hij loopt"


# -- De opgebouwde graaf: bestand, live, en verouderd ------------------------------------------
#
# Bob's vraag: is het niet beter de hele database op te bouwen en er een graaf over te zetten?
# Ja -- niet voor de snelheid (inlezen ~4 s tegen ~9 s live bouwen, op een vraag die ~10 s aan het
# taalmodel besteedt) maar voor **herleidbaarheid** (een bestand draagt een datum, dus een antwoord
# is te herleiden tot een versie van het register) en **robuustheid** (de vraagweg blijft werken
# als de Atlas onbereikbaar is). Deze tests leggen de drie trappen vast.

def _schrijf_graaf(tmp_path, monkeypatch, triples: int = 3):
    """Een klein graafbestand op schijf, plus de configuratie die ernaar wijst."""
    from leefomgevinglab.ld import store
    from leefomgevinglab.usecases.toezicht import graaf as graaf_mod
    g = graaf_mod.bouw([{**FIXTURE_VESTIGING, "naam": f"Uit het bestand {i}"}
                         for i in range(triples)], None, None, FIXTURE_AQUO_REF, context={})
    store.save_graph(g, str(tmp_path), naam="toezicht.ttl")
    cfg = dict(api._config.get("leefomgevinglab", {}))
    cfg["toezicht"] = {"graaf_pad": str(tmp_path / "toezicht.ttl"),
                        "graaf_max_ouderdom_dagen": 7}
    monkeypatch.setitem(api._config, "leefomgevinglab", cfg)
    return g


def test_de_route_leest_de_opgebouwde_graaf_in_plaats_van_live_te_bouwen(monkeypatch, tmp_path):
    """Met een bestand op schijf hoeft de Atlas niet bevraagd te worden. Dat is de robuustheid
    waar het om gaat: valt de bron weg, dan blijft de vraagweg werken en zegt hij van wanneer
    zijn beeld is."""
    client = _monkeypatch_graaf(monkeypatch, _VRAAG_SPARQL)
    _schrijf_graaf(tmp_path, monkeypatch)
    api._TOEZICHTGRAAF.update({"graaf": None, "gebouwd_op": 0.0, "bron": None, "telling": {}})
    # Live bouwen zou hierop stuklopen -- dus als de route tóch antwoordt, kwam hij van schijf.
    monkeypatch.setattr(api, "_toezicht_register",
                        lambda: (_ for _ in ()).throw(AssertionError("live gebouwd")))

    d = client.post("/api/toezicht/vraag", json={"vraag": "x"}).json()
    assert d["graaf"]["bron"] == "bestand"
    assert d["graaf"]["triples"] > 0
    assert d["graaf"]["vestigingen"] == 3


def test_zonder_bestand_bouwt_de_route_live_en_zegt_dat_ook(monkeypatch, tmp_path):
    """Een ontbrekend bestand is de terugval, geen fout -- maar de pagina moet wel kunnen zeggen
    waar haar antwoord vandaan komt."""
    client = _monkeypatch_graaf(monkeypatch, _VRAAG_SPARQL)
    cfg = dict(api._config.get("leefomgevinglab", {}))
    cfg["toezicht"] = {"graaf_pad": str(tmp_path / "bestaat-niet.ttl")}
    monkeypatch.setitem(api._config, "leefomgevinglab", cfg)
    api._TOEZICHTGRAAF.update({"graaf": None, "gebouwd_op": 0.0, "bron": None, "telling": {}})

    d = client.post("/api/toezicht/vraag", json={"vraag": "x"}).json()
    assert d["graaf"]["bron"] == "live"
    assert d["graaf"]["triples"] > 0


def test_een_oude_graaf_wordt_gebruikt_maar_luid_als_oud_gemeld(monkeypatch, tmp_path):
    """**De kern van het risico van persisteren.** Een oud bestand serveren alsof het actueel is,
    is erger dan langzaam zijn: de lezer krijgt een antwoord over het register van vorige maand
    en niets zegt dat. Het wordt dus wél gebruikt (beter een herleidbaar oud antwoord dan geen
    antwoord) maar met `verouderd` aan, en de pagina zet er een zichtbare waarschuwing bij met
    het commando om hem opnieuw te bouwen."""
    import os
    client = _monkeypatch_graaf(monkeypatch, _VRAAG_SPARQL)
    _schrijf_graaf(tmp_path, monkeypatch)
    pad = tmp_path / "toezicht.ttl"
    oud = time.time() - 30 * 86400
    os.utime(pad, (oud, oud))
    api._TOEZICHTGRAAF.update({"graaf": None, "gebouwd_op": 0.0, "bron": None, "telling": {}})

    d = client.post("/api/toezicht/vraag", json={"vraag": "x"}).json()
    g = d["graaf"]
    assert g["bron"] == "bestand", "een oude graaf wordt gebruikt, niet geweigerd"
    assert g["verouderd"] is True
    assert g["ouderdom_dagen"] >= 29
    assert g["opnieuw_bouwen"].endswith("22_bouw_toezichtgraaf.py"), (
        "de melding moet zeggen wat eraan te doen is, niet alleen dát het oud is")


def test_de_pagina_waarschuwt_zichtbaar_bij_een_oude_graaf(monkeypatch):
    r = _client(monkeypatch).get("/toezicht")
    assert "graafoud" in r.text
    assert "ouder dan" in r.text
    assert "22_bouw_toezichtgraaf.py" in r.text or "g.opnieuw_bouwen" in r.text


def test_de_pagina_noemt_altijd_waar_de_graaf_vandaan_komt_en_van_wanneer(monkeypatch):
    """Herkomst is de hele reden om te persisteren; hem niet tonen zou de winst weggooien."""
    r = _client(monkeypatch).get("/toezicht")
    assert "graafvoet" in r.text
    for veld in ("g.gebouwd_op", "g.bron", "g.signalen", "g.ouderdom_dagen"):
        assert veld in r.text, veld
