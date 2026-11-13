"""Het signaaldossier -- de drie delen die een toezichthouder op één vestiging meeneemt.

Deel A (`kaart`) is de identiteit van de vestiging: naam, plaats, locatie, locatiecode, het
KvK-vestigingsnummer, het vergunningkenmerk, de besluitdatum, het waterlichaam waarop geloosd
wordt en de link naar het vergunningdocument. Elk veld draagt zijn eigen zekerheid
(`kmg.lozingsmodel.ZEKERHEDEN`) en een ontbrekend veld blijft in de kaart staan, met
`waarde: None` -- voor toezicht ís een ontbrekende vergunningreferentie het signaal, dus wie hem
weglaat verbergt precies waar het om gaat (plan, §2 deel A). Deze module doet zelf geen netwerk en
geen opzoeking: elk kaartveld is een directe lezing van `vestiging`, ook `waterlichaam` -- die
opzoeking (`kmg.service._waterlichaam_per_vergunning`) is de taak van wie `vestiging` samenstelt,
niet van deze module.

Deel B (`signalen`) is de output van `signalen.signalen(...)`, al gerangschikt op zwaarte en dan
omvang, verrijkt met twee velden per signaal die het plan vraagt en die hier worden toegevoegd
omdat `signalen.py` zelf geen van beide kan afleiden:

- `grondslag` -- hoe het bewijs aan deze vestiging gekoppeld is, in het vocabulaire van
  `maaskaart.GRONDSLAG` (`code` / `ruimtelijk` / `heuristiek` / `geen`), hergebruikt in plaats van
  een tweede vocabulaire te verzinnen.
- `zekerheid` -- hoe zeker het bewijs is, in `lozingsmodel.ZEKERHEDEN`.

**Hoe dat per signaal is bepaald (de open vraag uit de opdracht).** `grondslag` en `zekerheid`
zijn in `lozingsmodel` begrippen per *veld* van een gedataficeerd voorschrift, niet per *signaal*.
De letterlijke lezing -- "de zwakste zekerheid onder de voorschriften in het bewijs" -- zou
vereisen dat elk bewijsvoorschrift eerst door `lozingsmodel.dataficeer()` gaat, en dat vraagt een
parameterreferentie die nergens in de interface van deze taak staat (`dossier()` krijgt alleen
`vestiging` en `context`, geen referentie). Bovendien dataficeert geen van de bewijsvormen die
`signalen.py` vandaag produceert gelijk: sommige regels leveren ruwe voorschriften, andere
overschrijdingsrijen uit `context`, weer andere een lijst ontbrekende velden. Er is dus geen
uniform "zekerheid per bewijsrij" om het zwakste van te nemen zonder zelf iets te verzinnen.

Daarom is de vraag hier vertaald naar wat wél uit de regel zelf volgt: **hoe is het bewijs aan
deze vestiging gekoppeld, en is er sowieso bewijs?** Twee statische tabellen
(`_HERKOMST_PER_REGEL`, zie onder) leggen dat per regel vast, met per regel een eigen
verantwoording in de tabel zelf -- dezelfde vorm als `signalen.DREMPELS`. Zonder bewijs
(`geen_geldigheidsduur` levert bewust een lege lijst, zie `signalen.py`) is de zekerheid altijd
`ontbreekt`, ongeacht wat de tabel voor die regel zegt: geen bewijs is zelf de zwakste uitkomst,
en dat geldt voor elke toekomstige regel die ooit met een lege lijst komt, niet alleen de twee van
vandaag.

Deel C (`rapport.schrijf`) staat in een eigen module, `rapport.py`.

**`telling`** draagt alleen afgeleide getallen (aantal voorschriften, aantal signalen, verdeling
naar zwaarte en naar regel) -- nooit een getypt cijfer, conform de huisregel.

**`voorbehouden`** is een lijst Nederlandse zinnen die zegt wat dit dossier **niet** kon toetsen:
welke contextsleutel ontbrak (`gemeten_codes`, `waterlichaam`, `register_codes`,
`stoffen_met_norm`) en welke agent is uitgezet (`uit`). De taalregel geldt ook hier: geen van deze
zinnen noemt een "overtreding".

**`uit` en `runlog` (sinds taak 6b bekabeld).** `dossier()` accepteert `uit: set[str] | None` en
`runlog` (een `toezicht.runlog.Runlog`, optioneel). De runner (taak 6/6b, `runner.
tool_dossier_samenstellen`) roept `dossier()` aan met de agents die uitstaan én met de runlog die
tot dan toe is opgebouwd; `dossier()` zet die om in deel D (`d["runlog"]`, met `uitgezet` en
`stappen`) en in het `stap`-veld per signaal (zie `_signalen_stap`). Zonder een echte run blijft
`runlog["stappen"]` leeg, maar het dict zelf is nooit `None` -- zie `dossier()` zelf. Wat al vanaf
taak 4/5 werkt: een uitgezette agent komt óók in `voorbehouden[0]` te staan, zodat hij niet
stilzwijgend minder dossier oplevert (plan, R2 in de ledger).

**Wat deze module niet bouwt.** `context["stoffen_met_norm"]` (de Aquo-codes met een KRW-norm,
nodig voor de zwaarte van signaal 1) wordt hier niet gevuld -- dat vraagt een live opzoeking in de
KRW-toetsresultaten en `dossier()` doet geen netwerk. Ontbreekt die sleutel, dan meldt
`_voorbehouden()` dat expliciet; wie `context` samenstelt (een latere taak) moet hem vullen.
"""
from collections import Counter

