"""Welke vergunningen kúnnen bijdragen aan een gemeten waarde, en hoeveel?

Dit is het deel waar deze pagina betrouwbaar of onbetrouwbaar wordt, dus het voorbehoud staat
in de uitkomst en niet alleen in de documentatie.

Wat het model doet: van elke vergunde vracht bovenstrooms van het meetpunt de bijdrage aan de
concentratie berekenen, door de vracht te delen door de jaarafvoer van het waterlichaam. Wat
overblijft tussen de som daarvan en de gemeten waarde heet 'bovenstrooms en diffuus' — dat
omvat buitenlandse bronnen, landbouw, riooloverstorten en atmosferische depositie.

Wat het model niet doet: geen verblijftijd, geen menging, geen afbraak of bezinking, en geen
rekening met het moment van lozen tegenover het moment van meten. Het rekent bovendien met de
vergúnde ruimte, niet met de werkelijke lozing, en een vergunning wordt zelden volledig benut.
De uitkomst is daarmee een bovengrens.

En het belangrijkste: dit is géén vaststelling van wie een overschrijding veroorzaakt. De
DSO-folder waar dit idee vandaan komt zegt het zelf — toezicht stelt dat vast, met het vergunde
beeld als meetlat. Deze module levert de meetlat.
"""

SECONDEN_PER_JAAR = 31_536_000

# De Maas stroomafwaarts. Namen uit de KRW-vlaklaag van RWS, nagekeken 2026-10-01.
# Dit is een keuze van dit lab: de bron kent geen expliciete volgorde, alleen losse
# waterlichamen. Zijtakken en kanalen staan er bewust niet in — die zouden een
# stroomschema vergen in plaats van een lijst.
STROOMVOLGORDE = [
    ("NL91BOM", "Bovenmaas"),
    ("NL91GM", "Grensmaas"),
    ("NL91ZM", "Zandmaas"),
    ("NL91BM", "Bedijkte Maas"),
    ("NL94_5", "Beneden Maas"),
    ("NL94_6", "Bergsche Maas"),
    ("NL94_1", "Haringvliet-oost"),
    ("NL94_11", "Haringvliet-west"),
]

_INDEX = {code: i for i, (code, _naam) in enumerate(STROOMVOLGORDE)}

# De meetset levert per stof zijn eigen eenheid. Intern rekenen wij in milligram per liter;
# dit zijn de factoren waarmee een uitkomst in mg/l naar de eenheid van de meting gaat.
EENHEIDSFACTOR = {"mg/l": 1.0, "ug/l": 1000.0, "µg/l": 1000.0}

VOORBEHOUD = (
    "Deze verdeling is een bovengrens, berekend met een sterk versimpeld model van dit lab: de "
    "vergunde vracht gedeeld over de jaarafvoer van het waterlichaam, zonder verblijftijd, "
    "menging of afbraak. Een vergunning wordt zelden volledig benut, dus de werkelijke bijdrage "
    "ligt lager. Welk aandeel aan wie toekomt stelt het toezicht vast, niet deze pagina."
)


def sleutel_post(post: dict, index: int) -> str:
    """Stabiele sleutel voor een registerpost: kenmerk, anders locatiecode, anders de positie.

    Niet elke Atlas-post draagt een `kenmerk` — de Atlas-connector behoudt met opzet de posten
    zonder kenmerk (zie `smwk_atlas.py`), waaronder vier rioolwaterzuiveringen. Een sleutel die
    bij een leeg kenmerk op `""` uitkomt, laat die posten stil uit elke opzoek-mapping wegvallen.
    Dezelfde sleutel moet aan beide kanten van de toerekening gebruikt worden: bij het opbouwen
    van `waterlichaam_per_post` (in `service.py`) én hier bij het opzoeken ervan in `bijdragen()`.
    """
    return post.get("kenmerk") or post.get("locatiecode") or f"#{index}"


def is_bovenstrooms(waterlichaam: str, meetpunt_waterlichaam: str) -> bool:
    """Ligt `waterlichaam` bovenstrooms van het meetpunt, of is het hetzelfde?

    Een onbekend waterlichaam telt niet mee: dan weten we de richting niet, en meetellen zou
    een bijdrage suggereren die we niet kunnen onderbouwen.
    """
    a, b = _INDEX.get(waterlichaam), _INDEX.get(meetpunt_waterlichaam)
    if a is None or b is None:
        return False
    return a <= b


