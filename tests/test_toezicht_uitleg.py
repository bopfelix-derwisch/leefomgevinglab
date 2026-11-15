"""`toezicht.uitleg` en `toezicht.terugkoppeling` (taak 7).

Geen netwerk, geen echte LLM: de retrieval (`_zoek`) en het taalmodel (`llm`) zijn overal
geïnjecteerd, zoals de brief voorschrijft (`_zoek=lambda q, n: []`). Een live Stelselcatalogus-
of embedding-aanroep staat hier niet; die horen in een `*_live.py`-bestand (zie `test_toezicht_
live.py` voor het patroon), en dit lab heeft dat vandaag niet nodig: `uitleg.zoek_bronnen` leest
alleen al-geladen referenties, geen bestand en geen netwerk zelf.
"""
import pytest

from leefomgevinglab.usecases.toezicht import aquo, signalen, terugkoppeling, uitleg

_VERBODEN = ("overtreding", "veroorzaakt door", "in strijd met")


# == uitleg.waarom ================================================================================

# -- Stap 1 (brief, verbatim): de uitlegger zwijgt zonder treffer -------------------------------

def test_zonder_bron_zegt_de_uitlegger_dat_hij_het_niet_weet():
    uit = uitleg.waarom("onbekend signaal", _zoek=lambda q, n: [])
    assert uit["beschikbaar"] is False
    assert uit["vindplaatsen"] == []
    assert "geen" in uit["reden"].lower()


# -- Stap 2: elke uitleg draagt minstens één benoemde vindplaats --------------------------------

def test_met_een_treffer_draagt_de_uitleg_de_vindplaats_van_die_treffer():
    def _zoek(vraag, n):
        return [{"tekst": "'Zink' heeft een KRW-norm van 7,80 µg/l.",
                 "vindplaats": "KRW-toetsresultaten, parameter Zn"}]

    uit = uitleg.waarom("Zink", _zoek=_zoek)
    assert uit["beschikbaar"] is True
    assert uit["vindplaatsen"] == ["KRW-toetsresultaten, parameter Zn"]
    assert "KRW-toetsresultaten" in uit["tekst"] or "Zink" in uit["tekst"]


def test_een_treffer_zonder_vindplaats_telt_niet_mee():
    """De harde regel, letterlijk: een treffer die geen bron noemt mag een uitleg niet
    schragen -- ook niet als hij verder prima tekst draagt."""
    def _zoek(vraag, n):
        return [{"tekst": "Dit zou een uitleg kunnen zijn.", "vindplaats": None}]

    uit = uitleg.waarom("iets", _zoek=_zoek)
    assert uit["beschikbaar"] is False
    assert uit["vindplaatsen"] == []


def test_meerdere_treffers_leveren_meerdere_vindplaatsen_op():
    def _zoek(vraag, n):
        return [
            {"tekst": "Feit A.", "vindplaats": "Bron A"},
            {"tekst": "Feit B.", "vindplaats": "Bron B"},
        ]

    uit = uitleg.waarom("iets", _zoek=_zoek)
    assert uit["beschikbaar"] is True
    assert uit["vindplaatsen"] == ["Bron A", "Bron B"]
    assert "Feit A" in uit["tekst"] and "Feit B" in uit["tekst"]


# -- De harde taalregel, ook op de uitleg zelf ---------------------------------------------------

def test_een_treffer_met_verboden_taal_wordt_genegeerd_niet_opgeschoond():
    def _zoek(vraag, n):
        return [{"tekst": "Dit is een overtreding van de norm.", "vindplaats": "Bron X"}]

    uit = uitleg.waarom("iets", _zoek=_zoek)
    assert uit["beschikbaar"] is False, \
        "een treffer met verboden taal mag een uitleg niet schragen, ook niet gedeeltelijk"


def test_een_goede_en_een_verboden_treffer_laten_alleen_de_goede_door():
    def _zoek(vraag, n):
        return [
            {"tekst": "Dit is in strijd met de norm.", "vindplaats": "Bron X"},
            {"tekst": "Dit is een neutraal feit.", "vindplaats": "Bron Y"},
        ]

    uit = uitleg.waarom("iets", _zoek=_zoek)
    assert uit["beschikbaar"] is True
    assert uit["vindplaatsen"] == ["Bron Y"]
    tekst_laag = uit["tekst"].lower()
    for verboden in _VERBODEN:
        assert verboden not in tekst_laag


def test_zonder_injectie_valt_waarom_terug_op_zoek_bronnen_en_dus_op_niets():
    """Zonder `_zoek` en zonder geladen referenties doet `waarom()` geen netwerk en geen
    bestandslezing -- `zoek_bronnen()` zonder bronnen geeft gewoon niets terug."""
    uit = uitleg.waarom("Zink")
    assert uit["beschikbaar"] is False


# == uitleg.zoek_bronnen: de drie bronnen apart ===================================================

def test_zoek_bronnen_vindt_een_geldige_aquo_naam():
    aquo_ref = {"geldig": {"zink": "Zn"}, "vervallen": {}, "vervangen_door": {}}
    treffers = uitleg.zoek_bronnen("Wat betekent Zink hier?", 3, aquo_ref=aquo_ref)
    assert len(treffers) == 1
    assert "Geldig" in treffers[0]["vindplaats"]
    assert "Zn" in treffers[0]["vindplaats"]


def test_zoek_bronnen_houdt_de_ij_digraaf_intact():
    """Fix-ronde 2 (publieke review op `/toezicht`, 2026-11-14): `aquo.laad()` geeft elke naam
    als dict-sleutel volledig kleine letters, dus "ijzer" komt hier binnen zonder hoofdletter.
    `str.capitalize()` gaf daarop "Ijzer" -- de Nederlandse ij-digraaf wordt bij een hoofdletter
    "IJ", geen enkele losse letter. Gerepareerd via `woordvorm.hoofdletter_bij_zinsbegin`."""
    aquo_ref = {"geldig": {"ijzer": "Fe"}, "vervallen": {}, "vervangen_door": {}}
    treffers = uitleg.zoek_bronnen("Wat betekent ijzer hier?", 3, aquo_ref=aquo_ref)
    assert len(treffers) == 1
    assert "'IJzer'" in treffers[0]["tekst"]
    assert "'Ijzer'" not in treffers[0]["tekst"]


def test_zoek_bronnen_vindt_een_ingetrokken_aquo_naam_met_vervanger():
    aquo_ref = {"geldig": {}, "vervallen": {"zwevende stof": "ZS"},
                "vervangen_door": {"zwevende stof": "ZSNIEUW"}}
    treffers = uitleg.zoek_bronnen("Zwevende stof staat als signaal", 3, aquo_ref=aquo_ref)
    assert len(treffers) == 1
    assert "Vervallen" in treffers[0]["vindplaats"]
    assert "ZSNIEUW" in treffers[0]["tekst"]


