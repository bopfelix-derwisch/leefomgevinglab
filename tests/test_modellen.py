"""De vergelijking van drie modellen: kloppen de tellingen, en blijft het onderscheid staan?

De kern van deze pagina is één stelling — een informatiemodel is geen datamodel — en die
stelling valt zodra de drie lagen als varianten van elkaar worden gepresenteerd. Deze tests
bewaken dat onderscheid, en dat elk getal op de pagina uit een bron komt die genoemd wordt.
"""
import pytest
from fastapi.testclient import TestClient

from leefomgevinglab.geluidsmeter.api import app
from leefomgevinglab.usecases import modellen as mo


@pytest.fixture(scope="module")
def a():
    return mo.analyse()


def _client(monkeypatch):
    monkeypatch.setattr("leefomgevinglab.geluidsmeter.api._config", {}, raising=False)
    return TestClient(app)


# --- het onderscheid ------------------------------------------------------------------------

def test_elke_laag_is_van_een_eigen_soort(a):
    """Zodra twee lagen dezelfde soort krijgen, is de stelling van deze pagina weg."""
    soorten = [l["soort"] for l in a["lagen"]]
    assert len(set(soorten)) == len(soorten)
    for verwacht in ("conceptueel", "informatiemodel", "technische uitwerking", "interface",
                     "fysiek"):
        assert verwacht in soorten, verwacht


def test_elke_laag_zegt_ook_waar_zij_niets_over_zegt(a):
    """Dát is wat een laag van een andere soort onderscheidt, niet wat zij wél vastlegt."""
    for l in a["lagen"]:
        assert l["legt_vast"] and l["zegt_niets_over"] and l["vorm"] and l["toetsbaar"]


def test_de_normatieve_lagen_zijn_niet_toetsbaar_en_de_technische_wel(a):
    """Het scherpste gevolg van het onderscheid dat deze pagina maakt.

    Een informatiemodel is normatief maar niet uitvoerbaar; een berichtschema is uitvoerbaar
    maar niet normatief. Wie ze als één ding behandelt, verliest juist dat verschil.
    """
    per_id = {l["id"]: l["toetsbaar"] for l in a["lagen"]}
    assert per_id["cim"].startswith("nee")
    assert per_id["imev"].startswith("nee"), \
        "het informatiemodel zelf is geen bestand waar een bericht tegen valideert"
    for i in ("schema", "api", "gir"):
        assert per_id[i].startswith("ja"), i


def test_elke_laag_heeft_een_bron_met_houder_en_versie(a):
    for l in a["lagen"]:
        b = a["bronnen"][l["id"]]
        assert b["naam"] and b["houder"] and b["versie"] and b["voluit"]


# --- vier bestanden, drie soorten ding -------------------------------------------------------

def test_elk_artefact_zegt_wat_het_is_en_wat_het_niet_is(a):
    """`niet` is het informatieve veld: wat een bestand niet is, is wat men erin zoekt."""
    for x in a["artefacten"]:
        assert x["bestand"] and x["soort"] and x["wat"] and x["vindplaats"] and x["omvang"]
        assert x["niet"], f"{x['bestand']} zonder 'niet' nodigt uit tot de verwarring"


def test_het_informatiemodel_en_het_berichtschema_hebben_verschillende_houders(a):
    """Dit is waarom ze niet één ding zijn: ze worden door verschillende partijen beheerd."""
    per = {x["soort"]: x for x in a["artefacten"]}
    assert "Geonovum" in per["model"]["houder"]
    assert "RWS" in per["berichtschema"]["houder"]
    assert per["model"]["houder"] != per["berichtschema"]["houder"]
    assert "geostandaarden" in per["model"]["vindplaats"]
    assert "rev-portaal" in per["berichtschema"]["vindplaats"]


def test_het_model_heeft_geen_bestand_en_dus_geen_verwijzingen(a):
    per = {x["soort"]: x for x in a["artefacten"]}
    assert per["model"]["verwijzingen"] is None, \
        "een begrippenkader wordt niet door een OpenAPI aangeroepen"


