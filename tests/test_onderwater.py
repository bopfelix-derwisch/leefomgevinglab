"""`usecases.onderwater` -- de technische anatomie van `/wasstraat` en `/toezicht`.

Deze pagina bestaat omdat in dit lab veel onder water gebeurt: de gegevensherkomst is zichtbaar,
de bewerking niet. Dat maakt haar een bijzonder soort pagina om te testen, want zij **beweert
dingen over andere code**. Een anatomie die haar getallen typt in plaats van aflekt, is precies
zo onbetrouwbaar als de ondoorzichtigheid die zij moet oplossen -- en dat is niet te zien aan de
pagina zelf. Deze tests gaan daar bijna allemaal over.
"""
import re

import pytest

from leefomgevinglab.usecases import onderwater
from leefomgevinglab.usecases.toezicht import signalen
from tests.test_toezicht_runner import AGENTS, TASKS

_CONFIG = {
    "leefomgevinglab": {
        "kmg": {"aquo_csv_pad": "/mnt/nvme/geluidsmeter/data/external/wkp/aquo_Parameter.csv",
                 "straal_m": 50000},
        "waterpresentatie": {"normen_pad": "/mnt/nvme/geluidsmeter/data/external/wkp/krw.json"},
        "smwk_atlas": {"cache_ttl_s": 86400, "base_url": "https://services.arcgis.com/x"},
        "cache_dir": "/mnt/nvme/geluidsmeter/data/cache",
    }
}


@pytest.fixture
def a():
    return onderwater.anatomie(AGENTS, TASKS, _CONFIG)


# -- De regels: afgeleid uit signalen.py, nooit getypt ------------------------------------------

def test_alle_tien_regels_staan_erin_en_komen_uit_de_catalogus(a):
    """Geen eigen lijst regel-id's in deze module: een elfde regel in `signalen.REGELS` hoort
    hier automatisch op te duiken. Stond er een eigen lijst, dan zou die regel stil ontbreken op
    precies de pagina die belooft te vertellen wat er gebeurt."""
    assert [r["id"] for r in a["regels"]] == [r.id for r in signalen.REGELS]


def test_elke_regel_draagt_haar_echte_drempel_en_de_betekenis_van_omvang(a):
    for r in a["regels"]:
        drempel, betekenis = signalen.DREMPELS[r["id"]]
        assert r["drempel"] == drempel
        assert r["omvang_betekent"] == betekenis


def test_de_twee_assen_worden_apart_benoemd_en_niet_door_elkaar_gehaald(a):
    """`Regel.laag` (papier/werkelijkheid) bepaalt op wélke pagina een regel landt;
    `is_voorbehoud` (drempel >= 99) bepaalt of zij binnen het papier een bevinding is. Dat zijn
    twee verschillende vragen, en de eindreview liet zien wat het kost om ze te verwarren: twee
    register-brede voorbehouden stonden als bevinding in de lijst en maakten `op_orde` tot dode
    code. Deze pagina moet ze dus gescheiden tonen, niet samenvoegen tot één 'soort'."""
    lagen = {r.id: r.laag for r in signalen.REGELS}
    for r in a["regels"]:
        assert r["laag"] == lagen[r["id"]]
        assert r["is_voorbehoud"] == signalen.is_voorbehoud(r["id"])
    assert {r["laag"] for r in a["regels"]} == {"papier", "werkelijkheid"}


def test_elke_regel_wijst_naar_de_pagina_waar_zij_werkelijk_landt(a):
    """De werkelijkheidsregels landen op `/toezicht`, de papierregels op `/wasstraat`. Dat is
    geen bewering van deze module maar van de twee filters -- dus wordt het hier uit `laag`
    afgeleid en niet per regel ingetypt."""
    for r in a["regels"]:
        verwacht = "/toezicht" if r["laag"] == "werkelijkheid" else "/wasstraat"
        assert r["pagina"] == verwacht, r["id"]