def test_zoek_bronnen_meldt_expliciet_als_er_geen_vervanger_is():
    """'Zwevende stof' is het echte geval (CLAUDE.md): beide Aquo-rijen zijn `Vervallen` en geen
    draagt een opvolger."""
    aquo_ref = {"geldig": {}, "vervallen": {"zwevende stof": "ZS"}, "vervangen_door": {}}
    treffers = uitleg.zoek_bronnen("Zwevende stof", 3, aquo_ref=aquo_ref)
    assert "geen vervangende code" in treffers[0]["tekst"].lower()


def test_zoek_bronnen_matcht_niet_op_een_losse_substring():
    """Woordgrensmatching: 'Zn' mag niet toevallig binnen een ander woord vuren."""
    aquo_ref = {"geldig": {"zn": "Zn"}, "vervallen": {}, "vervangen_door": {}}
    treffers = uitleg.zoek_bronnen("dit gaat over bronzen kleppen", 3, aquo_ref=aquo_ref)
    assert treffers == []


def test_zoek_bronnen_vindt_een_krw_norm_via_de_aquo_naam():
    aquo_ref = {"geldig": {"zink": "Zn"}, "vervallen": {}, "vervangen_door": {}}
    normenset = {"normen": {"NL91_PUNT": [
        {"meetpunt": "NL91_PUNT", "parameter": "Zn", "hoedanigheid": "NVT",
         "grondslag": "jaargemiddelde", "norm": 7.8, "eenheid": "ug/l"},
    ]}}
    treffers = uitleg.zoek_bronnen("Zink zit hierin", 3, aquo_ref=aquo_ref, normenset=normenset)
    assert any("7.8" in t["tekst"] for t in treffers)
    assert any("krw_normen.json" in t["vindplaats"] for t in treffers)


def test_zoek_bronnen_dedupliceert_dezelfde_norm_over_meetpunten():
    aquo_ref = {"geldig": {"zink": "Zn"}, "vervallen": {}, "vervangen_door": {}}
    normenset = {"normen": {
        "NL91_A": [{"meetpunt": "NL91_A", "parameter": "Zn", "hoedanigheid": "NVT",
                    "grondslag": "jaargemiddelde", "norm": 7.8, "eenheid": "ug/l"}],
        "NL91_B": [{"meetpunt": "NL91_B", "parameter": "Zn", "hoedanigheid": "NVT",
                    "grondslag": "jaargemiddelde", "norm": 7.8, "eenheid": "ug/l"}],
    }}
    treffers = uitleg.zoek_bronnen("Zink", 5, aquo_ref=aquo_ref, normenset=normenset)
    krw = [t for t in treffers if "krw_normen" in t["vindplaats"]]
    assert len(krw) == 1, "zelfde (code, hoedanigheid, grondslag) telt maar één keer"


def test_zoek_bronnen_gebruikt_de_catalogus_alleen_als_die_is_meegegeven():
    class _Catalogus:
        def zoek(self, vraag):
            return [{"term": "Zeer zorgwekkende stof",
                     "definitie": "Een stof met ernstige, onomkeerbare effecten.",
                     "vindplaats": "art. 5.22a Bal"}]

    treffers = uitleg.zoek_bronnen("zeer zorgwekkende stof", 3, catalogus=_Catalogus())
    assert len(treffers) == 1
    assert "Zeer zorgwekkende stof" in treffers[0]["tekst"]
    assert "art. 5.22a Bal" in treffers[0]["vindplaats"]


def test_zoek_bronnen_zonder_catalogus_doet_geen_netwerk():
    """Geen connector meegegeven -- geen aanroep, geen treffer, geen fout."""
    assert uitleg.zoek_bronnen("iets", 3) == []


def test_een_falende_catalogus_laat_de_andere_bronnen_in_stand():
    class _KapotteCatalogus:
        def zoek(self, vraag):
            raise RuntimeError("netwerk weg")

    aquo_ref = {"geldig": {"zink": "Zn"}, "vervallen": {}, "vervangen_door": {}}
    treffers = uitleg.zoek_bronnen("Zink", 3, aquo_ref=aquo_ref, catalogus=_KapotteCatalogus())
    assert len(treffers) == 1
    assert "Aquo" in treffers[0]["vindplaats"]


def test_een_kale_code_die_ook_een_gewoon_woord_is_matcht_niet_op_dat_woord():
    """Eindreview, bevinding 4: 'Te' (tellurium) is ook het Nederlandse woord 'te', en zonder
    naam-resolutie viel de oude matcher terug op een hoofdletter-ongevoelige vergelijking van de
    kale code tegen de vraagtekst. Een realistische normenset (zoals `krw_normen.json` die
    draagt) plus een niet-stof-signaalkop ('vracht niet te bepalen', 'vergunning niet te vinden')
    mag dan geen treffer meer geven -- geen `aquo_ref` hier, want dat is precies het pad waarin
    de code nooit aan een naam koppelt en dus kaal blijft."""
    normenset = {"normen": {"NL80_X": [
        {"meetpunt": "NL80_X", "parameter": "Te", "hoedanigheid": "nf",
         "grondslag": "jaargemiddelde", "norm": 100.0, "eenheid": "ug/l"},
    ]}}
    assert uitleg.zoek_bronnen("vracht niet te bepalen", 3, normenset=normenset) == []
    assert uitleg.zoek_bronnen("vergunning niet te vinden", 3, normenset=normenset) == []


def test_een_kale_code_matcht_nog_altijd_hoofdlettergevoelig_als_los_woord():
    """De positieve controle bij de vorige test: dezelfde kale code matcht nog steeds, als zij
    wél met haar eigen hoofdletter in de vraagtekst staat."""
    normenset = {"normen": {"NL80_X": [
        {"meetpunt": "NL80_X", "parameter": "Te", "hoedanigheid": "nf",
         "grondslag": "jaargemiddelde", "norm": 100.0, "eenheid": "ug/l"},
    ]}}
    treffers = uitleg.zoek_bronnen("Te zit in het voorschrift", 3, normenset=normenset)
    assert len(treffers) == 1
    assert "Te" in treffers[0]["tekst"]


def test_zoek_bronnen_knipt_af_op_n():
    aquo_ref = {"geldig": {"zink": "Zn", "zuurgraad": "pH"}, "vervallen": {}, "vervangen_door": {}}
    treffers = uitleg.zoek_bronnen("zink en zuurgraad in het voorschrift", 1, aquo_ref=aquo_ref)
    assert len(treffers) == 1


# == Fix-ronde 1, bevinding 1: de vierde bron, de /kmg-proclaimer ================================

def test_de_proclaimer_bron_vuurt_op_het_regime_trefwoord():
    """Precies de signaalkop van `niet_regime_zuiver` ('toets niet regime-zuiver') moet de
    hoedanigheid/grootheden-kanttekening opleveren -- de enige van de vier bronnen die geen
    stofnaam nodig heeft."""
    treffers = uitleg.zoek_bronnen("toets niet regime-zuiver", 3)
    assert len(treffers) == 1
    assert "grootheden" in treffers[0]["tekst"]
    assert "usecases/kmg/proclaimer.py" in treffers[0]["vindplaats"]
    assert "/kmg" in treffers[0]["vindplaats"]


