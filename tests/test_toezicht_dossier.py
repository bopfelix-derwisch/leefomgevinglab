"""`toezicht.dossier` en `toezicht.rapport` -- het informatieproduct zelf (plan, §2).

Geen netwerk: `dossier()` en `rapport.schrijf()` werken uitsluitend op wat ze als argument
krijgen. De grote fixture (`VESTIGING_MET_ALLES`/`CONTEXT_MET_ALLES`) komt uit
`test_toezicht_signalen.py` en laat -- zoals die module zelf al test -- alle tien signaalregels
vuren, inclusief signaal 1 twee keer (één keer per Aquo-code, zie taak 2).

**Eén uitzondering (fix-ronde 2, publieke review).** `test_geen_twee_signalen_in_een_dossier_
delen_dezelfde_bewering_op_het_echte_register` staat gemarkeerd `@pytest.mark.live` en raakt het
echte Atlas-register. Reden: de fixture-versie van deze invariant (direct erboven) bewaakt het
patroon op verzonnen data, en de echte bug (Tata Steel: twee `meerdere_grenswaarden`-signalen met
letterlijk dezelfde bewering, één parameter in twee eenheidsgroepen) zat in een combinatie die
geen fixture toevallig bouwde. Dezelfde reden als `test_toezicht_live.py`: een vangnet dat alleen
op verzonnen data draait, vindt deze klasse fout niet.
"""
import re
import tempfile

import pytest
from openpyxl import load_workbook

from leefomgevinglab.usecases.kmg.lozingsmodel import ZEKERHEDEN
from leefomgevinglab.usecases.maaskaart import GRONDSLAG
from leefomgevinglab.usecases.toezicht import aquo as aquo_mod
from leefomgevinglab.usecases.toezicht import dossier, rapport, signalen
from leefomgevinglab.usecases.toezicht import register as register_mod
from tests.test_toezicht_signalen import CONTEXT_MET_ALLES, VESTIGING_MET_ALLES

_VERBODEN = ("overtreding", "veroorzaakt door", "in strijd met")


# -- Deel A: de kaart ---------------------------------------------------------------------------

def test_een_ontbrekend_veld_staat_in_de_kaart_als_ontbrekend():
    """Brief, stap 1, letterlijk."""
    d = dossier.dossier({"naam": "X", "kenmerk": None, "url": None, "voorschriften": []}, {})
    assert d["kaart"]["kenmerk"] == {"waarde": None, "zekerheid": "ontbreekt"}
    assert "kenmerk" in d["kaart"], "weglaten verbergt juist wat voor toezicht het signaal is"


def test_alle_negen_kaartvelden_staan_er_ontbrekend_bij_een_lege_vestiging():
    """Niet alleen `kenmerk` -- alle negen velden uit het plan (§2 deel A) moeten aanwezig zijn
    en, zonder bron, `ontbreekt` dragen. Weglaten van een van de negen is hetzelfde probleem als
    de verbatim-test hierboven al voor `kenmerk` bewaakt."""
    d = dossier.dossier({"voorschriften": []}, {})
    verwacht = {"naam", "plaats", "locatie", "locatiecode", "vestigingsnummer_kvk", "kenmerk",
                "besluitdatum", "waterlichaam", "url"}
    assert set(d["kaart"]) == verwacht
    for veld in verwacht:
        assert d["kaart"][veld] == {"waarde": None, "zekerheid": "ontbreekt"}, veld


def test_een_volledige_kaart_toont_elk_veld_als_uit_de_bron():
    vestiging = {
        "naam": "Lozer BV", "plaats": "Deventer", "locatie": "aan de IJssel",
        "locatiecode": "LOC123", "vestigingsnummer_kvk": "000020643233",
        "kenmerk": "WL-2020-001", "besluitdatum": "2020-01-01", "waterlichaam": "NL91BM",
        "url": "https://example.org/vergunning.pdf", "voorschriften": [],
    }
    d = dossier.dossier(vestiging, {})
    for veld, waarde in (
        ("naam", "Lozer BV"), ("plaats", "Deventer"), ("locatie", "aan de IJssel"),
        ("locatiecode", "LOC123"), ("vestigingsnummer_kvk", "000020643233"),
        ("kenmerk", "WL-2020-001"), ("besluitdatum", "2020-01-01"),
        ("waterlichaam", "NL91BM"), ("url", "https://example.org/vergunning.pdf"),
    ):
        assert d["kaart"][veld] == {"waarde": waarde, "zekerheid": "uit de bron"}, veld


