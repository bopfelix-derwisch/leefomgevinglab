"""Gedeelde WFS-helpers voor de ketenstappen die echte bronnen bevragen.

Retries staan aan omdat het IPv6-pad naar PDOK vanaf deze machine regelmatig stilvalt en
httpx geen Happy-Eyeballs-fallback naar IPv4 doet — zie CLAUDE.md.
"""
import re

import httpx


def standaard_haal(url: str, params: dict, timeout_s: float = 25.0) -> str:
    with httpx.Client(timeout=timeout_s, follow_redirects=True,
                      transport=httpx.HTTPTransport(retries=3)) as c:
        r = c.get(url, params=params)
        if r.status_code >= 400:
            raise httpx.HTTPError(f"HTTP {r.status_code}")
        return r.text


def aantal_uit(tekst: str) -> int | None:
    """numberMatched uit een WFS hits-antwoord."""
    m = re.search(r'numberMatched="(\d+)"', tekst)
    return int(m.group(1)) if m else None


def hits_params(typenames: str, cql: str | None = None, bbox: str | None = None) -> dict:
    p = {"service": "WFS", "version": "2.0.0", "request": "GetFeature",
         "typeNames": typenames, "resultType": "hits"}
    if cql:
        p["cql_filter"] = cql
    if bbox:
        p["bbox"] = bbox
    return p


def features_params(typenames: str, cql: str | None = None, bbox: str | None = None,
                    count: int = 5, velden: str | None = None) -> dict:
    p = {"service": "WFS", "version": "2.0.0", "request": "GetFeature",
         "typeNames": typenames, "outputFormat": "application/json", "count": count}
    if cql:
        p["cql_filter"] = cql
    if bbox:
        p["bbox"] = bbox
    if velden:
        p["propertyName"] = velden
    return p


def bbox_rd(x: float, y: float, d: float) -> str:
    return f"{x - d},{y - d},{x + d},{y + d},urn:ogc:def:crs:EPSG::28992"


def tel(haal, url, params, bron, wat, uit) -> int | None:
    """Eén telling, met de uitkomst (of de storing) in `uit`. Werpt nooit."""
    try:
        n = aantal_uit(haal(url, params))
        uit.append({"bron": bron, "wat": wat, "status": "ok" if n is not None else "onleesbaar",
                    "aantal": n})
        return n
    except Exception as exc:
        uit.append({"bron": bron, "wat": wat, "status": "onbereikbaar", "aantal": None,
                    "fout": type(exc).__name__})
        return None


def haal_features(haal, url, params, bron, wat, uit) -> list:
    """Eigenschappen van de gevonden features; bij storing een lege lijst."""
    import json
    try:
        data = json.loads(haal(url, params))
        fs = [f.get("properties") or {} for f in (data.get("features") or [])]
        uit.append({"bron": bron, "wat": wat, "status": "ok", "aantal": len(fs)})
        return fs
    except Exception as exc:
        uit.append({"bron": bron, "wat": wat, "status": "onbereikbaar", "aantal": None,
                    "fout": type(exc).__name__})
        return []


def overgeslagen(bron: str, wat: str, uit: list) -> None:
    uit.append({"bron": bron, "wat": wat, "status": "overgeslagen", "aantal": None})
