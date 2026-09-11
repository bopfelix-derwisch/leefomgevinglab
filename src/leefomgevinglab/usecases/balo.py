"""De twee casussen langs de redeneerlijnen van de BALO-businessarchitectuur.

BALO hanteert één redeneermodel met drie redeneerlijnen. Deze pagina gebruikt er twee:

  * Redeneerlijn 2 — business- en portfolioroute:
        informatiebehoefte → informatiefunctie → generieke bouwsteen → portfolio
  * Redeneerlijn 3 — informatie- en dataroute:
        informatiebehoefte → informatieobject → informatiemodel → register/dataproduct → deling

De waardestroom en de informatiebehoefte vormen het scharnier waar beide lijnen op aansluiten.
Hier zetten we de acht ketenstappen van het Seveso-doelbeeld (/dvth) en het lozingsdoelbeeld
(/lozing) links op redeneerlijn 2 en rechts op redeneerlijn 3, zodat zichtbaar wordt welke
besluiten in beide casussen op dezelfde plek terugkomen.

Bron van de structuur: BALO businessarchitectuur v0.9 (concept, RWS/WVL). De waardestroomcodes,
de gesloten set van negen informatiefuncties en de informatieobjecten komen daaruit. De koppeling
aan de casussen, de statusoordelen over registers en de kosten-batenafweging zijn van dit lab.
"""

REDENEERLIJNEN = {
    2: {"naam": "Redeneerlijn 2 — business en portfolio",
        "route": "informatiebehoefte → informatiefunctie → generieke bouwsteen → portfolio",
        "vraag": "Welke terugkerende informatiehandelingen moeten duurzaam ondersteund worden?"},
    3: {"naam": "Redeneerlijn 3 — informatie en data",
        "route": "informatiebehoefte → informatieobject → informatiemodel → register → deling",
        "vraag": "Welke informatieobjecten, modellen en registers zijn nodig, en wie beheert ze?"},
}

WAARDESTROMEN = [
    {"code": "W1", "naam": "Van beleidsopgave naar uitvoerbare regels, kennis en informatie",
     "kernvraag": "Hoe vertalen we beleid en wetgeving naar uitvoerbare regels, begrippen en "
                  "informatieproducten?"},
    {"code": "W2", "naam": "Van registratie naar ruimtelijke informatiepositie en gebiedsafweging",
     "kernvraag": "Hoe krijgen gegevens waarde voor gebiedsgerichte afweging: wat mag waar, welke "
                  "risico's of beperkingen gelden?"},
    {"code": "W3", "naam": "Van kennisvraag naar gezaghebbend antwoord",
     "kernvraag": "Hoe geven we betrouwbare, actuele en uitlegbare antwoorden op basis van "
                  "gevalideerde bronnen?"},
    {"code": "W4", "naam": "Van initiatief naar oriëntatie, aanvraag of melding",
     "kernvraag": "Hoe weet een initiatiefnemer wat geldt, wat moet worden aangeleverd en via welk "
                  "kanaal?"},
    {"code": "W5", "naam": "Van melding of aanvraag naar besluit en publicatie",
     "kernvraag": "Hoe worden besluiten en publicaties een betrouwbare, herbruikbare bron voor "
                  "registers en publieke informatie?"},
    {"code": "W6", "naam": "Van verplichting naar gegevensaanlevering en betrouwbare registratie",
     "kernvraag": "Hoe maken we van verplicht aangeleverde gegevens betrouwbare, herbruikbare "
                  "registraties?"},
    {"code": "W7", "naam": "Van registratie naar toezicht, risicoanalyse en interventie",
     "kernvraag": "Hoe maken we toezicht en interventie gerichter en informatiegestuurder?"},
    {"code": "W8", "naam": "Van uitvoeringsdata naar beleidsmonitoring en publieke verantwoording",
     "kernvraag": "Wat leren we uit uitvoering en registers, en hoe gebruiken we dat voor beleid?"},
]

