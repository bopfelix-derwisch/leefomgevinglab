"""De kennisbasis leefomgeving, dossier *bevindingen VTH* -- het model achter `/kennisbasis`.

**De zwaarste test staat bovenaan en hij is het bestaansrecht van deze module.** Een pagina die
beweert wat vier rapporten zeggen, is zo goed als de controleerbaarheid van die bewering. Elke
bevinding draagt een letterlijk citaat en een paginanummer; `test_elk_citaat_staat_op_de_pagina`
houdt die twee tegen de werkelijke tekstextractie. Gaat iemand een citaat "verduidelijken", of
verschuift een paginanummer bij een nieuwe editie, dan valt dat hier om in plaats van stilletjes
op de pagina te blijven staan.

De tweede groep tests bewaakt de scheiding **bron / lab**: wat de documenten zeggen tegenover wat
dit lab eruit leest. Die scheiding is de reden dat deze pagina geen mening is, en zij staat op
drie plekken (de herkomsttabel, het `van`-veld in de graaf, en de aparte `LABLIJN`) -- dus ook op
drie plekken bewaakt.
"""
import pytest

from leefomgevinglab.kennisbasis import bevindingen as bv
from leefomgevinglab.kennisbasis import bronnen as br
from leefomgevinglab.kennisbasis import dossier as ds
from leefomgevinglab.kennisbasis import graaf as kg
from leefomgevinglab.kennisbasis import index as ix
from leefomgevinglab.kennisbasis import vindplaats as vp
from leefomgevinglab.geluidsmeter import api as api_mod


def _tekst_aanwezig() -> bool:
    return all(br.pad(b, "tekst").exists() for b in br.BRONNEN)


# -- De vindplaats: het hart van de kennisbasis -------------------------------------------------

@pytest.mark.skipif(not _tekst_aanwezig(),
                    reason="tekstextractie ontbreekt; maak haar met "
                           "scripts/23_bouw_kennisbasis.py --extract")
def test_elk_citaat_staat_op_de_pagina_die_de_bevinding_noemt():
    """**Het verschil tussen 'dit rapport zegt' en 'zo lees ik dit rapport'.**

    Dit is geen formaliteit: bij het bouwen stonden 16 van de 42 citaten op een andere pagina dan
    opgeschreven, omdat het gedrukte paginanummer in een rapport niet gelijk is aan de
    pdf-pagina -- en juist de pdf-pagina is wat `#page=N` in de deeplink opent. Twee citaten
    stonden nergens, omdat zij over een afbreekstreepje liepen. Zonder deze test had de pagina
    42 keurige verwijzingen gedragen waarvan er 16 naar de verkeerde bladzijde gingen."""
    fout = vp.controleer_alles(bv.BEVINDINGEN)
    assert not fout, "\n".join(
        f"{f['id']}: niet op pagina {f['pagina']} van {f['bron']}; "
        f"wel op {f['gevonden_op'] or 'geen enkele pagina'} -- {f['citaat'][:70]}"
        for f in fout)


@pytest.mark.skipif(not _tekst_aanwezig(), reason="tekstextractie ontbreekt")
def test_de_controle_keurt_een_verkeerde_pagina_af():
    """**Mutatietest op de bewaking zelf.** Een controle die alles goedkeurt is erger dan geen
    controle, want zij wekt vertrouwen. Hier wordt een bestaand citaat bewust op de verkeerde
    pagina gezet; de controle hoort dat te zien én te melden waar het wél staat."""
    echt = bv.BEVINDINGEN[0]
    uitslag = vp.controleer(echt["bron"], echt["citaat"], echt["pagina"] + 7)
    assert not uitslag["klopt"]
    assert echt["pagina"] in uitslag["gevonden_op"], (
        "de controle hoort de echte pagina te noemen; anders moet je zelf gaan zoeken")


