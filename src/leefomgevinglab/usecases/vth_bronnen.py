"""Bronnenlandschap onder het Cim-VTH-Flo: welke registraties vullen welke objecttypen.

Catalogus van registraties, API's en datasets bij rijk, RWS, provincies, waterschappen,
omgevingsdiensten en gemeenten, gemapt op de kern-objecttypen van het Conceptueel
Informatiemodel VTH Fysieke Leefomgeving (Geonovum, werkversie 4 augustus 2026, CC BY 4.0).

De mapping is een interpretatie van dit lab, geen product van Geonovum. Endpoints zijn
op 2026-09-10 handmatig aangeroepen; `check_endpoints` doet dat live opnieuw, zodat de
open/gesloten-claims verifieerbaar blijven in plaats van een momentopname te zijn.
"""
import asyncio

import httpx

# Bestuurslagen, in de volgorde waarin ze op de kaart van boven naar beneden staan.
LAGEN = {
    "rijk": "Rijk & landelijke registraties",
    "rws": "Rijkswaterstaat & landelijke diensten",
    "provincie": "Provincies",
    "waterschap": "Waterschappen",
    "omgevingsdienst": "Omgevingsdiensten",
    "gemeente": "Gemeenten",
}

OPENHEID = {
    "open": "Open — vrij aanroepbaar",
    "semi": "Semi — sleutel, contract of alleen aggregaat",
    "gesloten": "Gesloten — alleen bevoegd gezag",
}

# De 7 views met hun kern-objecttypen (Cim-VTH-Flo, Figuur 20).
VIEWS = [
    {"naam": "Locatie-view", "objecttypen": [
        "VTH-OBJECT", "GEO-OBJECT", "PAND", "ADRESSEERBAAR OBJECT",
        "KADASTRALE ONROERENDE ZAAK", "TOPOGRAFISCH OBJECT", "ANDER GEO-OBJECT"]},
    {"naam": "Activiteit-view", "objecttypen": [
        "ACTIVITEIT", "ACTIVITEITUITVOERING", "TOESTEMMING",
        "ALGEMEEN VERBINDEND VOORSCHRIFT", "SPECIFIEK VOORSCHRIFT", "OVERWEGING"]},
    {"naam": "Betrokkene-view", "objecttypen": [
        "BETROKKENE", "VTH-INSTANTIE", "NATUURLIJK PERSOON",
        "NIET-NATUURLIJK PERSOON", "VESTIGING"]},
    {"naam": "Verzoek-view", "objecttypen": [
        "VERZOEK", "TOESTEMMINGSAANVRAAG", "ACTIVITEITMELDING", "ACTIVITEITINFORMATIE"]},
    {"naam": "Toezicht- en handhaving-view", "objecttypen": [
        "CONTROLE", "BEVINDING", "OVERTREDING", "HANDHAVINGSMAATREGEL"]},
    {"naam": "Incident-view", "objecttypen": [
        "INCIDENT", "INCIDENTSIGNAAL", "KLACHT", "SIGNAAL",
        "INFORMATIE ONGEWOON VOORVAL", "HANDHAVINGSVERZOEK"]},
    {"naam": "Zaak- en Document-view", "objecttypen": [
        "ZAAK", "BESLUIT", "INFORMATIEOBJECT"]},
]


def _b(id, naam, houder, laag, openheid, standaard, vorm, objecttypen,
       toelichting, url, endpoint=None):
    return {"id": id, "naam": naam, "houder": houder, "laag": laag, "openheid": openheid,
            "standaard": standaard, "vorm": vorm, "objecttypen": objecttypen,
            "toelichting": toelichting, "url": url, "endpoint": endpoint}


