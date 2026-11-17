"""`usecases.eindbeeld_stelsel` -- het functioneel eindbeeld als gebouw.

Deze module beweert dingen over BALO v1.0, een document dat niet in de repo staat. De bewaking
gaat er daarom vooral over dat **bron en lezing gescheiden blijven**: de vragen zijn woordelijk
van BALO, de plaatsing ervan is van dit lab, en het gebouw als vorm ook. Een maquette die haar
eigen lezing als brongegeven presenteert, is erger dan geen maquette -- zij ziet eruit als
architectuur.
"""
import pytest

from leefomgevinglab.usecases import eindbeeld_stelsel as eb


@pytest.fixture(scope="module")
def g():
    return eb.gebouw()


# -- Bron en lezing gescheiden ------------------------------------------------------------------

def test_de_herkomst_noemt_zowel_balo_als_het_lab(g):
    assert g["herkomst"]
    for h in g["herkomst"]:
        assert h["van"] in ("bron", "lab"), h
        assert h["wat"] and h["bron"]
    soorten = {h["van"] for h in g["herkomst"]}
    assert soorten == {"bron", "lab"}, (
        "alles 'bron' zou de eigen lezing verbergen, alles 'lab' het document wegpoetsen")


def test_het_gebouw_als_vorm_staat_als_lezing_van_dit_lab(g):
    """BALO tekent een platte figuur. Dat die zich als gebouw laat lezen is een keuze van dit
    lab, gemaakt zodat iemand zonder architectuuropleiding er omheen kan lopen -- en zo'n keuze
    hoort niet als brongegeven te worden gepresenteerd."""
    regel = next(h for h in g["herkomst"] if "gebouw als vorm" in h["wat"])
    assert regel["van"] == "lab"
    assert "platte figuur" in regel["bron"]


def test_de_plaatsing_van_de_vragen_is_een_lezing_en_de_vragen_zelf_niet(g):
    """De vragen zijn van BALO, woordelijk. Waar zij hangen is van dit lab. Dat onderscheid is
    het hele verschil tussen citeren en interpreteren."""
    vragen_regel = next(h for h in g["herkomst"] if "vensters, woordelijk" in h["wat"])
    assert vragen_regel["van"] == "bron"
    plaats_regel = next(h for h in g["herkomst"] if h["wat"].startswith("Op welk vlak"))
    assert plaats_regel["van"] == "lab"


def test_elke_vraag_is_een_vraag(g):
    """Een venster met een bewering erin zou suggereren dat BALO het antwoord al geeft."""
    for v in eb.VRAGEN:
        assert v["vraag"].endswith("?"), v["vraag"]
        assert len(v["vraag"]) > 12


# -- Het gebouw klopt met zichzelf --------------------------------------------------------------

def test_de_verdiepingen_zijn_de_informatieketen_van_balo(g):
    """Vier niveaus op elkaar: data → informatie → kennis → inzicht. De volgorde is de keten, dus
    hun nummers moeten oplopen en uniek zijn."""
    nrs = [v["nr"] for v in g["verdiepingen"]]
    assert nrs == sorted(nrs) == list(range(1, len(nrs) + 1))
    assert [v["id"] for v in g["verdiepingen"]] == ["data", "informatie", "kennis", "inzicht"]


def test_elke_verdieping_zegt_wat_er_nodig_is_om_een_niveau_hoger_te_komen(g):
    """Dat is wat een trap tot een trap maakt in plaats van een stapel dozen: zonder dit veld
    staan er vier losse begrippen boven elkaar."""
    for v in g["verdiepingen"]:
        assert v["omhoog"], f"{v['id']} zegt niet hoe je een verdieping hoger komt"
        assert v["wat"]


def test_elke_verdieping_heeft_een_aanbod_en_een_vraagkant(g):
    """De twee gevels zijn de kern van de vorm: links wordt geleverd, rechts gehaald. Een
    verdieping zonder een van beide zou aan één kant een blinde muur hebben."""
    for v in g["verdiepingen"]:
        assert v["aanbod"], f"{v['id']} heeft geen aanbodkant"
        assert v["vraag"], f"{v['id']} heeft geen vraagkant"


def test_het_zwaartepunt_verschuift_van_aanbod_naar_vraag(g):
    """**Dit is geen vormeis maar een bevinding, en zij komt uit de data zelf.** Onderin levert
    bijna alleen de aanbodkant; bovenin haalt bijna alleen de vraagkant. Precies dat maakt het
    een keten en geen stapel -- en wie het gebouw ronddraait, ziet het."""
    onder, boven = g["verdiepingen"][0], g["verdiepingen"][-1]
    assert len(onder["aanbod"]) > len(onder["vraag"]), "onderin hoort het aanbod te overheersen"
    assert len(boven["vraag"]) > len(boven["aanbod"]), "bovenin de vraag"


def test_de_bodemplaat_en_het_dak_zijn_van_een_andere_soort_dan_een_verdieping(g):
    """Zij dragen geen stap in de keten maar houden hem bij elkaar -- en dat is waarom zij in de
    maquette platen zijn en geen verdiepingen."""
    for v in (g["bodemplaat"], g["dak"]):
        assert v["kop"] and v["wat"] and v["waarom"] and v["onderdelen"] and v["bron"]
        assert "omhoog" not in v, "een plaat heeft geen volgende verdieping"


