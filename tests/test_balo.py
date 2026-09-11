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
