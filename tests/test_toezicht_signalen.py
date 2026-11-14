"""De tien signaalregels: elk een gewone functie op één vestiging, zonder bron en zonder LLM.

Deze module test alle tien regels: de zeven die aan de vergunning zelf genoeg hebben (taak 1) en
de drie die meetdata en stroomrichting nodig hebben, via `context` aangeleverd (taak 2):
`geen_onafhankelijke_meting`, `norm_overschreden_bovenstrooms`, `stof_buiten_register`.
"""
import pytest

from leefomgevinglab.usecases.toezicht import signalen

# De plan-tekst noemt deze twee fixtures (stap 4 van taak 2) zonder ze te definiëren -- dat is
# met opzet aan de uitvoerder gelaten. Ze staan hier, aan de kop van het bestand, en zijn zo
# samengesteld dat `signalen.signalen(...)` alle tien regels tegelijk laat vuren: dat is het punt
# van de taalregel-test hieronder, die anders ongemerkt een subset zou kunnen dekken.
#
# Welke regel waarop in deze vestiging/context vuurt:
# - geen_onafhankelijke_meting: "Zwevende stof" (ZS) en "Zuurgraad" (pH) zijn vergund maar staan
#   niet in `gemeten_codes` (alleen Zn is "gemeten"); `stoffen_met_norm` bevat geen van beide
#   codes, dus deze twee signalen komen op `midden` uit -- de `hoog`-tak zelf heeft haar eigen
#   directe tests op `regel_geen_onafhankelijke_meting`.
# - vervallen_code: "Zwevende stof" draagt `aquo_status: "Vervallen"`.
# - niet_in_referentie: "Onbekend sulfiet-mengsel" heeft `aquo: None`.
# - meerdere_grenswaarden: Zink heeft twee grenswaarden (0.5 en 2.0 mg/l).
# - vracht_onbepaald: alle concentratievoorschriften zijn in mg/l, geen enkel debietvoorschrift.
# - norm_overschreden_bovenstrooms: de geïnjecteerde `is_bovenstrooms` geeft altijd `True`, en er
#   staan overschrijdingen in de context.
# - stof_buiten_register: PFOA staat in `overschrijdingen` maar niet in `register_codes`.
# - vergunning_niet_te_vinden: `kenmerk` ontbreekt.
# - niet_regime_zuiver: de twee Zink-voorschriften dragen een `bemonstering`.
# - geen_geldigheidsduur: er zijn voorschriften, en de Atlas kent nergens een geldigheidsperiode.
VESTIGING_MET_ALLES = {
    "naam": "Volledig signaaldossier (test)",
    "url": "https://example.org/vergunning",
    "kenmerk": None,
    "besluitdatum": "2020-01-01",
    "voorschriften": [
        {"parameter": "Zink", "waarde": 0.5, "eenheid": "milligram per liter", "aquo": "Zn",
         "bemonstering": "Steekmonster"},
        {"parameter": "Zink", "waarde": 2.0, "eenheid": "milligram per liter", "aquo": "Zn",
         "bemonstering": "Steekmonster"},
        {"parameter": "Zwevende stof", "waarde": 30.0, "eenheid": "milligram per liter",
         "aquo": "ZS", "aquo_status": "Vervallen"},
        {"parameter": "Onbekend sulfiet-mengsel", "waarde": 1.0, "eenheid": "milligram per liter",
         "aquo": None},
        {"parameter": "Zuurgraad", "waarde": 7.0, "eenheid": "dimensieloos", "aquo": "pH"},
    ],
}

CONTEXT_MET_ALLES = {
    "gemeten_codes": {"Zn"},
    "stoffen_met_norm": {"Ntot"},  # geen van de ongemeten codes (ZS, pH) hier -- zie de regel 1.
    "waterlichaam": "NL91ZM",
    "is_bovenstrooms": lambda waterlichaam, meetpunt_waterlichaam: True,
    "overschrijdingen": [
        {"meetpunt": "NL91_TESTPUNT", "waterlichaam": "NL91BM", "stof": "Zn",
         "gemeten": 10.0, "norm": 7.8, "eenheid": "ug/l"},
        {"meetpunt": "NL91_TESTPUNT2", "waterlichaam": "NL91BM", "stof": "PFOA",
         "gemeten": 5.0, "norm": 3.0, "eenheid": "ug/l"},
    ],
    "register_codes": {"Zn", "ZS"},
}


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


