import pytest

from leefomgevinglab.usecases import lozing
from leefomgevinglab.usecases.ketenkern import cim
from leefomgevinglab.usecases.lozing_keten import aquo, beoordeling, bronnen, casus, motor, toezicht


# ---------- architectuur ----------

def test_component_ids_uniek_en_geldig():
    ids = [c["id"] for c in lozing.COMPONENTEN]
    assert len(ids) == len(set(ids))
    assert all(c["baan"] in lozing.BANEN and c["status"] in lozing.STATUS for c in lozing.COMPONENTEN)


def test_flows_verbinden_bestaande_componenten():
    ids = {c["id"] for c in lozing.COMPONENTEN}
    fout = [f["id"] for f in lozing.FLOWS if f["van"] not in ids or f["naar"] not in ids]
    assert fout == []


def test_de_knip_staat_als_eigen_component_op_de_plaat():
    knip = next(c for c in lozing.COMPONENTEN if c["id"] == "knip")
    assert knip["status"] == "wijzigt"
    assert "waterbeheerder" in knip["toelichting"]


def test_register_lozingen_is_gemarkeerd_als_nieuw():
    reg = next(c for c in lozing.COMPONENTEN if c["id"] == "register_lozingen")
    assert reg["status"] == "nieuw"


def test_afstemming_tussen_de_twee_besluiten_bestaat_niet():
    f = next(f for f in lozing.FLOWS if f["id"] == "afstemming")
    assert f["status"] == "nieuw"


def test_ketenstappen_gebruiken_alleen_bestaande_cim_objecttypen():
    onbekend = sorted({ot for s in lozing.STAPPEN for ot in s["cim"]} - cim.GELDIGE_OBJECTTYPEN)
    assert onbekend == []


def test_elke_component_wordt_door_een_feature_gedekt():
    gedekt = {c for f in lozing.features() for c in f["componenten"]}
    assert sorted({c["id"] for c in lozing.COMPONENTEN} - gedekt) == []


def test_features_verwijzen_naar_bestaande_stappen_en_hebben_bouwstatus():
    nrs = {s["nr"] for s in lozing.STAPPEN}
    toegestaan = {"gebouwd", "vereenvoudigd", "nog niet"}
    for f in lozing.features():
        assert f["stap"] in nrs
        assert f.get("gereed") in toegestaan
        if f["gereed"] == "vereenvoudigd":
            assert f.get("gereed_noot")


def test_presentatie_wijst_naar_de_eigen_api():
    assert lozing.PRESENTATIE["api"] == "lozing"


# ---------- ABM en immissietoets ----------

def test_zzs_krijgt_de_zwaarste_saneringsinspanning():
    assert beoordeling.abm_klasse({"zzs": True}) == "Z"
    assert beoordeling.abm_klasse({"zzs": False, "indicatieve_toetswaarde_mg_l": 1.0}) == "B"
    assert beoordeling.abm_klasse({"zzs": False, "indicatieve_toetswaarde_mg_l": None}) == "A"


def test_immissietoets_verdunt_met_het_debiet_van_het_waterlichaam():
    groot = beoordeling.immissietoets(casus.CASUS, "IJssel")
    klein = beoordeling.immissietoets(casus.CASUS, "een sloot zonder debiet in de tabel")
    assert groot["verdunningsfactor"] > klein["verdunningsfactor"]
    # hetzelfde bedrijf, kleiner water: de immissie valt hoger uit
    z_groot = next(p for p in groot["parameters"] if p["naam"] == "PFOA")
    z_klein = next(p for p in klein["parameters"] if p["naam"] == "PFOA")
    assert z_klein["ratio"] > z_groot["ratio"]


def test_parameter_zonder_toetswaarde_krijgt_geen_oordeel():
    t = beoordeling.immissietoets(casus.CASUS, "IJssel")
    czv = next(p for p in t["parameters"] if p["naam"] == "CZV")
    assert czv["ratio"] is None and czv["oordeel"] == "geen toetswaarde"


def test_zzs_levert_altijd_een_minimalisatievoorschrift():
    t = beoordeling.immissietoets(casus.CASUS, "IJssel")
    assert t["zzs"] == ["PFOA"]
    assert any("minimalisatieplicht" in v["tekst"] for v in beoordeling.voorschriften(t))


def test_knelpunt_levert_een_extra_voorschrift():
    t = dict(beoordeling.immissietoets(casus.CASUS, "IJssel"), knelpunten=["zink"])
    ids = [v["id"] for v in beoordeling.voorschriften(t)]
    assert "W-05" in ids


# ---------- bevoegd gezag afleiden ----------

def test_rijkswater_maakt_de_minister_bevoegd():
    bg = bronnen.bevoegd_gezag({"live": True, "rijkswater": True, "waterlichaam": "IJssel",
                                "owl_id": "NL93_IJSSEL", "gemeente": "Deventer"})
    assert "Rijkswaterstaat" in bg["lozingsactiviteit"]
    assert "Deventer" in bg["milieubelastende_activiteit"]


def test_zonder_rijkswaterlichaam_is_het_waterschap_bevoegd():
    bg = bronnen.bevoegd_gezag({"live": True, "rijkswater": False, "gemeente": "Deventer"})
    assert "waterschap" in bg["lozingsactiviteit"]


