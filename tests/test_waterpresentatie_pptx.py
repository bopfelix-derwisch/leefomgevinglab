"""De PowerPoint: komt hij uit dezelfde bron, en staat alles op de dia?

Deze tests bouwen een echt bestand in een tijdelijke map. Dat is traag genoeg om op te vallen en
snel genoeg om elke keer te draaien, en het is de enige manier om te zien of een beeldtype
zonder tekenfunctie stilzwijgend van de dia valt.
"""
import importlib.util
from pathlib import Path

import pytest

from leefomgevinglab.usecases import waterpresentatie as wp

_SCRIPT = Path(__file__).parent.parent / "scripts" / "19_bouw_waterpresentatie_pptx.py"
pytest.importorskip("pptx", reason="python-pptx niet geïnstalleerd")
_spec = importlib.util.spec_from_file_location("pptx_bouwer", _SCRIPT)
pb = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(pb)


@pytest.fixture(scope="module")
def deck(tmp_path_factory):
    uit = tmp_path_factory.mktemp("ppt") / "waterdossier.pptx"
    pb.bouw(uit)
    from pptx import Presentation
    return Presentation(str(uit))


def test_er_is_een_titeldia_plus_een_dia_per_onderdeel(deck):
    assert len(deck.slides) == len(wp.DIAS) + 1


def test_de_dias_staan_op_zestien_bij_negen(deck):
    """4:3 op een moderne beamer laat zwarte balken zien; dit is geen detail op een demo."""
    assert (deck.slide_width, deck.slide_height) == (12192000, 6858000)


def test_elke_dia_draagt_haar_spreektekst_als_notitie(deck):
    """In de presentatiemodus hoort de tekst op het scherm van de spreker, niet op de beamer."""
    for dia, bron in zip(list(deck.slides)[1:], wp.DIAS):
        notitie = dia.notes_slide.notes_text_frame.text
        assert bron["spreektekst"] in notitie, f"dia {bron['nr']}"
        assert f"[{bron['seconden']} seconden]" in notitie


def test_titel_kernpunten_en_bron_staan_op_de_dia(deck):
    for dia, bron in zip(list(deck.slides)[1:], wp.DIAS):
        tekst = "\n".join(s.text_frame.text for s in dia.shapes if s.has_text_frame)
        assert bron["titel"] in tekst, f"dia {bron['nr']}: titel ontbreekt"
        for k in bron["kern"]:
            assert k in tekst, f"dia {bron['nr']}: kernpunt ontbreekt"
        assert bron["bron"] in tekst and bron["link"] in tekst


def test_elk_beeldtype_heeft_een_tekenfunctie():
    """Een onbekend type levert een lege dia op; dat mag niet ongemerkt gebeuren."""
    gebruikt = {d["beeld"]["soort"] for d in wp.DIAS}
    assert gebruikt <= set(pb.BEELDEN), f"geen tekenfunctie voor {gebruikt - set(pb.BEELDEN)}"


def test_elke_dia_heeft_ook_echt_een_beeld_gekregen(deck):
    """Alleen tekst en een lege onderhelft is geen dia maar een notitie."""
    for dia, bron in zip(list(deck.slides)[1:], wp.DIAS):
        onder = [s for s in dia.shapes if s.top is not None and s.top >= pb.BEELD_TOP
                 and s.height < pb.BEELD_HOOG]
        assert len(onder) >= 2, f"dia {bron['nr']} heeft geen beeld onder de kernpunten"


def test_de_tekstblokken_raken_het_beeld_niet(deck):
    """Dit ging in de eerste versie mis: een vierde kernpunt zakte in de plaat."""
    assert pb.KERN_TOP + pb.KERN_HOOG <= pb.BEELD_TOP
    assert pb.TITEL_TOP + pb.TITEL_HOOG <= pb.KERN_TOP
    assert pb.BEELD_TOP + pb.BEELD_HOOG <= 6050000, "het beeld loopt in de voettekst"


def test_niets_valt_van_de_dia(deck):
    """Balklabels liepen eerst rechts van de dia af."""
    for i, dia in enumerate(deck.slides):
        for s in dia.shapes:
            if s.left is None or s.width is None:
                continue
            assert s.left >= 0, f"dia {i}: vorm begint links van de dia"
            assert s.left + s.width <= deck.slide_width + 10000, \
                f"dia {i}: vorm loopt rechts van de dia af"


def test_de_kennisgraaf_zit_in_de_presentatie():
    """De graaf hoort in het verhaal, niet alleen op een eigen pagina."""
    graafdias = [d for d in wp.DIAS if d["deel"] == "De kennisgraaf"]
    assert len(graafdias) == 2
    assert all(d["link"] == "/kennisgraaf" for d in graafdias)
    tekst = " ".join(" ".join(d["kern"]) + " " + d["spreektekst"] for d in graafdias)
    assert "CAS" in tekst and "ingetrokken" in tekst


# --- het bestand ophalen ---------------------------------------------------------------------

def _client(monkeypatch, pad=None):
    from fastapi.testclient import TestClient

    from leefomgevinglab.geluidsmeter.api import app
    cfg = {"leefomgevinglab": {"waterpresentatie": {"pptx_pad": str(pad)}}} if pad else {}
    monkeypatch.setattr("leefomgevinglab.geluidsmeter.api._config", cfg, raising=False)
    return TestClient(app)


