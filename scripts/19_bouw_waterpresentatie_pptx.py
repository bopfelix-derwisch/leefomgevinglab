#!/usr/bin/env python3
"""De presentatie als PowerPoint — uit dezelfde bron als /waterpresentatie.

Waarom een generator en geen met de hand gemaakt bestand. Een pptx dat iemand los onderhoudt
loopt binnen een week uit de pas met de POC, en dan vertelt de spreker een getal dat op de
website al is bijgesteld. `usecases/waterpresentatie.py` blijft de enige bron: dit script leest
dezelfde `DIAS` en zet ze om in dia's, met de spreektekst in de **notitieruimte** zodat
PowerPoint hem in de presentatiemodus toont.

De beeldtypen worden als échte PowerPoint-vormen getekend, niet als plaatje. Een rechthoek blijft
daardoor verplaatsbaar en de tekst doorzoekbaar — wie de dia wil aanpassen kan dat, in plaats van
vast te zitten aan een gerenderde afbeelding.

Zeven beeldtypen, elk met een eigen tekenfunctie. Een onbekend type levert niets op in plaats
van een half beeld: een fout in de data hoort zichtbaar te zijn als lege ruimte.

Draaien:

    PYTHONPATH=src .venv/bin/python scripts/19_bouw_waterpresentatie_pptx.py \\
        --uit /mnt/nvme/geluidsmeter/data/external/waterdossier.pptx
"""
import argparse
import sys
from pathlib import Path

from pptx import Presentation
from pptx.dml.color import RGBColor
from pptx.enum.text import MSO_ANCHOR, PP_ALIGN
from pptx.util import Emu, Pt

from leefomgevinglab.usecases import waterpresentatie as wp

# Dezelfde palet-tokens als de webpagina's, zodat de PowerPoint en de site op elkaar lijken.
KLEUR = {
    "bg": RGBColor(0x08, 0x0C, 0x14), "panel": RGBColor(0x0D, 0x1B, 0x2A),
    "panel2": RGBColor(0x0A, 0x12, 0x20), "border": RGBColor(0x1A, 0x3A, 0x5C),
    "tekst": RGBColor(0xE0, 0xE6, 0xED), "licht": RGBColor(0xEA, 0xFF, 0xF6),
    "muted": RGBColor(0x8A, 0xA0, 0xB2), "dim": RGBColor(0x5B, 0x73, 0x85),
    "accent": RGBColor(0x2E, 0xCC, 0x8F), "kan": RGBColor(0x2E, 0xCC, 0x8F),
    "mag": RGBColor(0xE8, 0xB8, 0x4B), "gebeurt": RGBColor(0x4F, 0xC3, 0xF7),
    "gemeld": RGBColor(0xB3, 0x88, 0xFF), "weg": RGBColor(0xFF, 0x7A, 0x6B),
    "let": RGBColor(0xFF, 0xB7, 0x4D),
}
BREED, HOOG = Emu(12192000), Emu(6858000)          # 16:9
MARGE = Emu(685800)                                 # 0,75 inch
# De tekstblokken hebben een vaste hoogte, zodat een titel die over twee regels loopt of een
# extra kernpunt niet in het beeld zakt. Dat ging twee keer mis: eerst bij vier kernpunten, en
# daarna opnieuw bij vijf. Het blok wordt daarom berekend uit het maximum dat een dia mag
# dragen, en een test dwingt af dat geen dia daaroverheen gaat.
MAX_KERN = 5
KERN_REGEL = Emu(292000)                            # 12,5 pt bij regelafstand 1,3
VOET_TOP = Emu(6050000)

TITEL_TOP, TITEL_HOOG = Emu(880000), Emu(1320000)
KERN_TOP = Emu(2300000)
KERN_HOOG = Emu(MAX_KERN * KERN_REGEL)
BEELD_TOP = Emu(int(KERN_TOP + KERN_HOOG + 60000))
BEELD_HOOG = Emu(int(VOET_TOP - BEELD_TOP - 60000))


