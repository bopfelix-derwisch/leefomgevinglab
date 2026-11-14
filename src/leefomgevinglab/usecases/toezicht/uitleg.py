"""De uitlegger -- "waarom is dit erg?" (plan, §5.4), en nooit verder dan de bron gaat.

Een signaal zonder uitleg is voor een toezichthouder die niet thuis is in lozingsnormen en
Aquo-codes onbruikbaar. Maar een uitleg zonder benoemde bron is **erger dan geen uitleg**: zij
draagt een gezag dat zij niet heeft verdiend. Daarom antwoordt deze module uitsluitend uit een
afgebakende bronnenset, en zegt zij het eerlijk als zij er niets in vindt (brief, stap 1/2):

- de Aquo-domeintabel Parameter, inclusief de status van een code en haar `Vervangen door`
  (`toezicht.aquo.laad`, sinds taak 7 uitgebreid met die laatste kolom -- zie `aquo.py`);
- de KRW-normen (`krw_normen.json`, via `kmg.doelen.laad`) -- alleen de **chemische norm per
  stof en meetpunt**, niet het doel-per-waterlichaam dat `doelen.py` ernaast houdt: dat
  onderscheid is precies waarom `doelen.py` zelf twee functies heeft (`chemisch()` versus
  `toets()`), en deze module behoudt het door alleen de chemische kant te lezen;
- de Stelselcatalogus Omgevingswet (`connectors.stelselcatalogus.StelselcatalogusConnector`),
  voor de juridische vindplaats van een begrip -- "waarom is zwevende stof hier relevant" komt
  dan met een verwijzing naar de regeling, niet uit het model zelf.

**Waarom geen vectorindex (de open vraag uit de opdracht).** `/chatbot` gebruikt bge-m3 +
`VectorStore` omdat haar bron (IPLO) ongestructureerd proza is: duizenden documentpassages
zonder sleutel, waar alleen semantische gelijkenis een passage bij een vraag kan vinden. Geen van
de drie bronnen hier is dat. De Aquo-tabel en de KRW-normen zijn allebei al **sleutel-waarde**
(naam/code -> status, code/meetpunt -> norm) -- een vectorindex zou daar een onzekere, niet-
reproduceerbare gok over leggen op iets dat exact is na te slaan. De Stelselcatalogus doet haar
eigen woordzoekopdracht al op de bron zelf (`zoekTerm`), dus een tweede, eigen index zou die
verdubbelen zonder iets toe te voegen. Voor een paar duizend korte, structurele feiten is
letterlijke/woordgrens-matching dus niet de armere keuze maar de **juistere**: zij kan nooit een
stof vinden die er niet letterlijk staat, en dat is precies de garantie die de harde regel
hieronder vraagt. Embeddings winnen pas als de vraagstelling en de brontekst niet dezelfde woorden
delen -- hier delen ze die vrijwel altijd, want de vraag komt uit de eigen voorschriftnaam.

**De harde regel.** `waarom()` geeft nooit tekst terug zonder dat er minstens één treffer een
`vindplaats` draagt (`beschikbaar=False` anders, met een reden), en nooit tekst die een van de
drie verboden woorden bevat ("overtreding", "veroorzaakt door", "in strijd met") -- ook niet als
die toevallig uit een treffer komt. Zie `_toegestaan()`: een treffer die de taalregel breekt
wordt genegeerd, niet opgeschoond, want een bron die zulke taal gebruikt is hier niet te
vertrouwen in plaats van te herschrijven.
"""
import re

_VERBODEN = ("overtreding", "veroorzaakt door", "in strijd met")

_GEEN_TREFFER = (
    "Geen van de bronnen (Aquo-domeintabel Parameter, KRW-normen, Stelselcatalogus Omgevingswet) "
    "bevat een treffer voor deze vraag. Daarom legt de uitlegger hier niets uit -- hij weet het "
    "niet, en zegt dat liever dan te gokken."
)


def _toegestaan(tekst: str) -> bool:
    """Of `tekst` vrij is van de drie verboden woorden -- dezelfde taalregel als `signalen.py`,
    hier als poort vóór een treffer meetelt, niet als schoonmaakronde erna."""
    laag = (tekst or "").lower()
    return not any(verboden in laag for verboden in _VERBODEN)


def _bevat(haystack_lower: str, term: str) -> bool:
    """Of `term` als los woord (of woordgroep) in `haystack_lower` voorkomt -- woordgrensmatching,
    geen losse substring: "Zn" mag niet toevallig binnen een ander woord opduiken."""
    term = (term or "").strip().lower()
    if not term:
        return False
    return re.search(r"\b" + re.escape(term) + r"\b", haystack_lower) is not None