@pytest.mark.skipif(not _tekst_aanwezig(), reason="tekstextractie ontbreekt")
def test_de_controle_keurt_een_verzonnen_citaat_af():
    bron = bv.BEVINDINGEN[0]["bron"]
    uitslag = vp.controleer(bron, "dit staat in geen van deze rapporten geschreven", 1)
    assert not uitslag["klopt"] and uitslag["gevonden_op"] == []


def test_ligaturen_en_witruimte_worden_gelijkgetrokken():
    """`pdftotext` levert `ﬁ`, `ﬀ` en `ﬂ` als één teken, en `-layout` behoudt de kolomuitlijning.
    Zonder die normalisatie matcht geen enkel getypt citaat van meer dan een halve regel --
    precies de reden dat deze functie bestaat."""
    assert vp.normaliseer("de eﬀecten\n   van  de\nﬁguur") == "de effecten van de figuur"
    assert vp.normaliseer("'aan­halen'") == "'aanhalen'"


def test_een_ontbrekend_document_valt_luid_om_in_plaats_van_leeg_terug_te_geven():
    """Een lege paginalijst zou elke citaatcontrole laten slagen omdat er niets te controleren
    viel -- het ergste soort groene test."""
    with pytest.raises(KeyError):
        vp.paginas("bestaat-niet")


def test_een_deeplink_draagt_de_pagina():
    link = vp.deeplink("ilt", 16)
    assert link.startswith(br.OP_ID["ilt"]["url"]) and link.endswith("#page=16")


# -- De bronnen ---------------------------------------------------------------------------------

def test_elke_bron_draagt_een_publieke_vindplaats_en_een_reden():
    """Een document zonder publieke vindplaats hoort niet in deze kennisbasis: dan is het niet
    na te lezen en mag het hier ook niet staan. En zonder `waarom` is niet te zeggen waarom
    juist deze vier."""
    assert len(br.BRONNEN) >= 4
    for b in br.BRONNEN:
        assert b["url"].startswith("https://"), b["id"]
        assert b["waarom"] and b["uitgever"] and b["kenmerk"] and b["gericht_aan"], b["id"]
        assert b["datum"].count("-") == 2, b["id"]


def test_de_bron_id_s_zijn_uniek():
    ids = [b["id"] for b in br.BRONNEN]
    assert len(ids) == len(set(ids))


def test_de_brondata_staat_buiten_de_repo():
    """`CLAUDE.md`: brondata leeft op NVMe, nooit in de repo. Vier rapporten zijn samen ruim 14
    MB; die in git zetten maakt van een kennisbasis een archiefkast."""
    assert str(br.BASIS).startswith("/mnt/nvme/"), br.BASIS
    assert "workspaces" not in str(br.BASIS)


@pytest.mark.skipif(not _tekst_aanwezig(), reason="tekstextractie ontbreekt")
def test_het_aantal_paginas_wordt_afgeleid_en_niet_getypt():
    """Op dat getal rust de deeplink. Zou het als constante in de code staan, dan kan het uit de
    pas lopen met het bestand waarnaar het verwijst."""
    for b in br.BRONNEN:
        n = br.paginas(b)
        assert n and n > 1, b["id"]
        assert max(x["pagina"] for x in bv.BEVINDINGEN if x["bron"] == b["id"]) <= n


# -- De bevindingen en hun aanknoping -----------------------------------------------------------

def test_de_bevinding_id_s_zijn_uniek():
    ids = [b["id"] for b in bv.BEVINDINGEN]
    assert len(ids) == len(set(ids)), [i for i in ids if ids.count(i) > 1]


def test_elke_bevinding_is_volledig_en_gebruikt_het_vaste_vocabulaire():
    bron_ids = {b["id"] for b in br.BRONNEN}
    thema_ids = {t["id"] for t in bv.THEMAS}
    for b in bv.BEVINDINGEN:
        assert b["bron"] in bron_ids, b["id"]
        assert b["soort"] in bv.SOORTEN, (b["id"], b["soort"])
        assert b["thema"] in thema_ids, (b["id"], b["thema"])
        assert b["kop"] and b["wat"] and b["citaat"] and b["adressant"], b["id"]
        assert isinstance(b["pagina"], int) and b["pagina"] >= 1, b["id"]


