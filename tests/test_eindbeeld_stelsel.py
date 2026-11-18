"""`usecases.eindbeeld_stelsel` -- het eindbeeld als doorsnede door een stuk leefomgeving.

Twee eisen staan hier centraal, en beide komen rechtstreeks uit wat er van deze maquette gevraagd
is.

**Niet vrijblijvend.** Elk ding in de maquette draagt een uitlegveld (`architectuur`) én een
doorkijk (`waar`) naar een pagina waar het in dit lab op echte data draait. Een 3D-plaat zonder
die twee is een plaatje; mét die twee is het een ingang. De tests eisen ze op élk element, en
eisen bovendien dat de doorkijk naar een route wijst die werkelijk bestaat -- een dode link is
erger dan geen link, want hij belooft iets.

**Geen vaktaal in de voorgrond.** De negen handelingen zijn BALO's informatiefuncties, maar die
term staat met opzet niet in de naam: wie geen architect is heeft er niets aan. De vakterm hoort
in het uitlegveld, zodat niemand iets verliest.
"""
import pytest

from leefomgevinglab.geluidsmeter import api as api_mod
from leefomgevinglab.usecases import eindbeeld_stelsel as eb


@pytest.fixture(scope="module")
def m():
    return eb.maquette()


@pytest.fixture(scope="module")
def routes():
    """De paden die de app werkelijk bedient."""
    return {r.path for r in api_mod.app.routes if hasattr(r, "path")}


# -- De doorkijk naar de architectuurwereld -----------------------------------------------------

def test_elk_element_zegt_hoe_het_in_vaktaal_heet(m):
    """**De brug naar de architectuurwereld.** Zonder dit veld is de maquette een plaat voor
    leken en nutteloos voor wie het formeel moet verantwoorden; mét dit veld bedient zij beide."""
    for e in eb._alle_elementen():
        assert e.get("architectuur"), f"{e.get('id')} zegt niet hoe het in vaktaal heet"
        assert len(e["architectuur"]) > 25, f"{e['id']}: te kort om iets uit te leggen"


def test_elk_element_wijst_naar_een_pagina_waar_het_echt_draait(m):
    """Dit is wat de maquette van een visual onderscheidt: elk ding is een ingang naar werkende
    code met echte data."""
    for e in eb._alle_elementen():
        assert e.get("waar"), f"{e.get('id')} heeft geen doorkijk"
        assert e.get("waar_tekst"), f"{e['id']}: een link zonder uitleg waarheen"


def test_elke_doorkijk_wijst_naar_een_route_die_bestaat(m, routes):
    """**Een dode link is erger dan geen link**, want hij belooft iets. Deze test vangt ook het
    geval dat een pagina later hernoemd wordt zonder dat iemand aan de maquette denkt."""
    dood = sorted({e["waar"] for e in eb._alle_elementen() if e["waar"] not in routes})
    assert not dood, f"doorkijk naar niet-bestaande route(s): {dood}"


def test_de_doorkijken_spreiden_over_het_hele_lab(m):
    """Zouden alle elementen naar dezelfde pagina wijzen, dan is de doorkijk een formaliteit."""
    assert len(m["telling"]["paginas"]) >= 10, m["telling"]["paginas"]


def test_de_telling_van_de_doorkijk_is_volledig(m):
    t = m["telling"]
    assert t["met_uitleg"] == t["elementen"]
    assert t["met_doorkijk"] == t["elementen"]


# -- Geen vaktaal in de voorgrond ---------------------------------------------------------------

def test_de_handelingen_heten_in_gewone_woorden(m):
    """"Niet zo noemen", was de eis. De negen zijn BALO's informatiefuncties, maar de naam die
    een lezer ziet is een werkwoord dat iedereen kent."""
    verboden = ("informatiefunctie", "valideren", "registreren", "ontsluiten", "terugkoppelen",
                 "beschikbaar stellen", "lokaliseren")
    for h in m["handelingen"]:
        laag = h["naam"].lower()
        for woord in verboden:
            assert woord not in laag, f"{h['naam']}: {woord!r} is vaktaal, zet die in de uitleg"
        assert h["code"].startswith("F"), "de code hoort er wel te zijn, voor wie hem zoekt"


def test_de_vakterm_staat_wel_in_het_uitlegveld(m):
    """Weglaten zou het andere uiterste zijn: dan kan een architect de maquette niet plaatsen."""
    for h in m["handelingen"]:
        assert "nformatiefunctie" in h["architectuur"], h["naam"]
        assert h["code"] in h["architectuur"], f"{h['naam']} noemt zijn eigen code niet"