def _aquo_treffers(vraag_lower: str, aquo_ref: dict) -> list[dict]:
    """Treffers uit de Aquo-domeintabel: een geldige naam, of een ingetrokken naam met (indien
    aanwezig) haar opvolger. `aquo_ref` is de vorm die `aquo.laad()` teruggeeft."""
    uit = []
    vervangen_door = aquo_ref.get("vervangen_door") or {}
    for naam, code in (aquo_ref.get("geldig") or {}).items():
        if not _bevat(vraag_lower, naam):
            continue
        uit.append({
            "tekst": f"'{naam.capitalize()}' is in de Aquo-domeintabel Parameter een geldige "
                     f"parameter (code {code}).",
            "vindplaats": f"Aquo-domeintabel Parameter, code {code}, status Geldig",
        })
    for naam, code in (aquo_ref.get("vervallen") or {}).items():
        if not _bevat(vraag_lower, naam):
            continue
        vervanger = vervangen_door.get(naam)
        vervolg = (f" Vervangen door code {vervanger}." if vervanger
                   else " Er is geen vervangende code geregistreerd.")
        uit.append({
            "tekst": f"'{naam.capitalize()}' is in de Aquo-domeintabel Parameter ingetrokken "
                     f"(code {code}, status Vervallen).{vervolg}",
            "vindplaats": f"Aquo-domeintabel Parameter, code {code}, status Vervallen",
        })
    return uit


def _naam_bij_code(aquo_ref: dict) -> dict:
    """Code -> naam, de omkering van `aquo_ref["geldig"]` -- nodig omdat de KRW-normen alleen de
    code dragen (zie `krw_normen.json`), geen Nederlandse naam."""
    return {code: naam for naam, code in (aquo_ref.get("geldig") or {}).items()}


def _krw_treffers(vraag_lower: str, normenset: dict, aquo_ref: dict) -> list[dict]:
    """Treffers uit de KRW-normen -- alleen de **chemische norm per stof/meetpunt**
    (`kmg.doelen`'s onderscheid met een doel per waterlichaam, zie de moduledocstring). Eén
    treffer per unieke (code, hoedanigheid, grondslag): dezelfde norm staat op meerdere
    meetpunten, en dat is geen tien keer dezelfde vindplaats waard."""
    naam_bij_code = _naam_bij_code(aquo_ref)
    gezien = set()
    uit = []
    for rijen in (normenset.get("normen") or {}).values():
        for n in rijen:
            code = n.get("parameter")
            sleutel = (code, n.get("hoedanigheid"), n.get("grondslag"))
            if sleutel in gezien:
                continue
            naam = naam_bij_code.get(code, code)
            if not (_bevat(vraag_lower, naam) or _bevat(vraag_lower, code or "")):
                continue
            gezien.add(sleutel)
            uit.append({
                "tekst": f"Voor {naam} geldt een KRW-norm van {n.get('norm')} {n.get('eenheid')} "
                         f"({n.get('grondslag')}, hoedanigheid {n.get('hoedanigheid') or 'NVT'}).",
                "vindplaats": f"KRW-toetsresultaten (krw_normen.json), parameter {code}, "
                               f"meetpunt {n.get('meetpunt')}",
            })
    return uit


def _catalogus_treffers(vraag: str, catalogus) -> list[dict]:
    """Treffers uit de Stelselcatalogus Omgevingswet -- een live zoekopdracht op de bron zelf
    (`StelselcatalogusConnector.zoek`), dus geen eigen index. `catalogus` is injecteerbaar en
    standaard `None`: zonder connector doet deze functie niets, in plaats van er zelf een te
    maken (dat zou een stilzwijgende netwerkaanroep in een functie verbergen die daar geen
    argument voor krijgt)."""
    if catalogus is None:
        return []
    try:
        treffers = catalogus.zoek(vraag)
    except Exception:  # noqa: BLE001 -- een live bron mag nooit de uitlegger laten crashen
        return []
    uit = []
    for b in treffers or []:
        if not b.get("definitie"):
            continue
        vindplaats = f"Stelselcatalogus Omgevingswet, begrip '{b.get('term')}'"
        if b.get("vindplaats"):
            vindplaats += f" ({b['vindplaats']})"
        uit.append({"tekst": f"'{b.get('term')}': {b['definitie']}", "vindplaats": vindplaats})
    return uit