def test_de_api_specificatie_draagt_zelf_geen_inhoudelijk_schema(a):
    """Zij verwijst; zij definieert niet. Daarom kan zij het model niet vervangen."""
    assert a["telling"]["api_eigen_schemas"] == 0
    api = next(x for x in a["artefacten"] if x["soort"] == "API-specificatie")
    assert "geen enkel inhoudelijk schema" in api["niet"]


def test_de_envelop_krijgt_meer_verwijzingen_dan_de_inhoud(a):
    """Een OpenAPI is overwegend verpakking -- dat is het argument van de hele sectie."""
    t = a["telling"]
    assert t["refs_envelop"] > t["refs_inhoud"] * 4
    assert t["refs_envelop"] + t["refs_inhoud"] < t["refs_totaal"], \
        "de gedeelde geotypes horen ook in het totaal"
    assert mo.verwijzingen()["aandeel_envelop"] > 0.5


def test_de_tellingen_noemen_het_artefact_waar_zij_uit_komen(a):
    """De oude sleutels heetten imev_*; dat schreef schema- en API-cijfers aan het model toe."""
    t = a["telling"]
    assert not [k for k in t if k.startswith("imev_")], \
        "een telling die 'imev_' heet, legt een schema- of API-cijfer bij het informatiemodel"
    for k in ("schema_definities", "schema_objecttypen", "api_paden", "api_resourcefamilies"):
        assert k in t, k


def test_geen_enkele_tekst_schrijft_de_api_keuze_aan_het_informatiemodel_toe(a):
    """De fout die deze pagina aanwijst, één niveau lager toegepast op haar eigen tekst.

    "IMEV ontsluit twee objecttypen" is onwaar; de API-specificatie doet dat. Een los woord
    IMEV naast 'ontsluit', 'resource', 'endpoint' of 'pad' is daarom een rode vlag.

    Geciteerde tekst blijft buiten de controle. De pagina citeert de foute formulering juist om
    haar aan te wijzen, en een vangnet dat een tegenvoorbeeld niet van een bewering kan
    onderscheiden, dwingt je de uitleg weg te laten.
    """
    import re
    zonder_citaat = lambda x: re.sub(r"['\u2018\u2019\u201c\u201d\"][^'\u2018\u2019\u201c\u201d\"]{0,120}"
                                    r"['\u2018\u2019\u201c\u201d\"]", " ", x)
    teksten = []
    for v in a["vertalingen"]:
        teksten += [v["imev"], v["les"]]
    for o in a["overlap"]:
        teksten += [o["imev"], o["waarom"]]
    for b in a["bevindingen"]:
        teksten.append(b["wat"])
    for x in a["artefacten"]:
        teksten += [x["wat"], x["niet"]]
    verdacht = re.compile(r"\bIMEV\b(?![\s-]*(?:3\.0|-stelsel|\(het))[^.]{0,40}"
                          r"(ontsluit|resourcefam|endpoint|paden\b)", re.I)
    for tekst in teksten:
        assert not verdacht.search(zonder_citaat(tekst)), \
            f"IMEV krijgt hier een API-eigenschap: {tekst[:120]}"


def test_het_vangnet_ziet_de_fout_die_het_moet_zien():
    """Anders is de vorige test een test die altijd slaagt."""
    import re
    verdacht = re.compile(r"\bIMEV\b(?![\s-]*(?:3\.0|-stelsel|\(het))[^.]{0,40}"
                          r"(ontsluit|resourcefam|endpoint|paden\b)", re.I)
    assert verdacht.search("IMEV ontsluit twee objecttypen, niet 88")
    assert verdacht.search("In IMEV zitten twintig paden")
    assert not verdacht.search("IMEV 3.0 kent 88 objecttypen")
    assert not verdacht.search("De API-specificatie ontsluit twee resourcefamilies")


# --- de vertalingen -------------------------------------------------------------------------

