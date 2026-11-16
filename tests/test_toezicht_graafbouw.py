"""`toezicht.graafbouw` -- één bouwer voor de register-brede graaf, met twee aanroepers.

**Waarom deze module bestaat.** De route (`/api/toezicht/vraag`) bouwde de graaf zelf, en
`scripts/22_bouw_toezichtgraaf.py` bouwde hem ook -- maar zonder context, dus zonder signalen.
Twee bouwers die hetzelfde heten en iets anders maken is precies het patroon waar dit project het
meeste aan heeft verloren: het bestand op schijf zou dan stil een andere graaf zijn dan de route
in het geheugen heeft, en een antwoord zou afhangen van welke van de twee toevallig gebruikt werd.
Deze tests leggen vast dat er één bouwer is en wat hij oplevert.
"""
import pytest

from leefomgevinglab.ld.store import run_sparql
from leefomgevinglab.usecases.toezicht import graaf as graaf_mod
from leefomgevinglab.usecases.toezicht import graafbouw
from tests.test_toezicht_graaf import AQUO_FIXTURE, METINGEN_FIXTURE, REGISTER_FIXTURE


def _rijen(g, waar: str):
    return run_sparql(g, f"PREFIX t: <{graaf_mod.T}>\nSELECT * WHERE {{ {waar} }} LIMIT 200")


def _bronnen(**overschrijf):
    """De zes bronnen die de bouwer nodig heeft, als fixture. `waterlichaam_per_vergunning` is
    hier een gewone functie zodat geen test het netwerk raakt -- in productie is dat de
    parallelle opzoeking uit `kmg_service`."""
    bronnen = {
        "register": REGISTER_FIXTURE,
        "metingen": METINGEN_FIXTURE,
        "normen": {"beschikbaar": False, "normen": {}},
        "aquo_ref": AQUO_FIXTURE,
        "overschrijdingen": [{"meetpunt": "NL91_TESTPUNT", "waterlichaam": "NL91BM",
                               "stof": "Zn", "gemeten": 9.0, "norm": 7.8, "eenheid": "ug/l"}],
        "gemeten_codes": {"Zn"},
        "stoffen_met_norm": {"Zn"},
        "waterlichaam_per_vergunning": lambda reg: {
            (v.get("kenmerk"), v.get("locatiecode")): v.get("waterlichaam") for v in reg},
    }
    bronnen.update(overschrijf)
    return bronnen


def test_de_bouwer_levert_een_graaf_met_de_signalen_erin():
    """Het verschil met `scripts/22` zoals het was: dáár zat geen context, dus geen `t:Signaal`,
    dus geen brug tussen de twee lezers. Een gepersisteerde graaf zonder signalen zou de
    chatbox stil halveren."""
    g = graafbouw.bouw(**_bronnen())
    assert _rijen(g, "?s a t:Signaal ; t:laag ?laag"), "geen signalen in de gebouwde graaf"
    lagen = {str(r["laag"]) for r in _rijen(g, "?s a t:Signaal ; t:laag ?laag")}
    assert lagen == {"papier", "werkelijkheid"}, (
        f"beide lagen horen erin te zitten, gevonden: {lagen}")


def test_het_waterlichaam_komt_per_vestiging_en_niet_een_voor_allemaal():
    """De duurste fout die deze graaf kan maken. Zou elke vestiging hetzelfde waterlichaam
    krijgen, dan vuurt `norm_overschreden_bovenstrooms` op het hele register met een richting die
    voor vrijwel elke vergunning onjuist is."""
    gezien = {}

    def per_vergunning(reg):
        gezien["aangeroepen"] = len(reg)
        # Alleen de eerste vestiging krijgt een waterlichaam.
        eerste = reg[0]
        return {(eerste.get("kenmerk"), eerste.get("locatiecode")): "NL91BM"}

    g = graafbouw.bouw(**_bronnen(waterlichaam_per_vergunning=per_vergunning))
    assert gezien["aangeroepen"] == len(REGISTER_FIXTURE), (
        "de opzoeking hoort één keer over het hele register te gaan, niet per vestiging opnieuw")
    # Alleen de vestiging mét waterlichaam kan een bovenstrooms-signaal dragen.
    rijen = _rijen(g, '?v t:naam ?naam ; t:heeftSignaal ?s . '
                       '?s t:regel "norm_overschreden_bovenstrooms"')
    namen = {str(r["naam"]) for r in rijen}
    assert namen <= {REGISTER_FIXTURE[0]["naam"]}, (
        f"een vestiging zonder waterlichaam draagt een richtingsignaal: {namen}")


def test_de_bouwer_geeft_ook_een_telling_terug_die_is_afgeleid():
    """De route en het script tonen beide hoe groot de graaf is; dat getal komt uit de graaf en
    wordt niet door een van de twee geteld (of getypt)."""
    g, telling = graafbouw.bouw_met_telling(**_bronnen())
    assert telling["triples"] == len(g)
    assert telling["vestigingen"] == len(REGISTER_FIXTURE)
    assert telling["signalen"] == len(_rijen(g, "?s a t:Signaal"))
    assert telling["voorschriften"] == sum(
        len(v["voorschriften"]) for v in REGISTER_FIXTURE)


def test_de_telling_komt_uit_de_graaf_en_niet_uit_het_register_ernaast():
    """Twee paden gebruiken deze telling: de route die live bouwt (en het register als lijst
    heeft) en de route die de graaf van schijf leest (waar dat register niet bestaat). Zou de
    telling het register nodig hebben, dan moest het tweede pad een getal verzinnen -- en stond er
    op de pagina een aantal vestigingen dat niet uit de graaf komt die de vragen beantwoordt."""
    g = graafbouw.bouw(**_bronnen())
    assert graafbouw.telling(g) == graafbouw.telling(g), "geen verborgen toestand"
    # Dezelfde telling, zonder enig register als argument.
    assert graafbouw.telling(g)["vestigingen"] == len(REGISTER_FIXTURE)


def test_een_leeg_register_valt_luid_om_in_plaats_van_een_lege_graaf_te_geven():
    """Een lege graaf is het ergste antwoord dat deze laag kan geven: elke vraag levert dan "geen
    resultaten", wat leest als "er is niets aan de hand". Hetzelfde voorbehoud dat `scripts/22`
    al maakte bij een leeg Atlas-antwoord."""
    with pytest.raises(ValueError, match="leeg register"):
        graafbouw.bouw(**_bronnen(register=[]))
