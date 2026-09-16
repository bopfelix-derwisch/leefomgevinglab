import pytest

from leefomgevinglab.usecases.gebruiksruimte import gebied, regels, ruimte, service


# ---------- gebied en register ----------

def test_drie_locaties_aan_hetzelfde_waterlichaam():
    assert len(gebied.LOCATIES) >= 3
    assert {l["waterlichaam"] for l in gebied.LOCATIES.values()} == {"IJssel"}
    # verschillende gemeenten en provincies: de regels verschillen, het water niet
    assert len({l["gemeente"] for l in gebied.LOCATIES.values()}) >= 3


def test_waterlichaam_heeft_norm_en_achtergrond_per_parameter():
    for p in gebied.WATERLICHAAM["parameters"]:
        assert p["norm_mg_l"] > 0 and p["achtergrond_mg_l"] >= 0
        assert p["naam"] and "zzs" in p


def test_er_is_minstens_een_parameter_waar_de_norm_al_overschreden_is():
    """Zonder zo'n parameter mist de case zijn scherpste uitkomst."""
    vol = [p for p in gebied.WATERLICHAAM["parameters"] if p["achtergrond_mg_l"] >= p["norm_mg_l"]]
    assert vol, "verwacht een parameter zonder ruimte"


def test_register_bevat_bestaande_vergunningen_met_vrachten():
    assert len(gebied.REGISTER) >= 4
    namen = {v["naam"] for v in gebied.REGISTER}
    assert len(namen) == len(gebied.REGISTER)
    for v in gebied.REGISTER:
        assert v["debiet_m3_per_uur"] > 0 and v["concentraties"]
        onbekend = set(v["concentraties"]) - {p["naam"] for p in gebied.WATERLICHAAM["parameters"]}
        assert onbekend == set(), f"{v['naam']}: {onbekend}"


# ---------- regels en hun werking ----------

def test_werking_wordt_bepaald_per_regelingtype():
    assert regels.werking("Omgevingsplan") == "direct"
    assert regels.werking("AMvB") == "direct"
    assert regels.werking("Programma") == "indirect"
    assert regels.werking("Omgevingsvisie") == "indirect"


def test_onbekend_type_valt_niet_stil_weg():
    assert regels.werking("Iets Nieuws") == "onbekend"


def test_waterschapsverordening_geldt_niet_op_rijkswater():
    """De verordening staat wél op de locatie, maar raakt deze lozing niet."""
    r = regels.duiding({"type": "Waterschapsverordening", "titel": "x"}, rijkswater=True)
    assert r["van_toepassing"] is False and "rijkswater" in r["betekenis"].lower()
    r2 = regels.duiding({"type": "Waterschapsverordening", "titel": "x"}, rijkswater=False)
    assert r2["van_toepassing"] is True


def test_natura2000_werkt_indirect_door():
    r = regels.duiding({"type": "Aanwijzingsbesluit N2000", "titel": "Rijntakken"}, rijkswater=True)
    assert r["werking"] == "indirect" and r["van_toepassing"] is True


def test_regels_zonder_live_geven_een_lege_maar_geldige_lijst():
    uit = regels.regels_op_locatie(210500.0, 458500.0, rijkswater=True, live=False)
    assert uit["live"] is False and uit["regelingen"] == []
    assert uit["bron"]


def test_regels_degraderen_als_het_dso_wegvalt():
    def kapot(rd):
        raise OSError("geen netwerk")

    uit = regels.regels_op_locatie(210500.0, 458500.0, rijkswater=True, live=True, _haal=kapot)
    assert uit["live"] is True and uit["status"] == "onbereikbaar"
    assert uit["regelingen"] == []


# ---------- gebruiksruimte ----------

def _voornemen(debiet=420):
    return service.voornemen(debiet)


def test_ruimte_tot_de_norm_wordt_per_parameter_bepaald():
    r = ruimte.bereken(_voornemen(), gebied.REGISTER, gebied.WATERLICHAAM)
    assert len(r["parameters"]) == len(gebied.WATERLICHAAM["parameters"])
    for p in r["parameters"]:
        assert p["ruimte_mg_l"] == pytest.approx(p["norm_mg_l"] - p["achtergrond_mg_l"])


