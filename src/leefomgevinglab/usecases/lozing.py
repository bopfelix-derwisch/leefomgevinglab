"""Doelbeeld directe lozing: één lozingsactiviteit op een rijkswater, van aanvraag tot handhaving.

Het spiegelbeeld van /dvth. Waar de Seveso-keten één bevoegd gezag kent en een risicocontour
om een punt, kent deze keten twee bevoegde gezagen en een effect stroomafwaarts.

De keten: aanvraag via het DSO-loket → de knip tussen de MBA-vergunning (gemeente) en de
lozingsactiviteit (RWS namens de minister) → contextset met het ontvangende waterlichaam uit
de RWS-bronnen → beoordeling met ABM en immissietoets → besluit als STOP/TPOD-document met een
uit Aquo afgeleid objectmodel → een voorgesteld Register Lozingen → toezicht met monitoring →
handhaving volgens de LHSO.

Geverifieerd 2026-09-11:
  * Lozen rechtstreeks op een oppervlaktewaterlichaam is een lozingsactiviteit; bevoegd gezag is
    de waterbeheerder — voor wateren in rijksbeheer de minister van IenW, uitgevoerd door RWS.
    Voor regionale wateren is dat het waterschap. Indirect lozen op het riool valt daarentegen
    onder de milieubelastende activiteit, met de gemeente als bevoegd gezag.
  * Het beoordelingskader is de Algemene BeoordelingsMethodiek (ABM) met het Handboek
    Immissietoets; voor zeer zorgwekkende stoffen geldt een minimalisatieplicht.
  * De KRW-service van RWS bevat 89 oppervlaktewaterlichamen (54 vlak, 35 lijn) — de rijkswateren.
    Bij Deventer levert die naam='IJssel', owl_id='NL93_IJSSEL', stroomgebiedsdistrict 'NLRN'.
    Het veld owl_naam is in alle 54 vlakken leeg; de naam staat in 'naam'.
"""

BANEN = {
    "indienen": "Indienen & splitsen",
    "behandelen": "Behandelen — Rijkswaterstaat",
    "publiceren": "Publiceren",
    "toezicht": "Toezien & handhaven",
}

STATUS = {
    "bestaat": "Bestaat vandaag",
    "wijzigt": "Bestaat, moet om",
    "nieuw": "Nieuw in het doelbeeld",
}

CASUS = {
    "naam": "Overijsselse Papier- en Vezelfabriek B.V. — koel- en proceswater op de IJssel",
    "activiteit": "Lozingsactiviteit op een oppervlaktewaterlichaam (rijkswater)",
    "grondslag": "Bal — lozingsactiviteit; bevoegd gezag de minister van IenW, uitgevoerd door RWS",
    "bevoegd_gezag": "Minister van IenW (RWS) voor de lozing · gemeente voor de MBA",
    "rd": (206800.0, 474000.0),
    "toelichting": "Verzonnen bedrijf aan de IJssel bij Deventer. Het RD-punt is echt gekozen: de "
                   "KRW-service van RWS geeft daar het waterlichaam IJssel terug, en PDOK geeft "
                   "gemeente Deventer — zodat de keten bevoegd gezag én ontvangend water live kan "
                   "bepalen in plaats van ze te verzinnen.",
}


def _c(id, naam, baan, status, systeem, standaard, toelichting, band=False):
    return {"id": id, "naam": naam, "baan": baan, "status": status, "band": band,
            "systeem": systeem, "standaard": standaard, "toelichting": toelichting}


