"""De presentatie: klopt de timing, en kloppen de cijfers nog met de POC eronder?

Het tweede is waar deze testset om begonnen is. Een dia blijft een getal vertellen lang nadat de
onderliggende pagina veranderd is, en dat merk je pas met een publiek erbij. Daarom wordt elk
kerncijfer hier tegen dezelfde voorberekende momentopname gehouden die `/kmg` en `/watermodel`
gebruiken. Ontbreekt dat bestand, dan slaan die tests over in plaats van vals alarm te geven —
op een machine zonder de NVMe-data is er niets te vergelijken.
"""
import json
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from leefomgevinglab.geluidsmeter.api import app
from leefomgevinglab.usecases import water_hub as wh
from leefomgevinglab.usecases import waterpresentatie as wp

MOMENTOPNAME = Path("/mnt/nvme/geluidsmeter/data/external/wkp/kmg_overzicht.json")


@pytest.fixture(scope="module")
def poc():
    if not MOMENTOPNAME.exists():
        pytest.skip(f"momentopname ontbreekt: {MOMENTOPNAME}")
    return json.loads(MOMENTOPNAME.read_text())


def _client(monkeypatch):
    monkeypatch.setattr("leefomgevinglab.geluidsmeter.api._config", {}, raising=False)
    return TestClient(app)


# --- timing -----------------------------------------------------------------------------

def test_de_presentatie_duurt_precies_tien_minuten():
    """Geen schatting maar een afspraak: de dia's lopen vanzelf door."""
    assert wp.duur_s() == wp.DUUR_S == 600


def test_elke_dia_krijgt_een_begintijd_die_op_de_vorige_aansluit():
    t = 0
    for d in wp.dias():
        assert d["start_s"] == t, f"dia {d['nr']} begint niet waar de vorige ophoudt"
        t += d["seconden"]
    assert t == 600


def test_geen_dia_vraagt_een_onhaalbaar_spreektempo():
    """Boven ongeveer 185 woorden per minuut wordt Nederlands voorlezen haasten.

    De ondergrens staat er ook: een dia die veertig seconden blijft staan met dertig woorden
    eronder laat een spreker in stilte wachten, en dat valt bij een demo net zo hard op.
    """
    for d in wp.DIAS:
        wpm = len(d["spreektekst"].split()) / (d["seconden"] / 60)
        assert 110 <= wpm <= 185, f"dia {d['nr']}: {wpm:.0f} woorden per minuut"


# --- vorm -------------------------------------------------------------------------------

def test_elke_dia_draagt_een_bron_en_een_vindplaats():
    """Een bewering zonder vindplaats hoort niet in een demo: na afloop wil iemand doorklikken."""
    for d in wp.DIAS:
        assert d["bron"], f"dia {d['nr']} noemt geen bron"
        assert d["link"].startswith("/"), f"dia {d['nr']} linkt niet naar een labpagina"


def test_elk_beeld_heeft_een_soort_die_de_pagina_kan_tekenen():
    getekend = {"lagen", "balken", "drieluik", "stappen", "chips", "rivier", "tijdlijn"}
    html = (Path(__file__).parent.parent / "src" / "leefomgevinglab" / "static"
            / "waterpresentatie.html").read_text()
    for soort in getekend:
        assert f"{soort}:" in html, f"de pagina kent geen tekenfunctie voor {soort}"
    for d in wp.DIAS:
        assert d["beeld"]["soort"] in getekend, f"dia {d['nr']}: onbekend beeldtype"


def test_de_nummering_loopt_door_en_de_kernpunten_blijven_leesbaar():
    assert [d["nr"] for d in wp.DIAS] == list(range(1, len(wp.DIAS) + 1))
    for d in wp.DIAS:
        assert 1 <= len(d["kern"]) <= 5, f"dia {d['nr']} heeft te veel of te weinig kernpunten"


# --- de cijfers, tegen de POC ------------------------------------------------------------

def test_de_voorschriftentelling_klopt_met_de_momentopname(poc):
    totaal = sum(p["model"]["totaal"] for p in poc["punten"])
    bruikbaar = sum(p["model"]["bruikbaar"] for p in poc["punten"])
    volledig = sum(p["model"]["volledig"] for p in poc["punten"])
    assert wp.CIJFERS["voorschriften_totaal"] == totaal
    assert wp.CIJFERS["voorschriften_bruikbaar"] == bruikbaar
    assert wp.CIJFERS["voorschriften_volledig"] == volledig == 0
    assert wp.CIJFERS["voorschriften_bruikbaar_pct"] == pytest.approx(
        round(100 * bruikbaar / totaal, 1))


def test_nul_volledig_is_geen_tikfout_maar_de_bevinding(poc):
    """Geen enkel voorschrift draagt een geldigheidsperiode; dat is wat 'volledig = 0' betekent."""
    assert wp.CIJFERS["voorschriften_zonder_geldigheid"] == sum(
        p["model"]["zonder_geldigheid"] for p in poc["punten"])
    assert wp.CIJFERS["voorschriften_zonder_geldigheid"] == wp.CIJFERS["voorschriften_totaal"]


def test_het_aandeel_dat_het_register_verklaart_klopt_met_de_momentopname(poc):
    aandelen = [s["aandeel_pct"] for p in poc["punten"] for s in (p.get("stoffen") or [])
                if s.get("aandeel_pct") is not None]
    assert wp.CIJFERS["aandeel_gevallen"] == len(aandelen)
    assert wp.CIJFERS["aandeel_max_pct"] == pytest.approx(round(max(aandelen), 1))
    assert wp.CIJFERS["aandeel_nul"] == sum(1 for a in aandelen if a == 0)


