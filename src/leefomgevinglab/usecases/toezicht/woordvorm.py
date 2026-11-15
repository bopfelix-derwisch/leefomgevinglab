"""Eén plek voor een hoofdletter aan het begin van een Nederlandse naam -- nodig op twee plekken
in dit package die allebei een naam uit de bron (vaak kleine letters, zie `aquo.py`) als eerste
woord van een zin of citaat moeten tonen: `dossier._bewering()` (de ratio-tak van
`meerdere_grenswaarden`, "{stof} draagt bij deze vestiging...") en `uitleg._aquo_treffers()`
("'{naam}' is in de Aquo-domeintabel Parameter...").

**De ij-digraaf.** In het Nederlands is `ij` een digraaf: bij een hoofdletter worden het er twee
("IJsselmeer", niet "Ijsselmeer"; "IJzer", niet "Ijzer"). Zowel `str.capitalize()` als het
eenvoudige `woord[0].upper() + woord[1:]` weten dat niet -- beide maakten uit de kleine-letter
bronnaam "ijzer" de fout "Ijzer". Gevonden bij een publieke controle op `/wasstraat` (Tata Steel:
"Ijzer draagt bij deze vestiging meer dan één grenswaarde..."), en bij nazoeken bleek
`uitleg._aquo_treffers()` dezelfde fout te maken via `naam.capitalize()` -- een andere bewerking,
zelfde onderliggende aanname.

**Geen `.capitalize()`.** Die kapitaliseert niet alleen de eerste letter, maar verlaagt ook de
rest van het woord -- voor een naam met een interne hoofdletter (een samengestelde naam, een
afkorting) zou dat een tweede verminking zijn. `hoofdletter_bij_zinsbegin()` raakt uitsluitend het
begin van het woord aan en laat de rest exact zoals de bron hem gaf.

Nazoeking bij deze fix-ronde (geen andere plek in `usecases/toezicht/` kapitaliseert een naam uit
de bron op deze manier): alleen de twee plekken hierboven lezen een bronnaam en zetten er zelf een
hoofdletter voor; de overige teksten in `dossier.py`/`signalen.py`/`uitleg.py` tonen een naam
altijd ongewijzigd (midden in een zin, zoals `{stof}` in `geen_onafhankelijke_meting`'s
bewering) of gebruiken een eigen, vast woord (geen brondata)."""

# Nederlandse digrafen die als één letter kapitaliseren. Vandaag alleen `ij` -- de enige die dit
# lab in de praktijk is tegengekomen (ijzer); een tweede zou hier gewoon bij komen, niet als
# aparte functie ernaast.
_DIGRAFEN = ("ij",)


def hoofdletter_bij_zinsbegin(woord: str) -> str:
    """`woord` met een hoofdletter aan het begin -- "ijzer" -> "IJzer", "zink" -> "Zink", een
    al-hoofdletterige naam ("Zink") blijft ongewijzigd. Nooit de rest van het woord verlagen
    (in tegenstelling tot `str.capitalize()`), en nooit meer dan de digraaf zelf aanraken als het
    woord ermee begint."""
    if not woord:
        return woord
    for digraaf in _DIGRAFEN:
        n = len(digraaf)
        if woord[:n].lower() == digraaf:
            return digraaf.upper() + woord[n:]
    return woord[0].upper() + woord[1:]
