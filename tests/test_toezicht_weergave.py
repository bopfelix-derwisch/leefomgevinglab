"""`toezicht.weergave` -- de spiegeling van `wasstraat.dossier.papier_dossier()` voor
`/toezicht`: filtert het volledige tien-signalendossier naar de drie werkelijkheidssignalen en
voegt de wasstraat-uitkomst en de metingen toe."""
from leefomgevinglab.usecases.toezicht import weergave

# Twee papiersignalen en twee werkelijkheidssignalen, genoeg om de filtering en de telling te
# bewijzen zonder de hele pijplijn te draaien.
VOLLEDIG = {
    "kaart": {"naam": {"waarde": "Test BV", "zekerheid": "uit de bron"},
              "waterlichaam": {"waarde": None, "zekerheid": "ontbreekt"}},
    "signalen": [
        {"regel": "vervallen_code", "signaal": "grenswaarde op een ingetrokken code",
         "zwaarte": "hoog", "omvang": 2, "bewijs": []},
        {"regel": "geen_geldigheidsduur", "signaal": "geen geldigheidsduur",
         "zwaarte": "laag", "omvang": 3, "bewijs": []},
        {"regel": "geen_onafhankelijke_meting", "signaal": "geen onafhankelijke meting",
         "zwaarte": "midden", "omvang": 1, "bewijs": []},
        {"regel": "stof_buiten_register", "signaal": "gemeten stof die in geen vergunning staat",
         "zwaarte": "hoog", "omvang": 1, "bewijs": []},
    ],
    "telling": {"aantal_voorschriften": 7},
    "voorbehouden": ["Een signaal in dit dossier stelt nooit vast dat iets niet mag."],
    "runlog": {"uitgezet": [], "stappen": [{"nr": 1, "agent": "x"}]},
}


# -- wasstraat_samenvatting -----------------------------------------------------------------

def test_wasstraat_samenvatting_telt_alleen_de_papierbevindingen():
    """`geen_geldigheidsduur` is een sentinelregel (`signalen.is_voorbehoud`) en telt dus niet
    mee -- alleen `vervallen_code` blijft over (eindreview, must-fix 5+6)."""
    s = weergave.wasstraat_samenvatting(VOLLEDIG["signalen"])
    assert s["aantal_open"] == 1
    assert s["op_orde"] is False
    assert s["pad"] == "/wasstraat"


def test_wasstraat_samenvatting_is_op_orde_op_een_vergunning_met_alleen_voorbehouden():
    """De True-tak op een toestand die het register wél kent.

    Vóór must-fix 5+6 toetste deze test de True-tak op een lege signaallijst -- een vergunning
    zonder enig papiersignaal, en die bestaat in het Maas-register niet: `geen_geldigheidsduur`
    vuurt op 69 van de 69 en `niet_regime_zuiver` op 68 van de 69, dus het minimum was 1 en
    `op_orde` was onbereikbaar. Hier staat de echte toestand: twee werkelijkheidssignalen plus de
    twee sentinelvoorbehouden die élke vergunning draagt, en geen bevinding. Dát is "het papier
    is op orde"."""
    met_voorbehouden = [s for s in VOLLEDIG["signalen"] if s["regel"] != "vervallen_code"]
    assert {s["regel"] for s in met_voorbehouden} == {
        "geen_geldigheidsduur", "geen_onafhankelijke_meting", "stof_buiten_register"}
    s = weergave.wasstraat_samenvatting(met_voorbehouden)
    assert s["aantal_open"] == 0
    assert s["op_orde"] is True


# -- werkelijkheid_dossier --------------------------------------------------------------------

def test_werkelijkheid_dossier_filtert_naar_de_drie_werkelijkheidsregels():
    d = weergave.werkelijkheid_dossier(VOLLEDIG)
    regels = {s["regel"] for s in d["signalen"]}
    assert regels == {"geen_onafhankelijke_meting", "stof_buiten_register"}
    assert all(s["regel"] not in ("vervallen_code", "geen_geldigheidsduur") for s in d["signalen"])


def test_werkelijkheid_dossier_telt_opnieuw_over_de_gefilterde_lijst():
    d = weergave.werkelijkheid_dossier(VOLLEDIG)
    assert d["telling"]["aantal_signalen"] == 2
    assert d["telling"]["per_zwaarte"] == {"hoog": 1, "midden": 1, "laag": 0}
    assert d["telling"]["aantal_voorschriften"] == 7, "dit getal komt ongewijzigd over"


def test_werkelijkheid_dossier_draagt_de_wasstraat_samenvatting():
    d = weergave.werkelijkheid_dossier(VOLLEDIG)
    assert d["wasstraat"]["aantal_open"] == 1
    assert d["wasstraat"]["op_orde"] is False


def test_werkelijkheid_dossier_laat_voorbehouden_en_runlog_ongewijzigd():
    d = weergave.werkelijkheid_dossier(VOLLEDIG)
    assert d["voorbehouden"] == VOLLEDIG["voorbehouden"]
    assert d["runlog"] == VOLLEDIG["runlog"]


def test_werkelijkheid_dossier_zonder_waterlichaam_toont_ontbreekt():
    d = weergave.werkelijkheid_dossier(VOLLEDIG)
    assert d["kaart"]["waterlichaam"] == {"waarde": None, "zekerheid": "ontbreekt"}
    assert d["metingen"]["waterlichaam"] is None
    assert d["metingen"]["rijen"] == []


def test_werkelijkheid_dossier_met_waterlichaam_zet_afgeleide_zekerheid():
    """`waterlichaam` is in de Atlas-bron nooit aanwezig (zie `dossier._kaart`) -- gevonden via
    een coördinaatopzoeking is dus `afgeleid`, niet `uit de bron`."""
    d = weergave.werkelijkheid_dossier(VOLLEDIG, waterlichaam="NL91ZM",
                                        metingen_rijen=[{"meetpunt": "X"}])
    assert d["kaart"]["waterlichaam"] == {"waarde": "NL91ZM", "zekerheid": "afgeleid"}
    assert d["metingen"]["waterlichaam"] == "NL91ZM"
    assert d["metingen"]["rijen"] == [{"meetpunt": "X"}]
    assert d["metingen"]["reden_geen_waterlichaam"] is None


def test_werkelijkheid_dossier_zonder_waterlichaam_draagt_de_reden():
    d = weergave.werkelijkheid_dossier(VOLLEDIG, waterlichaam=None,
                                        waterlichaam_reden="geen coördinaat in de bron")
    assert d["metingen"]["reden_geen_waterlichaam"] == "geen coördinaat in de bron"
