"""Stelselcatalogus Omgevingswet: begrippen met hun juridische vindplaats.

Een federatieve SKOS-begrippengraaf achter een REST-API. Begrippenkaders van onder meer IMEV,
de regelgeving en de Omgevingswet-standaarden publiceren erin. Draait op DotWebStack van het
Kadaster — dat bleek uit een foutmelding, niet uit de documentatie.

Twee eigenaardigheden die het onthouden waard zijn:
  * De API weigert queryparameters die niet bij het endpoint horen mét een 400. `pageSize`
    samen met `zoekTerm` op /begrippen valt daaronder; stuur dus alleen wat mag.
  * Er komt geen RDF uit: text/turtle, application/ld+json en rdf+xml geven alle drie een 406.
    Het ís een graaf, maar je krijgt hem als HAL+JSON.
  * En let op de Accept-header: `application/json` wordt geweigerd met een 406, `application/
    hal+json` niet. Dat kost je een middag als je het niet weet.

Live geverifieerd 2026-09-14 op de productie-omgeving, met dezelfde DSO-sleutel als Ozon.
"""
from .base import BaseConnector, ConnectorError

ACCEPT = "application/hal+json"
SKOS_CONCEPT = "http://www.w3.org/2004/02/skos/core#Concept"
RELATIEVELDEN = ("isEngerDan", "isRuimerDan", "isGerelateerd",
                 "isGeneralisatieVan", "isSpecialisatieVan")


def _schema_naam(uri: str | None) -> str | None:
    """'…/id/conceptscheme/Regelgeving' → 'Regelgeving'."""
    if not uri:
        return None
    return str(uri).rstrip("/").split("/")[-1] or None


def _normaliseer(b: dict) -> dict:
    relaties = {}
    for veld in RELATIEVELDEN:
        waarde = b.get(veld)
        if waarde:
            relaties[veld] = len(waarde) if isinstance(waarde, list) else 1
    return {
        "term": b.get("term"),
        "definitie": b.get("definitie"),
        "uitleg": b.get("uitleg"),
        "conceptschema": b.get("conceptschema"),
        "conceptschema_naam": _schema_naam(b.get("conceptschema")),
        "vindplaats": b.get("metadata"),
        "is_skos_concept": b.get("type") == SKOS_CONCEPT,
        "relaties": relaties,
        "aantal_relaties": sum(relaties.values()),
    }


class StelselcatalogusConnector(BaseConnector):
    def __init__(self, base_url: str, api_key: str | None,
                 api_key_header: str = "x-api-key", **kwargs):
        super().__init__(**kwargs)
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self.api_key_header = api_key_header

    def _headers(self) -> dict:
        if not self.api_key:
            raise ConnectorError("Geen DSO_API_KEY geconfigureerd voor de Stelselcatalogus")
        # application/json geeft een 406 — deze API spreekt HAL.
        return {self.api_key_header: self.api_key, "Accept": ACCEPT}

    def zoek(self, zoekterm: str) -> list[dict]:
        """Begrippen die op de zoekterm passen. Alleen `zoekTerm` meesturen — zie moduletekst."""
        data = self.get_json(f"{self.base_url}/begrippen",
                             params={"zoekTerm": zoekterm}, headers=self._headers())
        ruw = (data.get("_embedded") or {}).get("begrippen") or []
        return [_normaliseer(b) for b in ruw]

    def conceptschemas(self) -> list[dict]:
        data = self.get_json(f"{self.base_url}/conceptschemas", headers=self._headers())
        return (data.get("_embedded") or {}).get("conceptschemas") or []