def test_parameter_zonder_ruimte_levert_geen_ruimte_op():
    r = ruimte.bereken(_voornemen(), gebied.REGISTER, gebied.WATERLICHAAM)
    vol = [p for p in r["parameters"] if p["ruimte_mg_l"] <= 0]
    assert vol
    for p in vol:
        assert p["oordeel"] == "geen ruimte"
        assert p["vrij_kg_jaar"] <= 0


def test_bijdrage_van_bestaande_vergunningen_wordt_apart_getoond():
    r = ruimte.bereken(_voornemen(), gebied.REGISTER, gebied.WATERLICHAAM)
    for p in r["parameters"]:
        assert p["vergund_kg_jaar"] >= 0
        assert p["vergunningen"] >= 1 or p["vergund_kg_jaar"] == 0


def test_een_groter_voornemen_benut_meer_ruimte():
    klein = ruimte.bereken(_voornemen(50), gebied.REGISTER, gebied.WATERLICHAAM)
    groot = ruimte.bereken(_voornemen(9000), gebied.REGISTER, gebied.WATERLICHAAM)
    pak = lambda r, n: next(p for p in r["parameters"] if p["naam"] == n)
    assert pak(groot, "stikstof totaal")["benutting_pct"] > pak(klein, "stikstof totaal")["benutting_pct"]


def test_bij_een_zeer_groot_debiet_knelt_ook_een_gewone_parameter():
    """Niet alleen de ZZS: bij genoeg volume loopt ook stikstof tegen de norm aan."""
    groot = ruimte.bereken(_voornemen(service.MAX_DEBIET), gebied.REGISTER, gebied.WATERLICHAAM)
    stikstof = next(p for p in groot["parameters"] if p["naam"] == "stikstof totaal")
    assert stikstof["oordeel"] == "past niet"
    klein = ruimte.bereken(_voornemen(420), gebied.REGISTER, gebied.WATERLICHAAM)
    assert next(p for p in klein["parameters"] if p["naam"] == "stikstof totaal")["oordeel"] == "past"


def test_conclusie_wijst_de_bepalende_parameter_aan():
    r = ruimte.bereken(_voornemen(), gebied.REGISTER, gebied.WATERLICHAAM)
    assert r["conclusie"]["antwoord"] in {"ja, mits", "nee, tenzij"}
    if r["conclusie"]["antwoord"] == "nee, tenzij":
        assert r["conclusie"]["bepalend"]


def test_zonder_register_valt_de_cumulatie_niet_te_bepalen():
    """De kern van de case: zonder register weet je niet van wie de ruimte is."""
    met = ruimte.bereken(_voornemen(), gebied.REGISTER, gebied.WATERLICHAAM)
    zonder = ruimte.bereken(_voornemen(), [], gebied.WATERLICHAAM)
    assert zonder["register_leeg"] is True and met["register_leeg"] is False
    assert all(p["vergund_kg_jaar"] == 0 for p in zonder["parameters"])
    assert zonder["conclusie"]["kanttekening"]


def test_rekensom_verwerkt_zowel_concentratie_als_voorberekende_vracht():
    w = {"debiet_m3_s": 300.0, "parameters": [
        {"naam": "zink", "norm_mg_l": 0.0078, "achtergrond_mg_l": 0.0071, "zzs": False,
         "toelichting": "t"}]}
    voornemen = {"debiet_m3_per_uur": 100.0, "concentraties": {"zink": 0.001}}

    oud = [{"naam": "A", "debiet_m3_per_uur": 100.0, "concentraties": {"zink": 0.01}}]
    nieuw = [{"naam": "A", "vrachten": {"zink": ruimte.vracht_kg_jaar(100.0, 0.01)}}]

    a = ruimte.bereken(voornemen, oud, w)["parameters"][0]
    b = ruimte.bereken(voornemen, nieuw, w)["parameters"][0]
    assert a["vergund_kg_jaar"] == b["vergund_kg_jaar"]


def test_onbepaalde_vracht_blijft_zichtbaar_als_ondergrens_niet_als_nul():
    """Een post zonder vracht maar mét een 'onbepaald'-vermelding voor deze stof telt niet
    stilzwijgend als nul mee — vergund_onbepaald telt hem, en de conclusie krijgt een
    kanttekening dat het totaal een ondergrens is."""
    w = {"debiet_m3_s": 300.0, "parameters": [
        {"naam": "zink", "norm_mg_l": 0.0078, "achtergrond_mg_l": 0.0071, "zzs": False,
         "toelichting": "t"}]}
    voornemen = {"debiet_m3_per_uur": 100.0, "concentraties": {"zink": 0.001}}
    register = [
        {"naam": "A", "vrachten": {"zink": 100.0}, "onbepaald": []},
        {"naam": "B", "vrachten": {}, "onbepaald": [
            {"parameter": "zink", "eenheid": "milligram per liter",
             "reden": "concentratie-eis zonder debiet-voorschrift"}]},
    ]
    r = ruimte.bereken(voornemen, register, w)
    p = r["parameters"][0]
    assert p["vergund_onbepaald"] == 1
    assert "ondergrens" in r["conclusie"]["kanttekening"].lower()