BRONNEN = [
    # --- Rijk & landelijke registraties -------------------------------------------------
    _b("bag", "BAG — Basisregistratie Adressen en Gebouwen", "Kadaster", "rijk", "open",
       "IMBAG", "registratie + WFS/OGC API",
       ["PAND", "ADRESSEERBAAR OBJECT", "GEO-OBJECT"],
       "Landsdekkend en authentiek. Vult de Locatie-view vrijwel één-op-één; het pand waar een "
       "activiteit plaatsvindt is hier een echt object met een identificatie.",
       "https://www.pdok.nl/introductie/-/article/basisregistratie-adressen-en-gebouwen-ba-1",
       "https://service.pdok.nl/lv/bag/wfs/v2_0?request=GetCapabilities&service=WFS"),
    _b("bgt", "BGT — Basisregistratie Grootschalige Topografie", "Kadaster + bronhouders", "rijk", "open",
       "IMGeo", "registratie + OGC API Features",
       ["TOPOGRAFISCH OBJECT", "GEO-OBJECT"],
       "De grootschalige ondergrond waarop VTH-objecten worden gesitueerd. Bronhouders zijn "
       "gemeenten, provincies, waterschappen en RWS samen — zelf al een ketenregistratie.",
       "https://www.pdok.nl/introductie/-/article/basisregistratie-grootschalige-topografie-bgt-",
       "https://api.pdok.nl/lv/bgt/ogc/v1/collections?f=json"),
    _b("brk", "BRK — Kadastrale kaart", "Kadaster", "rijk", "open",
       "IMKAD", "registratie + WFS",
       ["KADASTRALE ONROERENDE ZAAK", "GEO-OBJECT"],
       "De kaart is open; de rechthebbende erachter is dat niet. Het CIM heeft de zakelijk "
       "gerechtigde nodig als BETROKKENE, en juist dat deel zit achter de balie.",
       "https://www.pdok.nl/introductie/-/article/kadastrale-kaart",
       "https://service.pdok.nl/kadaster/kadastralekaart/wfs/v5_0?request=GetCapabilities&service=WFS"),
    _b("rev", "REV — Register Externe Veiligheidsrisico's", "RIVM / IenW", "rijk", "open",
       "IMEV 3.0.2", "registratie + WFS/OGC API",
       ["VTH-OBJECT", "ACTIVITEIT", "GEO-OBJECT", "BETROKKENE"],
       "De meest CIM-achtige open bron: risicovolle activiteiten als objecten mét bronhouder, "
       "activiteit en geometrie. Aangeleverd door omgevingsdiensten — de datakwaliteit is "
       "daarmee een spiegel van de keten. Zie /wfs-kwaliteit.",
       "https://www.rev-portaal.nl/",
       "https://rev-portaal.nl/geoserver/wfs?service=WFS&request=GetCapabilities&version=2.0.0"),
    _b("rev_pdok", "REV productiefaciliteiten via PDOK", "RVO / RWS via PDOK", "rijk", "open",
       "OGC API Features", "OGC API Features",
       ["VTH-OBJECT", "GEO-OBJECT"],
       "Dezelfde werkelijkheid als het REV-portaal, andere ontsluiting en andere indeling "
       "(per sector-collection). Overlap zonder gedeelde sleutel — dit lab gebruikt beide.",
       "https://www.pdok.nl/",
       "https://api.pdok.nl/rws/productie-en-industrie-productiefaciliteiten/ogc/v1/collections?f=json"),
    _b("bekendmakingen", "Officiële bekendmakingen (KOOP, SRU-API)", "KOOP / Ministerie BZK", "rijk", "open",
       "STOP / SRU", "publicatie-repository",
       ["BESLUIT", "TOESTEMMING", "INFORMATIEOBJECT"],
       "Het grootste open venster op BESLUIT: een SRU-query op dt.type any \"vergunning\" geeft "
       "ruim 2,0 miljoen records, inclusief watervergunningen van waterschappen. Maar het is "
       "tekst, geen objectstructuur — de vergunning is vindbaar, niet bevraagbaar.",
       "https://www.officielebekendmakingen.nl/",
       "https://repository.overheid.nl/sru?operation=explain"),
    _b("dso_ozon", "DSO — Omgevingsdocumenten (Ozon Presenteren)", "DSO-LV / IenW", "rijk", "semi",
       "STOP/TPOD", "REST API met sleutel",
       ["ALGEMEEN VERBINDEND VOORSCHRIFT", "SPECIFIEK VOORSCHRIFT"],
       "Welke regels gelden op een plek — omgevingsplan, verordening, AMvB. Vraagt een API-key. "
       "Dit lab gebruikt het live in de vergunningen-chatbot.",
       "https://iplo.nl/digitaal-stelsel/", "https://omgevingswet.overheid.nl/"),
    _b("dso_tr", "DSO — Toepasbare regels (STTR/RTR)", "DSO-LV / IenW", "rijk", "semi",
       "STTR / RTR", "REST API met sleutel",
       ["ALGEMEEN VERBINDEND VOORSCHRIFT", "ACTIVITEIT"],
       "De vergunningcheck achter het Omgevingsloket. Vertaalt regels naar vragenbomen — "
       "conceptueel de brug tussen ACTIVITEIT en VERZOEK.",
       "https://iplo.nl/digitaal-stelsel/toepasbare-regels/", "https://omgevingswet.overheid.nl/"),
    _b("stelselcatalogus", "Stelselcatalogus Omgevingswet", "DSO-LV / Geonovum", "rijk", "open",
       "begrippenkader", "catalogus + API",
       ["ACTIVITEIT"],
       "De landelijke lijst met activiteiten uit Bal/Bkl. Eén van de drie activiteitvocabulaires "
       "die naast elkaar bestaan — zie de overlap bij ACTIVITEIT.",
       "https://stelselcatalogus.omgevingswet.overheid.nl/",
       "https://stelselcatalogus.omgevingswet.overheid.nl/"),
    _b("nhr", "NHR — Handelsregister", "KvK", "rijk", "semi",
       "NHR-gegevensmodel", "REST API, betaald",
       ["NIET-NATUURLIJK PERSOON", "VESTIGING", "BETROKKENE"],
       "De enige authentieke bron voor wie een activiteit uitvoert. Niet open: per bevraging "
       "betaald. Daarmee is BETROKKENE structureel duurder dan de rest van het model.",
       "https://developers.kvk.nl/", "https://developers.kvk.nl/"),
    _b("brp", "BRP — Basisregistratie Personen", "RvIG", "rijk", "gesloten",
       "BRP", "besloten registratie",
       ["NATUURLIJK PERSOON"],
       "Voor NATUURLIJK PERSOON is er per definitie geen open bron. Het model heeft het "
       "objecttype nodig; het open-datalandschap kan het nooit leveren.",
       "https://www.rvig.nl/brp", None),
    _b("roo", "Register van Overheidsorganisaties", "Logius / overheid.nl", "rijk", "open",
       "OIN", "register + zoekdienst",
       ["VTH-INSTANTIE"],
       "Wie is bevoegd gezag, met organisatie-identificatie. De enige open bron die "
       "VTH-INSTANTIE als organisatie beschrijft in plaats van als polygoon.",
       "https://organisaties.overheid.nl/", "https://organisaties.overheid.nl/"),
    _b("bro", "BRO — Basisregistratie Ondergrond", "TNO / IenW", "rijk", "open",
       "IMBRO", "registratie + API",
       ["ANDER GEO-OBJECT"],
       "Bodem en ondergrond: onmisbaar bij bodemtoezicht, maar in het CIM alleen te plaatsen "
       "als ANDER GEO-OBJECT. Het model heeft geen bodem-specifiek objecttype.",
       "https://basisregistratieondergrond.nl/", "https://basisregistratieondergrond.nl/"),
    _b("emissieregistratie", "Emissieregistratie / PRTR", "RIVM", "rijk", "open",
       "E-PRTR", "bedrijfsrapporten + open data",
       ["ACTIVITEITINFORMATIE"],
       "Emissies per bedrijf uit de jaarlijkse informatieplicht — een van de weinige plekken "
       "waar ACTIVITEITINFORMATIE daadwerkelijk openbaar is, zij het geaggregeerd en met vertraging.",
       "https://www.emissieregistratie.nl/",
       "https://www.emissieregistratie.nl/data/bedrijfsrapporten"),
    _b("emjv", "e-MJV — elektronisch Milieujaarverslag", "RVO / bevoegd gezag", "rijk", "semi",
       "E-PRTR", "indieningsvoorziening",
       ["ACTIVITEITINFORMATIE", "VERZOEK"],
       "De indieningskant van dezelfde plicht: hier komt de informatie binnen, in "
       "Emissieregistratie gaat een deel eruit. Twee gezichten van één VERZOEK.",
       "https://www.e-mjv.nl/", "https://www.e-mjv.nl/"),
    _b("samenmeten", "Samen Meten — sensordata", "RIVM", "rijk", "open",
       "SensorThings API", "OGC SensorThings API",
       ["SIGNAAL"],
       "Burger- en overheidssensoren als continue meetreeks. In CIM-termen het dichtst bij "
       "SIGNAAL: aanwijzing dat er iets aan de hand is, nog geen INCIDENT.",
       "https://samenmeten.nl/", "https://api-samenmeten.rivm.nl/v1.0/Things?$top=1"),
    _b("inspectieview", "Inspectieview Milieu", "ILT", "rijk", "gesloten",
       "Inspectieview", "besloten uitwisseling",
       ["CONTROLE", "BEVINDING", "OVERTREDING", "HANDHAVINGSMAATREGEL"],
       "De enige bron voor de hele Toezicht- en handhaving-view: ruim 2 miljoen inspecties over "
       "vijf jaar, wettelijk verankerd in de Omgevingswet, met ILT, NVWA, NLA, RDI, "
       "omgevingsdiensten, politie, havenbedrijven en waterschappen. Alleen voor toezichthouders.",
       "https://www.ilent.nl/onderwerpen/inspectieview-voor-inspectietaken", None),
    _b("dataoverheid", "data.overheid.nl", "KOOP / BZK", "rijk", "open",
       "DCAT-AP-DONL", "datasetcatalogus + CKAN API",
       ["INFORMATIEOBJECT"],
       "De vindplaats waarlangs de versnipperde gemeentelijke en provinciale VTH-datasets "
       "überhaupt te ontdekken zijn. Zelf geen inhoud, wel de sleutel tot de rest.",
       "https://data.overheid.nl/",
       "https://data.overheid.nl/data/api/3/action/package_search?rows=1"),

    # --- Rijkswaterstaat & landelijke diensten -----------------------------------------
    _b("lma", "LMA / AMICE — afvalmeldingen", "Rijkswaterstaat", "rws", "gesloten",
       "EVOA / Bal-meldingen", "meldingenregister",
       ["ACTIVITEITINFORMATIE", "ACTIVITEITUITVOERING"],
       "Ruim 2 miljoen meldingen per jaar over ontvangst en afgifte van bedrijfs- en gevaarlijk "
       "afval, gebruikt voor toezicht en handhaving. Gesloten; dit lab werkt daarom met de open "
       "CBS-proxy op provincieniveau (zie /afval).",
       "https://lma.nl/", "https://amice.lma.nl/Amice.WebApp/Home"),
    _b("ctd", "CTD — Centraal Toegangspunt Data Rijkswaterstaat", "Rijkswaterstaat", "rws", "semi",
       "ISO 19115 · Data3Sixty", "datasetcatalogus (beta)",
       ["INFORMATIEOBJECT"],
       "RWS bundelt hier zijn eigen data met per dataset een datakwaliteitslabel, ISO 19115-metadata "
       "en een oordeel-knop voor gebruikers. Toegang verschilt per vertrouwelijkheidsniveau. "
       "Geen automatische controle: robots.txt van het portaal staat crawlen niet toe.",
       "https://rijkswaterstaatdata.nl/beta/", None),
    _b("rws_wegenlijst", "Actuele Wegenlijst (CTD-data-API)", "Rijkswaterstaat", "rws", "open",
       "PostgREST · GeoJSON EPSG:28992", "REST-API zonder sleutel",
       ["ANDER GEO-OBJECT", "GEO-OBJECT", "VTH-INSTANTIE"],
       "246 wegvakken met rijkswegnummer, hectometerbereik, geometrie in RD én de beherende "
       "RWS-dienst en district. Filteren, sorteren, pagineren en exacte tellingen zitten er "
       "standaard in. Twee kolommen ctd_update/ctd_update_bron geven per rij de actualiteit — "
       "precies wat het REV mist. De index van de API staat uit, dus je moet de tabelnaam kennen.",
       "https://rijkswaterstaatdata.nl/beta/",
       "https://ctddata.rijkswaterstaatdata.nl/actuele_wegenlijst?limit=1"),
    _b("nwb", "NWB — Nationaal Wegenbestand", "Rijkswaterstaat", "rws", "open",
       "NWB", "WFS",
       ["ANDER GEO-OBJECT"],
       "Wegvakken als geo-object; in dit lab al gebruikt voor de geluid-use-case. Voor VTH "
       "relevant als drager van transportroutes en Basisnet-contouren.",
       "https://www.pdok.nl/", "https://service.pdok.nl/rws/nwbwegen/wfs/v1_0?request=GetCapabilities&service=WFS"),
    _b("waterinfo", "Waterinfo", "Rijkswaterstaat", "rws", "open",
       "Aquo", "meetreeksen + API",
       ["SIGNAAL"],
       "Waterstanden en waterkwaliteit als continue meting. Net als Samen Meten: signaalwaarde, "
       "geen incident — de vertaalslag van meting naar INCIDENT staat niet in het model.",
       "https://waterinfo.rws.nl/", "https://waterinfo.rws.nl/"),
    _b("risicokaart", "Risicokaart", "IPO / provincies / IenW", "rws", "open",
       "IMEV / ISOR", "viewer + kaartlagen",
       ["VTH-OBJECT", "GEO-OBJECT"],
       "De publieksversie van dezelfde risico-objecten als het REV. Derde ontsluiting van "
       "dezelfde werkelijkheid, opnieuw met een eigen presentatie.",
       "https://www.risicokaart.nl/", "https://www.risicokaart.nl/"),

    # --- Provincies ---------------------------------------------------------------------
    _b("prov_verordening", "Provinciale omgevingsverordeningen", "Provincies via DSO", "provincie", "open",
       "STOP/TPOD", "omgevingsdocument",
       ["ALGEMEEN VERBINDEND VOORSCHRIFT"],
       "Sinds de Omgevingswet gestandaardiseerd gepubliceerd — een van de weinige plekken waar "
       "decentrale regelgeving landelijk uniform bevraagbaar is.",
       "https://omgevingswet.overheid.nl/", None),
    _b("prov_ges", "GES-contouren & belaste woningen", "Provincies / GGD", "provincie", "open",
       "—", "geodatasets via NGR",
       ["VTH-OBJECT", "GEO-OBJECT"],
       "Gezondheidseffectscreening rond risicovolle bedrijven en infrastructuur. Afgeleide "
       "producten: geen VTH-objecten maar berekeningen daarover.",
       "https://www.nationaalgeoregister.nl/", None),

    # --- Waterschappen ------------------------------------------------------------------
    _b("damo", "DAMO — Data Afspraken Modelmatig Ondersteund", "Het Waterschapshuis", "waterschap", "semi",
       "DAMO / IMWA / Aquo", "gegevensknooppunt + WFS",
       ["VTH-OBJECT", "GEO-OBJECT", "ANDER GEO-OBJECT"],
       "Het gedeelde datamodel van alle waterschappen, gebouwd op IMWA, IMGeo, IMKL, GWSW en "
       "BGT, met Aquo voor de definities. Bevat o.a. lozingspunten — in CIM-termen VTH-objecten, "
       "maar met een eigen objectenhandboek dat nergens naar het CIM verwijst.",
       "https://damo.hetwaterschapshuis.nl/", "https://damo.hetwaterschapshuis.nl/"),
    _b("ws_verordening", "Waterschapsverordeningen", "Waterschappen via DSO", "waterschap", "open",
       "STOP/TPOD", "omgevingsdocument",
       ["ALGEMEEN VERBINDEND VOORSCHRIFT"],
       "De waterschapsregels in dezelfde standaard als het omgevingsplan — het stelsel werkt "
       "hier zoals bedoeld.",
       "https://omgevingswet.overheid.nl/", None),
    _b("watervergunning", "Watervergunningen in de bekendmakingen", "Waterschappen", "waterschap", "open",
       "STOP", "publicatie",
       ["TOESTEMMING", "BESLUIT"],
       "Watervergunningen worden als officiële publicatie bekendgemaakt en zijn zo landelijk "
       "vindbaar — dezelfde route als gemeentelijke besluiten, dezelfde beperking: tekst.",
       "https://www.officielebekendmakingen.nl/", None),

    # --- Omgevingsdiensten ---------------------------------------------------------------
    _b("od_grenzen", "Grenzen Omgevingsdiensten", "Omgevingsdiensten via NGR", "omgevingsdienst", "open",
       "—", "geodataset",
       ["VTH-INSTANTIE"],
       "Van de 29 open datasets met 'omgevingsdienst' gaat het merendeel over gebiedsgrenzen. "
       "Omgevingsdiensten zijn in open data vooral aanwezig als polygoon, nauwelijks als inhoud.",
       "https://data.overheid.nl/", None),
    _b("od_bodem", "Bodemonderzoek- en saneringslocaties", "Omgevingsdiensten / provincies", "omgevingsdienst", "open",
       "SIKB0101", "geodatasets per regio",
       ["VTH-OBJECT", "ANDER GEO-OBJECT"],
       "Bijvoorbeeld Bodemonderzoeklocaties Midden-Holland en Bodemsanering Spoedlocaties. "
       "Inhoudelijke VTH-data die wél open is — maar per regio, in eigen vorm.",
       "https://data.overheid.nl/", None),
    _b("od_rev_aanlevering", "REV-aanlevering door omgevingsdiensten", "Omgevingsdiensten", "omgevingsdienst", "open",
       "IMEV 3.0.2", "aanlevering aan landelijk register",
       ["VTH-OBJECT", "ACTIVITEIT", "BETROKKENE"],
       "De enige route waarlangs uitvoeringsdata van omgevingsdiensten structureel en landelijk "
       "open beschikbaar komt. Kwaliteit varieert sterk per bronhouder — meetbaar via /wfs-kwaliteit.",
       "https://www.rev-portaal.nl/", None),

    # --- Gemeenten -----------------------------------------------------------------------
    _b("zgw", "ZGW-API's (Zaken, Documenten, Besluiten, Catalogi)", "VNG / Common Ground", "gemeente", "gesloten",
       "ZGW-API's", "API-standaard per organisatie",
       ["ZAAK", "INFORMATIEOBJECT", "BESLUIT"],
       "De enige plek waar ZAAK en INFORMATIEOBJECT als échte objecten bestaan, met een "
       "landelijke standaard. Maar elke gemeente draait een eigen instantie achter eigen "
       "autorisatie: de standaard is landelijk, de data nergens.",
       "https://vng.nl/", None),
    _b("gem_vergunningen", "Gemeentelijke vergunningdatasets", "Gemeenten", "gemeente", "open",
       "—", "open datasets per gemeente",
       ["TOESTEMMING", "BESLUIT", "TOESTEMMINGSAANVRAAG"],
       "Den Haag publiceert letterlijk 'Wabo vergunningen' en 'Wabo beschikkingen'; Amsterdam, "
       "Eindhoven, Utrecht en Groningen hebben eigen omgevingsvergunning-sets. Bewijs dat het "
       "kan — en tegelijk bewijs dat het niet is afgesproken.",
       "https://data.overheid.nl/", None),
    _b("gem_mor", "Meldingen Openbare Ruimte (MOR)", "Gemeenten", "gemeente", "open",
       "—", "open datasets per gemeente",
       ["KLACHT", "SIGNAAL", "INCIDENTSIGNAAL"],
       "Twintig datasets van o.a. Nijmegen, Delft en Eindhoven. De Incident-view is dus niet wit "
       "maar versnipperd: elke gemeente een eigen vorm, geen koppeling aan een VTH-object.",
       "https://data.overheid.nl/", None),
    _b("gem_omgevingsplan", "Omgevingsplannen", "Gemeenten via DSO", "gemeente", "open",
       "STOP/TPOD", "omgevingsdocument",
       ["ALGEMEEN VERBINDEND VOORSCHRIFT", "SPECIFIEK VOORSCHRIFT"],
       "Landelijk uniform bevraagbaar via het DSO — in dit lab gebruikt voor 'welke regels "
       "gelden hier'.",
       "https://omgevingswet.overheid.nl/", None),
]

