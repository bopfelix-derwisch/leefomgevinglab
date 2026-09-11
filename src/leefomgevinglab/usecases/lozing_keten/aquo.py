"""Het uit Aquo afgeleide objectmodel, als annotatieset binnen STOP/TPOD.

Waar het Seveso-besluit annotaties uit IMEV krijgt, komen ze hier uit Aquo — de gedeelde taal
van het waterdomein, beheerd door het Informatiehuis Water. Zelfde constructie, ander vocabulaire:
het besluit draagt de gegevens die anders in een los dossier zouden blijven hangen.

STOP/TPOD kent geen toepassingsprofiel voor een vergunningbesluit; de annotatienamen hieronder
zijn een voorstel van dit lab in de stijl van de bestaande TPOD-annotaties.
"""
from .beoordeling import abm_klasse

AQUO_VERPLICHT = ("identificatie", "bevoegdgezag", "begin_geldigheid", "tijdstip_registratie",
                  "lozingspunt", "ontvangend_waterlichaam", "lozingsactiviteit", "parameter",
                  "emissiegrenswaarde", "meetverplichting", "lozingsobject")


def _a(annotatie, uit_aquo, cim_objecttype, verplicht, uitleg):
    return {"annotatie": annotatie, "uit_imev": uit_aquo, "uit_aquo": uit_aquo,
            "cim_objecttype": cim_objecttype, "verplicht": verplicht, "uitleg": uitleg}


ANNOTATIES = [
    _a("Identificatie", "identificatie", None, True,
       "De identificatie van het lozingsobject in het besluit."),
    _a("BevoegdGezag", "bevoegdgezag", "VTH-INSTANTIE", True,
       "Bij rijkswater de minister van IenW; bij regionaal water het waterschap. Machineleesbaar, "
       "zodat achteraf te bepalen valt wie waarover besloot."),
    _a("Geldigheid", "begin_geldigheid", None, True,
       "Inwerkingtreding van het besluit — meteen de begindatum van het registerobject."),
    _a("Registratie", "tijdstip_registratie", None, True, "Het publicatietijdstip."),
    _a("Lozingspunt", "lozingspunt", "GEO-OBJECT", True,
       "De plek waar het water het oppervlaktewater in gaat, als punt met CRS."),
    _a("OntvangendWaterlichaam", "ontvangend_waterlichaam", "ANDER GEO-OBJECT", True,
       "Het KRW-waterlichaam dat de lozing ontvangt. Het CIM heeft hier geen eigen objecttype voor; "
       "het belandt in de restbak ANDER GEO-OBJECT."),
    _a("Lozingsactiviteit", "lozingsactiviteit", "ACTIVITEIT", True,
       "De activiteit uit de Bal-structuur, in plaats van een eigen lozingentypologie."),
    _a("Parameter", "parameter", None, True,
       "De stof of somparameter waarop wordt genormeerd, met de Aquo-parametercode."),
    _a("Emissiegrenswaarde", "emissiegrenswaarde", None, True,
       "De vergunde concentratie of vracht per parameter — het getal waarop later gehandhaafd wordt."),
    _a("Meetverplichting", "meetverplichting", None, True,
       "Hoe vaak en waar gemeten moet worden. Vandaag staat dit in de tekst van de vergunning en "
       "moet een toezichthouder het eruit lezen."),
    _a("Lozingsobject", "lozingsobject", "VTH-OBJECT", True,
       "De lozing zelf als object waaraan alles hangt."),
    _a("Voorschrift", None, "SPECIFIEK VOORSCHRIFT", False,
       "Geen Aquo-herkomst: dit komt uit het besluit zelf, en is precies wat een toezichthouder "
       "nodig heeft om een overtreding aan vast te knopen."),
]

VERPLICHTE_ANNOTATIES = [a["annotatie"] for a in ANNOTATIES if a["verplicht"]]