def test_de_tellingen_per_pagina_kloppen_met_de_regels_zelf(a):
    """Het soort getal dat op een uitlegpagina fout gaat: 'zeven papierregels' blijft staan nadat
    er een achtste bij komt. Hier wordt het geteld, niet geschreven."""
    regels = a["regels"]
    paginas = {p["pad"]: p for p in a["paginas"]}
    assert paginas["/wasstraat"]["aantal_bevindingen"] == len(
        [r for r in regels if r["laag"] == "papier" and not r["is_voorbehoud"]])
    assert paginas["/wasstraat"]["aantal_voorbehouden"] == len(
        [r for r in regels if r["laag"] == "papier" and r["is_voorbehoud"]])
    assert paginas["/toezicht"]["aantal_signalen"] == len(
        [r for r in regels if r["laag"] == "werkelijkheid"])


def test_geen_enkel_getal_in_de_uitlegteksten_is_los_ingetypt(a):
    """**De kernbewaking van deze module.** Een anatomie die zegt "zeven papierregels" in proza
    gaat liegen zodra de code verschuift, en juist deze pagina kan dat niet maken: zij is het
    enige dat de lezer heeft om de rest te controleren. Alle aantallen komen daarom uit de
    afgeleide velden, en de teksten dragen geen cijfers -- behalve de drempel-sentinel 99 en
    jaartallen, die geen telling zijn."""
    teksten = []
    for onderdeel in a["onderdelen"]:
        teksten += [onderdeel["wat"], onderdeel["waarom"]]
    for r in a["regels"]:
        teksten.append(r["uitleg"])
    fouten = []
    for tekst in teksten:
        for getal in re.findall(r"\b\d+\b", tekst or ""):
            if getal in ("99", "4", "2"):   # sentinel, en §4.4 als paragraafnummer
                continue
            if len(getal) == 4 and getal.startswith("20"):   # jaartal
                continue
            fouten.append(f"{getal!r} in: {tekst[:90]}")
    assert not fouten, (
        "los ingetypt getal in een uitlegtekst -- leid het af of laat het weg:\n"
        + "\n".join(fouten))


# -- Agents en taken: uit de YAML, met de llm-regel erbij ---------------------------------------

def test_de_agents_komen_uit_de_configuratie_met_hun_llm_regel(a):
    agents = {x["id"]: x for x in a["agents"]}
    assert agents["uitlegger"]["mag_llm"] is True
    assert agents["signaalsteller"]["mag_llm"] is False
    assert agents["uitlegger"]["llm"] and "8080" in agents["uitlegger"]["llm"]
    assert agents["signaalsteller"]["llm"] is None


def test_elke_agent_noemt_de_taken_die_hij_in_de_pijplijn_heeft(a):
    """Zonder dit leest een lezer zes agents en vier taken zonder te zien welke agent niets doet.
    `vraagsteller` en `terugkoppelaar` hebben geen taak -- dat is een feit over de pijplijn dat
    deze pagina moet laten zien, niet verbergen."""
    agents = {x["id"]: x for x in a["agents"]}
    assert agents["uitlegger"]["taken"] == ["leg_signalen_uit"]
    assert agents["vraagsteller"]["taken"] == []
    assert agents["terugkoppelaar"]["taken"] == []
    assert agents["vergunninglezer"]["taken"] == ["lees_vergunning"]


def test_de_taalmodelgrens_wordt_afgeleid_en_niet_beweerd(a):
    """De §4.4-grens staat in `agents.yaml` als een *afwezig veld*. Deze pagina mag die grens dus
    niet als belofte in proza herhalen, maar moet hem uit dezelfde afwezigheid aflezen."""
    grens = a["grens"]
    assert set(grens["mag_wel"]) == {x["id"] for x in a["agents"] if x["mag_llm"]}
    assert set(grens["mag_niet"]) == {x["id"] for x in a["agents"] if not x["mag_llm"]}
    assert "signaalsteller" in grens["mag_niet"], "een signaal is een regel die vuurt"
    assert grens["in_de_dossierroutes_aangeroepen"] is False, (
        "beide routes geven llm=None door; staat hier True, dan is dat een echte verandering")


# -- Config: een witte lijst, en nooit een absoluut serverpad -----------------------------------