def test_de_kaart_leest_het_waterlichaam_rechtstreeks_zonder_het_zelf_op_te_zoeken():
    """`dossier()` doet geen netwerk: `waterlichaam` in de kaart komt 1-op-1 uit `vestiging`,
    niet uit `context` en niet uit een eigen opzoeking op de voorschriftcoördinaten."""
    vestiging = {"waterlichaam": "NL91ZM", "voorschriften": []}
    d = dossier.dossier(vestiging, {"waterlichaam": "NL91BM"})
    assert d["kaart"]["waterlichaam"] == {"waarde": "NL91ZM", "zekerheid": "uit de bron"}


# -- Deel B: de signalen --------------------------------------------------------------------

def test_deel_b_bewaart_de_rangschikking_van_signalen_signalen():
    """`dossier()` verzint geen eigen volgorde; hij geeft door wat `signalen.signalen()` al
    rangschikt op zwaarte en dan omvang."""
    ruw = signalen.signalen(VESTIGING_MET_ALLES, CONTEXT_MET_ALLES)
    d = dossier.dossier(VESTIGING_MET_ALLES, CONTEXT_MET_ALLES)
    assert [s["regel"] for s in d["signalen"]] == [s["regel"] for s in ruw]
    assert [s["omvang"] for s in d["signalen"]] == [s["omvang"] for s in ruw]


def test_elk_signaal_draagt_de_zes_velden_van_deel_b():
    d = dossier.dossier(VESTIGING_MET_ALLES, CONTEXT_MET_ALLES)
    for s in d["signalen"]:
        for sleutel in ("signaal", "zwaarte", "bewijs", "grondslag", "zekerheid", "wat_te_doen"):
            assert sleutel in s, (s.get("regel"), sleutel)
        # Nog niet gebouwd (latere taken): expliciet afwezig, niet per ongeluk aanwezig als None.
        assert "waarom" not in s
        assert "stap" not in s


# -- Deel B, fix-ronde 1 (R20-review, bevinding 2): de bewering als volzin met het getal erin ----

def test_elk_signaal_draagt_een_bewering_met_het_getal_erin_voor_een_telling():
    """Plan §2, beslissing 2: geen los cijfer in een tegel, maar een zin waar het getal in zit.
    `vervallen_code` is hier een regel waarvan `omvang` een telling is (geen verhouding) --
    precies het geval dat de review vroeg te bewijzen."""
    d = dossier.dossier(VESTIGING_MET_ALLES, CONTEXT_MET_ALLES)
    s = next(x for x in d["signalen"] if x["regel"] == "vervallen_code")
    assert str(round(s["omvang"])) in s["bewering"]
    assert s["bewering"].endswith(".")
    for verboden in _VERBODEN:
        assert verboden not in s["bewering"].lower()


def test_de_bewering_bij_een_verhouding_toont_geen_tellingstekst():
    """`meerdere_grenswaarden` draagt een verhouding (hoogste/laagste grenswaarde), geen
    telling -- "4,0 verhouding hoogste / laagste grenswaarde." zou onzin zijn, dus deze regel
    krijgt een eigen vorm (factor ...×) in plaats van het tellingssjabloon."""
    d = dossier.dossier(VESTIGING_MET_ALLES, CONTEXT_MET_ALLES)
    s = next(x for x in d["signalen"] if x["regel"] == "meerdere_grenswaarden")
    assert "×" in s["bewering"]
    assert "4,0" in s["bewering"]
    assert "verhouding" not in s["bewering"]


def test_de_bewering_bij_een_onbegrensde_verhouding_crasht_niet_en_noemt_de_nul():
    """Eindreview, bevinding 2: `signalen.regel_meerdere_grenswaarden` geeft `float("inf")` als
    de laagste grenswaarde 0 is -- `_bewering()` mag daar geen `ValueError` op `.1f` of een
    onleesbare 'inf×' van maken, en moet wel de taalregel blijven halen."""
    v = {"voorschriften": [
        {"parameter": "Zink", "waarde": 0.0, "eenheid": "milligram per liter"},
        {"parameter": "Zink", "waarde": 2.0, "eenheid": "milligram per liter"},
    ]}
    d = dossier.dossier(v, {})
    s = next(x for x in d["signalen"] if x["regel"] == "meerdere_grenswaarden")
    assert s["bewering"]
    assert "0" in s["bewering"]
    for verboden in _VERBODEN:
        assert verboden not in s["bewering"].lower()


def test_elke_regel_in_de_catalogus_levert_een_niet_lege_bewering_met_het_getal_erin():
    """Alle tien regels, niet alleen de twee die de vorige twee tests noemen -- een regel zonder
    bewering zou de pagina terugzetten naar de kale kop die de review afkeurde. Het getal zelf
    (hier 5, zodat het niet toevallig met iets anders in de tekst samenvalt) moet in elke
    bewering terugkomen, ook bij de verhouding (als "5,0"), met één uitzondering:
    `geen_geldigheidsduur` schrijft een telling van 1 als "het enige voorschrift" zonder het
    cijfer zelf te tonen (zie de tabel) -- bij een telling van 5 staat het cijfer er wél."""
    for regel_id in signalen.DREMPELS:
        zin = dossier._bewering(5, regel_id)
        assert zin and zin.strip()
        assert "5" in zin, f"{regel_id}: het getal staat niet in de bewering: {zin!r}"
        for verboden in _VERBODEN:
            assert verboden not in zin.lower()