COMPONENTEN = [
    # --- Indienen & splitsen ----------------------------------------------------------
    _c("lozer", "Initiatiefnemer (de lozer)", "indienen", "bestaat", "—", "—",
       "Het bedrijf dat loost. In CIM-termen een BETROKKENE in de rol van initiatiefnemer, en de "
       "NIET-NATUURLIJK PERSOON achter de VESTIGING aan het water."),
    _c("dso_loket", "DSO Omgevingsloket", "indienen", "bestaat", "DSO-LV", "STTR/RTR",
       "De aanvraag komt hier binnen. De vergunningcheck leidt naar de lozingsactiviteit op een "
       "oppervlaktewaterlichaam — een wateractiviteit, niet de milieubelastende activiteit."),
    _c("knip", "De knip: twee bevoegde gezagen", "indienen", "wijzigt",
       "DSO-LV", "bevoegd-gezagregels Omgevingswet",
       "Eén initiatief, twee sporen. De lozingsactiviteit gaat naar de waterbeheerder — hier RWS "
       "namens de minister, omdat het rijkswater is. Het milieudeel blijft bij de gemeente. Bij een "
       "meervoudige aanvraag moet ergens bepaald worden wie waarover beslist; dat is deze knip."),
    _c("gemeente_mba", "Gemeente / omgevingsdienst — MBA-spoor", "indienen", "bestaat",
       "gemeente", "ZGW · Bal",
       "Het parallelle spoor: de milieubelastende activiteit van hetzelfde bedrijf. Twee besluiten "
       "over één fabriek, met eigen procedures en eigen doorlooptijden."),

    # --- Behandelen bij RWS ------------------------------------------------------------
    _c("rws_bg", "RWS namens de minister van IenW", "behandelen", "bestaat",
       "Rijkswaterstaat", "Ow · Bal",
       "Bevoegd gezag voor lozingsactiviteiten op wateren in rijksbeheer — en tegelijk de "
       "waterbeheerder die het effect op het watersysteem draagt. Anders dan bij een indirecte "
       "lozing vallen besluitnemer en waterbeheerder hier samen."),
    _c("rws_zaak", "Zaaksysteem RWS", "behandelen", "bestaat", "Rijkswaterstaat", "zaakgericht werken",
       "De zaak waarin de aanvraag wordt behandeld, met het veiligheids- en lozingsdossier als "
       "informatieobjecten."),
    _c("ctd", "CTD — Centraal Toegangspunt Data RWS", "behandelen", "wijzigt",
       "Rijkswaterstaat", "ISO 19115 · PostgREST",
       "De datavoorziening van RWS zelf, met per dataset een datakwaliteitslabel. In dit doelbeeld "
       "de plek die de contextset rond het lozingspunt samenstelt. Bestaat in beta; de rol als "
       "leverancier aan de vergunningverlening is nieuw."),
    _c("waterbronnen", "Waterbronnen & registraties", "behandelen", "bestaat", "diverse",
       "WFS · OGC API",
       "KRW-oppervlaktewaterlichamen en stroomgebieden van RWS, bestuurlijke gebieden van PDOK voor "
       "het MBA-bevoegd gezag, en het landelijke meetnet. Wat hiervan open is, staat op de "
       "bronnenkaart.", band=True),
    _c("analyse", "Analyse: ABM & immissietoets", "behandelen", "bestaat",
       "Rijkswaterstaat", "ABM · Handboek Immissietoets",
       "De Algemene BeoordelingsMethodiek bepaalt de saneringsinspanning per stof; de immissietoets "
       "rekent de restlozing door naar de concentratie in het ontvangende water."),
    _c("beoordeling", "Beoordeling & ontwerpbesluit", "behandelen", "bestaat",
       "Rijkswaterstaat", "BBT · ZZS · KRW",
       "Beste beschikbare technieken, minimalisatieplicht voor zeer zorgwekkende stoffen, en de "
       "vraag of het waterlichaam zijn KRW-doelen blijft halen. Levert de OVERWEGING."),

    # --- Publiceren ---------------------------------------------------------------------
    _c("plansysteem", "Plansysteem (STOP/TPOD)", "publiceren", "wijzigt",
       "bevoegd gezag", "STOP/TPOD",
       "Publiceert vandaag omgevingsdocumenten, niet individuele besluiten. In dit doelbeeld ook het "
       "lozingsbesluit, met het objectmodel als annotatie — dezelfde uitbreiding van de standaard "
       "als in het Seveso-doelbeeld."),
    _c("aquo_tpod", "Objectmodel afgeleid van Aquo", "publiceren", "nieuw",
       "Informatiehuis Water / Geonovum", "TPOD-annotatieset",
       "Waar het Seveso-besluit annotaties uit IMEV krijgt, komen ze hier uit Aquo: lozingspunt, "
       "parameter, emissiegrenswaarde, meetverplichting en het ontvangende waterlichaam. Aquo is de "
       "gedeelde taal van het waterdomein — alleen nog niet als annotatieset."),
    _c("lvbb", "LVBB / officiële bekendmakingen", "publiceren", "bestaat", "KOOP", "STOP",
       "Watervergunningen worden vandaag al bekendgemaakt via deze route en zijn zo landelijk "
       "vindbaar — als tekst, niet als objectstructuur."),
    _c("register_lozingen", "Register Lozingen (voorgesteld)", "publiceren", "nieuw",
       "nog te beleggen", "TPOD",
       "Het ontbrekende register. Voor externe veiligheid bestaat het REV; voor lozingen is er geen "
       "landelijk beeld van wie wat waar loost. Zonder zo'n register kun je vrachten per waterlichaam "
       "niet optellen, ZZS niet volgen en toezicht niet richten."),

    # --- Toezien & handhaven -------------------------------------------------------------
    _c("toezicht", "Toezicht RWS op de lozingsactiviteit", "toezicht", "bestaat",
       "Rijkswaterstaat", "—",
       "Administratief toezicht op de rapportageverplichting, en toezicht ter plaatse op de "
       "zuiveringsvoorziening. Geen GIR: dat is de gezamenlijke inspectieruimte voor Seveso."),
    _c("meetnet", "Monitoring & meetnet", "toezicht", "bestaat",
       "RWS / Informatiehuis Water", "Aquo · IM Metingen",
       "Het waterlichaam wordt zelf gemeten. Dat is het grote verschil met externe veiligheid: het "
       "effect van deze vergunning is waarneembaar, en dus toetsbaar — maar de meting hangt niet aan "
       "de vergunning die hem veroorzaakt."),
    _c("lhso", "LHSO-interventiematrix", "toezicht", "bestaat", "IPO / VNG", "LHSO",
       "Dezelfde landelijke handhavingsstrategie als in het Seveso-doelbeeld: gedrag van de "
       "overtreder tegen de mogelijke gevolgen. De uniformering zit hier, niet in de systemen."),
    _c("handhavingsbesluit", "Handhavingsbesluit", "toezicht", "bestaat",
       "bevoegd gezag", "STOP",
       "De maatregel wordt een besluit en gaat dezelfde publicatieroute als de vergunning."),

    _c("cim", "CIM-VTH-Flo", "behandelen", "wijzigt", "Geonovum / IenW", "conceptueel informatiemodel",
       "Hetzelfde informatiemodel als onder de Seveso-keten. Deze casus zet het onder druk op één "
       "punt: het effect ligt stroomafwaarts, en het CIM kent geen relatie tussen een lozing en het "
       "waterlichaam dat hem ontvangt.", band=True),
]