# Gesloten set van negen; uitbreiding kan volgens BALO alleen via wijziging van dat hoofdstuk.
INFORMATIEFUNCTIES = [
    {"nr": 1, "naam": "Ontvangen en innemen", "kort": "intake",
     "consolidatie": "hoog", "wat": "Aanvragen, meldingen, aanleveringen en documenten ontvangen."},
    {"nr": 2, "naam": "Valideren en verrijken", "kort": "valideren",
     "consolidatie": "zeer hoog", "wat": "Controleren en standaardiseren vóór registratie of deling."},
    {"nr": 3, "naam": "Registreren en beheren", "kort": "registreren",
     "consolidatie": "hoog", "wat": "Objecten, activiteiten, vergunningen en statussen vastleggen."},
    {"nr": 4, "naam": "Beschikbaar stellen en delen", "kort": "delen",
     "consolidatie": "zeer hoog", "wat": "Gegevens toegankelijk maken voor partners en systemen."},
    {"nr": 5, "naam": "Lokaliseren en ruimtelijk duiden", "kort": "lokaliseren",
     "consolidatie": "hoog", "wat": "Gegevens koppelen aan locatie, gebied of contour."},
    {"nr": 6, "naam": "Analyseren en signaleren", "kort": "analyseren",
     "consolidatie": "middel tot hoog", "wat": "Gegevens combineren tot risico's, patronen en signalen."},
    {"nr": 7, "naam": "Monitoren en verantwoorden", "kort": "monitoren",
     "consolidatie": "hoog", "wat": "Gegevens vertalen naar beleidsinformatie en verantwoording."},
    {"nr": 8, "naam": "Kennis ontsluiten en verklaren", "kort": "kennis",
     "consolidatie": "hoog", "wat": "Gevalideerde kennis, regels en toelichtingen beschikbaar maken."},
    {"nr": 9, "naam": "Terugkoppelen en leren", "kort": "terugkoppelen",
     "consolidatie": "zeer hoog", "wat": "Signalen uit uitvoering terugbrengen naar beleid en registers."},
]

# Registers en voorzieningen die de twee casussen raken, met het oordeel van dit lab.
REGISTERS = {
    "DSO": {"status": "bestaat", "wat": "Omgevingsloket, toepasbare regels, omgevingsdocumenten."},
    "Zaaksysteem (ZGW)": {"status": "bestaat", "wat": "Zaken, documenten en besluiten per organisatie — achter eigen autorisatie."},
    "PDOK / basisregistraties": {"status": "bestaat", "wat": "BAG, BGT, BRK, bestuurlijke gebieden. Open en bevraagbaar."},
    "REV": {"status": "moet om", "wat": "Gevuld via een eigen IMEV-aanleverketen, los van het besluit."},
    "RWS KRW-service": {"status": "bestaat", "wat": "89 rijkswaterlichamen; open WFS. Levert het ontvangende water én daarmee het bevoegd gezag."},
    "CTD Rijkswaterstaat": {"status": "moet om", "wat": "Datavoorziening met kwaliteitslabels; nog geen leverancier aan vergunningverlening."},
    "LVBB / bekendmakingen": {"status": "bestaat", "wat": "Landelijke publicatieroute — tekst, geen objectstructuur."},
    "GIR": {"status": "bestaat", "wat": "Inspectieruimte voor Seveso; gesloten voor iedereen buiten het toezicht."},
    "Meetnet / Aquo": {"status": "bestaat", "wat": "Meetreeksen van het waterlichaam; hangen niet aan de vergunning die ze veroorzaakt."},
    "Register Lozingen": {"status": "bestaat niet", "wat": "Geen landelijk beeld van wie wat waar loost."},
    "Data.OD": {"status": "bestaat niet", "wat": "Datapunt Omgevingsdiensten — initiatief van DCMR en OD De Vallei."},
}


def _s(nr, w, behoefte, functies, objecten, registers, knelpunt=""):
    return {"nr": nr, "w": w, "behoefte": behoefte, "functies": functies,
            "objecten": objecten, "registers": registers, "knelpunt": knelpunt}


