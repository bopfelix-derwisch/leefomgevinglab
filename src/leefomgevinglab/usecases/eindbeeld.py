"""Het eindbeeld: hoe ziet een informatieproduct eruit als de gaten dicht zijn?

Dit hele dossier gaat over wat ontbreekt. Deze module draait het om en laat zien wat je
terugkrijgt als het er wél is — op één traject van de Zandmaas, voor één stof.

**Alles hier is verzonnen, en dat is de bedoeling.** De bedrijfsnamen bestaan niet, de vrachten
zijn gekozen, de meetwaarde is gekozen. Zou dit met echte namen gebeuren, dan stond er een
bewering over een bestaand bedrijf die nergens op berust. Wat hier echt is, is de *vorm*: welke
velden een informatieproduct draagt, welke vraag het beantwoordt, en welke daarvan vandaag al
ingevuld kunnen worden.

**De toets die deze module zichzelf oplegt.** Elk getal is terug te voeren op een aanname in
`AANNAMES`, en elk veld draagt `vandaag`: bestaat het al, of hangt het aan een benoemd gat uit
`GATEN`. Een eindbeeld dat niet laat zien waar het van het heden verschilt, is een plaatje van
een wens.

**De vondst die pas in het eindbeeld zichtbaar wordt** — en de reden dat dit meer is dan een
mooie pagina: de onbenutte vergunde ruimte is op dit traject ruim drie keer zo groot als de
ruimte tot de norm. Zouden alle vergunninghouders hun vergunning volledig benutten, dan wordt de
norm overschreden zonder dat iemand een regel overtreedt. Dat is vandaag niet te zien, omdat de
gemelde vracht en de vergunde vracht niet aan elkaar te knopen zijn.
"""

TRAJECT = {
    "waterlichaam": "NL91ZM",
    "naam": "Zandmaas",
    "traject": "Roermond – Venlo",
    "lengte_km": 34,
    "bevoegd_gezag": "Rijkswaterstaat, namens de minister van Infrastructuur en Waterstaat",
    "periode": "2026",
}

STOF = {"code": "Zn", "naam": "zink", "hoedanigheid": "nf",
        "hoedanigheid_naam": "opgelost na filtratie", "cas": "7440-66-6", "eenheid": "µg/l"}

# Elk getal op de pagina komt hiervandaan. Zonder deze lijst is een synthetisch product een
# verhaal; mét deze lijst is het een doorrekening van uitgesproken keuzes.
AANNAMES = [
    {"id": "debiet", "wat": "jaarafvoer van het traject", "waarde": "250 m³/s",
     "waarom": "orde van grootte van de Maas bij gemiddelde afvoer; de KRW-service levert geen "
               "afvoergegevens"},
    {"id": "gemeten", "wat": "gemeten jaargemiddelde zink, opgelost", "waarde": "6,4 µg/l",
     "waarom": "tussen de werkelijke waarden bij Belfeld (6,37) en Heel (3,70) in, dus van de "
               "juiste orde"},
    {"id": "norm", "wat": "KRW-norm zink, opgeloste fractie", "waarde": "7,8 µg/l",
     "waarom": "dit is géén aanname maar de echte norm uit de KRW-toetsresultaten"},
    {"id": "lozers", "wat": "vier directe lozers en één zuivering", "waarde": "verzonnen namen",
     "waarom": "met echte namen zou hier een bewering over een bestaand bedrijf staan die "
               "nergens op berust"},
    {"id": "verdeling", "wat": "de verdeling over de vier herkomsten",
     "waarde": "12% direct · 19% zuivering · 48% bovenstrooms · 21% diffuus",
     "waarom": "gekozen op een plausibel patroon voor de Limburgse Maas: bovenstrooms domineert, "
               "puntbronnen zijn de minderheid"},
    {"id": "benutting", "wat": "de directe lozers benutten samen 15% van hun vergunning",
     "waarde": "6.100 van 41.000 kg/jaar",
     "waarom": "in de orde van wat E-PRTR bij Sappi laat zien (1,5% voor zink, 10% voor stikstof)"},
]

