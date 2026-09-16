"""De Atlas voor een Schone Maas: echte lozingsvergunningen, ruimtelijk bevraagbaar.

Van de Schone Maaswaterketen — de waterschappen Aa en Maas, Brabantse Delta, De Dommel en
Limburg, met Rijkswaterstaat en de drinkwaterbedrijven. Sinds april 2023 staan de directe
lozingsvergunningen erin. Voor het Maasstroomgebied is dit het register dat elders in
Nederland ontbreekt.

Twee lagen op één FeatureServer:
  * laag 0 — de vestigingen als punt (72 stuks), ruimtelijk bevraagbaar;
  * tabel 2 — de vergunde voorschriften (782 stuks), gekoppeld via `Kenmerk`.

De ruimtelijke query gaat rechtstreeks op RD (`inSR=28992`). Geverifieerd 2026-09-16: een punt
bij Maastricht geeft 11 vestigingen binnen 5 km, een punt bij Deventer nul.

Licentie: de lagen staan publiek open maar dragen geen expliciete licentie. Daarom live
bevragen met bronvermelding, en geen kopie van de dataset in deze repo.
"""
from datetime import datetime, timezone

from .base import BaseConnector

BASIS = ("https://services-eu1.arcgis.com/S0XTphM6W3v0bENW/arcgis/rest/services/"
         "Vestigingen_Vergunningen_Uniek/FeatureServer")

_VESTIGING_VELDEN = "Kenmerk,Statutaire_naam,Plaats,Locatieomschrijving,URL"
_VOORSCHRIFT_VELDEN = ("Kenmerk,Parameter,Waarde,Eenheid,Besluitdatum,Bemonsteringswijze,"
                       "meetpunt_X_Coordinaat,meetpunt_Y_Coordinaat")

BRON = {"naam": "Atlas voor een Schone Maas", "url": "https://atlas-smwk.hub.arcgis.com/",
        "houder": "Schone Maaswaterketen"}


def _datum(ms) -> str | None:
    """ArcGIS levert epoch-milliseconden; maak er een leesbare datum van."""
    if ms is None:
        return None
    try:
        return datetime.fromtimestamp(float(ms) / 1000.0, tz=timezone.utc).strftime("%Y-%m-%d")
    except (TypeError, ValueError, OSError):
        return None


class SmwkAtlasConnector(BaseConnector):
    def __init__(self, cache_dir: str, timeout: float = 20.0, cache_ttl: int = 86400,
                 base_url: str | None = None):
        super().__init__(cache_dir=cache_dir, timeout=timeout, cache_ttl=cache_ttl)
        self.base_url = (base_url or BASIS).rstrip("/")

    def vergunningen_bij_punt(self, x: float, y: float, straal_m: int = 5000) -> list[dict]:
        """De vergunde vestigingen binnen `straal_m` van dit RD-punt, met hun voorschriften."""
        vest = self.get_json(f"{self.base_url}/0/query", {
            "geometry": f"{x},{y}", "geometryType": "esriGeometryPoint", "inSR": 28992,
            "spatialRel": "esriSpatialRelIntersects", "distance": straal_m,
            "units": "esriSRUnit_Meter", "outFields": _VESTIGING_VELDEN,
            "returnGeometry": "false", "f": "json",
        })
        posten = {}
        for f in vest.get("features") or []:
            a = f.get("attributes") or {}
            kenmerk = a.get("Kenmerk")
            if not kenmerk or kenmerk in posten:
                continue
            posten[kenmerk] = {
                "kenmerk": kenmerk, "naam": a.get("Statutaire_naam"), "plaats": a.get("Plaats"),
                "locatie": (a.get("Locatieomschrijving") or "").strip() or None,
                "url": (a.get("URL") or "").strip() or None,
                "besluitdatum": None, "voorschriften": [],
            }
        if not posten:
            return []

        # ArcGIS kent geen parameterbinding; apostrofs verdubbelen is de SQL-conventie.
        lijst = ",".join("'" + k.replace("'", "''") + "'" for k in posten)
        voors = self.get_json(f"{self.base_url}/2/query", {
            "where": f"Kenmerk IN ({lijst})", "outFields": _VOORSCHRIFT_VELDEN,
            "returnGeometry": "false", "f": "json",
        })
        for f in voors.get("features") or []:
            a = f.get("attributes") or {}
            post = posten.get(a.get("Kenmerk"))
            if post is None:
                continue
            post["voorschriften"].append({
                "parameter": a.get("Parameter"), "waarde": a.get("Waarde"),
                "eenheid": a.get("Eenheid"), "bemonstering": a.get("Bemonsteringswijze"),
                "rd": [a.get("meetpunt_X_Coordinaat"), a.get("meetpunt_Y_Coordinaat")],
            })
            post["besluitdatum"] = post["besluitdatum"] or _datum(a.get("Besluitdatum"))

        return list(posten.values())