def _f(id, van, naar, label, standaard, status, toelichting=""):
    return {"id": id, "van": van, "naar": naar, "label": label,
            "standaard": standaard, "status": status, "toelichting": toelichting}


FLOWS = [
    _f("aanvraag", "lozer", "dso_loket", "aanvraag lozingsactiviteit", "STTR/RTR", "bestaat",
       "De vergunningcheck leidt naar een wateractiviteit, niet naar de milieubelastende activiteit."),
    _f("splitsen", "dso_loket", "knip", "meervoudige aanvraag", "bevoegd-gezagregels", "wijzigt",
       "Hier valt het initiatief uiteen in twee besluiten. Voor de aanvrager is het één fabriek."),
    _f("knip_rws", "knip", "rws_bg", "lozingsactiviteit → waterbeheerder", "Ow", "bestaat",
       "Rijkswater, dus de minister van IenW — in de praktijk RWS. Was het regionaal water geweest, "
       "dan was het waterschap bevoegd gezag."),
    _f("knip_gemeente", "knip", "gemeente_mba", "milieudeel → gemeente", "Ow", "bestaat"),
    _f("zaak", "rws_bg", "rws_zaak", "zaak starten", "zaakgericht werken", "bestaat"),
    _f("bronnen_ctd", "waterbronnen", "ctd", "ontsluiten", "WFS · OGC API", "wijzigt"),
    _f("ctd_analyse", "ctd", "analyse", "contextset: ontvangend waterlichaam", "nog te bepalen", "nieuw",
       "Welk waterlichaam ontvangt de lozing, in welk stroomgebiedsdistrict, en welke gemeente is "
       "bevoegd voor het milieudeel — alle drie af te leiden uit open bronnen."),
    _f("zaak_analyse", "rws_zaak", "analyse", "aanvraaggegevens", "—", "bestaat"),
    _f("analyse_beoordeling", "analyse", "beoordeling", "saneringsinspanning & immissie",
       "ABM · immissietoets", "bestaat"),
    _f("afstemming", "gemeente_mba", "beoordeling", "afstemming MBA ↔ lozing", "nog te bepalen", "nieuw",
       "De twee besluiten gaan over dezelfde fabriek en beïnvloeden elkaar: een emissiebeperking in "
       "het ene spoor verandert de vracht in het andere. Er is geen koppelvlak dat dit afdwingt."),
    _f("besluit_plansysteem", "beoordeling", "plansysteem", "besluit + geannoteerd objectmodel",
       "STOP/TPOD", "nieuw",
       "Hetzelfde scharnierpunt als bij Seveso: er bestaat geen toepassingsprofiel voor een "
       "vergunningbesluit."),
    _f("aquo_in_tpod", "aquo_tpod", "plansysteem", "annotatieset", "TPOD", "nieuw",
       "De Aquo-begrippen worden de annotatiewoordenschat van het besluit."),
    _f("plansysteem_lvbb", "plansysteem", "lvbb", "bekendmaking", "STOP", "bestaat"),
    _f("plansysteem_register", "plansysteem", "register_lozingen", "TPOD-deel → register", "TPOD", "nieuw",
       "Het besluit ís de aanlevering — als er een register was om in te landen."),
    _f("register_toezicht", "register_lozingen", "toezicht", "vergund beeld", "nog te bepalen", "nieuw",
       "De toezichthouder ziet wat vergund is naast wat gemeten wordt. Vandaag moet die vergelijking "
       "handmatig uit dossiers komen."),
    _f("meetnet_toezicht", "meetnet", "toezicht", "meetgegevens", "Aquo · IM Metingen", "bestaat"),
    _f("toezicht_lhso", "toezicht", "lhso", "bevinding → overtreding", "LHSO", "bestaat"),
    _f("lhso_besluit", "lhso", "handhavingsbesluit", "interventie kiezen", "LHSO-matrix", "bestaat"),
    _f("handhaving_lvbb", "handhavingsbesluit", "lvbb", "bekendmaking", "STOP", "bestaat"),
    _f("terugkoppeling", "handhavingsbesluit", "register_lozingen", "terugkoppeling naleving",
       "nog te bepalen", "nieuw"),
]