def test_elk_begrip_wordt_in_alle_drie_de_modellen_geplaatst(a):
    for v in a["vertalingen"]:
        assert v["begrip"] and v["cim"] and v["imev"] and v["gir"]
        assert v["les"], f"{v['begrip']} zonder les is een tabelrij zonder punt"


def test_de_vergunning_is_in_geen_van_beide_een_entiteit_maar_wel_in_een_een_gegeven(a):
    """Deze rij stond eerst fout op de pagina: IMEV zou de vergunning niet kennen.

    Natellen in het schema wees uit dat 44 objecttypen het vergunningnummer, de datum en de
    plicht als veld dragen. De bevinding is dus niet "het begrip ontbreekt in beide" maar de
    asymmetrie: IMEV bewaart de identificatie, GIR laat hem vallen. De test bewaakt dat de
    oude, te stellige formulering niet terugkomt.
    """
    v = next(x for x in a["vertalingen"] if "mag dit bedrijf" in x["begrip"])
    assert "komt niet voor" not in v["imev"], "de weerlegde bewering staat terug op de pagina"
    assert "basisVergunningNummer" in v["imev"]
    assert str(a["telling"]["schema_met_vergunningnummer"]) in v["imev"]
    assert "buiten scope" in v["gir"]


def test_bevoegd_gezag_is_in_gir_een_query_en_geen_relatie(a):
    v = next(x for x in a["vertalingen"] if "bevoegd gezag" in x["begrip"])
    assert "GEO-query" in v["gir"]
    assert "niet op historie" in v["les"] or "reproduceerbaar" in v["les"]


# --- de overlap tussen de twee registers ----------------------------------------------------

def test_elk_overlapbegrip_zegt_wat_beide_registers_ervan_vastleggen(a):
    for o in a["overlap"]:
        assert o["begrip"] and o["gir"] and o["imev"]
        assert o["waarom"], f"{o['begrip']} zonder onderbouwing is een oordeel zonder grond"


def test_joinbaarheid_is_een_van_drie_uitkomsten(a):
    """`deels` is geen `ja`: te verbinden via een tussentabel is geen gedeelde sleutel."""
    for o in a["overlap"]:
        assert o["join"] in ("ja", "deels", "nee"), o["begrip"]


def test_de_joinbare_begrippen_leunen_alle_op_een_basisregistratie(a):
    """Dit is de bevinding. Niets wat de twee registers zelf afspraken, verbindt ze."""
    buiten = ("KvK", "handelsregister", "BAG")
    joinbaar = [o for o in a["overlap"] if o["join"] == "ja"]
    assert joinbaar, "zonder joinbare begrippen is de analyse leeg"
    for o in joinbaar:
        tekst = o["gir"] + o["imev"] + o["waarom"]
        assert any(x in tekst for x in buiten), \
            f"{o['begrip']} heet joinbaar zonder sleutel van buiten te noemen"


def test_de_meeste_begrippen_zijn_niet_te_joinen(a):
    """Zou dit kantelen, dan is de boodschap van de sectie omgekeerd."""
    t = a["telling"]
    assert t["join_nee"] > t["join_ja"]
    assert t["join_ja"] + t["join_deels"] + t["join_nee"] == len(a["overlap"])


def test_bevoegd_gezag_is_in_beide_registers_iets_anders(a):
    o = next(x for x in a["overlap"] if "bevoegd gezag" in x["begrip"])
    assert o["join"] == "nee"
    assert "OIN" in o["gir"] and "enum" in o["imev"]
    # De twee GIR-artefacten doen het verschillend; "GIR" zonder meer is hier niet genoeg.
    # Het onderscheid tussen de twee GIR-artefacten staat nu in twee kolommen in plaats van in
    # één cel: het databasemodel lost bevoegdheid op als GEO-query, het informatiemodel draagt
    # een benoemde associatie. Beide kanten worden apart getoetst.
    assert "GEO-query" in o["gir"] and "niet uit een opgeslagen verband" in o["gir"]
    assert "heeft als " in o["gir_im"] and "bevoegd gezag" in o["gir_im"], (
        "het informatiemodel draagt de relatie wél -- dat hoort in die kolom te staan")