CASUSSEN = {
    "dvth": {
        "naam": "MBA Seveso-inrichting", "kort": "Seveso", "pad": "/dvth",
        "samenvatting": "Eén bevoegd gezag, risicocontour om een punt, IMEV als objectmodel, "
                        "landend in het REV.",
        "stappen": [
            _s(1, "W4", "Wat mag hier, en welke gegevens moeten mee?", [1, 8],
               ["Activiteit", "Melding / aanvraag", "Object / inrichting"], ["DSO"]),
            _s(2, "W5", "Welk dossier hoort bij deze aanvraag?", [1, 3],
               ["Melding / aanvraag", "Kennisobject"], ["DSO", "Zaaksysteem (ZGW)"],
               "ZAAK en INFORMATIEOBJECT bestaan alleen achter de autorisatie van één organisatie."),
            _s(3, "W2", "Wat ligt er rond deze locatie?", [5, 4, 2],
               ["Locatie / gebied", "Object / inrichting"], ["PDOK / basisregistraties", "REV", "Data.OD"],
               "Data.OD bestaat niet; elke dienst stelt de contextset zelf samen."),
            _s(4, "W5", "Wat is toelaatbaar, en onder welke voorwaarden?", [6, 5],
               ["Stof / emissie", "Locatie / gebied"], [],
               "De OVERWEGING — de afweging zelf — heeft nergens een register."),
            _s(5, "W5", "Hoe wordt het besluit een herbruikbare bron?", [3, 4],
               ["Vergunning / toestemming", "Activiteit", "Locatie / gebied"],
               ["DSO", "LVBB / bekendmakingen"],
               "STOP/TPOD kent geen toepassingsprofiel voor een vergunningbesluit."),
            _s(6, "W6", "Hoe komt het vergunde beeld betrouwbaar in het register?", [2, 3, 4],
               ["Object / inrichting", "Activiteit", "Stof / emissie"], ["REV"],
               "Aanlevering staat los van het besluit; kwaliteit verschilt per bronhouder."),
            _s(7, "W7", "Waar richten we toezicht op?", [6, 3, 4],
               ["Inspectie / toezichtsignaal", "Object / inrichting"], ["GIR", "REV"],
               "Het vergunde beeld en het toezichtbeeld leven in gescheiden systemen."),
            _s(8, "W7", "Welke interventie past, en wat leren we ervan?", [3, 9],
               ["Maatregel / interventie", "Handhavingsbesluit"],
               ["GIR", "LVBB / bekendmakingen", "REV"],
               "De terugkoppeling van naleving naar het risicobeeld loopt nergens."),
        ],
    },
    "lozing": {
        "naam": "Directe lozing op een rijkswater", "kort": "Lozing", "pad": "/lozing",
        "samenvatting": "Twee bevoegde gezagen, effect stroomafwaarts, Aquo als objectmodel, "
                        "en geen register om in te landen.",
        "stappen": [
            _s(1, "W4", "Welke activiteit is dit, en bij wie hoort hij?", [1, 8],
               ["Activiteit", "Melding / aanvraag"], ["DSO"]),
            _s(2, "W5", "Wie beslist waarover?", [1, 3, 5],
               ["Activiteit", "Locatie / gebied", "Melding / aanvraag"],
               ["DSO", "Zaaksysteem (ZGW)", "PDOK / basisregistraties"],
               "Twee bevoegde gezagen over één fabriek, zonder koppelvlak dat de besluiten afstemt."),
            _s(3, "W2", "Welk water ontvangt dit, en van wie is dat?", [5, 4],
               ["Locatie / gebied", "Object / inrichting"],
               ["RWS KRW-service", "PDOK / basisregistraties", "CTD Rijkswaterstaat"]),
            _s(4, "W5", "Wat mag er in, gezien wat het water aankan?", [6, 5],
               ["Stof / emissie", "Locatie / gebied"], [],
               "De ABM- en immissietoets leunt op aannames over debiet die nergens als dataproduct staan."),
            _s(5, "W5", "Hoe wordt het besluit een herbruikbare bron?", [3, 4],
               ["Vergunning / toestemming", "Stof / emissie", "Locatie / gebied"],
               ["DSO", "LVBB / bekendmakingen"],
               "Zelfde ontbrekende TPOD-profiel als bij Seveso — en hier ook nog uit een ander "
               "objectmodel (Aquo in plaats van IMEV)."),
            _s(6, "W6", "Waar landt het vergunde beeld?", [3, 4],
               ["Object / inrichting", "Stof / emissie", "Vergunning / toestemming"],
               ["Register Lozingen"],
               "Er is geen register. Vrachten per waterlichaam zijn niet optelbaar."),
            _s(7, "W7", "Wordt er nageleefd, en zien we dat?", [6, 7, 4],
               ["Inspectie / toezichtsignaal", "Indicator / rapportageobject"],
               ["Meetnet / Aquo"],
               "Het effect wordt wél gemeten, maar de meetreeks hangt niet aan de vergunning."),
            _s(8, "W7", "Welke interventie past, en wat leren we ervan?", [3, 9],
               ["Maatregel / interventie", "Handhavingsbesluit"],
               ["LVBB / bekendmakingen"],
               "Terugkoppelen kan niet: er is geen register dat het signaal ontvangt."),
        ],
    },
}


def _b(id, titel, vraag, wie, kosten, waarde, functies, registers, bewijs, afweging):
    return {"id": id, "titel": titel, "vraag": vraag, "wie": wie, "kosten": kosten,
            "waarde": waarde, "functies": functies, "registers": registers,
            "bewijs": bewijs, "afweging": afweging}


