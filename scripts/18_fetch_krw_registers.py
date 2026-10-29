#!/usr/bin/env python3
"""De KRW-registers van het Waterkwaliteitsportaal ophalen — machinaal, zonder sleutel.

De downloadmodule van het WKP is een Angular-app waar je je door vier keuzelijsten heen klikt,
en de rest van dit lab haalt zijn WKP-data daarom met de hand op. Dat hoeft niet: onder de app
zit een gewone JSON-API, open en zonder authenticatie. De basis staat in de runtime-configuratie
van de app zelf (`/assets/config/config.json`, veld `backendUrl`):

    GET  /api/v1/data-downloads/options/themes-and-subjects     de catalogus, 29 onderwerpen
    GET  /api/v1/data-downloads/options/filter-values?subject_id=N   jaren/gebieden per onderwerp
    POST /api/v1/data-downloads/download                        een zip met csv of gpkg

Let op bij die POST: het verzoek is een **lijst**, en het veld heet `subjectId` — niet het
`subject`-object dat de frontend intern doorgeeft. Stuur je dat object, dan antwoordt de API
`[0].SubjectId: Must not be null`.

Dit is géén officieel gepubliceerde API en kan zonder aankondiging veranderen. Daarom haalt dit
script de catalogus eerst op en zoekt het de onderwerp-id's op naam op, in plaats van ze hard te
coderen: verschuift een id, dan valt dit script luid om in plaats van stil het verkeerde bestand
binnen te halen.

**Wat we ophalen en waarom.**

`KRW-monitoringlocaties-geometrie` is strikt beter dan het meetobjectenbestand per waterbeheerder
dat `scripts/13` gebruikt. Dat laatste dekt alleen Rijkswaterstaat (322 punten, waarvan er 131 een
waterlichaam dragen); dit dekt heel Nederland (1571 punten) en draagt bij **alle** een
`waterlichaamCode`, plus het stroomgebieddistrict en een puntgeometrie die al in RD staat. In het
Maasdistrict liggen 395 meetpunten, verdeeld over zes beheerders — Rijkswaterstaat heeft er maar
21 van.

Het lost ook de namespace-breuk op die elders in dit lab met de hand wordt overbrugd: Eijsden
heet in de meetwaarden `NL80_EIJSDPTN` en hier `NL91_EIJSDPTN`, mét `waterlichaamCode NL91BOM`
erbij. Dit bestand is de gezaghebbende brug tussen die twee schrijfwijzen.

`KRW-oppervlaktewaterlichamen` geeft de 745 waterlichamen met hun stroomgebieddistrict en
waterbeheerder. Daarmee kan de zoekstraal van 50 km rond een meetpunt — een cirkel waar een
stroomgebied geen cirkel is — vervangen worden door een lidmaatschapsvraag: ligt dit waterlichaam
in district Maas? Het district telt er **163**, waarvan 14 van Rijkswaterstaat, terwijl
`toerekening.STROOMVOLGORDE` er 8 kent. De zes ontbrekende RWS-waterlichamen zijn geen
voetnoot: het Julianakanaal en de Midden-Limburgse en Noord-Brabantse kanalen zitten erbij, en
een vergunning die daarop loost valt vandaag buiten de hele toerekening.

**Wat er níét in zit.** In geen van de 29 onderwerpen staat de bovenstrooms-relatie tussen
waterlichamen. `VoorgangerCode` lijkt erop maar is versiehistorie, geen hydrologie. De
stroomvolgorde in `toerekening.py` blijft dus een keuze van dit lab — alleen kan hij nu over 163
waterlichamen gaan in plaats van over 8.

Draaien:

    PYTHONPATH=src .venv/bin/python scripts/18_fetch_krw_registers.py \\
        --uit /mnt/nvme/geluidsmeter/data/external/wkp

    PYTHONPATH=src .venv/bin/python scripts/18_fetch_krw_registers.py --catalogus
"""
import argparse
import csv
import io
import json
import sys
import zipfile
from datetime import datetime, timezone
from pathlib import Path

import httpx

BASIS = "https://wkp.rws.nl/api/v1/data-downloads"
JAAR = 2025

