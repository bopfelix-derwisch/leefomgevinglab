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
