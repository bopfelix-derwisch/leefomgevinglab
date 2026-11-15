"""De bewaakte vraagweg over de toezichtgraaf: NL-vraag -> SPARQL -> validatie -> uitvoering.

Hetzelfde huisstramien als `usecases/datavraag` (NL->SPARQL) en `usecases/afval/chat.py`
(NL->SQL): grounden, laten genereren, **valideren voordat er iets uitgevoerd wordt**, uitvoeren,
en het antwoord teruggeven met de rijen en de uitgevoerde query zichtbaar -- dezelfde transparantie
die `/afval` en `/datavraag` al bieden.

**De validator komt eerst, en is strenger dan zijn SQL-tegenhanger.** `afval/chat.valideer_sql`
bewaakt met een trefwoorden-denylist op platte tekst; dat werkt voor SQL omdat een los statement
daar altijd met een los werkwoord begint. SPARQL kent dat onderscheid niet op tekstniveau -- een
leesquery mag zelf `;` gebruiken (predicate-object-lijsten in een triple pattern) en SPARQL-
keywords zijn case-insensitief in de grammatica zelf, dus een denylist op woorden zou ofwel
legitieme queries blokkeren ofwel aan gekke hoofdletters voorbijkijken. Deze validator parseert
daarom de query met rdflib's eigen SPARQL-grammatica (`parseQuery`) in plaats van met een
patroon op tekst:

- **Alles dat geen Query is, faalt al bij het parsen.** `INSERT`/`DELETE`/`LOAD`/`DROP`/`CLEAR`/
  `CREATE`/`COPY`/`MOVE`/`ADD`/`WITH ... USING` horen bij de Update-grammatica, niet bij de
  Query-grammatica (`SelectQuery | ConstructQuery | DescribeQuery | AskQuery`) -- rdflib's parser
  weigert ze dus al vóór deze module er iets van hoeft te weten. Een tweede statement na een
  puntkomma faalt om dezelfde reden: dat is een Update-sequence, geen geldige Query.
- **Alleen SELECT en ASK zijn een vraag, geen gedaante van de graaf veranderen** -- CONSTRUCT en
  DESCRIBE parseren wél als Query, maar staan hier niet op de toegestane lijst.
- **Een SERVICE-clause wordt expliciet gezocht in de volledige parse-boom** (`_bevat_knooppunt`),
  ook genest in een subquery -- dat is de federatie die `graaf.py` bewust niet bouwt: een
  SERVICE-clause laat rdflib bij uitvoering een extern SPARQL-endpoint aanroepen, en dat is
  precies het netwerkpad dat deze graaf dicht moet houden.
- **Een `FROM`/`FROM NAMED`-dataclause wordt om dezelfde reden geweigerd**: hij trekt een extern
  gepubliceerde graaf de query in. Deze graaf is lokaal en afgeleid (plan), niet gefedereerd.
- **Een `LIMIT` is verplicht bij een SELECT.** Dit wijkt af van `afval/chat.valideer_sql`, die een
  ontbrekende `LIMIT` stilzwijgend toevoegt -- de verbatim test van dit brief (stap 1) eist juist
  dat een SELECT zonder `LIMIT` een `OngeldigeSparql` opwerpt, dus deze module weigert in plaats
  van aan te vullen. Bij `ASK` is `LIMIT` niet verplicht: dat levert een boolean, geen
  rijenverzameling om te begrenzen.
- **Een te grote `LIMIT` wordt geweigerd, niet teruggebracht.** Een eerdere versie herschreef hem
  met een tekst-brede `re.sub` over de hele querytekst -- en trof daarmee niet alleen de `LIMIT`-
  clausule, maar ook elke stringliteral die toevallig op hetzelfde patroon lijkt (bv. een
  triple pattern met `"limit 99999"` als object werd mee herschreven: fix-ronde 1, Important). Een
  op zichzelf valide verbetering (de AST in plaats van de tekst herschrijven) bleek niet
  mogelijk: de geparste `limitoffset`-node draagt geen enkele locatie-informatie (geen offset,
  geen regel/kolom) om terug te vinden waar in de originele tekst die clausule stond -- geverifieerd
  door de node en zijn `limit`-waarde te inspecteren (zie het taakrapport, fix-ronde 1). Zonder dat
  anker zou elke herschrijving weer op tekstpatronen moeten gokken, en dat is precies de fout die
  hier wordt rechtgezet. Een te grote `LIMIT` krijgt daarom dezelfde behandeling als een
  ontbrekende: geweigerd, met de toegestane bovengrens in de boodschap. Zo blijft de uitgevoerde
  query altijd letterlijk gelijk aan de query die de lezer te zien krijgt.

Overwogen en bewust buiten scope gelaten: een commentaarregel die een verboden keyword lijkt te
bevatten. De SPARQL-tokenizer gooit commentaar weg vóór het parsen, dus zo'n regel kan niets
activeren -- dat is geen aanval, alleen ruis (een test legt dat vast).
"""
import re