BRON = {
    "naam": "Waterkwaliteitsportaal — KRW-registers",
    "houder": "Informatiehuis Water",
    "url": "https://wkp.rws.nl/downloadmodule",
    "let_op": ("opgehaald via de JSON-API onder de downloadmodule; die is open maar niet "
               "officieel gepubliceerd en kan zonder aankondiging veranderen"),
}


def catalogus(client: httpx.Client) -> dict:
    r = client.get(f"{BASIS}/options/themes-and-subjects",
                   headers={"Accept": "application/json"})
    r.raise_for_status()
    return r.json()


def onderwerp_id(cat: dict, naam: str) -> int:
    """De id van een onderwerp, opgezocht op naam.

    Hardcoderen van de id zou dit script stil het verkeerde bestand laten ophalen als de
    catalogus verschuift. Een onbekende naam is hier daarom een fout, geen terugval.
    """
    for thema in cat.get("themes", []):
        for s in thema.get("subjects", []):
            if s.get("name") == naam:
                return int(s["id"])
    beschikbaar = sorted(s["name"] for t in cat.get("themes", []) for s in t.get("subjects", []))
    raise SystemExit(f"onderwerp '{naam}' staat niet in de catalogus; wel: {beschikbaar}")


def haal_zip(client: httpx.Client, subject_id: int, jaar: int = JAAR) -> zipfile.ZipFile:
    """Eén onderwerp als zip. Het verzoek is een lijst en het veld heet `subjectId`."""
    r = client.post(f"{BASIS}/download",
                    headers={"Accept": "application/zip", "Content-Type": "application/json"},
                    json=[{"subjectId": subject_id, "year": jaar,
                           "areaLevel": "nederland", "areaName": None,
                           "filename": f"WKP_{subject_id}_{jaar}"}])
    r.raise_for_status()
    return zipfile.ZipFile(io.BytesIO(r.content))


def _enige(z: zipfile.ZipFile, achtervoegsel: str) -> str:
    treffers = [n for n in z.namelist() if n.lower().endswith(achtervoegsel)]
    if len(treffers) != 1:
        raise SystemExit(f"verwachtte precies één {achtervoegsel} in de zip, kreeg {treffers}")
    return treffers[0]


def verdicht_waterlichamen(csv_tekst: str) -> dict:
    """De waterlichamen tot een opzoektabel op code.

    Alleen de velden waar dit lab iets mee doet; de rest (geldigheidsdata, versiehistorie,
    karakterschetslinks) blijft in de bron staan en hoort niet in een afgeleid bestand.
    """
    per_code: dict[str, dict] = {}
    per_district: dict[str, list] = {}
    for r in csv.DictReader(io.StringIO(csv_tekst), delimiter=";"):
        code = (r.get("WaterlichaamCode") or "").strip()
        if not code:
            continue
        district = (r.get("StroomgebieddistrictNaam") or "").strip() or None
        per_code[code] = {
            "code": code,
            "naam": (r.get("WaterlichaamNaam") or "").strip() or code,
            "district": district,
            "district_code": (r.get("StroomgebieddistrictCode") or "").strip() or None,
            "beheerder": (r.get("WaterbeheerderNaam") or "").strip() or None,
            "categorie": (r.get("OppervlaktewaterCategorie") or "").strip() or None,
            "watertype": (r.get("OppervlaktewaterWatertypeCode") or "").strip() or None,
            "status": (r.get("OppervlaktewaterStatus") or "").strip() or None,
        }
        if district:
            per_district.setdefault(district, []).append(code)
    return {"bron": BRON, "onderwerp": "KRW-oppervlaktewaterlichamen",
            "opgehaald_op": datetime.now(timezone.utc).strftime("%Y-%m-%d"),
            "waterlichamen": per_code,
            "per_district": {d: sorted(v) for d, v in sorted(per_district.items())},
            "telling": {"waterlichamen": len(per_code), "districten": len(per_district)}}