def test_elke_regel_vervoegt_het_enkelvoud_correct_bij_een_telling_van_1():
    """Fix-ronde 2 van de review: '1 voorschriften' (het meervoud, niet vervoegd) kwam voor bij
    meerdere van de tien regels. Getest voor alle tien -- een telling van 1 is precies de
    waarde die de fout blootlegt, en de twee regels die niet in `_BEWERING_PER_REGEL` staan
    (de verhouding kent geen telling) hebben dit probleem per ontwerp niet."""
    for regel_id in signalen.DREMPELS:
        zin = dossier._bewering(1, regel_id)
        assert "1 voorschriften" not in zin, f"{regel_id}: meervoud bij telling 1: {zin!r}"
        assert "1 stoffen" not in zin, f"{regel_id}: meervoud bij telling 1: {zin!r}"
        assert "1 velden" not in zin, f"{regel_id}: meervoud bij telling 1: {zin!r}"
        assert "1 concentratievoorschriften" not in zin, f"{regel_id}: {zin!r}"
        # `geen_geldigheidsduur` schrijft een telling van 1 bewust zonder het cijfer te tonen
        # ("het enige voorschrift") -- zie de tabel. Elke andere regel toont het wél.
        if regel_id != "geen_geldigheidsduur" and regel_id not in dossier._RATIO_REGELS:
            assert "1" in zin, f"{regel_id}: geen getal in de bewering bij telling 1: {zin!r}"


def test_geen_bewering_is_nog_een_sleutel_waardepaar():
    """Plan §2, beslissing 2, letterlijk: 'De bewering is een zin, geen sleutel-waardepaar.'
    Fix-ronde 1 liet `niet_regime_zuiver` en `geen_geldigheidsduur` terugvallen op precies dat
    patroon ("Kop: N voorschriften."). Deze regex herkent dat patroon (tekst, dubbele punt,
    een los getal plus woord, punt) -- een dubbele punt gevolgd door een echte bijzin (zoals bij
    `vracht_onbepaald`, waar na de punt geen cijfer volgt) matcht hem niet."""
    patroon = re.compile(r"^.+:\s*\d+\s+\S+\.$")
    for regel_id in signalen.DREMPELS:
        zin = dossier._bewering(5, regel_id)
        assert not patroon.match(zin), f"{regel_id}: nog een sleutel-waardepaar: {zin!r}"


def test_elke_regel_behalve_de_verhouding_staat_in_de_beweringtabel():
    """Volledigheid, zelfde vorm als bij `_HERKOMST_PER_REGEL`/`_WAT_TE_DOEN_PER_REGEL`."""
    assert set(dossier._BEWERING_PER_REGEL) | dossier._RATIO_REGELS == set(signalen.DREMPELS)


# -- Fix-ronde 3 (publieke review op `/toezicht`, 2026-11-14): een bewering moet haar stof -----
# -- noemen, en binnen één dossier mag geen twee signalen dezelfde bewering delen --------------

def test_geen_onafhankelijke_meting_noemt_de_eigen_stof_in_de_bewering():
    """`geen_onafhankelijke_meting` vuurt per Aquo-code (taak 2) -- zonder de stof in de
    bewering waren de twee exemplaren van `VESTIGING_MET_ALLES` (Zwevende stof en Zuurgraad)
    woordelijk niet van elkaar te onderscheiden. Dat was precies de publieke bevinding: vijf van
    de zes beweringen van Solvay (NATRON) waren identiek."""
    d = dossier.dossier(VESTIGING_MET_ALLES, CONTEXT_MET_ALLES)
    exemplaren = {s["bewering"] for s in d["signalen"] if s["regel"] == "geen_onafhankelijke_meting"}
    assert len(exemplaren) == 2, f"de twee exemplaren delen hun bewering: {exemplaren}"
    assert any("Zwevende stof" in b for b in exemplaren)
    assert any("Zuurgraad" in b for b in exemplaren)
    for b in exemplaren:
        assert "1 voorschrift " in b, f"geen vervoeging/getal in de bewering: {b!r}"


