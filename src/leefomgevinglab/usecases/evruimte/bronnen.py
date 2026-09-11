"""Live tellingen rond een punt: wat staat er binnen de contouren, en wat ligt er al?

Twee lessen uit het testen, allebei het onthouden waard:

  * PDOK negeert `cql_filter` volledig — op de BAG én op de bestuurlijke gebieden. Een
    DWITHIN in CQL levert stilzwijgend de héle dataset terug, wat een vals-positief oplevert
    dat je niet ziet. De standaard FES-filter via POST wérkt wel, en daar staat ook de
    PropertyIsLike op gebruiksdoel in.
  * De REV-WFS is een GeoServer en accepteert `cql_filter` juist wél.
"""
import json
import re

import httpx

BAG_WFS = "https://service.pdok.nl/lv/bag/wfs/v2_0"
BG_WFS = "https://service.pdok.nl/kadaster/bestuurlijkegebieden/wfs/v1_0"
REV_WFS = "https://rev-portaal.nl/geoserver/wfs"

REV_LAGEN = [
    ("rev_public:ev_activiteiten", "risicovolle activiteiten"),
    ("rev_public:ev_gifwolkaandachtsgebieden", "gifwolkaandachtsgebieden"),
    ("rev_public:ev_brandaandachtsgebieden", "brandaandachtsgebieden"),
    ("rev_public:ev_explosieaandachtsgebieden", "explosieaandachtsgebieden"),
]

# Gesleuteld op de contoursoort uit gebied.CONTOUREN, zodat de kaart de laag terugvindt.
# Eerder stonden hier de meervoudsnamen uit REV_LAGEN en vond de viewer ze nooit.
REV_AANDACHTSGEBIEDEN = {
    "gifwolkaandachtsgebied": "rev_public:ev_gifwolkaandachtsgebieden",
    "brandaandachtsgebied": "rev_public:ev_brandaandachtsgebieden",
    "explosieaandachtsgebied": "rev_public:ev_explosieaandachtsgebieden",
}

_FES = "http://www.opengis.net/fes/2.0"
_GML = "http://www.opengis.net/gml/3.2"


def fes_filter(x: float, y: float, straal_m: float, gebruiksdoel: str | None = None) -> str:
    """DWithin op het RD-punt, optioneel gecombineerd met een gebruiksdoel."""
    dwithin = (f'<fes:DWithin><fes:ValueReference>geom</fes:ValueReference>'
               f'<gml:Point srsName="urn:ogc:def:crs:EPSG::28992"><gml:pos>{x} {y}</gml:pos></gml:Point>'
               f'<fes:Distance uom="m">{straal_m}</fes:Distance></fes:DWithin>')
    if gebruiksdoel:
        dwithin = ('<fes:And>' + dwithin +
                   '<fes:PropertyIsLike wildCard="*" singleChar="?" escapeChar="\\">'
                   f'<fes:ValueReference>gebruiksdoel</fes:ValueReference>'
                   f'<fes:Literal>*{gebruiksdoel}*</fes:Literal></fes:PropertyIsLike></fes:And>')
    return f'<fes:Filter xmlns:fes="{_FES}" xmlns:gml="{_GML}">{dwithin}</fes:Filter>'


def _aantal(tekst: str) -> int | None:
    m = re.search(r'numberMatched="(\d+)"', tekst)
    return int(m.group(1)) if m else None


def standaard_post(url: str, data: dict, timeout_s: float = 45.0) -> str:
    with httpx.Client(timeout=timeout_s, follow_redirects=True,
                      transport=httpx.HTTPTransport(retries=3)) as c:
        r = c.post(url, data=data)
        if r.status_code >= 400:
            raise httpx.HTTPError(f"HTTP {r.status_code}")
        return r.text


def standaard_get(url: str, params: dict, timeout_s: float = 45.0) -> str:
    with httpx.Client(timeout=timeout_s, follow_redirects=True,
                      transport=httpx.HTTPTransport(retries=3)) as c:
        r = c.get(url, params=params)
        if r.status_code >= 400:
            raise httpx.HTTPError(f"HTTP {r.status_code}")
        return r.text


def tel_verblijfsobjecten(x, y, straal_m, gebruiksdoel=None, _post=None) -> int | None:
    post = _post or standaard_post
    return _aantal(post(BAG_WFS, {
        "service": "WFS", "version": "2.0.0", "request": "GetFeature",
        "typeNames": "bag:verblijfsobject", "resultType": "hits",
        "filter": fes_filter(x, y, straal_m, gebruiksdoel)}))


def tel_rev(x, y, straal_m, laag, _get=None) -> int | None:
    get = _get or standaard_get
    return _aantal(get(REV_WFS, {
        "service": "WFS", "version": "2.0.0", "request": "GetFeature", "typeNames": laag,
        "resultType": "hits",
        "cql_filter": f"DWITHIN(geometrie, POINT({x} {y}), {straal_m}, meters)"}))


def rev_geojson(x, y, straal_m, laag, maximaal=200, _get=None) -> dict:
    """De bestaande aandachtsgebieden als GeoJSON in WGS84, om op de kaart te tekenen."""
    get = _get or standaard_get
    ruw = get(REV_WFS, {
        "service": "WFS", "version": "2.0.0", "request": "GetFeature", "typeNames": laag,
        "outputFormat": "application/json", "srsName": "EPSG:4326", "count": maximaal,
        "cql_filter": f"DWITHIN(geometrie, POINT({x} {y}), {straal_m}, meters)"})
    return json.loads(ruw)


def gemeente_op_punt(x, y, _get=None) -> dict:
    get = _get or standaard_get
    ruw = get(BG_WFS, {
        "service": "WFS", "version": "2.0.0", "request": "GetFeature",
        "typeNames": "bestuurlijkegebieden:Gemeentegebied", "outputFormat": "application/json",
        "count": 1, "propertyName": "naam,ligtInProvincieNaam",
        "bbox": f"{x - 50},{y - 50},{x + 50},{y + 50},urn:ogc:def:crs:EPSG::28992"})
    fs = (json.loads(ruw).get("features") or [])
    p = fs[0].get("properties", {}) if fs else {}
    return {"gemeente": p.get("naam"), "provincie": p.get("ligtInProvincieNaam")}
