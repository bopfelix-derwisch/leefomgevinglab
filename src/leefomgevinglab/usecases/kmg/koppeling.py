"""Een vergunning aan een E-PRTR-inrichting knopen — en eerlijk zijn over hoe goed dat lukt.

Dit is dezelfde vraag als bij de parameternamen, één niveau hoger. De vergunning en de melding
gaan over hetzelfde bedrijf op dezelfde plek, en er is geen enkel veld dat ze verbindt.

**Wat er wel en niet werkt, gemeten op de vijf Maas-vergunningen met een zinkvracht.**

* Op naam alleen: één van de vijf. Schrijfwijzen lopen uiteen ("B.V." tegen "BV") en een
  inrichting staat soms onder de naam van het terrein in plaats van die van het bedrijf — Sitech
  zit op Chemelot.
* Op coördinaat alleen: te grof. Binnen 1500 m kreeg Sappi de zinkmelding van een naburig
  recyclingbedrijf toegewezen, en Johnson Matthey dezelfde. Nabijheid is in een industriegebied
  geen bewijs van identiteit.
* Op allebei, met een krappe straal: zuiver. Binnen 400 m én een naamgelijkenis boven de drempel
  gaf drie treffers op 34, 231 en 337 meter, alle drie met gelijkenis 1,00, en geen enkele
  vals-positieve.

Drie van de vijf dus, met twee misses die echte bedrijven zijn. Dat is de uitkomst, en zij hoort
zichtbaar te blijven in plaats van weggepoetst: elke koppeling draagt hier haar `gelijkenis` en
`afstand_m` mee, zodat een lezer kan zien waarop zij berust.

**Wat dit zou oplossen — en wat niet.** De Atlas kent het veld `Vestigingsnummer_KvK`, en dat is
wél gevuld: 31 van de 31 vergunningen rond Belfeld en 22 van de 22 rond Eijsden dragen er een
(live nagekeken 2026-10-27; een eerdere versie van deze tekst beweerde het tegendeel). De
vergunning heeft dus een identificatie van de rechtspersoon. E-PRTR heeft die niet: daar staat
`nationalid`, een negencijferig inrichtingsnummer uit het eMJV (`000201503`), dat geen
KvK-vestigingsnummer is en er ook niet uit af te leiden valt.

Het ontbrekende veld zit dus niet in de vergunning maar in de melding — of, preciezer, tussen de
twee in: er is geen gepubliceerde kruistabel van eMJV-inrichting naar KvK-vestiging. Dat is één
tabel, geen stelselwijziging, en zij vervangt deze hele heuristiek door een join.
"""
import difflib

# Boven deze gelijkenis wordt een naam als dezelfde inrichting gelezen. Empirisch gekozen: de drie
# echte treffers scoorden 1,00 en de dichtstbijzijnde onterechte kandidaat bleef ruim daaronder.
# Lager zetten levert vals-positieven in industriegebieden; hoger zetten verliest "B.V." tegen "BV".
DREMPEL = 0.55

# Rechtsvormen en ruis die niets over de identiteit zeggen en de vergelijking alleen verstoren.
# Zonder leestekens, want `normaliseer` haalt die er eerst af.
_RUIS = ("bv", "b", "v", "nv", "vof", "cv", "holding", "nederland",
         "netherlands", "the", "locatie")


def normaliseer(naam: str) -> str:
    """Een bedrijfsnaam terugbrengen tot wat hem onderscheidt.

    Leestekens gaan er eerst af en pas daarna wordt op ruis gefilterd. Andersom werkt het niet:
    "B.V." en "BV" zijn dan twee verschillende woorden, waarvan er maar één wordt weggestreept, en
    dan scoort een paar dat identiek hoort te zijn 0,91 in plaats van 1,00.
    """
    kaal = "".join(ch if ch.isalnum() or ch.isspace() else " "
                   for ch in (naam or "").lower())
    woorden = [w for w in kaal.split() if w not in _RUIS]
    return " ".join(woorden).strip()


def gelijkenis(a: str, b: str) -> float:
    na, nb = normaliseer(a), normaliseer(b)
    if not na or not nb:
        return 0.0
    return difflib.SequenceMatcher(None, na, nb).ratio()


def _afstand(p, q) -> float | None:
    if not p or not q or len(p) < 2 or len(q) < 2:
        return None
    return ((p[0] - q[0]) ** 2 + (p[1] - q[1]) ** 2) ** 0.5