def test_de_proclaimer_bron_vuurt_op_het_bovenstrooms_trefwoord():
    treffers = uitleg.zoek_bronnen("meting boven de norm, lozer bovenstrooms", 3)
    assert len(treffers) == 1
    assert "kan bijdragen" in treffers[0]["tekst"]


def test_de_proclaimer_bron_zwijgt_zonder_trefwoord():
    assert uitleg.zoek_bronnen("vracht niet te bepalen", 3) == []


def test_de_proclaimer_bron_heeft_geen_injectie_nodig_en_doet_geen_netwerk():
    """`zoek_bronnen()` zonder enig argument behalve de vraag -- de proclaimer is intrinsiek,
    anders dan de drie andere bronnen (zie `test_zonder_injectie_valt_waarom_terug_...`)."""
    uit = uitleg.waarom("toets niet regime-zuiver")
    assert uit["beschikbaar"] is True
    assert "usecases/kmg/proclaimer.py" in uit["vindplaatsen"][0]


def test_proclaimer_notities_vinden_vandaag_hun_fragment_in_de_echte_tekst():
    """Drift-wacht: beide kanttekeningen citeren een letterlijk fragment uit de live
    `proclaimer.bouw()`-tekst, geen parafrase. Verdwijnt dat fragment ooit uit `/kmg` (een
    herformulering daar), dan moet dát hier luid blijken in plaats van dat deze bron stilletjes
    niets meer teruggeeft."""
    kopjes = uitleg._proclaimer_kopjes()
    for notitie in uitleg._PROCLAIMER_NOTITIES:
        zin = uitleg._zin_met_fragment(kopjes, notitie["kop"], notitie["fragment"])
        assert zin is not None, (
            f"fragment '{notitie['fragment']}' niet meer gevonden in kopje '{notitie['kop']}' "
            "van usecases/kmg/proclaimer.py -- de notitie in uitleg.py moet bijgewerkt worden")


def test_de_vier_bronnen_staan_genoemd_in_de_reden_zonder_treffer():
    uit = uitleg.waarom("iets willekeurigs zonder enige trefwoord", _zoek=lambda q, n: [])
    for naam in ("Aquo-domeintabel", "KRW-normen", "Stelselcatalogus", "proclaimer"):
        assert naam in uit["reden"]


# == Fix-ronde 1, bevinding 2: precedentie en een strengere grens voor stofnamen ==================

def test_aquo_treffers_geeft_voorrang_aan_de_geldige_code_bij_een_dubbele_naam():
    """748 namen in de echte bron staan zowel in `geldig` als in `vervallen` (bv. 'minerale
    olie'). Zonder voorrang gaf dit twee treffers die elkaar tegenspreken (geldig + ingetrokken
    over dezelfde naam, in één tekst geplakt) -- nu geldt dezelfde voorrang als `aquo.verrijk()`."""
    aquo_ref = {"geldig": {"minerale olie": "MINOL"}, "vervallen": {"minerale olie": "MINOL_OUD"},
                "vervangen_door": {}}
    treffers = uitleg.zoek_bronnen("minerale olie zit in het voorschrift", 5, aquo_ref=aquo_ref)
    assert len(treffers) == 1
    assert "Geldig" in treffers[0]["vindplaats"]
    assert "MINOL_OUD" not in treffers[0]["vindplaats"]
    assert "ingetrokken" not in treffers[0]["tekst"].lower()


def test_zonder_een_geldige_tegenhanger_blijft_de_ingetrokken_naam_een_treffer():
    """De voorrang mag de ingetrokken naam niet onderdrukken als er geen geldige tegenhanger is
    (het echte 'Zwevende stof'-geval): dan is de ingetrokken code zelf nog steeds het signaal."""
    aquo_ref = {"geldig": {}, "vervallen": {"zwevende stof": "ZS"}, "vervangen_door": {}}
    treffers = uitleg.zoek_bronnen("Zwevende stof", 3, aquo_ref=aquo_ref)
    assert len(treffers) == 1
    assert "Vervallen" in treffers[0]["vindplaats"]


def test_een_dubbele_naam_levert_geen_zelf_tegensprekende_tekst_meer_op():
    """De letterlijke herhaling van de bevinding: vóór de fix plakte `waarom()` een 'geldig' en
    een 'ingetrokken' bewering over dezelfde naam aan elkaar. Na de fix mag die tegenspraak niet
    meer in de uiteindelijke tekst staan."""
    aquo_ref = {"geldig": {"minerale olie": "MINOL"}, "vervallen": {"minerale olie": "MINOL_OUD"},
                "vervangen_door": {}}
    uit = uitleg.waarom("minerale olie", _zoek=lambda q, n: uitleg.zoek_bronnen(q, n, aquo_ref=aquo_ref))
    assert uit["beschikbaar"] is True
    assert "geldige" in uit["tekst"].lower()
    assert "ingetrokken" not in uit["tekst"].lower()


def test_stofnaam_matcht_niet_als_staart_van_een_samengestelde_naam():
    """Fix-ronde 1, bevinding 2 (het meegeleverde voorbeeld): '(1-butyloctyl)-benzeen' bevat
    'benzeen' als woord met een koppelteken ervoor -- de strenge matcher mag dat niet als een
    treffer op de stof 'Benzeen' lezen, want dat citeert feiten over de verkeerde stof."""
    aquo_ref = {"geldig": {"benzeen": "C6H6"}, "vervallen": {}, "vervangen_door": {}}
    treffers = uitleg.zoek_bronnen("(1-butyloctyl)-benzeen is vergund", 3, aquo_ref=aquo_ref)
    assert treffers == []


def test_stofnaam_matcht_nog_altijd_als_los_woord():
    """De positieve controle bij de vorige test: 'benzeen' als eigen woord, niet als staart van
    een samenstelling, moet wél blijven vuren."""
    aquo_ref = {"geldig": {"benzeen": "C6H6"}, "vervallen": {}, "vervangen_door": {}}
    treffers = uitleg.zoek_bronnen("er is benzeen aangetroffen", 3, aquo_ref=aquo_ref)
    assert len(treffers) == 1


def test_stofnaam_matcht_nog_altijd_tussen_haakjes():
    """'(Zn)' is de normale manier waarop een code in de praktijk naast een naam staat -- de
    haakjes mogen de strenge matcher niet blokkeren, alleen een koppelteken/woordteken ertegenaan
    moet dat doen."""
    aquo_ref = {"geldig": {"zn": "Zn"}}
    treffers = uitleg.zoek_bronnen("zink (zn) in het register", 3, aquo_ref=aquo_ref)
    assert len(treffers) == 1


# -- Met de echte Aquo-loader, tegen een kleine tmp-CSV (geen echte 7000-rijige bron) ------------