# --- GIR is ook meer dan één ding -------------------------------------------------------------

def test_elk_gir_artefact_zegt_wat_het_is_en_wat_het_niet_is(a):
    """Dezelfde eis als voor de IMEV-artefacten. Dat deze lijst er niet was, is de reden dat
    twee uitspraken over 'GIR' jarenlang als waar konden gelden terwijl ze alleen over het
    databasemodel klopten."""
    assert len(a["gir_artefacten"]) >= 2, "één artefact noemen is het probleem, niet de oplossing"
    for x in a["gir_artefacten"]:
        assert x["bestand"] and x["soort"] and x["wat"] and x["houder"] and x["omvang"]
        assert x["niet"], f"{x['bestand']} zonder 'niet' nodigt uit tot de verwarring"


def test_de_gir_artefacten_zijn_elk_van_een_andere_soort():
    """**Bob's correctie, en zij was terecht.** Ik noemde de aangeleverde set één
    "architectuurmodel". Maar de set is aangeleverd als *informatiemodellen*, en dat is ook wat
    laag 3 bevat: Enterprise Architect geeft die drie views het diagramtype `class` mee, tegenover
    `business`, `motivation` en `application` voor de tien andere. Drie UML-klassenmodellen met
    attributen, datatypen, multipliciteit en benoemde associaties zíjn een informatiemodel; ze
    een architectuurmodel noemen verschuift precies de soort die deze pagina uit elkaar houdt.

    Daarom nu drie artefacten van drie soorten: het informatiemodel, de architectuurviews
    eromheen, en het databasemodel."""
    soorten = {x["soort"] for x in mo.GIR_ARTEFACTEN}
    assert len(soorten) == len(mo.GIR_ARTEFACTEN), (
        "twee artefacten van dezelfde soort zou de scheiding zinloos maken")
    assert soorten == {"informatiemodel", "architectuurviews", "databasemodel"}, soorten


def test_gir_heeft_een_informatiemodel_en_staat_dus_niet_alleen_op_de_fysieke_laag(a):
    """Het schema van vijf lagen noemt per soort één voorbeeld, en zette GIR op 'fysiek'. Dat is
    het databasemodel. GIR heeft daarnáást een informatiemodel -- dezelfde soort als IMEV -- en
    juist die gelijkstelling 'GIR = fysiek' maakte dat twee uitspraken over het databasemodel
    konden doorgaan voor uitspraken over GIR."""
    assert any(x["soort"] == "informatiemodel" for x in a["gir_artefacten"]), (
        "zonder dit artefact leest de fysieke laag als 'GIR'")
    gir_laag = next(l for l in a["lagen"] if l["id"] == "gir")
    assert "databasemodel" in gir_laag["zegt_niets_over"], (
        "de laagrij moet zelf zeggen dat zij over het databasemodel gaat, niet over GIR")
    assert "informatiemodel" in gir_laag["zegt_niets_over"]


def test_geen_gir_artefact_belooft_een_publieke_url_die_er_niet_is(a):
    """Beide zijn aangeleverd, geen van beide staat publiek. Dat moet er staan, want de pagina
    mag niet suggereren dat een lezer het na kan kijken."""
    for x in a["gir_artefacten"]:
        assert "geen publieke URL" in x["vindplaats"], x["bestand"]