STAPPEN = [
    {"nr": 1, "naam": "Aanvraag lozingsactiviteit via het DSO-loket",
     "componenten": ["lozer", "dso_loket"],
     "cim": ["VERZOEK", "TOESTEMMINGSAANVRAAG", "ACTIVITEIT", "ACTIVITEITUITVOERING",
             "BETROKKENE", "NIET-NATUURLIJK PERSOON", "VESTIGING"],
     "beschrijving": "Het bedrijf vraagt vergunning voor het lozen van koel- en proceswater "
                     "rechtstreeks op de IJssel. Dat is een lozingsactiviteit op een "
                     "oppervlaktewaterlichaam — een wateractiviteit."},
    {"nr": 2, "naam": "De knip: twee bevoegde gezagen",
     "componenten": ["knip", "gemeente_mba", "rws_bg", "rws_zaak"],
     "cim": ["VTH-INSTANTIE", "ZAAK", "INFORMATIEOBJECT"],
     "beschrijving": "De aanvraag valt uiteen: de lozing naar de waterbeheerder, het milieudeel naar "
                     "de gemeente. Welke van de twee de waterbeheerder is — RWS of het waterschap — "
                     "hangt af van wie het water beheert."},
    {"nr": 3, "naam": "Ontvangend waterlichaam via de RWS-bronnen",
     "componenten": ["waterbronnen", "ctd", "analyse"],
     "cim": ["VTH-OBJECT", "GEO-OBJECT", "ANDER GEO-OBJECT"],
     "beschrijving": "Live bepaald: welk KRW-waterlichaam ontvangt de lozing, in welk "
                     "stroomgebiedsdistrict ligt het, en welke gemeente is bevoegd voor het "
                     "milieudeel. Het bevoegd gezag volgt hier uit de data."},
    {"nr": 4, "naam": "Beoordeling: ABM, immissietoets en ZZS",
     "componenten": ["analyse", "beoordeling"],
     "cim": ["OVERWEGING", "SPECIFIEK VOORSCHRIFT"],
     "beschrijving": "Per stof de saneringsinspanning, daarna de restlozing doorgerekend naar een "
                     "concentratie in het ontvangende water. Voor zeer zorgwekkende stoffen geldt "
                     "bovendien een minimalisatieplicht."},
    {"nr": 5, "naam": "Besluit als STOP/TPOD met Aquo-annotaties",
     "componenten": ["beoordeling", "plansysteem", "aquo_tpod", "lvbb"],
     "cim": ["TOESTEMMING", "BESLUIT", "SPECIFIEK VOORSCHRIFT"],
     "beschrijving": "De vergunning als geannoteerd document: lozingspunt, parameters, "
                     "emissiegrenswaarden, meetverplichting en het ontvangende waterlichaam als "
                     "annotaties op de tekst."},
    {"nr": 6, "naam": "Landing in het voorgestelde Register Lozingen",
     "componenten": ["plansysteem", "register_lozingen"],
     "cim": ["VTH-OBJECT", "GEO-OBJECT", "ACTIVITEIT"],
     "beschrijving": "Wat bij externe veiligheid het REV is, ontbreekt hier. Deze stap laat zien wat "
                     "een register zou krijgen als het bestond — en dus wat er nu verloren gaat."},
    {"nr": 7, "naam": "Toezicht en monitoring op het waterlichaam",
     "componenten": ["register_lozingen", "toezicht", "meetnet"],
     "cim": ["CONTROLE", "BEVINDING"],
     "beschrijving": "Administratief toezicht op de rapportage, toezicht ter plaatse op de "
                     "zuiveringsvoorziening, en de meetreeks van het waterlichaam zelf. Anders dan "
                     "bij externe veiligheid is het effect hier meetbaar."},
    {"nr": 8, "naam": "Handhaving volgens de LHSO",
     "componenten": ["toezicht", "lhso", "handhavingsbesluit", "register_lozingen"],
     "cim": ["OVERTREDING", "HANDHAVINGSMAATREGEL", "BESLUIT"],
     "beschrijving": "Dezelfde interventiematrix als bij Seveso: gedrag tegen gevolgen. De uitkomst "
                     "is een besluit, en dat zou moeten terugkoppelen naar het register."},
]


