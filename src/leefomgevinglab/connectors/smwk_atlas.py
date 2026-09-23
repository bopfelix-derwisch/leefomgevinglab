"""De Atlas voor een Schone Maas: echte lozingsvergunningen, ruimtelijk bevraagbaar.

Van de Schone Maaswaterketen — de waterschappen Aa en Maas, Brabantse Delta, De Dommel en
Limburg, met Rijkswaterstaat en de drinkwaterbedrijven. Sinds april 2023 staan de directe
lozingsvergunningen erin. Voor het Maasstroomgebied is dit het register dat elders in
Nederland ontbreekt.

Twee lagen op één FeatureServer:
  * laag 0 — de vestigingen als punt (72 stuks), ruimtelijk bevraagbaar;
  * tabel 2 — de vergunde voorschriften (782 stuks), gekoppeld via `Kenmerk` en, voor de 29
    rijen zonder kenmerk, via `Locatiecode`.

De ruimtelijke query gaat rechtstreeks op RD (`inSR=28992`). Geverifieerd 2026-09-16: een punt
bij Maastricht geeft 11 vestigingen binnen 5 km, een punt bij Deventer nul.

Niet elke vestiging heeft een vergunningkenmerk (7 van de 72 in de hele laag, o.a. de vier
rioolwaterzuiveringen van Waterschapsbedrijf Limburg). Die vier zijn geen duplicaten van
elkaar — RWZI-effluent is de grootste lozingscategorie op een waterlichaam — dus ontdubbelen
gebeurt bij een blanco kenmerk op `Locatiecode`, met `Vestigingsnummer_KvK` als tweede
terugval, in plaats van simpelweg wegfilteren.

Licentie: de lagen staan publiek open maar dragen geen expliciete licentie. Daarom live
bevragen met bronvermelding, en geen kopie van de dataset in deze repo.
"""
from datetime import datetime, timezone

from .base import BaseConnector, ConnectorError

BASIS = ("https://services-eu1.arcgis.com/S0XTphM6W3v0bENW/arcgis/rest/services/"
         "Vestigingen_Vergunningen_Uniek/FeatureServer")

_VESTIGING_VELDEN = ("Kenmerk,Statutaire_naam,Plaats,Locatieomschrijving,URL,"
                     "Locatiecode,Vestigingsnummer_KvK")
