"""De stoffen als graaf: wat een kennisgraaf toevoegt bovenop het informatiemodel.

**Het onderscheid.** Het informatiemodel (`kmg/lozingsmodel.py`) beschrijft vélden: wat is een
lozingsvoorschrift, welke velden horen erbij, met welke zekerheid is elk ingevuld. Een graaf
beschrijft **relaties tussen dingen die elk hun eigen identiteit houden**. Dat klinkt academisch
tot je naar de openstaande lijst van dit dossier kijkt: hoedanigheid en geldigheidsperiode zijn
velden, maar de koppeling eMJV ↔ KvK en de stroomvolgorde tussen waterlichamen zijn relaties.
De helft van wat nog mist, is dus geen modelprobleem.

**Wat deze module aantoont, op de stoffen.** Dit lab vertaalt E-PRTR-stofnamen naar Aquo-codes
met een handgeschreven tabel van twaalf regels (`kmg/koppeling.PRTR_NAAR_AQUO`). De Aquo-
domeintabel draagt bij 4104 van de 5623 geldige parameters een **CAS-nummer** — een wereldwijd
gedeelde identificatie. De E-PRTR-verordening doet dat in bijlage II ook. Twee bronnen die
hetzelfde nummer dragen hoeven niet met de hand aan elkaar geknoopt te worden.

Wat eruit komt is genuanceerder dan "CAS lost alles op", en juist dat is de uitkomst:

* De **specifieke stoffen** koppelen vanzelf en eenduidig. Alle metalen, trichloormethaan en de
  chlooralkanen vinden via hun CAS-nummer precies één Aquo-code. Twee daarvan staan niet in onze
  handtabel — CAS vindt dus méér dan wij met de hand deden, niet minder.
* De **somparameters** hebben per definitie geen CAS. TOC, AOX, cyanides, totaal stikstof: dat
  zijn grootheden die door een meetmethode worden gedefinieerd, niet door een molecuul. Daar
  helpt een gedeeld stofnummer niet, en is een andere sóórt relatie nodig — part-of, of
  "gedefinieerd door methode". Dat is precies waar `Groep` en `Gerelateerd` in de Aquo-tabel voor
  bedoeld zijn.

**En dat laatste gooien we nu weg.** `Gerelateerd` is in 771 van de 7109 rijen gevuld en onze
ingest leest die kolom niet. `smetln6` ("som 6 metalen") draagt er een. Een vergunning die zowel
zink als som-6-metalen begrenst, telt in een recordmodel als twee losse velden; in een graaf is
het een deel-van-relatie, en dan is dubbeltelling een vraag die je kúnt stellen.

**Eén eerlijke beperking.** De waarden in `Gerelateerd` zijn UUID-URI's, terwijl de `Id`-kolom
een volgnummer is. Uit dit bestand alleen zijn die 771 relaties dus niet te resolven — de doelen
staan er niet met hun eigen UUID in. Zij komen hier als randen met een onbekend doel binnen, en
dat staat zo in de uitkomst in plaats van te worden weggelaten. Aquo publiceert vandaag geen RDF
en de MediaWiki-API eist een login, dus dit gat is niet door ons te dichten.
"""
import csv
from pathlib import Path

from .kmg.koppeling import PRTR_NAAR_AQUO

AQUO_PAD = "/mnt/nvme/geluidsmeter/data/external/wkp/aquo_Parameter.csv"

BRON_AQUO = {
    "naam": "Aquo-domeintabel Parameter",
    "houder": "Informatiehuis Water",
    "url": "https://www.aquo.nl/images/aquo/a/a3/Parameter.csv",
}

