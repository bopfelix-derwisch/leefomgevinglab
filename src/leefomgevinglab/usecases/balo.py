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


STATUS_BEHOEFTE = {
    "voldaan": "De informatie is er, op tijd en bruikbaar.",
    "deels": "De informatie is er, maar niet vindbaar, niet compleet of niet op tijd.",
    "niet": "De informatie ontstaat wel, maar wordt nergens vastgelegd of gedeeld.",
}


def _s(nr, w, behoefte, functies, objecten, registers, knelpunt="",
       wie="", waarde="", zonder="", status="voldaan", id=""):
    """Eén ketenstap. De informatiebehoefte is het scharnier: links de informatiefuncties
    die haar bedienen, rechts de objecten en registers die haar voeden."""
    return {"nr": nr, "w": w, "behoefte": behoefte, "functies": functies,
            "objecten": objecten, "registers": registers, "knelpunt": knelpunt,
            "id": id, "wie": wie, "waarde": waarde, "zonder": zonder, "status": status}


CASUSSEN = {
    "dvth": {
        "naam": "MBA Seveso-inrichting", "kort": "Seveso", "pad": "/dvth",
        "samenvatting": "Eén bevoegd gezag, risicocontour om een punt, IMEV als objectmodel, "
                        "landend in het REV.",
        "stappen": [
            _s(1, "W4", "Wat mag hier, en welke gegevens moeten mee?", [1, 8],
               ["Activiteit", "Melding / aanvraag", "Object / inrichting"], ["DSO"],
               id="dvth-1", wie="Initiatiefnemer en zijn adviseur", status="voldaan",
               waarde="Een complete aanvraag in één keer. Dat scheelt aanvullingsverzoeken en "
                      "voorkomt dat het bevoegd gezag op halve informatie begint te rekenen.",
               zonder="Aanvragen komen onvolledig binnen, de doorlooptijd loopt op en de "
                      "beoordeling start op drijfzand."),
            _s(2, "W5", "Welk dossier hoort bij deze aanvraag?", [1, 3],
               ["Melding / aanvraag", "Kennisobject"], ["DSO", "Zaaksysteem (ZGW)"],
               "ZAAK en INFORMATIEOBJECT bestaan alleen achter de autorisatie van één organisatie.",
               id="dvth-2", wie="Behandelaar bij de omgevingsdienst", status="deels",
               waarde="Alle stukken bij elkaar, met termijn en status bewaakt — één plek waar de "
                      "behandelaar ziet waar de zaak staat.",
               zonder="Ketenpartners zien niets. Wie van buiten de organisatie moet meekijken, "
                      "krijgt een kopie per mail of niets."),
            _s(3, "W2", "Wat ligt er rond deze locatie?", [5, 4, 2],
               ["Locatie / gebied", "Object / inrichting"],
               ["PDOK / basisregistraties", "REV", "Data.OD"],
               "Data.OD bestaat niet; elke dienst stelt de contextset zelf samen.",
               id="dvth-3", wie="Vergunningverlener en adviseur externe veiligheid", status="deels",
               waarde="De beoordeling kent de omgeving: 13 gifwolkaandachtsgebieden en 4266 panden "
                      "binnen een kilometer, in 1,4 seconde opgehaald in plaats van handmatig "
                      "uitgezocht.",
               zonder="Elke dienst zoekt het zelf bij elkaar, met eigen bronnen en eigen peildatum. "
                      "Dezelfde vraag levert bij twee diensten een ander antwoord op."),
            _s(4, "W5", "Wat is toelaatbaar, en onder welke voorwaarden?", [6, 5],
               ["Stof / emissie", "Locatie / gebied"], [],
               "De OVERWEGING — de afweging zelf — heeft nergens een register.",
               id="dvth-4", wie="Vergunningverlener en bevoegd gezag", status="niet",
               waarde="De afweging is navolgbaar: wat is getoetst, met welke uitkomst, en welk "
                      "voorschrift volgt eruit. Ook jaren later nog.",
               zonder="De motivering zit in een pdf. Toezicht kan niet zien wáárom iets vergund is, "
                      "en een volgende aanvraag kan er niet op voortbouwen."),
            _s(5, "W5", "Hoe wordt het besluit een herbruikbare bron?", [3, 4],
               ["Vergunning / toestemming", "Activiteit", "Locatie / gebied"],
               ["DSO", "LVBB / bekendmakingen"],
               "STOP/TPOD kent geen toepassingsprofiel voor een vergunningbesluit.",
               id="dvth-5", wie="Registerbeheerder, toezichthouder, publiek", status="niet",
               waarde="Het besluit draagt zijn eigen gegevens: 10 van de 10 verplichte "
                      "IMEV-eigenschappen zitten erin. Eén bron voor vergunning, register én publicatie.",
               zonder="Het besluit is tekst. Alles wat erin staat moet elders opnieuw worden "
                      "ingevoerd, met alle overtypfouten van dien."),
            _s(6, "W6", "Hoe komt het vergunde beeld betrouwbaar in het register?", [2, 3, 4],
               ["Object / inrichting", "Activiteit", "Stof / emissie"], ["REV"],
               "Aanlevering staat los van het besluit; kwaliteit verschilt per bronhouder.",
               id="dvth-6", wie="Registerbeheerder en bronhouders", status="deels",
               waarde="Wat vergund is en wat geregistreerd staat zijn hetzelfde — en dus is het "
                      "register bruikbaar voor omgevingsbesluiten van anderen.",
               zonder="Dubbele registratie met kwaliteitsverschil per bronhouder: 40 van de 45 "
                      "REV-lagen ontsluiten een IMEV-verplicht veld niet."),
            _s(7, "W7", "Waar richten we toezicht op?", [6, 3, 4],
               ["Inspectie / toezichtsignaal", "Object / inrichting"], ["GIR", "REV"],
               "Het vergunde beeld en het toezichtbeeld leven in gescheiden systemen.",
               id="dvth-7", wie="Toezichthouder en inspectieteam", status="deels",
               waarde="De inspectie bereidt voor op het actuele risicobeeld en kan handhaven op het "
                      "voorschrift dat erbij hoort.",
               zonder="Toezicht werkt uit een eigen dossier; het vergunde beeld moet er handmatig "
                      "bij worden gezocht, per bedrijf opnieuw."),
            _s(8, "W7", "Welke interventie past, en wat leren we ervan?", [3, 9],
               ["Maatregel / interventie", "Handhavingsbesluit"],
               ["GIR", "LVBB / bekendmakingen", "REV"],
               "De terugkoppeling van naleving naar het risicobeeld loopt nergens.",
               id="dvth-8", wie="Handhaver, registerbeheerder, beleid", status="niet",
               waarde="Naleefgedrag werkt door in het risicobeeld, en herhaald gedrag wordt "
                      "zichtbaar over bedrijven en diensten heen.",
               zonder="Elke inspectie begint blanco. Wat elders al is geconstateerd blijft "
                      "onzichtbaar, en beleid hoort het nooit."),
        ],
    },
    "lozing": {
        "naam": "Directe lozing op een rijkswater", "kort": "Lozing", "pad": "/lozing",
        "samenvatting": "Twee bevoegde gezagen, effect stroomafwaarts, Aquo als objectmodel, "
                        "en geen register om in te landen.",
        "stappen": [
            _s(1, "W4", "Welke activiteit is dit, en bij wie hoort hij?", [1, 8],
               ["Activiteit", "Melding / aanvraag"], ["DSO"],
               "Of de lozing direct of indirect is bepaalt het bevoegd gezag — en dat blijkt pas uit "
               "de locatie.",
               id="lozing-1", wie="Lozer en zijn adviseur", status="deels",
               waarde="De aanvrager komt bij het juiste loket en het juiste bevoegd gezag, ook als "
                      "zijn initiatief in twee besluiten uiteenvalt.",
               zonder="De aanvraag belandt bij de verkeerde partij of valt tussen twee gezagen in, "
                      "en de termijn loopt ondertussen door."),
            _s(2, "W5", "Wie beslist waarover?", [1, 3, 5],
               ["Activiteit", "Locatie / gebied", "Melding / aanvraag"],
               ["DSO", "Zaaksysteem (ZGW)", "PDOK / basisregistraties"],
               "Twee bevoegde gezagen over één fabriek, zonder koppelvlak dat de besluiten afstemt.",
               id="lozing-2", wie="Beide bevoegde gezagen en de lozer", status="niet",
               waarde="Beide besluiten kennen elkaar: een emissiebeperking in het milieuspoor werkt "
                      "door in de lozingsvracht, en andersom.",
               zonder="Twee besluiten over één fabriek die elkaar niet kennen — met kans op "
                      "tegenstrijdige of dubbele voorschriften."),
            _s(3, "W2", "Welk water ontvangt dit, en van wie is dat?", [5, 4],
               ["Locatie / gebied", "Object / inrichting"],
               ["RWS KRW-service", "PDOK / basisregistraties", "CTD Rijkswaterstaat"],
               id="lozing-3", wie="Waterbeheerder en vergunningverlener", status="voldaan",
               waarde="Het bevoegd gezag volgt uit de data in plaats van uit een aanname: IJssel, "
                      "NL93_IJSSEL, rijkswater, dus de minister. In 0,6 seconde, uit open bronnen.",
               zonder="Het bevoegd gezag wordt overgetypt uit een eerder dossier, met kans dat het "
                      "hele traject bij de verkeerde partij start."),
            _s(4, "W5", "Wat mag er in, gezien wat het water aankan?", [6, 5],
               ["Stof / emissie", "Locatie / gebied"], [],
               "De ABM- en immissietoets leunt op aannames over debiet die nergens als dataproduct staan.",
               id="lozing-4", wie="Vergunningverlener en waterbeheerder", status="niet",
               waarde="De toets is reproduceerbaar en herbruikbaar bij de volgende lozer op hetzelfde "
                      "water — inclusief wat er al vergund is.",
               zonder="Elke toets rekent met eigen aannames. Cumulatie met andere lozers op hetzelfde "
                      "waterlichaam blijft structureel buiten beeld."),
            _s(5, "W5", "Hoe wordt het besluit een herbruikbare bron?", [3, 4],
               ["Vergunning / toestemming", "Stof / emissie", "Locatie / gebied"],
               ["DSO", "LVBB / bekendmakingen"],
               "Zelfde ontbrekende TPOD-profiel als bij Seveso — en hier ook nog uit een ander "
               "objectmodel (Aquo in plaats van IMEV).",
               id="lozing-5", wie="Toezichthouder, waterbeheerder, publiek", status="niet",
               waarde="Emissiegrenswaarde en meetverplichting staan machineleesbaar in het besluit — "
                      "precies de twee dingen waarop later gehandhaafd wordt.",
               zonder="Grenswaarde en meetplicht staan in lopende tekst. Een toezichthouder moet ze "
                      "eruit lezen en overnemen voordat hij iets kan controleren."),
            _s(6, "W6", "Waar landt het vergunde beeld?", [3, 4],
               ["Object / inrichting", "Stof / emissie", "Vergunning / toestemming"],
               ["Register Lozingen"],
               "Er is geen register. Vrachten per waterlichaam zijn niet optelbaar.",
               id="lozing-6", wie="Waterbeheerder, beleid, publiek", status="niet",
               waarde="Vrachten per waterlichaam worden optelbaar en zeer zorgwekkende stoffen zijn "
                      "te volgen over lozers heen — de basis voor KRW-verantwoording.",
               zonder="Na bekendmaking blijft er geen optelbaar beeld over van wie er op de IJssel "
                      "loost. De vraag 'hoeveel PFOA gaat er dit jaar in' is niet te beantwoorden."),
            _s(7, "W7", "Wordt er nageleefd, en zien we dat?", [6, 7, 4],
               ["Inspectie / toezichtsignaal", "Indicator / rapportageobject"],
               ["Meetnet / Aquo"],
               "Het effect wordt wél gemeten, maar de meetreeks hangt niet aan de vergunning.",
               id="lozing-7", wie="Toezichthouder en waterbeheerder", status="deels",
               waarde="Meetreeks en vergunde grenswaarde naast elkaar: een overschrijding is direct "
                      "zichtbaar in plaats van pas bij de jaarrapportage.",
               zonder="Het effect wordt gemeten, maar niemand legt de meting naast de grenswaarde die "
                      "hem had moeten begrenzen."),
            _s(8, "W7", "Welke interventie past, en wat leren we ervan?", [3, 9],
               ["Maatregel / interventie", "Handhavingsbesluit"],
               ["LVBB / bekendmakingen"],
               "Terugkoppelen kan niet: er is geen register dat het signaal ontvangt.",
               id="lozing-8", wie="Handhaver, waterbeheerder, beleid", status="niet",
               waarde="Wat handhaving constateert werkt door in het beeld van het waterlichaam, en "
                      "in de beoordeling van de volgende aanvraag erop.",
               zonder="De interventie eindigt bij het besluit. Het watersysteem waar het om begonnen "
                      "was, weet van niets."),
        ],
    },
}