_VOORSCHRIFT_VELDEN = ("Kenmerk,Parameter,Waarde,Eenheid,Besluitdatum,Bemonsteringswijze,"
                       "meetpunt_X_Coordinaat,meetpunt_Y_Coordinaat,Locatiecode")

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

    def _query(self, laag: str, params: dict) -> dict:
        """Haalt op bij `laag` en bewaakt tegen een ArcGIS-storing die zich vermomt als HTTP 200.

        ArcGIS geeft bij een fout gewoon status 200 met een `error`-object in de body — dat is
        geen HTTP-fout, dus `BaseConnector.get_json` ziet hem niet. Onbehandeld zou zo'n antwoord
        als "geen features" doorkomen (en dan ook nog een dag gecachet blijven), terwijl de bron
        gewoon stuk was — met als gevolg dat `service._register()` de inhoudelijke boodschap
        "geen vergunningen in de Atlas" meldt over een storing. Hier alsnog een `ConnectorError`
        gooien zodat het bestaande except-pad het wél als onbereikbaar meldt, en de cache-file van
        déze aanroep meteen weggooien zodat de storing niet blijft hangen.
        """
        url = f"{self.base_url}/{laag}/query"
        data = self.get_json(url, params)
        if isinstance(data, dict) and "error" in data:
            cp = self._cache_path(url, params)
            if cp.exists():
                cp.unlink()
            raise ConnectorError(f"Atlas-fout bij {url}: {data['error']}")
        return data

    def vergunningen_bij_punt(self, x: float, y: float, straal_m: int = 5000) -> list[dict]:
        """De vergunde vestigingen binnen `straal_m` van dit RD-punt, met hun voorschriften.

        Ontdubbelen gebeurt op `Kenmerk` als dat er is; heeft een vestiging géén kenmerk
        (zie moduletekst), dan op `Locatiecode` en anders op `Vestigingsnummer_KvK`. Zo'n post
        blijft in het resultaat staan met `kenmerk: None` — de bron levert nu eenmaal geen
        vergunningkenmerk, en dat mag zichtbaar zijn in plaats van stilzwijgend te verdwijnen.
        `locatiecode` en `vestigingsnummer_kvk` gaan om diezelfde reden mee de post in: zonder
        kenmerk zijn het de enige velden die twee naamgenoten (bv. de RWZI's van Waterschapsbedrijf
        Limburg) nog uit elkaar houden.

        De voorschriftentabel koppelt normaal via `Kenmerk`, maar 29 van haar rijen (o.a. de
        RWZI's van Waterschapsbedrijf Limburg en de havenbedrijven) dragen zelf géén kenmerk en
        dus wél altijd een `Locatiecode`. Zonder een tweede koppeling op dat veld blijven precies
        de posten zonder kenmerk — vaak de grootste lozers — zonder voorschrift, en dus zonder
        vracht: ze tellen dan mee als 0 kg/jaar in plaats van als 'onbepaald'.
        """
        vest = self._query("0", {
            "geometry": f"{x},{y}", "geometryType": "esriGeometryPoint", "inSR": 28992,
            "spatialRel": "esriSpatialRelIntersects", "distance": straal_m,
            "units": "esriSRUnit_Meter", "outFields": _VESTIGING_VELDEN,
            "returnGeometry": "false", "f": "json",
        })
        posten = {}
        volgnummer = 0
        for f in vest.get("features") or []:
            a = f.get("attributes") or {}
            kenmerk = (a.get("Kenmerk") or "").strip() or None
            locatiecode = (a.get("Locatiecode") or "").strip() or None
            kvk_ruw = a.get("Vestigingsnummer_KvK")
            kvk = None if kvk_ruw in (None, "") else str(kvk_ruw).strip() or None

            if kenmerk:
                sleutel = ("kenmerk", kenmerk)
            elif locatiecode:
                sleutel = ("locatiecode", locatiecode)
            elif kvk:
                sleutel = ("kvk", kvk)
            else:
                # Geen enkel identificerend veld: elke vestiging telt apart.
                volgnummer += 1
                sleutel = ("volgnummer", volgnummer)
            if sleutel in posten:
                continue
            posten[sleutel] = {
                "kenmerk": kenmerk, "naam": a.get("Statutaire_naam"), "plaats": a.get("Plaats"),
                "locatie": (a.get("Locatieomschrijving") or "").strip() or None,
                "url": (a.get("URL") or "").strip() or None,
                "locatiecode": locatiecode, "vestigingsnummer_kvk": kvk,
                "besluitdatum": None, "voorschriften": [],
            }
        if not posten:
            return []

        def _koppel(features, vind_post):
            for f in features or []:
                a = f.get("attributes") or {}
                post = vind_post(a)
                if post is None:
                    continue
                post["voorschriften"].append({
                    "parameter": a.get("Parameter"), "waarde": a.get("Waarde"),
                    "eenheid": a.get("Eenheid"), "bemonstering": a.get("Bemonsteringswijze"),
                    "rd": [a.get("meetpunt_X_Coordinaat"), a.get("meetpunt_Y_Coordinaat")],
                })
                post["besluitdatum"] = post["besluitdatum"] or _datum(a.get("Besluitdatum"))

        by_kenmerk = {p["kenmerk"]: p for p in posten.values() if p["kenmerk"]}
        if by_kenmerk:
            # ArcGIS kent geen parameterbinding; apostrofs verdubbelen is de SQL-conventie.
            lijst = ",".join("'" + k.replace("'", "''") + "'" for k in by_kenmerk)
            voors = self._query("2", {
                "where": f"Kenmerk IN ({lijst})", "outFields": _VOORSCHRIFT_VELDEN,
                "returnGeometry": "false", "f": "json",
            })
            _koppel(voors.get("features"), lambda a: by_kenmerk.get(a.get("Kenmerk")))

        # Posten zonder kenmerk (zie docstring) koppelen op Locatiecode. De where-clause test
        # expliciet op NULL én op lege string — een eerdere controle zocht op één spatie en vond
        # daardoor niets, terwijl de bron zijn lege kenmerken als NULL of '' opslaat.
        by_locatiecode = {p["locatiecode"]: p for p in posten.values()
                          if not p["kenmerk"] and p["locatiecode"]}
        if by_locatiecode:
            lijst = ",".join("'" + k.replace("'", "''") + "'" for k in by_locatiecode)
            voors = self._query("2", {
                "where": f"(Kenmerk IS NULL OR Kenmerk = '') AND Locatiecode IN ({lijst})",
                "outFields": _VOORSCHRIFT_VELDEN, "returnGeometry": "false", "f": "json",
            })
            _koppel(voors.get("features"), lambda a: by_locatiecode.get(a.get("Locatiecode")))

        return list(posten.values())