# De E-PRTR-stoffen die rond de Maas daadwerkelijk naar water gemeld worden (live geteld op
# 2026-10-29: 461 waterregels rond Eijsden, Belfeld en het Haringvliet, 16 verschillende stoffen).
# `cas` komt uit bijlage II van de E-PRTR-verordening en is hier met de hand overgenomen — de
# WFS van het RIVM levert het veld niet mee, en dát is de bevinding: de brug bestaat in de
# standaard maar niet in de geleverde data.
#
# `som` markeert de parameters die door een meetmethode worden gedefinieerd in plaats van door
# een molecuul. Die hebben geen CAS, en dat is geen omissie maar hun aard.
PRTR_STOFFEN = [
    {"code": "ZNANDCOMPOUNDS", "naam": "zink en verbindingen", "cas": "7440-66-6", "som": False},
    {"code": "ASANDCOMPOUNDS", "naam": "arseen en verbindingen", "cas": "7440-38-2", "som": False},
    {"code": "NIANDCOMPOUNDS", "naam": "nikkel en verbindingen", "cas": "7440-02-0", "som": False},
    {"code": "CUANDCOMPOUNDS", "naam": "koper en verbindingen", "cas": "7440-50-8", "som": False},
    {"code": "PBANDCOMPOUNDS", "naam": "lood en verbindingen", "cas": "7439-92-1", "som": False},
    {"code": "CRANDCOMPOUNDS", "naam": "chroom en verbindingen", "cas": "7440-47-3", "som": False},
    {"code": "HGANDCOMPOUNDS", "naam": "kwik en verbindingen", "cas": "7439-97-6", "som": False},
    {"code": "TRICHLOROMETHANE", "naam": "trichloormethaan", "cas": "67-66-3", "som": False},
    {"code": "CHLORO-ALKANES(C10-13)", "naam": "chlooralkanen C10-13",
     "cas": "85535-84-8", "som": False},
    {"code": "TOTALNITROGEN", "naam": "totaal stikstof", "cas": None, "som": True},
    {"code": "TOTALPHOSPHORUS", "naam": "totaal fosfor", "cas": None, "som": True},
    {"code": "CHLORIDES", "naam": "chloriden (als totaal Cl)", "cas": None, "som": True},
    {"code": "FLUORIDES", "naam": "fluoriden (als totaal F)", "cas": None, "som": True},
    {"code": "CYANIDES", "naam": "cyaniden (als totaal CN)", "cas": None, "som": True},
    {"code": "TOC", "naam": "totaal organisch koolstof", "cas": None, "som": True},
    {"code": "HALOGENATEDORGANICCOMPOUNDS", "naam": "adsorbeerbare organische halogenen (AOX)",
     "cas": None, "som": True},
]

# De stoffen die dit lab in het waterdossier volgt, zodat de graaf ze kan markeren.
GEVOLGD = {"Zn", "Ntot", "PFOA"}

# Ruim midden-Maas punt voor de controle-bevraging: met de straal uit de kmg-config pakt
# dit het hele register van de Atlas in één greep.
MAASPUNT = (170000.0, 390000.0)