def test_meerdere_grenswaarden_noemt_de_parameter_in_de_bewering():
    """Zelfde reparatie voor de andere regel met dit probleem (op `/wasstraat` -- bij Tata Steel
    live elf keer achter elkaar "Dezelfde parameter..."). Twee parameters, allebei met twee
    grenswaarden, moeten twee te onderscheiden beweringen opleveren, elk met haar eigen naam."""
    v = {"voorschriften": [
        {"parameter": "Zink", "waarde": 0.5, "eenheid": "milligram per liter"},
        {"parameter": "Zink", "waarde": 2.0, "eenheid": "milligram per liter"},
        {"parameter": "Koper", "waarde": 1.0, "eenheid": "milligram per liter"},
        {"parameter": "Koper", "waarde": 4.0, "eenheid": "milligram per liter"},
    ]}
    d = dossier.dossier(v, {})
    exemplaren = {s["bewering"] for s in d["signalen"] if s["regel"] == "meerdere_grenswaarden"}
    assert len(exemplaren) == 2, f"de twee exemplaren delen hun bewering: {exemplaren}"
    assert any(b.startswith("Zink ") for b in exemplaren)
    assert any(b.startswith("Koper ") for b in exemplaren)


def test_geen_twee_signalen_in_een_dossier_delen_dezelfde_bewering():
    """De regel waar dit nu drie keer tegen gezondigd is (de eindreview op `vergunning_niet_te_
    vinden`, fix-ronde 2 van taak 7 op `waarom`, en nu deze twee regels): binnen één dossier mag
    geen enkele bewering letterlijk gelijk zijn aan een andere. Deze vestiging laat met opzet
    zowel `geen_onafhankelijke_meting` als `meerdere_grenswaarden` elk twee keer vuren, zodat een
    toekomstige regressie in deze of een andere regel hier meteen zichtbaar is -- de test legt het
    patroon zelf vast, niet alleen dit ene geval."""
    v = {"voorschriften": [
        {"parameter": "Zink", "waarde": 0.5, "eenheid": "milligram per liter", "aquo": "Zn"},
        {"parameter": "Zink", "waarde": 2.0, "eenheid": "milligram per liter", "aquo": "Zn"},
        {"parameter": "Koper", "waarde": 0.5, "eenheid": "milligram per liter", "aquo": "Cu"},
        {"parameter": "Koper", "waarde": 5.0, "eenheid": "milligram per liter", "aquo": "Cu"},
    ]}
    context = {"gemeten_codes": set()}  # bewust leeg maar aangeleverd: niets wordt gemeten
    d = dossier.dossier(v, context)
    beweringen = [s["bewering"] for s in d["signalen"]]
    assert len(beweringen) == len(set(beweringen)), (
        f"twee signalen delen dezelfde bewering: {beweringen}")
    # De controle is niet toevallig leeg: beide regels moeten hier echt meermaals vuren.
    assert sum(1 for s in d["signalen"] if s["regel"] == "geen_onafhankelijke_meting") == 2
    assert sum(1 for s in d["signalen"] if s["regel"] == "meerdere_grenswaarden") == 2


def test_meerdere_grenswaarden_houdt_de_ij_digraaf_intact_bij_zinsbegin():
    """Fix-ronde 2 (publieke review): de ratio-tak van `_bewering()` zet de parameternaam vóór
    "draagt" (zinsbegin) met een hoofdletter -- `stof[0].upper() + stof[1:]` gaf daarop "Ijzer"
    in plaats van "IJzer". Gerepareerd via `woordvorm.hoofdletter_bij_zinsbegin`."""
    v = {"voorschriften": [
        {"parameter": "ijzer", "waarde": 1.0, "eenheid": "milligram per liter"},
        {"parameter": "ijzer", "waarde": 3.0, "eenheid": "milligram per liter"},
    ]}
    d = dossier.dossier(v, {})
    s = next(x for x in d["signalen"] if x["regel"] == "meerdere_grenswaarden")
    assert s["bewering"].startswith("IJzer ")
    assert "Ijzer" not in s["bewering"]


