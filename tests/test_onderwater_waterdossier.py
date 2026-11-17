"""`onderwater.waterdossier` -- het informatiemodel en de kennisgraaf van het waterdossier.

**Waarom dit op `/onderwater` hoort.** Die pagina legt uit wat er onder water gebeurt, en deed dat
voor de twee signaalpagina's. Maar het waterdossier draagt twee dingen die nergens samen worden
uitgelegd: een **informatiemodel** dat per veld een zekerheid meevoert
(`kmg.lozingsmodel`) en **twee grafen** -- een stoffengraaf als referentie en de toezichtgraaf over
het register. Wie wil begrijpen waarom een getal op `/kmg` of `/toezicht` staat zoals het staat,
heeft die twee nodig.

**Dezelfde eis als de rest van die pagina: niets getypt.** Elke telling komt uit de bron die zij
beschrijft -- de constanten van het informatiemodel, de knopen en randen van de stoffengraaf, de
klassen en triples van de toezichtgraaf. Een uitlegpagina die haar eigen getallen verzint is
precies zo onbetrouwbaar als de ondoorzichtigheid die zij moet oplossen.
"""
import pytest

from leefomgevinglab.usecases import onderwater
from leefomgevinglab.usecases.kmg import lozingsmodel
from leefomgevinglab.usecases.toezicht import graaf as toezichtgraaf

_STOFFEN = {
    "knopen": [{"id": "prtr:A", "soort": "prtr"}, {"id": "cas:1", "soort": "cas"},
                {"id": "aquo:Zn", "soort": "aquo"}],
    "randen": [{"van": "prtr:A", "naar": "cas:1", "soort": "cas",
                 "herkomst": "E-PRTR-verordening bijlage II"},
                {"van": "cas:1", "naar": "aquo:Zn", "soort": "aquo",
                 "herkomst": "Aquo-domeintabel Parameter"}],
    "telling": {"prtr_stoffen": 3, "cas_en_hand": 2, "geen_brug": 1, "somparameters": 1},
    "per_herkomst": {"E-PRTR-verordening bijlage II": 1, "Aquo-domeintabel Parameter": 1},
}
_TOEZICHT = {"triples": 73071, "vestigingen": 69, "voorschriften": 650, "signalen": 598,
              "overschrijdingen": 29}


@pytest.fixture
def w():
    return onderwater.waterdossier(stoffengraaf=_STOFFEN, toezichtgraaf=_TOEZICHT)


# -- Het informatiemodel ------------------------------------------------------------------------

def test_de_vier_zekerheden_komen_uit_het_model_zelf(w):
    """Niet opnieuw opgesomd: verschuift de reeks in `lozingsmodel`, dan verschuift deze pagina
    mee. Dat is het verschil tussen uitleggen en navertellen."""
    assert [z["naam"] for z in w["informatiemodel"]["zekerheden"]] == list(
        lozingsmodel.ZEKERHEDEN)
    for z in w["informatiemodel"]["zekerheden"]:
        assert z["wat"], f"{z['naam']} zonder uitleg zegt niets"


def test_elk_veld_zegt_welke_zekerheid_het_hoogstens_kan_halen(w):
    """**Dit is de kern van dit model, en het staat nergens anders uitgelegd.** Twee velden kunnen
    per bron nooit 'uit de bron' zijn: de hoedanigheid is altijd een aanname en de
    geldigheidsperiode ontbreekt altijd. Een model dat alleen velden vastlegt, laat een
    onvolledige vergunning er netjes uitzien."""
    velden = {v["veld"]: v for v in w["informatiemodel"]["velden"]}
    assert velden["hoedanigheid"]["hoogste_zekerheid"] == "aangenomen"
    assert velden["geldigheid"]["hoogste_zekerheid"] == "ontbreekt"
    assert velden["waarde"]["hoogste_zekerheid"] == "uit de bron"
    for v in velden.values():
        assert v["hoogste_zekerheid"] in lozingsmodel.ZEKERHEDEN
        assert v["waarom"], f"{v['veld']} zonder reden is een bewering"


def test_de_aanname_over_de_hoedanigheid_wordt_woordelijk_uit_het_model_gehaald(w):
    """Deze aanname is bepalend voor zink -- de KRW-norm geldt op de opgeloste fractie -- dus mag
    de uitleg hier niet gaan afwijken van wat de code doet."""
    h = w["informatiemodel"]["hoedanigheid_aanname"]
    assert h["code"] == lozingsmodel.HOEDANIGHEID_AANNAME["code"]
    assert h["herkomst"] == lozingsmodel.HOEDANIGHEID_AANNAME["herkomst"]


