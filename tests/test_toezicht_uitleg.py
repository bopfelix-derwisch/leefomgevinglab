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
