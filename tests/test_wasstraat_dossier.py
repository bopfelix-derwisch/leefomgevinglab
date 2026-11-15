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
# De tweede as (eindreview, must-fix 5+6): twee van de zeven papierregels zijn een voorbehoud,
# geen bevinding. Hier net als in de code afgeleid uit de drempel, niet opnieuw getypt -- een
# derde sentinelregel komt zo automatisch in deze tests mee.
_VOORBEHOUD_REGELS = {r for r in _PAPIER_REGELS if signalen.is_voorbehoud(r)}
_BEVINDING_REGELS = _PAPIER_REGELS - _VOORBEHOUD_REGELS


def _volledig_dossier(runlog=None):
    return toezicht_dossier.dossier(VESTIGING_MET_ALLES, CONTEXT_MET_ALLES, runlog=runlog)


# -- Filteren op laag -----------------------------------------------------------------------

def test_papier_dossier_bevat_alleen_de_papierbevindingen():
    """Niet alle zeven papierregels: de twee sentinelregels zijn een voorbehoud en landen in het
    voorbehouden-blok (zie de tests daarover hieronder)."""
    volledig = _volledig_dossier()
    d = wasstraat_dossier.papier_dossier(volledig)
    regel_ids = {s["regel"] for s in d["signalen"]}
    assert regel_ids == _BEVINDING_REGELS
    assert regel_ids.isdisjoint(_WERKELIJKHEID_REGELS)
    assert regel_ids.isdisjoint(_VOORBEHOUD_REGELS)


def test_papier_dossier_laat_de_kaart_ongewijzigd_op_het_waterlichaam_na():
    volledig = _volledig_dossier()
    d = wasstraat_dossier.papier_dossier(volledig)
    assert d["kaart"] == {k: v for k, v in volledig["kaart"].items() if k != "waterlichaam"}


def test_de_papierkaart_draagt_het_waterlichaam_niet():
    """**Waarom dit veld hier niet hoort -- lees dit voordat je het terugzet.**

    Het waterlichaam is een feit over de werkelijkheid, niet over het papier: het staat in geen
    van de vijf papierbevindingen, en de vergunningverlener kan er niets mee. De Atlas draagt het
    veld nooit (zie `toezicht.dossier._kaart`, die alleen leest), dus `dossier()` gaf hier altijd
    `{"waarde": None, "zekerheid": "ontbreekt"}` -- en de wasstraatkaart zette daar haar rode
    ontbrekend-signaal op, voor alle 69 vergunningen. `/toezicht` wéét het wél
    (`weergave.werkelijkheid_dossier` vult het uit een coördinaatopzoeking, zekerheid
    `afgeleid`), dus twee publieke pagina's spraken elkaar tegen over hetzelfde feit (eindreview,
    must-fix 3). De opzoeking hier kopiëren zou deze pagina een netwerkronde kosten voor een veld
    dat zij niet nodig heeft; het veld weglaten is de goedkopere én de juiste keuze."""
    volledig = _volledig_dossier()
    assert "waterlichaam" in volledig["kaart"], "het volledige dossier draagt het veld nog wel"
    d = wasstraat_dossier.papier_dossier(volledig)
    assert "waterlichaam" not in d["kaart"]


def test_elk_papiersignaal_draagt_een_reparatie():
    volledig = _volledig_dossier()
    d = wasstraat_dossier.papier_dossier(volledig)
    for s in d["signalen"]:
        assert s.get("reparatie"), s["regel"]


def test_de_reparatiecatalogus_dekt_precies_de_papierbevindingen():
    """Geen bevinding zonder reparatie, en geen reparatie voor een regel die geen bevinding is.

    De twee sentinelregels stonden hier eerder wél in, met een reparatie die de
    vergunningverlener niet kan of niet hoeft uit te voeren: `niet_regime_zuiver` vroeg om het
    bemonsteringsregime te vermelden terwijl de regel juist alleen vuurt als het er staat, en
    `geen_geldigheidsduur` vroeg om een geldigheidsperiode die de Atlas per voorschrift niet
    kent (69 van de 69 kregen die instructie). Zie must-fix 5+6 van de eindreview."""
    assert set(wasstraat_dossier._REPARATIE_PER_REGEL) == _BEVINDING_REGELS
    assert set(wasstraat_dossier._REPARATIE_PER_REGEL).isdisjoint(_VOORBEHOUD_REGELS)


def test_de_voorbehoudcatalogus_dekt_precies_de_sentinelregels():
    assert set(wasstraat_dossier._VOORBEHOUD_PER_REGEL) == _VOORBEHOUD_REGELS