def zoek_bronnen(vraag: str, n: int, *, aquo_ref: dict | None = None,
                  normenset: dict | None = None, catalogus=None) -> list[dict]:
    """De standaard-retrieval: woordgrensmatching over drie bronnen, geïnjecteerd als
    al-geladen referenties (`aquo_ref`, `normenset`) of een connector (`catalogus`) -- zelfde
    stijl als `aquo.verrijk(vestiging, ref)` en `doelen.toets(doelenset, ...)`: deze functie laadt
    zelf niets van schijf en doet zelf geen netwerk, dat is aan de aanroeper (de runner-tool,
    `runner.tool_uitleg_genereren`). Zonder enige bron geeft zij dus terecht niets terug -- dat is
    niet een fout van deze functie, maar het eerlijke antwoord op "geen bron aangeleverd".

    Geen rangschikking op relevantie (geen score, geen embedding om op te sorteren): de volgorde
    is Aquo, dan KRW, dan de Stelselcatalogus -- eigen, exacte structuurdata eerst, de
    vrije-tekst-zoekopdracht op een externe bron als laatste. `n` knipt simpelweg af."""
    vraag_lower = (vraag or "").lower()
    treffers = _aquo_treffers(vraag_lower, aquo_ref or {})
    treffers += _krw_treffers(vraag_lower, normenset or {}, aquo_ref or {})
    treffers += _catalogus_treffers(vraag, catalogus)
    return treffers[:n] if n else treffers


def waarom(vraag: str, *, n: int = 3, _zoek=None, llm=None) -> dict:
    """Waarom dit (signaal, stof, begrip) aandacht vraagt -- uitsluitend uit de afgebakende
    bronnenset, met minstens één benoemde vindplaats zodra er iets te zeggen is, en anders een
    eerlijk "ik weet het niet" (brief, stap 1/2).

    `_zoek(vraag, n) -> list[dict]` is de injecteerbare retrieval (zie de brief: `_zoek=lambda q,
    n: []` in de test) -- zonder override valt deze functie terug op `zoek_bronnen` met lege
    bronnen, wat zonder verder geïnjecteerde data niets vindt en dus nooit zelf het netwerk of de
    schijf raakt. `llm` is optioneel en **herformuleert alleen** -- de vindplaatsen komen altijd
    rechtstreeks uit de treffers, nooit uit het model, en een herformulering die de taalregel
    breekt of mislukt valt terug op de deterministische tekst (zie `_herformuleer`)."""
    zoekfunctie = _zoek or zoek_bronnen
    ruwe = zoekfunctie(vraag, n) or []
    # De poort: geen vindplaats of een verboden woord betekent "deze treffer telt niet mee" --
    # niet opschonen, zie de moduledocstring.
    treffers = [t for t in ruwe if t.get("vindplaats") and _toegestaan(t.get("tekst") or "")]
    if not treffers:
        return {"vraag": vraag, "beschikbaar": False, "tekst": None, "vindplaatsen": [],
                "reden": _GEEN_TREFFER, "bronnen": []}

    vindplaatsen = [t["vindplaats"] for t in treffers]
    tekst = " ".join(t["tekst"] for t in treffers if t.get("tekst"))
    if llm is not None:
        herschreven = _herformuleer(vraag, treffers, llm)
        if herschreven and _toegestaan(herschreven):
            tekst = herschreven
    return {"vraag": vraag, "beschikbaar": True, "tekst": tekst, "vindplaatsen": vindplaatsen,
            "reden": None, "bronnen": treffers}


_PROMPT = """\
Je bent een uitlegger voor een toezichthouder op lozingen in de Maas. Leg in maximaal drie zinnen
uit waarom de volgende vraag aandacht verdient, UITSLUITEND op basis van de onderstaande feiten.
Verzin niets erbij, trek geen conclusie over of iets een overtreding is, en gebruik nooit de
woorden "overtreding", "veroorzaakt door" of "in strijd met". Als de feiten geen antwoord geven,
zeg dat.

Vraag: {vraag}

Feiten:
{feiten}
"""


def _herformuleer(vraag: str, treffers: list[dict], llm) -> str | None:
    """Een leesbaardere formulering van dezelfde treffers, via een geïnjecteerde `llm` (een
    functie `str -> str`, zoals `vraag.genereer_sparql` die ook injecteert) -- nooit een eigen
    httpx-aanroep hier, dus een test kan dit zonder netwerk toetsen. Elke fout van de aanroeper
    (timeout, onzinnig antwoord) valt stil terug op `None`, waarna `waarom()` de deterministische
    tekst houdt: een herformulering is een verfraaiing, nooit de enige weg naar een antwoord."""
    feiten = "\n".join(f"- {t['tekst']}" for t in treffers)
    try:
        return (llm(_PROMPT.format(vraag=vraag, feiten=feiten)) or "").strip() or None
    except Exception:  # noqa: BLE001 -- een geïnjecteerd model mag de uitlegger nooit laten vallen
        return None
