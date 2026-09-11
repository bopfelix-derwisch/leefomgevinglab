"""De acht ketenstappen voor de directe lozing. Zelfde protocol als het Seveso-dossier."""
from ..ketenkern import lhso
from ..ketenkern.cim import obj
from . import aquo, beoordeling, toezicht
from . import bronnen as bronnen_mod

KENMERK = "RWS-2026-LOZ-0118"


def _stap(nr, naam, componenten, standaard, invoer, uitvoer, objecten, duiding):
    return {"nr": nr, "naam": naam, "componenten": componenten, "standaard": standaard,
            "invoer": invoer, "uitvoer": uitvoer, "cim": objecten, "duiding": duiding}


def stap1_aanvraag(ctx):
    c = ctx["casus"]
    a = c["aanvraag"]
    objecten = [
        obj("BETROKKENE", f"NL.KVK.{c['kvk']}", naam=c["bedrijf"], rol="initiatiefnemer/lozer"),
        obj("NIET-NATUURLIJK PERSOON", f"NL.KVK.{c['kvk']}", naam=c["bedrijf"], kvk=c["kvk"]),
        obj("VESTIGING", f"NL.KVK.{c['kvk']}.001", naam=c["vestiging"], adres=c["adres"]),
        obj("ACTIVITEIT", "bal.lozingsactiviteit-oppervlaktewater", naam=c["activiteit"],
            grondslag=c["grondslag"]),
        obj("ACTIVITEITUITVOERING", f"{a['nummer']}.uitvoering",
            activiteit="bal.lozingsactiviteit-oppervlaktewater",
            debiet_m3_per_uur=c["lozing"]["debiet_m3_per_uur"],
            parameters=[p["naam"] for p in c["parameters"]]),
        obj("VERZOEK", a["nummer"], soort=a["type"], ingediend=a["ingediend"], procedure=a["procedure"]),
        obj("TOESTEMMINGSAANVRAAG", a["nummer"], voor="lozingsactiviteit op een oppervlaktewaterlichaam",
            bijlagen=a["bijlagen"]),
    ]
    return _stap(1, "Aanvraag lozingsactiviteit via het DSO-loket", ["lozer", "dso_loket"],
                 "STTR/RTR",
                 {"lozer": c["bedrijf"], "locatie_rd": list(c["rd"])},
                 {"aanvraagnummer": a["nummer"], "activiteit": c["activiteit"],
                  "lozing": c["lozing"], "parameters": c["parameters"], "bijlagen": a["bijlagen"]},
                 objecten,
                 "De vergunningcheck leidt naar een wateractiviteit — lozen op een "
                 "oppervlaktewaterlichaam — en niet naar de milieubelastende activiteit. Dat "
                 "onderscheid bepaalt in de volgende stap wie erover gaat.")


def stap2_knip(ctx):
    c = ctx["casus"]
    cs = bronnen_mod.contextset(*c["rd"], straal_m=ctx["straal_m"], live=ctx["live"], haal=ctx["haal"])
    ctx["contextset"] = cs
    bg = bronnen_mod.bevoegd_gezag(cs)
    ctx["bevoegd_gezag"] = bg
    zaak = f"ZAAK-{KENMERK}"
    objecten = [
        obj("VTH-INSTANTIE", "NL.RWS", naam=bg["lozingsactiviteit"], rol="bevoegd gezag lozingsactiviteit",
            grondslag=bg["grondslag"]),
        obj("VTH-INSTANTIE", f"NL.GEM.{(bg['gemeente'] or 'onbekend')}",
            naam=bg["milieubelastende_activiteit"], rol="bevoegd gezag milieubelastende activiteit"),
        obj("ZAAK", zaak, zaaktype="Omgevingsvergunning lozingsactiviteit — regulier",
            gestart="2026-04-09", doorlooptijd_weken=8, status="in behandeling"),
        *[obj("INFORMATIEOBJECT", f"DOC-W{i:02d}", titel=b, bron=c["aanvraag"]["nummer"])
          for i, b in enumerate(c["aanvraag"]["bijlagen"], 1)],
    ]
    return _stap(2, "De knip: twee bevoegde gezagen",
                 ["knip", "gemeente_mba", "rws_bg", "rws_zaak"], "bevoegd-gezagregels Omgevingswet",
                 {"verzoek": c["aanvraag"]["nummer"]},
                 {"bevoegd_gezag": bg, "zaak": zaak,
                  "twee_besluiten": ["lozingsactiviteit (waterbeheerder)",
                                     "milieubelastende activiteit (gemeente)"]},
                 objecten,
                 f"Het bevoegd gezag is niet aangenomen maar afgeleid: {bg['grondslag']}. "
                 f"Het milieudeel blijft bij {bg['milieubelastende_activiteit']}. Eén fabriek, twee "
                 "besluiten, twee procedures — en geen koppelvlak dat ze op elkaar afstemt.")


