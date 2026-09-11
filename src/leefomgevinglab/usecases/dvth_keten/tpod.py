"""Het uit IMEV afgeleide objectmodel, als annotatieset binnen STOP/TPOD.

Dit is het inhoudelijke hart van de ombouw uit het doelbeeld: de eigenschappen die het REV
vandaag via een aparte IMEV 3.0.2-levering binnenkrijgt, worden annotaties óp de tekst van
het vergunningbesluit. Het besluit draagt dan zelf de brongegevens.

Let op: STOP/TPOD kent vandaag geen toepassingsprofiel voor een vergunningbesluit. De
annotatienamen hieronder zijn dus een voorstel van dit lab in de stijl van de bestaande
TPOD-annotaties, geen vastgestelde standaard.
"""
from .casus import AFSTANDEN_M

# De IMEV-eigenschappen die in het doelbeeld een plek in het besluit moeten krijgen.
# De eerste vijf zijn de base-verplichte attributen van elk ExterneVeiligheidsobject —
# dezelfde die de WFS-check op /wfs-kwaliteit meet.
IMEV_VERPLICHT = ("identificatie", "bronhoudercode", "bevoegdgezag", "begin_geldigheid",
                  "tijdstip_registratie", "geometrie", "evactiviteit", "maatgevende_stof",
                  "aandachtsgebied", "risicobron")


def _a(annotatie, uit_imev, cim_objecttype, verplicht, uitleg):
    return {"annotatie": annotatie, "uit_imev": uit_imev, "cim_objecttype": cim_objecttype,
            "verplicht": verplicht, "uitleg": uitleg}


ANNOTATIES = [
    _a("Identificatie", "identificatie", None, True,
       "De NL.IMEV-identificatie wordt de identiteit van het geannoteerde object in het besluit."),
    _a("Bronhouder", "bronhoudercode", "VTH-INSTANTIE", True,
       "Vandaag een los veld dat de bronhouder zelf invult; in het doelbeeld volgt het uit "
       "wie het besluit publiceert."),
    _a("BevoegdGezag", "bevoegdgezag", "VTH-INSTANTIE", True,
       "Het bevoegd gezag staat al in de kop van het besluit — hier wordt het machineleesbaar. "
       "Precies het veld dat 40 van de 45 REV-lagen vandaag niet ontsluiten."),
    _a("Geldigheid", "begin_geldigheid", None, True,
       "De inwerkingtreding van het besluit is de begindatum van het registerobject. Eén datum "
       "in plaats van twee die uiteen kunnen lopen."),
    _a("Registratie", "tijdstip_registratie", None, True,
       "Het publicatietijdstip. In de huidige route is dit het moment van aanleveren, dat "
       "maanden na het besluit kan liggen."),
    _a("Locatie", "geometrie", "GEO-OBJECT", True,
       "TPOD annoteert tekst met locaties; de geometrie van de risicobron en van elk "
       "aandachtsgebied hangt aan de bijbehorende tekstdelen."),
    _a("Activiteit", "evactiviteit", "ACTIVITEIT", True,
       "De activiteit uit de Bal-structuur, in plaats van de eigen REV-activiteitenlijst — "
       "het einde van twee concurrerende activiteitvocabulaires."),
    _a("MaatgevendeStof", "maatgevende_stof", None, True,
       "Als gestructureerde waarde, niet als JSON-string in een tekstveld zoals de WFS die nu levert."),
    _a("Aandachtsgebied", "aandachtsgebied", "VTH-OBJECT", True,
       "Brand-, explosie- en gifwolkaandachtsgebied als gebiedsaanwijzing bij het voorschrift "
       "waaruit ze volgen."),
    _a("Risicobron", "risicobron", "VTH-OBJECT", True,
       "De inrichting zelf als object waaraan alles hangt."),
    _a("Voorschrift", None, "SPECIFIEK VOORSCHRIFT", False,
       "Geen IMEV-herkomst: dit komt uit het besluit zelf en is precies wat de huidige "
       "REV-route kwijtraakt — de regel waaraan later gehandhaafd wordt."),
]

VERPLICHTE_ANNOTATIES = [a["annotatie"] for a in ANNOTATIES if a["verplicht"]]