from leefomgevinglab.usecases.kmg.lozingsmodel import ZEKERHEDEN
from leefomgevinglab.usecases.maaskaart import GRONDSLAG
from leefomgevinglab.usecases.toezicht import signalen as signalen_mod

# Geen van de tien regels levert vandaag een `aangenomen`-zekerheid op (zie `_HERKOMST_PER_REGEL`
# hieronder), vandaar de `_` -- de volgorde komt wel uit `ZEKERHEDEN` zelf, niet opnieuw getypt.
UIT_DE_BRON, AFGELEID, _, ONTBREEKT = ZEKERHEDEN

# Deel A: kaartveld -> veld op `vestiging`. Alleen waar de naam verschilt (het KvK-vestigingsnummer
# heet in de Atlas-post `vestigingsnummer_kvk`, zie `connectors/smwk_atlas.py`) staat de bronnaam
# apart; de rest leest 1-op-1.
_KAART_VELDEN = (
    ("naam", "naam"),
    ("plaats", "plaats"),
    ("locatie", "locatie"),
    ("locatiecode", "locatiecode"),
    ("vestigingsnummer_kvk", "vestigingsnummer_kvk"),
    ("kenmerk", "kenmerk"),
    ("besluitdatum", "besluitdatum"),
    ("waterlichaam", "waterlichaam"),
    ("url", "url"),
)


def _kaartveld(waarde) -> dict:
    """Eén veld van deel A: aanwezig telt als `uit de bron` (deze module leidt niets af, zij
    leest alleen), afwezig als `ontbreekt`. Precies twee sleutels, niet meer -- de vorm die de
    opdracht letterlijk toetst (`{"waarde": None, "zekerheid": "ontbreekt"}`)."""
    aanwezig = waarde not in (None, "", [])
    return {"waarde": waarde, "zekerheid": UIT_DE_BRON if aanwezig else ONTBREEKT}


def _kaart(vestiging: dict) -> dict:
    return {kaart_sleutel: _kaartveld(vestiging.get(bron_sleutel))
            for kaart_sleutel, bron_sleutel in _KAART_VELDEN}


