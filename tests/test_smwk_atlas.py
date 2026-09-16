import pytest

from leefomgevinglab.connectors.smwk_atlas import SmwkAtlasConnector

_VESTIGINGEN = {"features": [
    {"attributes": {"Kenmerk": "RWS-2015/38632", "Statutaire_naam": "Lawter Maastricht BV",
                    "Plaats": "Maastricht", "Locatieomschrijving": "Maas linkeroever",
                    "URL": "https://example.invalid/verg1"}},
    {"attributes": {"Kenmerk": "DLB2006/8811", "Statutaire_naam": "Chromaflo Technologies BV",
                    "Plaats": "Maastricht", "Locatieomschrijving": "", "URL": ""}},
]}
_VOORSCHRIFTEN = {"features": [
    {"attributes": {"Kenmerk": "RWS-2015/38632", "Parameter": "zink", "Waarde": 0.3,
                    "Eenheid": "milligram per liter", "Besluitdatum": 1420070400000}},
    {"attributes": {"Kenmerk": "RWS-2015/38632", "Parameter": "Debiet", "Waarde": 25.0,
                    "Eenheid": "kubieke meter per uur", "Besluitdatum": 1420070400000}},
    {"attributes": {"Kenmerk": "DLB2006/8811", "Parameter": "stikstof totaal", "Waarde": 1.2,
                    "Eenheid": "ton per jaar", "Besluitdatum": None}},
]}


class _NepConnector(SmwkAtlasConnector):
    """Vervangt alleen het HTTP-deel; de opbouw van de query blijft echt."""

    def __init__(self, tmp_path, antwoorden):
        super().__init__(cache_dir=str(tmp_path))
        self.antwoorden = list(antwoorden)
        self.aanroepen = []

    def get_json(self, url, params=None, headers=None):
        self.aanroepen.append((url, params or {}))
        return self.antwoorden.pop(0)


def test_ruimtelijke_query_gebruikt_rd_en_een_straal(tmp_path):
    c = _NepConnector(tmp_path, [_VESTIGINGEN, _VOORSCHRIFTEN])
    c.vergunningen_bij_punt(177748.0, 321314.0, straal_m=5000)
    url, p = c.aanroepen[0]
    assert url.endswith("/0/query")
    assert p["inSR"] == 28992
    assert p["geometry"] == "177748.0,321314.0"
    assert p["geometryType"] == "esriGeometryPoint"
    assert p["distance"] == 5000
    assert p["units"] == "esriSRUnit_Meter"
    assert p["spatialRel"] == "esriSpatialRelIntersects"
    assert p["f"] == "json"


def test_voorschriften_worden_per_kenmerk_opgehaald(tmp_path):
    c = _NepConnector(tmp_path, [_VESTIGINGEN, _VOORSCHRIFTEN])
    c.vergunningen_bij_punt(177748.0, 321314.0)
    _, p = c.aanroepen[1]
    assert "RWS-2015/38632" in p["where"] and "DLB2006/8811" in p["where"]
    assert p["where"].startswith("Kenmerk IN (")


def test_elke_vestiging_krijgt_haar_eigen_voorschriften(tmp_path):
    c = _NepConnector(tmp_path, [_VESTIGINGEN, _VOORSCHRIFTEN])
    uit = c.vergunningen_bij_punt(177748.0, 321314.0)
    assert len(uit) == 2
    lawter = next(v for v in uit if v["kenmerk"] == "RWS-2015/38632")
    assert lawter["naam"] == "Lawter Maastricht BV"
    assert lawter["plaats"] == "Maastricht"
    assert {v["parameter"] for v in lawter["voorschriften"]} == {"zink", "Debiet"}
    chromaflo = next(v for v in uit if v["kenmerk"] == "DLB2006/8811")
    assert len(chromaflo["voorschriften"]) == 1


def test_besluitdatum_wordt_leesbaar(tmp_path):
    c = _NepConnector(tmp_path, [_VESTIGINGEN, _VOORSCHRIFTEN])
    uit = c.vergunningen_bij_punt(177748.0, 321314.0)
    lawter = next(v for v in uit if v["kenmerk"] == "RWS-2015/38632")
    assert lawter["besluitdatum"] == "2015-01-01"


def test_geen_vestigingen_geeft_geen_tweede_aanroep(tmp_path):
    c = _NepConnector(tmp_path, [{"features": []}])
    assert c.vergunningen_bij_punt(206800.0, 474000.0) == []
    assert len(c.aanroepen) == 1, "zonder vestigingen hoeft de tabel niet bevraagd"


