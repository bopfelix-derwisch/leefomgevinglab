"""Doelbeeld D-VTH: doelarchitectuur voor één MBA Seveso-inrichting, van aanvraag tot handhaving.

De keten: aanvraag via het DSO-loket → zaak bij de omgevingsdienst → context via Data.OD naar de
analysesystemen → beoordeling → besluit als STOP/TPOD-document met een uit IMEV afgeleid objectmodel
→ omgebouwd REV → toezicht in GIR volgens de LBR-methodiek → handhaving volgens de LHSO.

Het CIM-VTH-Flo ligt als informatiemodel onder de hele keten; per stap staat welke objecttypen
ontstaan. Zie /vth voor de kapstok en /vth-bronnen voor het bronnenlandschap.

Wat hier 'nieuw' heet, bestaat vandaag niet. Twee dingen in het bijzonder:
  * STOP/TPOD kent toepassingsprofielen voor omgevingsdocumenten (omgevingsplan, -verordening,
    -visie, instructie), niet voor een vergunningbesluit. Het besluit als TPOD-document is dus
    een uitbreiding van de standaard.
  * Het REV wordt vandaag gevoed via een eigen aanleverketen op IMEV 3.0.2. TPOD-native aanlevering
    vervangt die route.

Geverifieerd 2026-09-11: Seveso-inrichting is één milieubelastende activiteit (Bal §3.3.1),
volledig vergunningplichtig, provincie is bevoegd gezag met uitvoering bij zes Seveso-
omgevingsdiensten; GIR 2.0 registreert inspecties volgens de LBR (Systeem/Techniek/Cultuur);
de LHSO bepaalt de interventie via een matrix van gedrag × gevolgen.
"""

BANEN = {
    "indienen": "Indienen",
    "behandelen": "Behandelen — omgevingsdienst",
    "publiceren": "Publiceren",
    "toezicht": "Toezien & handhaven",
}

STATUS = {
    "bestaat": "Bestaat vandaag",
    "wijzigt": "Bestaat, moet om",
    "nieuw": "Nieuw in het doelbeeld",
}

CASUS = {
    "naam": "Zuidhaven Chemie B.V. — opslag tot vloeistof verdicht ammoniak",
    "activiteit": "Exploiteren van een Seveso-inrichting (hogedrempel)",
    "grondslag": "Bal §3.3.1 — één milieubelastende activiteit, volledig vergunningplichtig",
    "bevoegd_gezag": "Gedeputeerde Staten, uitvoering bij een Seveso-omgevingsdienst",
    "rd": (92150.0, 436420.0),
    "toelichting": "Volledig verzonnen bedrijf op een echt bestaand industrieterrein-achtig RD-punt, "
                   "zodat de Data.OD-stap straks tegen de echte REV- en PDOK-bronnen kan draaien "
                   "zonder een bestaand bedrijf te beschrijven.",
}


def _c(id, naam, baan, status, systeem, standaard, toelichting, band=False):
    """band=True: component die alle banen overspant en als balk wordt getekend."""
    return {"id": id, "naam": naam, "baan": baan, "status": status, "band": band,
            "systeem": systeem, "standaard": standaard, "toelichting": toelichting}