def test_uitleg_over_een_echt_ingetrokken_signaalvoorschrift(tmp_path):
    """End-to-end met `aquo.laad()` op een kleine, eigen CSV -- dezelfde vorm als
    `test_toezicht_aquo.py`, hier als bron voor de uitlegger."""
    import csv
    pad = tmp_path / "aquo_Parameter.csv"
    kop = ["Id", "Codes", "Omschrijving", "Groep", "CASnummer", "Alternatieve term",
           "Begin geldigheid", "Eind geldigheid", "Status", "Vervangen door", "Gerelateerd",
           "Wijzigingsnummer"]
    with pad.open("w", encoding="utf-8-sig", newline="") as f:
        w = csv.writer(f, delimiter=";")
        w.writerow(kop)
        w.writerow([1, "ZS", "Zwevende stof", "ChemischeStof", "", "", "2011-06-08",
                    "2100-01-01", "Vervallen", "", "", ""])
    ref = aquo.laad(str(pad))

    uit = uitleg.waarom("grenswaarde op een ingetrokken code: Zwevende stof",
                         _zoek=lambda q, n: uitleg.zoek_bronnen(q, n, aquo_ref=ref))
    assert uit["beschikbaar"] is True
    assert "Aquo-domeintabel Parameter" in uit["vindplaatsen"][0]
    assert "Vervallen" in uit["tekst"]


# -- `llm` herformuleert, maar alleen als de uitkomst standhoudt --------------------------------

def test_llm_herformuleert_de_tekst_als_hij_geldig_is():
    def nep_llm(prompt):
        return "Nette formulering op basis van de feiten."

    uit = uitleg.waarom("iets", _zoek=lambda q, n: [{"tekst": "feit", "vindplaats": "Bron"}],
                         llm=nep_llm)
    assert uit["tekst"] == "Nette formulering op basis van de feiten."
    assert uit["vindplaatsen"] == ["Bron"], "vindplaatsen komen altijd uit de treffers, nooit uit het model"


def test_llm_herformulering_met_verboden_taal_valt_terug_op_de_deterministische_tekst():
    def kapotte_llm(prompt):
        return "Dit is een overtreding."

    uit = uitleg.waarom("iets", _zoek=lambda q, n: [{"tekst": "feit", "vindplaats": "Bron"}],
                         llm=kapotte_llm)
    assert uit["tekst"] == "feit"


def test_een_falende_llm_valt_terug_op_de_deterministische_tekst():
    def stuk_llm(prompt):
        raise TimeoutError("geen verbinding")

    uit = uitleg.waarom("iets", _zoek=lambda q, n: [{"tekst": "feit", "vindplaats": "Bron"}],
                         llm=stuk_llm)
    assert uit["beschikbaar"] is True
    assert uit["tekst"] == "feit"


# == terugkoppeling ===============================================================================

# -- Stap 4 (brief): de terugkoppeling schrijft de regelversie mee -------------------------------

def test_registreer_schrijft_de_regelversie_van_de_regel_mee():
    oordeel = terugkoppeling.registreer("Vestiging X", "vervallen_code", "signaal_was_juist")
    assert oordeel["regelversie"] == terugkoppeling.regelversie("vervallen_code")
    assert oordeel["vestiging_id"] == "Vestiging X"
    assert oordeel["regel_id"] == "vervallen_code"
    assert oordeel["oordeel"] == "signaal_was_juist"


def test_regelversie_verandert_als_de_drempel_verandert():
    """De versie moet reageren op een echte, functionele wijziging -- hier gesimuleerd door de
    drempel-tabel te monkeypatchen (de echte wijziging zou een regelbewerking in `signalen.py`
    zijn, maar die mag deze test niet aanpassen)."""
    voor = terugkoppeling.regelversie("vervallen_code")
    oorspronkelijk = signalen.DREMPELS["vervallen_code"]
    try:
        signalen.DREMPELS["vervallen_code"] = (2, "een andere omschrijving")
        na = terugkoppeling.regelversie("vervallen_code")
    finally:
        signalen.DREMPELS["vervallen_code"] = oorspronkelijk
    assert voor != na


def test_regelversie_is_stabiel_voor_twee_aanroepen_zonder_wijziging():
    assert terugkoppeling.regelversie("vervallen_code") == terugkoppeling.regelversie("vervallen_code")


def test_een_onbekende_regel_geeft_een_fout_geen_lege_versie():
    with pytest.raises(terugkoppeling.OnbekendeRegel):
        terugkoppeling.regelversie("regel_die_niet_bestaat")


# -- Fix-ronde 1, bevinding 4: onleesbare brontekst valt luid om, niet stil terug op een zwakkere
# hash ------------------------------------------------------------------------------------------

def test_regelversie_faalt_luid_als_de_brontekst_niet_op_te_halen_is(monkeypatch):
    """Geen kale `OSError` laten ontsnappen, en zeker geen stille terugval op een hash zonder
    brontekst -- dat zou precies de onder-invalidatie reintroduceren die de moduledocstring
    afwijst (twee verschillende regels die een versie delen zodra hun bron onleesbaar is)."""
    def kapotte_getsource(_fn):
        raise OSError("geen brontekst beschikbaar (bevroren deployment)")

    monkeypatch.setattr(terugkoppeling.inspect, "getsource", kapotte_getsource)
    with pytest.raises(terugkoppeling.RegelversieNietTeBepalen):
        terugkoppeling.regelversie("vervallen_code")


def test_registreer_geeft_de_fout_door_in_plaats_van_zwijgend_te_versimpelen(monkeypatch):
    def kapotte_getsource(_fn):
        raise TypeError("geen brontekst voor een dynamisch gebouwde functie")

    monkeypatch.setattr(terugkoppeling.inspect, "getsource", kapotte_getsource)
    with pytest.raises(terugkoppeling.RegelversieNietTeBepalen):
        terugkoppeling.registreer("Vestiging X", "vervallen_code", "signaal_was_juist")


def test_een_onbekend_oordeel_wordt_geweigerd():
    with pytest.raises(terugkoppeling.OnbekendOordeel):
        terugkoppeling.registreer("Vestiging X", "vervallen_code", "waarschijnlijk_wel")


def test_elke_regel_heeft_een_eigen_versie_hash():
    """Geen toeval-botsing over de tien regels -- elke regel moet een eigen hash hebben, anders
    is de versie geen betrouwbare sleutel."""
    versies = {regel.id: terugkoppeling.regelversie(regel.id) for regel in signalen.REGELS}
    assert len(set(versies.values())) == len(versies)


# -- Opslaan en laden (JSONL, append-only) --------------------------------------------------------

def test_opslaan_en_laden_geven_dezelfde_registraties_terug(tmp_path):
    pad = tmp_path / "terugkoppeling.jsonl"
    a = terugkoppeling.registreer("Vestiging X", "vervallen_code", "signaal_was_juist")
    b = terugkoppeling.registreer("Vestiging Y", "stof_buiten_register", "bruikbaar")
    terugkoppeling.opslaan([a], str(pad))
    terugkoppeling.opslaan([b], str(pad))
    assert terugkoppeling.laden(str(pad)) == [a, b]