# Wat er vandaag ontbreekt en wat dicht moet zijn om dit product te kunnen maken. De `id` wordt
# per veld aangehaald, zodat elk vakje op de pagina terugwijst naar zijn eigen lacune.
GATEN = {
    "hoedanigheid": "hoedanigheid als veld in het voorschrift — nu niet te zeggen of een "
                    "vergunde waarde over de totale of de opgeloste fractie gaat",
    "geldigheid": "geldigheidsperiode per voorschrift — nu is een vervallen voorschrift niet "
                  "van een geldend te onderscheiden",
    "identificatie": "kruistabel eMJV ↔ KvK-vestiging — nu wordt een vergunning op naam en "
                     "afstand aan een melding geknoopt",
    "stroomvolgorde": "de bovenstrooms-relatie tussen waterlichamen als brongegeven — nu een "
                      "handgemaakte lijst van dit lab",
    "indirect": "een register van lozingen op het riool — nu valt alles achter de zuivering "
                "buiten beeld",
    "codes": "Aquo-code plus CAS in het voorschrift — nu koppelt een voorschrift op zijn "
             "Nederlandse stofnaam",
    "landelijk": "een landelijk register van lozingen — nu bestaat het alleen voor de Maas, "
                 "als regionaal initiatief",
    "metingen": "een machine-ingang op de meetwaarden — nu een handmatige momentopname, de "
                "WKP-module komt in 2027",
}

SECONDEN_PER_JAAR = 31_536_000
DEBIET_M3_S = 250.0
GEMETEN_UG_L = 6.4
NORM_UG_L = 7.8


def _vracht_kg(concentratie_ug_l: float) -> float:
    """µg/l maal m³/s naar kg per jaar."""
    return concentratie_ug_l * DEBIET_M3_S * SECONDEN_PER_JAAR / 1_000_000.0


# De directe lozers op dit traject. `vergund` en `gemeld` staan los van elkaar, want dat is
# precies het paar dat vandaag niet te leggen is.
LOZERS = [
    {"naam": "Papierfabriek De Maasoever B.V.", "plaats": "Roermond", "kvk": "000099000011",
     "emjv": "000900011", "vergund_kg": 21000.0, "gemeld_kg": 2900.0,
     "verloopt": "2031-04-01", "km": 4.2},
    {"naam": "Galvanisch Bedrijf Venlo-Zuid B.V.", "plaats": "Venlo", "kvk": "000099000022",
     "emjv": "000900022", "vergund_kg": 2600.0, "gemeld_kg": 2130.0,
     "verloopt": "2027-06-30", "km": 29.8},
    {"naam": "Koeltechniek Maasdal B.V.", "plaats": "Beesel", "kvk": "000099000033",
     "emjv": "000900033", "vergund_kg": 14800.0, "gemeld_kg": 760.0,
     "verloopt": "2027-02-15", "km": 18.5},
    {"naam": "Metaalrecycling Swalmen B.V.", "plaats": "Swalmen", "kvk": "000099000044",
     "emjv": "000900044", "vergund_kg": 2600.0, "gemeld_kg": 310.0,
     "verloopt": "2034-09-01", "km": 11.0},
]