def test_de_processen_dragen_hun_waardestroom_in_de_uitleg(m):
    for p in m["processen"]:
        assert "aardestroom W" in p["architectuur"], p["naam"]


# -- De vier lagen -------------------------------------------------------------------------------

def test_de_lagen_lopen_van_het_gebied_tot_de_bodem(m):
    assert [l["id"] for l in m["lagen"]] == ["gebied", "handelingen", "aansluitingen", "bodem"]
    nrs = [l["nr"] for l in m["lagen"]]
    assert nrs == sorted(nrs) == list(range(1, len(nrs) + 1))


def test_alleen_de_standaardenlaag_is_een_doorsnede(m):
    """Een doorsnede is iets wat je pas ziet als je opensnijdt. Zouden alle lagen zo heten, dan
    zegt het woord niets meer."""
    snij = [l["id"] for l in m["lagen"] if l["snijvlak"]]
    assert snij == ["aansluitingen"], snij


def test_het_gebied_is_concreet_en_niet_abstract(m):
    """De eerdere maquettes faalden op abstractie. De bovenste laag moet dingen bevatten die
    iemand kan aanwijzen: een bedrijf, een punt in de rivier, een woonwijk."""
    soorten = {g["soort"] for g in m["gebied"]}
    assert {"bedrijf", "water", "kwetsbaar"} <= soorten, soorten
    for g in m["gebied"]:
        assert g["wat"] and not g["wat"].startswith("Een informatie"), g["naam"]


# -- De standaardenlaag --------------------------------------------------------------------------

def test_elke_aansluiting_zegt_wat_er_zonder_de_standaard_misgaat(m):
    """Dat is waarom deze laag bestaat: een standaard is onzichtbaar tot zij ontbreekt. Zonder
    dit veld is het een opsomming van afkortingen."""
    for a in m["aansluitingen"]:
        assert a["zonder"], f"{a['object']} zegt niet wat er zonder misgaat"
        assert a["standaard"] and a["verbindt"]


def test_de_genoemde_standaarden_zijn_de_standaarden_die_dit_lab_echt_gebruikt(m):
    """Verzonnen of modieuze standaarden zouden de maquette onbetrouwbaar maken. Deze komen
    allemaal elders in dit lab voor."""
    genoemd = " ".join(a["standaard"] for a in m["aansluitingen"])
    for s in ("IMEV", "Aquo", "BAG", "STOP/TPOD", "OGC API"):
        assert s in genoemd, s


# -- Data die stroomt ------------------------------------------------------------------------------

def test_er_stroomt_data_in_twee_richtingen(m):
    """**De tweede richting is het punt.** Een plaat die alleen omhoog tekent maakt er een
    fabriek van; BALO noemt de keten uitdrukkelijk een leercyclus."""
    richtingen = {s["richting"] for s in m["stromen"]}
    assert richtingen == {"omhoog", "omlaag"}
    omlaag = next(s for s in m["stromen"] if s["richting"] == "omlaag")
    assert "leercyclus" in omlaag["architectuur"]


def test_elke_stroom_begint_en_eindigt_in_een_bestaande_laag(m):
    ids = {l["id"] for l in m["lagen"]}
    for s in m["stromen"]:
        assert s["van"] in ids and s["naar"] in ids, s


# -- Waarde en herkomst ----------------------------------------------------------------------------

def test_de_maquette_zegt_wat_het_oplevert_en_voor_wie(m):
    """Een maquette zonder dit is een plaat voor de bouwer."""
    assert len(m["waarde"]) >= 5
    wie = " ".join(w["wie"].lower() for w in m["waarde"])
    for doelgroep in ("bedrijf", "toezichthouder", "omwonende", "beleid"):
        assert doelgroep in wie, doelgroep
    for w in m["waarde"]:
        assert len(w["waarde"]) > 40, f"{w['wie']}: te vaag om waarde te heten"


def test_de_herkomst_scheidt_balo_van_de_lezing_van_dit_lab(m):
    soorten = {h["van"] for h in m["herkomst"]}
    assert soorten == {"bron", "lab"}
    for h in m["herkomst"]:
        assert h["wat"] and h["bron"]
    gewone_taal = next(h for h in m["herkomst"] if "gewone taal" in h["wat"])
    assert gewone_taal["van"] == "lab", (
        "de vertaling naar gewone woorden is een keuze van dit lab, geen brongegeven")


def test_de_telling_klopt_met_de_lijsten(m):
    t = m["telling"]
    assert t["lagen"] == len(m["lagen"])
    assert t["handelingen"] == len(m["handelingen"])
    assert t["aansluitingen"] == len(m["aansluitingen"])
    assert t["elementen"] == len(eb._alle_elementen())