def test_laden_zonder_bestand_geeft_een_lege_lijst_geen_fout(tmp_path):
    assert terugkoppeling.laden(str(tmp_path / "bestaat_niet.jsonl")) == []


# -- Rangschikking: de lege plek is zichtbaar, niet verborgen ------------------------------------

def test_rangschikking_zonder_enige_beoordeling_toont_alle_regels_als_leeg():
    uit = terugkoppeling.rangschikking([])
    assert len(uit) == len(signalen.REGELS)
    assert all(r["status"] == "geen terugkoppeling" for r in uit)
    assert all(r["aandeel_juist"] is None for r in uit)


def test_rangschikking_telt_juist_en_onjuist_per_regel():
    beoordelingen = [
        terugkoppeling.registreer("V1", "vervallen_code", "signaal_was_juist"),
        terugkoppeling.registreer("V2", "vervallen_code", "signaal_was_juist"),
        terugkoppeling.registreer("V3", "vervallen_code", "signaal_was_onjuist"),
    ]
    uit = terugkoppeling.rangschikking(beoordelingen)
    rij = next(r for r in uit if r["regel_id"] == "vervallen_code")
    assert rij["juist"] == 2
    assert rij["onjuist"] == 1
    assert rij["aandeel_juist"] == pytest.approx(2 / 3)
    assert rij["status"] == "beoordeeld"


def test_rangschikking_zet_de_regel_met_het_hoogste_aandeel_juist_vooraan():
    beoordelingen = [
        terugkoppeling.registreer("V1", "vervallen_code", "signaal_was_onjuist"),
        terugkoppeling.registreer("V2", "stof_buiten_register", "signaal_was_juist"),
    ]
    uit = terugkoppeling.rangschikking(beoordelingen)
    beoordeeld = [r for r in uit if r["status"] == "beoordeeld"]
    assert beoordeeld[0]["regel_id"] == "stof_buiten_register"


def test_regels_zonder_terugkoppeling_staan_achteraan_niet_vooraan():
    """Een regel zonder enig oordeel mag niet toevallig bovenaan staan als 'beste' regel --
    `aandeel_juist=None` moet achter elke regel met een echt aandeel komen."""
    beoordelingen = [terugkoppeling.registreer("V1", "vervallen_code", "signaal_was_onjuist")]
    uit = terugkoppeling.rangschikking(beoordelingen)
    beoordeelde_ids = {r["regel_id"] for r in uit if r["status"] == "beoordeeld"}
    laatste_index = max(i for i, r in enumerate(uit) if r["status"] == "geen terugkoppeling")
    eerste_beoordeeld_index = min(i for i, r in enumerate(uit) if r["regel_id"] in beoordeelde_ids)
    assert eerste_beoordeeld_index < laatste_index


def test_rangschikking_bewaart_de_versies_die_bij_de_beoordelingen_horen():
    oordeel = terugkoppeling.registreer("V1", "vervallen_code", "signaal_was_juist")
    uit = terugkoppeling.rangschikking([oordeel])
    rij = next(r for r in uit if r["regel_id"] == "vervallen_code")
    assert rij["versies"] == [oordeel["regelversie"]]


# == De harde taalregel over de drie paden: signaaltekst, dossier én het gerenderde werkblad =====
#
# De bestaande taalregel-tests in `test_toezicht_dossier.py` roepen `dossier.dossier()` rechtstreeks
# aan, en die functie zet `waarom` nooit (zie haar eigen test
# `test_een_uitgezette_agent_staat_als_uitgezet_in_het_dossier`: `waarom` is zelfs afwezig als
# `uitlegger` meedraait, want `dossier()` kent de uitlegger niet). Dat betekent dat geen bestaande
# test ooit een echte `waarom`-tekst door de dossier- of rapportpaden heen laat lopen. Deze test
# doet dat wel, via de volledige standaardpijplijn (`runner.Crew.draai`), en scant zowel het
# teruggegeven dossier als het gerenderde `.xlsx` -- precies de uitbreiding die de opdracht vraagt
# ("je waarom-tekst landt in alle drie de paden, dus breid de discipline uit in plaats van hem aan
# te nemen").

def test_de_taalregel_geldt_ook_voor_waarom_in_het_dossier_en_het_werkblad(tmp_path):
    from openpyxl import load_workbook

    from leefomgevinglab.usecases.toezicht import rapport, runner
    from tests.test_toezicht_runner import AGENTS, CONTEXT, TASKS, VESTIGING_FIXTURE

    aquo_ref = {"geldig": {}, "vervallen": {"zwevende stof": "ZS"}, "vervangen_door": {}}
    crew = runner.laad(AGENTS, TASKS)
    uitkomst = crew.draai(
        {"vestiging": VESTIGING_FIXTURE, "context": CONTEXT, "aquo_ref": aquo_ref})
    d = uitkomst["dossier"]

    gevuld = [s for s in d["signalen"] if s.get("waarom")]
    assert gevuld, "deze invoer moet minstens één signaal een waarom opleveren"

    # Pad 1: het dossier zelf.
    tekst_dossier = " ".join(s.get("waarom") or "" for s in d["signalen"]).lower()
    for verboden in _VERBODEN:
        assert verboden not in tekst_dossier

    # Pad 2: het gerenderde werkblad.
    pad = tmp_path / "met_waarom.xlsx"
    rapport.schrijf(d, str(pad))
    wb = load_workbook(str(pad))
    cellen = [str(cel) for naam in wb.sheetnames for rij in wb[naam].iter_rows(values_only=True)
              for cel in rij if cel is not None]
    tekst_werkblad = " ".join(cellen).lower()
    for verboden in _VERBODEN:
        assert verboden not in tekst_werkblad
    # En de uitleg moet ook echt op het blad terechtkomen, niet alleen ongevaarlijk afwezig zijn.
    assert any(gevuld[0]["waarom"] in cel for cel in cellen)


# == Fix-ronde 2 ===================================================================================

# -- Bevinding A: de vindplaats moet de dossier- en werkbladgrens overleven -----------------------

def test_tool_uitleg_genereren_draagt_de_vindplaatsen_niet_alleen_de_tekst_over():
    """Vóór deze fix zette `tool_uitleg_genereren` alleen `uit["tekst"]` op het signaal en liet
    `uit["vindplaatsen"]` vallen -- de harde regel hield binnen `uitleg.waarom()` stand maar was
    op de pagina onzichtbaar (geverifieerd: het woord 'vindplaats' kwam nul keer voor in de
    gepubliceerde HTML)."""
    from leefomgevinglab.usecases.toezicht import runner
    from tests.test_toezicht_runner import AGENTS, CONTEXT, TASKS, VESTIGING_FIXTURE

    aquo_ref = {"geldig": {}, "vervallen": {"zwevende stof": "ZS"}, "vervangen_door": {}}
    crew = runner.laad(AGENTS, TASKS)
    uitkomst = crew.draai(
        {"vestiging": VESTIGING_FIXTURE, "context": CONTEXT, "aquo_ref": aquo_ref})
    vervallen = next(s for s in uitkomst["dossier"]["signalen"] if s["regel"] == "vervallen_code")
    assert vervallen.get("waarom")
    assert vervallen.get("waarom_vindplaatsen"), \
        "een signaal met een waarom moet ook zijn vindplaatsen dragen"
    assert vervallen["waarom_vindplaatsen"] == ["Aquo-domeintabel Parameter, code ZS, status Vervallen"]


