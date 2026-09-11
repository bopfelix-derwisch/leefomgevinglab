"""Data.OD-stap: de contextset rond het RD-punt, live opgehaald bij de echte bronnen.

In het doelbeeld stelt Data.OD deze set samen; vandaag doet elke omgevingsdienst dat zelf.
Hier bevragen we wat open is: de REV-WFS voor omliggende risico-objecten en de BAG voor
wat er binnen de invloedsafstand staat.

De keten mag hier niet op stuklopen: valt een bron weg, dan gaat de contextset onvolledig
verder en zegt dat er ook bij. Retries staan aan omdat het IPv6-pad naar PDOK vanaf deze
machine regelmatig stilvalt — zie CLAUDE.md.
"""
from ..ketenkern import wfs

REV_WFS = "https://rev-portaal.nl/geoserver/wfs"
BAG_WFS = "https://service.pdok.nl/lv/bag/wfs/v2_0"

REV_LAGEN = [
    ("rev_public:ev_gifwolkaandachtsgebieden", "gifwolkaandachtsgebieden"),
    ("rev_public:ev_brandaandachtsgebieden", "brandaandachtsgebieden"),
    ("rev_public:ev_explosieaandachtsgebieden", "explosieaandachtsgebieden"),
    ("rev_public:ev_activiteiten", "risicovolle activiteiten"),
]
BAG_LAGEN = [("bag:pand", "panden"), ("bag:verblijfsobject", "verblijfsobjecten")]




def contextset(x: float, y: float, straal_m: int = 1000, live: bool = True, haal=None) -> dict:
    """Alles wat binnen `straal_m` van het punt ligt, per bron geteld."""
    bronnen, rev, bag = [], {}, {}

    if not live:
        for laag, oms in REV_LAGEN:
            wfs.overgeslagen("REV-WFS", oms, bronnen)
            rev[oms] = None
        for laag, oms in BAG_LAGEN:
            wfs.overgeslagen("BAG (PDOK)", oms, bronnen)
            bag[oms] = None
        return {"straal_m": straal_m, "rd": [x, y], "live": False, "volledig": False,
                "rev": rev, "bag": bag, "bronnen": bronnen}

    haal = haal or wfs.standaard_haal
    for laag, oms in REV_LAGEN:
        rev[oms] = wfs.tel(haal, REV_WFS, {
            "service": "WFS", "version": "2.0.0", "request": "GetFeature", "typeNames": laag,
            "resultType": "hits",
            "cql_filter": f"DWITHIN(geometrie, POINT({x} {y}), {straal_m}, meters)",
        }, "REV-WFS", oms, bronnen)
    bbox = wfs.bbox_rd(x, y, straal_m)
    for laag, oms in BAG_LAGEN:
        bag[oms] = wfs.tel(haal, BAG_WFS, {
            "service": "WFS", "version": "2.0.0", "request": "GetFeature", "typeNames": laag,
            "resultType": "hits", "bbox": bbox,
        }, "BAG (PDOK)", oms, bronnen)

    volledig = all(b["status"] == "ok" for b in bronnen)
    return {"straal_m": straal_m, "rd": [x, y], "live": True, "volledig": volledig,
            "rev": rev, "bag": bag, "bronnen": bronnen}
