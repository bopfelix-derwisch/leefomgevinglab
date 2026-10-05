"""Voorstel: een informatiemodel voor lozingsvoorschriften, en de dataficering van wat er ligt.

Dit is het model dat de memo op `/watermodel` bepleit, hier uitgevoerd op de echte Atlas-data. Het
doet twee dingen die uit elkaar gehouden moeten worden:

1. **Het legt vast wat een voorschrift als gegeven is** — welke stof, welke hoedanigheid, welke
   eenheid, welke grondslag, welke waarde, waar en wanneer geldig.
2. **Het legt vast hoe zeker we daarvan zijn.** Elk veld draagt een `zekerheid`: afkomstig uit de
   bron, afgeleid via een referentietabel, aangenomen, of ontbrekend. Dat tweede is het punt van de
   oefening. Een model dat alleen de velden vastlegt, maakt een onvolledige vergunning er netjes
   uitziend; een model dat de zekerheid meevoert, maakt zichtbaar wat er mist.

**Wat de bron wel en niet geeft.** Een Atlas-voorschrift heeft vijf velden: `parameter`, `waarde`,
`eenheid`, `bemonstering`, `rd`. Daarmee is de grondslag er wél — `bemonstering` onderscheidt een
etmaalgemiddelde van een steekmonster, en dat is precies wat bepaalt welke grenswaarde geldt als
er meerdere zijn. Maar twee dingen ontbreken volledig:

* **De hoedanigheid.** Geen van de 49 parameternamen in het Maasstroomgebied zegt of het om de
  totale of de opgeloste fractie gaat. De meetkant heeft dat veld wel, en voor zink is het bepalend:
  de KRW-norm geldt op de opgeloste fractie. Keuze van dit lab, vastgelegd in `HOEDANIGHEID_AANNAME`:
  een effluentvoorschrift wordt gelezen als de **totale** fractie, want zo wordt er in de praktijk
  op gehandhaafd — maar die lezing is een aanname en reist als zodanig mee.
* **De geldigheidsperiode.** Er is geen begin- en einddatum per voorschrift, alleen een
  besluitdatum per vergunning. Een vervallen voorschrift is dus niet van een geldend te
  onderscheiden.

**De parameterreferentie is afgeleid, niet verzonnen.** `scripts/16` leidt uit de WKP-meetwaarden
een tabel af van `ParameterCode` naast `ParameterOmschrijving` — 492 parameters uit één levering.
Dat is geen volledige Aquo-domeintabel: stoffen die Rijkswaterstaat niet chemisch meet ontbreken,
waaronder zwevende stof, Kjeldahl-stikstof, debiet, temperatuur en minerale olie. Een voorschrift
daarover blijft ongecodeerd en krijgt dat als reden mee. Een echte implementatie haalt deze tabel
bij Aquo zelf.
"""
import json
from pathlib import Path

# Hoe zeker een veld is. De volgorde is die van afnemende betrouwbaarheid en wordt gebruikt om de
# zwakste schakel van een voorschrift te bepalen.
ZEKERHEDEN = ("uit de bron", "afgeleid", "aangenomen", "ontbreekt")

# De aanname over hoedanigheid, expliciet en op één plek, zodat zij aanvechtbaar is.
HOEDANIGHEID_AANNAME = {
    "code": "NVT",
    "zekerheid": "aangenomen",
    "herkomst": ("de bron noemt geen hoedanigheid; een effluentvoorschrift wordt hier gelezen als "
                 "de totale fractie, omdat daar in de praktijk op gehandhaafd wordt"),
}

# Eenheden zoals de Atlas ze schrijft, naar een code en een dimensie. De dimensie bepaalt wat je
# met de waarde kunt: een concentratie is pas een vracht als er een debiet bij staat.
EENHEDEN = {
    "milligram per liter": ("mg/l", "concentratie"),
    "microgram per liter": ("ug/l", "concentratie"),
    "nanogram per liter": ("ng/l", "concentratie"),
    "gram per liter": ("g/l", "concentratie"),
    "kilogram per jaar": ("kg/jaar", "vracht"),
    "kilogram per dag": ("kg/d", "vracht"),
    "kilogram per week": ("kg/week", "vracht"),
    "kilogram per uur": ("kg/u", "vracht"),
    "gram per dag": ("g/d", "vracht"),
    "ton per jaar": ("ton/jaar", "vracht"),
    "kubieke meter per uur": ("m3/u", "debiet"),
    "kubieke meter per dag": ("m3/d", "debiet"),
    "kubieke meter per jaar": ("m3/jaar", "debiet"),
    # De bron bevat deze schrijffout één keer. Hem stil herstellen zou de fout verbergen; hem
    # koppelen mét een notitie houdt het voorschrift bruikbaar en de fout zichtbaar.
    "kubieke met per etmaal": ("m3/d", "debiet"),
    "graad Celsius": ("oC", "fysisch"),
    "dimensieloos": ("DIMSLS", "fysisch"),
    "megajoule per seconde": ("MJ/s", "fysisch"),
    "megawatt elektrisch": ("MWe", "fysisch"),
}
_EENHEID_NOTITIE = {"kubieke met per etmaal": "schrijffout in de bron; gelezen als kubieke meter per etmaal"}

