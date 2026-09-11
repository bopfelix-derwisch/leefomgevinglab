"""De acht ketenstappen. Elke stap krijgt de context, levert objecten en vertelt wat er gebeurde.

Protocol per stap: nr, naam, componenten (uit de architectuurplaat), standaard, invoer,
uitvoer, cim (de objecten die ontstaan) en een duiding in gewone taal.
"""
from . import bronnen as bronnen_mod
from . import lbr, lhso, tpod
from .cim import obj

KENMERK = "OD-2026-SEV-0417"

VOORSCHRIFTEN = [
    {"id": "V-01", "tekst": "Drukhouders en opslagtanks worden herkeurd volgens het keurschema; de "
                            "herkeuringstermijn wordt niet overschreden."},
    {"id": "V-02", "tekst": "De verlading van ammoniak vindt uitsluitend plaats met een gesloten "
                            "verlaadsysteem met dodemansknop."},
    {"id": "V-03", "tekst": "Het veiligheidsbeheerssysteem wordt ten minste jaarlijks beoordeeld, en "
                            "bij iedere wijziging van de installatie."},
    {"id": "V-04", "tekst": "Bijna-ongevallen worden geregistreerd en binnen vier weken geëvalueerd."},
    {"id": "V-05", "tekst": "Binnen het gifwolkaandachtsgebied worden geen nieuwe zeer kwetsbare "
                            "gebouwen toegelaten zonder instemming van het bevoegd gezag."},
]


def _stap(nr, naam, componenten, standaard, invoer, uitvoer, objecten, duiding):
    return {"nr": nr, "naam": naam, "componenten": componenten, "standaard": standaard,
            "invoer": invoer, "uitvoer": uitvoer, "cim": objecten, "duiding": duiding}


def stap1_aanvraag(ctx):
    c = ctx["casus"]
    a = c["aanvraag"]
    objecten = [
        obj("BETROKKENE", f"NL.KVK.{c['kvk']}", naam=c["bedrijf"], rol="initiatiefnemer"),
        obj("NIET-NATUURLIJK PERSOON", f"NL.KVK.{c['kvk']}", naam=c["bedrijf"], kvk=c["kvk"]),
        obj("VESTIGING", f"NL.KVK.{c['kvk']}.001", naam=c["vestiging"], adres=c["adres"]),
        obj("ACTIVITEIT", "bal.seveso-inrichting", naam=c["activiteit"], grondslag=c["grondslag"]),
        obj("ACTIVITEITUITVOERING", f"{a['nummer']}.uitvoering", activiteit="bal.seveso-inrichting",
            drempel=c["drempel"], stoffen=[s["naam"] for s in c["stoffen"]]),
        obj("VERZOEK", a["nummer"], soort=a["type"], ingediend=a["ingediend"], procedure=a["procedure"]),
        obj("TOESTEMMINGSAANVRAAG", a["nummer"], voor="exploiteren Seveso-inrichting",
            bijlagen=a["bijlagen"]),
    ]
    return _stap(1, "Aanvraag via het DSO-loket", ["initiatiefnemer", "dso_loket"], "STTR/RTR",
                 {"initiatiefnemer": c["bedrijf"], "locatie_rd": list(c["rd"])},
                 {"aanvraagnummer": a["nummer"], "activiteit": c["activiteit"],
                  "procedure": a["procedure"], "bijlagen": a["bijlagen"],
                  "stoffen": c["stoffen"], "installaties": c["installaties"]},
                 objecten,
                 "De vergunningcheck leidt naar één activiteit. Alle installaties samen vormen één "
                 "milieubelastende activiteit, met gecumuleerde risico's — dat is wat een "
                 "Seveso-inrichting onderscheidt van een verzameling losse activiteiten.")