def test_het_trappenhuis_is_het_enige_dat_naar_beneden_loopt(g):
    """Zonder deze weg terug is het gebouw een fabriek. BALO zegt het zelf: de keten is een
    leercyclus, geen productielijn -- en die zin hoort dus in de bron te staan."""
    t = g["trappenhuis"]
    assert "leercyclus" in t["bron"]
    assert t["wat"] and t["waarom"]


# -- De vensters --------------------------------------------------------------------------------

def test_elk_venster_hangt_op_een_vlak_dat_bestaat(g):
    vlakken = {"dak", "bodemplaat"} | {gev["id"] for gev in g["gevels"]}
    verdiepingen = {v["id"] for v in g["verdiepingen"]}
    for v in eb.VRAGEN:
        assert v["vlak"] in vlakken, v
        if v.get("verdieping"):
            assert v["verdieping"] in verdiepingen, v


def test_elk_vlak_draagt_vensters(g):
    """Een gevel zonder vensters is een blinde muur: dan valt er aan die kant niets te ontdekken
    en is ronddraaien zinloos."""
    assert g["dak"]["vragen"] and g["bodemplaat"]["vragen"]
    for gev in g["gevels"]:
        assert gev["vragen"], f"{gev['id']} heeft geen vensters"


def test_elke_gevel_heeft_op_elke_verdieping_een_venster(g):
    """Anders heeft het kiezen van een verdieping aan één kant geen gevolg, en lijkt het alsof
    daar geen vraag ligt."""
    verdiepingen = [v["id"] for v in g["verdiepingen"]]
    for gev in g["gevels"]:
        met_verdieping = {q["verdieping"] for q in gev["vragen"] if q.get("verdieping")}
        assert met_verdieping == set(verdiepingen), (
            f"{gev['id']}: vensters op {sorted(met_verdieping)}, verwacht alle verdiepingen")


# -- De standpunten ------------------------------------------------------------------------------

def test_er_is_een_standpunt_voor_elke_kant_die_de_pagina_belooft(g):
    ids = {s["id"] for s in g["standpunten"]}
    assert {"aanbod", "vraag", "dak", "bodemplaat"} <= ids, (
        "de zijkanten, de bovenkant en de onderkant horen elk een eigen standpunt te hebben")


def test_van_boven_kijkt_naar_beneden_en_van_onder_naar_boven(g):
    """**Het teken is hier geen detail.** In CSS kantelt een positieve `rotateX` de bovenkant van
    de kijker wég, dus van bovenaf kijken is een negatieve hoek. Dat stond eerst omgekeerd, en
    toen toonde de knop 'Van boven' het gebouw van onderen -- alleen te zien door ernaar te
    kijken, niet door de code te lezen."""
    boven = next(s for s in g["standpunten"] if s["id"] == "dak")
    onder = next(s for s in g["standpunten"] if s["id"] == "bodemplaat")
    assert boven["draai"]["x"] < 0, "van boven kijken is een negatieve rotateX"
    assert onder["draai"]["x"] > 0
    assert abs(boven["draai"]["x"]) > 40 and abs(onder["draai"]["x"]) > 40, (
        "een halfslachtige hoek toont het vlak niet")


def test_de_twee_zijkanten_kijken_tegenover_elkaar(g):
    aanbod = next(s for s in g["standpunten"] if s["id"] == "aanbod")
    vraag = next(s for s in g["standpunten"] if s["id"] == "vraag")
    assert aanbod["draai"]["y"] == -vraag["draai"]["y"], (
        "aanbod en vraag zijn elkaars tegenoverliggende gevel")


def test_elk_standpunt_zegt_wat_je_er_ziet(g):
    for s in g["standpunten"]:
        assert s["naam"] and s["ziet"], s


# -- Tellingen -----------------------------------------------------------------------------------

def test_de_telling_klopt_met_de_lijsten(g):
    t = g["telling"]
    assert t["verdiepingen"] == len(g["verdiepingen"])
    assert t["vragen"] == len(eb.VRAGEN)
    assert sum(t["vragen_per_vlak"].values()) == t["vragen"]
    assert t["standpunten"] == len(g["standpunten"])
    assert t["bron_regels"] + t["lab_regels"] == len(g["herkomst"])


def test_geen_uitgeschreven_aantal_in_de_moduletekst_wijkt_af_van_de_data():
    """Dit lab leidt zijn getallen af. De enige die in de moduletekst staan zijn structureel
    (vier verdiepingen, vijf niveaus in BALO's keten) en worden hier tegen de data gelegd."""
    bron = eb.__doc__ or ""
    t = eb.telling()
    if "vier niveaus zijn de verdiepingen" in bron:
        assert t["verdiepingen"] == 4
    assert "vijf niveaus" in bron, (
        "BALO's keten telt vijf niveaus -- vier verdiepingen plus de terugkoppeling; laat dat "
        "staan, anders lijkt er een niveau te ontbreken")