# Waarom bronnen die hetzelfde objecttype vullen tóch niet samenvallen.
OVERLAP_REDENEN = {
    "VTH-OBJECT": "Dezelfde fysieke werkelijkheid, vier identiteiten: het REV kent een risico-object, "
                  "BAG/BGT een pand, het NHR een vestiging, DAMO een waterobject. Geen gedeelde sleutel, "
                  "dus koppelen kan alleen op geometrie of adres — met alle valse treffers van dien.",
    "ACTIVITEIT": "Drie vocabulaires naast elkaar: Bal/Bkl-activiteiten uit de Stelselcatalogus, "
                  "evactiviteit in het REV, en SBI-codes in NHR en e-MJV. Alle drie beantwoorden "
                  "'wat gebeurt hier', geen enkele mapt op de andere.",
    "BESLUIT": "Drie dragers van hetzelfde besluit: landelijk als tekst in de bekendmakingen, "
               "gestructureerd maar besloten in de ZGW Besluiten-API, en incidenteel als open "
               "dataset bij een enkele gemeente.",
    "TOESTEMMING": "De vergunning zelf is landelijk vindbaar als publicatie, maar alleen bij een "
                   "handvol gemeenten als dataset. Wat de een publiceert, houdt de ander binnen.",
    "BETROKKENE": "Het NHR is authentiek maar betaald, het REV heeft een bronhouder-veld zonder "
                  "organisatie-identificatie, en het ROO kent alleen overheden. Drie halve antwoorden.",
    "VTH-INSTANTIE": "Het ROO beschrijft de organisatie, de NGR-dataset tekent het gebied van de "
                     "omgevingsdiensten, en de Actuele Wegenlijst van RWS zet de beherende dienst "
                     "per wegvak in een gewone kolom. Wie iets mag, en waar dat geldt, staan in "
                     "verschillende bronnen — en alleen bij RWS zitten ze in dezelfde rij.",
    "ANDER GEO-OBJECT": "De restbak van de Locatie-view, en juist daardoor het drukst bezet: BRO "
                        "(ondergrond), NWB en de Actuele Wegenlijst (wegen), DAMO (water) en "
                        "bodemlocaties belanden hier allemaal. Het model onderscheidt ze niet, "
                        "terwijl het in de uitvoering totaal verschillende objecten zijn.",
    "ACTIVITEITINFORMATIE": "Twee informatieplichten, twee stelsels, verschillend open: e-MJV/PRTR "
                            "voor emissies is deels openbaar, LMA/AMICE voor afval is dat niet.",
    "GEO-OBJECT": "Het best geregelde deel van het model: BAG, BGT, BRK en BRT vullen elkaar aan "
                  "in plaats van te concurreren. Hier werkt het stelsel zoals bedoeld.",
    "ALGEMEEN VERBINDEND VOORSCHRIFT": "Rijk, provincie, waterschap en gemeente publiceren allemaal "
                                       "in STOP/TPOD via het DSO — overlap zonder conflict, omdat de "
                                       "standaard vooraf is afgesproken.",
    "SIGNAAL": "Sensormetingen (Samen Meten, Waterinfo) en burgermeldingen (MOR) zijn allebei "
               "signalen, maar de stap van meting naar INCIDENT staat in geen enkele bron.",
}