def test_zonder_onbepaalde_vracht_geen_kanttekening_daarover():
    w = {"debiet_m3_s": 300.0, "parameters": [
        {"naam": "zink", "norm_mg_l": 0.0078, "achtergrond_mg_l": 0.0071, "zzs": False,
         "toelichting": "t"}]}
    voornemen = {"debiet_m3_per_uur": 100.0, "concentraties": {"zink": 0.001}}
    register = [{"naam": "A", "vrachten": {"zink": 100.0}, "onbepaald": []}]
    r = ruimte.bereken(voornemen, register, w)
    assert r["parameters"][0]["vergund_onbepaald"] == 0
    assert "ondergrens" not in r["conclusie"]["kanttekening"].lower()


def _w_zonder_norm(*namen):
    return {"debiet_m3_s": 300.0, "parameters": [
        {"naam": n, "norm_mg_l": 1.0, "achtergrond_mg_l": 0.5, "zzs": False, "toelichting": "t"}
        for n in namen]}


def _onbepaalde_post(naam, stof):
    return {"naam": naam, "vrachten": {},
            "onbepaald": [{"parameter": stof, "eenheid": "milligram per liter", "reden": "x"}]}


def test_kanttekening_bij_een_stof_is_enkelvoud():
    w = _w_zonder_norm("zink")
    voornemen = {"debiet_m3_per_uur": 100.0, "concentraties": {}}
    register = [_onbepaalde_post("A", "zink")]
    r = ruimte.bereken(voornemen, register, w)
    assert r["conclusie"]["kanttekening"] == (
        "Het vergunde totaal is voor sommige parameters een ondergrens: van zink "
        "(1 vergunning) viel de vracht niet te bepalen, en die telt dus niet mee in "
        "vergund_kg_jaar.")


def test_kanttekening_bij_twee_stoffen_gebruikt_en_en_meervoud():
    w = _w_zonder_norm("stikstof totaal", "zink")
    voornemen = {"debiet_m3_per_uur": 100.0, "concentraties": {}}
    register = [_onbepaalde_post("A", "stikstof totaal"),
                _onbepaalde_post("B", "zink"), _onbepaalde_post("C", "zink")]
    r = ruimte.bereken(voornemen, register, w)
    assert r["conclusie"]["kanttekening"] == (
        "Het vergunde totaal is voor sommige parameters een ondergrens: van stikstof totaal "
        "(1 vergunning) en zink (2 vergunningen) vielen de vrachten niet te bepalen, en die "
        "tellen dus niet mee in vergund_kg_jaar.")


def test_kanttekening_bij_drie_stoffen_gebruikt_kommas_en_en_voor_de_laatste():
    w = _w_zonder_norm("stikstof totaal", "zink", "AOX")
    voornemen = {"debiet_m3_per_uur": 100.0, "concentraties": {}}
    register = [_onbepaalde_post("A", "stikstof totaal"),
                _onbepaalde_post("B", "zink"), _onbepaalde_post("C", "AOX")]
    r = ruimte.bereken(voornemen, register, w)
    assert r["conclusie"]["kanttekening"] == (
        "Het vergunde totaal is voor sommige parameters een ondergrens: van stikstof totaal "
        "(1 vergunning), zink (1 vergunning) en AOX (1 vergunning) vielen de vrachten niet te "
        "bepalen, en die tellen dus niet mee in vergund_kg_jaar.")


# ---------- service ----------

def test_beeld_bundelt_regels_vergunningen_en_ruimte():
    b = service.beeld("brummen", debiet_m3_per_uur=420, live=False)
    assert b["locatie"]["gemeente"]
    assert "regels" in b and "ruimte" in b and "register" in b
    assert b["voornemen"]["debiet_m3_per_uur"] == 420


def test_onbekende_locatie_faalt_luid():
    with pytest.raises(KeyError):
        service.beeld("atlantis", debiet_m3_per_uur=10, live=False)


