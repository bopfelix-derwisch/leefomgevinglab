import httpx
import pytest

from leefomgevinglab.usecases import vth_bronnen as vb


def test_alle_objecttypen_van_bronnen_bestaan_in_het_cim():
    geldig = {ot for v in vb.VIEWS for ot in v["objecttypen"]}
    onbekend = sorted({ot for b in vb.BRONNEN for ot in b["objecttypen"]} - geldig)
    assert onbekend == []


def test_bron_ids_zijn_uniek():
    ids = [b["id"] for b in vb.BRONNEN]
    assert len(ids) == len(set(ids))


def test_elke_bron_heeft_geldige_laag_en_openheid():
    fout = [b["id"] for b in vb.BRONNEN
            if b["laag"] not in vb.LAGEN or b["openheid"] not in vb.OPENHEID]
    assert fout == []


def test_elke_bestuurslaag_uit_de_vraag_komt_voor():
    gebruikt = {b["laag"] for b in vb.BRONNEN}
    for laag in ("rijk", "rws", "provincie", "waterschap", "omgevingsdienst", "gemeente"):
        assert laag in gebruikt, f"geen bron voor bestuurslaag {laag}"


def test_overlappen_geeft_objecttypen_met_meerdere_bronnen():
    ov = vb.overlappen()
    assert ov, "verwacht overlap tussen bronnen"
    for o in ov:
        assert len(o["bronnen"]) >= 2
        assert o["objecttype"]
    # gesorteerd van meeste naar minste bronnen
    assert [len(o["bronnen"]) for o in ov] == sorted((len(o["bronnen"]) for o in ov), reverse=True)


def test_vth_object_wordt_door_meerdere_registraties_beschreven():
    ov = {o["objecttype"]: o for o in vb.overlappen()}
    assert "VTH-OBJECT" in ov
    assert len(ov["VTH-OBJECT"]["bronnen"]) >= 3


def test_dekking_per_view_telt_bronnen_per_openheid():
    dek = {d["view"]: d for d in vb.dekking_per_view()}
    assert len(dek) == len(vb.VIEWS)
    toezicht = dek["Toezicht- en handhaving-view"]
    assert toezicht["open"] == 0, "er is geen open bron voor controles/bevindingen"
    assert toezicht["gesloten"] >= 1
    locatie = dek["Locatie-view"]
    assert locatie["open"] >= 3


def test_catalogus_bundelt_alles():
    cat = vb.catalogus()
    assert cat["bronnen"] and cat["views"] and cat["overlap"] and cat["dekking"]
    assert cat["lagen"] == vb.LAGEN


@pytest.mark.anyio
async def test_check_endpoints_markeert_bereikbaarheid():
    async def fake_get(self, url, **kw):
        if "kapot" in url:
            raise httpx.ConnectError("nope")
        return httpx.Response(200 if "goed" in url else 503)

    bronnen = [{"id": "a", "endpoint": "https://goed/x"},
               {"id": "b", "endpoint": "https://kapot/x"},
               {"id": "c", "endpoint": "https://anders/x"},
               {"id": "d", "endpoint": None}]
    res = await vb.check_endpoints(bronnen, _get=fake_get)
    assert res["a"]["ok"] is True and res["a"]["status"] == 200
    assert res["b"]["ok"] is False and res["b"]["status"] is None
    assert res["c"]["ok"] is False and res["c"]["status"] == 503
    assert "d" not in res


@pytest.fixture
def anyio_backend():
    return "asyncio"