def _emu(frac_breedte: float) -> Emu:
    return Emu(int((BREED - 2 * MARGE) * frac_breedte))


def _vlak(dia, x, y, b, h, vul=None, lijn=None, rond=False):
    from pptx.enum.shapes import MSO_SHAPE
    vorm = dia.shapes.add_shape(
        MSO_SHAPE.ROUNDED_RECTANGLE if rond else MSO_SHAPE.RECTANGLE, x, y, b, h)
    vorm.shadow.inherit = False
    if vul is None:
        vorm.fill.background()
    else:
        vorm.fill.solid()
        vorm.fill.fore_color.rgb = vul
    if lijn is None:
        vorm.line.fill.background()
    else:
        vorm.line.color.rgb = lijn
        vorm.line.width = Pt(1)
    vorm.text_frame.word_wrap = True
    return vorm


def _tekst(dia, x, y, b, h, regels, grootte=14, kleur="tekst", vet=False,
           uitlijning=PP_ALIGN.LEFT, anker=MSO_ANCHOR.TOP, regelafstand=1.15):
    doos = dia.shapes.add_textbox(x, y, b, h)
    tf = doos.text_frame
    tf.word_wrap = True
    tf.vertical_anchor = anker
    for i, regel in enumerate(regels if isinstance(regels, list) else [regels]):
        p = tf.paragraphs[0] if i == 0 else tf.add_paragraph()
        p.alignment = uitlijning
        p.line_spacing = regelafstand
        r = p.add_run()
        r.text = regel
        r.font.size = Pt(grootte)
        r.font.bold = vet
        r.font.color.rgb = KLEUR[kleur] if isinstance(kleur, str) else kleur
        r.font.name = "Segoe UI"
    return doos


def _kl(naam) -> RGBColor:
    return KLEUR.get(naam, KLEUR["muted"])


# --- beeldtypen -------------------------------------------------------------------------

def _beeld_lagen(dia, b, links, top, hoog):
    n = len(b["lagen"])
    h = Emu(int(hoog / n) - 60000)
    for i, laag in enumerate(b["lagen"]):
        y = Emu(int(top + i * (hoog / n)))
        _vlak(dia, links, y, _emu(1.0), h, KLEUR["panel2"], KLEUR["border"], rond=True)
        _vlak(dia, links, y, Emu(50000), h, _kl(laag["kleur"]))
        _tekst(dia, Emu(int(links + 160000)), y, _emu(0.22), h, laag["naam"], 15,
               laag["kleur"] if laag["kleur"] in KLEUR else "licht", True, anker=MSO_ANCHOR.MIDDLE)
        _tekst(dia, Emu(int(links + 1700000)), y, _emu(0.7), h, laag["sub"], 12, "muted",
               anker=MSO_ANCHOR.MIDDLE)


def _beeld_balken(dia, b, links, top, hoog):
    n = len(b["balken"])
    rij = hoog / n
    # 0,32 label + 0,42 spoor + 0,22 bijschrift = 0,96; in de eerste versie liep het bijschrift
    # van de dia af omdat spoor en label samen al 0,98 besloegen.
    spoorlinks = Emu(int(links + (BREED - 2 * MARGE) * 0.34))
    spoorbreed = _emu(0.42)
    for i, r in enumerate(b["balken"]):
        y = Emu(int(top + i * rij))
        h = Emu(int(rij * 0.52))
        _tekst(dia, links, y, _emu(0.32), h, r["label"], 11.5, "muted",
               uitlijning=PP_ALIGN.RIGHT, anker=MSO_ANCHOR.MIDDLE)
        _vlak(dia, spoorlinks, y, spoorbreed, h, KLEUR["panel2"], KLEUR["border"])
        deel = max(0.012, min(1.0, (r["waarde"] / r["max"]) if r["max"] else 0))
        _vlak(dia, spoorlinks, y, Emu(int(spoorbreed * deel)), h, _kl(r["kleur"]))
        waarde = f"{r['waarde']:,.0f}".replace(",", ".")
        # Bij een korte balk valt de waarde half buiten de kleur en wordt zij onleesbaar. Dan
        # zetten we hem er rechts náást, op de donkere achtergrond.
        binnen = deel > 0.16
        _tekst(dia, Emu(int(spoorlinks + (90000 if binnen else spoorbreed * deel + 110000))),
               y, _emu(0.2), h, waarde, 11.5, "licht" if binnen else "muted",
               True, anker=MSO_ANCHOR.MIDDLE)
        if r.get("bij"):
            _tekst(dia, Emu(int(spoorlinks + spoorbreed + 130000)), y, _emu(0.22), h,
                   r["bij"], 10, "dim", anker=MSO_ANCHOR.MIDDLE)