# De zuivering, en wat er achter zit. Dit blok is het hart van het eindbeeld: vandaag is de RWZI
# één anonieme post, en wie er op loost staat in geen enkel register.
ZUIVERING = {
    "naam": "RWZI Maasdal", "plaats": "Roermond", "km": 7.4,
    "effluent_kg": 9400.0,
    "vergund_kg": None,          # de vergunning begrenst CZV, BZV, N, P en zwevende stof
    "aangesloten": 23,
    # `bedrijf` scheidt de aanwijsbare lozers van de rest. Zonder dat onderscheid telt
    # "de drie grootste" de huishoudens mee, en dan gaat een uitspraak over bedrijven over iets
    # anders dan zij beweert.
    "indirecte_lozers": [
        {"naam": "Oppervlaktebehandeling Roerdal B.V.", "kg": 3100.0,
         "regime": "vergunning", "bedrijf": True},
        {"naam": "Wasserij Midden-Limburg B.V.", "kg": 1850.0,
         "regime": "maatwerkvoorschrift", "bedrijf": True},
        {"naam": "Autodemontage Leudal B.V.", "kg": 1240.0,
         "regime": "algemene regels", "bedrijf": True},
        {"naam": "overige 20 bedrijven, elk onder de drempel", "kg": 1010.0,
         "regime": "algemene regels", "bedrijf": False},
        {"naam": "huishoudens en afstromend hemelwater", "kg": 2200.0,
         "regime": "zorgplicht", "bedrijf": False},
    ],
}

HERKOMSTEN = [
    {"id": "direct", "naam": "Directe lozingen", "kg": 6100.0, "kleur": "mag",
     "vandaag": "deels", "gat": "identificatie",
     "wat": "vier vergunde lozers; de gemelde vracht komt uit het milieujaarverslag"},
    {"id": "zuivering", "naam": "Effluent RWZI Maasdal", "kg": 9400.0, "kleur": "gemeld",
     "vandaag": "nee", "gat": "indirect",
     "wat": "23 aangesloten bedrijven plus huishoudens; vandaag één anonieme post"},
    {"id": "bovenstrooms", "naam": "Bovenstrooms (België en Grensmaas)", "kg": 24000.0,
     "kleur": "gebeurt", "vandaag": "deels", "gat": "stroomvolgorde",
     "wat": "wat bij Eijsden de grens al over komt, plus de Grensmaas"},
    {"id": "diffuus", "naam": "Diffuus", "kg": 11000.0, "kleur": "dim",
     "vandaag": "nee", "gat": "landelijk",
     "wat": "afspoeling, bouwmetalen, atmosferische depositie, erosie"},
]

SIGNALEN = [
    {"soort": "aflopend", "kop": "Twee vergunningen verlopen binnen twaalf maanden",
     "wat": "Galvanisch Bedrijf Venlo-Zuid (30-06-2027) en Koeltechniek Maasdal (15-02-2027). "
            "Samen 17.400 kg vergunde zinkvracht — het natuurlijke moment om de "
            "vergunde ruimte terug te brengen naar wat feitelijk wordt gebruikt.",
     "gat": "geldigheid"},
    {"soort": "benutting", "kop": "Eén lozer zit op 82 procent van zijn vergunning",
     "wat": "Galvanisch Bedrijf Venlo-Zuid meldt 2.130 van 2.600 kg. Bij de andere drie ligt de "
            "benutting onder de 15 procent. Dit is de enige waar een toename van de productie "
            "direct tegen de vergunning aan loopt.",
     "gat": "identificatie"},
    {"soort": "ongedekt", "kop": "Drie gemeten stoffen staan in geen enkele vergunning",
     "wat": "PFOA, PFOS en melamine worden op dit traject gemeten maar komen in geen van de vier "
            "vergunningen voor — en melamine kent de Aquo-domeintabel niet eens.",
     "gat": "codes"},
    {"soort": "indirect", "kop": "Drie indirecte lozers verklaren 70 procent van het effluent",
     "wat": "Van de 9.400 kg zink uit de zuivering komt 6.190 kg van drie bedrijven, waarvan er "
            "één onder algemene regels valt en dus geen vergunning heeft. Vandaag is dat "
            "onzichtbaar.",
     "gat": "indirect"},
]