# -- Eindreview, bevinding 2: eenheid moet meetellen, en pH is geen discrepantie ------------------

def test_een_concentratiegrens_en_een_vrachtgrens_voor_dezelfde_stof_geven_geen_signaal():
    """Live gaf dit 53 van de 164 toen getelde gevallen: een concentratiegrens (mg/l) en een
    vrachtgrens (kg/jaar) voor dezelfde stof zijn twee elkaar aanvullende voorwaarden, geen
    tegenstrijdigheid. De bewering "een factor 35704419,9× verschil" (CORUSNB, Warmte) kwam
    letterlijk uit het verschil tussen MJ/dag en MJ/seconde -- precies de eenhedenfout die
    `kmg.toerekening` elders in dit lab expliciet vermijdt."""
    v = {"voorschriften": [
        {"parameter": "Warmte", "waarde": 220000, "eenheid": "megajoule per dag"},
        {"parameter": "Warmte", "waarde": 2.508, "eenheid": "megajoule per seconde"},
    ]}
    assert signalen.regel_meerdere_grenswaarden(v, {}) == []


def test_twee_grenswaarden_in_dezelfde_eenheid_vuren_nog_steeds():
    """De positieve controle: twee écht verschillende grenswaarden in dezelfde eenheid voor
    dezelfde stof blijven een signaal -- de fix groepeert fijner, zij onderdrukt niet."""
    v = {"voorschriften": [
        {"parameter": "Warmte", "waarde": 1.0, "eenheid": "megajoule per seconde"},
        {"parameter": "Warmte", "waarde": 4.0, "eenheid": "megajoule per seconde"},
    ]}
    uit = signalen.regel_meerdere_grenswaarden(v, {})
    assert len(uit) == 1
    assert uit[0]["zwaarte"] == "hoog"


def test_zuurgraad_geeft_nooit_een_signaal_ook_niet_bij_een_groot_venster():
    """pH wordt altijd als venster vergund (bv. 6,5-9,0) -- dat is de normale, correcte vorm, geen
    'welke grenswaarde geldt?'-vraag, en een verhouding tussen twee pH-waarden is sowieso
    betekenisloos (logaritmisch). Live was dit 36 van de 164 toen getelde gevallen, puur dit
    patroon. Case-ongevoelig: de bron schrijft zowel 'Zuurgraad' als 'zuurgraad'."""
    v = {"voorschriften": [
        {"parameter": "Zuurgraad", "waarde": 6.5, "eenheid": "dimensieloos"},
        {"parameter": "Zuurgraad", "waarde": 9.0, "eenheid": "dimensieloos"},
    ]}
    assert signalen.regel_meerdere_grenswaarden(v, {}) == []
    v2 = {"voorschriften": [
        {"parameter": "zuurgraad", "waarde": 6.0, "eenheid": "dimensieloos"},
        {"parameter": "zuurgraad", "waarde": 12.0, "eenheid": "dimensieloos"},
    ]}
    assert signalen.regel_meerdere_grenswaarden(v2, {}) == []


def test_een_andere_dimensieloze_parameter_dan_zuurgraad_vuurt_nog_wel():
    """De uitsluiting is op naam, niet op eenheid: 'dimensieloos' draagt in het register ook
    'Vervuilingswaarde', een gewone telling waarvoor een venster geen correcte lezing is."""
    v = {"voorschriften": [
        {"parameter": "Vervuilingswaarde", "waarde": 10.0, "eenheid": "dimensieloos"},
        {"parameter": "Vervuilingswaarde", "waarde": 40.0, "eenheid": "dimensieloos"},
    ]}
    assert len(signalen.regel_meerdere_grenswaarden(v, {})) == 1


