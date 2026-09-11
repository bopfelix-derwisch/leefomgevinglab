"""Data.OD-stap: de contextset rond het RD-punt, live opgehaald bij de echte bronnen.

In het doelbeeld stelt Data.OD deze set samen; vandaag doet elke omgevingsdienst dat zelf.
Hier bevragen we wat open is: de REV-WFS voor omliggende risico-objecten en de BAG voor
wat er binnen de invloedsafstand staat.

De keten mag hier niet op stuklopen: valt een bron weg, dan gaat de contextset onvolledig
verder en zegt dat er ook bij. Retries staan aan omdat het IPv6-pad naar PDOK vanaf deze
machine regelmatig stilvalt — zie CLAUDE.md.
"""
import re

import httpx

REV_WFS = "https://rev-portaal.nl/geoserver/wfs"
BAG_WFS = "https://service.pdok.nl/lv/bag/wfs/v2_0"

REV_LAGEN = [
    ("rev_public:ev_gifwolkaandachtsgebieden", "gifwolkaandachtsgebieden"),
    ("rev_public:ev_brandaandachtsgebieden", "brandaandachtsgebieden"),
    ("rev_public:ev_explosieaandachtsgebieden", "explosieaandachtsgebieden"),
    ("rev_public:ev_activiteiten", "risicovolle activiteiten"),
]
BAG_LAGEN = [("bag:pand", "panden"), ("bag:verblijfsobject", "verblijfsobjecten")]


def standaard_haal(url: str, params: dict, timeout_s: float = 25.0) -> str:
    """Eén GET; geeft de responstekst. Retries vangen het wegvallende IPv6-pad naar PDOK op."""
    with httpx.Client(timeout=timeout_s, follow_redirects=True,
                      transport=httpx.HTTPTransport(retries=3)) as c:
        r = c.get(url, params=params)
        if r.status_code >= 400:
            raise httpx.HTTPError(f"HTTP {r.status_code}")
        return r.text


def _aantal(tekst: str) -> int | None:
    m = re.search(r'numberMatched="(\d+)"', tekst)
    return int(m.group(1)) if m else None


def _tel(haal, url, params, bron, omschrijving, uit):
    try:
        n = _aantal(haal(url, params))
        uit.append({"bron": bron, "wat": omschrijving, "status": "ok" if n is not None else "onleesbaar",
                    "aantal": n})
        return n
    except Exception as exc:
        uit.append({"bron": bron, "wat": omschrijving, "status": "onbereikbaar",
                    "aantal": None, "fout": type(exc).__name__})
        return None


def contextset(x: float, y: float, straal_m: int = 1000, live: bool = True, haal=None) -> dict:
    """Alles wat binnen `straal_m` van het punt ligt, per bron geteld."""
    bronnen, rev, bag = [], {}, {}

    if not live:
        for laag, oms in REV_LAGEN:
            bronnen.append({"bron": "REV-WFS", "wat": oms, "status": "overgeslagen", "aantal": None})
            rev[oms] = None
        for laag, oms in BAG_LAGEN:
            bronnen.append({"bron": "BAG (PDOK)", "wat": oms, "status": "overgeslagen", "aantal": None})
            bag[oms] = None
        return {"straal_m": straal_m, "rd": [x, y], "live": False, "volledig": False,
                "rev": rev, "bag": bag, "bronnen": bronnen}

    haal = haal or standaard_haal
    for laag, oms in REV_LAGEN:
        rev[oms] = _tel(haal, REV_WFS, {
            "service": "WFS", "version": "2.0.0", "request": "GetFeature", "typeNames": laag,
            "resultType": "hits",
            "cql_filter": f"DWITHIN(geometrie, POINT({x} {y}), {straal_m}, meters)",
        }, "REV-WFS", oms, bronnen)
    bbox = f"{x - straal_m},{y - straal_m},{x + straal_m},{y + straal_m},urn:ogc:def:crs:EPSG::28992"
    for laag, oms in BAG_LAGEN:
        bag[oms] = _tel(haal, BAG_WFS, {
            "service": "WFS", "version": "2.0.0", "request": "GetFeature", "typeNames": laag,
            "resultType": "hits", "bbox": bbox,
        }, "BAG (PDOK)", oms, bronnen)

    volledig = all(b["status"] == "ok" for b in bronnen)
    return {"straal_m": straal_m, "rd": [x, y], "live": True, "volledig": volledig,
            "rev": rev, "bag": bag, "bronnen": bronnen}