def test_rapport_schrijft_de_vindplaats_naast_de_waarom(tmp_path):
    """Dezelfde grens, nu voor het werkblad -- wat een inspecteur in de praktijk mee de deur uit
    neemt (zie `rapport.py`'s moduledocstring) moet de bron ook dragen, niet alleen de pagina."""
    from openpyxl import load_workbook

    from leefomgevinglab.usecases.toezicht import rapport

    d = {"signalen": [{
        "regel": "vervallen_code", "signaal": "grenswaarde op een ingetrokken code",
        "zwaarte": "hoog", "omvang": 1, "bewijs": [], "grondslag": "code", "zekerheid": "uit de bron",
        "wat_te_doen": "Vraag welke code nu geldt.",
        "waarom": "'Zwevende stof' is ingetrokken (code ZS).",
        "waarom_vindplaatsen": ["Aquo-domeintabel Parameter, code ZS, status Vervallen"],
    }]}
    pad = tmp_path / "met_vindplaats.xlsx"
    rapport.schrijf(d, str(pad))
    wb = load_workbook(str(pad))
    cellen = [str(c) for rij in wb[wb.sheetnames[0]].iter_rows(values_only=True) for c in rij
              if c is not None]
    assert any("vindplaats" in c.lower() for c in cellen)
    assert any("Aquo-domeintabel Parameter, code ZS, status Vervallen" in c for c in cellen)


def test_een_signaal_zonder_waarom_schrijft_ook_geen_vindplaatsrij(tmp_path):
    """De keerzijde: geen `waarom`, dan ook geen losse 'vindplaats'-rij die een poging zou
    suggereren die niets opleverde."""
    from openpyxl import load_workbook

    from leefomgevinglab.usecases.toezicht import rapport

    d = {"signalen": [{
        "regel": "geen_geldigheidsduur", "signaal": "geen geldigheidsduur", "zwaarte": "laag",
        "omvang": 3, "bewijs": [], "grondslag": "geen", "zekerheid": "ontbreekt",
        "wat_te_doen": "Vraag of de vergunning nog geldt.",
    }]}
    pad = tmp_path / "zonder_vindplaats.xlsx"
    rapport.schrijf(d, str(pad))
    wb = load_workbook(str(pad))
    cellen = [str(c) for rij in wb[wb.sheetnames[0]].iter_rows(values_only=True) for c in rij
              if c is not None]
    assert not any("vindplaats" in c.lower() for c in cellen)


# == Residu 1 (R30) ================================================================================
#
# De pagina onderscheidt een afwezige `waarom` al in twee oorzaken (`waarom_reden` plus, waar van
# toepassing, `waarom_gedupliceerd`) -- het werkblad deed dat tot nu toe niet: zonder `waarom` kreeg
# een signaal daar helemaal geen rij, dus de twee oorzaken waren op het blad allebei hetzelfde
# "niets". Deze tests lezen het geschreven bestand terug met `load_workbook`, niet het dossier-dict.

def test_rapport_schrijft_een_reden_als_waarom_ontbreekt(tmp_path):
    """Geen van de vier bronnen had een treffer -- het blad moet die reden nu wél tonen."""
    from openpyxl import load_workbook

    from leefomgevinglab.usecases.toezicht import rapport

    reden = "Geen van de vier bronnen (Aquo, normenset, stelselcatalogus, /kmg-proclaimer) " \
            "noemt dit trefwoord."
    d = {"signalen": [{
        "regel": "vervallen_code", "signaal": "grenswaarde op een ingetrokken code",
        "zwaarte": "hoog", "omvang": 1, "bewijs": [], "grondslag": "code", "zekerheid": "uit de bron",
        "wat_te_doen": "Vraag welke code nu geldt.",
        "waarom_reden": reden,
    }]}
    pad = tmp_path / "waarom_ontbreekt.xlsx"
    rapport.schrijf(d, str(pad))
    wb = load_workbook(str(pad))
    cellen = [str(c) for rij in wb[wb.sheetnames[0]].iter_rows(values_only=True) for c in rij
              if c is not None]
    assert any(reden in c for c in cellen)
    assert any("ontbreekt" in c.lower() for c in cellen)


def test_rapport_onderscheidt_een_dubbele_waarom_van_een_ontbrekende(tmp_path):
    """De tweede oorzaak (een treffer die hier bewust niet herhaald wordt) moet op het blad van
    de eerste (geen treffer) te onderscheiden zijn -- niet allebei als hetzelfde niets lezen."""
    from openpyxl import load_workbook

    from leefomgevinglab.usecases.toezicht import rapport

    reden = "Deze verklaring is woordelijk gelijk aan die van een eerder, zwaarder wegend " \
            "signaal in dit dossier en wordt daarom hier niet herhaald."
    d = {"signalen": [{
        "regel": "geen_onafhankelijke_meting", "signaal": "geen onafhankelijke meting",
        "zwaarte": "midden", "omvang": 1, "bewijs": [], "grondslag": "code", "zekerheid": "uit de bron",
        "wat_te_doen": "Vraag naar de meting.",
        "waarom_reden": reden,
        "waarom_gedupliceerd": True,
    }]}
    pad = tmp_path / "waarom_dupliceert.xlsx"
    rapport.schrijf(d, str(pad))
    wb = load_workbook(str(pad))
    cellen = [str(c) for rij in wb[wb.sheetnames[0]].iter_rows(values_only=True) for c in rij
              if c is not None]
    assert any(reden in c for c in cellen)
    assert any("dupliceert" in c.lower() for c in cellen)
    assert not any("ontbreekt" in c.lower() for c in cellen)


def test_rapport_laat_een_echte_waarom_onveranderd_naast_de_nieuwe_redenrij(tmp_path):
    """Een signaal met een echte `waarom` moet precies het bestaande pad volgen (de `waarom`- en
    `vindplaats`-rijen), ook al draagt het geen `waarom_reden` -- de nieuwe tak mag de bestaande
    niet raken."""
    from openpyxl import load_workbook

    from leefomgevinglab.usecases.toezicht import rapport

    d = {"signalen": [{
        "regel": "vervallen_code", "signaal": "grenswaarde op een ingetrokken code",
        "zwaarte": "hoog", "omvang": 1, "bewijs": [], "grondslag": "code", "zekerheid": "uit de bron",
        "wat_te_doen": "Vraag welke code nu geldt.",
        "waarom": "'Zwevende stof' is ingetrokken (code ZS).",
        "waarom_vindplaatsen": ["Aquo-domeintabel Parameter, code ZS, status Vervallen"],
    }]}
    pad = tmp_path / "waarom_echt.xlsx"
    rapport.schrijf(d, str(pad))
    wb = load_workbook(str(pad))
    cellen = [str(c) for rij in wb[wb.sheetnames[0]].iter_rows(values_only=True) for c in rij
              if c is not None]
    assert any("'Zwevende stof' is ingetrokken (code ZS)." in c for c in cellen)
    assert any("Aquo-domeintabel Parameter, code ZS, status Vervallen" in c for c in cellen)
    assert not any("ontbreekt" in c.lower() for c in cellen)
    assert not any("dupliceert" in c.lower() for c in cellen)


