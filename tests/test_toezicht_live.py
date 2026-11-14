"""De live controle -- de tellingen van het plan tegen de echte Atlas.

Dit is de taak die in dit lab het meeste oplevert, dus hij komt vóór de pagina (`/toezicht`
bestaat nog niet). Hij legt de getallen van het plan vast tegen de bron, zodat een verschuiving
in de Atlas voor een Schone Maas, de Aquo-domeintabel of het Waterkwaliteitsportaal luid faalt in
plaats van stil de pagina te veranderen.

Vier bronnen, drie live en één lokaal bestand:
  * `SmwkAtlasConnector` -- het vergunningenregister, live opgehaald (geen kopie in de repo).
  * `lozingsmodel.laad_parameters` + `aquo.laad` -- de Aquo-domeintabel Parameter, lokaal op
    `/mnt/nvme/geluidsmeter/data/external/wkp/`.
  * de ruwe WKP-meetwaarden-CSV (142 MB), eveneens lokaal daar, nooit in de repo.

Alle tellingen zijn gemeten op 2026-11-13 tegen deze bronnen; zie de assert-boodschappen voor
wat te doen als een getal niet meer klopt.

Staat standaard uit (marker `live`, zie fix 3, live-fixes-report.md -- aanzetten met
`pytest --run-live`). **Niet elke test hier hoeft dat te zijn**: de configuratietest op
`_toezicht_normenset` raakt geen netwerk en hoort daarom niet in dit bestand, maar in
`tests/test_api_toezicht.py` (zie de toelichting daar, fix-ronde 3 van die taak -- hetzelfde
patroon als deze fix, één taak eerder al toegepast).
"""
import csv
import json
import tempfile
from collections import Counter
from pathlib import Path

import pytest

from leefomgevinglab.connectors.smwk_atlas import SmwkAtlasConnector
from leefomgevinglab.usecases.kmg import lozingsmodel
from leefomgevinglab.usecases.toezicht import aquo, signalen

pytestmark = pytest.mark.live

_WKP_DIR = "/mnt/nvme/geluidsmeter/data/external/wkp"
_RUWE_CSV = f"{_WKP_DIR}/WKP_Meetwaarden_Rijkswaterstaat_2025_20261001171800.csv"
_AQUO_JSON = f"{_WKP_DIR}/aquo_parameters.json"
_AQUO_CSV = f"{_WKP_DIR}/aquo_Parameter.csv"
_METINGEN_JSON = f"{_WKP_DIR}/metingen_2025.json"

# Hetzelfde punt en dezelfde straal als het plan: heel het Maasstroomgebied vanuit één centraal
# RD-punt, ruim binnen de grens van 5000 m die andere live-tests (`test_atlas_live.py`) gebruiken.
_PUNT = (170000.0, 390000.0)
_STRAAL_M = 250000


def test_het_register_heeft_de_omvang_die_de_pagina_noemt(tmp_path):
    c = SmwkAtlasConnector(cache_dir=str(tmp_path))
    alles = c.vergunningen_bij_punt(170000.0, 390000.0, straal_m=250000)
    assert len(alles) == 69, "aantal vestigingen gewijzigd -- pagina en plan bijwerken"
    assert sum(len(v["voorschriften"]) for v in alles) == 782, (
        "aantal voorschriften gewijzigd -- pagina en plan bijwerken"
    )
    leeg = {f: sum(1 for v in alles if not v.get(f)) for f in ("url", "kenmerk", "besluitdatum")}
    assert leeg == {"url": 8, "kenmerk": 6, "besluitdatum": 5}, (
        "aantal lege velden (url/kenmerk/besluitdatum) gewijzigd -- pagina en plan bijwerken"
    )


@pytest.fixture(scope="module")
def register():
    """Het hele Maas-register, één keer per testmodule opgehaald -- elke live-test hieronder
    bouwt op dezelfde 69 vestigingen / 782 voorschriften als de verbatim-test hierboven. Eigen
    tijdelijke cache-map, nooit de projectmap: de Atlas-lagen zijn publiek maar dragen geen
    expliciete licentie (zie `smwk_atlas.py`), dus geen kopie bewaren."""
    with tempfile.TemporaryDirectory() as td:
        c = SmwkAtlasConnector(cache_dir=td)
        yield c.vergunningen_bij_punt(*_PUNT, straal_m=_STRAAL_M)