# Per regel: (grondslag, zekerheid-als-er-bewijs-is). Zie de moduledocstring voor de redenering
# in het algemeen; hier de verantwoording per regel.
#
# Fix-ronde 1, bevinding 2: `grondslag == "geen"` dekt hieronder twee verschillende situaties,
# en dat is met opzet, niet per ongeluk -- `maaskaart.GRONDSLAG` heeft geen vijfde waarde om ze
# uit elkaar te houden, en die vocabulaire is gedeeld met `/maaskaart` en hier niet uit te
# breiden. De twee situaties:
#   (a) **een koppeling is geprobeerd en mislukt** -- `niet_in_referentie` (de naam koppelde niet
#       aan een Aquo-code) en `vergunning_niet_te_vinden` (het identificerende veld is er niet om
#       mee te koppelen aan het vergunningdocument). Hier is "geen" het resultaat van een poging.
#   (b) **er is nooit een koppeling geprobeerd, en dat is ook niet nodig** -- `meerdere_
#       grenswaarden`, `vracht_onbepaald` en `niet_regime_zuiver` vergelijken alleen voorschriften
#       binnen dezelfde vestiging; `geen_geldigheidsduur` constateert een afwezig veld dat voor
#       het hele register geldt. Hier is "geen" de afwezigheid van een poging, niet het resultaat
#       van een mislukte.
# Beide lezen in deze tabel identiek (`"geen"`), met dezelfde tekst uit `maaskaart.GRONDSLAG` --
# dat is feitelijk niet onjuist (in beide gevallen is er geen koppeling gelegd), maar wie één
# woord voor twee begrippen gebruikt, graaft hier een volgende verwarring op dezelfde plek als
# `"ontbrekend"` vs. `"ontbreekt"` eerder in dit dossier. Vastgelegd hier in woorden in plaats van
# in een nieuwe grondslagwaarde, omdat die uitbreiding buiten de scope van deze taak valt.
_HERKOMST_PER_REGEL = {
    # Eigen voorschrift, aquo-code vergeleken met een vreemde set (de WKP-meetset) -- gekoppeld
    # via een gedeelde code.
    "geen_onafhankelijke_meting": ("code", UIT_DE_BRON),
    # Eigen voorschrift; `aquo_status` komt uit een geslaagde codekoppeling in `aquo.verrijk`
    # (de ingetrokken code zelf is gevonden, alleen niet meer geldig).
    "vervallen_code": ("code", UIT_DE_BRON),
    # (a) koppeling geprobeerd, mislukt: de codekoppeling vond geen Aquo-code (`aquo: None`).
    "niet_in_referentie": ("geen", UIT_DE_BRON),
    # (b) geen koppeling geprobeerd: twee voorschriften van dezelfde vestiging onderling
    # vergeleken, geen koppeling met iets buiten de vestiging nodig of gemaakt.
    "meerdere_grenswaarden": ("geen", UIT_DE_BRON),
    "vracht_onbepaald": ("geen", UIT_DE_BRON),
    # Koppelt via de positie van het waterlichaam in de stroomvolgorde -- een ruimtelijke/
    # hydrologische relatie, geen gedeelde code en geen naamgok.
    "norm_overschreden_bovenstrooms": ("ruimtelijk", AFGELEID),
    # Koppelt de stof-code van een overschrijding aan `register_codes` -- een gedeelde code,
    # maar via het hele register, niet via deze ene vestiging: afgeleid, niet uit de bron van
    # déze vestiging zelf.
    "stof_buiten_register": ("code", AFGELEID),
    # (a) koppeling geprobeerd, mislukt: het bewijs ís de afwezigheid van `url`/`kenmerk`/
    # `besluitdatum` -- er is niets om de vergunning mee terug te vinden, en de zekerheid is
    # daarom zelf `ontbreekt`.
    "vergunning_niet_te_vinden": ("geen", ONTBREEKT),
    # (b) geen koppeling geprobeerd: eigen voorschrift, een voorbehoud over vergelijkbaarheid.
    "niet_regime_zuiver": ("geen", UIT_DE_BRON),
    # (b) geen koppeling geprobeerd: geldt per definitie voor het hele dossier; bewijs is bewust
    # leeg (zie `signalen.py`), dus de generieke lege-bewijs-regel hieronder bepaalt de
    # zekerheid toch al op `ontbreekt`.
    "geen_geldigheidsduur": ("geen", ONTBREEKT),
}
# Volledigheid van deze tabel (elke regel in `signalen.DREMPELS` heeft een herkomst, en elke
# grondslag komt uit `maaskaart.GRONDSLAG`) is een test in `tests/test_toezicht_dossier.py`,
# geen assert hier -- dit bestand volgt daarin de rest van `usecases/toezicht`, waar een
# invariant altijd als test staat, nooit als module-assert.