def _beeld_drieluik(dia, b, links, top, hoog):
    n = len(b["kolommen"])
    breed = (BREED - 2 * MARGE) / n
    for i, k in enumerate(b["kolommen"]):
        x = Emu(int(links + i * breed))
        w = Emu(int(breed - 140000))
        _vlak(dia, x, top, w, hoog, KLEUR["panel2"], KLEUR["border"], rond=True)
        _vlak(dia, x, top, w, Emu(46000), _kl(k["kleur"]))
        _tekst(dia, Emu(int(x + 200000)), Emu(int(top + 180000)), Emu(int(w - 400000)),
               Emu(400000), k["kop"].upper(), 11, k["kleur"] if k["kleur"] in KLEUR else "accent", True)
        _tekst(dia, Emu(int(x + 200000)), Emu(int(top + 580000)), Emu(int(w - 400000)),
               Emu(760000), k["groot"], 21, "licht", True)
        _tekst(dia, Emu(int(x + 200000)), Emu(int(top + 1330000)), Emu(int(w - 400000)),
               Emu(850000), k["bij"], 11.5, "muted")


def _beeld_stappen(dia, b, links, top, hoog):
    n = len(b["stappen"])
    breed = (BREED - 2 * MARGE) / n
    for i, s in enumerate(b["stappen"]):
        x = Emu(int(links + i * breed))
        w = Emu(int(breed - 140000))
        aan = bool(s.get("actief"))
        _vlak(dia, x, top, w, hoog, KLEUR["panel2"],
              KLEUR["accent"] if aan else KLEUR["border"], rond=True)
        # Breed genoeg voor "EU" en "NL"; met 500000 EMU brak "EU" af over twee regels.
        _tekst(dia, Emu(int(x + 190000)), Emu(int(top + 110000)), Emu(900000), Emu(420000),
               str(s["nr"]), 16, "accent" if aan else "dim", True)
        # Hoe meer kolommen, hoe smaller elk vak en hoe vaker de naam over drie regels loopt.
        # Met een vaste hoogte van twee regels schoof de naam over zijn subtekst heen.
        naam_hoog = 232000 * (3 if n >= 4 else 2)
        _tekst(dia, Emu(int(x + 190000)), Emu(int(top + 560000)), Emu(int(w - 380000)),
               Emu(naam_hoog), s["naam"], 13, "licht", True)
        sub_top = 560000 + naam_hoog
        _tekst(dia, Emu(int(x + 190000)), Emu(int(top + sub_top)), Emu(int(w - 380000)),
               Emu(int(hoog - sub_top - 60000)), s["sub"], 10.5, "muted")