@pytest.fixture(scope="module")
def vergunde_codes(register):
    """Elke Aquo-code die ergens in het register voorkomt, via `lozingsmodel.dataficeer` -- de
    publieke koppelfunctie die het model ook gebruikt, geen eigen normalisatie in deze test.
    56 distincte codes op 2026-11-13 (zie `test_de_aquo_koppeling_dekt_het_plan_percentage`)."""
    if not Path(_AQUO_JSON).exists():
        pytest.skip(f"geen parameterreferentie op {_AQUO_JSON}; bouw hem met scripts/16")
    ref = lozingsmodel.laad_parameters(_AQUO_JSON)
    codes = set()
    for v in register:
        for vs in v.get("voorschriften") or []:
            code = lozingsmodel.dataficeer(vs, ref)["parameter"]["waarde"]
            if code:
                codes.add(code)
    return codes


@pytest.fixture(scope="module")
def ruwe_wkp_csv(vergunde_codes):
    """Eén keer, streamend, door de 142 MB ruwe WKP-meetwaarden-CSV -- voor alle live-tests die
    hem nodig hebben, in plaats van per test opnieuw 384.259 rijen te lezen:

    - welke Aquo-codes op de 92 WKP-meetpunten (uit de verdichte set `metingen_2025.json`)
      daadwerkelijk gemeten worden (signaal 1);
    - of een meting op een vergunde stof ooit een bemonsteringsapparaat meldt (signaal 9).

    Beide in één leespas, want een tweede pas over hetzelfde bestand is nodeloos traag."""
    if not Path(_RUWE_CSV).exists():
        pytest.skip(f"ruwe WKP-CSV niet gevonden op {_RUWE_CSV}")
    if not Path(_METINGEN_JSON).exists():
        pytest.skip(f"verdichte meetset niet gevonden op {_METINGEN_JSON}")
    puntenset = json.loads(Path(_METINGEN_JSON).read_text(encoding="utf-8"))
    puntcodes = {p["code"] for p in puntenset["punten"]}

    gemeten_codes_op_punten = set()
    totaal_rijen = 0
    leeg_bemonsteringsapparaat = 0
    totaal_bij_vergunde_code = 0
    gevuld_bij_vergunde_code = 0
    with open(_RUWE_CSV, encoding="utf-8-sig", newline="") as f:
        for rij in csv.DictReader(f, delimiter=";"):
            totaal_rijen += 1
            bac = (rij.get("BemonsteringsapparaatCode") or "").strip()
            if not bac:
                leeg_bemonsteringsapparaat += 1
            pc = rij.get("ParameterCode")
            if pc and rij.get("MeetobjectCode") in puntcodes:
                gemeten_codes_op_punten.add(pc)
            if pc in vergunde_codes:
                totaal_bij_vergunde_code += 1
                if bac:
                    gevuld_bij_vergunde_code += 1
    return {
        "gemeten_codes_op_punten": gemeten_codes_op_punten,
        "totaal_rijen": totaal_rijen,
        "leeg_bemonsteringsapparaat": leeg_bemonsteringsapparaat,
        "totaal_bij_vergunde_code": totaal_bij_vergunde_code,
        "gevuld_bij_vergunde_code": gevuld_bij_vergunde_code,
    }


def test_de_aquo_koppeling_dekt_het_plan_percentage(register):
    """De koppeling die het plan noemt: 677 van de 782 voorschriften koppelen aan een geldige
    Aquo-code (56 distincte stoffen), de overige 105 (13 distincte namen) niet. Dit gebruikt
    `lozingsmodel.dataficeer`, dezelfde publieke functie als de signaal-1-test hieronder --
    geen losse herimplementatie van de normalisatie."""
    ref = lozingsmodel.laad_parameters(_AQUO_JSON)
    assert ref.get("beschikbaar"), f"geen parameterreferentie op {_AQUO_JSON}"

    gekoppeld = 0
    ongekoppeld = 0
    codes = set()
    namen_ongekoppeld = set()
    for v in register:
        for vs in v.get("voorschriften") or []:
            code = lozingsmodel.dataficeer(vs, ref)["parameter"]["waarde"]
            if code:
                gekoppeld += 1
                codes.add(code)
            else:
                ongekoppeld += 1
                namen_ongekoppeld.add(vs.get("parameter"))

    assert gekoppeld == 677, (
        f"{gekoppeld} voorschriften koppelen aan een Aquo-code i.p.v. 677 -- de Atlas of de "
        "parameterreferentie is gewijzigd; plan en pagina moeten dan mee"
    )
    assert len(codes) == 56, f"{len(codes)} distincte gekoppelde stoffen i.p.v. 56"
    assert ongekoppeld == 105, f"{ongekoppeld} voorschriften ongekoppeld i.p.v. 105"
    assert len(namen_ongekoppeld) == 13, f"{len(namen_ongekoppeld)} distincte namen i.p.v. 13"