def test_de_twee_catalogi_dekken_samen_de_zeven_papierregels_zonder_overlap():
    """Elke papierregel landt ergens -- als bevinding mét reparatie, of als voorbehoud mét
    uitleg. Geen regel valt stil tussen de twee."""
    reparaties = set(wasstraat_dossier._REPARATIE_PER_REGEL)
    voorbehouden = set(wasstraat_dossier._VOORBEHOUD_PER_REGEL)
    assert reparaties & voorbehouden == set()
    assert reparaties | voorbehouden == _PAPIER_REGELS


# -- De sentinelregels landen in het voorbehouden-blok ----------------------------------------

def test_de_sentinelregels_landen_als_voorbehoud_en_niet_als_bevinding():
    volledig = _volledig_dossier()
    d = wasstraat_dossier.papier_dossier(volledig)
    tekst = " ".join(d["voorbehouden"])
    for kop in ("bemonsteringsregime", "geldigheidsperiode"):
        assert kop in tekst, kop
    assert all(s["regel"] not in _VOORBEHOUD_REGELS for s in d["signalen"])


def test_een_voorbehoudzin_draagt_de_bewering_van_het_signaal():
    """Het getal verdwijnt niet: de bewering van het signaal blijft staan, met de uitleg waarom
    zij geen bevinding is erachter."""
    volledig = _volledig_dossier()
    signaal = next(s for s in volledig["signalen"] if s["regel"] == "geen_geldigheidsduur")
    d = wasstraat_dossier.papier_dossier(volledig)
    assert any(signaal["bewering"] in v for v in d["voorbehouden"])


def test_de_generieke_slotzin_blijft_achteraan_staan():
    volledig = _volledig_dossier()
    d = wasstraat_dossier.papier_dossier(volledig)
    assert d["voorbehouden"][-1] == toezicht_dossier.SLOTZIN


def test_de_telling_noemt_het_aantal_voorbehouden_apart():
    volledig = _volledig_dossier()
    d = wasstraat_dossier.papier_dossier(volledig)
    assert d["telling"]["aantal_voorbehouden"] == len(_VOORBEHOUD_REGELS)
    assert d["telling"]["aantal_signalen"] == len(d["signalen"])


# -- Telling en voorbehouden, opnieuw afgeleid -----------------------------------------------

def test_de_telling_telt_alleen_de_papierbevindingen():
    volledig = _volledig_dossier()
    d = wasstraat_dossier.papier_dossier(volledig)
    assert d["telling"]["aantal_signalen"] == len(d["signalen"])
    assert set(d["telling"]["per_regel"]) == _BEVINDING_REGELS
    assert sum(d["telling"]["per_zwaarte"].values()) == len(d["signalen"])


def test_de_telling_behoudt_het_aantal_voorschriften_van_het_volledige_dossier():
    volledig = _volledig_dossier()
    d = wasstraat_dossier.papier_dossier(volledig)
    assert d["telling"]["aantal_voorschriften"] == volledig["telling"]["aantal_voorschriften"]


def test_voorbehouden_over_werkelijkheidssignalen_worden_weggefilterd():
    """Context zonder `gemeten_codes`/`waterlichaam`/`register_codes`/`stoffen_met_norm` levert
    in het volledige dossier vier voorbehouden op die alleen over de drie
    werkelijkheidssignalen gaan -- die horen niet op de papierpagina.

    **Deze test asserteert op exacte gelijkheid, niet op de filterconstructie zelf.** De eerdere
    versie zocht met `f"'{kop}'" in v` -- precies de constructie waarmee `_voorbehouden_papier`
    filtert -- en deelde daarmee de aanname die zij moest bewaken: een werkelijkheidsvoorbehoud
    dat de kop zónder aanhalingstekens noemt, kwam ongefilterd op `/wasstraat` terecht terwijl de
    test groen bleef (eindreview, kleinere bevinding 1). Nu staat er welke zinnen er precies
    horen te staan, dus een zin die erbij komt of afvalt valt om."""
    volledig = toezicht_dossier.dossier(VESTIGING_MET_ALLES, {})
    verwacht_weg = [v for v in volledig["voorbehouden"] if v != toezicht_dossier.SLOTZIN]
    assert len(verwacht_weg) == 4, "de vier contextvoorbehouden van een lege context"
    d = wasstraat_dossier.papier_dossier(volledig)
    eigen = [wasstraat_dossier._voorbehoud_zin(s) for s in volledig["signalen"]
             if s["regel"] in _VOORBEHOUD_REGELS]
    assert d["voorbehouden"] == eigen + [toezicht_dossier.SLOTZIN]


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

def test_voorbehoudteksten_zijn_nooit_een_vaststelling():
    for tekst in wasstraat_dossier._VOORBEHOUD_PER_REGEL.values():
        laag = tekst.lower()
        for verboden in ("overtreding", "veroorzaakt door", "in strijd met"):
            assert verboden not in laag, tekst


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