def stap3_waterlichaam(ctx):
    c = ctx["casus"]
    cs = ctx["contextset"]
    x, y = c["rd"]
    objecten = [
        obj("VTH-OBJECT", f"NL.AQUO.{KENMERK}", naam=c["vestiging"], soort="lozingsobject",
            lozingspunt=c["lozing"]["lozingspunt"], rd=[x, y]),
        obj("GEO-OBJECT", f"{KENMERK}.lozingspunt", geometrie=f"POINT({x} {y})", crs="EPSG:28992"),
    ]
    if cs.get("waterlichaam"):
        objecten.append(obj("ANDER GEO-OBJECT", cs.get("owl_id") or f"{KENMERK}.water",
                            naam=cs["waterlichaam"], soort="KRW-oppervlaktewaterlichaam",
                            stroomgebiedsdistrict=cs.get("stroomgebiedsdistrict"),
                            bron="RWS KRW-WFS"))
    else:
        objecten.append(obj("ANDER GEO-OBJECT", f"{KENMERK}.water", naam=None,
                            soort="ontvangend waterlichaam onbekend",
                            bron="niet bepaald" if not cs.get("live") else "geen treffer"))
    return _stap(3, "Ontvangend waterlichaam via de RWS-bronnen",
                 ["waterbronnen", "ctd", "analyse"], "WFS · OGC API",
                 {"rd": [x, y], "straal_m": cs["straal_m"], "live": cs["live"]},
                 {"contextset": cs},
                 objecten,
                 (f"Live bepaald: de lozing komt in {cs['waterlichaam']} "
                  f"({cs['owl_id']}), stroomgebiedsdistrict {cs['stroomgebiedsdistrict']}, gemeente "
                  f"{cs['gemeente']}."
                  if cs.get("waterlichaam") else
                  "Zonder live-modus blijft het ontvangende waterlichaam onbekend.") +
                 " Het CIM heeft geen objecttype voor een ontvangend waterlichaam; het belandt in "
                 "ANDER GEO-OBJECT — dezelfde restbak die op de bronnenkaart al de drukste was.")