from rdflib.plugins.sparql.parser import parseQuery
from rdflib.plugins.sparql.parserutils import CompValue

from leefomgevinglab.ld.store import run_sparql
from leefomgevinglab.usecases.toezicht import graaf as graaf_mod

_TOEGESTANE_TYPEN = ("SelectQuery", "AskQuery")
_MAX_LIMIT = 200

GROUNDING = f"""\
Lokale RDF-graaf (rdflib), namespace:
  t: <{graaf_mod.T}>
Klassen: t:Vestiging, t:Voorschrift, t:Bewering, t:Meting, t:Norm, t:Signaal.
Een Vestiging draagt t:naam, t:locatiecode en t:kenmerk als gewone literal -- SELECTEER DIE, nooit
het vestigingsknooppunt zelf: dat is een blank node en levert een onleesbaar id op.
Een Vestiging draagt verder t:heeftVoorschrift (naar een Voorschrift) en t:heeftVeld (naar een
Bewering over naam/plaats/locatie/locatiecode/vestigingsnummer_kvk/kenmerk/besluitdatum/
waterlichaam/url) -- die Bewering gebruik je alleen als de vraag over zekerheid of herkomst gaat.
Een Voorschrift draagt t:parameter, t:waarde, t:eenheid, t:bemonstering (directe velden) en
t:heeftHoedanigheid / t:heeftAquoKoppeling (elk naar een Bewering).
Een Bewering draagt t:veld, t:waarde, t:zekerheid (een van "uit de bron"/"afgeleid"/"aangenomen"/
"ontbreekt") en optioneel t:herkomst.
Een Meting draagt t:meetpunt, t:waterlichaam, t:stof, t:mediaan, t:maximum, t:eenheid.
Een Norm draagt t:meetpunt, t:stof, t:waarde, t:eenheid, t:grondslag.
Een Vestiging draagt t:heeftSignaal (naar een Signaal). Een Signaal draagt t:regel (de regel-id),
t:kop, t:zwaarte ("hoog"/"midden"/"laag"), t:omvang, en twee assen die je niet moet verwarren:
  t:laag is "papier" (de vergunning klopt niet tegen zichzelf; dit staat op /wasstraat, bij de
    vergunningverlener) of "werkelijkheid" (er is meetdata of stroomrichting voor nodig; dit
    staat op /toezicht, bij de toezichthouder);
  t:rol is "bevinding" (hier valt iets te repareren) of "voorbehoud" (deze regel vuurt op vrijwel
    het hele register en zegt dus niets over één vergunning).
Een vraag die beide lezers raakt, combineert ze: twee t:heeftSignaal op dezelfde Vestiging, de
een met t:laag "papier" en t:rol "bevinding", de ander met t:laag "werkelijkheid".
Gebruik SELECT DISTINCT zodra een vestiging via twee paden tegelijk wordt gematcht (bv. twee keer
t:heeftSignaal): zonder DISTINCT levert dat het kruisproduct van die paden op, en dan zegt het
aantal rijen niets over het aantal vergunningen.
Geef UITSLUITEND de SPARQL SELECT- of ASK-query terug: geen uitleg, geen ```-fences, altijd met
een LIMIT bij een SELECT."""