COMPONENTEN = [
    # --- Indienen ---------------------------------------------------------------------
    _c("initiatiefnemer", "Initiatiefnemer", "indienen", "bestaat",
       "—", "—",
       "De exploitant van de Seveso-inrichting. In CIM-termen een BETROKKENE in de rol van "
       "initiatiefnemer, en tevens de NIET-NATUURLIJK PERSOON achter de VESTIGING."),
    _c("dso_loket", "DSO Omgevingsloket", "indienen", "bestaat",
       "DSO-LV", "STTR/RTR · aanvraagformulier",
       "De aanvraag voor het exploiteren van een Seveso-inrichting komt hier binnen. De "
       "vergunningcheck leidt de aanvrager via toepasbare regels naar de juiste activiteit."),
    _c("dso_samenwerken", "DSO Samenwerkfunctionaliteit", "indienen", "bestaat",
       "DSO-LV", "Samenwerken-API",
       "Het kanaal waarlangs het bevoegd gezag het verzoek ophaalt en waarlangs de "
       "betrokken overheden samenwerken aan één aanvraag."),

    # --- Behandelen -------------------------------------------------------------------
    _c("zaaksysteem", "Zaaksysteem omgevingsdienst", "behandelen", "bestaat",
       "OD", "ZGW-API's (Zaken, Documenten, Besluiten, Catalogi)",
       "Haalt het verzoek op en maakt er een ZAAK van. Dit is de enige plek in de hele keten "
       "waar ZAAK en INFORMATIEOBJECT als echte objecten bestaan — achter eigen autorisatie."),
    _c("dataod", "Data.OD — Datapunt Omgevingsdiensten", "behandelen", "nieuw",
       "DCMR + OD De Vallei", "nog te bepalen",
       "Landelijke datavoorziening voor omgevingsdiensten, in ontwikkeling. In dit doelbeeld de "
       "plek die de contextset rond de aanvraag samenstelt uit basisregistraties, REV, NHR en "
       "milieubronnen, en die levert aan de analysesystemen."),
    _c("bronnen", "Basisregistraties & landelijke bronnen", "behandelen", "bestaat",
       "diverse", "WFS/OGC API · REST · SRU",
       "BAG, BGT, BRK, NHR, REV, BRO, PRTR/e-MJV en LMA. Wat hiervan open is, staat op de "
       "bronnenkaart; de contextset van Data.OD wordt hieruit opgebouwd.", band=True),
    _c("analyse", "Analysesystemen omgevingsdienst", "behandelen", "bestaat",
       "OD", "QRA · GIS · rekenmodellen",
       "Kwantitatieve risicoanalyse, afstandsberekening en de bepaling van brand-, explosie- "
       "en gifwolkaandachtsgebieden rond de inrichting."),
    _c("beoordeling", "Beoordeling & ontwerpbesluit", "behandelen", "bestaat",
       "OD", "Bal · Bkl",
       "Toetsing aan de regels voor Seveso-inrichtingen en aan de afstandseisen. Levert de "
       "OVERWEGING die het besluit draagt — het enige CIM-objecttype waarvoor nergens een bron bestaat."),

    # --- Publiceren -------------------------------------------------------------------
    _c("plansysteem", "Plansysteem (STOP/TPOD)", "publiceren", "wijzigt",
       "bevoegd gezag", "STOP/TPOD",
       "Vandaag publiceren plansystemen omgevingsdocumenten: omgevingsplan, -verordening, -visie, "
       "instructie. In dit doelbeeld publiceren ze óók het vergunningbesluit, met het "
       "objectmodel als annotatie. Daar bestaat nu geen toepassingsprofiel voor."),
    _c("imev_tpod", "Objectmodel afgeleid van IMEV", "publiceren", "nieuw",
       "Geonovum / IenW", "TPOD-annotatieset",
       "De kern van de ombouw: de objecten en attributen van IMEV 3.0.2 — risicobron, "
       "aandachtsgebied, maatgevende stof, contour — omgezet naar annotaties binnen TPOD, "
       "zodat het besluit zelf de brongegevens draagt in plaats van een losse aanlevering."),
    _c("lvbb", "LVBB / officiële bekendmakingen", "publiceren", "bestaat",
       "KOOP", "STOP",
       "De bekendmaking van het besluit. Vandaag al de landelijke route waarlangs vergunningen "
       "openbaar worden — als tekst, niet als objectstructuur."),
    _c("rev_nieuw", "REV — omgebouwd naar TPOD", "publiceren", "wijzigt",
       "RIVM / IenW", "TPOD in plaats van IMEV-aanlever-API",
       "Het REV wordt vandaag gevuld via een eigen aanleverketen op IMEV 3.0.2. In het doelbeeld "
       "landt het TPOD-deel van het besluit rechtstreeks in het register: het besluit ís de "
       "aanlevering. Dat haalt de dubbele registratie en het kwaliteitsverschil per bronhouder eruit."),

    # --- Toezien & handhaven ----------------------------------------------------------
    _c("gir", "GIR 2.0 — Gemeenschappelijke Inspectieruimte", "toezicht", "bestaat",
       "Rijksorganisatie ODI", "GIR",
       "De gedeelde inspectiedatabase waarin toezichtteams een inspectie samen voorbereiden, "
       "uitvoeren en afronden. Bevat de CONTROLE en de BEVINDING — en is gesloten voor iedereen "
       "buiten het toezicht."),
    _c("lbr", "LBR-methodiek", "toezicht", "bestaat",
       "SEVESO+", "Systeem · Techniek · Cultuur",
       "De Landelijke Benadering Risicobedrijven, sinds 2022 de inspectiemethode voor Seveso-"
       "inrichtingen. Drie pijlers geven de bevindingen een vaste structuur: beoordeling van het "
       "veiligheidsbeheerssysteem, van de staat van de techniek en van de veiligheidscultuur."),
    _c("lhso", "LHSO-interventiematrix", "toezicht", "bestaat",
       "IPO / VNG", "LHSO",
       "De landelijke handhavingsstrategie omgevingsrecht. De matrix zet het gedrag van de "
       "overtreder af tegen de mogelijke gevolgen en wijst zo de interventie aan. Omgevingsdiensten "
       "zijn verplicht ermee te werken — de uniformering zit hier, niet in de systemen."),
    _c("handhavingsbesluit", "Handhavingsbesluit", "toezicht", "bestaat",
       "bevoegd gezag", "STOP · ZGW Besluiten",
       "De maatregel wordt een besluit: last onder dwangsom, bestuursdwang of intrekking. "
       "Gaat dezelfde publicatieroute als de vergunning."),
    _c("cim", "CIM-VTH-Flo", "behandelen", "wijzigt",
       "Geonovum / IenW", "conceptueel informatiemodel",
       "Het overkoepelende informatiemodel: de gedeelde taal waarin elk koppelvlak in deze keten "
       "wordt uitgedrukt. Vandaag een werkversie zonder implementatie; in het doelbeeld de "
       "contractlaag tussen alle systemen hierboven.", band=True),
]