def test_een_grenswaarde_van_nul_geeft_geen_zerodivisionerror():
    """Eén grenswaarde 0 naast een andere, grotere grenswaarde zou `max/min` laten stuklopen.
    Vandaag komt dat in het register niet voor, maar een regel op een live eindpunt mag daar niet
    op vertrouwen (zie de docstring bij deze functie)."""
    v = {"voorschriften": [
        {"parameter": "Zink", "waarde": 0.0, "eenheid": "milligram per liter"},
        {"parameter": "Zink", "waarde": 2.0, "eenheid": "milligram per liter"},
    ]}
    uit = signalen.regel_meerdere_grenswaarden(v, {})
    assert len(uit) == 1
    assert uit[0]["omvang"] == float("inf")
    assert uit[0]["zwaarte"] == "hoog"


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


@pytest.mark.parametrize("eenheid", sorted(signalen.DEBIET_EENHEDEN))
def test_elke_bekende_debietspelling_voorkomt_het_signaal(eenheid):
    """Elke spelling uit `kmg/lozingsmodel.py` en `gebruiksruimte/atlas_register.py` moet hier
    als debiet herkend worden, anders ontstaat een vals-positieve "vracht niet te bepalen" op
    een vestiging die wél een debietvoorschrift heeft -- alleen in een andere spelling."""
    v = {"voorschriften": [
        {"parameter": "Zink", "waarde": 0.5, "eenheid": "milligram per liter"},
        {"parameter": "Debiet", "waarde": 100.0, "eenheid": eenheid}]}
    assert signalen.regel_vracht_onbepaald(v, {}) == []


def test_een_onbekende_kubieke_meter_eenheid_telt_niet_als_debiet():
    """Niet elke eenheid van de vorm "kubieke meter per ..." is een doorlopend debiet --
    `atlas_register.py` noemt "kubieke meter per schoonmaakactie" expliciet als tegenvoorbeeld.
    Zo'n onbekende spelling mag het signaal dus niet onderdrukken."""
    v = {"voorschriften": [
        {"parameter": "Zink", "waarde": 0.5, "eenheid": "milligram per liter"},
        {"parameter": "Spoeling", "waarde": 2.0, "eenheid": "kubieke meter per schoonmaakactie"}]}
    uit = signalen.regel_vracht_onbepaald(v, {})
    assert len(uit) == 1
    assert {b["parameter"] for b in uit[0]["bewijs"]} == {"Zink"}


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


def test_niet_regime_zuiver_blijft_laag_bij_veel_voorschriften():
    """De omvang die getoond wordt mag de echte, grote telling zijn -- de zwaarte moet daar niet
    door kunnen kantelen naar "hoog" of "midden"."""
    v = {"voorschriften": [{"parameter": f"Stof {i}", "waarde": 1.0,
                             "eenheid": "milligram per liter", "bemonstering": "Steekmonster"}
                            for i in range(150)]}
    s = signalen.regel_niet_regime_zuiver(v, {})[0]
    assert s["omvang"] == 150
    assert s["zwaarte"] == "laag"


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


def test_geen_geldigheidsduur_blijft_laag_bij_veel_voorschriften():
    v = {"voorschriften": [{"parameter": f"Stof {i}", "waarde": 1.0,
                             "eenheid": "milligram per liter"} for i in range(150)]}
    s = signalen.regel_geen_geldigheidsduur(v, {})[0]
    assert s["omvang"] == 150
    assert s["zwaarte"] == "laag"


def test_zwaarte_werpt_keyerror_op_een_onbekende_regel():
    with pytest.raises(KeyError):
        signalen.zwaarte("deze_regel_bestaat_niet", 5)


# Eén test per uitkomst van `zwaarte()` zelf (plan, Global Constraints), los van welke regel
# toevallig op die uitkomst uitkomt. "vergunning_niet_te_vinden" heeft drempel 3; elke rule met
# een echte (niet-sentinel) drempel zou hier even goed dienen.

def test_zwaarte_op_of_boven_de_drempel_is_hoog():
    assert signalen.zwaarte("vergunning_niet_te_vinden", 3) == "hoog"


def test_zwaarte_onder_de_drempel_maar_niet_nul_is_midden():
    assert signalen.zwaarte("vergunning_niet_te_vinden", 1) == "midden"


def test_zwaarte_op_nul_is_laag():
    assert signalen.zwaarte("vergunning_niet_te_vinden", 0) == "laag"