def laad_aquo(pad: str | None = None) -> dict:
    """De geldige Aquo-parameters, met hun CAS-nummer en relaties.

    Vervallen rijen gaan eruit: een vervallen code is geen sleutel om op te koppelen. De
    CAS-sentinel `NVT` wordt `None` — hij betekent "niet van toepassing", niet "onbekend
    nummer", en als tekst zou hij 1519 parameters aan elkaar knopen die niets delen.
    """
    p = Path(pad or AQUO_PAD)
    if not p.exists():
        return {"beschikbaar": False, "parameters": {}, "per_cas": {},
                "reden": f"Aquo-domeintabel ontbreekt ({p}); draai scripts/16_bouw_aquo_parameters.py"}

    parameters: dict[str, dict] = {}
    per_cas: dict[str, list[str]] = {}
    vervallen = 0
    with open(p, encoding="utf-8-sig", newline="") as f:
        for r in csv.DictReader(f, delimiter=";"):
            if (r.get("Status") or "").strip() != "Geldig":
                vervallen += 1
                continue
            code = (r.get("Codes") or "").strip()
            if not code:
                continue
            cas = (r.get("CASnummer") or "").strip()
            cas = None if cas in ("", "NVT") else cas
            parameters[code] = {
                "code": code,
                "naam": (r.get("Omschrijving") or "").strip() or code,
                "groep": (r.get("Groep") or "").strip() or None,
                "cas": cas,
                "gerelateerd": (r.get("Gerelateerd") or "").strip() or None,
                "alternatief": (r.get("Alternatieve term") or "").strip() or None,
            }
            if cas:
                per_cas.setdefault(cas, []).append(code)
    return {"beschikbaar": True, "parameters": parameters, "per_cas": per_cas,
            "bron": BRON_AQUO, "reden": None,
            "telling": {"geldig": len(parameters), "vervallen": vervallen,
                        "met_cas": sum(1 for v in parameters.values() if v["cas"]),
                        "met_relatie": sum(1 for v in parameters.values() if v["gerelateerd"]),
                        "cas_niet_uniek": sum(1 for v in per_cas.values() if len(v) > 1)}}


def koppel_via_cas(aquo: dict, stoffen: list[dict] | None = None) -> list[dict]:
    """Per E-PRTR-stof: lukt de koppeling via CAS, en wat deed de handtabel?

    Levert per stof een `soort`, en die vier waarden zijn het hele punt van deze pagina:

    * `cas_en_hand`  — beide wegen leiden naar dezelfde Aquo-code
    * `alleen_cas`   — CAS vindt een code die onze handtabel mist
    * `alleen_hand`  — geen CAS beschikbaar, de handtabel vulde het gat
    * `geen_brug`    — geen CAS en niet met de hand gekoppeld
    """
    uit = []
    for s in (stoffen or PRTR_STOFFEN):
        via_cas = (aquo.get("per_cas") or {}).get(s["cas"] or "", [])
        hand = PRTR_NAAR_AQUO.get(s["code"])
        code = via_cas[0] if len(via_cas) == 1 else None
        if code and hand:
            soort = "cas_en_hand" if code == hand else "cas_wijkt_af"
        elif code:
            soort = "alleen_cas"
        elif hand:
            soort = "alleen_hand"
        else:
            soort = "geen_brug"
        uit.append({**s, "aquo_via_cas": code, "aquo_via_hand": hand,
                    "cas_meerduidig": len(via_cas) > 1, "soort": soort,
                    "aquo": code or hand,
                    "naam_aquo": (aquo.get("parameters") or {}).get(code or hand or "", {}).get("naam")})
    return uit


def dubbeltelling(aquo: dict, som_code: str = "smetln6") -> dict:
    """Het risico dat een somparameter en haar delen allebei worden meegeteld.

    `smetln6` is "som 6 metalen (Zn, Cu, Pb, Ni, Cr, As)". Begrenst een vergunning zowel zink als
    die som, dan zijn dat in een recordmodel twee losse velden en telt wie ze optelt het zink
    dubbel. De Aquo-tabel weet dat er een relatie is — `Gerelateerd` is gevuld — maar zegt er niet
    bij welke. De delen hieronder komen daarom uit de **omschrijving**, en dat is precies het
    punt: de informatie staat in een zin in plaats van in een relatie.
    """
    param = (aquo.get("parameters") or {}).get(som_code)
    if not param:
        return {"beschikbaar": False, "reden": f"{som_code} niet in de domeintabel"}
    tekst = param["naam"]
    binnen = tekst[tekst.find("(") + 1:tekst.find(")")] if "(" in tekst else ""
    delen = [d.strip() for d in binnen.split(",") if d.strip()]
    gevonden = [d for d in delen if d in (aquo.get("parameters") or {})]
    return {"beschikbaar": True, "som": param, "delen_uit_omschrijving": delen,
            "delen_als_code": gevonden,
            "heeft_relatie": bool(param["gerelateerd"]),
            "relatie_resolvabaar": False,
            "les": ("De samenstelling staat in de omschrijving, niet als relatie. Een machine "
                    "die dubbeltelling wil voorkomen moet hier dus tekst ontleden.")}