def _beeld_chips(dia, b, links, top, hoog):
    x, y = links, top
    rij_h, max_x = Emu(430000), BREED - MARGE
    for soort, lijst in (("wel", b["wel"]), ("niet", b["niet"])):
        for woord in lijst:
            # Een ondergrens is nodig: met alleen een factor per teken brak "PFOA" af over twee
            # regels, terwijl een lange naam wél paste. Korte woorden hebben verhoudingsgewijs
            # meer binnenmarge nodig dan lange.
            w = Emu(max(840000, int(200000 + len(woord) * 118000)))
            if x + w > max_x:
                x, y = links, Emu(int(y + rij_h + 110000))
            vorm = _vlak(dia, x, y, w, rij_h,
                         KLEUR["panel2"] if soort == "niet" else KLEUR["panel"],
                         KLEUR["border"] if soort == "niet" else KLEUR["accent"], rond=True)
            tf = vorm.text_frame
            p = tf.paragraphs[0]
            p.alignment = PP_ALIGN.CENTER
            r = p.add_run()
            r.text = woord
            r.font.size = Pt(11)
            r.font.name = "Segoe UI"
            r.font.color.rgb = KLEUR["dim"] if soort == "niet" else KLEUR["accent"]
            # Doorhalen zegt hier iets: deze stof komt in geen enkele zuiveringsvergunning voor.
            if soort == "niet":
                r.font._rPr.set("strike", "sngStrike")
            x = Emu(int(x + w + 110000))


def _beeld_rivier(dia, b, links, top, hoog):
    punten = b["punten"]
    rij = hoog / len(punten)
    top_pct = max([p["pct"] for p in punten] + [1])
    spoorlinks = Emu(int(links + (BREED - 2 * MARGE) * 0.26))
    spoorbreed = _emu(0.60)
    for i, p in enumerate(punten):
        y = Emu(int(top + i * rij))
        h = Emu(int(rij * 0.58))
        _tekst(dia, links, y, _emu(0.24), h, p["naam"], 10.5, "muted",
               uitlijning=PP_ALIGN.RIGHT, anker=MSO_ANCHOR.MIDDLE)
        _vlak(dia, spoorlinks, y, spoorbreed, h, KLEUR["panel2"], KLEUR["border"])
        if p["pct"] > 0:
            _vlak(dia, spoorlinks, y, Emu(int(spoorbreed * p["pct"] / top_pct)), h, KLEUR["mag"])
        _tekst(dia, Emu(int(spoorlinks + spoorbreed + 120000)), y, _emu(0.1), h,
               f"{p['pct']:.1f}%".replace(".", ","), 11,
               "licht" if p["pct"] > 0 else "dim", anker=MSO_ANCHOR.MIDDLE)


def _beeld_tijdlijn(dia, b, links, top, hoog):
    n = len(b["items"])
    rij = hoog / n
    for i, x in enumerate(b["items"]):
        y = Emu(int(top + i * rij))
        h = Emu(int(rij * 0.8))
        _vlak(dia, links, y, _emu(1.0), h, KLEUR["panel2"], KLEUR["border"], rond=True)
        _vlak(dia, links, y, Emu(50000), h, KLEUR["accent"])
        _tekst(dia, Emu(int(links + 170000)), y, _emu(0.12), h, x["jaar"], 14, "accent", True,
               anker=MSO_ANCHOR.MIDDLE)
        _tekst(dia, Emu(int(links + 1300000)), y, _emu(0.83), h, x["wat"], 11.5, "muted",
               anker=MSO_ANCHOR.MIDDLE)