def test_zwaarte_van_een_altijd_laag_regel_blijft_laag_bij_een_grote_omvang():
    """De drempel-99-sentinel moet dit afdwingen zonder dat een aanroeper een nep-omvang nodig
    heeft: ook een werkelijk grote telling mag deze twee regels niet naar "hoog" of "midden"
    tillen."""
    assert signalen.zwaarte("niet_regime_zuiver", 1000) == "laag"
    assert signalen.zwaarte("geen_geldigheidsduur", 1000) == "laag"


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


# -- Taak 2: de drie regels die meetdata en stroomrichting nodig hebben ----------------------

def test_vergunde_stof_die_nergens_gemeten_wordt_geeft_een_signaal():
    v = {"voorschriften": [{"parameter": "Zuurgraad", "waarde": 7.0, "eenheid": "dimensieloos",
                            "aquo": "pH"},
                           {"parameter": "Zink", "waarde": 0.5, "eenheid": "milligram per liter",
                            "aquo": "Zn"}]}
    uit = signalen.regel_geen_onafhankelijke_meting(v, {"gemeten_codes": {"Zn", "Ntot"}})
    assert [s["bewijs"][0]["aquo"] for s in uit] == ["pH"]
    assert "geen onafhankelijke meting" in uit[0]["signaal"]


def test_geen_onafhankelijke_meting_geeft_een_apart_signaal_per_code():
    """Eén signaal per aquo-code, niet één voor de hele vestiging -- §6 maakt de zwaarte
    afhankelijk van de stof, en pH en Q kunnen een verschillende norm-status hebben. `omvang` is
    per signaal het aantal voorschriften zonder meting op die ene code."""
    v = {"voorschriften": [
        {"parameter": "Zuurgraad", "waarde": 7.0, "eenheid": "dimensieloos", "aquo": "pH"},
        {"parameter": "Debiet", "waarde": 10.0, "eenheid": "kubieke meter per uur", "aquo": "Q"},
        {"parameter": "Zink", "waarde": 0.5, "eenheid": "milligram per liter", "aquo": "Zn"}]}
    uit = signalen.regel_geen_onafhankelijke_meting(v, {"gemeten_codes": {"Zn"}})
    assert {s["bewijs"][0]["aquo"] for s in uit} == {"pH", "Q"}
    assert all(s["omvang"] == 1 for s in uit)


def test_geen_onafhankelijke_meting_groepeert_meerdere_voorschriften_op_dezelfde_code():
    """Twee voorschriften op dezelfde ongemeten code horen in één signaal, met `omvang` 2."""
    v = {"voorschriften": [
        {"parameter": "Zink", "waarde": 0.5, "eenheid": "milligram per liter", "aquo": "Zn"},
        {"parameter": "Zink", "waarde": 2.0, "eenheid": "milligram per liter", "aquo": "Zn"}]}
    uit = signalen.regel_geen_onafhankelijke_meting(v, {"gemeten_codes": set()})
    assert len(uit) == 1
    assert uit[0]["omvang"] == 2
    assert len(uit[0]["bewijs"]) == 2


def test_geen_onafhankelijke_meting_telt_een_ontbrekende_code_niet_mee():
    """Een voorschrift zonder (of met een mislukte) aquo-koppeling is een zaak van
    `niet_in_referentie`, niet van deze regel -- zonder code is er niets om tegen de meetset te
    vergelijken."""
    v = {"voorschriften": [{"parameter": "Onbekend", "waarde": 1.0,
                             "eenheid": "milligram per liter", "aquo": None}]}
    assert signalen.regel_geen_onafhankelijke_meting(v, {"gemeten_codes": set()}) == []


def test_alle_vergunde_stoffen_gemeten_geeft_geen_signaal():
    v = {"voorschriften": [{"parameter": "Zink", "waarde": 0.5, "eenheid": "milligram per liter",
                             "aquo": "Zn"}]}
    assert signalen.regel_geen_onafhankelijke_meting(v, {"gemeten_codes": {"Zn"}}) == []


def test_geen_onafhankelijke_meting_zwijgt_zonder_een_meetset_in_de_context():
    """`context` zonder `gemeten_codes` is "geen meetset aangeleverd", niet "niets wordt
    gemeten" -- anders zou `signalen(v, {})` (zoals taak 1 al test) voor elke stof met een
    aquo-code dit signaal laten afgaan."""
    v = {"voorschriften": [{"parameter": "Zink", "waarde": 0.5, "eenheid": "milligram per liter",
                             "aquo": "Zn"}]}
    assert signalen.regel_geen_onafhankelijke_meting(v, {}) == []


