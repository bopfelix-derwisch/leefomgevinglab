"""De vier lagen samen op één kaart van het Maasstroomgebied.

Elke pagina in dit dossier toont één laag goed. Deze legt ze over elkaar op de plek waar ze
horen, en laat zien wat dat oplevert: niet een stapel stippen, maar een kaart die de vraag
beantwoordt die op de eerste dia staat. Klik een meetpunt, en wat bovenstrooms ligt licht op.

**Wat echt is en wat niet.** De geometrie, de meetpunten, de vergunningen en de meldingen komen
alle vier uit hun eigen bron. Wat geharmoniseerd zou moeten zijn maar het niet is, draagt dat
mee: elke koppeling tussen twee lagen krijgt een `grondslag` — op een code, op een heuristiek,
of helemaal niet gelegd. Een kaart die dat verschil wegpoetst ziet er overtuigender uit dan zij
is, en dat is precies wat dit dossier níét wil laten zien.

**Waarom alleen rijkswateren een vorm hebben.** Het district Maas telt 163 waterlichamen, maar
de KRW-service van Rijkswaterstaat publiceert er maar een deel als geometrie — de regionale
waterlichamen zitten bij de waterschappen, elk in een eigen service. Op de kaart staat dus de
hoofdstroom; de regionale wateren zijn er wel, maar niet te tekenen. Dat staat er zo bij in
plaats van stilzwijgend te ontbreken.
"""
import json
from pathlib import Path

from leefomgevinglab.usecases.kmg import service as kmg_service
from leefomgevinglab.usecases.kmg import koppeling as kp_mod
from leefomgevinglab.usecases.kmg import metingen as metingen_mod
from leefomgevinglab.usecases.kmg import toerekening

KAART_PAD = "/mnt/nvme/geluidsmeter/data/external/wkp/maaskaart.json"

# Twee meetlatten die allebei "het doel" worden genoemd en die het niet zijn. Dit onderscheid
# is de meest gestelde vraag bij dit dossier, en het staat nergens in één zin bij elkaar.
MEETLATTEN = {
    "doel per waterlichaam": {
        "kop": "KRW-doel \u2014 vastgesteld v\u00f3\u00f3r dit waterlichaam",
        "wat": ("De waterbeheerder stelt per waterlichaam doelen vast voor de ecologische en "
                "fysisch-chemische toestand: stikstof, fosfor, zuurstof, zuurgraad, chloride en "
                "de biologie. Ze staan in het waterprogramma en verschillen per watertype \u2014 "
                "een laaglandbeek krijgt een ander stikstofdoel dan een grote rivier."),
        "let_op": ("Het is géén grenswaarde waar iemand op kan handhaven. Het is een doel "
                   "dat in 2027 gehaald moet zijn, en de toets is een klasse (goed, matig, "
                   "ontoereikend) op een zomergemiddelde."),
        "waar": "KRW-doelen, Waterkwaliteitsportaal \u00b7 per waterlichaam",
    },
    "chemische norm": {
        "kop": "Omgevingswaarde \u2014 landelijk, voor \u00e1lle oppervlaktewater",
        "wat": ("Voor 122 chemische stoffen geldt een landelijke norm: 45 prioritaire stoffen die "
                "Europa aanwijst en 77 die Nederland zelf aanwees. Die staan in bijlage III en "
                "IIIa van het Besluit kwaliteit leefomgeving en zijn niet per waterlichaam "
                "vastgesteld."),
        "let_op": ("De norm is wel pér meetpunt gecorrigeerd voor biobeschikbaarheid \u2014 "
                   "bij zink verschilt de getoetste waarde daardoor per punt \u2014 en geldt voor "
                   "een bépaalde fractie: voor zink de opgeloste, niet de totale."),
        "waar": "KRW-toetsresultaten \u00b7 per meetpunt, grondslag jaargemiddelde",
    },
}

# Hoe een koppeling tussen twee lagen tot stand komt. Dit is de kern van wat de kaart laat zien:
# dezelfde vier lagen, maar met zichtbaar waar de verbinding op rust.
GRONDSLAG = {
    "code": "op een gedeelde code — zo hoort het",
    "ruimtelijk": "op een coördinaat — betrouwbaar, maar zegt niets over identiteit",
    "heuristiek": "op naam plus afstand — een gok die meestal klopt",
    "geen": "niet gelegd — de gegevens bestaan, de verbinding niet",
}


