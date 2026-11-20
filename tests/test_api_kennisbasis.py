"""De routes `/kennisbasis`, `/api/kennisbasis` en `/api/kennisbasis/zoek`.

De pagina haalt *alles* uit de API en typt zelf geen bevinding, geen citaat en geen bronnaam.
Zou zij dat wel doen, dan kan de plaat iets anders tonen dan het dossier zegt -- en dan heeft de
citaatcontrole geen waarde meer, want zij controleert het model en niet de HTML.

De interactietests onderaan pinnen de drie fouten vast die deze vorm van plaat in dit lab eerder
heeft gemaakt: een pointer-capture die alle klikken opslokt, een hoek die de verkeerde kant op
kantelt, en een stapel die zichzelf niet inpast.
"""
import re

from fastapi.testclient import TestClient

from leefomgevinglab.geluidsmeter import api as api_mod
from leefomgevinglab.kennisbasis import bevindingen as bv
from leefomgevinglab.kennisbasis import bronnen as br


def _client():
    return TestClient(api_mod.app)


def _plat(html: str) -> str:
    """Witruimte genormaliseerd -- de HTML breekt op leeslengte af, dus een zoekterm met enkele
    spaties matcht anders niets. Zie `tests/test_api_maquette.py`, waar dit eerder misging."""
    return re.sub(r"\s+", " ", html)


# -- De API -------------------------------------------------------------------------------------

def test_de_api_levert_het_hele_dossier():
    d = _client().get("/api/kennisbasis").json()
    for sleutel in ("dossier", "bronnen", "themas", "verbanden", "onbesproken", "herkomst",
                    "bouwstenen", "geschikt", "graafvragen", "graaf", "gezondheid", "telling"):
        assert d[sleutel], sleutel
    assert len(d["bronnen"]) == len(br.BRONNEN)
    assert d["telling"]["bevindingen"] == len(bv.BEVINDINGEN)


def test_de_route_raakt_geen_bron_en_is_dus_snel():
    """Een kennisbasis over vier pdf's mag niet afhangen van de bereikbaarheid van een dienst.
    De citaatcontrole leest van NVMe, de rest komt uit de code."""
    import time
    t0 = time.perf_counter()
    assert _client().get("/api/kennisbasis").status_code == 200
    assert time.perf_counter() - t0 < 2.5


def test_de_api_meldt_de_gezondheid_van_de_kennisbasis_zelf():
    """Dit dossier gaat over rapporten die zeggen dat niemand weet wat er is. Een pagina die dat
    behandelt en zelf niet zegt waar haar getallen op rusten, doet precies waar zij over
    klaagt."""
    g = _client().get("/api/kennisbasis").json()["gezondheid"]
    assert set(g) >= {"citaten_gecontroleerd", "citaten", "citaten_fout",
                      "documenten_op_schijf", "documenten", "index"}
    assert g["documenten"] == len(br.BRONNEN)


def test_elke_graafvraag_komt_met_haar_query_en_haar_uitkomst_mee():
    """De pagina toont de SPARQL achter een uitkomst. Zonder die query is de uitkomst een
    bewering, en dan had er net zo goed een getal kunnen staan."""
    for v in _client().get("/api/kennisbasis").json()["graafvragen"]:
        assert v["vraag"] and v["waarom"] and v["sparql"] and v["rijen"]
        assert "SELECT" in v["sparql"].upper()


# -- De zoekroute ---------------------------------------------------------------------------------

def test_zoeken_zonder_index_meldt_dat_in_plaats_van_niets_te_vinden(monkeypatch):
    """Een lege trefferlijst leest als 'hierover staat niets in de rapporten'. Dat is iets heel
    anders dan 'de index is niet gebouwd', en het verschil moet in het antwoord staan."""
    monkeypatch.setattr(api_mod.kennisbasis_index, "laad", lambda: None)
    d = _client().post("/api/kennisbasis/zoek", json={"vraag": "iets"}).json()
    assert d["passages"] == [] and d["antwoord"] is None
    assert "index" in d["reden"] and "23_bouw_kennisbasis" in d["reden"]


def test_zoeken_zonder_taalmodel_levert_nog_steeds_de_passages(monkeypatch):
    """De passages zijn het product; de samenvatting is een laag erbovenop. Valt het taalmodel
    weg, dan hoort de kennisbasis niet mee te vallen."""
    class NepStore:
        chunks = [{}]

        def search(self, q, k):
            return [{"text": "een passage", "bron": "ilt", "bron_titel": "De basis moet op orde",
                     "uitgever": "ILT", "pagina": 5, "deel": 0,
                     "url": "https://example.invalid#page=5", "score": 0.9}]

    monkeypatch.setattr(api_mod.kennisbasis_index, "laad", lambda: NepStore())
    monkeypatch.setattr(api_mod, "_rag_embed_fn", lambda: (lambda teksten: [[0.0, 1.0]]))
    d = _client().post("/api/kennisbasis/zoek",
                       json={"vraag": "iets", "samenvatten": False}).json()
    assert len(d["passages"]) == 1
    assert d["passages"][0]["pagina"] == 5 and d["antwoord"] is None
    assert d["reden"] is None


def test_een_passage_draagt_altijd_haar_vindplaats(monkeypatch):
    """Zonder bron en pagina is een opgehaald fragment niet na te lezen, en dan is de index een
    zoekmachine zonder bronvermelding."""
    from leefomgevinglab.kennisbasis import index as ix
    store = ix.laad()
    if store is None:
        import pytest
        pytest.skip("index niet gebouwd; scripts/23_bouw_kennisbasis.py --index")
    for c in store.chunks[:50]:
        assert c["bron"] in {b["id"] for b in br.BRONNEN}
        assert c["pagina"] >= 1 and c["url"].endswith(f"#page={c['pagina']}")


