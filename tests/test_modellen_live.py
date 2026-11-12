"""Live controle van /modellen tegen de bestanden die het REV echt publiceert.

Deze pagina beweert getallen over vier bestanden op `rev-portaal.nl/oas`. Een test op
verzonnen data zou die beweringen nooit kunnen weerleggen — en juist dat is in dit lab de
manier waarop elke echte fout gevonden is. Daarom haalt deze test de bestanden op en rekent
na, inclusief de twee dingen die bij het natellen boven water kwamen:

* de eerder vermelde 88 objecttypen en 41 referentietypen waren niet te reproduceren; de
  indelingsregel van `modellen.indeling()` komt exact op 168 uit;
* `imev30-oas-schema.yaml` bevat een tabteken en is daardoor geen geldige YAML.

Skipt zonder `DSO_API_KEY`, de generieke live-vlag van deze repo. De bestanden zelf vragen
geen sleutel.
"""
import os
import re

import httpx
import pytest
import yaml

from leefomgevinglab.usecases import modellen as mo

pytestmark = pytest.mark.skipif(not os.environ.get("DSO_API_KEY"),
                                reason="live-tests uit (DSO_API_KEY niet gezet)")

BASIS = "https://rev-portaal.nl/oas/"


@pytest.fixture(scope="module")
def bestanden():
    """De vier bestanden als ruwe tekst, in één keer opgehaald."""
    namen = ["rev-v5-specification.yaml", "imev30-schema.yaml",
             "imev30-oas-schema.yaml", "common-schema.yaml"]
    uit = {}
    with httpx.Client(timeout=60.0, follow_redirects=True) as c:
        for naam in namen:
            r = c.get(BASIS + naam)
            if r.status_code != 200:
                pytest.skip(f"{naam} geeft {r.status_code}")
            uit[naam] = r.text
    return uit


def _schoon(tekst: str) -> str:
    """Maak regels die alleen witruimte zijn echt leeg.

    Nodig omdat één van de bestanden een tab op zo'n regel heeft, wat YAML verbiedt; de test
    onderaan stelt dat gebrek apart vast in plaats van het hier stil te verbergen. Let op het
    `\r`: de bestanden hebben CRLF-regeleindes, dus zonder dat in de tekenklasse matcht
    `[ \t]+$` de regel niet en blijft de tab staan.
    """
    return re.sub(r"^[ \t\r]+$", "", tekst, flags=re.M)


def _schemas(tekst: str) -> dict:
    return (yaml.safe_load(_schoon(tekst)).get("components") or {}).get("schemas") or {}


# --- wat elk bestand is -----------------------------------------------------------------------

def test_de_api_specificatie_is_een_openapi_en_leent_het_versienummer_van_het_model(bestanden):
    """De verwarring die deze pagina uitlegt, staat in de bron zelf."""
    spec = yaml.safe_load(bestanden["rev-v5-specification.yaml"])
    assert spec["openapi"].startswith("3.")
    assert spec["info"]["title"] == "REV API - v5"
    assert spec["info"]["version"] == "IMEV 3.0.1", \
        "als dit verandert, vervalt het argument op de pagina en moet de tekst mee"


def test_de_api_specificatie_definieert_zelf_geen_inhoudelijk_schema(bestanden):
    spec = yaml.safe_load(bestanden["rev-v5-specification.yaml"])
    comp = spec.get("components") or {}
    assert not (comp.get("schemas") or {}), \
        "de spec draagt nu wél eigen schemas; de bevinding op de pagina klopt dan niet meer"
    assert "securitySchemes" in comp
    assert len(spec["paths"]) == mo.telling()["api_paden"]


def test_de_schemabestanden_zijn_componentbundels_en_geen_openapi(bestanden):
    """Ze hebben geen openapi-, info- of paths-sleutel: losse bouwstenen, geen specificatie."""
    for naam in ("imev30-schema.yaml", "imev30-oas-schema.yaml", "common-schema.yaml"):
        d = yaml.safe_load(_schoon(bestanden[naam]))
        assert set(d) == {"components"}, f"{naam} heeft {sorted(d)}"


# --- de tellingen op de pagina ----------------------------------------------------------------

