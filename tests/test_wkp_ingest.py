import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "scripts"))

OBJ_KOP = ("Meetjaar;WaterbeheerderCode;WaterbeheerderNaam;Namespace;Identificatie;"
           "MeetobjectCode;Omschrijving;GeometriePuntX_RD;GeometriePuntY_RD;"
           "KRWwatertypeCode;HoortbijGeoobjectIdentificatie\n")
WRD_KOP = ("Meetjaar;MeetobjectCode;MonsterCompartimentCode;Monsterophaaldatum;"
           "ParameterCode;ParameterOmschrijving;EenheidCode;Limietsymbool;"
           "Numeriekewaarde;KwaliteitsoordeelCode\n")


def _schrijf(tmp_path, objecten, waarden):
    o = tmp_path / "obj.csv"
    w = tmp_path / "wrd.csv"
    o.write_text(OBJ_KOP + "".join(objecten), encoding="utf-8-sig")
    w.write_text(WRD_KOP + "".join(waarden), encoding="utf-8-sig")
    return str(o), str(w)


def _obj(code="NL80_EIJSDPTN", naam="Eijsden ponton", x="176000", y="310000",
         wl="NL91BOM"):
    return f"2025;1;Rijkswaterstaat;NL80;x;{code};{naam};{x};{y};R7;{wl}\n"


def _wrd(code="NL80_EIJSDPTN", par="Ntot", eenheid="mg/l", waarde="3,3",
         kwal="00", limiet="", datum="2025-03-11"):
    return (f"2025;{code};;{datum};{par};stikstof totaal;{eenheid};{limiet};"
            f"{waarde};{kwal}\n")


def test_mediaan_en_maximum_per_punt_en_stof(tmp_path):
    import importlib
    m = importlib.import_module("13_fetch_wkp_metingen")
    o, w = _schrijf(tmp_path, [_obj()],
                    [_wrd(waarde="2,0"), _wrd(waarde="3,0"), _wrd(waarde="10,0")])
    d = m.verdicht(o, w, {"Ntot"})
    stof = d["punten"][0]["stoffen"][0]
    assert stof["n"] == 3
    assert stof["mediaan"] == 3.0
    assert stof["maximum"] == 10.0


def test_hiaatwaarden_tellen_niet_mee(tmp_path):
    """KwaliteitsoordeelCode 99 draagt de sentinel 999999999999."""
    import importlib
    m = importlib.import_module("13_fetch_wkp_metingen")
    o, w = _schrijf(tmp_path, [_obj()],
                    [_wrd(waarde="3,0"),
                     _wrd(waarde="999999999999", kwal="99"),
                     _wrd(waarde="5,0")])
    d = m.verdicht(o, w, {"Ntot"})
    stof = d["punten"][0]["stoffen"][0]
    assert stof["n"] == 2
    assert stof["maximum"] == 5.0
    assert d["telling"]["hiaatwaarden"] == 1


def test_leeg_compartiment_wordt_niet_weggefilterd(tmp_path):
    """Bij chemische metingen is MonsterCompartimentCode leeg — dat is normaal."""
    import importlib
    m = importlib.import_module("13_fetch_wkp_metingen")
    o, w = _schrijf(tmp_path, [_obj()], [_wrd(waarde="3,0")])
    d = m.verdicht(o, w, {"Ntot"})
    assert d["punten"][0]["stoffen"][0]["n"] == 1


def test_waarden_onder_de_rapportagegrens_worden_geteld(tmp_path):
    import importlib
    m = importlib.import_module("13_fetch_wkp_metingen")
    o, w = _schrijf(tmp_path, [_obj()],
                    [_wrd(waarde="3,0"), _wrd(waarde="0,004", limiet="<")])
    stof = m.verdicht(o, w, {"Ntot"})["punten"][0]["stoffen"][0]
    assert stof["n"] == 2
    assert stof["onder_rapportagegrens"] == 1