def test_geen_onafhankelijke_meting_is_hoog_voor_een_stof_met_een_norm():
    """Fix-ronde 1, bevinding 1 (Important): zonder `stoffen_met_norm` op de aanroep kon dit
    signaal nooit `hoog` worden, ook al bestaat er voor zink een echte KRW-norm -- de
    `NORM_BEPAALT_ZWAARTE`-plumbing uit de zwaarte-reparatie was dan onbereikbaar vanaf de enige
    aanroeplocatie die er is. Dit test het nu door de regel zelf, niet alleen via `zwaarte()`."""
    v = {"voorschriften": [{"parameter": "Zink", "waarde": 0.5, "eenheid": "milligram per liter",
                             "aquo": "Zn"}]}
    uit = signalen.regel_geen_onafhankelijke_meting(
        v, {"gemeten_codes": set(), "stoffen_met_norm": {"Zn"}})
    assert len(uit) == 1
    assert uit[0]["zwaarte"] == "hoog"


def test_geen_onafhankelijke_meting_is_midden_voor_een_stof_zonder_norm():
    """Zelfde voorschrift, nu zonder dat `Zn` in `stoffen_met_norm` staat: het signaal gaat nog
    steeds af, maar blijft op `midden` -- er is dan niets om de grenswaarde tegen te houden."""
    v = {"voorschriften": [{"parameter": "Zink", "waarde": 0.5, "eenheid": "milligram per liter",
                             "aquo": "Zn"}]}
    uit = signalen.regel_geen_onafhankelijke_meting(
        v, {"gemeten_codes": set(), "stoffen_met_norm": {"Ntot"}})
    assert len(uit) == 1
    assert uit[0]["zwaarte"] == "midden"


def test_geen_onafhankelijke_meting_valt_terug_op_midden_zonder_stoffen_met_norm():
    """Ontbreekt `stoffen_met_norm` zelf (de sleutel staat niet in `context`), dan mag het
    signaal niet verdwijnen -- "we weten niet of er een norm is" is geen reden om te zwijgen,
    alleen een reden om niet naar `hoog` te escaleren. Dit is bewust anders dan `gemeten_codes`
    en `register_codes`, waar een ontbrekende sleutel de hele regel laat zwijgen."""
    v = {"voorschriften": [{"parameter": "Zink", "waarde": 0.5, "eenheid": "milligram per liter",
                             "aquo": "Zn"}]}
    uit = signalen.regel_geen_onafhankelijke_meting(v, {"gemeten_codes": set()})
    assert len(uit) == 1
    assert uit[0]["zwaarte"] == "midden"


def test_norm_overschreden_bovenstrooms_signaleert_bij_een_overschrijding_benedenstrooms():
    context = {
        "waterlichaam": "NL91ZM",
        "is_bovenstrooms": lambda waterlichaam, meetpunt_waterlichaam: True,
        "overschrijdingen": [{"meetpunt": "P1", "waterlichaam": "NL91BM", "stof": "Zn",
                               "gemeten": 10.0, "norm": 7.8, "eenheid": "ug/l"}],
    }
    uit = signalen.regel_norm_overschreden_bovenstrooms({}, context)
    assert len(uit) == 1
    assert uit[0]["zwaarte"] == "hoog"
    assert uit[0]["bewijs"][0]["stof"] == "Zn"


def test_norm_overschreden_bovenstrooms_zwijgt_als_vestiging_benedenstrooms_ligt():
    context = {
        "waterlichaam": "NL91ZM",
        "is_bovenstrooms": lambda waterlichaam, meetpunt_waterlichaam: False,
        "overschrijdingen": [{"meetpunt": "P1", "waterlichaam": "NL91BM", "stof": "Zn"}],
    }
    assert signalen.regel_norm_overschreden_bovenstrooms({}, context) == []


