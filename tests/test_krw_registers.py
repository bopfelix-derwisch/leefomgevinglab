"""De KRW-registers: de verdichting op fixtures, en de geproduceerde bestanden op hun claims.

Twee soorten test hier, bewust gescheiden. De eerste groep draait op kleine fixtures en raakt het
net niet — die moet overal groen zijn. De tweede groep leest de echte bestanden op de NVMe en
houdt ze tegen de getallen die elders in dit lab worden rondgezegd; die slaat over als de
bestanden er niet zijn, want op een machine zonder die data valt er niets te toetsen.
"""
import json
from pathlib import Path

import pytest

import importlib.util

_SCRIPT = Path(__file__).parent.parent / "scripts" / "18_fetch_krw_registers.py"
_spec = importlib.util.spec_from_file_location("krw_registers", _SCRIPT)
kr = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(kr)

DATA = Path("/mnt/nvme/geluidsmeter/data/external/wkp")

_KOP = ("Planperiode;StroomgebieddistrictCode;StroomgebieddistrictNaam;ProvincieCode;"
        "ProvincieNaam;WaterbeheerderCode;WaterbeheerderNaam;WaterlichaamCode;WaterlichaamNaam;"
        "OppervlaktewaterStatus;OppervlaktewaterCategorie;OppervlaktewaterWatertypeCode")


def _csv(*rijen: str) -> str:
    return "\n".join([_KOP, *rijen]) + "\n"


# --- de catalogus -------------------------------------------------------------------------

def _catalogus():
    return {"themes": [{"name": "Kaderrichtlijn Water", "subjects": [
        {"id": 9, "name": "KRW-monitoringlocaties-geometrie"},
        {"id": 17, "name": "KRW-oppervlaktewaterlichamen"},
    ]}]}


def test_een_onderwerp_wordt_op_naam_opgezocht_niet_op_een_vast_nummer():
    assert kr.onderwerp_id(_catalogus(), "KRW-oppervlaktewaterlichamen") == 17
    assert kr.onderwerp_id(_catalogus(), "KRW-monitoringlocaties-geometrie") == 9


def test_een_verschoven_catalogus_valt_luid_om_in_plaats_van_stil_het_verkeerde_te_halen():
    """Dit is een niet-gepubliceerde API; een onbekende naam mag geen terugval krijgen."""
    with pytest.raises(SystemExit) as e:
        kr.onderwerp_id(_catalogus(), "KRW-oppervlaktewaterlichamen-geometrie")
    assert "staat niet in de catalogus" in str(e.value)


# --- de verdichting van de waterlichamen ---------------------------------------------------

def test_waterlichamen_worden_per_code_en_per_district_ontsloten():
    d = kr.verdicht_waterlichamen(_csv(
        "3;NLMS;Maas;;;RWS;Rijkswaterstaat;NL91BOM;Bovenmaas;Sterk veranderd;Rivier;R7",
        "3;NLMS;Maas;;;RWS;Rijkswaterstaat;NL91JK;Julianakanaal;Kunstmatig;Meer;M7b",
        "3;NLRN;Rijn-Oost;;;WRIJ;Waterschap Rijn en IJssel;NL93_IJSSEL;IJssel;;Rivier;R7",
    ))
    assert d["telling"] == {"waterlichamen": 3, "districten": 2}
    assert d["per_district"]["Maas"] == ["NL91BOM", "NL91JK"]
    bom = d["waterlichamen"]["NL91BOM"]
    assert (bom["naam"], bom["district"], bom["beheerder"]) == (
        "Bovenmaas", "Maas", "Rijkswaterstaat")
    assert (bom["categorie"], bom["watertype"]) == ("Rivier", "R7")


def test_een_rij_zonder_waterlichaamcode_verdwijnt_zonder_de_rest_te_hinderen():
    d = kr.verdicht_waterlichamen(_csv(
        "3;NLMS;Maas;;;RWS;Rijkswaterstaat;;Naamloos;;Rivier;R7",
        "3;NLMS;Maas;;;RWS;Rijkswaterstaat;NL91ZM;Zandmaas;;Rivier;R7",
    ))
    assert list(d["waterlichamen"]) == ["NL91ZM"]


def test_lege_velden_worden_none_en_geen_lege_tekst():
    """Een leeg veld is onbekend, geen waarde. Dat onderscheid draagt de rest van dit lab ook."""
    d = kr.verdicht_waterlichamen(_csv(
        "3;NLMS;Maas;;;RWS;Rijkswaterstaat;NL91JK;Julianakanaal;;Meer;"))
    jk = d["waterlichamen"]["NL91JK"]
    assert jk["status"] is None and jk["watertype"] is None
    assert jk["categorie"] == "Meer"