def test_elk_blokje_bestaat_in_de_maquette_en_draagt_zijn_laag():
    """De aanknoping aan `/maquette` is wat "wat betekent dat blokje" beantwoordbaar maakt. Een
    verwijzing naar een blokje dat daar niet bestaat, breekt die belofte stil."""
    bestaand = {e["sleutel"] for e in bv.blokjes()}
    for b in bv.BEVINDINGEN:
        assert b["blokje"] in bestaand, (b["id"], b["blokje"])
        assert "/" in b["blokje"], (b["id"], "de sleutel hoort laag/id te zijn")
    for t in bv.THEMAS:
        assert t["blokje"] in bestaand, (t["id"], t["blokje"])


def test_de_blokjesleutel_draagt_de_laag_omdat_een_id_niet_uniek_is():
    """**De fout die deze sleutel heeft afgedwongen.** `verantwoorden` bestaat twee keer in de
    maquette: als proces ("Beleid kijkt of het werkt") en als handeling ("Laten zien hoe het
    gaat"). Een opzoeking op `id` liet er stil één van wegvallen -- vier bevindingen hingen aan
    het verkeerde blokje en de dekking kwam één tegel te laag uit. Deze test pint vast dat die
    twee uit elkaar te houden zijn."""
    sleutels = {e["sleutel"] for e in bv.blokjes()}
    assert "processen/verantwoorden" in sleutels and "handelingen/verantwoorden" in sleutels
    namen = {e["sleutel"]: (e.get("naam") or e.get("object")) for e in bv.blokjes()}
    assert namen["processen/verantwoorden"] != namen["handelingen/verantwoorden"]
    assert len(sleutels) == len(bv.blokjes()), "de sleutel hoort uniek te zijn"


def test_de_blokjes_zijn_de_tegels_en_niet_de_stromen_en_routes():
    """`eindbeeld_stelsel._alle_elementen()` draagt ook stromen, kanten en routes mee --
    richtingen en paden, geen plekken. Zou `onbesproken()` daarop rekenen, dan leek de dekking
    van dit dossier de helft van wat zij is."""
    from leefomgevinglab.usecases import eindbeeld_stelsel as eb
    assert len(bv.blokjes()) < len(eb._alle_elementen())
    sleutels = {e["sleutel"] for e in bv.blokjes()}
    for stroom in eb.STROMEN:
        assert not any(s.endswith("/" + stroom["id"]) for s in sleutels), stroom["id"]


def test_elke_doorkijk_wijst_naar_een_bestaande_route():
    """Elk blokje belooft dat deze plek in dit lab op echte data draait. Een dode link breekt die
    belofte stiller dan een foutmelding."""
    routes = {r.path for r in api_mod.app.routes if hasattr(r, "path")}
    dood = sorted({b["waar"] for b in bv.bevindingen() if b["waar"] not in routes})
    assert not dood, dood
    dood_lab = sorted({l["waar"] for l in bv.LABLIJN if l["waar"] not in routes})
    assert not dood_lab, dood_lab


def test_elk_thema_wordt_door_minstens_een_bevinding_gedragen():
    """Een thema zonder bevinding is een kop zonder inhoud -- en suggereert dat de rapporten er
    iets over zeggen."""
    for t in bv.per_thema():
        assert t["bevindingen"], t["id"]
        assert t["vraag"].endswith("?"), t["id"]


def test_de_dekking_telt_op():
    t = bv.telling()
    assert t["blokjes_met_bevinding"] + t["blokjes_onbesproken"] == t["blokjes"]
    assert t["blokjes_onbesproken"] > 0, (
        "als elk blokje een bevinding draagt, dekt het dossier het hele landschap -- dat doet "
        "het niet, en die suggestie wekken is erger dan het gat tonen")