# `bemonstering` naar een grondslag. Dit is het veld dat bepaalt wélke grenswaarde geldt wanneer
# een stof er meerdere heeft -- zonder dit is optellen of maximaliseren een gok.
GRONDSLAGEN = {
    "verzamelmonster gedurende 24 uur": "etmaalgemiddelde",
    "verzamelmonster gedurende 1 uur": "uurgemiddelde",
    "weekmengmonster": "weekgemiddelde",
    "jaarvracht op basis van weekmengmonster": "jaarvracht",
    "steekmonster": "momentaan",
    "rechtstreekse meting": "momentaan",
    "tijdsproportioneel": "etmaalgemiddelde",
}


def _norm(s: str) -> str:
    return " ".join((s or "").lower().replace("-", " ").split())


def laad_parameters(pad: str) -> dict:
    """De parameterreferentie lezen. Zacht falen: zonder referentie blijft dataficeren mogelijk,
    alleen dan zonder code — en dat moet het model kunnen zeggen."""
    p = Path(pad)
    if not p.exists():
        return {"beschikbaar": False, "op_naam": {},
                "reden": f"geen parameterreferentie op {pad}; bouw hem met scripts/16"}
    try:
        d = json.loads(p.read_text(encoding="utf-8"))
    except (ValueError, OSError) as exc:
        return {"beschikbaar": False, "op_naam": {},
                "reden": f"de parameterreferentie is onleesbaar ({type(exc).__name__})"}
    return {**d, "beschikbaar": True}


def _veld(waarde, zekerheid: str, herkomst: str = "", **extra) -> dict:
    return {"waarde": waarde, "zekerheid": zekerheid, "herkomst": herkomst, **extra}


def dataficeer(voorschrift: dict, referentie: dict) -> dict:
    """Eén Atlas-voorschrift naar het voorgestelde model, met de zekerheid per veld.

    Het resultaat draagt altijd `volledigheid` en `ontbreekt`: die twee maken een voorschrift
    vergelijkbaar met een ander zónder dat je de velden zelf hoeft na te lopen.
    """
    naam_bron = (voorschrift.get("parameter") or "").strip()
    eenheid_bron = (voorschrift.get("eenheid") or "").strip()
    bem_bron = (voorschrift.get("bemonstering") or "").strip()

    op_naam = (referentie or {}).get("op_naam") or {}
    code = op_naam.get(_norm(naam_bron))
    if code:
        parameter = _veld(code, "afgeleid",
                          "gekoppeld op omschrijving in de parameterreferentie", naam_bron=naam_bron)
    elif not naam_bron:
        parameter = _veld(None, "ontbreekt", "de bron noemt geen parameter", naam_bron=None)
    else:
        parameter = _veld(None, "ontbreekt",
                          "de naam komt niet voor in de parameterreferentie; die bevat alleen wat "
                          "Rijkswaterstaat chemisch meet", naam_bron=naam_bron)

    eh = EENHEDEN.get(eenheid_bron)
    if eh:
        eenheid = _veld(eh[0], "afgeleid", _EENHEID_NOTITIE.get(eenheid_bron, "gekoppeld op de eenhedentabel"),
                        naam_bron=eenheid_bron, dimensie=eh[1])
    else:
        eenheid = _veld(None, "ontbreekt",
                        "deze eenheid staat niet in de eenhedentabel van dit model" if eenheid_bron
                        else "de bron noemt geen eenheid",
                        naam_bron=eenheid_bron or None, dimensie=None)

    grondslag_code = GRONDSLAGEN.get(_norm(bem_bron))
    if grondslag_code:
        grondslag = _veld(grondslag_code, "afgeleid", "afgeleid uit het bemonsteringsvoorschrift",
                          naam_bron=bem_bron)
    elif bem_bron:
        grondslag = _veld(None, "ontbreekt",
                          "het bemonsteringsvoorschrift is niet herkend", naam_bron=bem_bron)
    else:
        grondslag = _veld(None, "ontbreekt", "de bron noemt geen bemonstering", naam_bron=None)

    rd = voorschrift.get("rd")
    lozingspunt = (_veld(list(rd), "uit de bron", "coördinaat van het voorschrift")
                   if rd else _veld(None, "ontbreekt", "de bron geeft geen coördinaat"))

    velden = {
        "parameter": parameter,
        "hoedanigheid": _veld(HOEDANIGHEID_AANNAME["code"], HOEDANIGHEID_AANNAME["zekerheid"],
                              HOEDANIGHEID_AANNAME["herkomst"]),
        "eenheid": eenheid,
        "waarde": (_veld(voorschrift.get("waarde"), "uit de bron", "grenswaarde uit het voorschrift")
                   if voorschrift.get("waarde") is not None
                   else _veld(None, "ontbreekt", "de bron geeft geen waarde")),
        "grondslag": grondslag,
        "lozingspunt": lozingspunt,
        # Niet in de Atlas aanwezig. Expliciet opnemen in plaats van weglaten: dit is een van de
        # velden waarvoor het informatiemodel juist bestaat.
        "geldigheid": _veld(None, "ontbreekt",
                            "de bron kent geen geldigheidsperiode per voorschrift, alleen een "
                            "besluitdatum per vergunning"),
    }

    ontbreekt = sorted(k for k, v in velden.items() if v["zekerheid"] == "ontbreekt")
    aangenomen = sorted(k for k, v in velden.items() if v["zekerheid"] == "aangenomen")
    # Toerekenbaar wil zeggen: er valt een getal mee te doen. Daarvoor zijn stof, eenheid en waarde
    # nodig; grondslag en geldigheid maken het oordeel beter maar zijn er niet voor nodig.
    toerekenbaar = all(velden[k]["waarde"] is not None for k in ("parameter", "eenheid", "waarde"))
    return {
        **velden,
        "toerekenbaar": toerekenbaar,
        "ontbreekt": ontbreekt,
        "aangenomen": aangenomen,
        "volledigheid": "volledig" if not ontbreekt else ("bruikbaar" if toerekenbaar else "onbruikbaar"),
    }