def _alle_parameters(pad: str | None = None) -> list[dict]:
    """Álle rijen, ook de vervallen — `laad_aquo` gooit die er juist uit.

    Voor koppelen wil je ze niet; voor een kwaliteitscontrole wil je ze wél, want "deze naam
    bestaat alleen nog als vervallen code" is een andere bevinding dan "deze naam bestaat niet".
    """
    p = Path(pad or AQUO_PAD)
    if not p.exists():
        return []
    with open(p, encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f, delimiter=";"))


def _sommen_met_delen(rijen: list[dict]) -> dict[str, tuple[str, list[str]]]:
    """Somparameters waarvan de delen uit de omschrijving te halen zijn.

    Dit is het punt van deze hele pagina in één functie: de samenstelling van een somparameter
    staat in een zin tussen haakjes, niet in een relatie. Om er een controle op te kunnen doen
    moeten wij die zin dus ontleden — iets wat een graaf met echte part-of-relaties overbodig
    zou maken.
    """
    uit: dict[str, tuple[str, list[str]]] = {}
    for r in rijen:
        if (r.get("Status") or "").strip() != "Geldig":
            continue
        o = (r.get("Omschrijving") or "").strip()
        if not o.lower().startswith("som") or "(" not in o or ")" not in o:
            continue
        delen = [d.strip() for d in o[o.find("(") + 1:o.find(")")].split(",") if d.strip()]
        if delen:
            uit[o.lower()] = ((r.get("Codes") or "").strip(), delen)
    return uit


def controleer(register: list[dict], aquo_pad: str | None = None) -> dict:
    """De graaf als kwaliteitscontrole over een echt vergunningregister.

    Drie vragen die je met een losse opzoektabel niet kunt stellen, omdat zij over de *status*
    en de *samenstelling* van een code gaan in plaats van over haar bestaan:

    1. **Hangt een voorschrift aan een vervallen code?** De koppeling slaat vervallen codes over,
       dus zo'n voorschrift valt stil weg als "onbruikbaar" zonder dat iemand ziet waarom. Het
       verschil tussen "deze naam ken ik niet" en "deze naam is ingetrokken" is bruikbaar: het
       tweede is een onderhoudsactie, het eerste een standaardisatievraag.
    2. **Kent Aquo deze naam helemaal niet?** Dat zijn de stoffen waar de standaard achterloopt
       op wat er vergund wordt.
    3. **Begrenst één vergunning zowel een som als haar delen?** Dan telt wie optelt dubbel. Deze
       vraag is alleen te stellen als je de samenstelling van de som kent.
    """
    rijen = _alle_parameters(aquo_pad)
    if not rijen:
        return {"beschikbaar": False,
                "reden": "Aquo-domeintabel ontbreekt; draai scripts/16_bouw_aquo_parameters.py"}

    per_naam: dict[str, list[dict]] = {}
    for r in rijen:
        per_naam.setdefault((r.get("Omschrijving") or "").strip().lower(), []).append(r)
    code_van = {n: rs[0].get("Codes", "").strip() for n, rs in per_naam.items()
                if any((x.get("Status") or "").strip() == "Geldig" for x in rs)}
    sommen = _sommen_met_delen(rijen)

    tel = tel_parameters(register)
    vervallen, onbekend = [], []
    for naam, n in sorted(tel.items(), key=lambda kv: -kv[1]):
        treffers = per_naam.get(naam.lower())
        if not treffers:
            onbekend.append({"naam": naam, "voorschriften": n})
        elif not any((t.get("Status") or "").strip() == "Geldig" for t in treffers):
            vervangen = (treffers[0].get("Vervangen door") or "").strip() or None
            vervallen.append({"naam": naam, "voorschriften": n,
                              "code": (treffers[0].get("Codes") or "").strip(),
                              "vervangen_door": vervangen})

    dubbel = []
    for post in register:
        namen = {(v.get("parameter") or "").strip().lower()
                 for v in (post.get("voorschriften") or [])}
        codes = {code_van[n] for n in namen if n in code_van}
        for somnaam in namen & set(sommen):
            somcode, delen = sommen[somnaam]
            overlap = sorted(set(delen) & codes)
            if overlap:
                dubbel.append({"vergunning": post.get("naam"),
                               "kenmerk": post.get("kenmerk"),
                               "som": somcode, "ook_apart": overlap})

    voorschriften = sum(tel.values())
    return {
        "beschikbaar": True,
        "telling": {
            "vergunningen": len(register), "voorschriften": voorschriften,
            "parameternamen": len(tel),
            "op_vervallen_code": sum(x["voorschriften"] for x in vervallen),
            "namen_vervallen": len(vervallen),
            "niet_in_aquo": sum(x["voorschriften"] for x in onbekend),
            "namen_onbekend": len(onbekend),
            "dubbeltelling": len(dubbel),
            "sommen_met_delen": len(sommen),
        },
        "vervallen": vervallen, "onbekend": onbekend, "dubbeltelling": dubbel,
    }


