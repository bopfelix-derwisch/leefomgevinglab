import pytest

from leefomgevinglab.usecases.gebruiksruimte import waterprofiel as wp

_IJSSEL = {"waterlichaam": "IJssel", "owl_id": "NL93_IJSSEL", "stroomgebiedsdistrict": "NLRN",
           "watertype": "R7", "watercategorie": "1", "waterstatus": "Sterk veranderd",
           "waterbeheerder": "Ministerie van IenW (Rijkswaterstaat)",
           "omvang": 123.4, "omvang_eenheid": "km2", "gemiddelde_diepte": 4.2,
           "rijkswater": True}
_MEER = {**_IJSSEL, "waterlichaam": "IJsselmeer", "owl_id": "NL92_IJSSELMEER",
         "watertype": "M21", "watercategorie": "2", "omvang": 1100.0, "gemiddelde_diepte": 4.5}
_KUST = {**_IJSSEL, "waterlichaam": "Waddenzee", "owl_id": "NL81_1",
         "watertype": "K2", "watercategorie": "3", "omvang": 2154.51, "gemiddelde_diepte": 3.0}
_OVERGANG = {**_IJSSEL, "waterlichaam": "Eems-Dollard", "owl_id": "NL92_EEMSDOLLARD",
             "watertype": "O2", "watercategorie": "4", "omvang": 500.0, "gemiddelde_diepte": 5.0}
_TERRITORIAAL = {**_IJSSEL, "waterlichaam": "Maas territoriaal water", "owl_id": "NL95_MAAS_TEW",
                 "watertype": "K0", "watercategorie": "5", "omvang": 300.0, "gemiddelde_diepte": 8.0}
_ONBEKEND = {**_IJSSEL, "waterlichaam": "Onbekend water", "owl_id": "NL00_ONBEKEND",
             "watertype": None, "watercategorie": "9", "omvang": 10.0}
# De KRW-service levert `gemdiepte` in de praktijk nooit als een echte meting: geverifieerd
# 2026-09-23 dat het veld in alle 54 vlakken en 35 lijnen exact -9999 is. De andere fixtures
# hierboven gebruiken 4.2 e.d. om andere aspecten van het profiel te testen; deze fixture bestaat
# specifiek om die sentinel zelf te toetsen.
_IJSSEL_SENTINEL = {**_IJSSEL, "gemiddelde_diepte": -9999}


def test_gemdiepte_sentinel_wordt_geen_none():
    """Bevinding 4 van de eindreview: de KRW-service levert `gemdiepte` nooit als echte meting —
    het veld is in alle 54 vlakken en 35 lijnen exact -9999 (geverifieerd 2026-09-23). Ongefilterd
    kwam dat als `water.gemiddelde_diepte: -9999` de API uit, gepresenteerd als een getal."""
    p = wp.profiel(_IJSSEL_SENTINEL)
    assert p["echt"]["gemiddelde_diepte"] is None


def test_een_echte_positieve_diepte_blijft_gewoon_staan():
    p = wp.profiel(_IJSSEL)
    assert p["echt"]["gemiddelde_diepte"] == 4.2


def test_het_echte_deel_komt_ongewijzigd_uit_de_bron():
    p = wp.profiel(_IJSSEL)
    assert p["echt"]["naam"] == "IJssel"
    assert p["echt"]["owl_id"] == "NL93_IJSSEL"
    assert p["echt"]["watertype"] == "R7"
    assert p["echt"]["beheerder"] == "Ministerie van IenW (Rijkswaterstaat)"
    assert p["echt"]["omvang"] == 123.4
    # niets uit het echte deel mag verzonnen zijn
    assert set(p["echt"]) <= {"naam", "owl_id", "stroomgebiedsdistrict", "watertype",
                              "watercategorie", "waterstatus", "beheerder", "omvang",
                              "omvang_eenheid", "gemiddelde_diepte"}


def test_elk_afgeleid_getal_heeft_een_herkomstregel():
    p = wp.profiel(_IJSSEL)
    assert p["afgeleid"]["debiet_m3_s"] > 0
    assert p["afgeleid"]["parameters"]
    for sleutel in p["afgeleid"]:
        assert sleutel in p["herkomst"], f"{sleutel} zonder herkomst"
        assert p["herkomst"][sleutel]