def test_de_vergunning_is_aan_beide_kanten_vastgelegd_maar_onvergelijkbaar(a):
    """**Deze test heette eerst `..._is_eenzijdig_vastgelegd` en bewaakte een onjuiste
    bewering.** De pagina zei dat GIR de vergunningidentificatie laat vallen; de
    GIR-informatiemodel (november 2023) draagt Omgevingsvergunning plus een Besluit met
    `Besluitidentificatie`. Het oude `assert "buiten scope" in o["gir"]` bleef na de
    correctie gewoon slagen -- de nieuwe tekst bevat die woorden óók, over het *databasemodel* --
    dus de test keurde de correctie goed zonder haar te zien. Precies het patroon dat dit
    project het meeste heeft gekost: groen om de verkeerde reden.

    Nu wordt de inhoudelijke positie gepind: beide kanten leggen een identificatie vast, uit
    twee stelsels, zonder crosswalk. Niet joinbaar, maar om een andere reden dan 'de ene kant
    heeft het niet'."""
    o = next(x for x in a["overlap"] if x["begrip"] == "De vergunning")
    assert o["join"] == "nee"
    assert "basisVergunningNummer" in o["imev"]
    # De identificatie staat in de informatiemodelkolom; de databasemodelkolom zegt terecht dat
    # zij daar buiten scope is. Sinds de vergelijking op gelijk niveau wordt getrokken, zijn dat
    # twee kolommen in plaats van één cel met beide verhalen erin.
    assert "Besluitidentificatie" in o["gir_im"], (
        "het informatiemodel draagt de identificatie wél -- dat hoort in die kolom")
    assert "buiten scope" in o["gir"], "en het databasemodel niet"
    # Op de bewering, niet op een los woord: de tekst mág "eenzijdig" noemen om te zeggen dat
    # zij dat juist níet is -- en die zelfcorrectie is waardevol voor een lezer. Wat hier moet
    # staan is de reden waarom het dán niet joint.
    assert "onvergelijkbaar" in o["waarom"]
    assert "crosswalk" in o["waarom"], "zeg waarom het dán niet joint"


def test_imev_eist_een_reden_bij_een_ontbrekende_waarde_en_gir_niet(a):
    """De zekerheid-per-veld uit het waterdossier, hier als standaard aangetroffen."""
    o = next(x for x in a["overlap"] if "ontbrekende waarde" in x["begrip"])
    assert "geenWaardeReden" in o["imev"]
    assert o["gir"].strip() == "NULL"
    for reden in ("gegevenInTransitie", "nietVanToepassing", "waardeOnbekend"):
        assert reden in o["imev"], reden


def test_de_pagina_houdt_de_drie_soorten_apart(monkeypatch):
    h = _client(monkeypatch).get("/modellen").text
    for woord in ("informatiemodel", "berichtschema", "API-specificatie"):
        assert woord in h, woord
    assert 'id="artefacten"' in h


def test_de_pagina_toont_de_overlap_en_de_joinbaarheid(monkeypatch):
    h = _client(monkeypatch).get("/modellen").text
    assert 'id="overlap"' in h and 'id="joinbalk"' in h
    assert "joinen" in h, "de sectie moet de vraag benoemen die zij beantwoordt"


# --- de bevindingen en hun herkomst ----------------------------------------------------------

def test_elke_bevinding_noemt_waar_zij_op_berust(a):
    for b in a["bevindingen"]:
        assert b["kop"] and b["wat"] and b["bron"]


def test_de_analyse_scheidt_wat_nagekeken_is_van_wat_uit_een_document_komt(a):
    h = a["herkomst"]
    assert h["live"] and h["document"]
    assert any("rev-portaal" in x for x in h["live"])
    assert any("ICTU" in x or "niet publiek" in x for x in h["document"])


def test_het_gir_document_wordt_niet_als_publieke_bron_gepresenteerd(a):
    """Het is een intern document; een URL suggereren die er niet is, is een valse vindplaats."""
    assert a["bronnen"]["gir"]["url"] is None


def test_elke_bron_wijst_naar_de_partij_die_haar_beheert(a):
    """Het informatiemodel staat bij Geonovum, de bestanden bij RWS. Dat is het onderscheid.

    Deze test verving een oudere die van `bronnen["imev"]` een rev-portaal-URL eiste. Die eis
    was precies de verwarring: zij maakte het model een bestand van het REV.
    """
    assert a["bronnen"]["imev"]["url"].startswith("https://definities.geostandaarden.nl/")
    for sleutel in ("schema", "api"):
        assert a["bronnen"][sleutel]["url"].startswith("https://rev-portaal.nl/oas/")
    assert "Geonovum" in a["bronnen"]["imev"]["houder"]