def test_het_aantal_meetpunten_klopt(poc):
    assert wp.CIJFERS["meetpunten"] == len(poc["punten"])


def test_de_dia_over_het_resultaat_noemt_hetzelfde_maximum_als_de_cijfers():
    """De plaat en de tekst mogen niet uit elkaar lopen: beide komen uit CIJFERS' bron."""
    dia = next(d for d in wp.DIAS if d["beeld"]["soort"] == "rivier")
    top = max(p["pct"] for p in dia["beeld"]["punten"])
    assert top == pytest.approx(wp.CIJFERS["aandeel_max_pct"])
    assert str(wp.CIJFERS["aandeel_max_pct"]).replace(".", ",") in " ".join(dia["kern"])


def test_de_rioolcijfers_zijn_onderling_consistent():
    """Zeven zuiveringsvergunningen met dertig voorschriften over vijf grootheden -- die drie
    getallen staan los van elkaar in de tekst en moeten elkaar niet tegenspreken."""
    c = wp.CIJFERS
    assert c["rwzi_in_register"] < c["register_maas"]
    assert c["rwzi_voorschriften"] >= c["rwzi_in_register"] * 1
    assert c["kvk_gevuld"] == c["register_maas"], "de claim is: gevuld in alle Maas-posten"
    dia = next(d for d in wp.DIAS if d["beeld"]["soort"] == "chips")
    assert len(dia["beeld"]["wel"]) == c["rwzi_grootheden"]


# --- de pagina --------------------------------------------------------------------------

def test_de_pagina_geeft_200_met_de_subnav(monkeypatch):
    r = _client(monkeypatch).get("/waterpresentatie")
    assert r.status_code == 200
    assert 'class="waternav"' in r.text
    assert r.text.count('aria-current="page"') == 1
    assert "__WATERNAV__" not in r.text
    assert "/api/waterpresentatie" in r.text


def test_het_eindpunt_levert_alle_dias_met_hun_duur(monkeypatch):
    d = _client(monkeypatch).get("/api/waterpresentatie").json()
    assert d["duur_s"] == 600
    assert d["aantal"] == len(d["dias"]) == len(wp.DIAS)
    assert d["dias"][0]["start_s"] == 0
    assert all("spreektekst" in x and "beeld" in x for x in d["dias"])


def test_de_presentatie_is_lid_van_het_waterdossier():
    lid = wh.lid("presentatie")
    assert lid["pad"] == "/waterpresentatie"
    assert lid["live"] == [], "een presentatie hoort niet op een trage bron te wachten"


def test_de_toerekening_wordt_ook_hier_als_bovengrens_gepresenteerd():
    """Dezelfde harde regel als op /kmg: dit lab stelt niet vast wie iets veroorzaakt.

    Op de bare term "veroorzaakt" toetsen kan niet: de spreektekst ontkent de bewering juist
    ("wij zeggen niet wie iets veroorzaakt"), en een ontkenning is met een deelstring niet van
    een bewering te onderscheiden. Daarom hetzelfde als op /kmg: de verboden formulering
    "veroorzaakt door", plus de eis dat het voorbehoud zélf wordt uitgesproken.
    """
    tekst = " ".join(d["spreektekst"] for d in wp.DIAS).lower()
    assert "veroorzaakt door" not in tekst
    assert "bovengrens" in tekst
    assert "nooit een vaststelling" in tekst


# --- de afbakening, sinds het stroomgebied de cirkel verving ------------------------------

def test_het_waterlichaamregister_klopt_met_de_presentatie():
    """163 Maas-waterlichamen is een brongegeven en hoort niet te verouderen in een dia."""
    from leefomgevinglab.usecases.kmg import stroomgebied

    r = stroomgebied.laad()
    if not r["beschikbaar"]:
        pytest.skip(r["reden"])
    assert wp.CIJFERS["waterlichamen_maas"] == len(stroomgebied.codes_in_district(r, "Maas"))


def test_wat_dit_lab_plaatst_en_wat_het_laat_liggen_klopt_met_de_code():
    from leefomgevinglab.usecases.kmg import toerekening

    assert wp.CIJFERS["waterlichamen_geplaatst"] == len(toerekening.STROOMVOLGORDE)
    assert wp.CIJFERS["waterlichamen_zonder_positie"] == len(toerekening.ZONDER_POSITIE)


def test_de_dia_over_hoe_verder_zegt_dat_de_cirkel_vervangen_is():
    """Een presentatie die een opgelost probleem als openstaand presenteert, is onwaar."""
    dia = next(d for d in wp.DIAS if d["beeld"]["soort"] == "tijdlijn")
    gedaan = [i for i in dia["beeld"]["items"] if i["jaar"] == "gedaan"]
    assert gedaan and "stroomgebieddistrict" in gedaan[0]["wat"]
    assert "cirkel van 50 km" not in " ".join(dia["kern"]), "dat staat niet meer op de lijst"


def test_de_stroomvolgorde_staat_wel_als_openstaand_punt():
    """Wat de download níét oploste hoort zichtbaar te blijven."""
    tekst = " ".join(" ".join(d["kern"]) + " " + d["spreektekst"] for d in wp.DIAS).lower()
    assert "stroomvolgorde" in tekst
    assert "geen relatie ertussen" in tekst or "geen enkele relatie ertussen" in tekst