DISCLAIMER = ("Indicatief: deze query is door een taalmodel gegenereerd op een lokale, afgeleide "
             "graaf. Geen vaststelling, geen officieel cijfer.")
VANGNET = "Controleer de uitgevoerde query en de brondata (Atlas, WKP, KRW) zelf bij twijfel."
BRON = "Toezichtgraaf: Atlas voor een Schone Maas + WKP + KRW-normen + Aquo (eigen, lokaal, afgeleid)."


class OngeldigeSparql(Exception):
    """De query is geen geldige SPARQL-leesquery (SELECT/ASK), bevat een verboden operatie, een
    SERVICE- of FROM-clause, mist een verplichte LIMIT, of overschrijdt de toegestane LIMIT."""


def _bevat_knooppunt(node, naam: str) -> bool:
    """Of een CompValue met deze naam ergens in de parse-boom voorkomt, hoe diep ook genest --
    zo wordt een SERVICE-clause ook binnen een subquery of geneste group graph pattern gevonden.
    AST-gebaseerd, niet tekst-gebaseerd: commentaar en hoofdlettergebruik kunnen dit niet omzeilen
    (de tokenizer heeft commentaar al weggegooid, en de grammatica is al case-insensitief)."""
    if isinstance(node, str):
        return False
    if isinstance(node, CompValue) and node.name == naam:
        return True
    if isinstance(node, dict):
        return any(_bevat_knooppunt(v, naam) for v in node.values())
    if isinstance(node, (list, tuple)):
        return any(_bevat_knooppunt(v, naam) for v in node)
    try:
        iterator = iter(node)
    except TypeError:
        return False
    return any(_bevat_knooppunt(v, naam) for v in iterator)


def valideer_sparql(q: str) -> str:
    """De bewaking: werpt `OngeldigeSparql` voor alles wat geen read-only SELECT/ASK is, voor een
    ontbrekende LIMIT bij een SELECT, en voor een LIMIT boven `_MAX_LIMIT`. Geeft anders de query
    ongewijzigd terug -- nooit een herschreven versie, zie de moduledocstring."""
    tekst = (q or "").strip()
    if not tekst:
        raise OngeldigeSparql("lege query")
    try:
        geparsed = parseQuery(tekst)
    except Exception as exc:
        raise OngeldigeSparql(f"geen geldige SPARQL-leesquery: {exc}") from exc
    query = geparsed[1]
    soort = getattr(query, "name", None)
    if soort not in _TOEGESTANE_TYPEN:
        raise OngeldigeSparql(f"alleen SELECT/ASK toegestaan, niet {soort}")
    # NB: `CompValue.get(sleutel)` geeft bij rdflib de sleutelnaam zelf terug als default (geen
    # `None`!) -- daarom hier `in` gebruiken voor aanwezigheid, nooit `.get(...)` op een CompValue.
    if "datasetClause" in query:
        raise OngeldigeSparql("FROM/FROM NAMED niet toegestaan -- deze graaf is lokaal, geen federatie")
    if _bevat_knooppunt(query, "ServiceGraphPattern"):
        raise OngeldigeSparql("SERVICE-clause niet toegestaan -- geen federatie, geen netwerk")
    if soort == "SelectQuery":
        limitoffset = query["limitoffset"] if "limitoffset" in query else None
        limiet = limitoffset["limit"] if limitoffset is not None and "limit" in limitoffset else None
        if limiet is None:
            raise OngeldigeSparql("LIMIT is verplicht bij een SELECT")
        if int(limiet) > _MAX_LIMIT:
            # Geen tekst-brede re.sub meer (fix-ronde 1, Important): die trof ook stringliterals
            # die toevallig op "limit <getal>" lijken. De geparste node draagt geen locatie om
            # alleen de echte clausule te raken, dus wordt een te grote LIMIT geweigerd -- net als
            # een ontbrekende -- in plaats van de tekst te herschrijven. Zie de moduledocstring.
            raise OngeldigeSparql(f"LIMIT boven de toegestane {_MAX_LIMIT} wordt geweigerd, "
                                  "niet aangepast")
    return tekst


