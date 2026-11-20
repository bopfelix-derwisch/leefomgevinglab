"""De vindplaats van een bevinding: het citaat, de pagina, en de controle dat die twee kloppen.

**Dit is de kern van de kennisbasis en niet een hulpmodule.** Een overzicht van bevindingen uit
rapporten is precies het soort pagina dat ongemerkt verschuift: een samenvatting van een
samenvatting, met een paginanummer dat niemand natrekt. Daarom draagt elke bevinding in
`bevindingen.py` een *letterlijke* zinsnede uit het document plus de pagina waarop die staat, en
controleert `controleer_alles()` dat de zinsnede daar werkelijk staat. Staat zij er niet, dan
valt de test om -- niet de pagina.

**Drie dingen in de tekstextractie maken een naïeve `in`-vergelijking onbetrouwbaar**, alle drie
bij het bouwen tegengekomen:

1. **Ligaturen.** De pdf's dragen `ﬁ`, `ﬀ` en `ﬂ` als één teken, dus "effecten" uit het rapport
   komt als "eﬀecten" uit `pdftotext`. Een getypt citaat matcht dan niets.
2. **Regelafbreking.** `-layout` behoudt de kolombreedte, dus een citaat van meer dan een regel
   bevat een harde regelovergang en vaak dubbele spaties uit de uitlijning.
3. **Afbreekstreepjes.** De kabinetsreactie is in kolommen gezet en breekt woorden af
   ("aanbe-\nveling"). Dat is níet weg te normaliseren zonder echte woorden te beschadigen, dus
   citaten die over zo'n afbreking lopen zijn hier gewoon verboden -- `controleer()` meldt ze als
   niet gevonden, en dan kies je een ander citaat.

`normaliseer()` lost de eerste twee op. De derde blijft een keuze van wie het citaat kiest, en
dat is juist goed: de controle mag niet zo tolerant worden dat zij alles goedkeurt.
"""
import re

from leefomgevinglab.kennisbasis import bronnen as bronnen_mod

#: De ligaturen die `pdftotext` uit deze vier pdf's levert, terug naar losse letters.
LIGATUREN = {"ﬁ": "fi", "ﬀ": "ff", "ﬂ": "fl", "ﬃ": "ffi", "ﬄ": "ffl", "ﬅ": "ft", "ﬆ": "st"}

#: Tekens die in de extractie als quote kunnen opduiken, allemaal naar de rechte variant.
AANHALINGEN = {"‘": "'", "’": "'", "“": '"', "”": '"', "‹": "'",
               "›": "'", "«": '"', "»": '"'}


def normaliseer(tekst: str) -> str:
    """Witruimte, ligaturen, zachte afbreekstreepjes en aanhalingstekens gelijkgetrokken.

    Zonder deze stap matcht geen enkel citaat van meer dan een halve regel, want `-layout`
    behoudt de uitlijning van de kolom."""
    s = tekst.replace("­", "")
    for bron, doel in {**LIGATUREN, **AANHALINGEN}.items():
        s = s.replace(bron, doel)
    s = s.replace("–", "-").replace("—", "-").replace("‑", "-")
    return re.sub(r"\s+", " ", s).strip()


def paginas(bron_id: str) -> list[str]:
    """De pagina's van een document als lijst, zodat index 0 pagina 1 is.

    Werpt `FileNotFoundError` als het document niet binnengehaald is -- stil een lege lijst
    teruggeven zou elke citaatcontrole laten slagen omdat er niets te controleren viel."""
    bron = bronnen_mod.OP_ID[bron_id]
    pad = bronnen_mod.pad(bron, "tekst")
    if not pad.exists():
        raise FileNotFoundError(
            f"{bron_id}: tekstextractie ontbreekt ({pad}). Haal de bron binnen met "
            f"scripts/23_bouw_kennisbasis.py")
    return pad.read_text().split("\f")


def zoek(bron_id: str, citaat: str) -> list[int]:
    """Alle pagina's (1-gebaseerd) waarop het citaat voorkomt. Leeg betekent: niet gevonden."""
    doel = normaliseer(citaat).lower()
    return [i for i, p in enumerate(paginas(bron_id), start=1)
            if doel in normaliseer(p).lower()]


def controleer(bron_id: str, citaat: str, pagina: int) -> dict:
    """Staat dit citaat op deze pagina van dit document?

    Levert altijd een uitslag terug in plaats van een uitzondering te werpen, zodat één fout
    citaat de hele controle niet afbreekt en je in één run ziet wat er allemaal mis is. Vindt hij
    het citaat op een *andere* pagina, dan staat die erbij -- dat is bijna altijd de oorzaak en
    scheelt het zelf zoeken."""
    treffers = zoek(bron_id, citaat)
    return {
        "bron": bron_id,
        "pagina": pagina,
        "klopt": pagina in treffers,
        "gevonden_op": treffers,
        "citaat": citaat,
    }


def controleer_alles(items) -> list[dict]:
    """De uitslagen van alle citaten die niet kloppen. Leeg is goed.

    `items` zijn dicts met minstens `bron`, `citaat` en `pagina` -- de bevindingen dus, maar de
    functie weet dat niet en is daarmee ook op een losse lijst te gebruiken."""
    fout = []
    for it in items:
        uitslag = controleer(it["bron"], it["citaat"], it["pagina"])
        if not uitslag["klopt"]:
            fout.append({**uitslag, "id": it.get("id")})
    return fout


def deeplink(bron_id: str, pagina: int) -> str:
    """De publieke vindplaats met het paginafragment erachter.

    Het fragment `#page=N` is geen eigenschap van de bron maar van de pdf-lezer van de bezoeker;
    werkt die niet mee, dan opent het document op pagina 1 en staat het nummer nog steeds op de
    pagina van dit lab. Daarom staat de pagina óók als tekst naast de link."""
    return f"{bronnen_mod.OP_ID[bron_id]['url']}#page={pagina}"
