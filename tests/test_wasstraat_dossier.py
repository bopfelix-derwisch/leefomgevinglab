"""`wasstraat.dossier` -- het papierdossier, gefilterd uit hetzelfde signaaldossier als
`/toezicht`.

Geen netwerk: `papier_dossier()` werkt uitsluitend op wat `toezicht.dossier.dossier()` al
teruggeeft. De grote fixture (`VESTIGING_MET_ALLES`/`CONTEXT_MET_ALLES`) komt uit
`test_toezicht_signalen.py` en laat alle tien signaalregels vuren -- dus ook alle zeven
papierregels tegelijk, wat de volledigheidstest hieronder nodig heeft.
"""
from leefomgevinglab.usecases.toezicht import dossier as toezicht_dossier
from leefomgevinglab.usecases.toezicht import runlog as toezicht_runlog
from leefomgevinglab.usecases.toezicht import signalen
from leefomgevinglab.usecases.wasstraat import dossier as wasstraat_dossier
from tests.test_toezicht_signalen import CONTEXT_MET_ALLES, VESTIGING_MET_ALLES

_WERKELIJKHEID_REGELS = {"geen_onafhankelijke_meting", "norm_overschreden_bovenstrooms",
                          "stof_buiten_register"}
_PAPIER_REGELS = set(signalen.DREMPELS) - _WERKELIJKHEID_REGELS


def _volledig_dossier(runlog=None):
    return toezicht_dossier.dossier(VESTIGING_MET_ALLES, CONTEXT_MET_ALLES, runlog=runlog)


# -- Filteren op laag -----------------------------------------------------------------------

def test_papier_dossier_bevat_alleen_de_zeven_papiersignalen():
    volledig = _volledig_dossier()
    d = wasstraat_dossier.papier_dossier(volledig)
    regel_ids = {s["regel"] for s in d["signalen"]}
    assert regel_ids == _PAPIER_REGELS
    assert regel_ids.isdisjoint(_WERKELIJKHEID_REGELS)


def test_papier_dossier_laat_de_kaart_ongewijzigd():
    volledig = _volledig_dossier()
    d = wasstraat_dossier.papier_dossier(volledig)
    assert d["kaart"] == volledig["kaart"]


def test_elk_papiersignaal_draagt_een_reparatie():
    volledig = _volledig_dossier()
    d = wasstraat_dossier.papier_dossier(volledig)
    for s in d["signalen"]:
        assert s.get("reparatie"), s["regel"]


def test_de_reparatiecatalogus_dekt_precies_de_zeven_papierregels():
    """Geen regel zonder reparatie, en geen reparatie voor een werkelijkheidsregel die hier
    toevallig nooit gevraagd wordt."""
    assert set(wasstraat_dossier._REPARATIE_PER_REGEL) == _PAPIER_REGELS


# -- Telling en voorbehouden, opnieuw afgeleid -----------------------------------------------

def test_de_telling_telt_alleen_de_papiersignalen():
    volledig = _volledig_dossier()
    d = wasstraat_dossier.papier_dossier(volledig)
    assert d["telling"]["aantal_signalen"] == len(d["signalen"])
    assert set(d["telling"]["per_regel"]) == _PAPIER_REGELS
    assert sum(d["telling"]["per_zwaarte"].values()) == len(d["signalen"])


def test_de_telling_behoudt_het_aantal_voorschriften_van_het_volledige_dossier():
    volledig = _volledig_dossier()
    d = wasstraat_dossier.papier_dossier(volledig)
    assert d["telling"]["aantal_voorschriften"] == volledig["telling"]["aantal_voorschriften"]


def test_voorbehouden_over_werkelijkheidssignalen_worden_weggefilterd():
    """Context zonder `gemeten_codes`/`waterlichaam`/`register_codes`/`stoffen_met_norm` levert
    in het volledige dossier vier voorbehouden op die alleen over de drie
    werkelijkheidssignalen gaan -- die horen niet op de papierpagina."""
    volledig = toezicht_dossier.dossier(VESTIGING_MET_ALLES, {})
    d = wasstraat_dossier.papier_dossier(volledig)
    for kop in ("geen onafhankelijke meting", "meting boven de norm, lozer bovenstrooms",
                "gemeten stof die in geen vergunning staat"):
        assert not any(f"'{kop}'" in v for v in d["voorbehouden"]), kop
    # De algemene slotzin blijft staan.
    assert any("stelt nooit vast" in v for v in d["voorbehouden"])