def tel_parameters(register: list[dict]) -> dict[str, int]:
    """Parameternaam → aantal voorschriften, over een heel register."""
    tel: dict[str, int] = {}
    for post in register:
        for v in post.get("voorschriften") or []:
            naam = (v.get("parameter") or "").strip()
            if naam:
                tel[naam] = tel.get(naam, 0) + 1
    return tel


# Waar een rand vandaan komt. Dit is dezelfde gedachte als `zekerheid` per veld in
# `kmg/lozingsmodel.py`, maar dan op relaties — en het is de kern van wat deze graaf laat zien.
# Een graaf waarin alle randen er hetzelfde uitzien, verbergt juist wat hier het onderwerp is.
HERKOMST = {
    "bron": "staat zo in de bron",
    "lab": "bewering van dit lab",
    "afgeleid": "afgeleid uit vrije tekst",
    "onvolgbaar": "staat in de bron, maar is niet te volgen",
}


def anatomie(aquo_pad: str | None = None) -> dict:
    """Waar de graaf uit bestaat: knoopsoorten, randsoorten en hun herkomst.

    De plaat met zestien rijen elders op deze pagina toont de **doorstroom** — welke stof langs
    welke weg bij welke code komt. Dit toont de **anatomie**: welke soorten dingen er zijn en
    welke soorten verbanden ertussen liggen, met per verband hoeveel het er zijn en waarop het
    berust.

    Dat laatste is de boodschap. Van de zeven randsoorten komen er vier rechtstreeks uit de
    bron, één is een bewering van dit lab, één is uit een zin ontleed, en één staat er wel maar
    is niet te volgen. De relaties die dit dossier het hardst nodig heeft zitten in die laatste
    drie categorieën.
    """
    rijen = _alle_parameters(aquo_pad)
    if not rijen:
        return {"beschikbaar": False,
                "reden": "Aquo-domeintabel ontbreekt; draai scripts/16_bouw_aquo_parameters.py"}
    aquo = laad_aquo(aquo_pad)
    geldig = [r for r in rijen if (r.get("Status") or "").strip() == "Geldig"]
    sommen = _sommen_met_delen(rijen)
    t = aquo["telling"]

    def _n(veld: str, alleen_geldig: bool = True) -> int:
        bron = geldig if alleen_geldig else rijen
        return sum(1 for r in bron if (r.get(veld) or "").strip())

    knopen = [
        {"id": "prtr", "naam": "E-PRTR-stof", "aantal": len(PRTR_STOFFEN),
         "wat": "wat een inrichting jaarlijks meldt te lozen"},
        {"id": "cas", "naam": "CAS-nummer", "aantal": len(aquo["per_cas"]),
         "wat": "wereldwijde identificatie van één stof"},
        {"id": "aquo", "naam": "Aquo-parameter", "aantal": t["geldig"],
         "bij": f"+ {t['vervallen']} vervallen", "wat": "de Nederlandse waterstandaard"},
        {"id": "groep", "naam": "Groep",
         "aantal": len({(r.get("Groep") or "").strip() for r in geldig if (r.get("Groep") or "").strip()}),
         "wat": "chemische stof, grootheid, object, …"},
        {"id": "som", "naam": "somparameter", "aantal": len(sommen),
         "wat": "een Aquo-parameter die uit andere bestaat"},
        {"id": "onbekend", "naam": "niet te volgen", "aantal": None,
         "wat": "de doelen van Gerelateerd bestaan, maar niet in dit bestand"},
    ]

    randen = [
        {"id": "prtr_cas", "van": "prtr", "naar": "cas", "naam": "heeft CAS",
         "aantal": sum(1 for s in PRTR_STOFFEN if s["cas"]), "herkomst": "lab",
         "toelichting": "staat in bijlage II van de E-PRTR-verordening, maar de WFS van het RIVM "
                        "levert het veld niet mee — dus met de hand overgenomen"},
        {"id": "aquo_cas", "van": "aquo", "naar": "cas", "naam": "heeft CAS",
         "aantal": t["met_cas"], "herkomst": "bron", "toelichting": "kolom CASnummer"},
        {"id": "prtr_aquo", "van": "prtr", "naar": "aquo", "naam": "gelijkgesteld aan",
         "aantal": len(PRTR_NAAR_AQUO), "herkomst": "lab",
         "toelichting": "de handtabel PRTR_NAAR_AQUO; precies wat het CAS-nummer overbodig maakt"},
        {"id": "aquo_groep", "van": "aquo", "naar": "groep", "naam": "hoort bij",
         "aantal": _n("Groep"), "herkomst": "bron", "toelichting": "kolom Groep"},
        {"id": "aquo_som", "van": "aquo", "naar": "som", "naam": "is een",
         "aantal": len(sommen), "herkomst": "bron",
         "toelichting": "herkenbaar aan de omschrijving; een somparameter is gewoon een "
                        "Aquo-parameter"},
        {"id": "som_deel", "van": "som", "naar": "aquo", "naam": "bestaat uit",
         "aantal": sum(len(d) for _c, d in sommen.values()), "herkomst": "afgeleid",
         "toelichting": "ontleed uit de tekst tussen haakjes in de omschrijving — dit is de "
                        "relatie die er zou moeten staan en niet staat"},
        {"id": "aquo_rel", "van": "aquo", "naar": "onbekend", "naam": "gerelateerd aan",
         "aantal": t["met_relatie"], "herkomst": "onvolgbaar",
         "toelichting": "kolom Gerelateerd draagt een UUID, terwijl de Id-kolom een volgnummer "
                        "is; het doel staat niet in dit bestand"},
        {"id": "aquo_verv", "van": "aquo", "naar": "onbekend", "naam": "vervangen door",
         "aantal": _n("Vervangen door", alleen_geldig=False), "herkomst": "onvolgbaar",
         "toelichting": "zelfde probleem; en bij 3 van de 4 ingetrokken codes in het "
                        "Maasregister is dit veld leeg"},
    ]

    per_herkomst: dict[str, int] = {}
    for r in randen:
        per_herkomst[r["herkomst"]] = per_herkomst.get(r["herkomst"], 0) + 1

    # De samenvattende zin wordt geteld en niet getypt. In de eerste versie stond hier "vier van
    # de acht" terwijl het er drie waren — precies de fout waar deze hele pagina over gaat.
    uit_de_bron = per_herkomst.get("bron", 0)
    rest = len(randen) - uit_de_bron
    return {"beschikbaar": True, "knopen": knopen, "randen": randen,
            "herkomst": HERKOMST, "per_herkomst": per_herkomst,
            "les": (f"{uit_de_bron} van de {len(randen)} randsoorten komen rechtstreeks uit de "
                    f"bron. De overige {rest} zijn een bewering van dit lab, uit vrije tekst "
                    f"ontleed, of staan er wel maar zijn niet te volgen — en juist daar zitten "
                    f"de verbanden die dit dossier nodig heeft.")}


