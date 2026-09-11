import pytest

from leefomgevinglab.usecases import dvth
from leefomgevinglab.usecases.dvth_keten import casus, lbr, motor, tpod
from leefomgevinglab.usecases.ketenkern import cim, lhso


# ---------- CIM-objectbibliotheek (F1.2) ----------

def test_cim_object_met_bekend_objecttype():
    o = cim.obj("VTH-OBJECT", "NL.X.1", naam="Zuidhaven")
    assert o["type"] == "VTH-OBJECT" and o["id"] == "NL.X.1" and o["attributen"]["naam"] == "Zuidhaven"


def test_cim_object_met_onbekend_objecttype_faalt():
    with pytest.raises(cim.CimFout) as e:
        cim.obj("RISICOBRON", "x")
    assert "RISICOBRON" in str(e.value)


def test_registry_verzamelt_per_stap_en_telt_types():
    r = cim.Registry()
    r.voeg_toe(3, [cim.obj("PAND", "p1"), cim.obj("PAND", "p2"), cim.obj("VTH-OBJECT", "v1")])
    assert r.per_stap[3] and len(r.alles()) == 3
    assert r.per_type()["PAND"] == 2


# ---------- Casus (F1.1) ----------

def test_casus_deelt_het_rd_punt_met_de_architectuurplaat():
    assert casus.CASUS["rd"] == dvth.CASUS["rd"]


def test_casus_is_een_hogedrempel_seveso_met_stoffen_en_installaties():
    c = casus.CASUS
    assert c["drempel"] == "hoog"
    assert c["stoffen"] and all("naam" in s and "hoeveelheid_ton" in s for s in c["stoffen"])
    assert c["installaties"]


# ---------- IMEV → TPOD (F3.1, F3.3) ----------

def test_elke_imev_verplichte_eigenschap_heeft_een_annotatie():
    gedekt = {a["uit_imev"] for a in tpod.ANNOTATIES}
    ontbreekt = [v for v in tpod.IMEV_VERPLICHT if v not in gedekt]
    assert ontbreekt == []


def test_annotaties_verwijzen_naar_bestaande_cim_objecttypen():
    onbekend = [a["annotatie"] for a in tpod.ANNOTATIES
                if a["cim_objecttype"] and a["cim_objecttype"] not in cim.GELDIGE_OBJECTTYPEN]
    assert onbekend == []


def test_validatie_ziet_een_ontbrekende_verplichte_annotatie():
    doc = {"tekstdelen": [{"annotaties": [{"annotatie": "Risicobron"}]}]}
    uit = tpod.valideer(doc)
    assert uit["ok"] is False
    assert "Aandachtsgebied" in uit["ontbrekend"]


def test_validatie_op_een_volledig_document_slaagt():
    doc = {"tekstdelen": [{"annotaties": [{"annotatie": a["annotatie"]} for a in tpod.ANNOTATIES]}]}
    assert tpod.valideer(doc)["ok"] is True


# ---------- LBR (F4.1, F4.2) ----------

def test_bevindingen_dekken_de_drie_lbr_pijlers():
    b = lbr.bevindingen(casus.CASUS)
    assert {x["pijler"] for x in b} == set(lbr.PIJLERS)


def test_elke_bevinding_verwijst_naar_een_voorschrift():
    for b in lbr.bevindingen(casus.CASUS):
        assert b["voorschrift"], f"bevinding {b['id']} hangt in de lucht"


# ---------- LHSO (F4.4) ----------

def test_interventiematrix_dekt_alle_combinaties():
    for g in lhso.GEDRAG:
        for v in lhso.GEVOLGEN:
            uit = lhso.interventie(g, v)
            assert uit["cel"] and uit["interventie"] and uit["zwaarte"] >= 1


def test_lichtste_en_zwaarste_hoek_van_de_matrix():
    licht = lhso.interventie(lhso.GEDRAG[0], lhso.GEVOLGEN[0])
    zwaar = lhso.interventie(lhso.GEDRAG[-1], lhso.GEVOLGEN[-1])
    assert licht["cel"] == "A1" and zwaar["cel"] == "D4"
    assert licht["zwaarte"] < zwaar["zwaarte"]
    assert licht["interventie"] != zwaar["interventie"]