def bijdragen(gemeten: float, parameter: str, register: list[dict],
              waterlichaam_meetpunt: str, waterlichaam_per_post: dict[str, str],
              debiet_m3_s: float, eenheid: str = "mg/l",
              parameter_code: str | None = None) -> dict:
    """Per vergunning de bovengrens van de bijdrage aan de gemeten concentratie, plus wat overblijft.

    Er wordt intern in mg/l gerekend, maar de uitkomst staat in `eenheid` — de eenheid van de
    meting zelf, want niet elke stof in de meetset is mg/l.

    `parameter_code` is de Aquo-code van de gemeten stof. Staat hij er, dan wordt de vergunde
    vracht op die code opgezocht in `post["vrachten_aquo"]`; anders valt de opzoeking terug op de
    Nederlandse omschrijving in `post["vrachten"]`. Die terugval blijft bestaan omdat niet elk
    voorschrift te codificeren is — zie `lozingsmodel.py`.

    `waterlichaam_per_post` wordt opgezocht via `sleutel_post()` — dus op `kenmerk`, en bij een
    leeg kenmerk op `locatiecode` of de positie in `register`. Een post zonder bekend
    waterlichaam (de sleutel zit niet in `waterlichaam_per_post`) telt niet mee; dat is geen gok
    maar een bewuste, zichtbare uitsluiting (zie `service._waterlichaam_per_vergunning`).

    Sleutels in de uitkomst:
    - posten[].bijdrage_bovengrens: bovengrens van de concentratiebijdrage, in `eenheid`
    - som_bovengrens: som van alle bijdragen, in `eenheid`
    - restant: wat overblijft (bovenstrooms en diffuus), in `eenheid`
    - eenheid: de eenheid waarin bijdrage_bovengrens, som_bovengrens en restant staan
    - voorbehoud: de belangrijkste beperking van dit model
    """
    if debiet_m3_s <= 0:
        raise ValueError(
            "debiet_m3_s moet groter dan nul zijn; bij wegvallende afvoer verdunt er niets "
            f"en houdt dit model op te gelden (gekregen: {debiet_m3_s})"
        )
    if eenheid not in EENHEIDSFACTOR:
        raise ValueError(
            f"onbekende eenheid {eenheid!r}; stil aannemen dat het mg/l is zou de bijdrage een "
            f"factor 1000 verkeerd kunnen zetten"
        )
    factor = EENHEIDSFACTOR[eenheid]

    liters_per_jaar = debiet_m3_s * SECONDEN_PER_JAAR * 1000.0
    posten = []
    for i, post in enumerate(register):
        wl = waterlichaam_per_post.get(sleutel_post(post, i))
        if not wl or not is_bovenstrooms(wl, waterlichaam_meetpunt):
            continue
        # Koppelen op Aquo-code als het informatiemodel die geleverd heeft, anders op de
        # Nederlandse omschrijving. Dat tweede is de oude weg en werkt alleen zolang twee bronnen
        # een stof letterlijk hetzelfde schrijven; de code kan niet stilvallen op een andere
        # schrijfwijze. Zie `lozingsmodel.vrachten_op_code`.
        vracht_kg = None
        if parameter_code:
            post_aquo = (post.get("vrachten_aquo") or {}).get(parameter_code)
            if post_aquo is not None:
                vracht_kg = post_aquo.get("kg_jaar") if isinstance(post_aquo, dict) else post_aquo
        if vracht_kg is None:
            vracht_kg = (post.get("vrachten") or {}).get(parameter)
        if not vracht_kg:
            continue
        bijdrage = vracht_kg * 1e6 / liters_per_jaar * factor
        posten.append({
            "naam": post.get("naam"), "kenmerk": post.get("kenmerk"),
            "waterlichaam": wl, "vracht_kg_jaar": vracht_kg,
            "bijdrage_bovengrens": bijdrage,
        })

    posten.sort(key=lambda p: p["bijdrage_bovengrens"], reverse=True)
    som = sum(p["bijdrage_bovengrens"] for p in posten)
    return {
        "posten": posten,
        "som_bovengrens": som,
        "restant": gemeten - som,
        "restant_label": "bovenstrooms en diffuus",
        "debiet_m3_s": debiet_m3_s,
        "eenheid": eenheid,
        "voorbehoud": VOORBEHOUD,
    }