def test_norm_overschreden_bovenstrooms_zwijgt_zonder_waterlichaam_van_de_vestiging():
    """Zonder het waterlichaam van deze vestiging is de richting niet te bepalen -- dan liever
    zwijgen dan gokken."""
    context = {"overschrijdingen": [{"meetpunt": "P1", "waterlichaam": "NL91BM", "stof": "Zn"}]}
    assert signalen.regel_norm_overschreden_bovenstrooms({}, context) == []


def test_norm_overschreden_bovenstrooms_valt_terug_op_kmg_toerekening():
    """Zonder geïnjecteerde `is_bovenstrooms` gebruikt de regel de echte stroomvolgorde uit
    `kmg.toerekening` -- geen netwerk, wel de echte logica (Bovenmaas ligt bovenstrooms van de
    Zandmaas in `STROOMVOLGORDE`)."""
    context = {"waterlichaam": "NL91BOM",
               "overschrijdingen": [{"meetpunt": "P1", "waterlichaam": "NL91ZM", "stof": "Zn"}]}
    assert len(signalen.regel_norm_overschreden_bovenstrooms({}, context)) == 1


def test_norm_overschreden_bovenstrooms_telt_dezelfde_stof_op_twee_meetpunten_als_een():
    """Fix-ronde 1, bevinding 2 (Minor): `omvang` is "aantal overschreden stoffen" (`DREMPELS`),
    geen aantal overschrijdingsrijen -- Zn op twee meetpunten benedenstrooms moet `omvang == 1`
    geven, met beide rijen toch in `bewijs`."""
    context = {
        "waterlichaam": "NL91ZM",
        "is_bovenstrooms": lambda a, b: True,
        "overschrijdingen": [
            {"meetpunt": "P1", "waterlichaam": "NL91BM", "stof": "Zn",
             "gemeten": 10.0, "norm": 7.8, "eenheid": "ug/l"},
            {"meetpunt": "P2", "waterlichaam": "NL91BM", "stof": "Zn",
             "gemeten": 9.0, "norm": 7.8, "eenheid": "ug/l"},
        ],
    }
    uit = signalen.regel_norm_overschreden_bovenstrooms({}, context)
    assert len(uit) == 1
    assert uit[0]["omvang"] == 1
    assert len(uit[0]["bewijs"]) == 2


def test_stof_buiten_register_signaleert_een_stof_die_in_geen_voorschrift_voorkomt():
    context = {"register_codes": {"Zn"},
               "overschrijdingen": [{"meetpunt": "P1", "waterlichaam": "NL91BM", "stof": "PFOA",
                                      "gemeten": 5.0, "norm": 3.0, "eenheid": "ug/l"}]}
    uit = signalen.regel_stof_buiten_register({}, context)
    assert len(uit) == 1
    assert uit[0]["bewijs"][0]["stof"] == "PFOA"
    assert uit[0]["zwaarte"] == "hoog"


def test_stof_buiten_register_zwijgt_als_de_stof_wel_een_voorschrift_heeft():
    context = {"register_codes": {"PFOA"},
               "overschrijdingen": [{"meetpunt": "P1", "waterlichaam": "NL91BM", "stof": "PFOA"}]}
    assert signalen.regel_stof_buiten_register({}, context) == []


def test_stof_buiten_register_zwijgt_zonder_een_register_in_de_context():
    """Zelfde reden als bij `gemeten_codes`: "geen register aangeleverd" is iets anders dan "het
    register is leeg", en mag dus niet elke overschrijding als "buiten register" markeren."""
    context = {"overschrijdingen": [{"meetpunt": "P1", "waterlichaam": "NL91BM", "stof": "PFOA"}]}
    assert signalen.regel_stof_buiten_register({}, context) == []


def test_stof_buiten_register_is_een_bevinding_over_het_register_niet_over_de_vestiging():
    """Zelfde patroon als `geen_geldigheidsduur`: precies één signaal per dossier, en dezelfde
    bevinding voor elke vestiging -- het gaat over het register als geheel."""
    context = {"register_codes": set(),
               "overschrijdingen": [{"meetpunt": "P1", "waterlichaam": "NL91BM", "stof": "PFOA"}]}
    a = signalen.regel_stof_buiten_register({"voorschriften": []}, context)
    b = signalen.regel_stof_buiten_register({"voorschriften": [{"parameter": "X"}]}, context)
    assert a == b
    assert len(a) == 1