def past_in_vak(tekst: str, breedte_emu: int, hoogte_emu: int, punten: float) -> bool:
    """Ruwe schatting of een tekst in zijn vak past.

    Geen letterexacte meting — python-pptx kan niet weten hoe PowerPoint afbreekt — maar genoeg
    om grove overloop te vangen. Dat is nodig gebleken: in deze renderer liep drie keer een
    tekst uit zijn kader, telkens pas zichtbaar na het renderen naar pdf.

    Een teken is bij Segoe UI ongeveer 0,52 × de puntgrootte breed, en een regel ongeveer
    1,22 × de puntgrootte hoog. Eén punt is 12700 EMU.
    """
    tekenbreedte = punten * 0.52 * 12700
    regelhoogte = punten * 1.22 * 12700
    per_regel = max(1, int(breedte_emu / tekenbreedte))
    # +1 per woordafbreking die een regel vroegtijdig beëindigt; ruw benaderd met een marge.
    regels = -(-len(tekst) // per_regel) + 1
    return regels * regelhoogte <= hoogte_emu


BEELDEN = {"lagen": _beeld_lagen, "balken": _beeld_balken, "drieluik": _beeld_drieluik,
           "stappen": _beeld_stappen, "chips": _beeld_chips, "rivier": _beeld_rivier,
           "tijdlijn": _beeld_tijdlijn}


# --- de dia's ----------------------------------------------------------------------------

def _achtergrond(dia):
    vorm = _vlak(dia, Emu(0), Emu(0), BREED, HOOG, KLEUR["bg"])
    # De gekleurde streep onderaan is dezelfde als op de webpagina: vier lagen, vier kleuren.
    strook_b = BREED / 4
    for i, naam in enumerate(("kan", "mag", "gebeurt", "gemeld")):
        _vlak(dia, Emu(int(i * strook_b)), Emu(int(HOOG - 40000)), Emu(int(strook_b)),
              Emu(40000), KLEUR[naam])
    return vorm


def _titeldia(prs, p):
    dia = prs.slides.add_slide(prs.slide_layouts[6])
    _achtergrond(dia)
    _tekst(dia, MARGE, Emu(2100000), _emu(0.92), Emu(1200000), p["titel"], 40, "licht", True)
    _tekst(dia, MARGE, Emu(3500000), _emu(0.78), Emu(900000), p["ondertitel"], 16, "muted")
    _tekst(dia, MARGE, Emu(5300000), _emu(0.9), Emu(500000),
           f"{p['aantal']} dia's · {p['duur_s'] // 60} minuten · "
           f"leefomgevinglab.felixisfelix.com/waterpresentatie", 12, "dim")
    return dia


def _dia(prs, d, totaal):
    dia = prs.slides.add_slide(prs.slide_layouts[6])
    _achtergrond(dia)
    _tekst(dia, MARGE, Emu(520000), _emu(0.9), Emu(330000), d["deel"].upper(), 11, "accent", True)
    _tekst(dia, MARGE, TITEL_TOP, _emu(0.88), TITEL_HOOG, d["titel"], 28, "licht", True)
    _tekst(dia, MARGE, KERN_TOP, _emu(0.94), KERN_HOOG,
           [f"—  {k}" for k in d["kern"]], 12.5, "muted", regelafstand=1.3)

    teken = BEELDEN.get(d["beeld"]["soort"])
    if teken:
        teken(dia, d["beeld"], MARGE, BEELD_TOP, BEELD_HOOG)

    _tekst(dia, MARGE, Emu(6050000), _emu(0.68), Emu(400000),
           f"Bron: {d['bron']}  ·  {d['link']}", 10, "dim")
    _tekst(dia, Emu(int(BREED - MARGE - _emu(0.16))), Emu(6050000), _emu(0.16), Emu(400000),
           f"{d['nr']} / {totaal}", 10, "dim", uitlijning=PP_ALIGN.RIGHT)

    # De spreektekst gaat de notitieruimte in: in de presentatiemodus van PowerPoint staat hij
    # dan op het scherm van de spreker en niet op de beamer.
    notities = dia.notes_slide.notes_text_frame
    notities.text = (f"[{d['seconden']} seconden]\n\n{d['spreektekst']}")
    return dia


def bouw(uit: Path) -> dict:
    p = wp.presentatie()
    prs = Presentation()
    prs.slide_width, prs.slide_height = BREED, HOOG
    _titeldia(prs, p)
    for d in p["dias"]:
        _dia(prs, d, p["aantal"])
    uit.parent.mkdir(parents=True, exist_ok=True)
    prs.save(str(uit))
    return {"dias": len(prs.slides), "duur_s": p["duur_s"], "pad": str(uit),
            "bytes": uit.stat().st_size}


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--uit", required=True, help="pad voor het .pptx-bestand")
    a = ap.parse_args()
    d = bouw(Path(a.uit))
    print(f"{d['dias']} dia's ({d['duur_s'] // 60}:{d['duur_s'] % 60:02d}) -> "
          f"{d['pad']} ({d['bytes'] // 1024} kB)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