def verdicht_monitoringlocaties(gpkg_pad: str) -> dict:
    """De monitoringlocaties tot punt, waterlichaam en district per code.

    De geometrie komt al in RD binnen (EPSG:28992), hetzelfde stelsel als de Atlas-vergunningen,
    dus er wordt hier niets geprojecteerd. Wijkt de bron daarvan af, dan valt dat op als een fout
    in plaats van als een punt dat stilletjes in zee ligt.
    """
    import geopandas as gpd

    g = gpd.read_file(gpkg_pad)
    if g.crs is None or g.crs.to_epsg() != 28992:
        raise SystemExit(f"verwachtte EPSG:28992, kreeg {g.crs}")

    per_code: dict[str, dict] = {}
    for _, rij in g.iterrows():
        code = str(rij.get("monitoringlocatieCode") or "").strip()
        if not code:
            continue
        punt = rij.geometry
        per_code[code] = {
            "code": code,
            "naam": str(rij.get("naam") or "").strip() or code,
            "rd": [round(punt.x, 1), round(punt.y, 1)] if punt is not None and not punt.is_empty
                  else None,
            "waterlichaam": str(rij.get("waterlichaamCode") or "").strip() or None,
            "waterlichaam_naam": str(rij.get("waterlichaamNaam") or "").strip() or None,
            "district": str(rij.get("stroomgebieddistrictNaam") or "").strip() or None,
            "beheerder": str(rij.get("waterbeheerderNaam") or "").strip() or None,
            "chemisch": str(rij.get("chemischeMonitoring") or "").strip().lower() in ("ja", "true", "1"),
        }
    zonder = [c for c, v in per_code.items() if not v["waterlichaam"]]
    return {"bron": BRON, "onderwerp": "KRW-monitoringlocaties-geometrie",
            "opgehaald_op": datetime.now(timezone.utc).strftime("%Y-%m-%d"),
            "locaties": per_code,
            "telling": {"locaties": len(per_code), "zonder_waterlichaam": len(zonder)}}


def _toon_catalogus(cat: dict) -> None:
    for thema in cat.get("themes", []):
        print(f"## {thema.get('name')}")
        for s in thema.get("subjects", []):
            print(f"   {s['id']:>3}  {s['name']}")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--uit", help="map voor de verdichte bestanden")
    ap.add_argument("--jaar", type=int, default=JAAR)
    ap.add_argument("--catalogus", action="store_true",
                    help="toon alleen de beschikbare onderwerpen en stop")
    a = ap.parse_args()

    with httpx.Client(timeout=300.0, follow_redirects=True) as client:
        cat = catalogus(client)
        if a.catalogus:
            _toon_catalogus(cat)
            return 0
        if not a.uit:
            ap.error("--uit is verplicht als je niet alleen de catalogus opvraagt")

        uit = Path(a.uit)
        uit.mkdir(parents=True, exist_ok=True)

        z = haal_zip(client, onderwerp_id(cat, "KRW-oppervlaktewaterlichamen"), a.jaar)
        wl = verdicht_waterlichamen(z.read(_enige(z, ".csv")).decode("utf-8-sig"))
        (uit / "krw_waterlichamen.json").write_text(
            json.dumps(wl, ensure_ascii=False, indent=1))
        maas = wl["per_district"].get("Maas", [])
        print(f"{wl['telling']['waterlichamen']} waterlichamen in "
              f"{wl['telling']['districten']} districten; district Maas: {len(maas)} "
              f"-> {uit / 'krw_waterlichamen.json'}")

        z = haal_zip(client, onderwerp_id(cat, "KRW-monitoringlocaties-geometrie"), a.jaar)
        naam = _enige(z, ".gpkg")
        tijdelijk = uit / naam
        tijdelijk.write_bytes(z.read(naam))
        try:
            ml = verdicht_monitoringlocaties(str(tijdelijk))
        finally:
            tijdelijk.unlink(missing_ok=True)
        (uit / "krw_monitoringlocaties.json").write_text(
            json.dumps(ml, ensure_ascii=False, indent=1))
        t = ml["telling"]
        print(f"{t['locaties']} monitoringlocaties, {t['zonder_waterlichaam']} zonder "
              f"waterlichaam -> {uit / 'krw_monitoringlocaties.json'}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