def stap2_zaak(ctx):
    c = ctx["casus"]
    nummer = c["aanvraag"]["nummer"]
    zaak = f"ZAAK-{KENMERK}"
    objecten = [
        obj("ZAAK", zaak, zaaktype="Omgevingsvergunning MBA — uitgebreid", gestart="2026-03-03",
            doorlooptijd_weken=26, status="in behandeling"),
        obj("VTH-INSTANTIE", "NL.OD.SEVESO", naam=c["uitvoering"],
            bevoegd_gezag=c["bevoegd_gezag"], rol="behandelend namens bevoegd gezag"),
        *[obj("INFORMATIEOBJECT", f"DOC-{i:02d}", titel=b, bron=nummer)
          for i, b in enumerate(c["aanvraag"]["bijlagen"], 1)],
    ]
    return _stap(2, "Zaak bij de omgevingsdienst", ["dso_samenwerken", "zaaksysteem"],
                 "ZGW Zaken/Documenten",
                 {"verzoek": nummer},
                 {"zaak": zaak, "zaaktype": "Omgevingsvergunning MBA — uitgebreid",
                  "documenten": len(c["aanvraag"]["bijlagen"]),
                  "behandelaar": c["uitvoering"], "bevoegd_gezag": c["bevoegd_gezag"]},
                 objecten,
                 "Het VERZOEK uit het DSO wordt een ZAAK. Bevoegd gezag blijft Gedeputeerde Staten; "
                 "de uitvoering ligt bij een Seveso-omgevingsdienst. Dit is de enige plek in de keten "
                 "waar ZAAK en INFORMATIEOBJECT als echte objecten bestaan — achter eigen autorisatie.")


def stap3_contextset(ctx):
    c = ctx["casus"]
    x, y = c["rd"]
    cs = bronnen_mod.contextset(x, y, straal_m=ctx["straal_m"], live=ctx["live"], haal=ctx["haal"])
    ctx["contextset"] = cs
    n_rev = sum(v for v in cs["rev"].values() if isinstance(v, int))
    objecten = [
        obj("VTH-OBJECT", f"NL.IMEV.{KENMERK}", naam=c["vestiging"], soort="Seveso-inrichting",
            rd=[x, y]),
        obj("GEO-OBJECT", f"{KENMERK}.locatie", geometrie=f"POINT({x} {y})", crs="EPSG:28992"),
        obj("PAND", f"{KENMERK}.panden", aggregaat=True, aantal=cs["bag"].get("panden"),
            binnen_m=cs["straal_m"], bron="BAG via PDOK" if cs["live"] else "niet bevraagd"),
        obj("ADRESSEERBAAR OBJECT", f"{KENMERK}.verblijfsobjecten", aggregaat=True,
            aantal=cs["bag"].get("verblijfsobjecten"), binnen_m=cs["straal_m"],
            bron="BAG via PDOK" if cs["live"] else "niet bevraagd"),
        *[obj("VTH-OBJECT", f"{KENMERK}.omgeving.{k.replace(' ', '_')}", aggregaat=True,
              soort=k, aantal=v, binnen_m=cs["straal_m"], bron="REV-WFS")
          for k, v in cs["rev"].items() if isinstance(v, int) and v],
    ]
    return _stap(3, "Contextset via Data.OD", ["bronnen", "dataod", "analyse"],
                 "WFS/OGC API",
                 {"rd": [x, y], "straal_m": cs["straal_m"], "live": cs["live"]},
                 {"contextset": cs, "rev_objecten_in_de_buurt": n_rev},
                 objecten,
                 ("Live opgehaald bij de echte bronnen: " if cs["live"] else "Overgeslagen (geen live-modus): ") +
                 (f"{n_rev} REV-objecten en {cs['bag'].get('panden')} panden binnen {cs['straal_m']} m."
                  if cs["live"] else "de contextset blijft leeg.") +
                 (" Niet alle bronnen antwoordden; de contextset is onvolledig." if not cs["volledig"] and cs["live"] else ""))