def test_dezelfde_parameter_in_twee_eenheidsgroepen_krijgt_twee_te_onderscheiden_beweringen():
    """Fix-ronde 2 (publieke review): `regel_meerdere_grenswaarden` groepeert op
    `(parameter, eenheid)` (fix-ronde van `signalen.py` zelf) -- dus dezelfde parameter kan
    **twee** signalen opleveren, één per eenheidsgroep. Live bij Tata Steel (Warmte, megajoule
    per dag naast megajoule per jaar) rondden beide toevallig af op dezelfde factor ("2,5×"), en
    zonder de eenheid in de bewering waren de twee toen letterlijk identiek. De bewering noemt de
    eenheid nu altijd (niet alleen zodra er toevallig een botsing is) -- eenvoudiger, en het
    blijft kloppen als een derde eenheidsgroep er ooit bijkomt."""
    v = {"voorschriften": [
        {"parameter": "Warmte", "waarde": 100.0, "eenheid": "megajoule per dag"},
        {"parameter": "Warmte", "waarde": 250.0, "eenheid": "megajoule per dag"},
        {"parameter": "Warmte", "waarde": 1000.0, "eenheid": "megajoule per jaar"},
        {"parameter": "Warmte", "waarde": 2500.0, "eenheid": "megajoule per jaar"},
    ]}
    d = dossier.dossier(v, {})
    exemplaren = [s for s in d["signalen"] if s["regel"] == "meerdere_grenswaarden"]
    assert len(exemplaren) == 2, "beide eenheidsgroepen moeten hier een eigen signaal opleveren"
    beweringen = {s["bewering"] for s in exemplaren}
    assert len(beweringen) == 2, f"de twee eenheidsgroepen delen hun bewering: {beweringen}"
    assert any("megajoule per dag" in b for b in beweringen)
    assert any("megajoule per jaar" in b for b in beweringen)


@pytest.mark.live
def test_geen_twee_signalen_in_een_dossier_delen_dezelfde_bewering_op_het_echte_register():
    """Het vangnet dat telt: de twee fixture-tests hierboven bewaken het patroon op verzonnen
    data, maar de live-bug bij Tata Steel zat in een combinatie die geen fixture toevallig
    bouwde. Doorloopt alle 69 echte vergunningen (`SmwkAtlasConnector`, net als
    `test_toezicht_live.py`) en faalt luid zodra één dossier twee signalen met dezelfde bewering
    draagt -- geen context nodig, want het gevonden geval (`meerdere_grenswaarden`) is een
    papierregel."""
    from leefomgevinglab.connectors.smwk_atlas import SmwkAtlasConnector

    aquo_csv = "/mnt/nvme/geluidsmeter/data/external/wkp/aquo_Parameter.csv"
    ref = aquo_mod.laad(aquo_csv)
    if not ref.get("beschikbaar"):
        pytest.skip(f"geen Aquo-domeintabel op {aquo_csv}; haal hem op (zie aquo.py)")

    with tempfile.TemporaryDirectory() as td:
        c = SmwkAtlasConnector(cache_dir=td)
        ruw = c.vergunningen_bij_punt(170000.0, 390000.0, straal_m=250000)
    register = register_mod.voorbereid(ruw)

    fouten = []
    for v in register:
        verrijkt = aquo_mod.verrijk(v, ref)
        d = dossier.dossier(verrijkt, {})
        beweringen = [s["bewering"] for s in d["signalen"]]
        if len(beweringen) != len(set(beweringen)):
            dubbel = sorted({b for b in beweringen if beweringen.count(b) > 1})
            fouten.append((v.get("naam"), v.get("kenmerk"), dubbel))

    assert not fouten, f"dossiers met een dubbele bewering op het echte register: {fouten}"


def test_grondslag_en_zekerheid_komen_uit_de_bestaande_vocabulaires():
    """Geen tweede vocabulaire: elke `grondslag` moet in `maaskaart.GRONDSLAG` staan en elke
    `zekerheid` in `lozingsmodel.ZEKERHEDEN`."""
    d = dossier.dossier(VESTIGING_MET_ALLES, CONTEXT_MET_ALLES)
    for s in d["signalen"]:
        assert s["grondslag"] in GRONDSLAG, s
        assert s["zekerheid"] in ZEKERHEDEN, s


def test_signaal_zonder_bewijs_krijgt_zekerheid_ontbreekt():
    """`geen_geldigheidsduur` levert altijd een lege `bewijs`-lijst (zie `signalen.py`) -- geen
    bewijs is zelf de zwakste zekerheid, ongeacht wat een regel-tabel anders zou zeggen."""
    d = dossier.dossier(VESTIGING_MET_ALLES, CONTEXT_MET_ALLES)
    geen_geldigheidsduur = [s for s in d["signalen"] if s["regel"] == "geen_geldigheidsduur"]
    assert len(geen_geldigheidsduur) == 1
    assert geen_geldigheidsduur[0]["bewijs"] == []
    assert geen_geldigheidsduur[0]["zekerheid"] == "ontbreekt"


def test_norm_overschreden_bovenstrooms_is_ruimtelijk_en_afgeleid():
    """Dit signaal koppelt via de positie van het waterlichaam in de stroomvolgorde -- geen
    gedeelde code, geen naamgok: `ruimtelijk`, net als een coördinaatkoppeling in `maaskaart`."""
    d = dossier.dossier(VESTIGING_MET_ALLES, CONTEXT_MET_ALLES)
    s = next(s for s in d["signalen"] if s["regel"] == "norm_overschreden_bovenstrooms")
    assert s["grondslag"] == "ruimtelijk"
    assert s["zekerheid"] == "afgeleid"


