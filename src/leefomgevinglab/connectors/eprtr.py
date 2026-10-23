"""E-PRTR: wat een inrichting zelf meldt te lozen, als WFS van het RIVM.

Naast "wat mag" (de vergunning) en "wat gebeurt" (de meting) staat hier een derde grootheid: wat
een bedrijf zelf jaarlijks rapporteert te hebben geloosd. Die komt uit het elektronisch
Milieujaarverslag, wordt door het RIVM voor de Europese E-PRTR-verplichting samengesteld, en is —
als enige bron in deze hele keten — **machinaal bevraagbaar**:

    https://data.rivm.nl/geo/inspire/wfs
    laag  inspire:facility_pollutant_release
    CRS   EPSG:28992, hetzelfde RD als de Atlas-vergunningen

Per rij: `nationalid`, de naam van de productielocatie, het jaar, de stof, `mediumcode` (AIR of
WATER), de gemelde vracht in kilogram, en een puntgeometrie. De geometriekolom heet `geom` — niet
`the_geom`, wat een DWITHIN stilzwijgend op nul treffers laat uitkomen.

**Waarom dit ertoe doet.** Het verschil tussen de vergunde en de gemelde vracht is de vergunde
ruimte die niet gebruikt wordt. Dat getal staat nergens geregistreerd, terwijl het bepaalt hoeveel
een waterlichaam nog legaal kan verslechteren zonder dat iemand een regel overtreedt. Gemeten bij
Sappi Maastricht: 7008 kg zink per jaar vergund, 105 kg gemeld over 2022 — 1,5 procent benut.

**Twee dingen om niet te vergeten bij het lezen.**

Een lege uitkomst is geen nul. E-PRTR dekt alleen inrichtingen boven de Europese
rapportagedrempels; een kleinere lozer komt er nooit in voor. "Niets gemeld" en "niets geloosd"
zijn dus verschillende uitspraken, en deze module geeft daarom nooit een 0 terug waar zij niets
vond.

En de koppeling is een heuristiek, geen sleutel — zie `koppeling.py`.
"""
from .base import BaseConnector, ConnectorError

WFS = "https://data.rivm.nl/geo/inspire/wfs"
LAAG = "inspire:facility_pollutant_release"

BRON = {
    "naam": "E-PRTR — gemelde emissies per inrichting",
    "houder": "Rijksinstituut voor Volksgezondheid en Milieu",
    "url": WFS,
    "herkomst": ("elektronisch Milieujaarverslag, samengesteld voor de Europese "
                 "E-PRTR-verplichting; alleen inrichtingen boven de rapportagedrempel"),
}


class EprtrConnector(BaseConnector):
    """Gemelde emissies rond een RD-punt."""

    def __init__(self, cache_dir: str, timeout: float = 30.0, cache_ttl: int = 86400,
                 base_url: str | None = None):
        super().__init__(cache_dir, timeout=timeout, cache_ttl=cache_ttl)
        self.base_url = base_url or WFS

    def _features(self, cql: str, maximaal: int = 500) -> list[dict]:
        data = self.get_json(self.base_url, params={
            "service": "WFS", "version": "2.0.0", "request": "GetFeature",
            "typeNames": LAAG, "outputFormat": "application/json",
            "count": maximaal, "CQL_FILTER": cql,
        })
        uit = []
        for f in (data or {}).get("features") or []:
            p = dict(f.get("properties") or {})
            geo = (f.get("geometry") or {}).get("coordinates")
            p["rd"] = [geo[0], geo[1]] if geo and len(geo) >= 2 else None
            uit.append(p)
        return uit

    def meldingen_bij_punt(self, x: float, y: float, straal_m: int = 400,
                           alleen_water: bool = True) -> list[dict]:
        """Gemelde emissies van inrichtingen binnen `straal_m` van een RD-punt.

        De straal staat bewust krap. Ruimer dan een paar honderd meter pakt in een industriegebied
        de buren mee: met 1500 m kreeg Sappi de zinkmelding van een naburig recyclingbedrijf
        toegewezen. Nabijheid alleen is hier geen bewijs van identiteit — vandaar dat
        `koppeling.py` er nog een naamvergelijking overheen legt.
        """
        if straal_m <= 0:
            raise ValueError(f"straal_m moet groter dan nul zijn (gekregen: {straal_m})")
        rijen = self._features(f"DWITHIN(geom,POINT({x} {y}),{straal_m},meters)")
        if alleen_water:
            rijen = [r for r in rijen if (r.get("mediumcode") or "").upper() == "WATER"]
        return rijen

    def inrichtingen_bij_punt(self, x: float, y: float, straal_m: int = 400) -> list[dict]:
        """De inrichtingen zelf, ontdubbeld — handig om te zien wie er in de buurt ligt."""
        per_id: dict[str, dict] = {}
        for r in self._features(f"DWITHIN(geom,POINT({x} {y}),{straal_m},meters)"):
            sleutel = r.get("nationalid") or r.get("productionsite_name") or ""
            per_id.setdefault(sleutel, {"nationalid": r.get("nationalid"),
                                        "naam": r.get("productionsite_name"),
                                        "rd": r.get("rd")})
        return sorted(per_id.values(), key=lambda v: (v["naam"] or ""))


__all__ = ["EprtrConnector", "ConnectorError", "BRON", "WFS", "LAAG"]