def test_de_tellingen_van_het_informatiemodel_zijn_afgeleid(w):
    im = w["informatiemodel"]
    assert im["aantal_eenheden"] == len(lozingsmodel.EENHEDEN)
    assert im["aantal_grondslagen"] == len(set(lozingsmodel.GRONDSLAGEN.values()))
    assert im["aantal_bemonsteringstermen"] == len(lozingsmodel.GRONDSLAGEN)


# -- De twee grafen -----------------------------------------------------------------------------

def test_er_zijn_twee_grafen_en_zij_doen_iets_anders(w):
    """**Het punt van deze sectie.** "De kennisgraaf" bestaat niet: er zijn twee grafen met een
    ander doel. De stoffengraaf is een *referentie* -- hij legt uit hoe een stofnaam in de ene
    bron aan een code in de andere hangt. De toezichtgraaf is een *registergraaf* -- hij draagt
    de vergunningen, metingen en signalen zelf. Ze verwisselen leidt tot de verwachting dat je
    aan de ene kant vragen kunt stellen die alleen aan de andere kant te beantwoorden zijn."""
    grafen = {g["id"]: g for g in w["grafen"]}
    assert set(grafen) == {"stoffen", "toezicht"}
    assert grafen["stoffen"]["soort"] == "referentiegraaf"
    assert grafen["toezicht"]["soort"] == "registergraaf"
    for g in grafen.values():
        assert g["wat"] and g["waarom_graaf"] and g["pagina"]
        assert g["telling"], f"{g['id']} zonder telling"


def test_de_stoffengraaf_telt_uit_de_graaf_en_niet_uit_de_tekst(w):
    g = next(x for x in w["grafen"] if x["id"] == "stoffen")
    assert g["telling"]["knopen"] == len(_STOFFEN["knopen"])
    assert g["telling"]["randen"] == len(_STOFFEN["randen"])
    # Per soort knoop, zodat zichtbaar is dat het drie lagen zijn: stof, CAS, Aquo.
    assert g["telling"]["per_soort"] == {"prtr": 1, "cas": 1, "aquo": 1}


def test_elke_rand_in_de_stoffengraaf_draagt_een_herkomst(w):
    """Dát is wat deze graaf boven een tabel uittilt: niet alleen dát twee namen bij elkaar
    horen, maar op wiens gezag. Een rand zonder herkomst is een bewering zonder bron."""
    g = next(x for x in w["grafen"] if x["id"] == "stoffen")
    assert g["telling"]["randen_met_herkomst"] == g["telling"]["randen"]
    assert g["herkomsten"], "de bronnen achter de randen horen benoemd"


def test_de_toezichtgraaf_noemt_zijn_klassen_uit_het_model(w):
    """Een opsomming die naast de code kan gaan liggen is waardeloos op een uitlegpagina."""
    g = next(x for x in w["grafen"] if x["id"] == "toezicht")
    assert "Vestiging" in g["klassen"] and "Signaal" in g["klassen"]
    assert "Overschrijding" in g["klassen"], (
        "deze klasse is er juist bijgekomen om een onbruikbaar trage query te vervangen")
    assert g["telling"]["triples"] == _TOEZICHT["triples"]
    assert g["telling"]["signalen"] == _TOEZICHT["signalen"]


def test_zonder_cijfers_valt_de_sectie_niet_om_maar_zegt_zij_dat():
    """De toezichtgraaf wordt pas geteld als hij geladen is; de pagina mag niet wachten en mag
    ook niet doen alsof hij leeg is."""
    w = onderwater.waterdossier(stoffengraaf=None, toezichtgraaf=None)
    for g in w["grafen"]:
        assert g["telling"] == {} or g["telling"] is None or not g["telling"]
        assert g["nog_niet_geteld"] is True
    # Het informatiemodel heeft geen bron nodig: dat zijn constanten.
    assert w["informatiemodel"]["zekerheden"]


def test_geen_getal_staat_los_in_de_uitlegteksten(w):
    """Zelfde bewaking als de rest van `/onderwater`: een tekst met een ingetypt aantal gaat
    liegen zodra de code schuift, en juist deze pagina moet de rest controleerbaar maken."""
    import re
    teksten = [w["informatiemodel"]["wat"], w["informatiemodel"]["waarom"]]
    for v in w["informatiemodel"]["velden"]:
        teksten.append(v["waarom"])
    for z in w["informatiemodel"]["zekerheden"]:
        teksten.append(z["wat"])
    for g in w["grafen"]:
        teksten += [g["wat"], g["waarom_graaf"]]
    fouten = [f"{getal!r} in: {tekst[:80]}" for tekst in teksten
              for getal in re.findall(r"\b\d+\b", tekst or "")
              if not (len(getal) == 4 and getal.startswith("20"))]
    assert not fouten, "los ingetypt getal:\n" + "\n".join(fouten)