# -- De pagina ------------------------------------------------------------------------------------

def test_de_pagina_haalt_haar_inhoud_uit_de_api_en_typt_niets_zelf():
    """Geen citaat, geen bevindingskop en geen brontitel in de HTML. Zou dat wel zo zijn, dan
    kan de plaat iets anders tonen dan het dossier zegt en controleert de citaattest de
    verkeerde tekst."""
    r = _client().get("/kennisbasis")
    assert r.status_code == 200
    assert "/api/kennisbasis" in r.text
    plat = _plat(r.text)
    for b in bv.BEVINDINGEN:
        assert b["citaat"] not in plat, f"{b['id']}: het citaat hoort uit de API te komen"
        assert b["kop"] not in plat, f"{b['id']}: de kop hoort uit de API te komen"
    for bron in br.BRONNEN:
        assert bron["url"] not in r.text, f"{bron['id']}: de URL hoort uit de API te komen"
    for t in bv.THEMAS:
        assert t["naam"] not in plat


def test_de_pagina_legt_uit_wat_de_blokjes_zijn():
    """Dat was de vraag waarvoor deze pagina gemaakt is: de blokjes van de maquette verder
    toelichten."""
    plat = _plat(_client().get("/kennisbasis").text)
    assert "wat betekenen de blokjes" in plat.lower()
    assert "/maquette" in plat
    assert "gestippeld" in plat.lower(), (
        "een blokje zonder bevinding hoort herkenbaar te zijn")


def test_de_pagina_noemt_zichzelf_geen_samenvatting():
    """Het onderscheid waar deze kennisbasis op rust: een citaat met vindplaats is iets anders
    dan een samenvatting."""
    plat = _plat(_client().get("/kennisbasis").text)
    assert "geen samenvatting" in plat.lower()
    assert "citaat" in plat.lower() and "pagina" in plat.lower()


def test_de_homepagina_draagt_een_ingang_naar_de_kennisbasis():
    r = _client().get("/")
    assert "/kennisbasis" in r.text
    assert "ennisbasis leefomgeving" in r.text


def test_de_maquette_en_de_kennisbasis_wijzen_naar_elkaar():
    """De plaat van de kennisbasis is dezelfde stapel als die van de maquette; wie de ene leest
    hoort de andere te kunnen vinden."""
    assert "/maquette" in _client().get("/kennisbasis").text


# -- De plaat: de fouten die deze vorm eerder maakte ------------------------------------------------

def test_een_klik_op_een_blokje_wordt_niet_door_de_scene_afgevangen():
    """**De bug die op `/maquette` alle velden stil brak.** De scène riep bij elke `pointerdown`
    meteen `setPointerCapture` aan om te kunnen slepen. Met een actieve pointer-capture gaat óók
    het `click`-event naar het vangende element, en reageerde niets meer -- zonder foutmelding.
    Te zien aan de twee eigenschappen die de reparatie uitmaken: vangen pas na een sleepdrempel,
    en een pointerdown op iets klikbaars start geen sleep."""
    r = _client().get("/kennisbasis")
    pointerdown = r.text.split('addEventListener("pointerdown"')[1].split("});")[0]
    assert "setPointerCapture" not in pointerdown
    assert ".tegel" in pointerdown and "return" in pointerdown
    assert "DREMPEL" in r.text


def test_de_stapel_past_zichzelf_in_plaats_van_op_een_vaste_hoogte_te_rekenen():
    """Hoe hoog de stapel wordt hangt af van het aantal blokjes per laag en van de vensterbreedte.
    Met een getuned getal viel de bovenste laag buiten beeld zodra er een bevinding bijkwam."""
    r = _client().get("/kennisbasis")
    assert "clientHeight" in r.text and "schaal" in r.text
    assert "offsetHeight" in r.text, "de plaathoogtes horen gemeten te worden, niet geschat"


def test_er_is_geen_stand_van_boven_want_de_platen_staan_rechtop():
    """Op `/maquette` werkt 'van boven' omdat de bovenste laag daar als kaart ligt. Hier staan
    de platen rechtop, dus van boven kijk je tegen hun randen en is er niets te lezen -- dat is
    in een browser nagekeken, niet aangenomen."""
    r = _client().get("/kennisbasis")
    assert 'data-blik="opzij"' in r.text
    assert 'data-blik="boven"' not in r.text


def test_de_plaat_is_zonder_muis_te_bedienen():
    r = _client().get("/kennisbasis")
    assert "ArrowLeft" in r.text and "ArrowUp" in r.text
    assert 'tabindex="0"' in r.text
    assert "focus-visible" in r.text
    assert "prefers-reduced-motion" in r.text


def test_een_blik_en_een_blokje_zijn_deelbaar_via_de_url():
    r = _client().get("/kennisbasis")
    assert "URLSearchParams" in r.text and "blokje" in r.text
    for vraag in ("?blik=opzij", "?blokje=gebied/bedrijf"):
        assert _client().get(f"/kennisbasis{vraag}").status_code == 200


def test_de_pagina_laadt_geen_3d_bibliotheek():
    """CSS-transforms in plaats van WebGL: de blokjes blijven echte knoppen, dus leesbaar,
    klikbaar en met het toetsenbord te bereiken."""
    r = _client().get("/kennisbasis")
    assert "<script src=" not in r.text
    assert "preserve-3d" in r.text and "perspective" in r.text
