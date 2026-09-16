"""Van een KRW-feature naar een waterlichaamprofiel — met echt en verzonnen strikt gescheiden.

De vaste IJssel in `gebied.py` volstaat voor drie locaties. Wie op een willekeurig punt wil
prikken heeft voor elk rijkswater een profiel nodig. De identiteit van het water komt uit de
KRW-service van RWS en is echt: naam, id, beheerder, watertype, categorie, status, omvang,
gemiddelde diepte.

Het debiet, de normen en de achtergrondconcentraties zitten niet in die service en worden hier
afgeleid uit de categorie en de omvang. Die getallen zijn illustratief — het mechanisme is echt,
de cijfers niet. Elk afgeleid veld draagt daarom een herkomstregel, zodat de pagina kan tonen
waar een getal vandaan komt in plaats van het te laten doorgaan voor meting.

Vindt iemand ooit een echte bron voor achtergrondconcentraties per waterlichaam (het
Waterkwaliteitsportaal is de kandidaat), dan vervalt het hele `afgeleid`-blok en blijft de
rest staan.
"""

import math

# Basisprofielen per KRW-categorie: 1 rivier, 2 meer, 3 kust, 4 overgangswater.
# `norm_factor` schaalt de norm zelf per watertypegroep (KRW-doelen verschillen per watertype);
# `factor` schaalt daarna de achtergrondconcentratie ten opzichte van díe norm. Beide zijn van
# dezelfde orde als de KRW-doelen maar door dit lab gekozen, niet uit het Bkl overgenomen. De
# verhoudingen tussen de categorieën dragen het verhaal, niet de absolute waarden — met dien
# verstande dat `factor` bewust zo gekozen is dat in élke categorie, inclusief de terugval,
# minstens twee van de vier parameters onder hun norm blijven en PFOA er nooit een heeft (zie
# `_PARAMETERS` hieronder). Met de oorspronkelijke kust- en overgangsfactor (1.60 en 1.30) klapte
# dat spectrum in: nog maar 1 van 4 hield ruimte.
_CATEGORIEEN = {
    "1": {"naam": "rivier", "debiet_basis_m3_s": 300.0, "norm_factor": 1.00, "factor": 1.00},
    "2": {"naam": "meer", "debiet_basis_m3_s": 40.0, "norm_factor": 0.90, "factor": 0.85},
    "3": {"naam": "kustwater", "debiet_basis_m3_s": 1500.0, "norm_factor": 1.25, "factor": 0.95},
    "4": {"naam": "overgangswater", "debiet_basis_m3_s": 800.0, "norm_factor": 1.10, "factor": 1.05},
}
_TERUGVAL = {"naam": "onbekend type", "debiet_basis_m3_s": 150.0, "norm_factor": 1.00, "factor": 1.00}

# Vier parameters, gekozen omdat ze samen het spectrum laten zien: een nutriënt die dicht tegen
# de norm aan zit, een metaal, een somparameter met ruim wat lucht, en een ZZS waarvoor nooit
# ruimte is. Welke van de eerste drie in een gegeven categorie daadwerkelijk onder de norm blijft,
# verschilt (de categoriefactor schuift de achtergrond op) — maar per categorie houden er altijd
# minstens twee ruimte, en PFOA nooit.
# `norm_mg_l` hier is de basisnorm (categorie rivier); per categorie wordt hij geschaald met
# `norm_factor`. `verzadiging` is de verhouding achtergrond/norm binnen dezelfde categorie en
# blijft dus, ongeacht `norm_factor`, bepalend voor of een stof boven of onder de norm zit —
# `factor` (hierboven) schuift die verhouding vervolgens per categorie op.
_PARAMETERS = [
    {"naam": "stikstof totaal", "norm_mg_l": 2.2, "verzadiging": 0.98, "zzs": False,
     "toelichting": "Nutriënt. De norm ligt dicht bij wat er al in zit, dus hier gaat het volume "
                    "van een lozing wél meetellen."},
    {"naam": "zink", "norm_mg_l": 0.0078, "verzadiging": 0.91, "zzs": False,
     "toelichting": "Metaal; krappe marge, grotendeels diffuus van herkomst."},
    {"naam": "AOX", "norm_mg_l": 0.05, "verzadiging": 0.42, "zzs": False,
     "toelichting": "Somparameter organische halogenen; hier nog ruimte."},
    {"naam": "PFOA", "norm_mg_l": 0.0000048, "verzadiging": 1.27, "zzs": True,
     "toelichting": "Zeer zorgwekkende stof. De achtergrond ligt bóven de norm — er is geen "
                    "ruimte, en er geldt een minimalisatieplicht."},
]