def test_vergunning_niet_te_vinden_is_geen_koppeling_en_ontbreekt():
    """Het bewijs ís de afwezigheid van identificerende velden -- er is dus niets om de
    vergunning mee terug te vinden, en dat is zelf de zekerheid."""
    d = dossier.dossier(VESTIGING_MET_ALLES, CONTEXT_MET_ALLES)
    s = next(s for s in d["signalen"] if s["regel"] == "vergunning_niet_te_vinden")
    assert s["grondslag"] == "geen"
    assert s["zekerheid"] == "ontbreekt"


def test_signaal_1_kan_twee_keer_voorkomen_en_elk_exemplaar_krijgt_zijn_herkomst():
    """Taak 2: `geen_onafhankelijke_meting` vuurt per Aquo-code. Deel B mag daar niet van
    uitgaan dat er precies één signaal per regel is."""
    d = dossier.dossier(VESTIGING_MET_ALLES, CONTEXT_MET_ALLES)
    exemplaren = [s for s in d["signalen"] if s["regel"] == "geen_onafhankelijke_meting"]
    assert len(exemplaren) == 2
    for s in exemplaren:
        assert s["grondslag"] == "code"
        assert s["zekerheid"] == "uit de bron"


def test_elke_regel_in_de_catalogus_heeft_een_herkomst():
    """`_HERKOMST_PER_REGEL` moet exact `signalen.DREMPELS` dekken -- mist er een regel, dan valt
    deel B stil terug op een `KeyError` zodra die regel voor het eerst vuurt."""
    assert set(dossier._HERKOMST_PER_REGEL) == set(signalen.DREMPELS)


def test_elke_grondslag_in_de_herkomsttabel_bestaat_in_maaskaart_grondslag():
    """Geen tweede vocabulaire naast `maaskaart.GRONDSLAG`."""
    grondslagen = {grondslag for grondslag, _ in dossier._HERKOMST_PER_REGEL.values()}
    assert grondslagen <= set(GRONDSLAG)


def test_elke_regel_in_de_catalogus_heeft_een_wat_te_doen():
    """Geen enkele regel mag zonder -- anders mist deel B het veld stil zodra die regel vuurt."""
    for regel in signalen.REGELS:
        assert regel.id in dossier._WAT_TE_DOEN_PER_REGEL
        assert dossier._WAT_TE_DOEN_PER_REGEL[regel.id].strip()


# -- Deel B: telling -------------------------------------------------------------------------

def test_telling_is_afgeleid_en_verandert_met_de_signalen():
    """Geen getal wordt getypt: minder voorschriften -> minder signalen -> andere telling."""
    d_vol = dossier.dossier(VESTIGING_MET_ALLES, CONTEXT_MET_ALLES)
    assert d_vol["telling"]["aantal_signalen"] == len(d_vol["signalen"])
    assert d_vol["telling"]["aantal_voorschriften"] == len(VESTIGING_MET_ALLES["voorschriften"])
    assert sum(d_vol["telling"]["per_zwaarte"].values()) == d_vol["telling"]["aantal_signalen"]
    assert sum(d_vol["telling"]["per_regel"].values()) == d_vol["telling"]["aantal_signalen"]

    # Geen signalen vraagt meer dan lege voorschriften: zonder kenmerk/url/besluitdatum vuurt
    # `vergunning_niet_te_vinden` juist wél (zie hieronder), dus die drie moeten gevuld zijn.
    kaal = {"naam": "Leeg", "kenmerk": "K1", "url": "https://x", "besluitdatum": "2020-01-01",
            "voorschriften": []}
    d_kaal = dossier.dossier(kaal, {})
    assert d_kaal["telling"]["aantal_signalen"] == 0
    assert d_kaal["telling"]["aantal_voorschriften"] == 0
    assert d_kaal["telling"]["per_zwaarte"] == {"hoog": 0, "midden": 0, "laag": 0}
    assert d_kaal["telling"]["per_regel"] == {}


def test_telling_per_regel_telt_signaal_1_twee_keer():
    d = dossier.dossier(VESTIGING_MET_ALLES, CONTEXT_MET_ALLES)
    assert d["telling"]["per_regel"]["geen_onafhankelijke_meting"] == 2


# -- Deel B: voorbehouden ---------------------------------------------------------------------

def test_voorbehoud_bij_ontbrekende_contextsleutels():
    d = dossier.dossier({"voorschriften": []}, {})
    tekst = " ".join(d["voorbehouden"])
    assert "gemeten_codes" in tekst
    assert "waterlichaam" in tekst
    assert "register_codes" in tekst
    assert "stoffen_met_norm" in tekst