def test_de_naam_valt_terug_op_de_code_in_plaats_van_leeg_te_blijven():
    d = kr.verdicht_waterlichamen(_csv("3;NLMS;Maas;;;RWS;Rijkswaterstaat;NL91ZM;;;Rivier;R7"))
    assert d["waterlichamen"]["NL91ZM"]["naam"] == "NL91ZM"


# --- de geproduceerde bestanden ------------------------------------------------------------

@pytest.fixture(scope="module")
def waterlichamen():
    p = DATA / "krw_waterlichamen.json"
    if not p.exists():
        pytest.skip(f"ontbreekt: {p} (draai scripts/18_fetch_krw_registers.py)")
    return json.loads(p.read_text())


@pytest.fixture(scope="module")
def locaties():
    p = DATA / "krw_monitoringlocaties.json"
    if not p.exists():
        pytest.skip(f"ontbreekt: {p} (draai scripts/18_fetch_krw_registers.py)")
    return json.loads(p.read_text())


def test_elk_rijkswaterlichaam_in_de_maas_is_geplaatst_of_uitdrukkelijk_niet(waterlichamen):
    """Geen rijkswaterlichaam in district Maas mag stilzwijgend ontbreken.

    De stroomvolgorde kende er acht; district Maas heeft er veertien van Rijkswaterstaat. De zes
    die erbij kwamen zijn ofwel geplaatst (mét grondslag in `GROND`) ofwel uitdrukkelijk níét te
    plaatsen (`ZONDER_POSITIE`). Wat deze test afdwingt is dat er geen derde categorie is: een
    waterlichaam dat nergens genoemd wordt en daardoor onzichtbaar wegvalt.
    """
    from leefomgevinglab.usecases.kmg import toerekening

    geplaatst = {code for code, _naam in toerekening.STROOMVOLGORDE}
    maas = waterlichamen["per_district"]["Maas"]
    assert len(maas) > 100, "een stroomgebied is geen handjevol waterlichamen"
    rws = [c for c in maas
           if waterlichamen["waterlichamen"][c]["beheerder"] == "Rijkswaterstaat"]
    vergeten = [c for c in rws
                if c not in geplaatst and c not in toerekening.ZONDER_POSITIE]
    assert not vergeten, f"niet geplaatst en niet benoemd: {vergeten}"
    assert toerekening.ZONDER_POSITIE, "de twee onplaatsbare horen benoemd te blijven"


def test_elke_plaatsing_zegt_waarop_zij_berust(waterlichamen):
    """De codes komen uit de bron, de volgorde niet — dus draagt elke code een grondslag."""
    from leefomgevinglab.usecases.kmg import toerekening

    for code, naam in toerekening.STROOMVOLGORDE:
        grond = toerekening.positie_grond(code)
        assert grond, f"{code} ({naam}) zegt niet waarop zijn plaatsing berust"
    # Wat niet op de hoofdstroom ligt, moet dat ook zeggen in plaats van als gegeven te gelden.
    afgeleid = [c for c, g in toerekening.GROND.items() if g != "hoofdstroom"]
    assert all("dit lab" in toerekening.GROND[c] for c in afgeleid)


def test_elke_in_de_stroomvolgorde_genoemde_code_bestaat_echt(waterlichamen):
    """De volgorde is een labkeuze, maar de codes erin horen uit de bron te komen."""
    from leefomgevinglab.usecases.kmg import toerekening

    maas = set(waterlichamen["per_district"]["Maas"])
    onbekend = [(code, naam) for code, naam in toerekening.STROOMVOLGORDE if code not in maas]
    assert not onbekend, f"codes die niet in district Maas voorkomen: {onbekend}"


def test_alle_monitoringlocaties_dragen_een_waterlichaam(locaties):
    """Dit is de winst tegenover het meetobjectenbestand per beheerder, waar het 131 van 322 is."""
    assert locaties["telling"]["zonder_waterlichaam"] == 0
    assert locaties["telling"]["locaties"] > 1000


def test_de_locaties_overbruggen_de_namespacebreuk_bij_eijsden(locaties):
    """De meetwaarden noemen dit punt NL80_EIJSDPTN, dit register NL91_EIJSDPTN.

    Dat verschil wordt elders in dit lab met de hand overbrugd (zie `scripts/17`). Hier staat
    het expliciet: dezelfde locatie, met het waterlichaam erbij.
    """
    e = locaties["locaties"]["NL91_EIJSDPTN"]
    assert e["waterlichaam"] == "NL91BOM"
    assert e["district"] == "Maas"
    assert e["rd"] and 170_000 < e["rd"][0] < 185_000, "RD-coördinaat, geen WGS84"


def test_het_maasdistrict_telt_meer_meetpunten_dan_rijkswaterstaat_alleen(locaties):
    maas = [v for v in locaties["locaties"].values() if v["district"] == "Maas"]
    rws = [v for v in maas if v["beheerder"] == "Rijkswaterstaat"]
    assert len(maas) > 300 and len(rws) < 50, "de waterschappen leveren het leeuwendeel"