def balans() -> dict:
    """De stofbalans: wat is er gemeten, en waar komt het vandaan?"""
    gemeten_kg = _vracht_kg(GEMETEN_UG_L)
    verdeeld = sum(h["kg"] for h in HERKOMSTEN)
    herkomsten = [{**h, "pct": round(100 * h["kg"] / verdeeld, 1),
                   "gat_tekst": GATEN.get(h["gat"])} for h in HERKOMSTEN]
    return {
        "gemeten_ug_l": GEMETEN_UG_L, "gemeten_kg": round(gemeten_kg),
        "norm_ug_l": NORM_UG_L,
        "verdeeld_kg": round(verdeeld),
        # Het verschil tussen de gemeten vracht en de som van de herkomsten is geen restpost die
        # je wegpoetst: hij zegt hoe goed de balans sluit, en dat is zelf een kwaliteitsoordeel.
        "sluitverschil_kg": round(gemeten_kg - verdeeld),
        "sluitverschil_pct": round(100 * (gemeten_kg - verdeeld) / gemeten_kg, 1),
        "herkomsten": herkomsten,
    }


def ruimte() -> dict:
    """De ruimte tot de norm, en het stuk vergunde ruimte dat stilligt.

    Hier komt de bevinding uit die zonder eindbeeld niet te zien is: de onbenutte vergunde
    ruimte is groter dan de ruimte tot de norm. Niemand overtreedt iets, en toch kan de norm
    worden overschreden zonder dat er een besluit aan te pas komt.
    """
    vrij_kg = _vracht_kg(NORM_UG_L - GEMETEN_UG_L)
    vergund = sum(l["vergund_kg"] for l in LOZERS)
    gemeld = sum(l["gemeld_kg"] for l in LOZERS)
    onbenut = vergund - gemeld
    return {
        "vrij_kg": round(vrij_kg),
        "vergund_kg": round(vergund), "gemeld_kg": round(gemeld),
        "onbenut_kg": round(onbenut),
        "benut_pct": round(100 * gemeld / vergund, 1),
        "onbenut_maal_vrij": round(onbenut / vrij_kg, 1),
        "past_binnen_de_norm": onbenut <= vrij_kg,
        "les": ("De vergunde ruimte die vandaag stilligt is "
                f"{round(onbenut / vrij_kg, 1)} keer zo groot als de ruimte tot de norm. Zouden "
                "alle vier de houders hun vergunning volledig benutten, dan wordt de norm "
                "overschreden zonder dat iemand een regel overtreedt — en zonder dat er een "
                "besluit aan te pas komt."),
    }


def lozers() -> list[dict]:
    """De directe lozers, met vergund en gemeld naast elkaar."""
    uit = []
    for l in LOZERS:
        benut = 100 * l["gemeld_kg"] / l["vergund_kg"] if l["vergund_kg"] else None
        uit.append({**l, "benut_pct": round(benut, 1) if benut is not None else None,
                    "onbenut_kg": round(l["vergund_kg"] - l["gemeld_kg"])})
    return sorted(uit, key=lambda x: x["km"])


def zuivering() -> dict:
    """Wat er achter de zuivering zit — het blok dat vandaag niet bestaat."""
    delen = sorted(ZUIVERING["indirecte_lozers"], key=lambda x: -x["kg"])
    totaal = sum(d["kg"] for d in delen)
    bedrijven = [d for d in delen if d["bedrijf"]][:3]
    top3 = sum(d["kg"] for d in bedrijven)
    return {**ZUIVERING, "indirecte_lozers": [
        {**d, "pct": round(100 * d["kg"] / totaal, 1)} for d in delen],
        "som_kg": round(totaal),
        "top3_bedrijven": [d["naam"] for d in bedrijven],
        "top3_kg": round(top3), "top3_pct": round(100 * top3 / totaal, 1),
        "sluit_aan_op_effluent": abs(totaal - ZUIVERING["effluent_kg"]) < 1.0}