# --- de tellingen ----------------------------------------------------------------------------

def test_de_indeling_van_het_schema_dekt_elke_definitie(a):
    """De som moet exact het totaal zijn. Een restpost zou een stil gat in de telling zijn."""
    t = a["telling"]
    assert sum(mo.indeling().values()) == t["schema_definities"]
    for naam, _, aantal in mo.INDELING:
        assert t[f"schema_{naam}"] == aantal > 0, naam


def test_elke_bak_in_de_indeling_zegt_op_welke_regel_zij_berust(a):
    """Zonder die regel is de indeling een lijstje en niet na te rekenen."""
    for naam, regel, _ in mo.INDELING:
        assert naam and regel and len(regel) > 20, naam


def test_de_api_ontsluit_minder_dan_het_schema_beschrijft(a):
    t = a["telling"]
    assert t["api_resourcefamilies"] < t["schema_objecttypen"], \
        "dat de API er twee ontsluit en het schema 79 beschrijft, is de bevinding"


def test_de_velden_met_een_vergunningnummer_passen_in_de_objecttypen(a):
    t = a["telling"]
    assert t["schema_met_vergunningnummer"] < t["schema_objecttypen"], \
        "44 van de 79 -- niet van de 168, want hulptypen en enumeraties dragen geen velden"


def test_het_aantal_niet_gebouwde_tabellen_past_in_het_totaal(a):
    t = a["telling"]
    assert 0 < t["gir_niet_gebouwd"] < t["gir_tabellen"]


def test_de_tellingen_dekken_de_inhoud(a):
    t = a["telling"]
    assert t["lagen"] == len(a["lagen"])
    assert t["vertalingen"] == len(a["vertalingen"])
    assert t["bevindingen"] == len(a["bevindingen"])
    assert t["overlap"] == len(a["overlap"])
    assert t["artefacten"] == len(a["artefacten"])


# --- de pagina --------------------------------------------------------------------------------

def test_de_pagina_geeft_200(monkeypatch):
    r = _client(monkeypatch).get("/modellen")
    assert r.status_code == 200
    assert "/api/modellen" in r.text


def test_de_pagina_staat_niet_in_het_waterdossier(monkeypatch):
    """Dit is een VTH-analyse; de waternav hoort er niet op."""
    h = _client(monkeypatch).get("/modellen").text
    assert 'class="waternav"' not in h
    assert "__WATERNAV__" not in h


def test_de_vth_paginas_wijzen_naar_de_analyse(monkeypatch):
    c = _client(monkeypatch)
    for pad in ("/vth", "/vth-bronnen"):
        assert "/modellen" in c.get(pad).text, f"{pad} linkt niet naar de analyse"


def test_het_eindpunt_levert_de_hele_analyse(monkeypatch):
    d = _client(monkeypatch).get("/api/modellen").json()
    for sleutel in ("bronnen", "artefacten", "lagen", "vertalingen", "overlap", "bevindingen",
                    "herkomst", "telling"):
        assert d[sleutel], sleutel


def test_de_pagina_toont_de_gir_artefacten_en_noemt_haar_eigen_correctie(monkeypatch):
    """De GIR-artefacten moeten op de pagina staan, niet alleen in de API: het hele punt is dat
    een lézer kan zien over welk artefact een uitspraak gaat. En de pagina zegt dat zij zelf
    twee dingen fout had -- dat is geen zelfkastijding maar informatie: wie de oude versie heeft
    gelezen, draagt nu een onjuiste overtuiging mee."""
    r = _client(monkeypatch).get("/modellen")
    assert 'id="girartefacten"' in r.text
    # Op witruimte genormaliseerd: de HTML is op leeslengte afgebroken, dus een zoekterm met
    # enkele spaties matcht niets -- dezelfde valkuil als bij de proza-bewaking op /toezicht.
    import re as _re
    plat = _re.sub(r"\s+", " ", r.text)
    assert "waar over het databasemodel en onwaar over het informatiemodel" in plat
    assert "GIR heeft óók een <b>informatiemodel</b>" in plat, (
        "de pagina moet zeggen dát GIR een informatiemodel heeft -- dat is de correctie")
    # De namen van de artefacten komen uit de API, niet uit de HTML.
    assert "databasemodel (ICTU" not in r.text, "de artefactnamen horen uit /api/modellen te komen"


