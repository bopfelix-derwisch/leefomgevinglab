"""Contextset rond het lozingspunt, live opgehaald bij de echte bronnen.

Twee vragen die de keten zelf moet kunnen beantwoorden:
  1. Ontvangt een rijkswater deze lozing? De KRW-service van RWS bevat juist de rijkswateren
     (89 oppervlaktewaterlichamen); een treffer betekent dat de minister van IenW bevoegd gezag
     is en RWS uitvoert. Geen treffer betekent regionaal water, en dus het waterschap.
  2. Welke gemeente is bevoegd voor het milieudeel? Dat komt uit de bestuurlijke gebieden van PDOK.

Let op twee eigenaardigheden die bij het testen bovenkwamen: het geometrieattribuut heet bij de
KRW-service `shape` en bij de bestuurlijke gebieden `geom`, en die laatste negeert een
`cql_filter` — daar moet een bbox voor gebruikt worden.
"""
from ..ketenkern import wfs

KRW_WFS = "https://geo.rijkswaterstaat.nl/services/ogc/gdr/kaderrichtlijn_water/ows"
BG_WFS = "https://service.pdok.nl/kadaster/bestuurlijkegebieden/wfs/v1_0"

KRW_LAGEN = [
    ("kaderrichtlijn_water:KRW_oppervlaktewaterlichamen_vlak", "waterlichaam (vlak)"),
    ("kaderrichtlijn_water:KRW_oppervlaktewaterlichamen_lijn", "waterlichaam (lijn)"),
]


def contextset(x: float, y: float, straal_m: int = 1000, live: bool = True, haal=None) -> dict:
    bronnen = []
    leeg = {"straal_m": straal_m, "rd": [x, y], "waterlichaam": None, "owl_id": None,
            "stroomgebiedsdistrict": None, "rijkswater": None, "gemeente": None,
            "provincie": None, "watertype": None, "watercategorie": None,
            "waterstatus": None, "waterbeheerder": None, "omvang": None,
            "omvang_eenheid": None, "gemiddelde_diepte": None, "bronnen": bronnen}

    if not live:
        for _, oms in KRW_LAGEN:
            wfs.overgeslagen("RWS KRW-WFS", oms, bronnen)
        wfs.overgeslagen("PDOK bestuurlijke gebieden", "gemeente", bronnen)
        return {**leeg, "live": False, "volledig": False}

    haal = haal or wfs.standaard_haal
    waterlichaam = owl_id = sgd = None
    extra = {}
    for laag, oms in KRW_LAGEN:
        if waterlichaam:
            wfs.overgeslagen("RWS KRW-WFS", oms, bronnen)
            continue
        fs = wfs.haal_features(haal, KRW_WFS, wfs.features_params(
            laag, cql=f"DWITHIN(shape, POINT({x} {y}), {straal_m}, meters)",
            count=3,
            velden="naam,owl_id,sgd_id,gebtype,owltype,owlcat,owlstat,"
                   "wbhnaam,wbhcode,omvang,eenheid,gemdiepte"), "RWS KRW-WFS", oms, bronnen)
        if fs:
            p = fs[0]
            waterlichaam = (p.get("naam") or "").strip() or None
            owl_id, sgd = p.get("owl_id"), p.get("sgd_id")
            extra = {"watertype": p.get("owltype"), "watercategorie": p.get("owlcat"),
                     "waterstatus": p.get("owlstat"),
                     "waterbeheerder": (p.get("wbhnaam") or "").strip() or None,
                     "omvang": p.get("omvang"), "omvang_eenheid": p.get("eenheid"),
                     "gemiddelde_diepte": p.get("gemdiepte")}

    gem = wfs.haal_features(haal, BG_WFS, wfs.features_params(
        "bestuurlijkegebieden:Gemeentegebied", bbox=wfs.bbox_rd(x, y, 50), count=3,
        velden="naam,ligtInProvincieNaam"), "PDOK bestuurlijke gebieden", "gemeente", bronnen)

    volledig = all(b["status"] == "ok" for b in bronnen if b["status"] != "overgeslagen")
    return {**leeg, **extra, "live": True, "volledig": volledig,
            "waterlichaam": waterlichaam, "owl_id": owl_id, "stroomgebiedsdistrict": sgd,
            "rijkswater": bool(owl_id),
            "gemeente": (gem[0].get("naam") if gem else None),
            "provincie": (gem[0].get("ligtInProvincieNaam") if gem else None)}


def bevoegd_gezag(cs: dict) -> dict:
    """Leid het bevoegd gezag af uit wat de bronnen teruggaven."""
    if cs.get("rijkswater"):
        beheerder = cs.get("waterbeheerder")
        if beheerder:
            lozing, bron = beheerder, "RWS KRW-service (veld wbhnaam)"
        else:
            lozing = "Minister van IenW, uitgevoerd door Rijkswaterstaat"
            bron = "afgeleid uit de aanwezigheid van owl_id"
        grond = (f"het lozingspunt ligt aan {cs.get('waterlichaam') or 'een rijkswater'} "
                 f"({cs.get('owl_id')}), een water in rijksbeheer")
    elif cs.get("live"):
        lozing, bron = "het waterschap als waterbeheerder", "afgeleid: geen treffer in de KRW-service"
        grond = "geen rijkswaterlichaam gevonden binnen de straal; dan is het regionaal water"
    else:
        lozing, bron = "niet bepaald (bronnen niet bevraagd)", "niet bevraagd"
        grond = "zonder live-modus valt het bevoegd gezag niet af te leiden"
    gem = cs.get("gemeente")
    return {"lozingsactiviteit": lozing, "grondslag": grond, "bron_beheerder": bron,
            "milieubelastende_activiteit": (f"burgemeester en wethouders van {gem}" if gem
                                            else "de gemeente (niet bepaald)"),
            "gemeente": gem, "provincie": cs.get("provincie")}