# De vraag die een inspecteur ter plaatse kan stellen (plan, §2 deel B). Vast per regel: dit is
# geen generatie (geen LLM, geen risico op een vaststellende formulering) maar een vaste
# catalogus, in dezelfde geest als `signalen.DREMPELS`.
_WAT_TE_DOEN_PER_REGEL = {
    "geen_onafhankelijke_meting":
        "Vraag de actuele zelfrapportage van deze stof op en vergelijk die met een eigen "
        "steekproef ter plaatse.",
    "vervallen_code":
        "Vraag welke code de vergunning nu voor deze stof zou moeten noemen en of de "
        "grenswaarde sindsdien is herzien.",
    "niet_in_referentie":
        "Vraag de vergunninghouder welke stof hiermee precies bedoeld wordt.",
    "meerdere_grenswaarden":
        "Vraag welk voorschrift hier leidend is en onder welk bemonsteringsregime.",
    "vracht_onbepaald":
        "Vraag het actuele lozingsdebiet op, of een recente debietmeting, om deze grenswaarde "
        "naar een vracht te kunnen omrekenen.",
    "norm_overschreden_bovenstrooms":
        "Vraag de eigen lozingscijfers van de laatste periode op voor deze stof.",
    "stof_buiten_register":
        "Ga na of deze stof ergens anders in de keten vergund had moeten worden.",
    "vergunning_niet_te_vinden":
        "Vraag het vergunningdocument zelf op bij het bevoegd gezag.",
    "niet_regime_zuiver":
        "Vraag welk bemonsteringsregime bij deze vergelijking is gebruikt.",
    "geen_geldigheidsduur":
        "Vraag of deze vergunning nog van kracht is.",
}


def _zekerheid(regel_id: str, bewijs: list[dict]) -> str:
    """Geen bewijs is zelf de zwakste uitkomst -- ook voor een regel wiens tabelwaarde iets
    anders zou zeggen, mocht die ooit per ongeluk zonder bewijs vuren."""
    if not bewijs:
        return ONTBREEKT
    return _HERKOMST_PER_REGEL[regel_id][1]


# Taak 6b (R14): de agent in `runner.py` wiens stap de signalen oplevert. Eigen klein koppelpunt
# met de runnerconfiguratie (alleen deze naam, geen import van `runner.py` zelf -- die module
# importeert op haar beurt `dossier.py`, en een importcirkel is hier geen prijs waard voor één
# string) zodat elk signaal kan terugwijzen naar de stap die het opleverde, zonder de inhoud van
# die stap hier te dupliceren.
_SIGNAALSTELLER_AGENT = "signaalsteller"


def _signalen_stap(runlog) -> dict | None:
    """De runlog-stap die de signalen heeft bepaald, voor het `stap`-veld van elk signaal (R14).
    `None` zonder meegegeven runlog, of als die (nog) geen signaalsteller-stap bevat -- bv. een
    losse `Runlog()` in een test, of `dossier()` zonder de runner aangeroepen. Geen stap is dan
    zelf de juiste uitkomst: er is immers geen proces om naar terug te wijzen."""
    if runlog is None:
        return None
    for s in runlog.als_gegeven():
        if s.get("agent") == _SIGNAALSTELLER_AGENT:
            return {"agent": s["agent"], "tool": s.get("tool"), "nr": s["nr"]}
    return None


def _signaal_deel_b(ruw: dict, stap: dict | None) -> dict:
    regel_id = ruw["regel"]
    grondslag, _ = _HERKOMST_PER_REGEL[regel_id]
    uit = {
        "regel": regel_id,
        "signaal": ruw["signaal"],
        "zwaarte": ruw["zwaarte"],
        "omvang": ruw["omvang"],
        "bewijs": ruw["bewijs"],
        "grondslag": grondslag,
        "zekerheid": _zekerheid(regel_id, ruw["bewijs"]),
        "wat_te_doen": _WAT_TE_DOEN_PER_REGEL[regel_id],
    }
    if stap is not None:
        uit["stap"] = stap
    return uit