# kosten en waarde op een schaal 1-3 (laag / midden / hoog)
BESLUITEN = [
    _b("B1", "Toepassingsprofiel voor het vergunningbesluit",
       "Maken we een TPOD-profiel waarmee een besluit zijn eigen gegevens draagt?",
       "Geonovum, IenW, plansysteemleveranciers", 3, 3, [3, 4], ["REV", "Register Lozingen", "DSO"],
       "Beide casussen lopen op precies dezelfde plek vast: STOP/TPOD heeft profielen voor "
       "omgevingsdocumenten, niet voor besluiten. Twee onafhankelijke dossiers, één knelpunt.",
       "Duur en traag — een standaardisatietraject met leveranciers, niet een implementatie. Maar "
       "het is de enige wijziging die in beide ketens tegelijk werkt, en hij maakt alle volgende "
       "besluiten goedkoper."),
    _b("B2", "Het REV vullen uit het besluit in plaats van uit een aparte aanlevering",
       "Bouwen we het REV om van IMEV-aanlevering naar TPOD-native?",
       "RIVM, IenW, bronhouders", 3, 3, [2, 3], ["REV"],
       "In de Seveso-keten komen alle 10 verplichte IMEV-eigenschappen rechtstreeks uit het "
       "geannoteerde besluit; er blijft niets over om apart te leveren. De WFS-check laat zien wat "
       "de huidige route kost: 40 van de 45 REV-lagen ontsluiten een IMEV-verplicht veld niet.",
       "Hoge kosten aan de registerkant, maar het verschil tussen vergund en geregistreerd verdwijnt "
       "— inclusief het kwaliteitsverschil per bronhouder dat nu meetbaar is. Hangt af van B1."),
    _b("B3", "Eén validatieframework voor registeraanlevering",
       "Bouwen we één herbruikbaar validatiemechanisme, met domeinspecifieke regelsets erin?",
       "WVL, registerbeheerders", 2, 3, [2], ["REV", "Register Lozingen", "CTD Rijkswaterstaat"],
       "BALO noemt dit zelf het hoogste consolidatiepotentieel van de negen functies. De WFS-check "
       "in dit lab is precies zo'n framework op één register, en vond daar meteen structurele gaten.",
       "Het mechanisme is generiek, de regels blijven van het domein. Relatief lage kosten, werkt "
       "direct in elk register, en is niet afhankelijk van B1 of B2."),
    _b("B4", "Eerst het registerpatroon, dan pas het register",
       "Stellen we een gemeenschappelijk registerpatroon vast vóórdat we per domein een register "
       "inrichten?",
       "WVL, IenW, domeineigenaren", 2, 3, [3], ["Register Lozingen", "REV"],
       "De lozingscasus vraagt om een register dat niet bestaat. De verleiding is er één te bouwen; "
       "BALO waarschuwt dat een gemeenschappelijk patroon iets anders is dan één database.",
       "Zonder patroon krijgt elk domein zijn eigen register met eigen semantiek — precies het "
       "probleem dat de bronnenkaart nu al laat zien bij VTH-OBJECT, dat door zeven bronnen wordt "
       "beschreven zonder gedeelde sleutel."),
    _b("B5", "Koppelvlak bij een meervoudige aanvraag",
       "Regelen we hoe twee bevoegde gezagen over één initiatief hun besluiten op elkaar afstemmen?",
       "IenW, RWS, VNG, DSO-beheer", 2, 2, [1, 4, 9], ["DSO", "Zaaksysteem (ZGW)"],
       "De lozingscasus valt uiteen in twee besluiten over dezelfde fabriek: de lozing bij de "
       "waterbeheerder, het milieudeel bij de gemeente. Een emissiebeperking in het ene spoor "
       "verandert de vracht in het andere.",
       "Middelgrote kosten, vooral bestuurlijk. De waarde zit in het voorkomen van tegenstrijdige "
       "of dubbele voorschriften — moeilijk te kwantificeren, pijnlijk als het misgaat."),
    _b("B6", "Het terugmeld- en leerpatroon operationeel maken",
       "Maken we van terugkoppeling een werkend patroon in plaats van een pijl op een plaat?",
       "WVL, registerbeheerders, toezichthouders", 2, 3, [9], ["REV", "GIR", "Register Lozingen"],
       "In beide ketens is stap 8 de enige die nergens landt. Wat handhaving constateert, werkt niet "
       "door in het risicobeeld — in geen van beide dossiers.",
       "BALO noemt het consolidatiepotentieel zeer hoog. Het patroon is generiek; de "
       "escalatieroute verschilt per stelsel. Levert direct waarde op zonder B1 of B2 af te wachten."),
    _b("B7", "Context en bevoegd gezag afleiden uit bronnen",
       "Leiden we standaard af wie bevoegd is en wat er in de omgeving ligt, in plaats van het over "
       "te typen?",
       "WVL, uitvoeringsorganisaties", 1, 2, [5, 4], ["RWS KRW-service", "PDOK / basisregistraties"],
       "De lozingsketen doet dit al: een treffer in de KRW-service betekent rijkswater en dus de "
       "minister; PDOK geeft de gemeente. Acht stappen in 0,6 seconde, op open bronnen.",
       "De goedkoopste van alle besluiten, en al bewezen. De waarde is begrensd — het lost geen "
       "registerprobleem op — maar het haalt een foutgevoelige handmatige stap weg."),
]