def _view_van(objecttype: str) -> str | None:
    for v in VIEWS:
        if objecttype in v["objecttypen"]:
            return v["naam"]
    return None


def overlappen(bronnen: list | None = None) -> list[dict]:
    """Objecttypen die door meer dan één bron worden gevuld, meeste bronnen eerst."""
    bronnen = BRONNEN if bronnen is None else bronnen
    per_ot: dict[str, list[str]] = {}
    for b in bronnen:
        for ot in b["objecttypen"]:
            per_ot.setdefault(ot, []).append(b["id"])
    uit = [{"objecttype": ot, "view": _view_van(ot), "bronnen": ids,
            "reden": OVERLAP_REDENEN.get(ot, "")}
           for ot, ids in per_ot.items() if len(ids) > 1]
    uit.sort(key=lambda o: (-len(o["bronnen"]), o["objecttype"]))
    return uit


def dekking_per_view(bronnen: list | None = None) -> list[dict]:
    """Per view het aantal bronnen per openheidsklasse, plus de onbediende objecttypen."""
    bronnen = BRONNEN if bronnen is None else bronnen
    uit = []
    for v in VIEWS:
        ots = set(v["objecttypen"])
        raak = [b for b in bronnen if ots & set(b["objecttypen"])]
        gedekt = {ot for b in raak for ot in b["objecttypen"] if ot in ots}
        rij = {"view": v["naam"], "objecttypen": len(ots),
               "gedekt": len(gedekt), "zonder_bron": sorted(ots - gedekt)}
        for k in OPENHEID:
            rij[k] = sum(1 for b in raak if b["openheid"] == k)
        uit.append(rij)
    return uit