def test_onleesbare_waarde_laat_de_rij_niet_klappen(tmp_path):
    import importlib
    m = importlib.import_module("13_fetch_wkp_metingen")
    o, w = _schrijf(tmp_path, [_obj()],
                    [_wrd(waarde="3,0"), _wrd(waarde="nvt"), _wrd(waarde="")])
    d = m.verdicht(o, w, {"Ntot"})
    assert d["punten"][0]["stoffen"][0]["n"] == 1
    assert d["telling"]["onleesbaar"] == 2


def test_punt_draagt_coordinaten_en_waterlichaam(tmp_path):
    import importlib
    m = importlib.import_module("13_fetch_wkp_metingen")
    o, w = _schrijf(tmp_path, [_obj()], [_wrd()])
    p = m.verdicht(o, w, {"Ntot"})["punten"][0]
    assert p["code"] == "NL80_EIJSDPTN"
    assert p["naam"] == "Eijsden ponton"
    assert p["rd"] == [176000.0, 310000.0]
    assert p["waterlichaam"] == "NL91BOM"


def test_punten_zonder_gevraagde_stof_vallen_weg(tmp_path):
    import importlib
    m = importlib.import_module("13_fetch_wkp_metingen")
    o, w = _schrijf(tmp_path, [_obj(), _obj(code="NL80_ANDERS", naam="Ergens")],
                    [_wrd()])
    d = m.verdicht(o, w, {"Ntot"})
    assert [p["code"] for p in d["punten"]] == ["NL80_EIJSDPTN"]


def test_periode_komt_uit_de_monsterdata(tmp_path):
    import importlib
    m = importlib.import_module("13_fetch_wkp_metingen")
    o, w = _schrijf(tmp_path, [_obj()],
                    [_wrd(datum="2025-02-01"), _wrd(datum="2025-11-20")])
    stof = m.verdicht(o, w, {"Ntot"})["punten"][0]["stoffen"][0]
    assert stof["van"] == "2025-02-01"
    assert stof["tot"] == "2025-11-20"


def test_lege_monsterophaaldatum_valt_terug_op_begindatum(tmp_path):
    """Bij de chemische metingen is Monsterophaaldatum leeg; de datum staat in Begindatum."""
    import importlib
    m = importlib.import_module("13_fetch_wkp_metingen")
    wrd_kop = ("Meetjaar;MeetobjectCode;MonsterCompartimentCode;Monsterophaaldatum;"
               "Begindatum;Resultaatdatum;ParameterCode;ParameterOmschrijving;EenheidCode;"
               "Limietsymbool;Numeriekewaarde;KwaliteitsoordeelCode\n")
    o = tmp_path / "obj.csv"
    w = tmp_path / "wrd.csv"
    o.write_text(OBJ_KOP + _obj(), encoding="utf-8-sig")
    rij = "2025;NL80_EIJSDPTN;;;2025-01-07;2025-01-07;Ntot;stikstof totaal;mg/l;;3,3;00\n"
    w.write_text(wrd_kop + rij, encoding="utf-8-sig")
    stof = m.verdicht(str(o), str(w), {"Ntot"})["punten"][0]["stoffen"][0]
    assert stof["van"] == "2025-01-07"
    assert stof["tot"] == "2025-01-07"


def test_onbekend_meetobject_valt_niet_stil_weg(tmp_path):
    """Een meetwaarde waarvan de MeetobjectCode niet in het meetobjectenbestand staat
    (de twee WKP-bestanden passen dan niet bij elkaar) moet in de teller belanden, niet
    stilletjes verdwijnen. `onbekend_meetobject` is een deelverzameling van `meegeteld`."""
    import importlib
    m = importlib.import_module("13_fetch_wkp_metingen")
    o, w = _schrijf(tmp_path, [_obj()],
                    [_wrd(), _wrd(code="NL80_SPOOKPUNT")])
    d = m.verdicht(o, w, {"Ntot"})
    assert d["telling"]["onbekend_meetobject"] == 1
    assert d["telling"]["meegeteld"] == 2
    assert [p["code"] for p in d["punten"]] == ["NL80_EIJSDPTN"]