def bouw(aquo_pad: str | None = None) -> dict:
    """De graaf: knopen, randen met hun herkomst, en wat eruit volgt."""
    aquo = laad_aquo(aquo_pad)
    if not aquo.get("beschikbaar"):
        return {"beschikbaar": False, "reden": aquo.get("reden"),
                "knopen": [], "randen": [], "telling": {}}

    koppelingen = koppel_via_cas(aquo)
    knopen, randen = [], []

    for k in koppelingen:
        knopen.append({"id": f"prtr:{k['code']}", "soort": "prtr",
                       "label": k["code"], "naam": k["naam"], "cas": k["cas"],
                       "som": k["som"]})
        if k["cas"]:
            knopen.append({"id": f"cas:{k['cas']}", "soort": "cas", "label": k["cas"]})
            randen.append({"van": f"prtr:{k['code']}", "naar": f"cas:{k['cas']}",
                           "soort": "cas", "herkomst": "E-PRTR-verordening bijlage II"})
        doel = k["aquo"]
        if doel:
            p = aquo["parameters"].get(doel, {})
            knopen.append({"id": f"aquo:{doel}", "soort": "aquo", "label": doel,
                           "naam": p.get("naam"), "cas": p.get("cas"),
                           "groep": p.get("groep"), "gevolgd": doel in GEVOLGD})
            if k["cas"] and k["aquo_via_cas"]:
                randen.append({"van": f"cas:{k['cas']}", "naar": f"aquo:{doel}",
                               "soort": "cas", "herkomst": "Aquo-domeintabel, kolom CASnummer"})
            if k["aquo_via_hand"]:
                randen.append({"van": f"prtr:{k['code']}", "naar": f"aquo:{k['aquo_via_hand']}",
                               "soort": "hand", "herkomst": "handtabel van dit lab"})

    # Ontdubbelen: dezelfde Aquo-code kan via meerdere wegen binnenkomen.
    uniek, gezien = [], set()
    for n in knopen:
        if n["id"] not in gezien:
            gezien.add(n["id"])
            uniek.append(n)

    per_soort: dict[str, int] = {}
    for k in koppelingen:
        per_soort[k["soort"]] = per_soort.get(k["soort"], 0) + 1

    return {
        "beschikbaar": True, "bron": BRON_AQUO, "reden": None,
        "knopen": uniek, "randen": randen,
        "koppelingen": koppelingen,
        "anatomie": anatomie(aquo_pad),
        "aquo_telling": aquo.get("telling") or {},
        "dubbeltelling": dubbeltelling(aquo),
        "telling": {
            "prtr_stoffen": len(koppelingen),
            "via_cas": sum(1 for k in koppelingen if k["aquo_via_cas"]),
            "met_de_hand": sum(1 for k in koppelingen if k["aquo_via_hand"]),
            "alleen_cas": per_soort.get("alleen_cas", 0),
            "alleen_hand": per_soort.get("alleen_hand", 0),
            "cas_en_hand": per_soort.get("cas_en_hand", 0),
            "cas_wijkt_af": per_soort.get("cas_wijkt_af", 0),
            "geen_brug": per_soort.get("geen_brug", 0),
            "somparameters": sum(1 for k in koppelingen if k["som"]),
        },
    }