def test_zonder_live_wordt_geen_bevoegd_gezag_verzonnen():
    bg = bronnen.bevoegd_gezag({"live": False, "rijkswater": None, "gemeente": None})
    assert "niet bepaald" in bg["lozingsactiviteit"]


# ---------- Aquo → TPOD ----------

def test_elke_verplichte_aquo_eigenschap_heeft_een_annotatie():
    gedekt = {a["uit_aquo"] for a in aquo.ANNOTATIES}
    assert [v for v in aquo.AQUO_VERPLICHT if v not in gedekt] == []


def test_annotaties_verwijzen_naar_bestaande_cim_objecttypen():
    onbekend = [a["annotatie"] for a in aquo.ANNOTATIES
                if a["cim_objecttype"] and a["cim_objecttype"] not in cim.GELDIGE_OBJECTTYPEN]
    assert onbekend == []


def test_ontvangend_waterlichaam_belandt_in_de_restbak():
    a = next(a for a in aquo.ANNOTATIES if a["annotatie"] == "OntvangendWaterlichaam")
    assert a["cim_objecttype"] == "ANDER GEO-OBJECT"


def test_validatie_ziet_een_ontbrekende_annotatie():
    uit = aquo.valideer({"tekstdelen": [{"annotaties": [{"annotatie": "Lozingspunt"}]}]})
    assert uit["ok"] is False and "Emissiegrenswaarde" in uit["ontbrekend"]


def test_register_zegt_erbij_dat_het_niet_bestaat():
    run = motor.run_keten(live=False)
    assert run["register"]["register_bestaat"] is False


# ---------- toezicht ----------

def test_bevindingen_dekken_de_drie_sporen():
    t = beoordeling.immissietoets(casus.CASUS, "IJssel")
    assert {b["spoor"] for b in toezicht.bevindingen(casus.CASUS, t)} == set(toezicht.SPOREN)


def test_aandachtspunt_is_geen_overtreding():
    t = beoordeling.immissietoets(casus.CASUS, "IJssel")
    b = toezicht.bevindingen(casus.CASUS, t)
    assert any(not toezicht.is_overtreding(x) for x in b)
    assert any(toezicht.is_overtreding(x) for x in b)


# ---------- de keten ----------

def test_keten_doorloopt_acht_stappen():
    assert [s["nr"] for s in motor.run_keten(live=False)["stappen"]] == list(range(1, 9))


def test_stapnamen_komen_overeen_met_de_plaat():
    run = motor.run_keten(live=False)
    assert [s["naam"] for s in run["stappen"]] == [s["naam"] for s in lozing.STAPPEN]


def test_keten_levert_de_beloofde_objecttypen():
    run = motor.run_keten(live=False)
    geraakt = {o["type"] for o in run["objecten"]}
    beloofd = {ot for s in lozing.STAPPEN for ot in s["cim"]}
    assert beloofd <= geraakt, f"beloofd maar niet geleverd: {sorted(beloofd - geraakt)}"


def test_twee_bevoegde_gezagen_als_aparte_objecten():
    run = motor.run_keten(live=False)
    instanties = [o for o in run["objecten"] if o["type"] == "VTH-INSTANTIE"]
    rollen = {o["attributen"]["rol"] for o in instanties}
    assert rollen == {"bevoegd gezag lozingsactiviteit", "bevoegd gezag milieubelastende activiteit"}


def test_lus_van_overtreding_naar_voorschrift_is_gesloten():
    run = motor.run_keten(live=False)
    voorschriften = {o["id"] for o in run["objecten"] if o["type"] == "SPECIFIEK VOORSCHRIFT"}
    overtredingen = [o for o in run["objecten"] if o["type"] == "OVERTREDING"]
    assert overtredingen
    for o in overtredingen:
        assert o["attributen"]["voorschrift"] in voorschriften


def test_dossierstempel_en_registersleutel():
    run = motor.run_keten(live=False)
    assert run["dossier"]["id"] == "lozing"
    assert "register" in run and "rev" not in run


def test_keten_degradeert_als_de_bronnen_wegvallen():
    def kapot(*a, **kw):
        raise OSError("geen netwerk")

    run = motor.run_keten(live=True, _haal=kapot)
    assert [s["nr"] for s in run["stappen"]] == list(range(1, 9))
    assert any(b["status"] == "onbereikbaar" for b in run["bronnen"])
    stap2 = next(s for s in run["stappen"] if s["nr"] == 2)
    assert "waterschap" in stap2["uitvoer"]["bevoegd_gezag"]["lozingsactiviteit"]


def test_zonder_live_worden_geen_bronnen_bevraagd():
    assert all(b["status"] == "overgeslagen" for b in motor.run_keten(live=False)["bronnen"])


@pytest.mark.parametrize("veld", ["nr", "naam", "componenten", "standaard", "invoer",
                                  "uitvoer", "cim", "duiding"])
def test_elke_stap_levert_het_protocol(veld):
    for s in motor.run_keten(live=False)["stappen"]:
        assert veld in s and s[veld] not in (None, "")