def _strip_codeblok(tekst: str) -> str:
    m = re.search(r"```(?:sparql)?\s*(.+?)```", tekst, re.DOTALL | re.IGNORECASE)
    return (m.group(1) if m else tekst).strip()


def genereer_sparql(vraag: str, llm) -> str:
    """`llm` is een geïnjecteerde functie `str -> str` (het volledige prompt -> het ruwe
    antwoord) -- geen httpx hier, zodat een test het taalmodel zelf nooit aanroept."""
    prompt = f"{GROUNDING}\n\nVraag: {vraag}"
    ruwe = llm(prompt)
    return _strip_codeblok(ruwe or "")


def stel(vraag: str, graaf, llm) -> dict:
    """Grond -> genereer -> valideer -> voer uit, met het conservatieve contract dat `/afval` en
    `/datavraag` al voeren: antwoord, sparql en rijen altijd zichtbaar, nooit een stille 500."""
    base = {"vraag": vraag, "disclaimer": DISCLAIMER, "vangnet": VANGNET, "bron": BRON}
    if graaf is None:
        return {**base, "antwoord": None, "sparql": None, "rijen": [], "beschikbaar": False}
    try:
        ruwe = genereer_sparql(vraag, llm)
    except Exception as exc:  # noqa: BLE001 -- llm is geïnjecteerd, elke fout van buiten mag
        return {**base, "antwoord": "AI tijdelijk niet beschikbaar.", "sparql": None,
                "rijen": [], "beschikbaar": False, "fout": type(exc).__name__}
    try:
        sparql = valideer_sparql(ruwe)
    except OngeldigeSparql:
        return {**base, "antwoord": "Deze vraag kon niet veilig naar een query worden vertaald.",
                "sparql": ruwe, "rijen": [], "beschikbaar": False}
    try:
        rijen = run_sparql(graaf, sparql)
    except Exception:  # noqa: BLE001 -- een query kan ook tegen een geldige graaf nog breken
        return {**base, "antwoord": "De query kon niet worden uitgevoerd.", "sparql": sparql,
                "rijen": [], "beschikbaar": False}
    antwoord = f"{len(rijen)} resultaten." if rijen else "Geen resultaten voor deze vraag."
    return {**base, "antwoord": antwoord, "sparql": sparql, "rijen": rijen, "beschikbaar": True}


def taalmodel(base_url: str, model: str, timeout_s: float = 60.0):
    """Een `llm`-functie (`str -> str`) die het lokale llama.cpp-model op `base_url` aanroept.

    **Waarom deze factory hier staat en niet in de route.** `stel()` en `genereer_sparql()` nemen
    `llm` als geïnjecteerde functie, zodat een test nooit een model aanroept; dat contract blijft
    precies zo. Deze factory is alleen de ene plek waar dat contract wordt ingevuld voor echt
    gebruik, zodat de route één regel blijft en de HTTP-vorm niet in `api.py` terechtkomt.

    **Eerlijk over de duplicatie:** dit is de achtste plek in dit lab die hetzelfde
    `/chat/completions`-verzoek doet (zie o.a. `usecases/afval/chat._chat`,
    `usecases/datavraag/nl2sparql`, `usecases/afval/duiding`). Die zeven samenvoegen is een eigen
    opruiming en hoort niet in een feature-tak; wat hier telt is dat `/toezicht` er geen
    negende variant bovenop zet en dat het aanroeppad testbaar blijft.

    Een fout van het model wordt niet opgevangen: `stel()` doet dat al expliciet en geeft dan
    "AI tijdelijk niet beschikbaar" terug in plaats van een 500. Hier stil een lege string
    teruggeven zou van een onbereikbaar model een lege query maken, en dat leest als "deze vraag
    kon niet veilig worden vertaald" -- een verkeerde diagnose voor de gebruiker."""
    import httpx

    def aanroepen(prompt: str) -> str:
        resp = httpx.post(
            f"{base_url.rstrip('/')}/chat/completions",
            json={"model": model, "messages": [{"role": "user", "content": prompt}],
                  "temperature": 0.0},
            timeout=timeout_s,
        )
        resp.raise_for_status()
        return resp.json()["choices"][0]["message"]["content"].strip()

    return aanroepen