def _f(id, van, naar, label, standaard, status, toelichting=""):
    return {"id": id, "van": van, "naar": naar, "label": label,
            "standaard": standaard, "status": status, "toelichting": toelichting}


FLOWS = [
    _f("aanvraag", "initiatiefnemer", "dso_loket", "aanvraag MBA Seveso",
       "STTR/RTR", "bestaat",
       "De vergunningcheck leidt naar één activiteit: het exploiteren van een Seveso-inrichting."),
    _f("loket_naar_samenwerken", "dso_loket", "dso_samenwerken", "verzoek beschikbaar",
       "Samenwerken-API", "bestaat"),
    _f("ophalen_zaak", "dso_samenwerken", "zaaksysteem", "verzoek ophalen → ZAAK",
       "ZGW Zaken/Documenten", "bestaat",
       "Het VERZOEK uit het DSO wordt een ZAAK bij de omgevingsdienst."),
    _f("bronnen_naar_dataod", "bronnen", "dataod", "ontsluiten",
       "WFS/OGC API · REST", "wijzigt",
       "Vandaag haalt elke omgevingsdienst dit apart op, in eigen vorm. Data.OD maakt er één "
       "landelijke voorziening van."),
    _f("dataod_naar_analyse", "dataod", "analyse", "contextset op het punt",
       "nog te bepalen", "nieuw",
       "Alles wat binnen invloedsafstand ligt: panden, kwetsbare gebouwen, omliggende risicobronnen, "
       "bodem- en waterinformatie, de vestiging uit het NHR."),
    _f("zaak_naar_analyse", "zaaksysteem", "analyse", "aanvraaggegevens",
       "ZGW", "bestaat"),
    _f("analyse_naar_beoordeling", "analyse", "beoordeling", "aandachtsgebieden & afstanden",
       "QRA · Bkl", "bestaat"),
    _f("besluit_naar_plansysteem", "beoordeling", "plansysteem", "besluit + geannoteerd objectmodel",
       "STOP/TPOD", "nieuw",
       "Het scharnierpunt van het doelbeeld. STOP/TPOD kent vandaag geen toepassingsprofiel voor "
       "een vergunningbesluit; dit vraagt een nieuw profiel."),
    _f("imev_in_tpod", "imev_tpod", "plansysteem", "annotatieset",
       "TPOD", "nieuw",
       "Het uit IMEV afgeleide objectmodel wordt de annotatiewoordenschat van het besluit."),
    _f("plansysteem_naar_lvbb", "plansysteem", "lvbb", "bekendmaking",
       "STOP", "bestaat"),
    _f("plansysteem_naar_rev", "plansysteem", "rev_nieuw", "TPOD-deel → register",
       "TPOD", "nieuw",
       "Het besluit ís de aanlevering: geen aparte IMEV-levering meer door de bronhouder."),
    _f("rev_naar_gir", "rev_nieuw", "gir", "risicobeeld delen",
       "nog te bepalen", "nieuw",
       "De toezichthouder ziet in GIR wat er vergund is, uit dezelfde bron als het publieke register."),
    _f("gir_volgens_lbr", "gir", "lbr", "inspectie volgens LBR",
       "Systeem · Techniek · Cultuur", "bestaat"),
    _f("lbr_naar_lhso", "lbr", "lhso", "bevinding → overtreding",
       "LHSO", "bestaat"),
    _f("lhso_naar_besluit", "lhso", "handhavingsbesluit", "interventie kiezen",
       "LHSO-matrix", "bestaat"),
    _f("handhaving_naar_lvbb", "handhavingsbesluit", "lvbb", "bekendmaking",
       "STOP", "bestaat"),
    _f("terugkoppeling", "handhavingsbesluit", "rev_nieuw", "terugkoppeling naleving",
       "nog te bepalen", "nieuw",
       "De sluitsteen: wat handhaving constateert, werkt door in het risicobeeld. Vandaag loopt "
       "die lus nergens."),
]


