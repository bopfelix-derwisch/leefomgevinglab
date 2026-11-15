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

def test_geen_post_op_vestigingen(monkeypatch):
    _monkeypatch_bronnen(monkeypatch)
    r = _client(monkeypatch).post("/api/toezicht/vestigingen")
    assert r.status_code in (404, 405)


def test_geen_post_op_dossier(monkeypatch):
    _monkeypatch_bronnen(monkeypatch)
    r = _client(monkeypatch).post("/api/toezicht/dossier?vestiging=TEST01")
    assert r.status_code in (404, 405)


def test_geen_put_nergens(monkeypatch):
    _monkeypatch_bronnen(monkeypatch)
    client = _client(monkeypatch)
    assert client.put("/api/toezicht/vestigingen").status_code in (404, 405)
    assert client.put("/api/toezicht/dossier?vestiging=TEST01").status_code in (404, 405)


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