def test_signaal_1_vindt_de_stoffen_zonder_onafhankelijke_meting(register, vergunde_codes,
                                                                   ruwe_wkp_csv):
    """Stap 3 van de taakbrief: van de 56 vergunde stoffen wordt er geen enkele van 18 gemeten op
    een van de 92 WKP-meetpunten, samen goed voor 274 voorschriften. Dit draait de echte
    `signalen.regel_geen_onafhankelijke_meting` tegen de echte Atlas plus de ruwe meet-CSV, geen
    losse herberekening -- zodat een wijziging in de regel zelf hier ook meetelt.

    De valkuil uit de taakbrief: de verdichte meetset (`metingen_2025.json`) draagt maar 3
    stoffen (dit lab volgt alleen stikstof, zink en PFOA); alleen de ruwe CSV (492 ParameterCodes
    in heel het bestand) laat zien wát er werkelijk op die 92 punten gemeten wordt. Met de
    verdichte set zelf zou dit bijna elke stof als 'ongemeten' melden -- fout, zoals de
    taakbrief vermeldt.

    De aggregaten (18 stoffen, 274 voorschriften) laten een verschuiving in de samenstelling
    onopgemerkt: gaat een WKP-export morgen Cl2 (5 voorschriften) wél meten en T (11) niet meer,
    dan blijven totaal én aantal gelijk terwijl de stoffen die de pagina noemt zijn veranderd.
    Daarom wordt hieronder de volledige verdeling per Aquo-code in één keer tegen de verwachting
    gehouden, niet alleen de twee totalen."""
    ref = lozingsmodel.laad_parameters(_AQUO_JSON)
    geannoteerd = []
    for v in register:
        nieuwe_voorschriften = []
        for vs in v.get("voorschriften") or []:
            code = lozingsmodel.dataficeer(vs, ref)["parameter"]["waarde"]
            nieuwe_voorschriften.append({**vs, "aquo": code})
        geannoteerd.append({**v, "voorschriften": nieuwe_voorschriften})

    context = {"gemeten_codes": ruwe_wkp_csv["gemeten_codes_op_punten"]}
    alle_signalen = []
    for v in geannoteerd:
        alle_signalen.extend(signalen.regel_geen_onafhankelijke_meting(v, context))

    # Eén code kan in meerdere vestigingen een eigen signaal opleveren (regel_geen_onafhankelijke_
    # meting vuurt per vestiging per code); de Counter telt hun omvang dus bij elkaar op tot één
    # totaal per stof, in plaats van alleen de laatste te onthouden.
    per_code = Counter()
    for s in alle_signalen:
        per_code[s["bewijs"][0]["aquo"]] += s["omvang"]
    totaal_voorschriften = sum(per_code.values())

    assert len(vergunde_codes) == 56, f"{len(vergunde_codes)} vergunde stoffen i.p.v. 56"
    assert len(per_code) == 18, (
        f"{len(per_code)} stoffen zonder meting i.p.v. 18 -- de Atlas, de WKP-CSV of de regel "
        "zelf is gewijzigd; plan §3/§6 en de pagina moeten dan mee"
    )
    assert totaal_voorschriften == 274, (
        f"{totaal_voorschriften} voorschriften zonder meting i.p.v. 274 -- zie vorige assert"
    )
    verwacht_per_code = {
        "pH": 88, "Q": 58, "minrlole": 47, "WARMTE": 26, "smetln6": 16, "T": 11, "Cl2": 5,
        "NKj": 4, "sVBCl": 4, "VERMGN": 2, "smetlglt": 2, "BZV5": 2, "OVERSFQTE": 2, "Bi": 2,
        "VERVLWDE": 2, "BZV1": 1, "smetln5": 1, "sMAK": 1,
    }
    assert dict(per_code) == verwacht_per_code, (
        f"de samenstelling van de 18 ongemeten stoffen is veranderd: {dict(per_code)} i.p.v. "
        f"{verwacht_per_code} -- de aantallen stoffen/voorschriften hierboven kunnen toevallig "
        "gelijk blijven terwijl de WKP een andere stof is gaan (of gestopt is met) meten, of "
        "terwijl het register een ander voorschrift heeft gekregen; loop in dat geval na welke "
        "stof(fen) van kant wisselden voordat je deze verwachting bijwerkt"
    )


