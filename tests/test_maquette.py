"""`usecases.maquette` -- het stelselbeeld 2037 met de transitie als derde as.

Deze module beweert dingen over twee documenten die niet in de repo staan. De bewaking gaat er
daarom vooral over dat **bron en lezing gescheiden blijven**: wat geciteerd is mag niet verschuiven,
en wat dit lab erbij bedenkt moet als zodanig gemarkeerd zijn. Een maquette die een eigen lezing
als brongegeven presenteert, is erger dan geen maquette -- zij ziet eruit als architectuur.
"""
import re

import pytest

from leefomgevinglab.usecases import balo as balo_mod
from leefomgevinglab.usecases import maquette as mq


@pytest.fixture(scope="module")
def m():
    return mq.maquette()


# -- Bron en lezing gescheiden ------------------------------------------------------------------

def test_elke_herkomstregel_zegt_of_het_bron_of_lab_is(m):
    """Zonder dit veld is niet te zien welk deel van de plaat uit het document komt. Dat is op een
    architectuurpagina geen detail: een lezer die de lezing van dit lab voor beleid aanneemt,
    neemt een besluit op grond van iets wat niemand heeft vastgesteld."""
    assert m["herkomst"], "zonder herkomst is de maquette niet te controleren"
    for h in m["herkomst"]:
        assert h["van"] in ("bron", "lab"), h
        assert h["wat"] and h["bron"]
    soorten = {h["van"] for h in m["herkomst"]}
    assert soorten == {"bron", "lab"}, (
        "beide soorten horen erin te staan -- alles 'bron' zou de eigen lezing verbergen, "
        "alles 'lab' zou het document wegpoetsen")


def test_de_plaatsing_in_lagen_staat_als_lezing_van_dit_lab(m):
    """**Het eerlijkste punt van deze pagina.** De bron plaatst de voorzieningen niet in lagen;
    dat doet dit lab, op grond van de geciteerde fasetekst. Juist die plaatsing is wat de maquette
    laat bewegen, dus zij mag nergens als brongegeven doorgaan."""
    regel = next(h for h in m["herkomst"] if "laag" in h["wat"] and "voorziening" in h["wat"])
    assert regel["van"] == "lab"
    assert "De bron plaatst de voorzieningen niet in lagen" in regel["bron"]


def test_de_waardestromen_zijn_woordelijk_die_van_de_balo_pagina():
    """`/balo` leunt op v0.9, deze module op v1.0. Lopen die uiteen, dan staan er twee
    verschillende W-definities in hetzelfde lab en is minstens één pagina verouderd. Nagekeken:
    tussen die versies zijn de waardestromen niet veranderd -- en deze test houdt dat zo."""
    hier = [w["wat"] for w in mq.WAARDESTROMEN]
    daar = [(v.get("naam") or v.get("titel")) for v in balo_mod.WAARDESTROMEN] \
        if isinstance(balo_mod.WAARDESTROMEN, list) else None
    assert daar, "de BALO-pagina draagt geen waardestromenlijst meer -- dan moet deze test mee"
    assert hier == daar, (
        "de waardestromen van /balo (v0.9) en deze module (v1.0) lopen uiteen; één van de twee "
        "pagina's is dan verouderd")


def test_wat_vaststaat_wordt_apart_gehouden_van_het_voorstel(m):
    """De bron zegt zelf dat fasering en jaartallen een voorstel zijn en dat er maar een handvol
    dingen vaststaat. Een plaat die dat niet onderscheidt, leest als besloten beleid."""
    assert m["vaststaand"]
    tekst = " ".join(m["vaststaand"]).lower()
    assert "2037" in tekst and "dso" in tekst
    assert len(m["vaststaand"]) < len(m["plateaus"]), (
        "er hoort minder vast te staan dan er plateaus zijn -- anders is het geen voorstel")


# -- De plateaus en de gaps ---------------------------------------------------------------------

def test_elk_plateau_draagt_zijn_eigen_stelselstand_geciteerd(m):
    for p in m["plateaus"]:
        assert p["jaren"] and p["naam"] and p["stelselstand"]


def test_de_maquette_heeft_iets_te_tonen_want_er_bewegen_voorzieningen(m):
    """**Als niets van laag wisselt, is een derde as versiering.** Deze test is de rechtvaardiging
    van de hele pagina: een transitiepad waarin alles blijft staan waar het staat, kun je als
    tabel tonen."""
    t = m["telling"]
    assert t["voorzieningen_die_bewegen"] >= 3, (
        f"maar {t['voorzieningen_die_bewegen']} voorzieningen wisselen van laag -- dan is de "
        "tijdas geen inzicht maar decoratie")
    assert t["voorzieningen_die_bewegen"] < t["voorzieningen"], (
        "als álles beweegt is er geen stabiele kern, en dan klopt de lezing waarschijnlijk niet")


def test_een_gap_wordt_afgeleid_en_nooit_apart_ingetypt(m):
    """In ArchiMate en TOGAF is de gap het object waartegen je plant. Zou hij apart genoteerd
    worden, dan kan hij uit de pas lopen met de plateaus die hij verbindt -- en dan plant iemand
    tegen een verschil dat er niet is."""
    for v in m["voorzieningen"]:
        assert len(v["gaps"]) == len(m["plateaus"]) - 1, v["id"]
        for g in v["gaps"]:
            verwacht = v["lagen"][g["van_plateau"]] != v["lagen"][g["naar_plateau"]]
            if g["van_laag"] and g["naar_laag"]:
                assert g["verschuift"] == verwacht, (v["id"], g)
            assert g["vervalt"] == (bool(g["van_laag"]) and g["naar_laag"] is None)