def test_stof_buiten_register_telt_dezelfde_stof_op_twee_meetpunten_als_een():
    """Fix-ronde 1, bevinding 2 (Minor): zelfde reden als bij `norm_overschreden_bovenstrooms` --
    `omvang` is "aantal gemeten stoffen zonder enig voorschrift" (`DREMPELS`), geen aantal rijen."""
    context = {"register_codes": set(),
               "overschrijdingen": [
                   {"meetpunt": "P1", "waterlichaam": "NL91BM", "stof": "PFOA"},
                   {"meetpunt": "P2", "waterlichaam": "NL91BM", "stof": "PFOA"},
               ]}
    uit = signalen.regel_stof_buiten_register({}, context)
    assert len(uit) == 1
    assert uit[0]["omvang"] == 1
    assert len(uit[0]["bewijs"]) == 2


def test_de_fixture_met_alles_laat_alle_tien_regels_vuren():
    """Voorwaarde voor de taalregel-test hieronder: zonder dit zou die test een subset van de
    regels kunnen dekken zonder dat iemand het merkt."""
    regel_ids = {s["regel"] for s in signalen.signalen(VESTIGING_MET_ALLES, CONTEXT_MET_ALLES)}
    assert regel_ids == set(signalen.DREMPELS)


# -- Wasstraat/toezicht-splitsing: `Regel.laag` ------------------------------------------------

def test_elke_regel_heeft_precies_een_laag():
    """`laag` is afgeleid (`_WERKELIJKHEID_REGELS`), dus kan nooit iets anders zijn dan deze
    twee waarden -- deze test legt dat vast als invariant, niet als toeval van vandaag."""
    for regel in signalen.REGELS:
        assert regel.laag in ("papier", "werkelijkheid"), regel.id


def test_de_twee_lagen_dekken_samen_de_tien_regels():
    """De splitsing uit het plan (2026-11-14-wasstraat-en-toezicht-splitsen.md, §"De splitsing,
    gemeten en niet bedacht"): 7 regels papier, 3 regels werkelijkheid, geen overlap en samen
    precies de tien regels uit `DREMPELS`."""
    papier = {r.id for r in signalen.REGELS if r.laag == "papier"}
    werkelijkheid = {r.id for r in signalen.REGELS if r.laag == "werkelijkheid"}
    assert papier & werkelijkheid == set()
    assert papier | werkelijkheid == set(signalen.DREMPELS)
    assert werkelijkheid == {"geen_onafhankelijke_meting", "norm_overschreden_bovenstrooms",
                              "stof_buiten_register"}
    assert len(papier) == 7 and len(werkelijkheid) == 3


def test_een_signaal_is_nooit_een_vaststelling():
    """Dezelfde taalregel als /kmg, hier op de gegenereerde signaaltekst."""
    for s in signalen.signalen(VESTIGING_MET_ALLES, CONTEXT_MET_ALLES):
        tekst = (s["signaal"] + s.get("waarom", "") + s.get("wat_te_doen", "")).lower()
        for verboden in ("overtreding", "veroorzaakt door", "in strijd met"):
            assert verboden not in tekst, f"{s['signaal']}: {verboden}"


# -- Taak 2, ruling R10: `zwaarte()` repareren zodat `norm_aanwezig` effect heeft -------------

def test_geen_onafhankelijke_meting_is_hoog_met_norm_midden_zonder():
    """§6: signaal 1 weegt hoog bij een stof met een KRW-norm, anders midden -- vóór de reparatie
    was die tweede uitkomst onbereikbaar."""
    assert signalen.zwaarte("geen_onafhankelijke_meting", 1, norm_aanwezig=True) == "hoog"
    assert signalen.zwaarte("geen_onafhankelijke_meting", 1, norm_aanwezig=False) == "midden"


def test_norm_aanwezig_raakt_alleen_regels_in_norm_bepaalt_zwaarte():
    """Een regel buiten `NORM_BEPAALT_ZWAARTE` blijft `hoog` zodra de drempel gehaald is, met of
    zonder norm -- `vervallen_code` staat niet in die set."""
    assert signalen.zwaarte("vervallen_code", 1, norm_aanwezig=False) == "hoog"
    assert signalen.zwaarte("vervallen_code", 1, norm_aanwezig=True) == "hoog"