def laad_kaart(pad: str | None = None) -> dict:
    p = Path(pad or KAART_PAD)
    if not p.exists():
        return {"beschikbaar": False,
                "reden": f"kaartbestand ontbreekt ({p}); draai scripts/20_bouw_maaskaart.py"}
    return {"beschikbaar": True, **json.loads(p.read_text())}


def _rd(post: dict):
    return kmg_service._vergunning_coordinaat(post)


def _is_zuivering(naam: str, locatiecode: str | None) -> bool:
    """Een rioolwaterzuivering herkennen aan haar naam of locatiecode.

    Bewust ruim: deze posten zijn op de kaart een eigen soort, want achter zo'n punt zit een
    hele lozingsroute die nergens geregistreerd staat.
    """
    n = (naam or "").upper()
    lc = (locatiecode or "").upper()
    return (lc.startswith("RWZI") or lc == "AWZWAALW"
            or "RWZI" in n or "WATERSCHAPSBEDRIJF" in n or "ZUIVER" in n)


def meetpunten(overzicht_pad: str, metingen_pad: str) -> list[dict]:
    """De meetpunten met hun uitkomst, uit de voorberekende momentopname.

    De coördinaat komt uit de meetset en niet uit het overzicht: het overzicht draagt de
    uitkomsten, de meetset de plek.
    """
    p = Path(overzicht_pad)
    if not p.exists():
        return []
    set_ = metingen_mod.laad(metingen_pad)
    rd_van = {q["code"]: q.get("rd") for q in (set_.get("punten") or [])}
    uit = []
    for b in (json.loads(p.read_text()).get("punten") or []):
        stoffen = [s for s in (b.get("stoffen") or []) if s.get("aandeel_pct") is not None]
        top = max((s["aandeel_pct"] for s in stoffen), default=None)
        uit.append({
            "code": b["code"], "naam": b.get("naam"),
            "rd": rd_van.get(b["code"]),
            "waterlichaam": b.get("waterlichaam"),
            "waterlichaam_naam": b.get("waterlichaam_naam"),
            "register": b.get("register"),
            "aandeel_max_pct": top,
            "stoffen": [_stof(s, b.get("waterlichaam")) for s in (b.get("stoffen") or [])],
            # Hoe het meetpunt aan zijn waterlichaam komt: uit het meetobjectenbestand, dus
            # op een code. Dit is de enige koppeling in dit hele dossier die zo gelegd is.
            "grondslag": "code",
        })
    return uit


# µg/l en mg/l naar kg per jaar, bij een debiet in m³/s. Dezelfde eenheidsval als elders in dit
# dossier: wie hier mg/l aanneemt zit bij zink een factor duizend mis.
_PER_KG = {"mg/l": 1_000.0, "ug/l": 1_000_000.0, "\u00b5g/l": 1_000_000.0}


def _ruimte_kg_jaar(ruimte: float | None, eenheid: str | None,
                    waterlichaam: str | None) -> float | None:
    """De ruimte tot het doel, van een concentratie naar een vracht per jaar.

    Levert `None` bij een onbekende eenheid in plaats van mg/l aan te nemen: een stille aanname
    is hier een factor duizend waard. En bij een negatieve ruimte blijft het getal negatief —
    dat is geen hoeveelheid die erbij kan maar een tekort, en dat hoort zichtbaar te blijven.
    """
    if ruimte is None or not eenheid:
        return None
    deler = _PER_KG.get(eenheid.strip())
    if deler is None:
        return None
    debiet = kmg_service.DEBIET_M3_S.get(waterlichaam or "", kmg_service.STANDAARD_DEBIET)
    return round(ruimte * debiet * toerekening.SECONDEN_PER_JAAR / deler)


def _stof(s: dict, waterlichaam: str | None) -> dict:
    """Eén gemeten stof, met haar meetlat en de ruimte die er nog is."""
    ruimte = s.get("ruimte")
    return {
        "code": s.get("code"), "naam": s.get("naam"),
        "hoedanigheid_naam": s.get("hoedanigheid_naam"),
        "gemeten": s.get("gemeten"), "eenheid": s.get("eenheid"),
        "aandeel_pct": s.get("aandeel_pct"), "posten": s.get("posten"),
        "klasse": s.get("klasse"),
        "doel_waarde": s.get("doel_waarde"),
        "doel_soort": s.get("doel_soort"),
        "doel_grondslag": s.get("doel_grondslag"),
        "doel_element": s.get("doel_element"),
        "ruimte": ruimte,
        "ruimte_kg_jaar": _ruimte_kg_jaar(ruimte, s.get("eenheid"), waterlichaam),
        "meetlat": MEETLATTEN.get(s.get("doel_soort") or ""),
    }