def stap4_beoordeling(ctx):
    c = ctx["casus"]
    gebieden = tpod.afstanden_voor(c)
    ctx["aandachtsgebieden"] = gebieden
    cs = ctx["contextset"]
    grootste = max(g["afstand_m"] for g in gebieden)
    panden = cs["bag"].get("panden")
    objecten = [
        obj("OVERWEGING", f"{KENMERK}.overweging",
            getoetst_aan=["Bal §3.3.1", "Bkl afdeling 5.1 — aandachtsgebieden"],
            aandachtsgebieden=[g["soort"] for g in gebieden],
            grootste_afstand_m=grootste,
            panden_binnen_invloedsgebied=panden,
            indicatief=True,
            conclusie="Vergunning kan worden verleend onder voorschriften; het "
                      "gifwolkaandachtsgebied reikt tot buiten de inrichtingsgrens."),
        *[obj("SPECIFIEK VOORSCHRIFT", v["id"], tekst=v["tekst"], besluit=KENMERK)
          for v in VOORSCHRIFTEN],
    ]
    return _stap(4, "Beoordeling en afstandstoets", ["analyse", "beoordeling"], "Bal · Bkl",
                 {"stoffen": [s["naam"] for s in c["stoffen"]], "contextset": "stap 3"},
                 {"aandachtsgebieden": gebieden, "grootste_afstand_m": grootste,
                  "panden_binnen_straal": panden, "voorschriften": VOORSCHRIFTEN,
                  "indicatief": True},
                 objecten,
                 f"De maatgevende stof is ammoniak; het gifwolkaandachtsgebied van {grootste} m is "
                 "bepalend en reikt tot buiten de inrichting. De afstanden hier zijn indicatief — een "
                 "echte QRA rekent met scenario's, weerklassen en faalfrequenties. Dit is ook de stap "
                 "die de OVERWEGING oplevert: het enige CIM-objecttype waarvoor nergens een bron bestaat.")


def stap5_besluit(ctx):
    c = ctx["casus"]
    doc = tpod.bouw_besluit(c, ctx["aandachtsgebieden"], VOORSCHRIFTEN, KENMERK)
    validatie = tpod.valideer(doc)
    ctx["document"], ctx["validatie"] = doc, validatie
    objecten = [
        obj("TOESTEMMING", KENMERK, soort="omgevingsvergunning MBA", verleend_aan=c["bedrijf"],
            inwerkingtreding="2026-05-14"),
        obj("BESLUIT", KENMERK, soort="verleningsbesluit", kenmerk=KENMERK,
            bekendgemaakt_via="LVBB / officiële bekendmakingen", standaard=doc["standaard"]),
    ]
    return _stap(5, "Besluit als STOP/TPOD-document",
                 ["beoordeling", "plansysteem", "imev_tpod", "lvbb"], "STOP/TPOD (voorgesteld)",
                 {"overweging": f"{KENMERK}.overweging", "voorschriften": len(VOORSCHRIFTEN)},
                 {"document": doc, "validatie": validatie},
                 objecten,
                 f"Het besluit draagt zelf de brongegevens: {validatie['verplicht']} verplichte "
                 "annotaties, allemaal geplaatst. Let op dat dit een voorgesteld profiel is — "
                 "STOP/TPOD kent vandaag geen toepassingsprofiel voor een vergunningbesluit.")


def stap6_rev(ctx):
    rev = tpod.naar_rev(ctx["document"])
    ctx["rev"] = rev
    c = ctx["casus"]
    x, y = c["rd"]
    objecten = [
        obj("VTH-OBJECT", f"NL.IMEV.{KENMERK}", herkomst="besluit", velden_uit_besluit=rev["uit_besluit"],
            los_aan_te_leveren=rev["los_aan_te_leveren"]),
        obj("GEO-OBJECT", f"NL.IMEV.{KENMERK}.geometrie", geometrie=f"POINT({x} {y})",
            crs="EPSG:28992", herkomst="annotatie Locatie"),
        obj("ACTIVITEIT", "bal.seveso-inrichting", herkomst="annotatie Activiteit",
            vervangt="eigen REV-activiteitenlijst"),
    ]
    return _stap(6, "Landing in het omgebouwde REV", ["plansysteem", "rev_nieuw"], "TPOD",
                 {"document": ctx["document"]["kenmerk"]},
                 {"record": rev["record"], "herkomst": rev["herkomst"],
                  "uit_besluit": rev["uit_besluit"], "los_aan_te_leveren": rev["los_aan_te_leveren"]},
                 objecten,
                 f"{len(rev['uit_besluit'])} van de {len(tpod.IMEV_VERPLICHT)} IMEV-eigenschappen komen "
                 "rechtstreeks uit het besluit; de rest zou nog apart moeten worden geleverd. In de "
                 "huidige route komt álles apart — inclusief het verschil in kwaliteit per bronhouder "
                 "dat de WFS-check meet.")