def koppel(vergunning_naam: str, vergunning_rd, meldingen: list[dict],
           drempel: float = DREMPEL) -> dict:
    """De beste inrichting bij deze vergunning, of een expliciete niet-treffer.

    Levert altijd een woordenboek met `gekoppeld`. Is dat onwaar, dan staat in `reden` waarom —
    "niets binnen de straal" en "wel iets in de buurt maar met een andere naam" zijn verschillende
    uitspraken en worden hier niet op één hoop gegooid.
    """
    if not meldingen:
        return {"gekoppeld": False, "reden": "geen E-PRTR-inrichting binnen de zoekstraal",
                "soort": "niets in de buurt"}

    kandidaten = {}
    for m in meldingen:
        naam = m.get("productionsite_name") or ""
        kandidaten.setdefault(naam, {"naam": naam, "nationalid": m.get("nationalid"),
                                     "rd": m.get("rd"), "rijen": []})
        kandidaten[naam]["rijen"].append(m)

    beste = max(kandidaten.values(),
                key=lambda k: gelijkenis(k["naam"], vergunning_naam), default=None)
    score = gelijkenis(beste["naam"], vergunning_naam) if beste else 0.0
    if score < drempel:
        return {"gekoppeld": False, "soort": "naam wijkt af",
                "reden": (f"wel {len(kandidaten)} inrichting(en) in de buurt, maar geen met een "
                          f"passende naam; dichtstbij qua naam is "
                          f"{beste['naam'] if beste else '?'} ({score:.2f})"),
                "nabij": sorted(kandidaten)}

    return {
        "gekoppeld": True,
        "naam": beste["naam"], "nationalid": beste["nationalid"],
        "gelijkenis": round(score, 3),
        "afstand_m": (round(_afstand(vergunning_rd, beste["rd"]))
                      if _afstand(vergunning_rd, beste["rd"]) is not None else None),
        "meldingen": beste["rijen"],
        # Waarop deze koppeling berust, zodat een lezer haar kan wegen in plaats van geloven.
        "grondslag": "nabijheid plus naamgelijkenis; er is geen gedeelde identificatie",
    }


def gemeld_per_stof(koppeling: dict, aquo_van_prtr: dict | None = None,
                    medium: str | None = "WATER") -> dict:
    """De gemelde vracht per stof, uit de meest recente jaargang die er is.

    Het filteren op medium gebeurt hier en niet bij het ophalen, en dat is met opzet. Zou je alleen
    de waterregels ophalen, dan is een inrichting die wél bestaat maar niets naar water meldt niet
    te onderscheiden van een inrichting die er niet is — en dat zijn twee heel verschillende
    uitspraken. Johnson Matthey en Solvay zijn precies dat geval.

    E-PRTR gebruikt eigen stofaanduidingen (`ZNANDCOMPOUNDS`), niet Aquo-codes. `aquo_van_prtr`
    vertaalt waar wij de vertaling kennen; de rest blijft onder zijn eigen naam staan in plaats van
    te verdwijnen.
    """
    if not koppeling.get("gekoppeld"):
        return {}
    vertaal = aquo_van_prtr or PRTR_NAAR_AQUO
    uit: dict[str, dict] = {}
    for r in koppeling.get("meldingen") or []:
        if medium and (r.get("mediumcode") or "").upper() != medium.upper():
            continue
        stof = (r.get("pollutant") or "").strip()
        kg = r.get("totalpollutantquantitykg")
        if not stof or kg is None:
            continue
        sleutel = vertaal.get(stof.upper(), stof)
        jaar = r.get("year")
        huidig = uit.get(sleutel)
        if huidig is None or (jaar or 0) > (huidig.get("jaar") or 0):
            uit[sleutel] = {"kg_jaar": float(kg), "jaar": jaar, "prtr_stof": stof,
                            "aquo": sleutel in vertaal.values()}
    return uit


# E-PRTR-stofnamen naar Aquo-codes, voor de stoffen die dit lab volgt. Bewust kort: alleen wat
# nagekeken is. Een stof die hier niet staat blijft onder haar eigen E-PRTR-naam staan, zodat
# zichtbaar blijft dát zij gemeld is.
PRTR_NAAR_AQUO = {
    "ZNANDCOMPOUNDS": "Zn",
    "NIANDCOMPOUNDS": "Ni",
    "CUANDCOMPOUNDS": "Cu",
    "PBANDCOMPOUNDS": "Pb",
    "CRANDCOMPOUNDS": "Cr",
    "ASANDCOMPOUNDS": "As",
    "CDANDCOMPOUNDS": "Cd",
    "HGANDCOMPOUNDS": "Hg",
    "TOTALNITROGEN": "Ntot",
    "TOTALPHOSPHORUS": "Ptot",
    "CHLORIDES": "Cl",
    "FLUORIDES": "F",
}


def benutting(vergund_kg: float | None, gemeld_kg: float | None) -> dict | None:
    """Welk deel van de vergunde ruimte daadwerkelijk gemeld wordt.

    Geen getal zonder beide helften, en geen percentage bij een vergunde ruimte van nul. Ontbreekt
    de melding, dan is dat geen nul maar een onbekende: E-PRTR kent alleen inrichtingen boven de
    rapportagedrempel.
    """
    if vergund_kg is None or gemeld_kg is None or vergund_kg <= 0:
        return None
    return {"vergund_kg": vergund_kg, "gemeld_kg": gemeld_kg,
            "benut_pct": round(gemeld_kg / vergund_kg * 100, 2),
            "onbenut_kg": round(vergund_kg - gemeld_kg, 3)}
