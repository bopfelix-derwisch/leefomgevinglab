"""De tien signaalregels: elk een gewone functie op één vestiging, zonder bron en zonder LLM.

Deze module test de zeven regels die aan de vergunning zelf genoeg hebben (taak 1). De drie
regels die meetdata en stroomrichting nodig hebben (`geen_onafhankelijke_meting`,
`norm_overschreden_bovenstrooms`, `stof_buiten_register`) komen in taak 2 erbij.
"""
from leefomgevinglab.usecases.toezicht import signalen


def test_dezelfde_parameter_met_twee_grenswaarden_geeft_een_signaal():
    v = {"naam": "Testlozer", "voorschriften": [
        {"parameter": "Zink", "waarde": 0.5, "eenheid": "milligram per liter"},
        {"parameter": "Zink", "waarde": 2.0, "eenheid": "milligram per liter"},
        {"parameter": "Lood", "waarde": 0.1, "eenheid": "milligram per liter"}]}
    uit = signalen.regel_meerdere_grenswaarden(v, {})
    assert len(uit) == 1
    s = uit[0]
    assert s["signaal"] == "welke grenswaarde geldt?"
    assert s["zwaarte"] == "hoog", "factor 4 verschil is meer dan 2"
    assert {b["waarde"] for b in s["bewijs"]} == {0.5, 2.0}
    assert "Lood" not in str(s["bewijs"])


def test_een_kleine_afwijking_in_grenswaarden_weegt_niet_hoog():
    v = {"voorschriften": [
        {"parameter": "Zink", "waarde": 1.0, "eenheid": "milligram per liter"},
        {"parameter": "Zink", "waarde": 1.5, "eenheid": "milligram per liter"}]}
    s = signalen.regel_meerdere_grenswaarden(v, {})[0]
    assert s["zwaarte"] == "midden", "factor 1,5 blijft onder de drempel van 2"


def test_eenmalige_grenswaarde_geeft_geen_signaal():
    v = {"voorschriften": [{"parameter": "Zink", "waarde": 1.0, "eenheid": "milligram per liter"}]}
    assert signalen.regel_meerdere_grenswaarden(v, {}) == []


def test_een_vervallen_aquo_code_geeft_een_signaal():
    v = {"voorschriften": [
        {"parameter": "Zwevende stof", "waarde": 30.0, "eenheid": "milligram per liter",
         "aquo": "ZS", "aquo_status": "Vervallen"},
        {"parameter": "Zink", "waarde": 0.5, "eenheid": "milligram per liter", "aquo": "Zn"}]}
    uit = signalen.regel_vervallen_code(v, {})
    assert len(uit) == 1
    s = uit[0]
    assert s["signaal"] == "grenswaarde op een ingetrokken code"
    assert s["zwaarte"] == "hoog", "geen geldige referentie om tegen te toetsen"
    assert [b["parameter"] for b in s["bewijs"]] == ["Zwevende stof"]


def test_geen_vervallen_codes_geeft_geen_signaal():
    v = {"voorschriften": [{"parameter": "Zink", "waarde": 0.5, "eenheid": "milligram per liter",
                             "aquo": "Zn"}]}
    assert signalen.regel_vervallen_code(v, {}) == []


def test_een_onbekende_parameternaam_geeft_een_signaal():
    v = {"voorschriften": [
        {"parameter": "Onbekend sulfiet-mengsel", "waarde": 1.0, "eenheid": "milligram per liter",
         "aquo": None},
        {"parameter": "Zink", "waarde": 0.5, "eenheid": "milligram per liter", "aquo": "Zn"}]}
    uit = signalen.regel_niet_in_referentie(v, {})
    assert len(uit) == 1
    s = uit[0]
    assert s["signaal"] == "parameter niet in de referentie"
    assert s["zwaarte"] == "midden", "drempel van 3 niet gehaald, dus geen hoog"
    assert [b["parameter"] for b in s["bewijs"]] == ["Onbekend sulfiet-mengsel"]


def test_alle_namen_herkend_geeft_geen_signaal():
    v = {"voorschriften": [{"parameter": "Zink", "waarde": 0.5, "eenheid": "milligram per liter",
                             "aquo": "Zn"}]}
    assert signalen.regel_niet_in_referentie(v, {}) == []


def test_concentratie_zonder_debietvoorschrift_geeft_een_signaal():
    v = {"voorschriften": [
        {"parameter": "Zink", "waarde": 0.5, "eenheid": "milligram per liter"},
        {"parameter": "Lood", "waarde": 0.1, "eenheid": "microgram per liter"}]}
    uit = signalen.regel_vracht_onbepaald(v, {})
    assert len(uit) == 1
    s = uit[0]
    assert s["signaal"] == "vracht niet te bepalen"
    assert {b["parameter"] for b in s["bewijs"]} == {"Zink", "Lood"}


def test_concentratie_met_debietvoorschrift_geeft_geen_signaal():
    v = {"voorschriften": [
        {"parameter": "Zink", "waarde": 0.5, "eenheid": "milligram per liter"},
        {"parameter": "Debiet", "waarde": 100.0, "eenheid": "kubieke meter per uur"}]}
    assert signalen.regel_vracht_onbepaald(v, {}) == []