def test_het_pptx_is_op_te_halen(monkeypatch, tmp_path):
    uit = tmp_path / "deck.pptx"
    pb.bouw(uit)
    r = _client(monkeypatch, uit).get("/waterpresentatie.pptx")
    assert r.status_code == 200
    assert "presentationml" in r.headers["content-type"]
    assert r.content[:2] == b"PK", "een pptx is een zip"


def test_een_ontbrekend_bestand_zegt_hoe_je_het_bouwt(monkeypatch, tmp_path):
    r = _client(monkeypatch, tmp_path / "bestaat-niet.pptx").get("/waterpresentatie.pptx")
    assert r.status_code == 404
    assert "scripts/19" in r.json()["detail"]


def test_de_pagina_biedt_de_download_aan(monkeypatch):
    h = _client(monkeypatch).get("/waterpresentatie").text
    assert "/waterpresentatie.pptx" in h


def test_geen_dia_draagt_meer_kernpunten_dan_het_blok_aankan():
    """Twee keer ging dit mis -- bij vier bullets, en daarna opnieuw bij vijf."""
    for d in wp.DIAS:
        assert len(d["kern"]) <= pb.MAX_KERN, \
            f"dia {d['nr']} heeft {len(d['kern'])} kernpunten, het blok draagt er {pb.MAX_KERN}"


def test_het_beeld_past_tussen_de_kernpunten_en_de_voettekst():
    assert pb.BEELD_TOP >= pb.KERN_TOP + pb.KERN_HOOG
    assert pb.BEELD_TOP + pb.BEELD_HOOG <= pb.VOET_TOP
    assert pb.BEELD_HOOG > 1_500_000, "een beeldvlak van niets is geen beeld"


def test_het_pptx_wordt_niet_blind_gecachet(monkeypatch, tmp_path):
    """Cloudflare cachete dit bestand vier uur op zijn extensie, en serveerde daardoor een
    presentatie van de dag ervoor terwijl de site de nieuwe toonde. Dat is echt gebeurd."""
    uit = tmp_path / "deck.pptx"
    pb.bouw(uit)
    r = _client(monkeypatch, uit).get("/waterpresentatie.pptx")
    assert "no-cache" in r.headers.get("cache-control", "")


def test_de_download_url_draagt_de_versie(monkeypatch, tmp_path):
    """Een nieuwe versie moet een nieuwe cache-sleutel krijgen, niet alleen nieuwe bytes."""
    uit = tmp_path / "deck.pptx"
    pb.bouw(uit)
    d = _client(monkeypatch, uit).get("/api/waterpresentatie").json()
    assert d["pptx"]["url"].startswith("/waterpresentatie.pptx?v=")
    assert d["pptx"]["bytes"] == uit.stat().st_size
    assert d["pptx"]["gebouwd_op"]


def test_zonder_bestand_blijft_de_rest_van_het_antwoord_heel(monkeypatch, tmp_path):
    d = _client(monkeypatch, tmp_path / "weg.pptx").get("/api/waterpresentatie").json()
    assert d["pptx"] is None
    assert d["aantal"] == len(wp.DIAS), "de presentatie zelf hangt niet aan het pptx"


def test_de_kale_url_verwijst_naar_de_versie_van_vandaag(monkeypatch, tmp_path):
    """Zodat een gedeelde link nooit een presentatie van gisteren oplevert."""
    uit = tmp_path / "deck.pptx"
    pb.bouw(uit)
    r = _client(monkeypatch, uit).get("/waterpresentatie.pptx", follow_redirects=False)
    assert r.status_code == 302
    assert r.headers["location"] == f"/waterpresentatie.pptx?v={int(uit.stat().st_mtime)}"


def test_een_verouderde_versie_in_de_url_verwijst_door(monkeypatch, tmp_path):
    uit = tmp_path / "deck.pptx"
    pb.bouw(uit)
    r = _client(monkeypatch, uit).get("/waterpresentatie.pptx?v=1", follow_redirects=False)
    assert r.status_code == 302


def test_de_kale_url_levert_na_de_doorverwijzing_gewoon_het_bestand(monkeypatch, tmp_path):
    uit = tmp_path / "deck.pptx"
    pb.bouw(uit)
    r = _client(monkeypatch, uit).get("/waterpresentatie.pptx")
    assert r.status_code == 200 and r.content[:2] == b"PK"


def test_geen_tekst_in_een_stappenvak_loopt_over():
    """Drie keer liep hier een tekst uit zijn kader, telkens pas zichtbaar na het renderen.

    De schatting is ruw -- python-pptx weet niet hoe PowerPoint afbreekt -- maar grove overloop
    hoort niet pas op de beamer op te vallen.
    """
    from pptx.util import Emu

    for d in wp.DIAS:
        if d["beeld"]["soort"] != "stappen":
            continue
        stappen = d["beeld"]["stappen"]
        n = len(stappen)
        breed = int((Emu(12192000) - 2 * pb.MARGE) / n) - 140000 - 380000
        naam_hoog = 232000 * (3 if n >= 4 else 2)
        sub_hoog = pb.BEELD_HOOG - (560000 + naam_hoog) - 60000
        for s in stappen:
            assert pb.past_in_vak(s["naam"], breed, naam_hoog, 13), \
                f"dia {d['nr']}: naam te lang — {s['naam']}"
            assert pb.past_in_vak(s["sub"], breed, sub_hoog, 10.5), \
                f"dia {d['nr']}: subtekst te lang — {s['sub'][:60]}"