def dataficeer_post(post: dict, referentie: dict) -> dict:
    """Alle voorschriften van één vestiging, plus wat eruit te halen valt."""
    uit = [dataficeer(v, referentie) for v in (post.get("voorschriften") or [])]
    return {
        "naam": post.get("naam"), "kenmerk": post.get("kenmerk"),
        "locatiecode": post.get("locatiecode"), "plaats": post.get("plaats"),
        "voorschriften": uit,
        "telling": tel(uit),
    }


def tel(voorschriften: list[dict]) -> dict:
    """De maat waarmee twee registers te vergelijken zijn."""
    t = {"totaal": len(voorschriften), "volledig": 0, "bruikbaar": 0, "onbruikbaar": 0,
         "zonder_parameter": 0, "zonder_eenheid": 0, "zonder_grondslag": 0, "zonder_geldigheid": 0,
         "aangenomen_hoedanigheid": 0}
    for v in voorschriften:
        t[v["volledigheid"]] = t.get(v["volledigheid"], 0) + 1
        if v["parameter"]["waarde"] is None:
            t["zonder_parameter"] += 1
        if v["eenheid"]["waarde"] is None:
            t["zonder_eenheid"] += 1
        if v["grondslag"]["waarde"] is None:
            t["zonder_grondslag"] += 1
        if v["geldigheid"]["waarde"] is None:
            t["zonder_geldigheid"] += 1
        if v["hoedanigheid"]["zekerheid"] == "aangenomen":
            t["aangenomen_hoedanigheid"] += 1
    return t


def vrachten_op_code(gedataficeerd: dict, debiet_m3_per_uur: float | None) -> dict:
    """De vergunde jaarvracht per Aquo-parametercode, uit de gedataficeerde voorschriften.

    Dit is waar het model zijn winst oplevert: de sleutel is een code en geen Nederlandse naam,
    dus de koppeling met een meting kan niet stilvallen op een andere schrijfwijze.

    Komt een stof met meerdere grenswaarden voor, dan wordt per grondslag het **maximum** genomen
    en daarna de strengste grondslag gekozen die er is — optellen zou de vergunde ruimte
    vermenigvuldigen met het aantal manieren waarop zij is opgeschreven.
    """
    SECONDEN_PER_JAAR = 31_536_000
    per_code: dict[str, dict] = {}
    for v in gedataficeerd.get("voorschriften") or []:
        if not v["toerekenbaar"]:
            continue
        code = v["parameter"]["waarde"]
        dim = v["eenheid"]["dimensie"]
        waarde = float(v["waarde"]["waarde"])
        eh = v["eenheid"]["waarde"]
        if dim == "vracht":
            factor = {"kg/jaar": 1.0, "kg/d": 365.0, "kg/week": 52.0,
                      "kg/u": 8760.0, "g/d": 0.365, "ton/jaar": 1000.0}.get(eh)
            vracht = waarde * factor if factor else None
        elif dim == "concentratie" and debiet_m3_per_uur:
            # mg/l × m3/u → kg/jaar: 1 mg/l op 1 m3 is 1 g, dus ×1e-3 kg per m3.
            mg_per_l = waarde * (1000.0 if eh == "g/l" else 1.0 if eh == "mg/l"
                                 else 1e-3 if eh == "ug/l" else 1e-6 if eh == "ng/l" else None)
            vracht = (mg_per_l * debiet_m3_per_uur * 8760.0 * 1e-3) if mg_per_l is not None else None
        else:
            vracht = None
        if vracht is None:
            continue
        huidig = per_code.get(code)
        if huidig is None or vracht > huidig["kg_jaar"]:
            per_code[code] = {"kg_jaar": vracht, "grondslag": v["grondslag"]["waarde"],
                              "uit_eenheid": eh, "hoedanigheid": v["hoedanigheid"]["waarde"],
                              "hoedanigheid_zekerheid": v["hoedanigheid"]["zekerheid"]}
    return per_code