def test_de_telling_klopt_met_de_lijsten():
    t = bv.telling()
    assert t["bevindingen"] == len(bv.BEVINDINGEN) == len(bv.bevindingen())
    assert t["themas"] == len(bv.THEMAS)
    assert t["verbanden"] == len(bv.VERBANDEN)
    assert sum(t["per_bron"].values()) == t["bevindingen"]
    assert sum(t["per_soort"].values()) == t["bevindingen"]
    assert t["lablijnen"] == len(bv.LABLIJN)


# -- De verbanden: de reden dat het een dossier is ----------------------------------------------

def test_elk_verband_verbindt_bestaande_bevindingen_met_een_bekende_relatie():
    ids = {b["id"] for b in bv.BEVINDINGEN}
    for v in bv.VERBANDEN:
        assert v["van"] in ids and v["naar"] in ids, v
        assert v["van"] != v["naar"], v
        assert v["relatie"] in bv.RELATIES, v
        assert v["wat"], v


def test_de_meeste_verbanden_lopen_over_bronnen_heen():
    """**Dit is de rechtvaardiging van het hele dossier.** Lopen alle verbanden binnen één
    rapport, dan voegt het samenbrengen van vier rapporten niets toe en had je ze los kunnen
    lezen."""
    t = bv.telling()
    assert t["verbanden_over_bronnen"] > t["verbanden"] / 2, (
        f"maar {t['verbanden_over_bronnen']} van de {t['verbanden']} verbanden raken twee "
        "verschillende rapporten")


def test_alle_vier_de_bronnen_doen_mee_aan_de_verbanden():
    betrokken = set()
    for v in bv.verbanden():
        betrokken.add(v["van_bron"])
        betrokken.add(v["naar_bron"])
    assert betrokken == {b["id"] for b in br.BRONNEN}, (
        "een bron die in geen enkel verband voorkomt, staat los in dit dossier")


# -- Bron en lezing gescheiden -------------------------------------------------------------------

def test_de_herkomsttabel_onderscheidt_bron_en_lab():
    soorten = {h["van"] for h in bv.HERKOMST}
    assert soorten == {"bron", "lab"}, (
        "alles 'bron' verbergt de eigen lezing, alles 'lab' poetst de documenten weg")
    for h in bv.HERKOMST:
        assert h["wat"] and h["bron"]


def test_de_indeling_en_de_verbanden_staan_als_lezing_van_dit_lab():
    """De thema-indeling en de knopen tussen bevindingen komen uit geen enkel document. Zouden ze
    als brongegeven doorgaan, dan leest een lezing van dit lab als vastgesteld beleid."""
    lab = " ".join(h["wat"] + " " + h["bron"] for h in bv.HERKOMST if h["van"] == "lab")
    assert "thema" in lab.lower()
    assert "verband" in lab.lower()
    assert "maquette" in lab.lower()


def test_de_lablijn_staat_apart_van_de_bevindingen():
    """Wat dit lab zelf op echte data meette, is geen bevinding uit een rapport. Het staat in een
    eigen lijst met een eigen herkomstregel, en draagt daarom geen citaat of pagina."""
    thema_ids = {t["id"] for t in bv.THEMAS}
    for l in bv.LABLIJN:
        assert l["thema"] in thema_ids, l
        assert l["wat"] and l["hoe"] and l["waar"]
        assert "citaat" not in l and "pagina" not in l


# -- De kennisgraaf -------------------------------------------------------------------------------

@pytest.fixture(scope="module")
def graaf():
    return kg.bouw()


def test_de_graaf_draagt_alles_uit_de_lijsten(graaf):
    t = kg.telling(graaf)
    assert t["bronnen"] == len(br.BRONNEN)
    assert t["bevindingen"] == len(bv.BEVINDINGEN)
    assert t["themas"] == len(bv.THEMAS)
    assert t["verbanden"] == len(bv.VERBANDEN)
    assert t["labmetingen"] == len(bv.LABLIJN)
    assert t["triples"] > t["bevindingen"] * 5