def test_echt_en_afgeleid_overlappen_niet():
    """De scheiding is het hele punt; een veld mag niet in beide zitten."""
    p = wp.profiel(_IJSSEL)
    assert set(p["echt"]) & set(p["afgeleid"]) == set()


def test_verschillende_categorieen_geven_verschillende_profielen():
    rivier, meer, kust = wp.profiel(_IJSSEL), wp.profiel(_MEER), wp.profiel(_KUST)
    debieten = {rivier["afgeleid"]["debiet_m3_s"], meer["afgeleid"]["debiet_m3_s"],
                kust["afgeleid"]["debiet_m3_s"]}
    assert len(debieten) == 3, "zonder differentiatie is 'een profiel per water' een lege huls"
    normen = {p["afgeleid"]["parameters"][0]["norm_mg_l"] for p in (rivier, meer, kust)}
    assert len(normen) > 1


def test_elk_profiel_houdt_een_parameter_zonder_ruimte():
    """PFOA: achtergrond boven de norm. Zonder dat mist elke locatie de scherpste uitkomst."""
    for cs in (_IJSSEL, _MEER, _KUST):
        ps = wp.profiel(cs)["afgeleid"]["parameters"]
        assert any(p["achtergrond_mg_l"] >= p["norm_mg_l"] for p in ps)
        assert any(p["zzs"] for p in ps)


def test_spectrum_blijft_intact_in_elke_categorie():
    """In élke categorie — ook overgangswater en de terugval — houden minstens twee van de vier
    parameters ruimte (achtergrond < norm), en heeft PFOA die nooit. Zonder deze garantie klapt
    het parameterspectrum in: met de oorspronkelijke kust- en overgangsfactor hield nog maar 1
    van de 4 parameters ruimte, en kreeg een bezoeker die daar prikt overal 'geen ruimte'."""
    for cs in (_IJSSEL, _MEER, _KUST, _OVERGANG, _TERRITORIAAL, _ONBEKEND):
        parameters = wp.profiel(cs)["afgeleid"]["parameters"]
        met_ruimte = [p for p in parameters if p["achtergrond_mg_l"] < p["norm_mg_l"]]
        assert len(met_ruimte) >= 2, cs["watercategorie"]

        pfoa = next(p for p in parameters if p["naam"] == "PFOA")
        assert pfoa["achtergrond_mg_l"] >= pfoa["norm_mg_l"], cs["watercategorie"]


def test_categorie_5_is_geen_terugval_meer():
    """Bevinding 10 van de eindreview: owlcat '5' (de vier territoriale wateren) viel voorheen
    in de terugval 'onbekend type'. Geverifieerd 2026-09-23 dat categorie 5 live voorkomt bij
    Eems/Maas/Rijn/Schelde territoriaal water, watertype K0."""
    p = wp.profiel(_TERRITORIAAL)
    assert p["volledig"] is True
    assert p["afgeleid"]["categorie_naam"] == "territoriaal water"
    assert "terugval" not in p["herkomst"]["debiet_m3_s"]


def test_onbekende_categorie_valt_terug_zonder_te_knallen():
    p = wp.profiel({**_IJSSEL, "watercategorie": "9", "watertype": None})
    assert p["afgeleid"]["debiet_m3_s"] > 0
    assert "terugval" in p["herkomst"]["debiet_m3_s"]
    assert p["volledig"] is False


def test_zonder_waterlichaam_is_er_geen_profiel():
    p = wp.profiel({"rijkswater": False, "waterlichaam": None, "owl_id": None})
    assert p["afgeleid"] == {}
    assert p["volledig"] is False
    assert p["reden"]


def test_als_waterlichaam_levert_wat_de_rekensom_verwacht():
    w = wp.als_waterlichaam(wp.profiel(_IJSSEL))
    assert w["debiet_m3_s"] > 0
    for p in w["parameters"]:
        assert {"naam", "norm_mg_l", "achtergrond_mg_l", "zzs", "toelichting"} <= set(p)
