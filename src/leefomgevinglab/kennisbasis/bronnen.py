"""De brondocumenten van de kennisbasis: vier openbare rapporten over VTH en de Omgevingswet.

**Wat hier wél en niet staat.** Dit bestand draagt alleen de *kaart* van een document: titel,
uitgever, datum, kenmerk, de publieke vindplaats, en waar de binnengehaalde kopie op NVMe staat.
De inhoud staat niet in de repo en komt daar ook niet in -- zie `CLAUDE.md`: brondata leeft op
`/mnt/nvme/geluidsmeter/data/`. Een repo die vier rapporten van samen 14 MB meedraagt is geen
kennisbasis, dat is een archiefkast.

**Waarom een paginaveld afgeleid wordt en niet getypt.** `paginas()` leest het aantal pagina's uit
het geëxtraheerde tekstbestand (`pdftotext` zet een `\f` tussen pagina's). Zou dat getal hier als
constante staan, dan kan het uit de pas lopen met het bestand waarnaar het verwijst -- en juist op
dat getal rust de deeplink naar de bron (`#page=N`). Hetzelfde geldt voor `beschikbaar`: of een
document binnengehaald is, is een vraag aan de schijf, geen bewering in code.

**De openbaarheid is geen aanname.** Alle vier de documenten zijn door een overheidsorgaan
gepubliceerd op een eigen, publiek bereikbare vindplaats; die URL's zijn nagelopen (alle vier
HTTP 200, 2026-11-20). Dat is de grond waarop dit lab ze mag binnenhalen en indexeren. Een
document zonder zo'n vindplaats hoort hier niet.
"""
from pathlib import Path

#: Waar de binnengehaalde documenten en hun tekstextractie staan. Buiten de repo, met opzet.
BASIS = Path("/mnt/nvme/geluidsmeter/data/external/kennisbasis")

#: De vier bronnen van het dossier *bevindingen VTH*, in de volgorde waarin ze elkaar beantwoorden:
#: twee toezichtrapporten van oktober 2026, het reflectierapport dat zij bevestigen, en de
#: kabinetsreactie daarop.
BRONNEN = [
    {
        "id": "rli",
        "korte_naam": "Rli-advies",
        "titel": "Toezicht met vertrouwen",
        "ondertitel": "Toezicht en handhaving onder de Omgevingswet",
        "uitgever": "Raad voor de leefomgeving en infrastructuur",
        "soort": "advies",
        "datum": "2026-10-13",
        "kenmerk": "RLI-2026/2753",
        "url": "https://www.rli.nl/publicaties/2026/advies/toezicht-met-vertrouwen",
        "bestand": "bronnen/rli_toezicht_met_vertrouwen.pdf",
        "tekst": "rli_toezicht.txt",
        "gericht_aan": "minister van VRO en staatssecretaris van IenW",
        "waarom": "Vraagt niet of de uitvoering haar werk doet, maar of het stelsel haar dat "
                  "toestaat. Het enige van de vier dat de vijf oorzaken benoemt.",
    },
    {
        "id": "ilt",
        "korte_naam": "ILT-onderzoek",
        "titel": "De basis moet op orde",
        "ondertitel": "Milieurisico's door onvoldoende grip op actualisatie vergunningen",
        "uitgever": "Inspectie Leefomgeving en Transport",
        "soort": "onderzoek",
        "datum": "2026-10-09",
        "kenmerk": "8e VTH-onderzoek",
        "url": "https://www.ilent.nl/documenten/over-de-ilt/onderzoeken-naar-het-vth-stelsel/"
               "rapporten/onderzoek-naar-actualiteit-van-milieuvergunningen-bij-omgevingsdiensten",
        "bestand": "bronnen/ilt_actualisatie_vergunningen.pdf",
        "tekst": "vth_actualisatie.txt",
        "gericht_aan": "gemeenten en provincies, omgevingsdiensten en Omgevingsdienst NL, "
                       "ministerie van IenW",
        "waarom": "Het meest concrete van de vier: alle 26 omgevingsdiensten gesproken, en de "
                  "bevinding gaat precies over het gegeven waarop dit lab elders rekent.",
    },
    {
        "id": "ec",
        "korte_naam": "Reflectierapport",
        "titel": "Werk aan de winkel",
        "ondertitel": "Reflectierapport Omgevingswet 2025",
        "uitgever": "Evaluatiecommissie Omgevingswet",
        "soort": "reflectierapport",
        "datum": "2026-01-01",
        "kenmerk": "tweede reflectierapport",
        "url": "https://www.rijksoverheid.nl/documenten/rapporten/2026/01/01/"
               "tweede-reflectierapport-van-de-evaluatiecommissie-omgevingswet-werk-aan-de-winkel",
        "bestand": "bronnen/werk_aan_de_winkel.pdf",
        "tekst": "werk_aan_de_winkel.txt",
        "gericht_aan": "minister van VRO, overheden, koepels",
        "waarom": "Kijkt naar het hele stelsel in plaats van naar het toezicht alleen, en is de "
                  "bron die de andere twee als bevestiging aanhalen.",
    },
    {
        "id": "kabinet",
        "korte_naam": "Kabinetsreactie",
        "titel": "Kabinetsreactie op het tweede reflectierapport",
        "ondertitel": "Kamerstuk 33 118, nr. 320",
        "uitgever": "minister van Volkshuisvesting en Ruimtelijke Ordening",
        "soort": "kamerstuk",
        "datum": "2026-06-29",
        "kenmerk": "33 118, nr. 320 (vergaderjaar 2025-2026)",
        "url": "https://zoek.officielebekendmakingen.nl/kst-33118-320.html",
        "bestand": "bronnen/kabinetsreactie_33118_320.pdf",
        "tekst": "kabinetsreactie.txt",
        "gericht_aan": "Tweede Kamer",
        "waarom": "Zonder dit stuk is het dossier eenzijdig: hier staat wat er met de "
                  "aanbevelingen gebeurt, en welke oorzaak het kabinet juist niet wegneemt.",
    },
]

OP_ID = {b["id"]: b for b in BRONNEN}


def pad(bron: dict, veld: str = "bestand") -> Path:
    """Het absolute pad van een bronbestand. `veld` is `bestand` (de pdf) of `tekst`."""
    return BASIS / bron[veld]


def paginas(bron: dict) -> int | None:
    """Het aantal pagina's volgens de tekstextractie, of `None` als die er niet is.

    `pdftotext` scheidt pagina's met een form feed. Het aantal pagina's is dus het aantal
    scheidingstekens plus één -- maar alleen als er iets staat; een leeg bestand heeft nul
    pagina's, niet één."""
    p = pad(bron, "tekst")
    if not p.exists():
        return None
    inhoud = p.read_text()
    if not inhoud.strip():
        return 0
    return inhoud.count("\f") + 1


def beschikbaar(bron: dict) -> dict:
    """Of de pdf en de tekstextractie op schijf staan, met hun omvang. Een vraag aan de schijf,
    geen bewering in code -- de pagina moet kunnen zeggen 'niet binnengehaald' in plaats van een
    deeplink aan te bieden die niets opent."""
    pdf, txt = pad(bron, "bestand"), pad(bron, "tekst")
    return {
        "pdf": pdf.exists(),
        "pdf_bytes": pdf.stat().st_size if pdf.exists() else None,
        "tekst": txt.exists(),
        "paginas": paginas(bron),
    }


def overzicht() -> list[dict]:
    """De vier bronnen met hun beschikbaarheid erbij -- wat de pagina nodig heeft."""
    return [{**b, "op_schijf": beschikbaar(b)} for b in BRONNEN]