def test_elke_bewering_in_de_graaf_zegt_of_zij_bron_of_lab_is(graaf):
    """**De eigenschap waarvoor hier een graaf staat.** Zonder `k:van` per knooppunt is "geef me
    alleen wat de rapporten zelf zeggen" geen vraag maar een discipline bij het lezen."""
    from rdflib import RDF
    for klasse in (kg.K.Bron, kg.K.Bevinding, kg.K.Thema, kg.K.Verband, kg.K.Labmeting):
        for s in graaf.subjects(RDF.type, klasse):
            vanen = list(graaf.objects(s, kg.K.van))
            assert len(vanen) == 1, (klasse, s)
            assert str(vanen[0]) in (kg.BRON, kg.LAB), (s, vanen)


def test_een_bevinding_komt_uit_een_bron_en_een_verband_is_van_het_lab(graaf):
    from rdflib import RDF
    for s in graaf.subjects(RDF.type, kg.K.Bevinding):
        assert str(next(graaf.objects(s, kg.K.van))) == kg.BRON
    for s in graaf.subjects(RDF.type, kg.K.Verband):
        assert str(next(graaf.objects(s, kg.K.van))) == kg.LAB


def test_elke_graafvraag_levert_rijen_op(graaf):
    """Een bevraagbare laag die alleen belooft, is geen laag. De pagina toont deze drie vragen
    mét hun uitkomst, dus moeten ze er een hebben."""
    for v in kg.VRAGEN:
        rijen = kg.stel(graaf, v["id"])
        assert rijen, v["id"]
        assert v["vraag"].endswith("?") and v["waarom"]


def test_elke_graafvraag_is_begrensd(graaf):
    """Dezelfde regel als op `/toezicht`: een query zonder `LIMIT` kan een pagina onleesbaar
    maken, en wat de lezer ziet mag niet afwijken van wat er is uitgevoerd."""
    for v in kg.VRAGEN:
        assert "LIMIT" in v["sparql"].upper(), v["id"]


def test_een_onbekende_graafvraag_valt_luid_om(graaf):
    """Een stil leeg antwoord leest als 'er is niets', en dat is iets anders dan 'die vraag
    bestaat niet'."""
    with pytest.raises(KeyError):
        kg.stel(graaf, "deze-vraag-bestaat-niet")


def test_de_graaf_wijst_het_blokje_aan_dat_de_meeste_rapporten_raakt(graaf):
    """De uitkomst die dit dossier oplevert: er is één plek in het eindbeeld waar alle vier de
    rapporten iets over zeggen. Zou dat er geen zijn, dan raken de bronnen elkaar nergens en is
    de plaat een toevallige verzameling."""
    rijen = kg.stel(graaf, "blokjes_meeste_bronnen")
    assert int(rijen[0]["bronnen"]) == len(br.BRONNEN), rijen[0]


# -- De index ---------------------------------------------------------------------------------

@pytest.mark.skipif(not _tekst_aanwezig(), reason="tekstextractie ontbreekt")
def test_elke_chunk_draagt_een_controleerbare_vindplaats():
    """Hierom wordt per pagina gechunkt in plaats van per vast aantal tekens: een chunk die over
    een paginagrens loopt kan niet eerlijk geciteerd worden."""
    chunks = ix.paginachunks("kabinet")
    assert chunks
    paginas = br.paginas(br.OP_ID["kabinet"])
    for c in chunks:
        assert 1 <= c["pagina"] <= paginas
        assert c["url"].endswith(f"#page={c['pagina']}")
        assert c["text"].strip() and "\f" not in c["text"]