def stap4_beoordeling(ctx):
    c = ctx["casus"]
    cs = ctx["contextset"]
    toets = beoordeling.immissietoets(c, cs.get("waterlichaam"))
    vs = beoordeling.voorschriften(toets)
    ctx["toets"], ctx["voorschriften"] = toets, vs
    objecten = [
        obj("OVERWEGING", f"{KENMERK}.overweging",
            getoetst_aan=["ABM", "Handboek Immissietoets", "BBT", "ZZS-minimalisatieplicht"],
            verdunningsfactor=toets["verdunningsfactor"],
            knelpunten=toets["knelpunten"], zzs=toets["zzs"], indicatief=True,
            conclusie="Vergunning kan worden verleend onder voorschriften, met aanvullende "
                      "maatregelen voor de parameters die de toetswaarde overschrijden."),
        *[obj("SPECIFIEK VOORSCHRIFT", v["id"], tekst=v["tekst"], besluit=KENMERK) for v in vs],
    ]
    knel = ", ".join(toets["knelpunten"]) or "geen parameter"
    return _stap(4, "Beoordeling: ABM, immissietoets en ZZS", ["analyse", "beoordeling"],
                 "ABM · Handboek Immissietoets",
                 {"parameters": [p["naam"] for p in c["parameters"]],
                  "waterlichaam": cs.get("waterlichaam")},
                 {"immissietoets": toets, "voorschriften": vs},
                 objecten,
                 (f"Verdunningsfactor {toets['verdunningsfactor']} op basis van een jaargemiddeld "
                  f"debiet; na verdunning overschrijdt {knel} de toetswaarde. "
                  if toets["knelpunten"] else
                  f"Verdunningsfactor {toets['verdunningsfactor']}: het ontvangende water is zó groot "
                  "dat geen enkele parameter de toetswaarde nog nadert. Dat is geen detail maar de "
                  "kern van dit dossier — op een rivier van dit formaat bijt de immissietoets niet, "
                  f"en zit de werkelijke beperking in {toets['bindend']}. Op een klein regionaal water "
                  "met een fractie van dit debiet zou dezelfde lozing er heel anders uitkomen. ") +
                 f"{', '.join(toets['zzs']) or 'Geen stof'} valt onder de minimalisatieplicht. "
                 "De toetswaarden hier zijn illustratief gekozen om de keten te laten rekenen — het "
                 "zijn niet de wettelijke normen, en dit is geen ABM-toets.")


def stap5_besluit(ctx):
    c = ctx["casus"]
    cs = ctx["contextset"]
    bg = ctx["bevoegd_gezag"]
    doc = aquo.bouw_besluit(c, ctx["toets"], ctx["voorschriften"], KENMERK,
                            cs.get("waterlichaam"), bg["lozingsactiviteit"])
    validatie = aquo.valideer(doc)
    ctx["document"], ctx["validatie"] = doc, validatie
    objecten = [
        obj("TOESTEMMING", KENMERK, soort="omgevingsvergunning lozingsactiviteit",
            verleend_aan=c["bedrijf"], inwerkingtreding="2026-06-25"),
        obj("BESLUIT", KENMERK, soort="verleningsbesluit", kenmerk=KENMERK,
            bekendgemaakt_via="LVBB / officiële bekendmakingen", standaard=doc["standaard"]),
    ]
    return _stap(5, "Besluit als STOP/TPOD met Aquo-annotaties",
                 ["beoordeling", "plansysteem", "aquo_tpod", "lvbb"], "STOP/TPOD (voorgesteld)",
                 {"overweging": f"{KENMERK}.overweging", "voorschriften": len(ctx["voorschriften"])},
                 {"document": doc, "validatie": validatie},
                 objecten,
                 f"Het besluit draagt zijn eigen gegevens: {validatie['verplicht']} verplichte "
                 "annotaties uit Aquo, waaronder de emissiegrenswaarde per parameter en de "
                 "meetverplichting — precies de twee dingen waar een toezichthouder later op moet "
                 "kunnen sturen, en die nu in lopende tekst staan.")