def test_debiet_wordt_begrensd():
    b = service.beeld("brummen", debiet_m3_per_uur=10**9, live=False)
    assert b["voornemen"]["debiet_m3_per_uur"] <= service.MAX_DEBIET


def test_informatiefuncties_worden_expliciet_benoemd():
    """De case is bedoeld om informatiefuncties aan te tonen — benoem welke."""
    b = service.beeld("brummen", debiet_m3_per_uur=420, live=False)
    assert b["informatiefuncties"]
    for f in b["informatiefuncties"]:
        assert f["nr"] in range(1, 10) and f["hoe"]


# ---------- API ----------

def _client(monkeypatch):
    from fastapi.testclient import TestClient
    import leefomgevinglab.geluidsmeter.api as api
    monkeypatch.setattr(api, "load_config", lambda *a, **k: api._config)
    return TestClient(api.app)


def test_api_geeft_het_beeld(monkeypatch):
    d = _client(monkeypatch).get("/api/gebruiksruimte?locatie=deventer&debiet=420&live=0").json()
    assert d["locatie"]["gemeente"] == "Deventer"
    assert d["ruimte"]["conclusie"]["antwoord"]
    assert len(d["register"]) == len(gebied.REGISTER)


def test_api_kent_de_locatie_niet(monkeypatch):
    r = _client(monkeypatch).get("/api/gebruiksruimte?locatie=atlantis&live=0")
    assert r.status_code == 404


def test_api_pagina(monkeypatch):
    r = _client(monkeypatch).get("/gebruiksruimte")
    assert r.status_code == 200 and "api/gebruiksruimte" in r.text


def test_beeld_op_vaste_locatie_blijft_hetzelfde_na_de_refactor():
    """Karakterisering: /gebruiksruimte mag door de refactor niet stilletjes veranderen.

    Elke verwachte waarde staat hier letterlijk uitgeschreven — niet als verwijzing naar
    `gebied.REGISTER`/`gebied.LOCATIES`/`service.VERANTWOORDING` — want een test die zichzelf
    citeert, ziet drift in precies dát wat hij zou moeten bewaken niet. Zo verdween de oude
    verantwoordingstekst ongemerkt uit een eerdere versie van deze test.
    """
    b = service.beeld("deventer", debiet_m3_per_uur=420, live=False)
    assert b["locatie"]["gemeente"] == "Deventer"
    assert b["locatie"]["rd"] == [206800.0, 474000.0]
    assert b["water"]["naam"] == "IJssel"
    assert b["water"]["debiet_m3_s"] == 300.0
    assert [p["naam"] for p in b["ruimte"]["parameters"]] == [
        "stikstof totaal", "zink", "AOX", "PFOA"]
    assert b["ruimte"]["conclusie"]["antwoord"] == "nee, tenzij"
    assert b["ruimte"]["conclusie"]["bepalend"] == "PFOA"
    assert b["max_debiet"] == 20000
    assert len(b["informatiefuncties"]) == 5

    assert b["register"] == [
        {"naam": "Papierfabriek Gelre B.V.", "plaats": "Zutphen", "kenmerk": "RWS-2019-LOZ-0042",
         "owl_id": "NL93_IJSSEL", "debiet_m3_per_uur": 350,
         "concentraties": {"stikstof totaal": 3.1, "zink": 0.009, "AOX": 0.11, "PFOA": 0.00002}},
        {"naam": "Zuivelcoöperatie IJsselvallei", "plaats": "Deventer",
         "kenmerk": "RWS-2021-LOZ-0117", "owl_id": "NL93_IJSSEL", "debiet_m3_per_uur": 180,
         "concentraties": {"stikstof totaal": 6.4, "zink": 0.004, "AOX": 0.02, "PFOA": 0.0}},
        {"naam": "RWZI Deventer — effluent", "plaats": "Deventer", "kenmerk": "RWS-2017-LOZ-0008",
         "owl_id": "NL93_IJSSEL", "debiet_m3_per_uur": 2100,
         "concentraties": {"stikstof totaal": 7.8, "zink": 0.012, "AOX": 0.03, "PFOA": 0.000031}},
        {"naam": "Metaalwarenfabriek Doesburg", "plaats": "Doesburg",
         "kenmerk": "RWS-2022-LOZ-0203", "owl_id": "NL93_IJSSEL", "debiet_m3_per_uur": 95,
         "concentraties": {"stikstof totaal": 1.2, "zink": 0.21, "AOX": 0.04, "PFOA": 0.0}},
        {"naam": "Koelwater energiecentrale Harculo", "plaats": "Zwolle",
         "kenmerk": "RWS-2015-LOZ-0001", "owl_id": "NL93_IJSSEL", "debiet_m3_per_uur": 4500,
         "concentraties": {"stikstof totaal": 0.3, "zink": 0.001, "AOX": 0.0, "PFOA": 0.0}},
    ]

    assert b["locaties"] == [
        {"id": "brummen", "naam": "IJsseloever bij Brummen", "rd": (210500.0, 458500.0),
         "gemeente": "Brummen", "provincie": "Gelderland", "waterlichaam": "IJssel"},
        {"id": "deventer", "naam": "IJsseldijk Deventer", "rd": (206800.0, 474000.0),
         "gemeente": "Deventer", "provincie": "Overijssel", "waterlichaam": "IJssel"},
        {"id": "doesburg", "naam": "Havengebied Doesburg", "rd": (206000.0, 447500.0),
         "gemeente": "Doesburg", "provincie": "Gelderland", "waterlichaam": "IJssel"},
    ]

    assert b["regels"] == {"live": False, "status": "overgeslagen", "regelingen": [],
                           "bron": "DSO Presenteren (Ozon) — live", "telling": {}}

    assert b["bevoegd_gezag"] == {
        "lozingsactiviteit": "niet bepaald (bronnen niet bevraagd)",
        "grondslag": "zonder live-modus valt het bevoegd gezag niet af te leiden",
        "bron_beheerder": "niet bevraagd",
        "milieubelastende_activiteit": "de gemeente (niet bepaald)",
        "gemeente": None, "provincie": None}

    assert b["voornemen"] == {
        "soort": "directe lozing van koel- en gezuiverd proceswater",
        "debiet_m3_per_uur": 420.0,
        "concentraties": {"stikstof totaal": 2.47, "zink": 0.0125, "AOX": 0.084, "PFOA": 0.00024}}

    assert b["verantwoording"] == (
        "Regelingen live uit het DSO. Het register met bestaande vergunningen bestaat "
        "landelijk niet; voor het Maasstroomgebied komt het live uit de Atlas voor een "
        "Schone Maas, daarbuiten is het synthetisch. Normen en achtergrondconcentraties "
        "zijn illustratief. Het mechanisme is echt, de cijfers niet.")


