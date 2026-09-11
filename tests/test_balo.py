from fastapi.testclient import TestClient

import leefomgevinglab.geluidsmeter.api as api
from leefomgevinglab.usecases import balo, dvth, lozing


def test_beide_casussen_hebben_acht_stappen():
    for k, c in balo.CASUSSEN.items():
        assert [s["nr"] for s in c["stappen"]] == list(range(1, 9)), k


def test_stappen_sluiten_aan_op_de_doelbeelden():
    assert len(balo.CASUSSEN["dvth"]["stappen"]) == len(dvth.STAPPEN)
    assert len(balo.CASUSSEN["lozing"]["stappen"]) == len(lozing.STAPPEN)


def test_elke_stap_verwijst_naar_een_bestaande_waardestroom():
    codes = {w["code"] for w in balo.WAARDESTROMEN}
    for k, c in balo.CASUSSEN.items():
        fout = [s["nr"] for s in c["stappen"] if s["w"] not in codes]
        assert fout == [], f"{k}: stappen met onbekende waardestroom {fout}"


def test_elke_stap_gebruikt_alleen_de_negen_informatiefuncties():
    geldig = {f["nr"] for f in balo.INFORMATIEFUNCTIES}
    assert len(geldig) == 9
    for k, c in balo.CASUSSEN.items():
        for s in c["stappen"]:
            assert set(s["functies"]) <= geldig, f"{k} stap {s['nr']}"
            assert s["functies"], f"{k} stap {s['nr']} heeft geen informatiefunctie"


def test_elke_stap_verwijst_naar_bekende_registers():
    for k, c in balo.CASUSSEN.items():
        for s in c["stappen"]:
            onbekend = [r for r in s["registers"] if r not in balo.REGISTERS]
            assert onbekend == [], f"{k} stap {s['nr']}: {onbekend}"


def test_elke_stap_heeft_informatiebehoefte_en_objecten():
    for k, c in balo.CASUSSEN.items():
        for s in c["stappen"]:
            assert s["behoefte"].endswith("?"), f"{k} stap {s['nr']}: behoefte is geen vraag"
            assert s["objecten"], f"{k} stap {s['nr']} heeft geen informatieobject"


def test_registerstatus_is_een_van_drie_waarden():
    assert {m["status"] for m in balo.REGISTERS.values()} <= {"bestaat", "moet om", "bestaat niet"}


def test_de_ontbrekende_registers_staan_als_zodanig_gemarkeerd():
    assert balo.REGISTERS["Register Lozingen"]["status"] == "bestaat niet"
    assert balo.REGISTERS["REV"]["status"] == "moet om"


def test_dekking_telt_per_casus_en_vindt_gedeelde_functies():
    d = {f["nr"]: f for f in balo.dekking_informatiefuncties()}
    assert len(d) == 9
    # registreren en delen komen in beide ketens voor
    assert d[3]["in_beide"] and d[4]["in_beide"]
    assert d[3]["totaal"] >= 4


def test_registergebruik_staat_op_volgorde_van_gebruik():
    r = balo.registergebruik()
    assert [x["totaal"] for x in r] == sorted((x["totaal"] for x in r), reverse=True)
    assert all("status" in x and "per_casus" in x for x in r)


def test_gedeelde_knelpunten_vinden_de_stappen_waar_beide_ketens_vastlopen():
    g = balo.gedeelde_knelpunten()
    stappen = {x["stap"] for x in g}
    # publiceren, registreren en terugkoppelen lopen in beide dossiers vast
    assert {5, 6, 8} <= stappen
    for x in g:
        assert set(x["knelpunten"]) == set(balo.CASUSSEN)


def test_besluiten_hebben_een_kosten_en_waardeoordeel():
    assert balo.BESLUITEN
    ids = [b["id"] for b in balo.BESLUITEN]
    assert len(ids) == len(set(ids))
    for b in balo.BESLUITEN:
        assert b["kosten"] in balo.SCHAAL and b["waarde"] in balo.SCHAAL
        assert b["vraag"].endswith("?"), f"{b['id']}: geen besluitvraag"
        assert b["bewijs"] and b["afweging"] and b["wie"]


def test_besluiten_verwijzen_naar_bestaande_functies_en_registers():
    geldig_f = {f["nr"] for f in balo.INFORMATIEFUNCTIES}
    for b in balo.BESLUITEN:
        assert set(b["functies"]) <= geldig_f, b["id"]
        assert set(b["registers"]) <= set(balo.REGISTERS), b["id"]


def test_er_is_minstens_een_goedkoop_besluit_met_waarde():
    """Zonder laaghangend fruit is een roadmap niet te starten."""
    assert any(b["kosten"] == 1 and b["waarde"] >= 2 for b in balo.BESLUITEN)