def _b(id, titel, vraag, wie, kosten, waarde, functies, registers, bewijs, afweging, lost_op=()):
    """`lost_op` verwijst naar de informatiebehoeften die dit besluit bedient — daar zit de waarde."""
    return {"id": id, "titel": titel, "vraag": vraag, "wie": wie, "kosten": kosten,
            "waarde": waarde, "functies": functies, "registers": registers,
            "bewijs": bewijs, "afweging": afweging, "lost_op": list(lost_op)}


# kosten en waarde op een schaal 1-3 (laag / midden / hoog)
BESLUITEN = [
    _b("B1", "Toepassingsprofiel voor het vergunningbesluit",
       "Maken we een TPOD-profiel waarmee een besluit zijn eigen gegevens draagt?",
       "Geonovum, IenW, plansysteemleveranciers", 3, 3, [3, 4], ["REV", "Register Lozingen", "DSO"],
       "Beide casussen lopen op precies dezelfde plek vast: STOP/TPOD heeft profielen voor "
       "omgevingsdocumenten, niet voor besluiten. Twee onafhankelijke dossiers, één knelpunt.",
       "Duur en traag — een standaardisatietraject met leveranciers, niet een implementatie. Maar "
       "het is de enige wijziging die in beide ketens tegelijk werkt, en hij maakt alle volgende "
       "besluiten goedkoper.",
       lost_op=['dvth-5', 'lozing-5']),
    _b("B2", "Het REV vullen uit het besluit in plaats van uit een aparte aanlevering",
       "Bouwen we het REV om van IMEV-aanlevering naar TPOD-native?",
       "RIVM, IenW, bronhouders", 3, 3, [2, 3], ["REV"],
       "In de Seveso-keten komen alle 10 verplichte IMEV-eigenschappen rechtstreeks uit het "
       "geannoteerde besluit; er blijft niets over om apart te leveren. De WFS-check laat zien wat "
       "de huidige route kost: 40 van de 45 REV-lagen ontsluiten een IMEV-verplicht veld niet.",
       "Hoge kosten aan de registerkant, maar het verschil tussen vergund en geregistreerd verdwijnt "
       "— inclusief het kwaliteitsverschil per bronhouder dat nu meetbaar is. Hangt af van B1.",
       lost_op=['dvth-6', 'dvth-7']),
    _b("B3", "Eén validatieframework voor registeraanlevering",
       "Bouwen we één herbruikbaar validatiemechanisme, met domeinspecifieke regelsets erin?",
       "WVL, registerbeheerders", 2, 3, [2], ["REV", "Register Lozingen", "CTD Rijkswaterstaat"],
       "BALO noemt dit zelf het hoogste consolidatiepotentieel van de negen functies. De WFS-check "
       "in dit lab is precies zo'n framework op één register, en vond daar meteen structurele gaten.",
       "Het mechanisme is generiek, de regels blijven van het domein. Relatief lage kosten, werkt "
       "direct in elk register, en is niet afhankelijk van B1 of B2.",
       lost_op=['dvth-6', 'lozing-6']),
    _b("B4", "Eerst het registerpatroon, dan pas het register",
       "Stellen we een gemeenschappelijk registerpatroon vast vóórdat we per domein een register "
       "inrichten?",
       "WVL, IenW, domeineigenaren", 2, 3, [3], ["Register Lozingen", "REV"],
       "De lozingscasus vraagt om een register dat niet bestaat. De verleiding is er één te bouwen; "
       "BALO waarschuwt dat een gemeenschappelijk patroon iets anders is dan één database.",
       "Zonder patroon krijgt elk domein zijn eigen register met eigen semantiek — precies het "
       "probleem dat de bronnenkaart nu al laat zien bij VTH-OBJECT, dat door zeven bronnen wordt "
       "beschreven zonder gedeelde sleutel.",
       lost_op=['lozing-6', 'dvth-6']),
    _b("B5", "Koppelvlak bij een meervoudige aanvraag",
       "Regelen we hoe twee bevoegde gezagen over één initiatief hun besluiten op elkaar afstemmen?",
       "IenW, RWS, VNG, DSO-beheer", 2, 2, [1, 4, 9], ["DSO", "Zaaksysteem (ZGW)"],
       "De lozingscasus valt uiteen in twee besluiten over dezelfde fabriek: de lozing bij de "
       "waterbeheerder, het milieudeel bij de gemeente. Een emissiebeperking in het ene spoor "
       "verandert de vracht in het andere.",
       "Middelgrote kosten, vooral bestuurlijk. De waarde zit in het voorkomen van tegenstrijdige "
       "of dubbele voorschriften — moeilijk te kwantificeren, pijnlijk als het misgaat.",
       lost_op=['lozing-1', 'lozing-2']),
    _b("B6", "Het terugmeld- en leerpatroon operationeel maken",
       "Maken we van terugkoppeling een werkend patroon in plaats van een pijl op een plaat?",
       "WVL, registerbeheerders, toezichthouders", 2, 3, [9], ["REV", "GIR", "Register Lozingen"],
       "In beide ketens is stap 8 de enige die nergens landt. Wat handhaving constateert, werkt niet "
       "door in het risicobeeld — in geen van beide dossiers.",
       "BALO noemt het consolidatiepotentieel zeer hoog. Het patroon is generiek; de "
       "escalatieroute verschilt per stelsel. Levert direct waarde op zonder B1 of B2 af te wachten.",
       lost_op=['dvth-8', 'lozing-8', 'dvth-7']),
    _b("B7", "Context en bevoegd gezag afleiden uit bronnen",
       "Leiden we standaard af wie bevoegd is en wat er in de omgeving ligt, in plaats van het over "
       "te typen?",
       "WVL, uitvoeringsorganisaties", 1, 2, [5, 4], ["RWS KRW-service", "PDOK / basisregistraties"],
       "De lozingsketen doet dit al: een treffer in de KRW-service betekent rijkswater en dus de "
       "minister; PDOK geeft de gemeente. Acht stappen in 0,6 seconde, op open bronnen.",
       "De goedkoopste van alle besluiten, en al bewezen. De waarde is begrensd — het lost geen "
       "registerprobleem op — maar het haalt een foutgevoelige handmatige stap weg.",
       lost_op=['dvth-3', 'lozing-3']),
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


def behoeften() -> list:
    """Alle informatiebehoeften uit beide casussen, plat, met hun plek in de cyclus."""
    uit = []
    for k, c in CASUSSEN.items():
        for s in c["stappen"]:
            uit.append({"id": s["id"], "casus": k, "casus_kort": c["kort"], "stap": s["nr"],
                        "w": s["w"], "waardestroom": waardestroom(s["w"])["naam"],
                        "vraag": s["behoefte"], "wie": s["wie"], "waarde": s["waarde"],
                        "zonder": s["zonder"], "status": s["status"],
                        "functies": s["functies"], "registers": s["registers"]})
    return uit


def cyclus() -> list:
    """Per waardestroom: welke informatiebehoeften spelen daar, en worden ze bediend?

    Dit is het antwoord op de vraag waar in de cyclus de informatiebehoefte zit — inclusief de
    waardestromen die door deze twee casussen helemaal niet geraakt worden.
    """
    alle = behoeften()
    uit = []
    for w in WAARDESTROMEN:
        hier = [b for b in alle if b["w"] == w["code"]]
        tel = {s: sum(1 for b in hier if b["status"] == s) for s in STATUS_BEHOEFTE}
        uit.append({**w, "behoeften": hier, "aantal": len(hier), "per_status": tel,
                    "geraakt": bool(hier)})
    return uit


def waardeoverzicht() -> dict:
    """De kern in cijfers: hoeveel informatiebehoeften, en hoeveel daarvan worden bediend."""
    alle = behoeften()
    c = cyclus()
    return {"totaal": len(alle),
            "per_status": {s: sum(1 for b in alle if b["status"] == s) for s in STATUS_BEHOEFTE},
            "waardestromen_geraakt": sum(1 for w in c if w["geraakt"]),
            "waardestromen_totaal": len(WAARDESTROMEN),
            "niet_geraakt": [w["code"] for w in c if not w["geraakt"]],
            "onvervuld": [b["id"] for b in alle if b["status"] != "voldaan"]}


def besluitwaarde() -> list:
    """Per besluit: welke informatiebehoeften het bedient, en in hoeveel waardestromen."""
    idx = {b["id"]: b for b in behoeften()}
    return [{**bes,
             "bedient": [idx[i] for i in bes["lost_op"] if i in idx],
             "aantal_behoeften": len([i for i in bes["lost_op"] if i in idx]),
             "waardestromen": sorted({idx[i]["w"] for i in bes["lost_op"] if i in idx}),
             "casussen": sorted({idx[i]["casus_kort"] for i in bes["lost_op"] if i in idx})}
            for bes in BESLUITEN]


def onbediend() -> list:
    """Onvervulde informatiebehoeften die géén van de voorgestelde besluiten oplost.

    Een besluitenlijst die dit niet laat zien, suggereert dekking die er niet is.
    """
    bediend = {i for b in BESLUITEN for i in b["lost_op"]}
    return [b for b in behoeften() if b["status"] != "voldaan" and b["id"] not in bediend]


def overzicht() -> dict:
    return {"redeneerlijnen": REDENEERLIJNEN, "waardestromen": WAARDESTROMEN,
            "informatiefuncties": INFORMATIEFUNCTIES, "registers": REGISTERS,
            "casussen": CASUSSEN, "besluiten": BESLUITEN, "balo_besluiten": BALO_BESLUITEN,
            "schaal": SCHAAL, "dekking": dekking_informatiefuncties(),
            "registergebruik": registergebruik(), "gedeelde_knelpunten": gedeelde_knelpunten(),
            "status_behoefte": STATUS_BEHOEFTE, "behoeften": behoeften(), "cyclus": cyclus(),
            "waardeoverzicht": waardeoverzicht(), "besluitwaarde": besluitwaarde(),
            "onbediend": onbediend(),
            "bron": "BALO businessarchitectuur v0.9 (concept, RWS/WVL) — structuur en begrippen. "
                    "Koppeling aan de casussen, statusoordelen en kosten-batenafweging zijn van dit lab."}