_KRW_MAAS = """{"features":[{"properties":{
    "naam":"Maas","owl_id":"NL91_MAAS","sgd_id":"NLMS","gebtype":"R",
    "owltype":"R7","owlcat":"1","owlstat":"Sterk veranderd",
    "wbhnaam":"Ministerie van Infrastructuur en Waterstaat (Rijkswaterstaat)",
    "wbhcode":"NL_MINIW","omvang":210.0,"eenheid":"km2","gemdiepte":5.0}}]}"""
# Zelfde vorm als _KRW_MAAS, maar met het owl_id van de IJssel — nodig om de synthetische
# terugval te raken (zie test_prik_buiten_het_maasstroomgebied_valt_terug_op_synthetisch):
# prikken op Deventer-coördinaten zegt niets over welk waterlichaam de fixture teruggeeft.
_KRW_IJSSEL = """{"features":[{"properties":{
    "naam":"IJssel","owl_id":"NL93_IJSSEL","sgd_id":"NLRN","gebtype":"R",
    "owltype":"R7","owlcat":"1","owlstat":"Sterk veranderd",
    "wbhnaam":"Ministerie van Infrastructuur en Waterstaat (Rijkswaterstaat)",
    "wbhcode":"NL_MINIW","omvang":300.0,"eenheid":"km2","gemdiepte":4.0}}]}"""
# Een derde, willekeurig rijkswaterlichaam — noch Maas, noch IJssel — voor de derde
# registertoestand: geen Atlas-treffer én geen synthetische terugval.
_KRW_WAAL = """{"features":[{"properties":{
    "naam":"Waal","owl_id":"NL85_WAAL","sgd_id":"NLRN","gebtype":"R",
    "owltype":"R7","owlcat":"1","owlstat":"Sterk veranderd",
    "wbhnaam":"Ministerie van Infrastructuur en Waterstaat (Rijkswaterstaat)",
    "wbhcode":"NL_MINIW","omvang":300.0,"eenheid":"km2","gemdiepte":4.0}}]}"""