def test_de_duurste_besluiten_hebben_ook_de_hoogste_waarde():
    duur = [b for b in balo.BESLUITEN if b["kosten"] == 3]
    assert duur and all(b["waarde"] == 3 for b in duur), \
        "een duur besluit met lage waarde hoort niet in het voorstel te staan"


def test_balo_besluiten_zijn_de_vragen_uit_het_document():
    assert {b["besluit"] for b in balo.BALO_BESLUITEN} == {
        "Werkwijze", "Prioriteit", "Opdrachtgevers", "Eigenaarschap", "Capaciteit"}


def test_bron_wordt_vermeld_en_onderscheidt_wat_van_het_lab_is():
    o = balo.overzicht()
    assert "BALO" in o["bron"] and "lab" in o["bron"]


# ---------- API en pagina ----------

def _client(monkeypatch):
    monkeypatch.setattr(api, "load_config", lambda *a, **k: api._config)
    return TestClient(api.app)


def test_balo_api(monkeypatch):
    d = _client(monkeypatch).get("/api/balo/overzicht").json()
    assert len(d["informatiefuncties"]) == 9
    assert len(d["waardestromen"]) == 8
    assert set(d["casussen"]) == {"dvth", "lozing"}
    assert d["besluiten"] and d["gedeelde_knelpunten"]


def test_balo_pagina(monkeypatch):
    r = _client(monkeypatch).get("/balo")
    assert r.status_code == 200
    assert "balo/overzicht" in r.text


# ---------- informatiebehoefte en waarde ----------

def test_elke_behoefte_heeft_id_eigenaar_waarde_en_gemis():
    b = balo.behoeften()
    assert len(b) == 16
    for x in b:
        assert x["id"] and x["wie"] and x["waarde"] and x["zonder"], x
        assert x["status"] in balo.STATUS_BEHOEFTE


def test_behoefte_ids_zijn_uniek():
    ids = [x["id"] for x in balo.behoeften()]
    assert len(ids) == len(set(ids))


def test_een_stap_met_knelpunt_kan_niet_voldaan_zijn():
    for k, c in balo.CASUSSEN.items():
        for s in c["stappen"]:
            if s["knelpunt"]:
                assert s["status"] != "voldaan", f"{k} stap {s['nr']}"


def test_cyclus_dekt_alle_waardestromen_en_telt_kloppend():
    c = balo.cyclus()
    assert len(c) == 8
    assert sum(w["aantal"] for w in c) == len(balo.behoeften())
    for w in c:
        assert sum(w["per_status"].values()) == w["aantal"]


def test_cyclus_laat_zien_welke_waardestromen_buiten_beeld_blijven():
    o = balo.waardeoverzicht()
    assert o["waardestromen_geraakt"] < o["waardestromen_totaal"]
    assert set(o["niet_geraakt"]) == {"W1", "W3", "W8"}


def test_waardeoverzicht_telt_de_statussen_kloppend():
    o = balo.waardeoverzicht()
    assert sum(o["per_status"].values()) == o["totaal"] == 16
    assert len(o["onvervuld"]) == o["totaal"] - o["per_status"]["voldaan"]


def test_publiceren_is_het_zwartste_gat_in_de_cyclus():
    """W5 draagt de meeste onvervulde behoeften — daar zit het ontbrekende TPOD-profiel."""
    w5 = next(w for w in balo.cyclus() if w["code"] == "W5")
    onvervuld = {w["code"]: w["per_status"]["niet"] for w in balo.cyclus()}
    assert w5["per_status"]["niet"] == max(onvervuld.values())


def test_elk_besluit_bedient_bestaande_behoeften():
    ids = {b["id"] for b in balo.behoeften()}
    for b in balo.besluitwaarde():
        assert b["lost_op"], f"{b['id']} bedient geen enkele informatiebehoefte"
        assert set(b["lost_op"]) <= ids, b["id"]
        assert b["aantal_behoeften"] == len(b["lost_op"])


def test_waardeoordeel_is_onderbouwd_met_behoeften():
    """Een hoge waarde moet je kunnen aanwijzen, niet alleen beweren."""
    for b in balo.besluitwaarde():
        if b["waarde"] == 3:
            assert b["aantal_behoeften"] >= 2, f"{b['id']}: waarde hoog, maar {b['aantal_behoeften']} behoefte(n)"
        if b["waarde"] >= 2:
            assert b["aantal_behoeften"] >= 1, b["id"]


def test_blinde_vlekken_worden_benoemd():
    """Behoeften die geen enkel besluit oplost, moeten zichtbaar zijn."""
    ob = balo.onbediend()
    assert ob, "verwacht minstens één onbediende behoefte — anders suggereert de lijst volledigheid"
    bediend = {i for b in balo.BESLUITEN for i in b["lost_op"]}
    for x in ob:
        assert x["id"] not in bediend and x["status"] != "voldaan"