ROADMAP = [
    {"fase": "Fase 1", "titel": "Fundament: casus en dossier", "features": [
        {"id": "W1.1", "naam": "Synthetische lozingscasus", "gereed": "gebouwd",
         "wat": "Eén verzonnen fabriek aan de IJssel met debiet, parameters en vrachten, op een echt "
                "RD-punt waar de KRW-service een waterlichaam teruggeeft.",
         "componenten": ["lozer"], "stap": 1},
        {"id": "W1.2", "naam": "Dossier op de gedeelde ketenkern", "gereed": "gebouwd",
         "wat": "De objectbibliotheek, de LHSO-matrix en de ketenmotor zijn dossier-onafhankelijk; dit "
                "dossier levert alleen zijn eigen casus, bronnen, annotatieset en stappen.",
         "componenten": ["cim"], "stap": 1},
    ]},
    {"fase": "Fase 2", "titel": "Indienen, splitsen en context", "features": [
        {"id": "W2.1", "naam": "Aanvraag als wateractiviteit", "gereed": "gebouwd",
         "wat": "De aanvraag voor een lozingsactiviteit op een oppervlaktewaterlichaam, met de lozer "
                "als BETROKKENE en de lozing als ACTIVITEITUITVOERING.",
         "componenten": ["dso_loket"], "stap": 1},
        {"id": "W2.2", "naam": "De knip expliciet maken", "gereed": "gebouwd",
         "wat": "Twee VTH-INSTANTIEs met elk hun eigen besluit uit één aanvraag, zodat zichtbaar wordt "
                "waar de keten uiteenvalt. De zaak bij RWS volgt het lozingsspoor.",
         "componenten": ["knip", "gemeente_mba", "rws_bg", "rws_zaak"], "stap": 2},
        {"id": "W2.3", "naam": "Bevoegd gezag live afleiden", "gereed": "gebouwd",
         "wat": "Ligt het lozingspunt aan een rijkswater? De KRW-service van RWS bevat juist de "
                "rijkswateren; een treffer daar betekent dat de minister bevoegd gezag is. De gemeente "
                "voor het milieudeel komt uit de bestuurlijke gebieden van PDOK.",
         "componenten": ["waterbronnen", "ctd"], "stap": 3},
        {"id": "W2.4", "naam": "ABM en immissietoets", "gereed": "vereenvoudigd",
         "gereed_noot": "Indicatieve verdunningsberekening met een vast debiet per waterlichaam; de "
                        "echte immissietoets rekent met mengzones, achtergrondconcentraties en "
                        "stofspecifieke normen.",
         "wat": "Per parameter de saneringsinspanning en de doorgerekende concentratie in het "
                "ontvangende water, getoetst aan een indicatieve norm.",
         "componenten": ["analyse"], "stap": 4},
        {"id": "W2.5", "naam": "ZZS-minimalisatie in de overweging", "gereed": "gebouwd",
         "wat": "Zeer zorgwekkende stoffen krijgen een eigen spoor: minimalisatieplicht, "
                "vijfjaarlijkse vermijdings- en reductieplicht, en een voorschrift dat daaruit volgt.",
         "componenten": ["beoordeling"], "stap": 4},
    ]},
    {"fase": "Fase 3", "titel": "Publiceren: van Aquo naar TPOD", "features": [
        {"id": "W3.1", "naam": "Aquo → TPOD-annotatieset", "gereed": "gebouwd",
         "wat": "De begrippen uit het waterdomein — lozingspunt, parameter, emissiegrenswaarde, "
                "meetverplichting, ontvangend waterlichaam — omgezet naar annotaties binnen TPOD.",
         "componenten": ["aquo_tpod"], "stap": 5},
        {"id": "W3.2", "naam": "Besluitgenerator en validatie", "gereed": "gebouwd",
         "wat": "Het lozingsbesluit als geannoteerd document, met een controle of elke verplichte "
                "annotatie een plek heeft gekregen.",
         "componenten": ["plansysteem"], "stap": 5},
        {"id": "W3.3", "naam": "Bekendmaking via de LVBB", "gereed": "vereenvoudigd",
         "gereed_noot": "Een stap in het model, geen echte levering aan de LVBB.",
         "wat": "De publicatieroute die watervergunningen vandaag al volgen.",
         "componenten": ["lvbb"], "stap": 5},
        {"id": "W3.4", "naam": "Register Lozingen vullen uit het besluit", "gereed": "gebouwd",
         "wat": "Het registerobject dat uit de annotaties valt af te leiden, met per veld de herkomst — "
                "en de constatering dat er vandaag niets is om het in te zetten.",
         "componenten": ["register_lozingen"], "stap": 6},
    ]},
    {"fase": "Fase 4", "titel": "Toezien en handhaven", "features": [
        {"id": "W4.1", "naam": "Toezicht op drie sporen", "gereed": "gebouwd",
         "wat": "Bevindingen langs administratief toezicht, meetgegevens en de technische staat van de "
                "zuiveringsvoorziening, elk verwijzend naar een voorschrift uit het besluit.",
         "componenten": ["toezicht", "meetnet"], "stap": 7},
        {"id": "W4.2", "naam": "LHSO-interventie", "gereed": "vereenvoudigd",
         "gereed_noot": "Eén interventie per cel; de LHSO laat binnen een segment ruimte voor een "
                        "gemotiveerde keuze.",
         "wat": "Gedrag tegen gevolgen, met de matrixcel en de gekozen interventie.",
         "componenten": ["lhso"], "stap": 8},
        {"id": "W4.3", "naam": "Handhavingsbesluit en terugkoppeling", "gereed": "vereenvoudigd",
         "gereed_noot": "De terugkoppeling is als uitvoer gemodelleerd; er is geen register dat hem "
                        "ontvangt — dat is nu juist het punt.",
         "wat": "De maatregel als besluit, met terugkoppeling naar het vergunde beeld.",
         "componenten": ["handhavingsbesluit", "register_lozingen"], "stap": 8},
    ]},
    {"fase": "Fase 5", "titel": "Vergelijken met het Seveso-doelbeeld", "features": [
        {"id": "W5.1", "naam": "Ketenviewer in deze tab", "gereed": "gebouwd",
         "wat": "Dezelfde runner als op /dvth: acht stappen met payloads, bronstatus, dekking, het "
                "geannoteerde besluit en de matrix.",
         "componenten": ["cim"], "stap": 1},
        {"id": "W5.2", "naam": "Waar het CIM wringt bij stroomafwaarts effect", "gereed": "gebouwd",
         "wat": "Het CIM kent geen relatie tussen een lozing en het waterlichaam dat hem ontvangt. "
                "Het ontvangende water belandt in ANDER GEO-OBJECT — dezelfde restbak die op de "
                "bronnenkaart al de drukste was.",
         "componenten": ["cim"], "stap": 3},
        {"id": "W5.3", "naam": "Het ontbrekende register benoemen", "gereed": "gebouwd",
         "wat": "Naast elkaar: wat het REV voor externe veiligheid levert, en wat er voor lozingen "
                "niet is. Zonder register geen cumulatie per waterlichaam en geen ZZS-vrachten.",
         "componenten": ["register_lozingen"], "stap": 6},
    ]},
]