def test_voorbehoud_ontbreekt_niet_meer_zodra_de_contextsleutel_gevuld_is():
    context = {"gemeten_codes": set(), "waterlichaam": "NL91BM", "register_codes": set(),
               "stoffen_met_norm": {"Zn"}}
    d = dossier.dossier({"voorschriften": []}, context)
    tekst = " ".join(d["voorbehouden"])
    assert "gemeten_codes" not in tekst
    assert "register_codes" not in tekst
    assert "stoffen_met_norm" not in tekst


def test_runlog_draagt_uitgezet_en_stappen_ook_zonder_een_draaiende_crew():
    """Sinds taak 6b bekabeld (R14): `dossier()` geeft nooit meer `None` terug voor deel D, ook
    niet zonder een echte `Runlog` -- `uitgezet` komt rechtstreeks uit `uit`, en `stappen` blijft
    dan gewoon leeg in plaats van het hele deel D af te schaffen."""
    d = dossier.dossier({"voorschriften": []}, {})
    assert d["runlog"] == {"uitgezet": [], "stappen": []}
    d_uit = dossier.dossier({"voorschriften": []}, {}, uit={"uitlegger"})
    assert d_uit["runlog"]["uitgezet"] == ["uitlegger"]
    assert d_uit["runlog"]["stappen"] == []


def test_een_uitgezette_agent_staat_vooraan_in_de_voorbehouden():
    """Vooruitlopend op taak 6b (`test_een_uitgezette_agent_staat_als_uitgezet_in_het_dossier`,
    ledger): die taak verwacht dat deze zin er al staat op index 0, en bouwt alleen de
    `runlog`-kant erbij. Eigen woordkeuze, geen "overtreding"-achtige taal."""
    d = dossier.dossier({"voorschriften": []}, {}, uit={"uitlegger"})
    assert "uitlegger stond uit" in d["voorbehouden"][0]


def test_meerdere_uitgezette_agents_staan_allebei_in_dezelfde_voorbehoudzin():
    d = dossier.dossier({"voorschriften": []}, {}, uit={"uitlegger", "vraagsteller"})
    assert "uitlegger" in d["voorbehouden"][0]
    assert "vraagsteller" in d["voorbehouden"][0]
    assert "stonden uit" in d["voorbehouden"][0]


def test_zonder_uitgezette_agents_begint_voorbehouden_niet_met_die_zin():
    d = dossier.dossier({"voorschriften": []}, {})
    assert "stond uit" not in d["voorbehouden"][0]
    assert "stonden uit" not in d["voorbehouden"][0]


# -- De harde taalregel, ook op het dossier zelf --------------------------------------------

def test_het_dossier_is_nooit_een_vaststelling():
    """Dezelfde taalregel als `signalen.py` (`test_een_signaal_is_nooit_een_vaststelling`), hier
    toegepast op de hele dossiertekst: de kaart, elk signaalveld en de voorbehouden."""
    d = dossier.dossier(VESTIGING_MET_ALLES, CONTEXT_MET_ALLES, uit={"uitlegger"})
    stukken = [str(v["waarde"]) for v in d["kaart"].values()]
    for s in d["signalen"]:
        stukken += [s["signaal"], s["grondslag"], s["zekerheid"], s["wat_te_doen"]]
    stukken += d["voorbehouden"]
    tekst = " ".join(stukken).lower()
    for verboden in _VERBODEN:
        assert verboden not in tekst, verboden


def test_het_gerenderde_werkblad_is_ook_nooit_een_vaststelling(tmp_path):
    """Fix-ronde 1, bevinding 1 (Important): de vorige test toetst alleen wat `dossier()`
    teruggeeft. `rapport.py` schrijft daarnaast zelf teksten de cel in die niet uit `dossier()`
    komen -- met name `signalen.DREMPELS[regel_id][1]` ("omvang betekent"). Verandert die string
    ooit in een vaststelling, dan zou de test hierboven dat niet merken: hij heeft `DREMPELS` nooit
    gezien.

    Dit scant daarom het **geschreven bestand**, niet de invoer ervan: elke cel van elk blad, plus
    de bladnamen zelf. `VESTIGING_MET_ALLES`/`CONTEXT_MET_ALLES` laat signaal 1 twee keer vuren,
    dus dit raakt meerdere bladen, niet toevallig het eerste."""
    d = dossier.dossier(VESTIGING_MET_ALLES, CONTEXT_MET_ALLES, uit={"uitlegger"})
    pad = tmp_path / "taalregel.xlsx"
    rapport.schrijf(d, str(pad))

    wb = load_workbook(str(pad))
    assert len(wb.sheetnames) > 1, "anders toetst dit maar één blad, niet de herhaling van signaal 1"

    gevonden = []
    for naam in wb.sheetnames:
        gevonden.append(naam)
        ws = wb[naam]
        for rij in ws.iter_rows(values_only=True):
            for cel in rij:
                if cel is not None:
                    gevonden.append(str(cel))

    tekst = " ".join(gevonden).lower()
    for verboden in _VERBODEN:
        assert verboden not in tekst, f"'{verboden}' staat in het gerenderde werkblad"