def test_de_configuratiesleutels_zijn_een_witte_lijst_en_geen_sectiedump(a):
    """`core/config.yaml` draagt ook `submit_token` en api-headernamen. Een dump van een sectie
    zou die meenemen naar een publieke pagina, dus deze module noemt alleen sleutels die deze
    twee routes werkelijk lezen."""
    sleutels = {c["sleutel"] for c in a["config"]}
    assert "leefomgevinglab.kmg.aquo_csv_pad" in sleutels
    assert "leefomgevinglab.waterpresentatie.normen_pad" in sleutels
    for verboden in ("submit_token", "api_key", "token", "secret"):
        assert not any(verboden in s for s in sleutels), verboden


def test_geen_enkel_absoluut_serverpad_verlaat_deze_module(a):
    """De eindreview ving dit eerder op `/api/wasstraat/pijplijn`, dat
    `/mnt/nvme/workspaces/...` publiceerde. Dezelfde regel geldt hier, en met meer reden: deze
    pagina staat vól paden."""
    import json
    tekst = json.dumps(a, ensure_ascii=False)
    assert "/mnt/nvme" not in tekst, "absoluut serverpad in de anatomie"
    assert "/home/" not in tekst


def test_een_sleutel_die_in_de_configuratie_ontbreekt_wordt_als_ontbrekend_getoond(a):
    """Stil weglaten zou de ergste vorm zijn die deze pagina kan hebben: zij zou dan precies de
    misconfiguratie verbergen die zij hoort te laten zien. `/kmg` las maanden een
    `normen_pad`-sleutel die niet bestond en toonde daardoor alle stoffen zonder normoordeel."""
    zonder = onderwater.anatomie(AGENTS, TASKS, {"leefomgevinglab": {}})
    for c in zonder["config"]:
        assert c["aanwezig"] is False
        assert c["waarde"] is None
    aanwezig = {c["sleutel"]: c["aanwezig"] for c in a["config"]}
    assert aanwezig["leefomgevinglab.kmg.aquo_csv_pad"] is True


# -- Bronnen -------------------------------------------------------------------------------------

def test_elke_bron_noemt_houder_bevragingswijze_en_waar_de_code_haar_leest(a):
    """Een bronnenlijst zonder vindplaats in de code is niet te controleren -- en controleerbaar
    maken is de hele reden dat deze pagina bestaat."""
    assert a["bronnen"], "zonder bronnen is er geen anatomie"
    for b in a["bronnen"]:
        assert b["naam"] and b["houder"] and b["hoe"] and b["waar_in_de_code"]
        assert b["licentie"], "de licentiepositie hoort expliciet, ook als die 'geen' is"


def test_de_atlas_draagt_haar_licentievoorbehoud(a):
    """De Atlas-lagen zijn publiek maar dragen geen expliciete licentie. Dat staat in CLAUDE.md
    als harde randvoorwaarde (live bevragen met bronvermelding, nooit kopiëren) en hoort dus op
    de pagina die de bronnen uitlegt."""
    atlas = next(b for b in a["bronnen"] if "Atlas" in b["naam"])
    tekst = atlas["licentie"].lower()
    # Op inhoud, niet op verwoording: de twee dingen die een lezer hieruit moet halen zijn dat er
    # geen expliciete licentie is, en dat de dataset daarom niet gekopieerd wordt.
    assert "expliciete licentie" in tekst
    assert "nooit" in tekst or "niet" in tekst, "het kopieerverbod hoort erbij"
    assert "kopi" in tekst


# -- Onderdelen: de uitgelegde delen -------------------------------------------------------------

def test_elk_onderdeel_zegt_wat_het_is_waarom_het_zo_is_en_waar_het_staat(a):
    """`waarom` is het veld dat deze pagina onderscheidt van een gegenereerde API-referentie. Een
    onderdeel zonder reden is documentatie die niemand helpt controleren."""
    assert len(a["onderdelen"]) >= 5
    for o in a["onderdelen"]:
        assert o["kop"] and o["wat"] and o["waarom"] and o["waar"]


def test_geen_enkele_tekst_belooft_iets_wat_de_pagina_niet_toont(a):
    """Dezelfde taalregel als op de signaalpagina's: nooit een vaststelling."""
    import json
    tekst = json.dumps(a, ensure_ascii=False).lower()
    for verboden in ("overtreding", "veroorzaakt door", "in strijd met"):
        assert verboden not in tekst, verboden