def test_een_afgebouwde_voorziening_verdwijnt_niet_stil(m):
    """Afbouw is de kern van fase 4. Een voorziening zonder laag hoort in `afgebouwd` te staan
    mét haar fasetekst -- haar weglaten zou juist het resultaat van de transitie onzichtbaar
    maken."""
    laatste = m["plateaus"][-1]
    assert laatste["afgebouwd"], (
        "op het laatste plateau is niets afgebouwd -- dan mist de maquette het eindbeeld van de "
        "roadmap, die zegt dat tijdelijke portalen, registers en viewers weg zijn")
    for a in laatste["afgebouwd"]:
        assert a["tekst"], f"{a['id']} valt weg zonder dat er staat waarom"


def test_elk_beslismoment_hangt_aan_een_bestaand_plateau(m):
    ids = {p["id"] for p in m["plateaus"]}
    for b in m["beslismomenten"]:
        assert b["plateau"] in ids, b
        assert b["kop"] and b["vraag"] and b["wanneer"]


def test_een_voorziening_met_een_besluit_verwijst_naar_een_bestaand_plateau(m):
    ids = {p["id"] for p in m["plateaus"]}
    met = [v for v in m["voorzieningen"] if v["besluit"]]
    assert met, "de roadmap zet ruitjes bij enkele voorzieningen; die horen hier terug"
    for v in met:
        assert v["besluit"]["plateau"] in ids, v["id"]
        assert v["besluit"]["vraag"].endswith("?"), (
            f"{v['id']}: een besluit is hier een open vraag, geen uitkomst")


def test_een_open_rol_blijft_open(m):
    """De roadmap zet een `?` waar de rol of eigenaar in 2037 nog te besluiten is. Dat invullen
    zou de belangrijkste onzekerheid van het stuk wegpoetsen."""
    t = m["telling"]
    assert t["rollen_open_in_2037"] > 0
    assert t["rollen_open_in_2037"] < t["voorzieningen"], (
        "als alles open is, zegt de roadmap niets; als niets open is, is het geen voorstel")


# -- Functies en lagen --------------------------------------------------------------------------

def test_elke_functie_staat_in_een_bestaande_laag_met_haar_plek_in_2037(m):
    ids = {l["id"] for l in m["lagen"]}
    for f in m["functies"]:
        assert f["laag"] in ids, f
        assert f["plek_2037"], f"{f['id']} zonder plaatsbepaling is geen verdeling"


def test_de_functies_zijn_over_alle_drie_de_lagen_verdeeld(m):
    """Zitten ze allemaal in één laag, dan is "verdeeld" een woord zonder inhoud -- en dan is het
    federatieve beeld van de bron niet weergegeven."""
    per = m["telling"]["functies_per_laag"]
    assert len(per) == len(m["lagen"])
    assert all(n > 0 for n in per.values()), per


def test_elke_voorziening_verwijst_naar_bestaande_waardestromen_en_functies(m):
    w_ids = {w["id"] for w in m["waardestromen"]}
    f_ids = {f["id"] for f in m["functies"]}
    for v in m["voorzieningen"]:
        assert set(v["w"]) <= w_ids, (v["id"], set(v["w"]) - w_ids)
        assert set(v["f"]) <= f_ids, (v["id"], set(v["f"]) - f_ids)


# -- Geen getal getypt --------------------------------------------------------------------------

def test_geen_uitgeschreven_aantal_in_de_moduletekst_wijkt_af_van_de_data():
    """Dit lab leidt zijn getallen af, en deze module typte er bij het schrijven twee verkeerd
    ("de negen voorzieningen" bij tien rijen). De twee die overblijven zijn structureel -- drie
    lagen, vijf plateaus -- en worden hier tegen de data gelegd."""
    bron = mq.__doc__ or ""
    t = mq.telling()
    if "drie lagen" in bron:
        assert t["lagen"] == 3
    if "Vijf" in bron or "vijf plateaus" in bron:
        assert t["plateaus"] == 5
    for woord, getal in (("negen voorzieningen", "voorzieningen"),
                          ("acht waardestromen", "waardestromen"),
                          ("negen informatiefuncties", "functies")):
        assert woord not in bron, (
            f"{woord!r} staat in de moduletekst; gebruik de afgeleide telling "
            f"({t[getal]}) in plaats van een getal in proza")


def test_de_telling_klopt_met_de_lijsten(m):
    t = m["telling"]
    assert t["voorzieningen"] == len(m["voorzieningen"])
    assert t["plateaus"] == len(m["plateaus"])
    assert t["functies"] == len(m["functies"])
    assert t["waardestromen"] == len(m["waardestromen"])
    assert t["beslismomenten"] == len(m["beslismomenten"])
    assert sum(t["functies_per_laag"].values()) == t["functies"]


def test_geen_fasetekst_is_stilletjes_leeg(m):
    """De fasetekst is het citaat; een lege cel zou als "er gebeurt niets" lezen terwijl de bron
    daar wél iets zegt."""
    for v in m["voorzieningen"]:
        for p in m["plateaus"]:
            assert v["fasen"].get(p["id"]), f"{v['id']} heeft geen tekst op {p['jaren']}"