STAPPEN = [
    {"nr": 1, "naam": "Aanvraag via het DSO-loket",
     "componenten": ["initiatiefnemer", "dso_loket"],
     "cim": ["VERZOEK", "TOESTEMMINGSAANVRAAG", "ACTIVITEIT", "ACTIVITEITUITVOERING",
             "BETROKKENE", "VESTIGING"],
     "beschrijving": "De exploitant vraagt vergunning voor het exploiteren van een Seveso-inrichting. "
                     "Eén activiteit, gecumuleerde risico's van alle installaties."},
    {"nr": 2, "naam": "Zaak bij de omgevingsdienst",
     "componenten": ["dso_samenwerken", "zaaksysteem"],
     "cim": ["ZAAK", "INFORMATIEOBJECT", "VTH-INSTANTIE"],
     "beschrijving": "De omgevingsdienst haalt het verzoek op en start een zaak. Bevoegd gezag blijft "
                     "Gedeputeerde Staten; de uitvoering ligt bij een Seveso-omgevingsdienst."},
    {"nr": 3, "naam": "Contextset via Data.OD",
     "componenten": ["bronnen", "dataod", "analyse"],
     "cim": ["VTH-OBJECT", "GEO-OBJECT", "PAND", "ADRESSEERBAAR OBJECT", "NIET-NATUURLIJK PERSOON"],
     "beschrijving": "Alles wat rond het RD-punt ligt wordt opgehaald: omliggende risicobronnen uit het "
                     "REV, panden en adressen, de vestiging uit het NHR. Hier draait de keten straks "
                     "tegen de échte bronnen."},
    {"nr": 4, "naam": "Beoordeling en afstandstoets",
     "componenten": ["analyse", "beoordeling"],
     "cim": ["OVERWEGING", "SPECIFIEK VOORSCHRIFT"],
     "beschrijving": "Brand-, explosie- en gifwolkaandachtsgebieden worden bepaald en getoetst; de "
                     "afweging en de voorschriften komen eruit."},
    {"nr": 5, "naam": "Besluit als STOP/TPOD-document",
     "componenten": ["beoordeling", "plansysteem", "imev_tpod", "lvbb"],
     "cim": ["TOESTEMMING", "BESLUIT", "SPECIFIEK VOORSCHRIFT"],
     "beschrijving": "De vergunning wordt gepubliceerd als geannoteerd document, met het uit IMEV "
                     "afgeleide objectmodel als annotatieset, en bekendgemaakt via de LVBB."},
    {"nr": 6, "naam": "Landing in het omgebouwde REV",
     "componenten": ["plansysteem", "rev_nieuw"],
     "cim": ["VTH-OBJECT", "GEO-OBJECT", "ACTIVITEIT"],
     "beschrijving": "Het TPOD-deel wordt het registerobject. Geen aparte IMEV-aanlevering meer, dus "
                     "geen verschil meer tussen wat vergund is en wat geregistreerd staat."},
    {"nr": 7, "naam": "Toezicht in GIR volgens de LBR",
     "componenten": ["rev_nieuw", "gir", "lbr"],
     "cim": ["CONTROLE", "BEVINDING"],
     "beschrijving": "Het inspectieteam bereidt voor op het risicobeeld uit het register en legt "
                     "bevindingen vast langs de drie pijlers Systeem, Techniek en Cultuur."},
    {"nr": 8, "naam": "Handhaving volgens de LHSO",
     "componenten": ["lbr", "lhso", "handhavingsbesluit", "rev_nieuw"],
     "cim": ["OVERTREDING", "HANDHAVINGSMAATREGEL", "BESLUIT"],
     "beschrijving": "Een bevinding die een overtreding blijkt, gaat door de interventiematrix: gedrag "
                     "van de overtreder tegen de mogelijke gevolgen. De uitkomst is een besluit, en die "
                     "koppelt terug naar het risicobeeld."},
]


