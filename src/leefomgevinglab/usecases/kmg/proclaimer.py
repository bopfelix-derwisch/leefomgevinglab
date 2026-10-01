"""De verantwoording bij deze pagina — een proclaimer, geen disclaimer.

Niet uitleggen waar we níet voor instaan, maar hoe dit gemaakt is en waar we wél voor instaan.

De tekst wordt opgebouwd uit dezelfde gegevens die de pagina voeden: het meetjaar, het aantal
metingen, de ophaaldatum en de bronnaam komen uit de meetset zelf. Daarmee kan wat er staat
niet uit de pas lopen met wat je ziet — een test dwingt dat af.
"""


def _metingen(meetset: dict) -> int:
    t = meetset.get("telling") or {}
    if t.get("meegeteld"):
        return int(t["meegeteld"])
    return sum(s.get("n", 0) for p in (meetset.get("punten") or [])
               for s in (p.get("stoffen") or []))


def bouw(meetset: dict, register_bron: dict, regels_bron: str,
         doelen_beschikbaar: bool) -> dict:
    """De vier kopjes van de proclaimer, met de getallen uit de data."""
    beschikbaar = bool(meetset.get("beschikbaar"))
    bron = meetset.get("bron") or {}
    houder = bron.get("houder") or "onbekende bronhouder"
    bronnaam = bron.get("naam") or "onbekende bron"
    jaar = meetset.get("meetjaar") or "onbekend jaar"
    opgehaald = meetset.get("opgehaald_op") or "onbekende datum"
    n = _metingen(meetset)
    punten = len(meetset.get("punten") or [])
    reg = (register_bron.get("bron") or {}).get("naam") or "onbekend register"
    hiaat = (meetset.get("telling") or {}).get("hiaatwaarden", 0)

    if beschikbaar:
        echt = (
            f"De gemeten waarden op deze pagina komen uit het {bronnaam} van {houder}. Het is "
            f"gevalideerde monitoring over meetjaar {jaar}: {n} metingen op {punten} meetpunten, "
            f"volgens het Aquo-informatiemodel Metingen. Wij hebben die set op {opgehaald} "
            f"opgehaald en verdicht tot een mediaan en een maximum per meetpunt en stof. "
            f"Daarbij zijn {hiaat} waarden met het kwaliteitsoordeel 'Hiaat waarde' overgeslagen; "
            f"die dragen een plaatshoudergetal en zijn geen meting. "
            f"De vergunningen komen uit de {reg} en worden bij elke weergave live opgehaald. "
            f"De regels die hier gelden komen live uit {regels_bron}."
        )
    else:
        echt = (
            f"Er zijn op dit moment **geen meetgegevens** geladen: {meetset.get('reden') or ''} "
            f"De vergunningen uit de {reg} en de regels uit {regels_bron} worden wel live "
            f"opgehaald en staan hieronder."
        )

    van_ons = (
        "De verdeling van een gemeten waarde over de vergunningen is een model van dit lab, geen "
        "gegeven uit een bron. Wij delen de vergunde vracht van elke bovenstroomse lozing door de "
        "jaarafvoer van het waterlichaam, en noemen wat overblijft 'bovenstrooms en diffuus'. "
        "Daar zit geen verblijftijd in, geen menging, geen afbraak en geen bezinking, en er wordt "
        "gerekend met de vergunde ruimte in plaats van met de werkelijke lozing. Omdat een "
        "vergunning zelden volledig wordt benut, is elke berekende bijdrage een bovengrens. "
        "De volgorde van de Maas-waterlichamen waarmee wij 'bovenstrooms' bepalen is eveneens "
        "door ons vastgelegd; de bron kent die volgorde niet."
    )

    if not doelen_beschikbaar:
        van_ons += (
            " Er zijn geen KRW-doelen geladen, dus deze pagina toont de metingen **zonder "
            "normoordeel**. Terugvallen op de illustratieve normen die dit lab elders gebruikt "
            "zou een echte meting tegen een verzonnen norm zetten; dat doen wij hier niet."
        )

    niet_mee = (
        "Deze pagina stelt niet vast wie een overschrijding teweegbrengt. Dat oordeel ligt bij "
        "het toezicht, dat daarvoor het vergunde beeld als meetlat gebruikt. Wat u hier ziet is "
        "die meetlat: welke vergunningen bovenstrooms liggen en hoeveel ruimte zij hebben. Een "
        "balk in de grafiek betekent 'kan bijdragen', niet 'heeft bijgedragen'."
    )

    gat = (
        "Twee van de drie lagen komen machinaal binnen: de regels uit het DSO en de vergunningen "
        "uit de Atlas. De metingen niet. De Digitale Delta API van Rijkswaterstaat geeft vandaag "
        "op elk data-eindpunt een 401, en de module van het Waterkwaliteitsportaal waarmee "
        "waterbeheerders hun metingen rechtstreeks via die API gaan publiceren wordt begin 2027 "
        "opgeleverd. Tot die tijd is de derde laag een momentopname die iemand met de hand "
        f"ophaalt — deze is van {opgehaald}. Leest u dit later: kijk of het inmiddels anders is."
    )

    return {
        "kopjes": [
            {"kop": "Wat u ziet en waar het vandaan komt", "tekst": echt},
            {"kop": "Wat van ons is", "tekst": van_ons},
            {"kop": "Wat u hier niet uit kunt afleiden", "tekst": niet_mee},
            {"kop": "Waar het gat zit", "tekst": gat},
        ],
        "gegevens": {"meetjaar": jaar, "metingen": n, "meetpunten": punten,
                     "opgehaald_op": opgehaald, "hiaatwaarden": hiaat,
                     "bron": bronnaam, "houder": houder, "register": reg,
                     "doelen_beschikbaar": doelen_beschikbaar},
    }