# -- Deel C: het rapport ----------------------------------------------------------------------

def test_het_rapport_heeft_een_blad_per_signaal_en_neemt_de_bronrijen_mee(tmp_path):
    """Brief, stap 3."""
    d = dossier.dossier(VESTIGING_MET_ALLES, CONTEXT_MET_ALLES)
    pad = tmp_path / "dossier.xlsx"
    uit = rapport.schrijf(d, str(pad))

    assert uit == str(pad)
    assert pad.exists()

    wb = load_workbook(str(pad))
    assert len(wb.sheetnames) == len(d["signalen"]) == 11
    assert len(set(wb.sheetnames)) == len(wb.sheetnames), "signaal 1 komt twee keer voor"
    for naam in wb.sheetnames:
        assert len(naam) <= 31
        assert not set(naam) & set(":\\/?*[]")

    # Het eerste signaal (hoogste zwaarte) draagt zijn bewijs terug te vinden op zijn eigen blad.
    eerste = d["signalen"][0]
    ws = wb[wb.sheetnames[0]]
    rijen = [tuple(r) for r in ws.iter_rows(values_only=True)]
    assert any(rij[0] == "signaal" and rij[1] == eerste["signaal"] for rij in rijen)
    if eerste["bewijs"]:
        eerste_bewijswaarde = next(iter(eerste["bewijs"][0].values()))
        platte_tekst = [cel for rij in rijen for cel in rij]
        assert eerste_bewijswaarde in platte_tekst or str(eerste_bewijswaarde) in [
            str(c) for c in platte_tekst]


def test_een_signaal_zonder_bewijs_krijgt_toch_een_leesbaar_blad(tmp_path):
    """`geen_geldigheidsduur` heeft een lege `bewijs`-lijst -- dat mag het rapport niet laten
    crashen, en het blad moet zeggen waaróm er geen bronrijen staan."""
    d = dossier.dossier(VESTIGING_MET_ALLES, CONTEXT_MET_ALLES)
    pad = tmp_path / "dossier.xlsx"
    rapport.schrijf(d, str(pad))
    wb = load_workbook(str(pad))

    geldigheid_index = next(i for i, s in enumerate(d["signalen"])
                             if s["regel"] == "geen_geldigheidsduur")
    ws = wb[wb.sheetnames[geldigheid_index]]
    tekst = " ".join(str(cel) for rij in ws.iter_rows(values_only=True) for cel in rij
                      if cel is not None)
    assert "geen afzonderlijke bronrijen" in tekst.lower()


def test_een_dossier_zonder_signalen_geeft_toch_een_bestand(tmp_path):
    vestiging = {"naam": "Schoon dossier", "kenmerk": "K1", "url": "https://x",
                 "besluitdatum": "2020-01-01", "voorschriften": []}
    d = dossier.dossier(vestiging, {})
    assert d["signalen"] == []
    pad = tmp_path / "leeg.xlsx"
    rapport.schrijf(d, str(pad))
    wb = load_workbook(str(pad))
    assert wb.sheetnames == ["Geen signalen"]


def test_coordinaten_in_bewijs_breken_het_rapport_niet(tmp_path):
    """Een echt Atlas-voorschrift draagt `rd: [x, y]` -- een lijst, die openpyxl niet als
    celwaarde accepteert. Dit mag geen `TypeError` geven."""
    vestiging = {"naam": "Met coordinaat", "kenmerk": None,
                 "voorschriften": [
                     {"parameter": "Zink", "waarde": 0.5, "eenheid": "milligram per liter",
                      "bemonstering": "Steekmonster", "rd": [170000.0, 390000.0]},
                 ]}
    d = dossier.dossier(vestiging, {})
    assert d["signalen"], "dit voorschrift moet minstens signaal 9 opleveren"
    pad = tmp_path / "coordinaat.xlsx"
    rapport.schrijf(d, str(pad))  # mag niet raisen
    assert pad.exists()


def test_rapport_schrijft_naar_tmp_path_nooit_naar_de_repo_of_nvme(tmp_path):
    """Huisregel: geen schrijfactie buiten `tmp_path` in een gewone test."""
    d = dossier.dossier({"voorschriften": []}, {})
    pad = tmp_path / "onderweg" / "dossier.xlsx"
    teruggegeven = rapport.schrijf(d, str(pad))
    assert teruggegeven == str(pad)
    assert pad.exists()