ROADMAP = [
    {"fase": "Fase 1", "titel": "Fundament: casus, objecten en ketenmotor", "features": [
        {"id": "F1.1", "gereed": "gebouwd", "naam": "Synthetische Seveso-casus",
         "wat": "Eén verzonnen hogedrempelinrichting met stoffen, installaties en een RD-punt, plus de "
                "aanvraaggegevens. Vast en reproduceerbaar, zodat elke stap hetzelfde vertrekpunt heeft.",
         "componenten": ["initiatiefnemer"], "stap": 1},
        {"id": "F1.2", "gereed": "gebouwd", "naam": "CIM-objectbibliotheek in code",
         "wat": "De objecttypen die deze keten raakt als dataklassen, met de attributen die het CIM "
                "voorschrijft — de contractlaag waar elke stap in- en uitgaand aan voldoet.",
         "componenten": ["cim"], "stap": 1},
        {"id": "F1.3", "gereed": "gebouwd", "naam": "Ketenmotor met stap-protocol",
         "wat": "Elke stap is een functie die invoer, uitvoer, ontstane CIM-objecten en een duiding "
                "teruggeeft. De motor voert ze op volgorde uit en bewaart het spoor.",
         "componenten": ["cim"], "stap": 1},
    ]},
    {"fase": "Fase 2", "titel": "Indienen en behandelen", "features": [
        {"id": "F2.1", "gereed": "gebouwd", "naam": "Aanvraagobject conform het DSO",
         "wat": "Een aanvraag voor het exploiteren van een Seveso-inrichting, met de activiteit uit de "
                "Bal-structuur en de initiatiefnemer als BETROKKENE.",
         "componenten": ["dso_loket"], "stap": 1},
        {"id": "F2.2", "gereed": "gebouwd", "naam": "Verzoek ophalen en zaak starten",
         "wat": "Het verzoek via de samenwerkfunctionaliteit omzetten naar een ZAAK met "
                "INFORMATIEOBJECTen, in de vorm van de ZGW-API's.",
         "componenten": ["dso_samenwerken", "zaaksysteem"], "stap": 2},
        {"id": "F2.3", "gereed": "gebouwd", "naam": "Data.OD-connector: contextset op het punt",
         "wat": "Live bevraging van de echte bronnen rond het RD-punt — REV-WFS voor omliggende "
                "aandachtsgebieden, PDOK voor panden en adressen — en dat bundelen tot één contextset.",
         "componenten": ["bronnen", "dataod"], "stap": 3},
        {"id": "F2.4", "gereed": "vereenvoudigd", "gereed_noot": "Indicatieve afstandstabel per stofcategorie; een echte QRA rekent met scenario's, weerklassen en faalfrequenties.", "naam": "Afstandstoets en aandachtsgebieden",
         "wat": "Brand-, explosie- en gifwolkaandachtsgebied afleiden en toetsen tegen wat er binnen "
                "die afstanden werkelijk staat.",
         "componenten": ["analyse"], "stap": 4},
        {"id": "F2.5", "gereed": "gebouwd", "naam": "Beoordeling met onderbouwing",
         "wat": "De OVERWEGING samenstellen: wat is getoetst, wat is de uitkomst, welke voorschriften "
                "volgen eruit. Het objecttype waar nergens een bron voor bestaat, hier wél gevuld.",
         "componenten": ["beoordeling"], "stap": 4},
    ]},
    {"fase": "Fase 3", "titel": "Publiceren: van IMEV naar TPOD", "features": [
        {"id": "F3.1", "gereed": "gebouwd", "naam": "IMEV → TPOD-annotatieset",
         "wat": "De objecten en attributen van IMEV 3.0.2 omzetten naar een annotatiewoordenschat die "
                "binnen TPOD past. Het inhoudelijke hart van de ombouw.",
         "componenten": ["imev_tpod"], "stap": 5},
        {"id": "F3.2", "gereed": "gebouwd", "naam": "Besluitgenerator STOP/TPOD",
         "wat": "Het vergunningbesluit als geannoteerd document, met de risicobron, de "
                "aandachtsgebieden en de maatgevende stof als annotaties op de tekst.",
         "componenten": ["plansysteem"], "stap": 5},
        {"id": "F3.3", "gereed": "gebouwd", "naam": "Validatie van het besluitdocument",
         "wat": "Controleren of het gegenereerde document voldoet aan de annotatieset en of elke "
                "verplichte IMEV-eigenschap een plek heeft gekregen.",
         "componenten": ["plansysteem", "imev_tpod"], "stap": 5},
        {"id": "F3.4", "gereed": "vereenvoudigd", "gereed_noot": 'De bekendmaking is een stap in het model, geen echte levering aan de LVBB.', "naam": "Bekendmaking via de LVBB",
         "wat": "De publicatiestap: het besluit als officiële publicatie, zodat de route naar de "
                "bekendmakingen dezelfde blijft als vandaag.",
         "componenten": ["lvbb"], "stap": 5},
        {"id": "F3.5", "gereed": "gebouwd", "naam": "REV-adapter op TPOD",
         "wat": "Het TPOD-deel omzetten naar registerobjecten en tonen dat het besluit de aanlevering "
                "kan zijn.",
         "componenten": ["rev_nieuw"], "stap": 6},
        {"id": "F3.6", "gereed": "gebouwd", "naam": "Vergelijking oude en nieuwe route",
         "wat": "Naast elkaar: wat het REV vandaag via IMEV binnenkrijgt tegenover wat het besluit "
                "zelf al draagt. Maakt de winst van de ombouw meetbaar.",
         "componenten": ["rev_nieuw", "imev_tpod"], "stap": 6},
    ]},
    {"fase": "Fase 4", "titel": "Toezien en handhaven", "features": [
        {"id": "F4.1", "gereed": "gebouwd", "naam": "Inspectie-object in GIR-vorm",
         "wat": "De CONTROLE met aanleiding, team, datum en het risicobeeld waarop is voorbereid.",
         "componenten": ["gir"], "stap": 7},
        {"id": "F4.2", "gereed": "gebouwd", "naam": "Bevindingen langs de LBR-pijlers",
         "wat": "BEVINDINGen gestructureerd naar Systeem, Techniek en Cultuur in plaats van vrije "
                "tekst — zo worden ze vergelijkbaar tussen inspecties en tussen diensten.",
         "componenten": ["lbr"], "stap": 7},
        {"id": "F4.3", "gereed": "gebouwd", "naam": "Overtreding afleiden uit bevindingen",
         "wat": "Van constatering naar OVERTREDING, met verwijzing naar het voorschrift uit het "
                "besluit dat wordt overtreden — de lus terug naar fase 3.",
         "componenten": ["lbr", "lhso"], "stap": 8},
        {"id": "F4.4", "gereed": "vereenvoudigd", "gereed_noot": 'Eén interventie per cel; de LHSO laat binnen een segment ruimte voor een gemotiveerde keuze.', "naam": "LHSO-interventiematrix",
         "wat": "Gedrag van de overtreder tegen de mogelijke gevolgen, met de matrix die de interventie "
                "aanwijst en de motivering vastlegt.",
         "componenten": ["lhso"], "stap": 8},
        {"id": "F4.5", "gereed": "vereenvoudigd", "gereed_noot": 'De terugkoppeling naar het risicobeeld is als uitvoer gemodelleerd; er is geen register dat hem ontvangt.', "naam": "Handhavingsbesluit en terugkoppeling",
         "wat": "De maatregel als besluit, bekendgemaakt langs dezelfde route, met terugkoppeling naar "
                "het risicobeeld in het register.",
         "componenten": ["handhavingsbesluit", "rev_nieuw"], "stap": 8},
    ]},
    {"fase": "Fase 5", "titel": "De keten zichtbaar maken", "features": [
        {"id": "F5.1", "gereed": "gebouwd", "naam": "Ketenviewer in deze tab",
         "wat": "Stap voor stap doorlopen, met per stap de in- en uitgaande payload en de ontstane "
                "CIM-objecten. Dit is het werkende ketentje.",
         "componenten": ["cim"], "stap": 1},
        {"id": "F5.2", "gereed": "gebouwd", "naam": "CIM-dekkingsmeter over de keten",
         "wat": "Welke objecttypen van het CIM raakt deze ene casus, en welke blijven onaangeroerd — "
                "de tegenhanger van de dekkingsanalyse op de bronnenkaart.",
         "componenten": ["cim"], "stap": 8},
        {"id": "F5.3", "gereed": "gebouwd", "naam": "Impactanalyse CIM-Flo × TPOD",
         "wat": "Waar het CIM en de TPOD-annotatieset elkaar niet dekken: welke objecttypen laten zich "
                "niet annoteren, welke annotaties passen in geen objecttype.",
         "componenten": ["cim", "imev_tpod"], "stap": 5},
        {"id": "F5.4", "gereed": "gebouwd", "naam": "Keten exporteren",
         "wat": "De hele doorloop als één JSON, zodat de uitkomst buiten het lab te beoordelen is.",
         "componenten": ["cim"], "stap": 8},
    ]},
]