def test_de_indelingsregel_dekt_alle_definities_en_komt_op_de_getoonde_aantallen(bestanden):
    """De kern: geen enkel getal op deze pagina is getypt, alle zijn ze af te leiden."""
    s = _schemas(bestanden["imev30-schema.yaml"])
    t = mo.telling()
    assert len(s) == t["schema_definities"]
    gemeten = mo.indeling(s)
    assert sum(gemeten.values()) == len(s), \
        "een definitie valt in geen bak -- dat zou een stil gat in de telling zijn"
    assert gemeten == mo.indeling(), f"schema gewijzigd: {gemeten}"


def test_de_oude_aantallen_88_en_41_zijn_inderdaad_niet_te_reproduceren(bestanden):
    """Vastgelegd zodat ze niet terugkruipen: 88 + 41 dekt de 168 definities niet."""
    s = _schemas(bestanden["imev30-schema.yaml"])
    g = mo.indeling(s)
    assert g["objecttypen"] != 88
    assert g["keuzetypen"] != 41
    assert 88 + 41 + g["enumeraties"] != len(s)


def test_vierenveertig_objecttypen_dragen_het_vergunningnummer(bestanden):
    """De correctie waar deze analyse om begon, tegen het echte bestand."""
    s = _schemas(bestanden["imev30-schema.yaml"])
    met = [n for n, v in s.items()
           if isinstance(v, dict) and "basisVergunningNummer" in (v.get("properties") or {})]
    assert len(met) == mo.telling()["schema_met_vergunningnummer"]
    for veld in ("datumVergunningOfMelding", "vergunningsPlicht"):
        assert any(veld in (s[n].get("properties") or {}) for n in met), veld


def test_voidable_komt_op_het_getoonde_aantal_plekken_voor(bestanden):
    import json
    s = _schemas(bestanden["imev30-schema.yaml"])
    aantal = json.dumps(s).count("#/components/schemas/Voidable")
    assert aantal == mo.telling()["schema_voidable_plekken"]
    vr = s["VoidReasonValue"]
    assert set(vr["enum"]) == {"gegevenInTransitie", "nietVanToepassing", "waardeOnbekend"}


def test_bevoegdgezag_is_een_bestuurslaag_en_geen_organisatie(bestanden):
    s = _schemas(bestanden["imev30-schema.yaml"])
    enum = set(s["BevoegdGezag"]["enum"])
    assert enum == {"rijk", "provincie", "gemeente", "gegevenInTransitie"}, enum


def test_de_verwijzingen_verdelen_zich_zoals_de_pagina_zegt(bestanden):
    """43 naar de envelop, 8 naar de inhoud, 7 naar de geotypes: een API is verpakking."""
    spec = yaml.safe_load(bestanden["rev-v5-specification.yaml"])
    per = {}

    def loop(x):
        if isinstance(x, dict):
            for k, v in x.items():
                if k == "$ref" and isinstance(v, str) and "#" in v:
                    doel = v.split("#")[0]
                    if doel:
                        per[doel] = per.get(doel, 0) + 1
                else:
                    loop(v)
        elif isinstance(x, list):
            for y in x:
                loop(y)

    loop(spec)
    assert per == mo.verwijzingen()["per_bestand"], per


# --- en het gebrek dat bij het natellen boven water kwam ---------------------------------------

def test_de_envelop_is_geen_geldige_yaml(bestanden):
    """Niet om te vitten: het staat als bevinding op de pagina en moet dus waar blijven.

    Zodra RWS de tab weghaalt, faalt deze test en hoort de bevinding van de pagina af.
    """
    tekst = bestanden["imev30-oas-schema.yaml"]
    assert "\t" in tekst
    with pytest.raises(yaml.YAMLError) as fout:
        yaml.safe_load(tekst)
    assert "tab" in str(fout.value).lower() or "\\t" in str(fout.value)
    # De tab staat op een regel die verder leeg is -- achtergebleven witruimte, geen inhoud.
    regels = [i for i, r in enumerate(tekst.splitlines(), 1) if "\t" in r]
    assert all(not tekst.splitlines()[i - 1].strip() for i in regels), \
        "de tab zit nu in een inhoudelijke regel; de bevinding moet dan herschreven"