def test_rapport_schrijft_geen_redenrij_zonder_een_van_de_drie_velden(tmp_path):
    """De keerzijde, net als bij de vindplaats hierboven: geen `waarom`, geen `waarom_reden` en
    geen `waarom_gedupliceerd` -- dan blijft dit signaal zonder rij, een poging die niets
    opleverde moet geen rij suggereren."""
    from openpyxl import load_workbook

    from leefomgevinglab.usecases.toezicht import rapport

    d = {"signalen": [{
        "regel": "geen_geldigheidsduur", "signaal": "geen geldigheidsduur", "zwaarte": "laag",
        "omvang": 3, "bewijs": [], "grondslag": "geen", "zekerheid": "ontbreekt",
        "wat_te_doen": "Vraag of de vergunning nog geldt.",
    }]}
    pad = tmp_path / "waarom_helemaal_niets.xlsx"
    rapport.schrijf(d, str(pad))
    wb = load_workbook(str(pad))
    # Niet alle cellen (de "zekerheid"-rij draagt toevallig ook het woord "ontbreekt" als
    # waarde) -- alleen de labels in de eerste kolom, want dáár zou een nieuwe "waarom"-rij
    # moeten staan als deze tak onterecht vuurde.
    labels = [str(rij[0]).lower() for rij in wb[wb.sheetnames[0]].iter_rows(values_only=True)
              if rij and rij[0] is not None]
    assert not any(label.startswith("waarom") for label in labels)


def test_uitleg_waarom_verwerpt_ook_een_verboden_vindplaats():
    """Fix-ronde 2 breidt de poort uit: niet alleen de tekst van een treffer, ook zijn vindplaats
    moet de taalregel halen -- nu die vindplaats voor het eerst zichtbaar is op de pagina en in
    het werkblad."""
    def _zoek(vraag, n):
        return [{"tekst": "Een neutraal feit.", "vindplaats": "Bron met een overtreding erin"}]

    uit = uitleg.waarom("iets", _zoek=_zoek)
    assert uit["beschikbaar"] is False


# -- Bevinding B: de vraag moet over het signaal zelf gaan, niet overspoeld worden door stofnamen -

def test_vracht_onbepaald_krijgt_geen_verklaring_als_er_geen_juiste_bron_is():
    """Het letterlijke voorbeeld uit de bevinding: vóór de fix citeerde dit signaal drie Aquo-
    zinnen over 'Minerale olie'/'Olie'/'Zwevende stof' -- geen daarvan legt uit waarom een
    ontbrekend debietvoorschrift aandacht verdient. Na de fix: liever geen verklaring dan een
    over de verkeerde vraag."""
    from leefomgevinglab.usecases.toezicht import runner

    vestiging = {
        "naam": "Reproductie bevinding B", "kenmerk": "K1", "url": "https://x",
        "besluitdatum": "2020-01-01",
        "voorschriften": [
            {"parameter": "Minerale olie", "waarde": 1.0, "eenheid": "milligram per liter"},
            {"parameter": "Olie", "waarde": 2.0, "eenheid": "milligram per liter"},
            {"parameter": "Zwevende stof", "waarde": 30.0, "eenheid": "milligram per liter",
             "aquo": "ZS", "aquo_status": "Vervallen"},
        ],
    }
    aquo_ref = {"geldig": {"minerale olie": "MINROLE", "olie": "OLE"},
                "vervallen": {"zwevende stof": "ZS"}, "vervangen_door": {}}
    crew = runner.laad(*_agents_tasks())
    uitkomst = crew.draai({"vestiging": vestiging, "context": {}, "aquo_ref": aquo_ref})
    vracht = next(s for s in uitkomst["dossier"]["signalen"] if s["regel"] == "vracht_onbepaald")
    assert "waarom" not in vracht, \
        "geen van de bronnen legt uit waarom een debietvoorschrift ontbreekt -- dit moet leeg blijven"


def test_niet_regime_zuiver_krijgt_zijn_eigen_antwoord_niet_het_aquo_antwoord_van_een_ander_signaal():
    """De tweede helft van hetzelfde voorbeeld: `niet_regime_zuiver` moet de hoedanigheid-
    kanttekening van de proclaimer-bron krijgen (fix-ronde 1), niet de Aquo-zinnen die vóór deze
    fix elke beschikbare plek vulden."""
    from leefomgevinglab.usecases.toezicht import runner

    vestiging = {
        "naam": "Reproductie bevinding B", "kenmerk": "K1", "url": "https://x",
        "besluitdatum": "2020-01-01",
        "voorschriften": [
            {"parameter": "Minerale olie", "waarde": 1.0, "eenheid": "milligram per liter",
             "bemonstering": "Steekmonster"},
            {"parameter": "Olie", "waarde": 2.0, "eenheid": "milligram per liter",
             "bemonstering": "Steekmonster"},
        ],
    }
    aquo_ref = {"geldig": {"minerale olie": "MINROLE", "olie": "OLE"}, "vervallen": {},
                "vervangen_door": {}}
    crew = runner.laad(*_agents_tasks())
    uitkomst = crew.draai({"vestiging": vestiging, "context": {}, "aquo_ref": aquo_ref})
    regime = next(s for s in uitkomst["dossier"]["signalen"] if s["regel"] == "niet_regime_zuiver")
    assert regime.get("waarom")
    assert "minerale olie" not in regime["waarom"].lower()
    assert "olie" not in regime["waarom"].lower() or "grootheden" in regime["waarom"].lower()
    assert "grootheden" in regime["waarom"].lower()
    assert "proclaimer" in regime["waarom_vindplaatsen"][0].lower()


