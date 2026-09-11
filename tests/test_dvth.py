from leefomgevinglab.usecases import dvth


def test_component_ids_zijn_uniek():
    ids = [c["id"] for c in dvth.COMPONENTEN]
    assert len(ids) == len(set(ids))


def test_elke_component_zit_in_een_bestaande_baan():
    fout = [c["id"] for c in dvth.COMPONENTEN if c["baan"] not in dvth.BANEN]
    assert fout == []


def test_elke_component_heeft_een_geldige_status():
    fout = [c["id"] for c in dvth.COMPONENTEN if c["status"] not in dvth.STATUS]
    assert fout == []


def test_elke_flow_verbindt_bestaande_componenten():
    ids = {c["id"] for c in dvth.COMPONENTEN}
    fout = [f["id"] for f in dvth.FLOWS if f["van"] not in ids or f["naar"] not in ids]
    assert fout == []


def test_de_vier_banen_uit_de_opdracht_bestaan():
    assert list(dvth.BANEN) == ["indienen", "behandelen", "publiceren", "toezicht"]


def test_kern_van_de_doelarchitectuur_zit_erin():
    ids = {c["id"] for c in dvth.COMPONENTEN}
    for nodig in ("dso_loket", "zaaksysteem", "dataod", "analyse", "plansysteem",
                  "imev_tpod", "rev_nieuw", "gir", "lhso"):
        assert nodig in ids, f"component {nodig} ontbreekt in het doelbeeld"


def test_besluit_als_tpod_document_staat_als_nieuw_gemarkeerd():
    # STOP/TPOD kent geen toepassingsprofiel voor een vergunningbesluit; dat mag het
    # doelbeeld niet als bestaande praktijk presenteren.
    flow = next(f for f in dvth.FLOWS if f["id"] == "besluit_naar_plansysteem")
    assert flow["status"] == "nieuw"


def test_rev_wordt_omgebouwd_van_imev_naar_tpod():
    rev = next(c for c in dvth.COMPONENTEN if c["id"] == "rev_nieuw")
    assert rev["status"] == "wijzigt"
    assert "IMEV" in rev["toelichting"] and "TPOD" in rev["toelichting"]


def test_keten_heeft_acht_stappen_in_volgorde():
    nrs = [s["nr"] for s in dvth.STAPPEN]
    assert nrs == list(range(1, 9))


def test_elke_ketenstap_raakt_bestaande_componenten_en_cim_objecttypen():
    ids = {c["id"] for c in dvth.COMPONENTEN}
    for s in dvth.STAPPEN:
        assert s["componenten"], f"stap {s['nr']} raakt geen component"
        assert set(s["componenten"]) <= ids, f"stap {s['nr']} verwijst naar onbekende component"
        assert s["cim"], f"stap {s['nr']} levert geen CIM-objecttypen op"


def test_ketenstappen_gebruiken_alleen_bestaande_cim_objecttypen():
    from leefomgevinglab.usecases import vth_bronnen as vb
    geldig = {ot for v in vb.VIEWS for ot in v["objecttypen"]}
    onbekend = sorted({ot for s in dvth.STAPPEN for ot in s["cim"]} - geldig)
    assert onbekend == []


def test_roadmap_features_verwijzen_naar_bestaande_componenten_en_stappen():
    ids = {c["id"] for c in dvth.COMPONENTEN}
    nrs = {s["nr"] for s in dvth.STAPPEN}
    for f in dvth.features():
        assert set(f["componenten"]) <= ids, f"feature {f['id']} verwijst naar onbekende component"
        assert f["stap"] in nrs, f"feature {f['id']} verwijst naar onbekende ketenstap"


def test_feature_ids_zijn_uniek():
    ids = [f["id"] for f in dvth.features()]
    assert len(ids) == len(set(ids))


def test_elke_component_wordt_door_minstens_een_feature_gedekt():
    gedekt = {c for f in dvth.features() for c in f["componenten"]}
    ongedekt = sorted({c["id"] for c in dvth.COMPONENTEN} - gedekt)
    assert ongedekt == [], f"geen enkele feature raakt: {ongedekt}"


def test_elke_ketenstap_heeft_minstens_een_feature():
    per_stap = {f["stap"] for f in dvth.features()}
    ontbreekt = sorted({s["nr"] for s in dvth.STAPPEN} - per_stap)
    assert ontbreekt == []


def test_architectuur_bundelt_alles():
    a = dvth.architectuur()
    assert a["banen"] == dvth.BANEN
    assert len(a["componenten"]) == len(dvth.COMPONENTEN)
    assert a["flows"] and a["stappen"] and a["roadmap"] and a["casus"]


def test_casus_is_een_seveso_mba_met_rd_punt():
    c = dvth.CASUS
    assert "Seveso" in c["activiteit"]
    x, y = c["rd"]
    assert 0 < x < 300000 and 300000 < y < 620000       # binnen het RD-bereik van Nederland


def test_elke_feature_heeft_een_bouwstatus():
    toegestaan = {"gebouwd", "vereenvoudigd", "nog niet"}
    fout = [f["id"] for f in dvth.features() if f.get("gereed") not in toegestaan]
    assert fout == []


def test_vereenvoudigde_features_zeggen_waarom():
    zonder = [f["id"] for f in dvth.features()
              if f.get("gereed") == "vereenvoudigd" and not f.get("gereed_noot")]
    assert zonder == [], f"vereenvoudigd zonder toelichting: {zonder}"