_GEM_MAASTRICHT = """{"features":[{"properties":{"naam":"Maastricht","ligtInProvincieNaam":"Limburg"}}]}"""
_GEM_EEN = """{"features":[{"properties":{"naam":"Zutphen","ligtInProvincieNaam":"Gelderland"}}]}"""
_GEEN = '{"features":[]}'


def _haal_reeks(antwoorden):
    it = iter(antwoorden)

    def haal(url, params, timeout_s=25.0):
        return next(it)
    return haal


def _atlas_maastricht(x, y, straal_m):
    return [{"kenmerk": "RWS-2015/38632", "naam": "Lawter Maastricht BV", "plaats": "Maastricht",
             "locatie": None, "url": None, "besluitdatum": "2015-01-01",
             "voorschriften": [
                 {"parameter": "zink", "waarde": 0.3, "eenheid": "milligram per liter",
                  "bemonstering": None, "rd": [x, y]},
                 {"parameter": "Debiet", "waarde": 25.0, "eenheid": "kubieke meter per uur",
                  "bemonstering": None, "rd": [x, y]}]}]


def test_prik_op_de_maas_gebruikt_echte_vergunningen():
    b = service.beeld_op_punt(177748.0, 321314.0, live=True,
                              _haal_water=_haal_reeks([_KRW_MAAS, _GEM_MAASTRICHT]),
                              _haal_regels=lambda rd: [],
                              _haal_atlas=_atlas_maastricht)
    assert b["water"]["naam"] == "Maas"
    assert b["register_bron"]["echt"] is True
    assert b["register"][0]["kenmerk"] == "RWS-2015/38632"
    assert b["ruimte"]["parameters"], "de rekensom draait ook op de Maas"


def test_prik_op_de_ijssel_valt_terug_op_synthetisch():
    """Rijkswater buiten het Maasstroomgebied, maar wél de IJssel: het bekende synthetische
    register van vijf posten, niet een leeg register — dat zijn twee verschillende dingen."""
    b = service.beeld_op_punt(206800.0, 474000.0, live=True,
                              _haal_water=_haal_reeks([_KRW_IJSSEL, _GEM_EEN]),
                              _haal_regels=lambda rd: [],
                              _haal_atlas=lambda x, y, straal_m: [])
    assert b["register_bron"]["echt"] is False
    assert b["register"] == gebied.REGISTER
    assert len(b["register"]) == 5
    assert "Maasstroomgebied" in b["register_bron"]["reden"]


def test_prik_op_ander_rijkswater_geeft_leeg_register_zonder_terugval():
    """Een rijkswater dat noch in de Atlas zit noch de IJssel is: geen synthetische terugval,
    gewoon een leeg register — de derde, van de andere twee te onderscheiden toestand."""
    b = service.beeld_op_punt(120000.0, 430000.0, live=True,
                              _haal_water=_haal_reeks([_KRW_WAAL, _GEM_EEN]),
                              _haal_regels=lambda rd: [],
                              _haal_atlas=lambda x, y, straal_m: [])
    assert b["register_bron"]["echt"] is False
    assert b["register"] == []
    assert b["register_bron"]["bron"]["naam"] == "geen"


def test_prik_zonder_rijkswater_geeft_geen_rekensom_maar_wel_een_antwoord():
    b = service.beeld_op_punt(150000.0, 400000.0, live=True,
                              _haal_water=_haal_reeks([_GEEN, _GEEN, _GEM_MAASTRICHT]),
                              _haal_regels=lambda rd: [],
                              _haal_atlas=lambda x, y, straal_m: [])
    assert b["rijkswater"] is False
    assert b["ruimte"] is None
    assert b["geen_ruimte_reden"]
    assert "waterschap" in b["bevoegd_gezag"]["lozingsactiviteit"]


def test_atlas_storing_laat_de_rest_van_het_beeld_staan():
    def stuk(x, y, straal_m):
        raise RuntimeError("Atlas plat")

    b = service.beeld_op_punt(177748.0, 321314.0, live=True,
                              _haal_water=_haal_reeks([_KRW_MAAS, _GEM_MAASTRICHT]),
                              _haal_regels=lambda rd: [], _haal_atlas=stuk)
    assert b["water"]["naam"] == "Maas"
    assert b["register_bron"]["status"] == "onbereikbaar"
    assert b["ruimte"] is not None