def test_signaal_9_klopt_zolang_de_wkp_geen_regime_meldt(ruwe_wkp_csv):
    """Stap 4 van de taakbrief. `regel_niet_regime_zuiver` is een voorbehoud dat vuurt zodra een
    voorschrift een bemonsteringsregime draagt (13 varianten in het register, zie signalen.py):
    de aanname is dat een WKP-meting dat regime nooit meldt, dus een vergelijking van meting
    tegen grenswaarde nooit regime-zuiver kan zijn.

    Twee tellingen tegen de ruwe CSV, 2026-11-13: (a) van de metingen op een van de 56 vergunde
    stoffen meldt er niet één een bemonsteringsapparaat -- dat is de exacte voorwaarde waaronder
    signaal 9 een geldig voorbehoud is; (b) over het hele bestand is BemonsteringsapparaatCode
    leeg in 326.718 van de 384.259 rijen, gevuld uitsluitend bij biologische bemonstering (fuik,
    elektrisch schepnet, boomkor, ankerkuil, ...). Zodra (a) niet meer nul is, moet signaal 9 van
    de pagina af -- dat is wat deze test luid laat falen."""
    assert ruwe_wkp_csv["totaal_bij_vergunde_code"] == 55423, (
        f"{ruwe_wkp_csv['totaal_bij_vergunde_code']} metingen op een vergunde stof i.p.v. "
        "55.423 -- controleer of de rest van deze test nog van toepassing is"
    )
    assert ruwe_wkp_csv["gevuld_bij_vergunde_code"] == 0, (
        f"{ruwe_wkp_csv['gevuld_bij_vergunde_code']} metingen op een vergunde stof melden nu wél "
        "een bemonsteringsapparaat -- signaal 9 (niet_regime_zuiver) is geen geldig voorbehoud "
        "meer en moet van de pagina af, of de regel moet per stof gaan differentiëren"
    )
    assert ruwe_wkp_csv["totaal_rijen"] == 384259, (
        f"WKP-export telt nu {ruwe_wkp_csv['totaal_rijen']} rijen i.p.v. 384.259 -- nieuwe "
        "export opgehaald, loop deze test na"
    )
    assert ruwe_wkp_csv["leeg_bemonsteringsapparaat"] == 326718, (
        f"{ruwe_wkp_csv['leeg_bemonsteringsapparaat']} van {ruwe_wkp_csv['totaal_rijen']} rijen "
        "zonder bemonsteringsapparaat i.p.v. 326.718/384.259 -- de WKP-export is aangepast"
    )