def test_alle_drie_identificerende_velden_ontbreken_weegt_hoog():
    v = {"naam": "X", "url": None, "kenmerk": None, "besluitdatum": None, "voorschriften": []}
    uit = signalen.regel_vergunning_niet_te_vinden(v, {})
    assert len(uit) == 1
    s = uit[0]
    assert s["signaal"] == "vergunning niet te vinden"
    assert s["zwaarte"] == "hoog", "alle drie identificerende velden ontbreken"
    assert {b["veld"] for b in s["bewijs"]} == {"url", "kenmerk", "besluitdatum"}


def test_een_ontbrekend_veld_weegt_niet_hoog():
    v = {"url": "https://example.org/x", "kenmerk": "ABC123", "besluitdatum": None,
         "voorschriften": []}
    s = signalen.regel_vergunning_niet_te_vinden(v, {})[0]
    assert s["zwaarte"] == "midden"
    assert {b["veld"] for b in s["bewijs"]} == {"besluitdatum"}


def test_alle_velden_aanwezig_geeft_geen_signaal():
    v = {"url": "https://example.org/x", "kenmerk": "ABC123", "besluitdatum": "2020-01-01",
         "voorschriften": []}
    assert signalen.regel_vergunning_niet_te_vinden(v, {}) == []


def test_een_bemonsteringsregime_geeft_altijd_een_laag_voorbehoud():
    v = {"voorschriften": [
        {"parameter": "Zink", "waarde": 0.5, "eenheid": "milligram per liter",
         "bemonstering": "Verzamelmonster gedurende 24 uur"},
        {"parameter": "Lood", "waarde": 0.1, "eenheid": "milligram per liter",
         "bemonstering": "Steekmonster"}]}
    uit = signalen.regel_niet_regime_zuiver(v, {})
    assert len(uit) == 1
    s = uit[0]
    assert s["signaal"] == "toets niet regime-zuiver"
    assert s["zwaarte"] == "laag", "een voorbehoud, geen bevinding -- dus nooit hoger dan laag"
    assert len(s["bewijs"]) == 2


def test_geen_bemonsteringsregime_geeft_geen_signaal():
    v = {"voorschriften": [{"parameter": "Zink", "waarde": 0.5, "eenheid": "milligram per liter"}]}
    assert signalen.regel_niet_regime_zuiver(v, {}) == []


def test_geen_geldigheidsduur_geeft_precies_een_signaal_per_dossier():
    v = {"voorschriften": [
        {"parameter": "Zink", "waarde": 0.5, "eenheid": "milligram per liter"},
        {"parameter": "Lood", "waarde": 0.1, "eenheid": "milligram per liter"}]}
    uit = signalen.regel_geen_geldigheidsduur(v, {})
    assert len(uit) == 1, "één signaal voor het hele dossier, niet één per voorschrift"
    s = uit[0]
    assert s["signaal"] == "geen geldigheidsduur"
    assert s["zwaarte"] == "laag"


def test_geen_voorschriften_geeft_geen_geldigheidssignaal():
    assert signalen.regel_geen_geldigheidsduur({"voorschriften": []}, {}) == []


def test_zwaarte_werpt_keyerror_op_een_onbekende_regel():
    import pytest
    with pytest.raises(KeyError):
        signalen.zwaarte("deze_regel_bestaat_niet", 5)


def test_signalen_verzamelt_alle_regels_en_rangschikt_op_zwaarte_dan_omvang():
    v = {"naam": "Volledig geval", "url": None, "kenmerk": None, "besluitdatum": None,
         "voorschriften": [
             {"parameter": "Zink", "waarde": 0.5, "eenheid": "milligram per liter"},
             {"parameter": "Zink", "waarde": 2.0, "eenheid": "milligram per liter"},
         ]}
    uit = signalen.signalen(v, {})
    # Zowel "vergunning niet te vinden" (hoog, alle drie ontbreken) als "welke grenswaarde
    # geldt?" (hoog, factor 4) moeten er zijn, en alle "hoog"-signalen staan voor de rest.
    zwaartes = [s["zwaarte"] for s in uit]
    eerste_niet_hoog = next((i for i, z in enumerate(zwaartes) if z != "hoog"), len(zwaartes))
    assert all(z == "hoog" for z in zwaartes[:eerste_niet_hoog])
    assert zwaartes[eerste_niet_hoog:] == sorted(zwaartes[eerste_niet_hoog:],
                                                  key=lambda z: {"midden": 0, "laag": 1}[z])
    namen = {s["signaal"] for s in uit}
    assert "vergunning niet te vinden" in namen
    assert "welke grenswaarde geldt?" in namen


def test_signalen_geeft_alleen_het_geldigheidsvoorbehoud_voor_een_schone_vestiging():
    """Alle andere regels zwijgen; `geen_geldigheidsduur` vuurt altijd zodra er voorschriften
    zijn, want de Atlas kent nergens een geldigheidsperiode per voorschrift."""
    v = {"naam": "Schoon", "url": "https://example.org", "kenmerk": "K1",
         "besluitdatum": "2020-01-01", "voorschriften": [
             {"parameter": "Zink", "waarde": 0.5, "eenheid": "milligram per liter",
              "aquo": "Zn", "bemonstering": None},
             {"parameter": "Debiet", "waarde": 10.0, "eenheid": "kubieke meter per uur"}]}
    uit = signalen.signalen(v, {})
    assert len(uit) == 1
    assert uit[0]["signaal"] == "geen geldigheidsduur"
    assert uit[0]["zwaarte"] == "laag"
