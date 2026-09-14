"""Het beeld op een locatie: contouren, wat eronder valt, wat er al ligt, en wat dat betekent."""
from concurrent.futures import ThreadPoolExecutor

from pyproj import Transformer

from leefomgevinglab.usecases import begrippen as begrippen_mod
from leefomgevinglab.usecases.gebruiksruimte import regels as regels_mod

from . import bronnen, gebied, oordeel

_NAAR_WGS = Transformer.from_crs("EPSG:28992", "EPSG:4326", always_xy=True)

# Wat de regelingtypes betekenen voor een Seveso-voornemen (tegenhanger van de lozingsduiding).
DUIDING_EV = {
    "AMvB": ("Rijksregels. Het exploiteren van een Seveso-inrichting is één vergunningplichtige "
             "milieubelastende activiteit; het Bkl bepaalt hoe aandachtsgebieden doorwerken naar "
             "wat er in de omgeving mag staan.", True),
    "Omgevingsplan": ("Bepaalt wat hier mag komen — en, andersom, wat er ín het aandachtsgebied "
                      "aan gevoelige functies mag worden toegelaten. Dit is het instrument waarmee "
                      "de gemeente de ruimte om de inrichting heen vastlegt.", True),
    "Omgevingsverordening": ("Provinciale regels op deze locatie. De provincie is bevoegd gezag "
                             "voor de Seveso-inrichting zelf.", True),
    "Waterschapsverordening": ("Geldt op deze locatie, maar raakt dit voornemen niet: het gaat om "
                               "externe veiligheid, niet om een lozing.", False),
    "Voorbeschermingsregels": ("Tijdelijke bescherming vooruitlopend op een wijziging; kan een "
                               "aanvraag blokkeren zolang die loopt.", True),
    "Voorbeschermingsregels Omgevingsplan": ("Tijdelijke bescherming vooruitlopend op een wijziging "
                                             "van het omgevingsplan.", True),
    "Omgevingsvisie": ("Beleid. Bepaalt of dit gebied überhaupt bedoeld is voor risicovolle "
                       "bedrijvigheid.", True),
    "Programma": ("Beleidsprogramma; bindt het bestuursorgaan en kleurt de afweging.", True),
    "Aanwijzingsbesluit N2000": ("Natura 2000. Een Seveso-inrichting raakt dit vooral via depositie "
                                 "en via de gevolgen van een incident.", True),
}


def wgs84(x: float, y: float) -> list:
    lon, lat = _NAAR_WGS.transform(x, y)
    return [round(lon, 6), round(lat, 6)]


def beeld(locatie_id: str, live: bool = True, _post=None, _get=None, _haal_regels=None) -> dict:
    loc = gebied.LOCATIES[locatie_id]              # KeyError bij onbekende locatie
    x, y = loc["rd"]
    groot = gebied.grootste_straal()

    tellingen, bestaand, lagen, bronstatus = {}, {}, {}, []

    def _noteer(bron, wat, waarde, fout=None):
        bronstatus.append({"bron": bron, "wat": wat,
                           "status": "overgeslagen" if not live else ("onbereikbaar" if fout else "ok"),
                           "aantal": waarde, **({"fout": fout} if fout else {})})

    # Elke contour × klasse × gebruiksdoel is een losse bevraging; sequentieel duurt dat ruim
    # tien seconden. Ze zijn onafhankelijk, dus parallel — netjes begrensd zodat we PDOK niet
    # overvragen.
    opdrachten = [(c["soort"], c["straal_m"], klasse, doel)
                  for c in gebied.CONTOUREN
                  for klasse, doelen in gebied.KWETSBAARHEID.items()
                  for doel in doelen] if live else []

    def _tel(op):
        soort, straal, klasse, doel = op
        try:
            return op, bronnen.tel_verblijfsobjecten(x, y, straal, doel, _post=_post), None
        except Exception as exc:
            return op, None, type(exc).__name__

    ruw = {}
    if opdrachten:
        with ThreadPoolExecutor(max_workers=8) as pool:
            for op, n, fout in pool.map(_tel, opdrachten):
                ruw[op] = (n, fout)

    for c in gebied.CONTOUREN:
        per_klasse, storing = {}, None
        for klasse, doelen in gebied.KWETSBAARHEID.items():
            if not live:
                per_klasse[klasse] = None
                continue
            totaal = 0
            for doel in doelen:
                n, fout = ruw.get((c["soort"], c["straal_m"], klasse, doel), (None, "ontbreekt"))
                if fout:
                    storing, totaal = fout, None
                    break
                totaal += n or 0
            per_klasse[klasse] = totaal
        tellingen[c["soort"]] = per_klasse
        _noteer("BAG (PDOK)", f"kwetsbaarheid binnen {c['straal_m']} m",
                sum(v for v in per_klasse.values() if v) if live and not storing else None,
                storing)

    for laag, oms in bronnen.REV_LAGEN:
        if not live:
            bestaand[oms] = None
            _noteer("REV-WFS", oms, None)
            continue
        try:
            bestaand[oms] = bronnen.tel_rev(x, y, groot, laag, _get=_get)
            _noteer("REV-WFS", oms, bestaand[oms])
        except Exception as exc:
            bestaand[oms] = None
            _noteer("REV-WFS", oms, None, type(exc).__name__)

    if live:
        for soort, laag in bronnen.REV_AANDACHTSGEBIEDEN.items():
            try:
                lagen[soort] = bronnen.rev_geojson(x, y, groot, laag, _get=_get)
            except Exception:
                lagen[soort] = {"type": "FeatureCollection", "features": []}

    bg = {"gemeente": loc["gemeente"], "provincie": None}
    if live:
        try:
            bg = bronnen.gemeente_op_punt(x, y, _get=_get)
        except Exception:
            pass

    r = regels_mod.regels_op_locatie(x, y, rijkswater=True, live=live,
                                     _haal=_haal_regels, tabel=DUIDING_EV)

    return {
        "locatie": {**loc, "rd": list(loc["rd"]), "wgs84": wgs84(x, y)},
        "gemeente": bg, "voornemen": gebied.VOORNEMEN,
        "contouren": gebied.CONTOUREN, "kwetsbaarheid": gebied.KWETSBAARHEID,
        "klasse_uitleg": gebied.KLASSE_UITLEG,
        # De indeling hierboven is ónze afleiding uit het BAG-gebruiksdoel; de catalogus heeft de
        # juridische definitie. Dat verschil hoort op de pagina te staan, niet in een voetnoot.
        "kloof": begrippen_mod.KLOOF,
        "tellingen": tellingen, "bestaand": bestaand, "lagen": lagen,
        "bronnen": bronstatus, "regels": r,
        "oordeel": oordeel.beoordeel(tellingen, bestaand),
        "locaties": [{**l, "rd": list(l["rd"]), "wgs84": wgs84(*l["rd"])}
                     for l in gebied.LOCATIES.values()],
        "live": live,
        "verantwoording": "Tellingen live uit de BAG (verblijfsobjecten binnen de contour, per "
                          "gebruiksdoel) en het REV. De kwetsbaarheidsindeling is afgeleid van het "
                          "BAG-gebruiksdoel en daarmee indicatief: het Bkl kijkt ook naar de "
                          "feitelijke aanwezigheid van personen. De contourafstanden komen uit een "
                          "indicatieve tabel, niet uit een QRA.",
    }
