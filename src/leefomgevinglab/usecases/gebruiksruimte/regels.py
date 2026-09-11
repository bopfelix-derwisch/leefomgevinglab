"""Welke regels gelden op deze locatie, en werken ze direct of indirect door?

De regelingen komen live uit het DSO (Ozon Presenteren). De classificatie naar werking en de
duiding voor een lozingsvoornemen zijn van dit lab.

Het onderscheid dat deze case wil laten zien:
  * direct werkend — de regel bindt de initiatiefnemer zelf (AMvB, omgevingsplan, verordening);
  * indirect werkend — de regel bindt het bevoegd gezag en werkt via de vergunning door naar de
    initiatiefnemer (instructieregels, programma's, aanwijzingsbesluiten).

En een derde categorie die makkelijk wordt gemist: een regeling die op de locatie geldt maar
dit voornemen niet raakt. De waterschapsverordening is daar het schoolvoorbeeld van — ze staat
op elke IJsseloever, maar een lozing op rijkswater valt eronder niet.
"""

BRON = "DSO Presenteren (Ozon) — live"

WERKING = {
    "AMvB": "direct",
    "Omgevingsplan": "direct",
    "Omgevingsverordening": "direct",
    "Waterschapsverordening": "direct",
    "Voorbeschermingsregels": "direct",
    "Voorbeschermingsregels Omgevingsplan": "direct",
    "Omgevingsvisie": "indirect",
    "Programma": "indirect",
    "Aanwijzingsbesluit N2000": "indirect",
    "Projectbesluit": "direct",
    "Instructie": "indirect",
}

# Wat een regelingtype betekent voor een lozingsvoornemen op rijkswater.
_DUIDING = {
    "AMvB": ("Rijksregels. Voor deze lozing is de kern dat lozen op een oppervlaktewaterlichaam "
             "een vergunningplichtige lozingsactiviteit is, met de waterbeheerder als bevoegd gezag.", True),
    "Omgevingsplan": ("Bindt de locatie zelf: wat mag hier staan en gebeuren. Bepaalt of de "
                      "inrichting er überhaupt mag komen — los van de vraag of er geloosd mag worden.", True),
    "Omgevingsverordening": ("Provinciale regels die op deze locatie doorwerken, bijvoorbeeld voor "
                             "grondwaterbescherming of stiltegebied.", True),
    "Waterschapsverordening": ("Geldt op deze locatie, maar raakt dit voornemen niet: het gaat om "
                               "een lozing op rijkswater, en daarvoor is niet het waterschap maar "
                               "de minister van IenW bevoegd gezag.", False),
    "Voorbeschermingsregels": ("Tijdelijke bescherming vooruitlopend op een wijziging. Kan een "
                               "aanvraag blokkeren zolang die loopt.", True),
    "Voorbeschermingsregels Omgevingsplan": ("Tijdelijke bescherming vooruitlopend op een wijziging "
                                             "van het omgevingsplan.", True),
    "Omgevingsvisie": ("Beleid, geen bindende regel voor de initiatiefnemer. Werkt door in de "
                       "afweging van het bevoegd gezag.", True),
    "Programma": ("Beleidsprogramma. Bindt het bestuursorgaan, niet de aanvrager — maar bepaalt wel "
                  "hoeveel ruimte het bevoegd gezag zichzelf toestaat te vergeven.", True),
    "Aanwijzingsbesluit N2000": ("Natura 2000. Werkt indirect maar hard door: een lozing die de "
                                 "instandhoudingsdoelen kan raken, vraagt een aanvullende toets "
                                 "bovenop de lozingsvergunning.", True),
}
_ONBEKEND = ("Type niet geclassificeerd door dit lab; werking onbekend.", True)


def werking(type_: str) -> str:
    return WERKING.get(type_, "onbekend")


def duiding(regeling: dict, rijkswater: bool, tabel: dict | None = None) -> dict:
    """Eén regeling, geclassificeerd en geduid voor dit voornemen.

    `tabel` laat een andere case (zoals externe veiligheid) zijn eigen duiding meegeven;
    de classificatie naar werking is gedeeld.
    """
    t = regeling.get("type") or "onbekend"
    tekst, van_toepassing = (tabel or _DUIDING).get(t, _ONBEKEND)
    if tabel is None and t == "Waterschapsverordening" and not rijkswater:
        tekst = ("Regionaal water: dan is het waterschap de waterbeheerder, en geldt deze "
                 "verordening wél voor de lozing.")
        van_toepassing = True
    return {"titel": regeling.get("titel"), "type": t, "werking": werking(t),
            "bevoegd_gezag": regeling.get("bevoegd_gezag"),
            "betekenis": tekst, "van_toepassing": van_toepassing}


def regels_op_locatie(x: float, y: float, rijkswater: bool = True, live: bool = True,
                      _haal=None, maximaal: int = 25, tabel: dict | None = None) -> dict:
    """Haal de geldende regelingen op en classificeer ze. Valt een bron weg, dan gaat de case door."""
    if not live:
        return {"live": False, "status": "overgeslagen", "regelingen": [], "bron": BRON,
                "telling": {}}
    try:
        ruw = (_haal or _standaard_haal)((x, y))
    except Exception as exc:
        return {"live": True, "status": "onbereikbaar", "regelingen": [], "bron": BRON,
                "fout": type(exc).__name__, "telling": {}}

    uit = [duiding(r, rijkswater, tabel) for r in ruw[:maximaal]]
    uit.sort(key=lambda r: (r["werking"] != "direct", not r["van_toepassing"], r["type"]))
    telling = {}
    for r in uit:
        sleutel = "niet van toepassing" if not r["van_toepassing"] else r["werking"]
        telling[sleutel] = telling.get(sleutel, 0) + 1
    return {"live": True, "status": "ok", "regelingen": uit, "bron": BRON, "telling": telling}


def _standaard_haal(rd):
    """De echte DSO-bevraging; los gehouden zodat de tests hem kunnen vervangen."""
    import os
    from leefomgevinglab.connectors.ozon import OzonConnector
    from leefomgevinglab.geluidsmeter.config import load_config
    cfg = load_config().get("leefomgevinglab", {})
    oz = cfg.get("ozon", {})
    env = oz.get("environment", "prod")
    c = OzonConnector(base_url=oz.get(env, {}).get("base_url", ""),
                      api_key=os.environ.get("DSO_API_KEY_PROD") or os.environ.get("DSO_API_KEY"),
                      api_key_header=oz.get("api_key_header", "x-api-key"),
                      cache_dir=cfg.get("cache_dir", "/tmp/llab_cache"))
    return c.regelingen_op_punt(rd)