def bouw_besluit(casus: dict, toets: dict, voorschriften: list, kenmerk: str,
                 waterlichaam: str | None, bevoegd_gezag: str) -> dict:
    x, y = casus["rd"]
    delen = [
        {"id": "art-1", "kop": "Artikel 1 — Vergunning",
         "tekst": f"Aan {casus['bedrijf']} wordt vergunning verleend voor het lozen van "
                  f"{casus['lozing']['soort']} op {waterlichaam or 'het ontvangende oppervlaktewater'} "
                  f"vanaf lozingspunt {casus['lozing']['lozingspunt']}.",
         "annotaties": [
             {"annotatie": "Lozingsobject", "waarde": casus["vestiging"]},
             {"annotatie": "Identificatie", "waarde": f"NL.AQUO.{kenmerk}"},
             {"annotatie": "Lozingsactiviteit", "waarde": "lozingsactiviteit op een oppervlaktewaterlichaam"},
             {"annotatie": "Lozingspunt", "waarde": f"POINT({x} {y})", "crs": "EPSG:28992"},
             {"annotatie": "OntvangendWaterlichaam", "waarde": waterlichaam or "onbekend"},
             {"annotatie": "BevoegdGezag", "waarde": bevoegd_gezag},
         ]},
        {"id": "art-2", "kop": "Artikel 2 — Emissiegrenswaarden",
         "tekst": "Voor de hieronder genoemde parameters gelden de vermelde grenswaarden.",
         "annotaties": [x for p in toets["parameters"] for x in (
             {"annotatie": "Parameter", "waarde": p["naam"], "zzs": p["zzs"],
              "saneringsinspanning": p["abm"]},
             {"annotatie": "Emissiegrenswaarde", "waarde": p["concentratie_mg_l"],
              "eenheid": "mg/l", "parameter": p["naam"], "indicatief": True})]},
        {"id": "art-3", "kop": "Artikel 3 — Meten en rapporteren",
         "tekst": "De vergunninghouder meet de lozing en rapporteert jaarlijks aan het bevoegd gezag.",
         "annotaties": [{"annotatie": "Meetverplichting", "waarde": "maandelijks bemonsteren op "
                                                                    "het lozingspunt; jaarrapportage"}]},
        {"id": "art-4", "kop": "Artikel 4 — Voorschriften",
         "tekst": "Aan deze vergunning zijn de volgende voorschriften verbonden.",
         "annotaties": [{"annotatie": "Voorschrift", "waarde": v["id"], "tekst": v["tekst"]}
                        for v in voorschriften]},
        {"id": "art-5", "kop": "Artikel 5 — Inwerkingtreding",
         "tekst": "Dit besluit treedt in werking met ingang van de dag na bekendmaking.",
         "annotaties": [{"annotatie": "Geldigheid", "waarde": "2026-06-25"},
                        {"annotatie": "Registratie", "waarde": "2026-06-24T09:00:00Z"}]},
    ]
    return {"kenmerk": kenmerk, "soort": "omgevingsvergunning lozingsactiviteit",
            "standaard": "STOP/TPOD (voorgesteld profiel — bestaat nog niet)",
            "tekstdelen": delen}


def valideer(document: dict) -> dict:
    aanwezig = {a["annotatie"] for d in document.get("tekstdelen", []) for a in d.get("annotaties", [])}
    ontbrekend = [a for a in VERPLICHTE_ANNOTATIES if a not in aanwezig]
    return {"ok": not ontbrekend, "aanwezig": sorted(aanwezig), "ontbrekend": ontbrekend,
            "verplicht": len(VERPLICHTE_ANNOTATIES)}


def naar_register(document: dict) -> dict:
    """Wat een Register Lozingen uit dit besluit zou krijgen — als het bestond."""
    plat = {}
    for deel in document.get("tekstdelen", []):
        for a in deel.get("annotaties", []):
            plat.setdefault(a["annotatie"], []).append(a)
    veld = {a["annotatie"]: a["uit_aquo"] for a in ANNOTATIES if a["uit_aquo"]}
    record, herkomst = {}, {}
    for annotatie, items in plat.items():
        if annotatie not in veld:
            continue
        record[veld[annotatie]] = items[0].get("waarde") if len(items) == 1 else [i.get("waarde") for i in items]
        herkomst[veld[annotatie]] = f"annotatie {annotatie} in {document['kenmerk']}"
    return {"record": record, "herkomst": herkomst,
            "uit_besluit": sorted(record),
            "los_aan_te_leveren": [v for v in AQUO_VERPLICHT if v not in record],
            "register_bestaat": False,
            "opmerking": "Er is geen landelijk register voor lozingen. Dit laat zien wat een "
                         "register zou krijgen, en dus wat er nu na bekendmaking verdwijnt."}


__all__ = ["AQUO_VERPLICHT", "ANNOTATIES", "VERPLICHTE_ANNOTATIES", "bouw_besluit",
           "valideer", "naar_register", "abm_klasse"]