def bouw_besluit(casus: dict, aandachtsgebieden: list, voorschriften: list, kenmerk: str) -> dict:
    """Het vergunningbesluit als geannoteerd document in de stijl van STOP/TPOD."""
    stof = next((s["naam"] for s in casus["stoffen"] if s.get("maatgevend")), None)
    x, y = casus["rd"]
    delen = [
        {"id": "art-1", "kop": "Artikel 1 — Vergunning",
         "tekst": f"Aan {casus['bedrijf']} wordt vergunning verleend voor het exploiteren van een "
                  f"Seveso-inrichting op de locatie {casus['adres']}.",
         "annotaties": [
             {"annotatie": "Risicobron", "waarde": casus["vestiging"]},
             {"annotatie": "Identificatie", "waarde": f"NL.IMEV.{kenmerk}"},
             {"annotatie": "Activiteit", "waarde": "exploiteren van een Seveso-inrichting"},
             {"annotatie": "Locatie", "waarde": f"POINT({x} {y})", "crs": "EPSG:28992"},
             {"annotatie": "MaatgevendeStof", "waarde": stof},
             {"annotatie": "BevoegdGezag", "waarde": casus["bevoegd_gezag"]},
             {"annotatie": "Bronhouder", "waarde": casus["uitvoering"]},
         ]},
        {"id": "art-2", "kop": "Artikel 2 — Aandachtsgebieden",
         "tekst": "Rond de inrichting gelden de hieronder aangewezen aandachtsgebieden.",
         "annotaties": [{"annotatie": "Aandachtsgebied", "waarde": a["soort"],
                         "afstand_m": a["afstand_m"], "indicatief": True}
                        for a in aandachtsgebieden]},
        {"id": "art-3", "kop": "Artikel 3 — Voorschriften",
         "tekst": "Aan deze vergunning zijn de volgende voorschriften verbonden.",
         "annotaties": [{"annotatie": "Voorschrift", "waarde": v["id"], "tekst": v["tekst"]}
                        for v in voorschriften]},
        {"id": "art-4", "kop": "Artikel 4 — Inwerkingtreding",
         "tekst": "Dit besluit treedt in werking met ingang van de dag na bekendmaking.",
         "annotaties": [{"annotatie": "Geldigheid", "waarde": "2026-05-14"},
                        {"annotatie": "Registratie", "waarde": "2026-05-13T09:00:00Z"}]},
    ]
    return {"kenmerk": kenmerk, "soort": "omgevingsvergunning milieubelastende activiteit",
            "standaard": "STOP/TPOD (voorgesteld profiel — bestaat nog niet)",
            "tekstdelen": delen}


def valideer(document: dict) -> dict:
    """Heeft elke verplichte annotatie een plek gekregen in het document?"""
    aanwezig = {a["annotatie"] for d in document.get("tekstdelen", []) for a in d.get("annotaties", [])}
    ontbrekend = [a for a in VERPLICHTE_ANNOTATIES if a not in aanwezig]
    return {"ok": not ontbrekend, "aanwezig": sorted(aanwezig), "ontbrekend": ontbrekend,
            "verplicht": len(VERPLICHTE_ANNOTATIES)}


def naar_rev(document: dict) -> dict:
    """Zet het geannoteerde besluit om naar een registerobject — het besluit ís de aanlevering."""
    plat = {}
    for deel in document.get("tekstdelen", []):
        for a in deel.get("annotaties", []):
            plat.setdefault(a["annotatie"], []).append(a)
    veld = {a["annotatie"]: a["uit_imev"] for a in ANNOTATIES if a["uit_imev"]}
    record, herkomst = {}, {}
    for annotatie, items in plat.items():
        if annotatie not in veld:
            continue
        record[veld[annotatie]] = items[0].get("waarde") if len(items) == 1 else [i.get("waarde") for i in items]
        herkomst[veld[annotatie]] = f"annotatie {annotatie} in {document['kenmerk']}"
    return {"record": record, "herkomst": herkomst,
            "uit_besluit": sorted(record), "los_aan_te_leveren": [v for v in IMEV_VERPLICHT if v not in record]}


def afstanden_voor(casus: dict) -> list:
    """Indicatieve aandachtsgebieden op basis van de maatgevende stof."""
    stoffen = {s["naam"] for s in casus["stoffen"]}
    uit = []
    if "ammoniak" in stoffen:
        uit.append({"soort": "gifwolkaandachtsgebied", "afstand_m": AFSTANDEN_M["gifwolkaandachtsgebied"],
                    "grond": "acuut toxisch gas, tot vloeistof verdicht"})
    if "propaan" in stoffen:
        uit += [{"soort": "brandaandachtsgebied", "afstand_m": AFSTANDEN_M["brandaandachtsgebied"],
                 "grond": "brandbaar gas in drukhouder"},
                {"soort": "explosieaandachtsgebied", "afstand_m": AFSTANDEN_M["explosieaandachtsgebied"],
                 "grond": "brandbaar gas in drukhouder"}]
    return uit