PRESENTATIE = {
    "api": "lozing",
    "titel": "Doelbeeld directe lozing",
    "badge": "doelbeeld lozing",
    "kop_voor": "Doelbeeld ", "kop_accent": "directe lozing",
    "kop_na": " — één lozingsactiviteit op een rijkswater",
    "intro": "Het spiegelbeeld van het Seveso-doelbeeld. Een bedrijf loost koel- en proceswater "
             "rechtstreeks op de IJssel. Omdat dat een rijkswater is, is de minister van IenW "
             "bevoegd gezag en voert RWS uit — en valt de aanvraag uiteen in twee besluiten, want "
             "het milieudeel blijft bij de gemeente. Het beoordelingskader is de ABM met de "
             "immissietoets, het objectmodel in het besluit komt uit Aquo, en het register waarin "
             "het zou moeten landen bestaat niet.",
    "aannames_kop": "Drie dingen die dit doelbeeld anders maken dan Seveso",
    "aannames": [
        {"kop": "Twee bevoegde gezagen over één fabriek.",
         "tekst": "De lozingsactiviteit gaat naar de waterbeheerder — bij rijkswater de minister van "
                  "IenW, uitgevoerd door RWS; bij regionaal water het waterschap. Het milieudeel "
                  "blijft bij de gemeente. Er is geen koppelvlak dat afdwingt dat beide besluiten op "
                  "elkaar aansluiten, terwijl een emissiebeperking in het ene spoor de vracht in het "
                  "andere verandert. Ter vergelijking: bij een indirecte lozing op het riool is de "
                  "gemeente bevoegd gezag en heeft het waterschap sinds de Omgevingswet nog slechts "
                  "adviesrecht zonder instemming."},
        {"kop": "Er is geen register.",
         "tekst": "Voor externe veiligheid bestaat het REV; voor lozingen is er geen landelijk beeld "
                  "van wie wat waar loost. Daardoor kun je vrachten per waterlichaam niet optellen, "
                  "ZZS niet volgen en toezicht niet richten. Het Register Lozingen in deze plaat is "
                  "een voorstel, geen bestaande voorziening."},
        {"kop": "Het effect ligt stroomafwaarts.",
         "tekst": "Seveso is een contour om een punt; een lozing werkt door in een watersysteem en "
                  "telt op bij alle andere lozingen op hetzelfde waterlichaam. Het CIM-VTH-Flo kent "
                  "geen relatie tussen een lozing en het water dat hem ontvangt — het ontvangende "
                  "waterlichaam belandt in ANDER GEO-OBJECT."},
    ],
    "verantwoording": "Dit is een doelbeeld van dit lab, geen vastgesteld architectuurdocument. Dat "
                      "een door RWS verleende watervergunning een directe lozing op rijkswater "
                      "betreft, dat het beoordelingskader de ABM met de immissietoets is en dat voor "
                      "ZZS een minimalisatieplicht geldt, is nagelopen op IPLO en bij het RIVM. Het "
                      "bedrijf is verzonnen; het RD-punt en het ontvangende waterlichaam zijn echt.",
}


def features() -> list[dict]:
    return [dict(f, fase=blok["fase"], fase_titel=blok["titel"])
            for blok in ROADMAP for f in blok["features"]]


def dekking_per_component() -> dict:
    uit = {c["id"]: 0 for c in COMPONENTEN}
    for f in features():
        for c in f["componenten"]:
            uit[c] = uit.get(c, 0) + 1
    return uit


def architectuur() -> dict:
    return {"presentatie": PRESENTATIE, "banen": BANEN, "status": STATUS, "casus": CASUS,
            "componenten": COMPONENTEN, "flows": FLOWS, "stappen": STAPPEN,
            "roadmap": ROADMAP, "dekking": dekking_per_component()}