def test_kenmerk_met_apostrof_breekt_de_where_clause_niet(tmp_path):
    vest = {"features": [{"attributes": {"Kenmerk": "RWS-O'Neill/1", "Statutaire_naam": "X",
                                         "Plaats": "Y", "Locatieomschrijving": "", "URL": ""}}]}
    c = _NepConnector(tmp_path, [vest, {"features": []}])
    c.vergunningen_bij_punt(1.0, 2.0)
    _, p = c.aanroepen[1]
    assert "O''Neill" in p["where"], "apostrof moet verdubbeld worden"


def test_blanco_kenmerk_met_verschillende_locatiecode_blijft_apart(tmp_path):
    """Vier RWZI's van hetzelfde waterschapsbedrijf mogen niet samenvallen tot één post."""
    vest = {"features": [
        {"attributes": {"Kenmerk": "", "Statutaire_naam": "Waterschapsbedrijf Limburg",
                        "Plaats": "Maastricht", "Locatieomschrijving": "", "URL": "",
                        "Locatiecode": "RWZIB", "Vestigingsnummer_KvK": "000020643233"}},
        {"attributes": {"Kenmerk": "", "Statutaire_naam": "Waterschapsbedrijf Limburg",
                        "Plaats": "Maastricht", "Locatieomschrijving": "", "URL": "",
                        "Locatiecode": "RWZIL", "Vestigingsnummer_KvK": "000020643268"}},
    ]}
    c = _NepConnector(tmp_path, [vest])
    uit = c.vergunningen_bij_punt(1.0, 2.0)
    assert len(uit) == 2
    assert {p["kenmerk"] for p in uit} == {None}


def test_blanco_kenmerk_met_dezelfde_locatiecode_wordt_een_post(tmp_path):
    """Een echte duplicaatrij (zelfde Locatiecode) vouwt wél samen."""
    vest = {"features": [
        {"attributes": {"Kenmerk": "", "Statutaire_naam": "Bloemen De Maas B.V.",
                        "Plaats": "Niftrik", "Locatieomschrijving": "", "URL": "",
                        "Locatiecode": "JWMAAS", "Vestigingsnummer_KvK": "000018363989"}},
        {"attributes": {"Kenmerk": " ", "Statutaire_naam": "Bloemen De Maas B.V.",
                        "Plaats": "Niftrik", "Locatieomschrijving": "", "URL": "",
                        "Locatiecode": "JWMAAS", "Vestigingsnummer_KvK": "000018363989"}},
    ]}
    c = _NepConnector(tmp_path, [vest])
    uit = c.vergunningen_bij_punt(1.0, 2.0)
    assert len(uit) == 1


def test_post_met_blanco_kenmerk_krijgt_kenmerk_none_en_blijft_buiten_where(tmp_path):
    vest = {"features": [
        {"attributes": {"Kenmerk": "  ", "Statutaire_naam": "J.P. Havens Graanhandel N.V.",
                        "Plaats": "Maashees", "Locatieomschrijving": "", "URL": "",
                        "Locatiecode": "HAVENS", "Vestigingsnummer_KvK": "000006266630"}},
        {"attributes": {"Kenmerk": "RWS-2015/38632", "Statutaire_naam": "Lawter Maastricht BV",
                        "Plaats": "Maastricht", "Locatieomschrijving": "", "URL": "",
                        "Locatiecode": None, "Vestigingsnummer_KvK": None}},
    ]}
    c = _NepConnector(tmp_path, [vest, {"features": []}])
    uit = c.vergunningen_bij_punt(1.0, 2.0)
    havens = next(v for v in uit if v["naam"] == "J.P. Havens Graanhandel N.V.")
    assert havens["kenmerk"] is None
    _, p = c.aanroepen[1]
    assert "HAVENS" not in p["where"]
    assert p["where"] == "Kenmerk IN ('RWS-2015/38632')"


def test_alle_gevonden_vestigingen_blanco_kenmerk_geeft_geen_tweede_aanroep(tmp_path):
    vest = {"features": [
        {"attributes": {"Kenmerk": "", "Statutaire_naam": "X", "Plaats": "Y",
                        "Locatieomschrijving": "", "URL": "",
                        "Locatiecode": "A", "Vestigingsnummer_KvK": None}},
    ]}
    c = _NepConnector(tmp_path, [vest])
    uit = c.vergunningen_bij_punt(1.0, 2.0)
    assert len(uit) == 1
    assert len(c.aanroepen) == 1, "zonder kenmerken hoeft de voorschriftentabel niet bevraagd"