def test_twee_verschillende_regels_krijgen_nooit_dezelfde_waarom_tekst_op_de_echte_fixture():
    """Letterlijk gevraagd in de taakbrief: op de grote, alles-laat-vuren-fixture
    (`VESTIGING_MET_ALLES`/`CONTEXT_MET_ALLES`) mogen twee verschillende regel-ID's nooit dezelfde
    `waarom`-tekst dragen. Dit gebeurt legitiem bij gelijke onderliggende feiten (`vervallen_code`
    en `geen_onafhankelijke_meting` kunnen allebei over 'Zwevende stof' gaan) -- `tool_uitleg_
    genereren` dedupliceert daarom over de hele vestiging, niet per signaal."""
    from leefomgevinglab.usecases.toezicht import runner
    from tests.test_toezicht_signalen import CONTEXT_MET_ALLES, VESTIGING_MET_ALLES

    aquo_ref = {"geldig": {"zink": "Zn"}, "vervallen": {"zwevende stof": "ZS"},
                "vervangen_door": {}}
    normenset = {"normen": {"NL91_X": [
        {"meetpunt": "NL91_X", "parameter": "Zn", "hoedanigheid": "NVT",
         "grondslag": "jaargemiddelde", "norm": 7.8, "eenheid": "ug/l"},
    ]}}
    crew = runner.laad(*_agents_tasks())
    uitkomst = crew.draai({"vestiging": VESTIGING_MET_ALLES, "context": CONTEXT_MET_ALLES,
                           "aquo_ref": aquo_ref, "normenset": normenset})
    teksten = [s["waarom"] for s in uitkomst["dossier"]["signalen"] if s.get("waarom")]
    assert teksten, "deze fixture moet minstens één waarom opleveren om dit te kunnen toetsen"
    assert len(teksten) == len(set(teksten)), \
        f"twee signalen dragen dezelfde waarom-tekst: {teksten}"
    # En elk signaal met een waarom draagt ook een vindplaats (bevinding A, nog een keer, nu over
    # de hele, zwaarste fixture in plaats van één handgemaakt geval).
    for s in uitkomst["dossier"]["signalen"]:
        if s.get("waarom"):
            assert s.get("waarom_vindplaatsen"), f"{s['regel']} heeft een waarom zonder vindplaats"


def _agents_tasks():
    import os

    from leefomgevinglab.usecases.toezicht import runner
    config_dir = os.path.join(os.path.dirname(runner.__file__), "config")
    return (os.path.join(config_dir, "agents.yaml"), os.path.join(config_dir, "tasks.yaml"))


# == Fix-ronde (eindreview, bevinding 5): een afwezige verklaring was onzichtbaar ================
#
# `static/toezicht.html` toonde vóór deze fix niets zodra een signaal geen `waarom` droeg -- en
# dat gold voor twee heel verschillende oorzaken (geen bron gevonden; een gevonden tekst die hier
# bewust niet herhaald wordt omdat een eerder, zwaarder signaal hem al claimt). Beide moeten nu
# een eigen, zichtbare `waarom_reden` krijgen, en de tweede ook `waarom_gedupliceerd=True`.

def test_een_signaal_zonder_enige_treffer_draagt_waarom_reden_in_plaats_van_niets():
    """Het letterlijke voorbeeld uit bevinding B (hierboven): `vracht_onbepaald` krijgt geen
    `waarom`, want geen van de vier bronnen legt uit waarom een debietvoorschrift ontbreekt. Vóór
    deze fix betekende dat: niets. Nu draagt het signaal `uitleg._GEEN_TREFFER` als `waarom_reden`,
    en expliciet geen `waarom_gedupliceerd`."""
    from leefomgevinglab.usecases.toezicht import runner

    vestiging = {
        "naam": "Reproductie bevinding 5", "kenmerk": "K1", "url": "https://x",
        "besluitdatum": "2020-01-01",
        "voorschriften": [
            {"parameter": "Minerale olie", "waarde": 1.0, "eenheid": "milligram per liter"},
        ],
    }
    aquo_ref = {"geldig": {"minerale olie": "MINROLE"}, "vervallen": {}, "vervangen_door": {}}
    crew = runner.laad(*_agents_tasks())
    uitkomst = crew.draai({"vestiging": vestiging, "context": {}, "aquo_ref": aquo_ref})
    vracht = next(s for s in uitkomst["dossier"]["signalen"] if s["regel"] == "vracht_onbepaald")
    assert "waarom" not in vracht
    assert vracht.get("waarom_reden") == uitleg._GEEN_TREFFER
    assert not vracht.get("waarom_gedupliceerd")


def test_een_onderdrukte_duplicaattekst_draagt_een_andere_reden_dan_geen_treffer():
    """De tweede oorzaak: op de grote, alles-laat-vuren-fixture claimt een eerder, zwaarder
    signaal dezelfde Aquo-treffer voor 'Zwevende stof' als een latere `geen_onafhankelijke_
    meting`-instantie (zie `test_twee_verschillende_regels_krijgen_nooit_dezelfde_waarom_tekst_
    op_de_echte_fixture` hierboven) -- die tweede instantie moet nu een eigen `waarom_reden`
    dragen, onderscheiden van 'geen bron gevonden' via `waarom_gedupliceerd=True`."""
    from leefomgevinglab.usecases.toezicht import runner
    from tests.test_toezicht_signalen import CONTEXT_MET_ALLES, VESTIGING_MET_ALLES

    aquo_ref = {"geldig": {"zink": "Zn"}, "vervallen": {"zwevende stof": "ZS"},
                "vervangen_door": {}}
    normenset = {"normen": {"NL91_X": [
        {"meetpunt": "NL91_X", "parameter": "Zn", "hoedanigheid": "NVT",
         "grondslag": "jaargemiddelde", "norm": 7.8, "eenheid": "ug/l"},
    ]}}
    crew = runner.laad(*_agents_tasks())
    uitkomst = crew.draai({"vestiging": VESTIGING_MET_ALLES, "context": CONTEXT_MET_ALLES,
                           "aquo_ref": aquo_ref, "normenset": normenset})
    gedupliceerd = [s for s in uitkomst["dossier"]["signalen"] if s.get("waarom_gedupliceerd")]
    assert gedupliceerd, "deze fixture moet minstens één onderdrukte duplicaattekst opleveren"
    for s in gedupliceerd:
        assert "waarom" not in s
        assert s.get("waarom_reden")
        assert s["waarom_reden"] != uitleg._GEEN_TREFFER, (
            "een onderdrukte duplicaattekst moet een andere reden dragen dan 'geen bron "
            "gevonden' -- dat zijn twee verschillende oorzaken (bevinding 5)")


def test_de_taalregel_geldt_ook_voor_waarom_reden():
    """Dezelfde harde taalregel als op `waarom` zelf, nu ook op de nieuwe `waarom_reden` -- die
    tekst landt sinds deze fix ook op de pagina."""
    from leefomgevinglab.usecases.toezicht import runner
    from tests.test_toezicht_signalen import CONTEXT_MET_ALLES, VESTIGING_MET_ALLES

    aquo_ref = {"geldig": {"zink": "Zn"}, "vervallen": {"zwevende stof": "ZS"},
                "vervangen_door": {}}
    crew = runner.laad(*_agents_tasks())
    uitkomst = crew.draai({"vestiging": VESTIGING_MET_ALLES, "context": CONTEXT_MET_ALLES,
                           "aquo_ref": aquo_ref})
    redenen = [s.get("waarom_reden") for s in uitkomst["dossier"]["signalen"] if s.get("waarom_reden")]
    assert redenen, "deze fixture moet minstens één waarom_reden opleveren om dit te kunnen toetsen"
    tekst = " ".join(redenen).lower()
    for verboden in _VERBODEN:
        assert verboden not in tekst