def test_de_eenheden_in_het_register_zijn_volledig_gedekt(register):
    """Zorgpunt 1 uit de taakopdracht: `signalen.CONCENTRATIE_EENHEDEN` en `DEBIET_EENHEDEN` zijn
    met de hand overgenomen uit andere eenhedentabellen in dit lab (zie de docstring in
    signalen.py) en zouden kunnen achterlopen bij wat de Atlas werkelijk gebruikt -- de brief
    noemde al minstens acht distincte eenheden tegen zeven in de oorspronkelijke telling.

    Pin daarom het volledige eenhedenlandschap: 21 distincte spellingen op 782 voorschriften,
    gemeten op 2026-11-13. Komt er een 22e spelling bij, dan faalt dit luid in plaats van
    `regel_vracht_onbepaald` stil fout te laten lopen op een eenheid die hij niet kent."""
    eenheden = Counter()
    for v in register:
        for vs in v.get("voorschriften") or []:
            eenheden[vs.get("eenheid")] += 1
    verwacht = {
        "milligram per liter": 386, "dimensieloos": 90, "kilogram per dag": 76,
        "kilogram per jaar": 64, "microgram per liter": 59, "kubieke meter per uur": 21,
        "kubieke meter per dag": 21, "megajoule per seconde": 18, "kubieke meter per jaar": 12,
        "graad Celsius": 11, "kilogram per week": 4, "megajoule per dag": 4,
        "megajoule per jaar": 4, None: 2, "ton per jaar": 2, "aantal per jaar": 2,
        "megawatt elektrisch": 2, "kubieke met per etmaal": 1, "kubieke meter per week": 1,
        "kubieke meter per schoonmaakactie": 1, "kubieke meter per seconde": 1,
    }
    assert dict(eenheden) == verwacht, (
        "het eenhedenlandschap in de Atlas is gewijzigd t.o.v. 2026-11-13 -- controleer "
        "handmatig of signalen.CONCENTRATIE_EENHEDEN/DEBIET_EENHEDEN nog elke concentratie- en "
        "debiet-achtige spelling dekken voordat je deze verwachting bijwerkt"
    )

    # Elke eenheid die in het register werkelijk een concentratie is, moet signalen.py als
    # concentratie herkennen -- mist er één, dan ontstaat een vals-negatief "vracht wél te
    # bepalen" in regel_vracht_onbepaald.
    concentratie_in_register = {"milligram per liter", "microgram per liter"}
    ontbrekend = concentratie_in_register - signalen.CONCENTRATIE_EENHEDEN
    assert not ontbrekend, (
        f"concentratie-eenheden {ontbrekend} staan in het register maar niet in "
        "signalen.CONCENTRATIE_EENHEDEN -- meld dit als bevinding, pas signalen.py niet zelf aan "
        "(buiten deze taak)"
    )

    # Elke eenheid die werkelijk een doorlopend debiet is (dus géén 'per schoonmaakactie' -- dat
    # is met opzet geen debiet, zie de docstring bij DEBIET_EENHEDEN) moet signalen.py als debiet
    # herkennen.
    debiet_in_register = {"kubieke meter per uur", "kubieke meter per dag",
                           "kubieke meter per jaar", "kubieke met per etmaal",
                           "kubieke meter per week", "kubieke meter per seconde"}
    ontbrekend = debiet_in_register - signalen.DEBIET_EENHEDEN
    assert not ontbrekend, (
        f"debiet-eenheden {ontbrekend} staan in het register maar niet in "
        "signalen.DEBIET_EENHEDEN -- meld dit als bevinding, pas signalen.py niet zelf aan "
        "(buiten deze taak)"
    )


def test_vervallen_code_raakt_de_aantallen_die_het_plan_noemt(register):
    """Zorgpunt 2 uit de taakopdracht: het plan noemt 90 voorschriften op een ingetrokken code,
    waarvan 83 'Zwevende stof'. Gemeten op 2026-11-13 tegen de live Atlas plus de ruwe
    Aquo-domeintabel (niet de voorgefilterde JSON, die laat ingetrokken codes juist weg --
    zie aquo.py): dat klopt, dus hier wordt de 90/83 gepind in plaats van bijgesteld."""
    ref = aquo.laad(_AQUO_CSV)
    assert ref.get("beschikbaar"), f"Aquo-domeintabel niet leesbaar op {_AQUO_CSV}"

    totaal = 0
    per_naam = Counter()
    for v in register:
        verrijkt = aquo.verrijk(v, ref)
        for vs in verrijkt["voorschriften"]:
            if vs.get("aquo_status") == "Vervallen":
                totaal += 1
                per_naam[vs.get("parameter")] += 1

    assert totaal == 90, (
        f"{totaal} voorschriften op een vervallen code i.p.v. 90 -- plan §6 bijwerken als dit "
        "klopt, of signaal 2 (vervallen_code) nalopen als het een regressie is"
    )
    assert per_naam["Zwevende stof"] == 83, (
        f"'Zwevende stof' draagt {per_naam['Zwevende stof']} vervallen voorschriften i.p.v. 83 "
        "-- plan §6 bijwerken als dit klopt"
    )

# Fix-ronde 3 (R20-review): `test_de_normenset_is_echt_bereikbaar_via_de_configuratie` stond hier
# eerst, maar dit bestand draagt een module-brede `pytestmark` die alles skipt zonder
# `DSO_API_KEY` -- die test raakt geen netwerk en heeft die sleutel niet nodig (hij leest een
# lokaal JSON-bestand via `laad_normen`), dus zou in elke run zonder die sleutel stilzwijgend
# niet meelopen. Verplaatst naar `tests/test_api_toezicht.py`, dat geen skip-gate draagt.
