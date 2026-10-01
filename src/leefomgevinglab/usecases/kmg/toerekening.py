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

VOORBEHOUD = (
    "Deze verdeling is een bovengrens, berekend met een sterk versimpeld model van dit lab: de "
    "vergunde vracht gedeeld over de jaarafvoer van het waterlichaam, zonder verblijftijd, "
    "menging of afbraak. Een vergunning wordt zelden volledig benut, dus de werkelijke bijdrage "
    "ligt lager. Welk aandeel aan wie toekomt stelt het toezicht vast, niet deze pagina."
)


def is_bovenstrooms(waterlichaam: str, meetpunt_waterlichaam: str) -> bool:
    """Ligt `waterlichaam` bovenstrooms van het meetpunt, of is het hetzelfde?

    Een onbekend waterlichaam telt niet mee: dan weten we de richting niet, en meetellen zou
    een bijdrage suggereren die we niet kunnen onderbouwen.
    """
    a, b = _INDEX.get(waterlichaam), _INDEX.get(meetpunt_waterlichaam)
    if a is None or b is None:
        return False
    return a <= b


def bijdragen(gemeten_mg_l: float, parameter: str, register: list[dict],
              waterlichaam_meetpunt: str, waterlichaam_per_post: dict[str, str],
              debiet_m3_s: float) -> dict:
    """Per vergunning de bovengrens van de bijdrage aan de gemeten concentratie, plus wat overblijft.

    Sleutels in de uitkomst:
    - posten[].bijdrage_bovengrens_mg_l: bovengrens van de concentratiebijdrage (mg/l)
    - som_bovengrens_mg_l: som van alle bijdragen (mg/l)
    - restant_mg_l: wat overblijft (bovenstrooms en diffuus)
    - voorbehoud: de belangrijkste beperking van dit model
    """
    if debiet_m3_s <= 0:
        raise ValueError(
            "debiet_m3_s moet groter dan nul zijn; bij wegvallende afvoer verdunt er niets "
            f"en houdt dit model op te gelden (gekregen: {debiet_m3_s})"
        )

    liters_per_jaar = debiet_m3_s * SECONDEN_PER_JAAR * 1000.0
    posten = []
    for post in register:
        wl = waterlichaam_per_post.get(post.get("kenmerk") or "")
        if not wl or not is_bovenstrooms(wl, waterlichaam_meetpunt):
            continue
        vracht_kg = (post.get("vrachten") or {}).get(parameter)
        if not vracht_kg:
            continue
        bijdrage = vracht_kg * 1e6 / liters_per_jaar
        posten.append({
            "naam": post.get("naam"), "kenmerk": post.get("kenmerk"),
            "waterlichaam": wl, "vracht_kg_jaar": vracht_kg,
            "bijdrage_bovengrens_mg_l": bijdrage,
        })

    posten.sort(key=lambda p: p["bijdrage_bovengrens_mg_l"], reverse=True)
    som = sum(p["bijdrage_bovengrens_mg_l"] for p in posten)
    return {
        "posten": posten,
        "som_bovengrens_mg_l": som,
        "restant_mg_l": gemeten_mg_l - som,
        "restant_label": "bovenstrooms en diffuus",
        "debiet_m3_s": debiet_m3_s,
        "voorbehoud": VOORBEHOUD,
    }