def test_onbekend_gedrag_faalt_luid():
    with pytest.raises(ValueError):
        lhso.interventie("wispelturig", lhso.GEVOLGEN[0])


# ---------- Ketenmotor (F1.3, F5.1, F5.2) ----------

def test_keten_doorloopt_acht_stappen_in_volgorde():
    run = motor.run_keten(live=False)
    assert [s["nr"] for s in run["stappen"]] == list(range(1, 9))


def test_elke_stap_levert_het_protocol():
    for s in motor.run_keten(live=False)["stappen"]:
        for veld in ("nr", "naam", "componenten", "standaard", "invoer", "uitvoer", "cim", "duiding"):
            assert veld in s, f"stap {s['nr']} mist {veld}"
        assert s["duiding"], f"stap {s['nr']} heeft geen duiding"


def test_stapnamen_komen_overeen_met_de_architectuurplaat():
    run = motor.run_keten(live=False)
    assert [s["naam"] for s in run["stappen"]] == [s["naam"] for s in dvth.STAPPEN]


def test_alle_objecten_uit_de_keten_zijn_geldige_cim_objecten():
    run = motor.run_keten(live=False)
    onbekend = sorted({o["type"] for o in run["objecten"]} - cim.GELDIGE_OBJECTTYPEN)
    assert onbekend == []


def test_keten_raakt_de_objecttypen_die_de_plaat_belooft():
    run = motor.run_keten(live=False)
    geraakt = {o["type"] for o in run["objecten"]}
    beloofd = {ot for s in dvth.STAPPEN for ot in s["cim"]}
    assert beloofd <= geraakt, f"beloofd maar niet geleverd: {sorted(beloofd - geraakt)}"


def test_dekkingsmeter_telt_geraakte_en_ongeraakte_objecttypen():
    d = motor.run_keten(live=False)["dekking"]
    assert d["totaal"] == len(cim.GELDIGE_OBJECTTYPEN)
    assert 0 < d["geraakt"] < d["totaal"]
    assert len(d["niet_geraakt"]) == d["totaal"] - d["geraakt"]


def test_bevinding_verwijst_terug_naar_een_voorschrift_uit_het_besluit():
    run = motor.run_keten(live=False)
    voorschriften = {o["id"] for o in run["objecten"] if o["type"] == "SPECIFIEK VOORSCHRIFT"}
    overtredingen = [o for o in run["objecten"] if o["type"] == "OVERTREDING"]
    assert overtredingen
    for o in overtredingen:
        assert o["attributen"]["voorschrift"] in voorschriften, "de lus naar het besluit is niet gesloten"


def test_impactanalyse_vergelijkt_cim_met_de_tpod_annotatieset():
    imp = motor.run_keten(live=False)["impact"]
    assert "zonder_annotatie" in imp and "annotaties_zonder_objecttype" in imp
    assert imp["geannoteerd"] >= 1


def test_zonder_live_worden_geen_bronnen_bevraagd():
    run = motor.run_keten(live=False)
    assert all(b["status"] == "overgeslagen" for b in run["bronnen"])


def test_live_stap_degradeert_als_een_bron_onbereikbaar_is():
    def kapot(*a, **kw):
        raise OSError("geen netwerk")

    run = motor.run_keten(live=True, _haal=kapot)
    assert [s["nr"] for s in run["stappen"]] == list(range(1, 9)), "keten moet doorlopen"
    assert any(b["status"] == "onbereikbaar" for b in run["bronnen"])
    stap3 = next(s for s in run["stappen"] if s["nr"] == 3)
    assert stap3["uitvoer"]["contextset"]["volledig"] is False


def test_ketenuitkomst_gebruikt_een_dossierneutrale_registersleutel():
    # de motor is gedeeld; 'rev' is Seveso-jargon en hoort niet in de kern
    run = motor.run_keten(live=False)
    assert "register" in run and "rev" not in run
    assert run["dossier"]["id"] == "dvth"