def test_de_uitgezette_agent_blijft_zichtbaar_in_de_voorbehouden():
    volledig = toezicht_dossier.dossier(VESTIGING_MET_ALLES, CONTEXT_MET_ALLES, uit={"uitlegger"})
    d = wasstraat_dossier.papier_dossier(volledig)
    assert any("uitlegger" in v for v in d["voorbehouden"])
    assert d["runlog"]["uitgezet"] == ["uitlegger"]


# -- De runlog: uitleg per stap en samenvatting ------------------------------------------------

def _gevulde_runlog() -> toezicht_runlog.Runlog:
    log = toezicht_runlog.Runlog()
    log.stap("vergunninglezer", "lees_vergunning", "atlas_vergunningen", 1, 1, False, duur=0.01)
    log.stap("signaalsteller", "bepaal_signalen", "signalen_stellen", 1, 10, False, duur=0.02)
    log.stap("dossiersteller", "stel_dossier_samen", "dossier_samenstellen", 1, 1, False,
             duur=0.03)
    log.stap("uitlegger", "leg_signalen_uit", "uitleg_genereren", 10, 3, False, duur=0.04)
    return log


def test_elke_stap_in_de_standaardpijplijn_krijgt_een_uitleg():
    volledig = _volledig_dossier(runlog=_gevulde_runlog())
    d = wasstraat_dossier.papier_dossier(volledig)
    stappen = d["runlog"]["stappen"]
    assert len(stappen) == 4
    for stap in stappen:
        assert stap["uitleg"], stap["taak"]
        assert stap["uitleg"] != wasstraat_dossier._GEEN_UITLEG


def test_een_onbekende_taak_krijgt_de_generieke_uitleg_in_plaats_van_te_crashen():
    assert wasstraat_dossier._stap_uitleg("iets_wat_niet_bestaat") == wasstraat_dossier._GEEN_UITLEG


def test_de_samenvatting_telt_stappen_rijen_en_duur_op():
    volledig = _volledig_dossier(runlog=_gevulde_runlog())
    d = wasstraat_dossier.papier_dossier(volledig)
    s = d["runlog"]["samenvatting"]
    assert s["aantal_stappen"] == 4
    assert s["rijen_in_totaal"] == 1 + 1 + 1 + 10
    assert s["rijen_uit_totaal"] == 1 + 10 + 1 + 3
    assert abs(s["totale_duur"] - 0.10) < 1e-9
    assert s["stappen_met_taalmodel"] == []
    assert "Geen van de stappen heeft een taalmodel aangeroepen" in s["zin"]


def test_de_samenvatting_noemt_de_agents_die_echt_een_taalmodel_gebruikten():
    log = _gevulde_runlog()
    # Herschrijf de laatste stap als een echte taalmodelaanroep.
    log._stappen[-1]["llm"] = True
    volledig = _volledig_dossier(runlog=log)
    d = wasstraat_dossier.papier_dossier(volledig)
    s = d["runlog"]["samenvatting"]
    assert s["stappen_met_taalmodel"] == ["uitlegger"]
    assert "uitlegger" in s["zin"]
    assert "Geen van de stappen" not in s["zin"]


def test_de_samenvatting_zonder_stappen_meldt_dat_er_nog_geen_dossier_is():
    d = wasstraat_dossier.papier_dossier(_volledig_dossier())
    s = d["runlog"]["samenvatting"]
    assert s["aantal_stappen"] == 0
    assert s["zin"] == "Nog geen dossier opgevraagd."


# -- Taalregel, ook op de nieuwe teksten -------------------------------------------------------

def test_reparatieteksten_zijn_nooit_een_vaststelling():
    for tekst in wasstraat_dossier._REPARATIE_PER_REGEL.values():
        laag = tekst.lower()
        for verboden in ("overtreding", "veroorzaakt door", "in strijd met"):
            assert verboden not in laag, tekst


def test_stapuitleg_is_nooit_een_vaststelling():
    for tekst in wasstraat_dossier._STAP_UITLEG.values():
        laag = tekst.lower()
        for verboden in ("overtreding", "veroorzaakt door", "in strijd met"):
            assert verboden not in laag, tekst