def _telling(vestiging: dict, signalen_lijst: list[dict]) -> dict:
    """Uitsluitend afgeleide getallen -- niets hier is getypt."""
    per_zwaarte = Counter(s["zwaarte"] for s in signalen_lijst)
    per_regel = Counter(s["regel"] for s in signalen_lijst)
    return {
        "aantal_voorschriften": len(vestiging.get("voorschriften") or []),
        "aantal_signalen": len(signalen_lijst),
        "aantal_regels_die_vuurden": len(per_regel),
        "per_zwaarte": {z: per_zwaarte.get(z, 0) for z in ("hoog", "midden", "laag")},
        "per_regel": dict(per_regel),
    }


def _voorbehouden(context: dict, uit: set[str] | None) -> list[str]:
    """Wat dit dossier niet kon toetsen, in woorden -- nooit een vaststelling (zelfde taalregel
    als de signalen zelf). De uitgezette-agent-zin staat altijd vooraan: dat is waar een latere
    taak (de runner) op test."""
    voorbehouden = []
    if uit:
        namen = sorted(uit)
        werkwoord = "stond" if len(namen) == 1 else "stonden"
        voorbehouden.append(
            f"{', '.join(namen)} {werkwoord} uit bij het samenstellen van dit dossier -- wat "
            "daarvan afhankelijk is, ontbreekt dus in plaats van stil te verdwijnen.")
    if context.get("gemeten_codes") is None:
        voorbehouden.append(
            "Geen meetset aangeleverd (context['gemeten_codes'] ontbreekt): het signaal 'geen "
            "onafhankelijke meting' is voor deze vestiging niet getoetst.")
    if not context.get("waterlichaam"):
        voorbehouden.append(
            "Geen waterlichaam van deze vestiging opgegeven: het signaal 'meting boven de norm, "
            "lozer bovenstrooms' is niet getoetst.")
    if context.get("register_codes") is None:
        voorbehouden.append(
            "Geen registercodes aangeleverd (context['register_codes'] ontbreekt): het signaal "
            "'gemeten stof die in geen vergunning staat' is niet getoetst.")
    if not context.get("stoffen_met_norm"):
        voorbehouden.append(
            "Geen Aquo-codes met een KRW-norm aangeleverd (context['stoffen_met_norm'] ontbreekt "
            "of is leeg): het signaal 'geen onafhankelijke meting' kan voor deze vestiging niet "
            "boven 'midden' uitkomen.")
    voorbehouden.append(
        "Een signaal in dit dossier stelt nooit vast dat iets niet mag; het vraagt aandacht voor "
        "nader onderzoek, meer niet.")
    return voorbehouden


def dossier(vestiging: dict, context: dict, uit: set[str] | None = None, runlog=None) -> dict:
    """Het signaaldossier voor één vestiging: `kaart` (deel A), `signalen` (deel B, gerangschikt),
    `telling` (afgeleide aantallen), `voorbehouden` en `runlog` (deel D, taak 6b).

    `runlog` is hier een optionele `toezicht.runlog.Runlog` (of een object met dezelfde
    `als_gegeven()`) -- typisch de log die de runner tijdens deze dossier-run al heeft opgebouwd
    (zie `runner.tool_dossier_samenstellen`). Zonder een echte `Runlog` (bv. `dossier()` los
    aangeroepen, zoals elders in deze testsuite) blijft `runlog["stappen"]` leeg, maar `runlog`
    is nooit meer `None`: `uitgezet` komt altijd uit `uit`, ook zonder een draaiende crew, zodat
    een uitgezette agent in het dossier zichtbaar blijft los van of er een echte run was.

    Geen netwerk, geen LLM hier zelf: alles komt binnen via `vestiging`, `context` en `runlog`,
    precies zoals `signalen.signalen` dat al afdwingt."""
    stap = _signalen_stap(runlog)
    signalen_lijst = [_signaal_deel_b(s, stap) for s in signalen_mod.signalen(vestiging, context)]
    return {
        "kaart": _kaart(vestiging),
        "signalen": signalen_lijst,
        "telling": _telling(vestiging, signalen_lijst),
        "voorbehouden": _voorbehouden(context, uit),
        "runlog": {
            "uitgezet": sorted(uit) if uit else [],
            "stappen": runlog.als_gegeven() if runlog is not None else [],
        },
    }