def features() -> list[dict]:
    """Alle roadmap-features plat, met hun fase erbij."""
    return [dict(f, fase=blok["fase"], fase_titel=blok["titel"])
            for blok in ROADMAP for f in blok["features"]]


def dekking_per_component() -> dict:
    """Hoeveel features raken elke component — laat zien waar het werk zit."""
    uit = {c["id"]: 0 for c in COMPONENTEN}
    for f in features():
        for c in f["componenten"]:
            uit[c] = uit.get(c, 0) + 1
    return uit


PRESENTATIE = {
    "api": "dvth",
    "titel": "Doelbeeld D-VTH",
    "badge": "doelbeeld D-VTH",
    "kop_voor": "Doelbeeld ", "kop_accent": "D-VTH",
    "kop_na": " — één Seveso-inrichting, van aanvraag tot handhaving",
    "intro": "De doelarchitectuur voor de digitale VTH-keten, uitgewerkt op precies één geval: een "
             "milieubelastende activiteit van het type Seveso-inrichting. Het CIM-VTH-Flo ligt als "
             "informatiemodel onder elk koppelvlak; de aanvraag komt via het DSO-loket binnen, wordt "
             "door het zaaksysteem van de omgevingsdienst opgehaald, beoordeeld op data die via "
             "Data.OD naar de analysesystemen komt, en het besluit wordt als STOP/TPOD-document "
             "gepubliceerd met een uit IMEV afgeleid objectmodel — dat vervolgens in een omgebouwd "
             "REV landt. Toezicht gebeurt in GIR volgens de LBR-methodiek, handhaving volgens de LHSO.",
    "aannames_kop": "Drie aannames die het doelbeeld expliciet maakt",
    "aannames": [
        {"kop": "Het besluit als TPOD-document.",
         "tekst": "STOP/TPOD kent toepassingsprofielen voor omgevingsdocumenten — omgevingsplan, "
                  "omgevingsverordening, omgevingsvisie, instructie — maar niet voor een "
                  "vergunningbesluit. De stap van beoordeling naar plansysteem vraagt dus een nieuw "
                  "toepassingsprofiel; dat is geen implementatiedetail maar een standaardisatietraject."},
        {"kop": "Het REV moet om.",
         "tekst": "Het register wordt nu gevuld via een eigen aanleverketen op IMEV 3.0.2, los van "
                  "het besluit. In het doelbeeld ís het besluit de aanlevering. Dat haalt de dubbele "
                  "registratie eruit — en daarmee ook het kwaliteitsverschil per bronhouder dat de "
                  "WFS-check nu meet."},
        {"kop": "Data.OD bestaat nog niet als voorziening.",
         "tekst": "Het Datapunt Omgevingsdiensten is een initiatief van DCMR en Omgevingsdienst De "
                  "Vallei, met steun van Omgevingsdienst NL. In dit doelbeeld is het de plek die de "
                  "contextset samenstelt; vandaag doet elke dienst dat zelf."},
    ],
    "verantwoording": "Dit is een doelbeeld van dit lab, geen vastgesteld architectuurdocument van "
                      "enige organisatie. Feiten over Seveso als milieubelastende activiteit, de "
                      "LBR-inspectiemethodiek en de LHSO zijn nagelopen op IPLO, bij SEVESO+ en bij "
                      "Geonovum; wat niet bestaat, staat als nieuw gemarkeerd. Het bedrijf in de "
                      "casus is verzonnen.",
}


def architectuur() -> dict:
    """Alles wat de plaat en de roadmap nodig hebben, in één payload."""
    return {"presentatie": PRESENTATIE, "banen": BANEN, "status": STATUS, "casus": CASUS,
            "componenten": COMPONENTEN, "flows": FLOWS, "stappen": STAPPEN,
            "roadmap": ROADMAP, "dekking": dekking_per_component()}
