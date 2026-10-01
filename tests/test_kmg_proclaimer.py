from leefomgevinglab.usecases.kmg import proclaimer

MEETSET = {
    "beschikbaar": True, "meetjaar": "2025", "opgehaald_op": "2026-10-01",
    "bron": {"naam": "Waterkwaliteitsportaal", "houder": "Informatiehuis Water",
             "url": "https://wkp.rws.nl/downloadmodule"},
    "punten": [{"code": "A", "stoffen": [{"code": "Ntot", "n": 52},
                                         {"code": "Zn", "n": 104}]}],
    "telling": {"meegeteld": 156, "hiaatwaarden": 3000},
}
REGISTER_BRON = {"echt": True, "bron": {"naam": "Atlas voor een Schone Maas"}}


def _tekst(p):
    return " ".join(k["tekst"] for k in p["kopjes"]).lower()


def test_de_proclaimer_heeft_vier_kopjes():
    p = proclaimer.bouw(MEETSET, REGISTER_BRON, "DSO Ozon", doelen_beschikbaar=True)
    assert len(p["kopjes"]) == 4
    for k in p["kopjes"]:
        assert k["kop"] and k["tekst"]


def test_het_meetjaar_komt_uit_de_data_niet_uit_een_vaste_tekst():
    p = proclaimer.bouw({**MEETSET, "meetjaar": "2024"}, REGISTER_BRON, "DSO Ozon", True)
    assert "2024" in _tekst(p)
    assert "2025" not in _tekst(p)


def test_het_aantal_metingen_klopt_met_de_meetset():
    p = proclaimer.bouw(MEETSET, REGISTER_BRON, "DSO Ozon", True)
    assert p["gegevens"]["metingen"] == 156
    assert "156" in _tekst(p)


def test_de_bronhouder_wordt_genoemd():
    p = proclaimer.bouw(MEETSET, REGISTER_BRON, "DSO Ozon", True)
    assert "informatiehuis water" in _tekst(p)
    assert "atlas voor een schone maas" in _tekst(p)


def test_het_gat_wordt_benoemd_met_een_datum():
    p = proclaimer.bouw(MEETSET, REGISTER_BRON, "DSO Ozon", True)
    t = _tekst(p)
    assert "2027" in t, "de WKP-module komt begin 2027 — dat hoort erbij"
    assert "401" in t, "de Digitale Delta API geeft vandaag 401"


def test_zonder_meetset_zegt_de_proclaimer_dat():
    leeg = {"beschikbaar": False, "punten": [], "telling": {},
            "reden": "geen meetset gevonden", "meetjaar": None, "bron": None,
            "opgehaald_op": None}
    p = proclaimer.bouw(leeg, REGISTER_BRON, "DSO Ozon", True)
    assert "geen meetgegevens" in _tekst(p)


def test_zonder_krw_doelen_zegt_de_proclaimer_dat():
    p = proclaimer.bouw(MEETSET, REGISTER_BRON, "DSO Ozon", doelen_beschikbaar=False)
    assert "geen krw-doel" in _tekst(p) or "zonder normoordeel" in _tekst(p)


def test_de_proclaimer_belooft_geen_vaststelling():
    p = proclaimer.bouw(MEETSET, REGISTER_BRON, "DSO Ozon", True)
    t = _tekst(p)
    assert "veroorzaakt door" not in t
    assert "toezicht" in t


def test_de_tellingen_claimen_niets_over_deze_pagina():
    meetset_multi = {**MEETSET, "punten": [{"code": "A", "stoffen": [{"code": "Ntot", "n": 52}, {"code": "Zn", "n": 104}]}, {"code": "B", "stoffen": [{"code": "Ntot", "n": 52}]}]}
    p = proclaimer.bouw(meetset_multi, REGISTER_BRON, "DSO Ozon", True, punten_in_beeld=1)
    t = _tekst(p)
    assert "landelijke set" in t
    assert "alleen die staan in de keuzelijst" in t
    assert p["gegevens"]["punten_in_beeld"] == 1


def test_zonder_beperking_wordt_er_niets_over_een_keuzelijst_gezegd():
    p = proclaimer.bouw(MEETSET, REGISTER_BRON, "DSO Ozon", True)
    assert "keuzelijst" not in _tekst(p)
    assert p["gegevens"]["punten_in_beeld"] is None


def test_zonder_meetset_wordt_geen_momentopname_beweerd():
    leeg = {"beschikbaar": False, "punten": [], "telling": {},
            "reden": "geen meetset gevonden", "meetjaar": None, "bron": None,
            "opgehaald_op": None}
    p = proclaimer.bouw(leeg, REGISTER_BRON, "DSO Ozon", True)
    t = _tekst(p)
    assert "onbekende datum" not in t
    assert "geen opgehaald" in t


def test_een_echte_nul_telt_als_nul():
    nul = {**MEETSET, "telling": {"meegeteld": 0, "hiaatwaarden": 0},
           "punten": [{"code": "A", "stoffen": [{"code": "Ntot", "n": 7}]}]}
    p = proclaimer.bouw(nul, REGISTER_BRON, "DSO Ozon", True)
    assert p["gegevens"]["metingen"] == 0, "7 zou betekenen dat de terugval ten onrechte aansloeg"