_ECHTE_VELDEN = {
    "waterlichaam": "naam", "owl_id": "owl_id", "stroomgebiedsdistrict": "stroomgebiedsdistrict",
    "watertype": "watertype", "watercategorie": "watercategorie", "waterstatus": "waterstatus",
    "waterbeheerder": "beheerder", "omvang": "omvang", "omvang_eenheid": "omvang_eenheid",
    "gemiddelde_diepte": "gemiddelde_diepte",
}


def _rond_significant(x: float, cijfers: int = 4) -> float:
    """Rond af op een vast aantal significante cijfers, niet op een vast aantal decimalen.

    De parameters lopen in orde van grootte uiteen van stikstof (~1 mg/l) tot PFOA (~1e-6 mg/l);
    een vaste decimalenafronding zou PFOA plat slaan tot 0.0. Voorkomt ook drijvendekomma-ruis
    zoals 1.9800000000000002 in wat de API en de pagina uiteindelijk tonen.
    """
    if x == 0:
        return 0.0
    exponent = math.floor(math.log10(abs(x)))
    schaal = 10 ** (cijfers - 1 - exponent)
    return round(x * schaal) / schaal


def _debiet(cat: dict, omvang, bekend: bool) -> float:
    """Basisdebiet van de categorie, geschaald met de omvang van dít waterlichaam."""
    basis = cat["debiet_basis_m3_s"]
    if not bekend or not omvang or omvang <= 0:
        return basis
    # Milde schaling: een tien keer zo groot water krijgt ruwweg twee keer het debiet.
    return round(basis * (float(omvang) / 100.0) ** 0.3, 1)


def profiel(cs: dict) -> dict:
    """Een profiel voor het waterlichaam uit deze contextset."""
    echt = {doel: cs.get(bron_veld) for bron_veld, doel in _ECHTE_VELDEN.items()}

    if not cs.get("owl_id"):
        return {"echt": echt, "afgeleid": {}, "herkomst": {}, "volledig": False,
                "reden": "geen rijkswaterlichaam op dit punt; zonder waterlichaam is er geen "
                         "norm om ruimte tegen af te zetten"}

    code = str(cs.get("watercategorie") or "")
    bekend = code in _CATEGORIEEN
    cat = _CATEGORIEEN.get(code, _TERUGVAL)
    q = _debiet(cat, cs.get("omvang"), bekend)

    parameters = []
    for p in _PARAMETERS:
        norm = p["norm_mg_l"] * cat["norm_factor"]
        achtergrond = norm * p["verzadiging"] * cat["factor"]
        parameters.append({"naam": p["naam"], "norm_mg_l": _rond_significant(norm),
                           "achtergrond_mg_l": _rond_significant(achtergrond), "zzs": p["zzs"],
                           "toelichting": p["toelichting"]})

    herkomst_debiet = (f"afgeleid van KRW-categorie {code} ({cat['naam']}) en de omvang "
                       f"uit de bron" if bekend else
                       f"terugval: categorie '{code}' is onbekend, basisdebiet gebruikt")
    return {
        "echt": echt,
        "afgeleid": {"debiet_m3_s": q, "parameters": parameters,
                     "categorie_naam": cat["naam"]},
        "herkomst": {
            "debiet_m3_s": herkomst_debiet,
            "parameters": "normen door dit lab gekozen in de orde van de KRW-doelen, niet uit "
                          f"het Bkl overgenomen, en per categorie geschaald met een "
                          f"normfactor ({cat['norm_factor']}); achtergrondconcentraties "
                          "daarna afgeleid van diezelfde norm door hem eerst te vermenigvuldigen "
                          "met een vaste verzadigingsgraad per stof (van 0.42 voor AOX tot 1.27 "
                          f"voor PFOA) en vervolgens met de categoriefactor ({cat['factor']})",
            "categorie_naam": f"KRW-categorie {code} uit de bron" if bekend else "terugval",
        },
        "volledig": bekend,
    }


def als_waterlichaam(p: dict) -> dict:
    """Het profiel in het formaat dat `ruimte.bereken()` verwacht."""
    if not p.get("afgeleid"):
        raise ValueError(p.get("reden") or "geen profiel")
    return {"naam": p["echt"].get("naam"), "owl_id": p["echt"].get("owl_id"),
            "debiet_m3_s": p["afgeleid"]["debiet_m3_s"],
            "parameters": p["afgeleid"]["parameters"]}
