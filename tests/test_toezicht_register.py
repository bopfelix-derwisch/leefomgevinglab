"""`toezicht.register` -- de grens waarop het Atlas-register `toezicht` binnenkomt (eindreview,
bevindingen 1 en 3). Geen netwerk hier: beide functies werken uitsluitend op wat ze als argument
krijgen."""
from leefomgevinglab.usecases.toezicht import register


# == dedupliceer_voorschriften / voorbereid (bevinding 3) ========================================

def test_een_letterlijk_herhaalde_rij_telt_maar_een_keer():
    v = {"naam": "X", "voorschriften": [
        {"parameter": "Zink", "waarde": 0.5, "eenheid": "milligram per liter",
         "bemonstering": "Steekmonster", "rd": [1.0, 2.0]},
        {"parameter": "Zink", "waarde": 0.5, "eenheid": "milligram per liter",
         "bemonstering": "Steekmonster", "rd": [1.0, 2.0]},
    ]}
    uit = register.dedupliceer_voorschriften(v)
    assert len(uit["voorschriften"]) == 1


def test_een_ander_meetpunt_maakt_nog_geen_verschil_voorschrift():
    """`rd` (het meetpunt) telt niet mee in de sleutel -- dat is coördinaatmetadata, geen deel
    van de eis zelf. Twee anders identieke rijen met een andere coördinaat zijn nog steeds één
    duplicaat."""
    v = {"naam": "X", "voorschriften": [
        {"parameter": "Zink", "waarde": 0.5, "eenheid": "milligram per liter",
         "bemonstering": "Steekmonster", "rd": [1.0, 2.0]},
        {"parameter": "Zink", "waarde": 0.5, "eenheid": "milligram per liter",
         "bemonstering": "Steekmonster", "rd": [3.0, 4.0]},
    ]}
    uit = register.dedupliceer_voorschriften(v)
    assert len(uit["voorschriften"]) == 1


def test_een_ander_bemonsteringsregime_is_geen_duplicaat():
    """Anders dan `gebruiksruimte.atlas_register._dedupe`: het regime telt hier mee, want signaal
    9 (`niet_regime_zuiver`) gaat juist over welk regime een voorschrift draagt. Twee voorschriften
    met dezelfde parameter/waarde/eenheid maar een ander regime zijn twee verschillende eisen."""
    v = {"naam": "X", "voorschriften": [
        {"parameter": "Zink", "waarde": 0.5, "eenheid": "milligram per liter",
         "bemonstering": "Steekmonster"},
        {"parameter": "Zink", "waarde": 0.5, "eenheid": "milligram per liter",
         "bemonstering": "Verzamelmonster gedurende 24 uur"},
    ]}
    uit = register.dedupliceer_voorschriften(v)
    assert len(uit["voorschriften"]) == 2


def test_parameter_en_eenheid_worden_case_en_spatie_ongevoelig_vergeleken():
    v = {"naam": "X", "voorschriften": [
        {"parameter": "Zink", "waarde": 0.5, "eenheid": "Milligram per liter  ",
         "bemonstering": "Steekmonster"},
        {"parameter": " zink", "waarde": 0.5, "eenheid": "milligram per liter",
         "bemonstering": "steekmonster"},
    ]}
    uit = register.dedupliceer_voorschriften(v)
    assert len(uit["voorschriften"]) == 1


def test_de_vestiging_zelf_blijft_verder_onaangeroerd():
    v = {"naam": "X", "kenmerk": "K1", "voorschriften": [
        {"parameter": "Zink", "waarde": 0.5, "eenheid": "milligram per liter"},
    ]}
    uit = register.dedupliceer_voorschriften(v)
    assert uit["naam"] == "X"
    assert uit["kenmerk"] == "K1"


def test_voorbereid_dedupliceert_elke_vestiging_in_het_register():
    register_lijst = [
        {"naam": "A", "voorschriften": [
            {"parameter": "Zink", "waarde": 0.5, "eenheid": "milligram per liter"},
            {"parameter": "Zink", "waarde": 0.5, "eenheid": "milligram per liter"},
        ]},
        {"naam": "B", "voorschriften": [
            {"parameter": "Lood", "waarde": 0.1, "eenheid": "milligram per liter"},
        ]},
    ]
    uit = register.voorbereid(register_lijst)
    assert [len(v["voorschriften"]) for v in uit] == [1, 1]


# == identiteiten (bevinding 1) ===================================================================

def test_een_unieke_locatiecode_blijft_zichzelf():
    reg = [{"locatiecode": "A", "kenmerk": "K1"}, {"locatiecode": "B", "kenmerk": "K2"}]
    assert register.identiteiten(reg) == ["A", "B"]


def test_een_dubbele_locatiecode_krijgt_twee_verschillende_identiteiten():
    """Het letterlijke CORUSNB/Tata Steel-geval: twee vergunningen van dezelfde vestiging onder
    dezelfde locatiecode, onderscheiden via hun kenmerk."""
    reg = [
        {"locatiecode": "CORUSNB", "kenmerk": "RWS-2015/19557"},
        {"locatiecode": "CORUSNB", "kenmerk": "RWS/DNB-2012/5083"},
    ]
    ids = register.identiteiten(reg)
    assert len(ids) == len(set(ids)) == 2
    assert ids[0] != ids[1]
    assert all(i.startswith("CORUSNB") for i in ids)


def test_een_dubbele_locatiecode_met_een_ontbrekend_kenmerk_blijft_uniek():
    """Het RWZIV-geval: van de twee entries onder dezelfde locatiecode heeft er één geen
    kenmerk. Laag 2 (`locatiecode` + `kenmerk`) is dan nog steeds uniek, want `None` != een
    echt kenmerk."""
    reg = [
        {"locatiecode": "RWZIV", "kenmerk": None},
        {"locatiecode": "RWZIV", "kenmerk": "RWS-2019/23694"},
    ]
    ids = register.identiteiten(reg)
    assert len(ids) == len(set(ids)) == 2


def test_een_degeneratief_geval_waar_zelfs_kenmerk_niet_uniek_maakt_valt_terug_op_een_volgnummer():
    """Verdedigend: zelfs als twee vestigingen zowel dezelfde locatiecode als hetzelfde (of
    allebei ontbrekend) kenmerk delen, mag deze functie nooit twee keer dezelfde identiteit
    teruggeven."""
    reg = [
        {"locatiecode": "X", "kenmerk": None},
        {"locatiecode": "X", "kenmerk": None},
        {"locatiecode": "X", "kenmerk": "K"},
    ]
    ids = register.identiteiten(reg)
    assert len(ids) == len(set(ids)) == 3


def test_identiteiten_houdt_het_hele_register_uniek_ook_bij_meerdere_dubbele_paren():
    """Niet alleen één dubbel paar -- live staan er acht naast elkaar (CORUSNB, RMP, HOECHSTNB,
    RWZIV, POORTERNB, CREVECOEUR, CROSF, NUTRC)."""
    reg = []
    for lc in ("CORUSNB", "RMP", "HOECHSTNB", "RWZIV", "POORTERNB", "CREVECOEUR", "CROSF",
               "NUTRC"):
        reg.append({"locatiecode": lc, "kenmerk": f"{lc}-A"})
        reg.append({"locatiecode": lc, "kenmerk": f"{lc}-B"})
    reg.append({"locatiecode": "SOLO", "kenmerk": "S1"})
    ids = register.identiteiten(reg)
    assert len(ids) == len(set(ids)) == len(reg)