def velden() -> list[dict]:
    """Per veld in het product: kan dit vandaag al, en zo niet, welk gat zit ertussen?

    Dit is de kern van de pagina. Een eindbeeld zonder deze kolom is een wens; mét deze kolom is
    het een opdrachtenlijst.
    """
    return [
        {"veld": "Gemeten vracht per stof", "vandaag": "ja",
         "hoe": "Waterkwaliteitsportaal — maar als handmatige momentopname", "gat": "metingen"},
        {"veld": "Norm met hoedanigheid", "vandaag": "ja",
         "hoe": "KRW-toetsresultaten; per meetpunt gecorrigeerd voor biobeschikbaarheid",
         "gat": None},
        {"veld": "Vergunde vracht per lozer", "vandaag": "deels",
         "hoe": "Atlas voor een Schone Maas; 85% van de voorschriften is te codificeren",
         "gat": "codes"},
        {"veld": "Vergunde waarde: totaal of opgelost?", "vandaag": "nee",
         "hoe": "staat in geen enkel voorschrift", "gat": "hoedanigheid"},
        {"veld": "Geldt dit voorschrift nog?", "vandaag": "nee",
         "hoe": "geen enkel voorschrift draagt een geldigheidsperiode", "gat": "geldigheid"},
        {"veld": "Gemelde vracht naast de vergunde", "vandaag": "deels",
         "hoe": "E-PRTR, gekoppeld op naam en afstand — 1 van 22 lukt", "gat": "identificatie"},
        {"veld": "Wie loost er op de zuivering?", "vandaag": "nee",
         "hoe": "er is geen register van indirecte lozingen", "gat": "indirect"},
        {"veld": "Wat ligt bovenstrooms?", "vandaag": "deels",
         "hoe": "stroomgebieddistrict uit het WKP; de volgorde erbinnen is van dit lab",
         "gat": "stroomvolgorde"},
        {"veld": "Hetzelfde buiten het Maasstroomgebied", "vandaag": "nee",
         "hoe": "de Atlas is een regionaal initiatief", "gat": "landelijk"},
    ]


def _nl(getal: float) -> str:
    """Een getal met een punt als duizendtalscheiding, zoals Nederlands het schrijft.

    Via de Engelse opmaak en dan de komma vervangen gaat mis zodra er ook een zinskomma in de
    tekst staat; dat gebeurde hier.
    """
    return f"{getal:,.0f}".replace(",", ".")


def _signalen() -> list[dict]:
    """De signalen, met de afgeleide getallen ingevuld waar ze berekend horen te worden."""
    z = zuivering()
    uit = []
    for s in SIGNALEN:
        s = dict(s)
        if s["soort"] == "indirect":
            zonder = [d for d in z["indirecte_lozers"]
                      if d["bedrijf"] and d["regime"] == "algemene regels"]
            s["kop"] = (f"Drie indirecte lozers verklaren {z['top3_pct']:.0f} procent van het "
                        "effluent")
            s["wat"] = (f"Van de {_nl(z['effluent_kg'])} kg zink uit de zuivering komt "
                        f"{_nl(z['top3_kg'])} kg van drie bedrijven, waarvan er {len(zonder)} "
                        "onder algemene regels valt en dus geen vergunning heeft. Vandaag is dat "
                        "onzichtbaar.")
        uit.append({**s, "gat_tekst": GATEN.get(s["gat"])})
    return uit


def product() -> dict:
    """Het hele informatieproduct, met zijn aannames en zijn afstand tot vandaag."""
    v = velden()
    tel = {"ja": 0, "deels": 0, "nee": 0}
    for x in v:
        tel[x["vandaag"]] += 1
    return {
        "synthetisch": True,
        "waarschuwing": ("Alles op deze pagina is verzonnen: de bedrijfsnamen bestaan niet, de "
                         "vrachten zijn gekozen. Echt is de vórm van het product en de lijst "
                         "met gaten die dicht moeten om het te kunnen maken."),
        "traject": TRAJECT, "stof": STOF,
        "aannames": AANNAMES, "gaten": GATEN,
        "balans": balans(), "ruimte": ruimte(),
        "lozers": lozers(), "zuivering": zuivering(),
        "signalen": _signalen(),
        "velden": v, "veld_telling": tel,
    }