def stap7_toezicht(ctx):
    bev = lbr.bevindingen(ctx["casus"])
    ctx["bevindingen"] = bev
    controle = f"CTRL-{KENMERK}-01"
    objecten = [
        obj("CONTROLE", controle, aanleiding="reguliere Seveso-inspectie", methodiek="LBR",
            pijlers=list(lbr.PIJLERS), datum="2027-02-18",
            voorbereid_op=f"NL.IMEV.{KENMERK}", team=["Seveso-OD", "NLA", "veiligheidsregio"]),
        *[obj("BEVINDING", b["id"], pijler=b["pijler"], oordeel=b["oordeel"],
              constatering=b["constatering"], voorschrift=b["voorschrift"], controle=controle)
          for b in bev],
    ]
    return _stap(7, "Toezicht in GIR volgens de LBR", ["rev_nieuw", "gir", "lbr"],
                 "GIR · Systeem/Techniek/Cultuur",
                 {"risicobeeld": f"NL.IMEV.{KENMERK}"},
                 {"controle": controle, "bevindingen": bev},
                 objecten,
                 "Het inspectieteam bereidt voor op het risicobeeld uit het register en legt langs de "
                 "drie LBR-pijlers vast wat het aantreft. Elke bevinding verwijst naar een voorschrift "
                 "uit het besluit van stap 5 — daarmee is de lus tussen vergunnen en handhaven gesloten.")


def stap8_handhaving(ctx):
    overtredingen, maatregelen, objecten = [], [], []
    for b in ctx["bevindingen"]:
        if not lbr.is_overtreding(b):
            continue
        iv = lhso.interventie(b["gedrag"], b["gevolgen"])
        oid = b["id"].replace("BEV", "OVT")
        mid = b["id"].replace("BEV", "HHM")
        overtredingen.append({"id": oid, "bevinding": b["id"], "voorschrift": b["voorschrift"]})
        maatregelen.append({"id": mid, **iv})
        objecten += [
            obj("OVERTREDING", oid, bevinding=b["id"], voorschrift=b["voorschrift"],
                omschrijving=b["constatering"]),
            obj("HANDHAVINGSMAATREGEL", mid, overtreding=oid, cel=iv["cel"],
                interventie=iv["interventie"], spoor=iv["spoor"], grondslag="LHSO"),
        ]
    besluit = f"HHB-{KENMERK}-01"
    objecten.append(obj("BESLUIT", besluit, soort="handhavingsbesluit",
                        maatregelen=[m["id"] for m in maatregelen],
                        bekendgemaakt_via="LVBB / officiële bekendmakingen"))
    zwaarste = max(maatregelen, key=lambda m: m["zwaarte"]) if maatregelen else None
    return _stap(8, "Handhaving volgens de LHSO", ["lbr", "lhso", "handhavingsbesluit", "rev_nieuw"],
                 "LHSO-interventiematrix",
                 {"bevindingen": [b["id"] for b in ctx["bevindingen"]]},
                 {"overtredingen": overtredingen, "maatregelen": maatregelen,
                  "handhavingsbesluit": besluit,
                  "terugkoppeling": {"naar": f"NL.IMEV.{KENMERK}", "wat": "naleefgedrag",
                                     "status": "in het doelbeeld nieuw — deze lus loopt vandaag nergens"}},
                 objecten,
                 (f"{len(overtredingen)} van de {len(ctx['bevindingen'])} bevindingen zijn een overtreding; "
                  f"de zwaarste valt in cel {zwaarste['cel']} van de interventiematrix en leidt tot "
                  f"'{zwaarste['interventie']}'." if zwaarste else "Geen bevinding leidt tot een overtreding.") +
                 " Een aandachtspunt is geen overtreding — dat onderscheid maakt de LBR expliciet.")


ALLE = [stap1_aanvraag, stap2_zaak, stap3_contextset, stap4_beoordeling,
        stap5_besluit, stap6_rev, stap7_toezicht, stap8_handhaving]