@pytest.mark.skipif(not _tekst_aanwezig(), reason="tekstextractie ontbreekt")
def test_geen_chunk_is_te_lang_voor_de_embedding_server():
    """**De fout die de eerste indexbouw liet mislukken.** De grens is niet de contextgrens van
    het model (8192) maar de *fysieke batchgrens* van llama.cpp, standaard 512 tokens: één
    invoer daarboven geeft `HTTP 500 ... increase the physical batch size`. Met 1800 tekens
    Nederlandse rapporttekst gebeurde dat vanaf chunk 112."""
    assert ix.CHUNK_TEKENS <= 1200, (
        "boven ongeveer 1200 tekens komt een chunk over de 512-tokengrens van de "
        "embedding-server; verhoog dan ook --ubatch-size, maar die server deelt de IPLO-index")
    for c in ix.alle_chunks():
        assert len(c["text"]) <= ix.CHUNK_TEKENS, (c["bron"], c["pagina"], len(c["text"]))


@pytest.mark.skipif(not _tekst_aanwezig(), reason="tekstextractie ontbreekt")
def test_lege_paginas_komen_niet_in_de_index():
    """Een titelblad levert wel treffers op maar geen antwoord."""
    for c in ix.alle_chunks():
        assert len(c["text"]) >= ix.MINIMUM_TEKENS or c["deel"] > 0


def test_een_ontbrekende_index_meldt_dat_in_plaats_van_leeg_te_zijn():
    s = ix.status()
    assert set(s) >= {"gebouwd", "chunks"}
    if not s["gebouwd"]:
        assert s["chunks"] == 0
    else:
        assert s["chunks"] > 0 and sum(s["per_bron"].values()) == s["chunks"]


def test_de_index_staat_buiten_de_repo():
    assert ix.STORE_DIR.startswith("/mnt/nvme/")


def test_de_prompt_verbiedt_verzinnen_en_eist_een_vindplaats():
    """Een kennisbasis waarin het model uit zijn eigen gewichten praat, is geen kennisbasis."""
    p = ix.prompt("waarom?", [{"bron_titel": "X", "pagina": 3, "text": "y"}])
    assert "Verzin niets" in p
    assert "pagina" in p and "rapport" in p
    assert "[X, pagina 3]" in p


# -- Het dossier als geheel ---------------------------------------------------------------------

def test_de_gezondheid_liegt_niet_als_zij_niet_kan_controleren():
    """**De valkuil van een zelfrapporterende pagina.** Kan de citaatcontrole niet draaien omdat
    de tekstextractie ontbreekt, dan mag `citaten_fout: 0` niet als 'alles klopt' lezen. Daarom
    is er een apart veld dat zegt óf er gecontroleerd is."""
    g = ds.gezondheid()
    assert "citaten_gecontroleerd" in g
    if not g["citaten_gecontroleerd"]:
        assert g["citaten_reden"], "zeg dan waarom niet"
    else:
        assert g["citaten"] == len(bv.BEVINDINGEN)


def test_het_dossier_draagt_alles_wat_de_pagina_nodig_heeft():
    d = ds.dossier()
    for sleutel in ("dossier", "bronnen", "themas", "verbanden", "onbesproken", "herkomst",
                    "bouwstenen", "geschikt", "graafvragen", "graaf", "gezondheid", "telling"):
        assert d[sleutel], sleutel


def test_het_dossier_zegt_waarvoor_het_niet_geschikt_is():
    """Een instrument dat zijn eigen grens niet noemt, wordt buiten die grens gebruikt."""
    assert any(not g["ja"] for g in ds.GESCHIKT)
    assert any(g["ja"] for g in ds.GESCHIKT)


def test_elke_hergebruikte_bouwsteen_wijst_naar_een_bestaande_route():
    """De claim is dat dit op bestaande componenten draait. Een bouwsteen die naar niets wijst,
    maakt van die claim een praatje."""
    routes = {r.path for r in api_mod.app.routes if hasattr(r, "path")}
    for b in ds.BOUWSTENEN:
        assert b["waar"] in routes, b
        assert b["bestond"] and b["hier"]