def catalogus() -> dict:
    """Alles wat de visualisatie nodig heeft, in één payload."""
    return {"lagen": LAGEN, "openheid": OPENHEID, "views": VIEWS, "bronnen": BRONNEN,
            "overlap": overlappen(), "dekking": dekking_per_view(),
            "bron_model": "Cim-VTH-Flo (Geonovum, werkversie 4 augustus 2026, CC BY 4.0)"}


async def check_endpoints(bronnen: list | None = None, timeout_s: float = 8.0, _get=None) -> dict:
    """Roep elk endpoint live aan. Alleen bronnen mét endpoint komen in het resultaat.

    `_get` is een injectiepunt voor tests; standaard httpx.AsyncClient.get.
    """
    bronnen = BRONNEN if bronnen is None else bronnen
    doelen = [b for b in bronnen if b.get("endpoint")]

    # PDOK staat op een IPv6-adres waarheen het pad vanaf deze machine regelmatig stilvalt.
    # curl valt dan terug op IPv4 (Happy Eyeballs), httpx doet dat niet — zonder retries meldt
    # de check vals-negatief 'onbereikbaar'. Met retries=3: 20 van 21 endpoints, en de enige
    # overblijver is een echte serverfout. Gemeten 2026-09-10.
    transport = httpx.AsyncHTTPTransport(retries=3)
    async with httpx.AsyncClient(timeout=timeout_s, follow_redirects=True,
                                 transport=transport) as client:
        get = _get or type(client).get

        async def een(b):
            try:
                r = await get(client, b["endpoint"])
                return b["id"], {"status": r.status_code, "ok": 200 <= r.status_code < 400}
            except Exception as exc:                       # netwerk, TLS, timeout, DNS
                return b["id"], {"status": None, "ok": False, "fout": type(exc).__name__}

        paren = await asyncio.gather(*(een(b) for b in doelen))
    return dict(paren)