def stap6_register(ctx):
    reg = aquo.naar_register(ctx["document"])
    ctx["register"] = reg
    cs = ctx["contextset"]
    x, y = ctx["casus"]["rd"]
    objecten = [
        obj("VTH-OBJECT", f"NL.AQUO.{KENMERK}", herkomst="besluit",
            velden_uit_besluit=reg["uit_besluit"], los_aan_te_leveren=reg["los_aan_te_leveren"]),
        obj("GEO-OBJECT", f"NL.AQUO.{KENMERK}.lozingspunt", geometrie=f"POINT({x} {y})",
            crs="EPSG:28992", herkomst="annotatie Lozingspunt"),
        obj("ACTIVITEIT", "bal.lozingsactiviteit-oppervlaktewater",
            herkomst="annotatie Lozingsactiviteit"),
    ]
    return _stap(6, "Landing in het voorgestelde Register Lozingen",
                 ["plansysteem", "register_lozingen"], "TPOD",
                 {"document": ctx["document"]["kenmerk"]},
                 {"record": reg["record"], "herkomst": reg["herkomst"],
                  "uit_besluit": reg["uit_besluit"], "los_aan_te_leveren": reg["los_aan_te_leveren"],
                  "register_bestaat": reg["register_bestaat"], "opmerking": reg["opmerking"]},
                 objecten,
                 f"{len(reg['uit_besluit'])} van de {len(aquo.AQUO_VERPLICHT)} Aquo-eigenschappen "
                 "vallen rechtstreeks uit het besluit te lezen. Alleen: er is geen register om ze in "
                 f"te zetten. Na bekendmaking blijft van {cs.get('waterlichaam') or 'dit waterlichaam'} "
                 "geen optelbaar beeld over van wie er allemaal op loost.")


def stap7_toezicht(ctx):
    bev = toezicht.bevindingen(ctx["casus"], ctx["toets"])
    ctx["bevindingen"] = bev
    controle = f"CTRL-{KENMERK}-01"
    cs = ctx["contextset"]
    objecten = [
        obj("CONTROLE", controle, aanleiding="periodieke controle lozingsactiviteit",
            sporen=list(toezicht.SPOREN), datum="2027-05-12", toezichthouder="Rijkswaterstaat",
            voorbereid_op=f"NL.AQUO.{KENMERK}", meetnet=cs.get("waterlichaam")),
        *[obj("BEVINDING", b["id"], spoor=b["spoor"], oordeel=b["oordeel"],
              constatering=b["constatering"], voorschrift=b["voorschrift"], controle=controle)
          for b in bev],
    ]
    return _stap(7, "Toezicht en monitoring op het waterlichaam",
                 ["register_lozingen", "toezicht", "meetnet"], "Aquo · IM Metingen",
                 {"vergund_beeld": f"NL.AQUO.{KENMERK}"},
                 {"controle": controle, "bevindingen": bev, "sporen": list(toezicht.SPOREN)},
                 objecten,
                 "Drie sporen in plaats van de LBR-pijlers: administratief, meetgegevens en de "
                 "technische staat van de voorziening. Het middelste spoor is wat dit dossier "
                 "onderscheidt van externe veiligheid — het effect van deze vergunning wordt "
                 "daadwerkelijk gemeten, alleen hangt die meetreeks niet aan de vergunning die hem "
                 "veroorzaakt.")


def stap8_handhaving(ctx):
    overtredingen, maatregelen, objecten = [], [], []
    for b in ctx["bevindingen"]:
        if not toezicht.is_overtreding(b):
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
    return _stap(8, "Handhaving volgens de LHSO",
                 ["toezicht", "lhso", "handhavingsbesluit", "register_lozingen"],
                 "LHSO-interventiematrix",
                 {"bevindingen": [b["id"] for b in ctx["bevindingen"]]},
                 {"overtredingen": overtredingen, "maatregelen": maatregelen,
                  "handhavingsbesluit": besluit,
                  "terugkoppeling": {"naar": "Register Lozingen", "wat": "naleefgedrag en vrachten",
                                     "status": "kan niet — het register bestaat niet"}},
                 objecten,
                 (f"{len(overtredingen)} van de {len(ctx['bevindingen'])} bevindingen zijn een "
                  f"overtreding; de zwaarste valt in cel {zwaarste['cel']} en leidt tot "
                  f"'{zwaarste['interventie']}'." if zwaarste else "Geen overtredingen.") +
                 " Dezelfde matrix als bij Seveso — de handhaving is wél geüniformeerd, ook al is "
                 "de rest van de keten dat niet.")


ALLE = [stap1_aanvraag, stap2_knip, stap3_waterlichaam, stap4_beoordeling,
        stap5_besluit, stap6_register, stap7_toezicht, stap8_handhaving]