def _haal_atlas(x: float, y: float, straal_m: int):
    return kmg_service._atlas_standaard(x, y, straal_m)


def lagen(kaart: dict, overzicht_pad: str, metingen_pad: str,
          straal_m: int = 250000, live: bool = True,
          _atlas=None, _meldingen=None) -> dict:
    """De vier lagen op hun plek, elk met de grondslag van zijn koppeling."""
    punten = meetpunten(overzicht_pad, metingen_pad)
    midden = (170000.0, 390000.0)

    vergunningen, zuiveringen, fout = [], [], None
    if live:
        try:
            posten = (_atlas or _haal_atlas)(*midden, straal_m)
            for i, post in enumerate(posten):
                rd = _rd(post)
                rij = {
                    "kenmerk": post.get("kenmerk"),
                    "naam": post.get("naam"), "plaats": post.get("plaats"),
                    "kvk": post.get("vestigingsnummer_kvk"),
                    "rd": list(rd) if rd else None,
                    "voorschriften": len(post.get("voorschriften") or []),
                    # De vergunning komt op de kaart via haar coördinaat. Dat is betrouwbaar
                    # voor een plek, maar zegt niets over wélk bedrijf het is.
                    "grondslag": "ruimtelijk" if rd else "geen",
                }
                (zuiveringen if _is_zuivering(post.get("naam"), post.get("locatiecode"))
                 else vergunningen).append(rij)
        except Exception as exc:                     # noqa: BLE001 — bron mag wegvallen
            fout = type(exc).__name__

    meldingen = []
    if live and _meldingen is not None:
        for m in _meldingen():
            meldingen.append({**m, "grondslag": "heuristiek"})

    return {
        "meetpunten": punten,
        "vergunningen": vergunningen, "zuiveringen": zuiveringen,
        "meldingen": meldingen,
        "atlas_fout": fout,
        "grondslagen": GRONDSLAG,
    }


def bovenstrooms_van(code: str) -> list[str]:
    """De waterlichamen die bovenstrooms van dit waterlichaam liggen, zichzelf meegerekend.

    De kaart gebruikt dit om bij een klik op te lichten wat kan bijdragen. Het is dezelfde
    ordening als `toerekening.is_bovenstrooms` — en daarmee dezelfde labkeuze, geen brongegeven.
    """
    return [c for c, _n in toerekening.STROOMVOLGORDE
            if toerekening.is_bovenstrooms(c, code)]


def beeld(kaart_pad: str | None = None, overzicht_pad: str = "", metingen_pad: str = "",
          straal_m: int = 250000, live: bool = True, _atlas=None, _meldingen=None) -> dict:
    kaart = laad_kaart(kaart_pad)
    if not kaart.get("beschikbaar"):
        return {"beschikbaar": False, "reden": kaart.get("reden")}
    d = lagen(kaart, overzicht_pad, metingen_pad, straal_m, live,
              _atlas=_atlas, _meldingen=_meldingen)
    bovenstrooms = {c: bovenstrooms_van(c) for c, _n in toerekening.STROOMVOLGORDE}
    return {
        "beschikbaar": True,
        "kaart": {k: kaart[k] for k in
                  ("bron", "district", "tolerantie_m", "bbox", "vlakken", "lijnen",
                   "stroomvolgorde", "zonder_positie", "telling")},
        **d,
        "bovenstrooms": bovenstrooms,
        "meetlatten": MEETLATTEN,
        "debiet_m3_s": kmg_service.DEBIET_M3_S,
        # Wat deze kaart over zichzelf moet zeggen, uit de data in plaats van uit een vaste zin.
        "voorbehoud": {
            "geometrie": (f"Het district telt {kaart['telling']['in_district']} waterlichamen; "
                          f"hiervan publiceert de KRW-service er "
                          f"{kaart['telling']['vlakken'] + kaart['telling']['lijnen']} als "
                          "geometrie. De regionale wateren zitten bij de waterschappen, elk in "
                          "een eigen service, en staan hier dus niet op."),
            "vereenvoudigd": (f"De omtrek is vereenvoudigd tot {kaart['tolerantie_m']:.0f} meter "
                              "om de kaart in een browser te kunnen tekenen."),
            "stroomvolgorde": ("Welk waterlichaam bovenstrooms van welk ligt, is een keuze van "
                               "dit lab; de bron kent geen ordening tussen waterlichamen."),
            "koppelingen": ("Elke stip draagt de grondslag van haar koppeling. Alleen de "
                            "meetpunten hangen op een gedeelde code aan hun waterlichaam."),
        },
    }