# De vragen die BALO zelf aan management en portfolio stelt.
BALO_BESLUITEN = [
    {"besluit": "Werkwijze", "vraag": "Gebruiken we de drie sturingslijnen als gezamenlijk kader voor "
                                      "opdracht-, product- en portfoliogesprekken?"},
    {"besluit": "Prioriteit", "vraag": "Welke twee cases en welke twee of drie verbeteronderwerpen "
                                       "pakken we als eerste op?"},
    {"besluit": "Opdrachtgevers", "vraag": "Welke onderwerpen vragen een gesprek met de opdrachtgever "
                                           "voordat WVL capaciteit inzet?"},
    {"besluit": "Eigenaarschap", "vraag": "Wie is verantwoordelijk voor registersturing, "
                                          "datakwaliteit, standaardbeheer en leveranciersmanagement?"},
    {"besluit": "Capaciteit", "vraag": "Welke structurele ruimte is nodig om over opdrachten heen te "
                                       "analyseren en te implementeren?"},
]

SCHAAL = {1: "laag", 2: "midden", 3: "hoog"}


def functie(nr: int) -> dict:
    return next(f for f in INFORMATIEFUNCTIES if f["nr"] == nr)


def waardestroom(code: str) -> dict:
    return next(w for w in WAARDESTROMEN if w["code"] == code)


def dekking_informatiefuncties() -> list:
    """Per informatiefunctie: in welke casussen en stappen komt hij voor?"""
    uit = []
    for f in INFORMATIEFUNCTIES:
        per_casus = {k: [s["nr"] for s in c["stappen"] if f["nr"] in s["functies"]]
                     for k, c in CASUSSEN.items()}
        uit.append({**f, "per_casus": per_casus,
                    "totaal": sum(len(v) for v in per_casus.values()),
                    "in_beide": all(per_casus.values())})
    return uit


def registergebruik() -> list:
    """Per register: status, en in welke casussen en stappen hij voorkomt."""
    uit = []
    for naam, meta in REGISTERS.items():
        per_casus = {k: [s["nr"] for s in c["stappen"] if naam in s["registers"]]
                     for k, c in CASUSSEN.items()}
        uit.append({"naam": naam, **meta, "per_casus": per_casus,
                    "totaal": sum(len(v) for v in per_casus.values())})
    return sorted(uit, key=lambda r: -r["totaal"])


def gedeelde_knelpunten() -> list:
    """Stappen waar beide casussen op hetzelfde punt vastlopen — daar zit de meeste waarde."""
    uit = []
    for nr in range(1, 9):
        knel = {k: next(s["knelpunt"] for s in c["stappen"] if s["nr"] == nr)
                for k, c in CASUSSEN.items()}
        if all(knel.values()):
            uit.append({"stap": nr, "knelpunten": knel})
    return uit


def overzicht() -> dict:
    return {"redeneerlijnen": REDENEERLIJNEN, "waardestromen": WAARDESTROMEN,
            "informatiefuncties": INFORMATIEFUNCTIES, "registers": REGISTERS,
            "casussen": CASUSSEN, "besluiten": BESLUITEN, "balo_besluiten": BALO_BESLUITEN,
            "schaal": SCHAAL, "dekking": dekking_informatiefuncties(),
            "registergebruik": registergebruik(), "gedeelde_knelpunten": gedeelde_knelpunten(),
            "bron": "BALO businessarchitectuur v0.9 (concept, RWS/WVL) — structuur en begrippen. "
                    "Koppeling aan de casussen, statusoordelen en kosten-batenafweging zijn van dit lab."}