# --- de vergelijking op niveau informatiemodel -------------------------------------------------

def test_elke_overlaprij_noemt_ook_het_gir_informatiemodel(a):
    """**De vergelijking doorgetrokken op gelijk niveau.** Deze tabel zette IMEV tegenover het
    GIR-*databasemodel*: een berichtschema tegenover tabellen. De module zei dat zelf al in haar
    docstring ("een GIR-kolom en een IMEV-veld zijn niet dezelfde soort ding"), maar deed het
    toch, omdat de informatiemodelkant ontbrak. Nu staat per begrip ook wat het
    GIR-informatiemodel vastlegt -- dezelfde laag als IMEV."""
    for o in a["overlap"]:
        assert o.get("gir_im"), f"{o['begrip']} mist de informatiemodelkant"
        assert len(o["gir_im"]) > 30, f"{o['begrip']}: te kort om iets te zeggen"


def test_de_informatiemodelkant_noemt_klassen_en_niet_tabellen(a):
    """De twee kolommen moeten van elkaar te onderscheiden zijn: het informatiemodel spreekt in
    klassen en attributen, het databasemodel in reg_-tabellen. Lopen die door elkaar, dan is de
    scheiding alleen een kopje."""
    met_klasse = [o for o in a["overlap"] if "klasse" in o["gir_im"]]
    assert len(met_klasse) >= 8, "het informatiemodel hoort in klassen te spreken"
    for o in a["overlap"]:
        assert "reg_" not in o["gir_im"], (
            f"{o['begrip']}: een reg_-tabel in de informatiemodelkolom -- dat is de andere laag")


def test_twee_begrippen_lopen_tussen_de_twee_gir_artefacten_uiteen(a):
    """Dát is wat het scheiden oplevert. De vergunning en de domino-relatie staan in het
    informatiemodel wél en in het databasemodel niet -- in het ene geval buiten scope, in het
    andere ontworpen maar nooit gebouwd."""
    vergunning = next(o for o in a["overlap"] if o["begrip"] == "De vergunning")
    assert "buiten scope" in vergunning["gir"]
    assert "informatiemodel" not in vergunning["gir"], (
        "de databasemodelkolom hoort alleen over het databasemodel te gaan -- anders is de "
        "scheiding in kolommen alleen een kopje")
    assert "Besluitidentificatie" in vergunning["gir_im"]
    domino = next(o for o in a["overlap"] if "Domino" in o["begrip"])
    assert "nooit gebouwd" in domino["gir"] or "geschrapt" in domino["gir"]
    assert "wél aanwezig" in domino["gir_im"]


def test_de_pagina_toont_drie_kanten_en_zegt_waarom_twee_ervan_gelijkwaardig_zijn(monkeypatch):
    import re as _re
    r = _client(monkeypatch).get("/modellen")
    plat = _re.sub(r"\s+", " ", r.text)
    assert "GIR 2.0 · informatiemodel" in plat
    assert "REV · informatiemodel + schema" in plat
    assert "GIR 2.0 · databasemodel" in plat
    assert "de eerste twee zijn van gelijke soort" in plat
    assert "o.gir_im" in r.text, "de kolom hoort uit de API te komen"


def test_het_joinoordeel_gaat_over_de_registers_en_niet_over_de_modellen(monkeypatch):
    """Een gedeeld begrip is nog geen gedeelde sleutel. Zonder die zin kan een lezer denken dat
    de nieuwe kolom het joinoordeel verandert -- en dat doet zij niet."""
    import re as _re
    plat = _re.sub(r"\s+", " ", _client(monkeypatch).get("/modellen").text)
    assert "gaat over de registers, niet over de modellen" in plat
