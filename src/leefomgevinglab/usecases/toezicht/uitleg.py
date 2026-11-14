"""De uitlegger -- "waarom is dit erg?" (plan, §5.4), en nooit verder dan de bron gaat.

Een signaal zonder uitleg is voor een toezichthouder die niet thuis is in lozingsnormen en
Aquo-codes onbruikbaar. Maar een uitleg zonder benoemde bron is **erger dan geen uitleg**: zij
draagt een gezag dat zij niet heeft verdiend. Daarom antwoordt deze module uitsluitend uit een
afgebakende bronnenset, en zegt zij het eerlijk als zij er niets in vindt (brief, stap 1/2). Vier
bronnen, precies de vier uit het plan (§5.4):

- de Aquo-domeintabel Parameter, inclusief de status van een code en haar `Vervangen door`
  (`toezicht.aquo.laad`, sinds taak 7 uitgebreid met die laatste kolom -- zie `aquo.py`);
- de KRW-normen (`krw_normen.json`, via `kmg.doelen.laad`) -- alleen de **chemische norm per
  stof en meetpunt**, niet het doel-per-waterlichaam dat `doelen.py` ernaast houdt: dat
  onderscheid is precies waarom `doelen.py` zelf twee functies heeft (`chemisch()` versus
  `toets()`), en deze module behoudt het door alleen de chemische kant te lezen;
- de Stelselcatalogus Omgevingswet (`connectors.stelselcatalogus.StelselcatalogusConnector`),
  voor de juridische vindplaats van een begrip -- "waarom is zwevende stof hier relevant" komt
  dan met een verwijzing naar de regeling, niet uit het model zelf;
- de proclaimerteksten van `/kmg` (`kmg.proclaimer`) -- **sinds fix-ronde 1**, en niet decoratief:
  dit is de enige bron die geen stofnaam nodig heeft. De drie bronnen hierboven matchen allemaal
  op een stof- of codenaam, en een aantal signalen draagt geen enkele in hun bewijs
  (`niet_regime_zuiver`, `norm_overschreden_bovenstrooms` noemt er wel een, maar de vraag "waarom
  is bovenstrooms-liggen relevant" is geen stof-vraag). `proclaimer.bouw()` is een zuivere functie
  van haar argumenten (geen bestand, geen netwerk) en draagt precies het soort niet-sleutel-waarde
  kanttekening dat deze signalen nodig hebben: dat een vergunning een vracht begrenst en dus niet
  tegen een andere grootheid (bv. de opgeloste fractie) gelegd mag worden, en dat het register
  nooit een oorzaak vaststelt, alleen een bovengrens. Zie `_PROCLAIMER_NOTITIES` voor de twee
  kanttekeningen die vandaag zo ontsloten zijn, en hun eigen drift-bewakende test
  (`test_proclaimer_notities_vinden_vandaag_hun_fragment_in_de_echte_tekst`).

**Waarom geen vectorindex (de open vraag uit de opdracht).** `/chatbot` gebruikt bge-m3 +
`VectorStore` omdat haar bron (IPLO) ongestructureerd proza is: duizenden documentpassages
zonder sleutel, waar alleen semantische gelijkenis een passage bij een vraag kan vinden. Geen van
de vier bronnen hier is dat. De Aquo-tabel en de KRW-normen zijn allebei al **sleutel-waarde**
(naam/code -> status, code/meetpunt -> norm) -- een vectorindex zou daar een onzekere, niet-
reproduceerbare gok over leggen op iets dat exact is na te slaan (en zou de precedentie-regel van
`_aquo_treffers` hieronder evengoed zelf moeten implementeren, dus geen vrijstelling van die
plicht). De Stelselcatalogus doet haar eigen woordzoekopdracht al op de bron zelf (`zoekTerm`),
dus een tweede, eigen index zou die verdubbelen zonder iets toe te voegen. De proclaimerteksten
zijn een handvol vaste alinea's, geen corpus. Voor een paar duizend korte, structurele feiten is
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

**Twee woordgrensmatchers, met opzet (fix-ronde 1, bevinding 2).** `_bevat()` (los, `\\b...\\b`)
is voor de eigen, gecontroleerde triggerwoorden van de proclaimer-kanttekeningen -- "regime" moet
bijvoorbeeld vuren op de signaalkop "toets niet *regime*-zuiver", een samengesteld woord met een
koppelteken. `_bevat_stofnaam()` (strenger, geen koppelteken of woordteken aan weerszijden) is
voor Aquo- en KRW-stofnamen: een live proef op `(1-butyloctyl)-benzeen` leverde met de losse
matcher een treffer op *Benzeen* op -- een andere stof die alleen als staart van een samengestelde
naam voorkomt. Scheikundige namen zijn vaak met een koppelteken samengesteld, en precies daar moet
de hardere garantie van de harde regel gelden: een treffer die een andere stof citeert dan er
feitelijk staat, draagt zelf een onterecht gezag. Dat risico speelt niet bij de eigen
triggerwoorden, want die komen niet uit chemische nomenclatuur maar uit dit lab zelf.
"""
import re

from leefomgevinglab.usecases.kmg import proclaimer as proclaimer_mod

_VERBODEN = ("overtreding", "veroorzaakt door", "in strijd met")

_GEEN_TREFFER = (
    "Geen van de bronnen (Aquo-domeintabel Parameter, KRW-normen, Stelselcatalogus Omgevingswet, "
    "de /kmg-proclaimer) bevat een treffer voor deze vraag. Daarom legt de uitlegger hier niets "
    "uit -- hij weet het niet, en zegt dat liever dan te gokken."
)


def _toegestaan(tekst: str) -> bool:
    """Of `tekst` vrij is van de drie verboden woorden -- dezelfde taalregel als `signalen.py`,
    hier als poort vóór een treffer meetelt, niet als schoonmaakronde erna."""
    laag = (tekst or "").lower()
    return not any(verboden in laag for verboden in _VERBODEN)


def _bevat(haystack_lower: str, term: str) -> bool:
    """Of `term` als los woord (of woordgroep) in `haystack_lower` voorkomt -- gewone
    woordgrensmatching (`\\b`), waarbij een koppelteken wél als grens telt ("regime" vuurt dus op
    "regime-zuiver"). Voor de eigen, gecontroleerde triggerwoorden van de proclaimer-
    kanttekeningen (zie de moduledocstring) -- niet voor stofnamen, zie `_bevat_stofnaam`."""
    term = (term or "").strip().lower()
    if not term:
        return False
    return re.search(r"\b" + re.escape(term) + r"\b", haystack_lower) is not None


def _bevat_stofnaam(haystack_lower: str, term: str) -> bool:
    """Strengere grensmatching voor Aquo- en KRW-stofnamen: de term mag aan weerszijden geen
    woordteken *en* geen koppelteken hebben. Fix-ronde 1, bevinding 2: met de losse `_bevat` gaf
    de query '(1-butyloctyl)-benzeen' een treffer op 'Benzeen' -- een andere stof die hier alleen
    als staart van een samengestelde naam voorkomt. Zie de moduledocstring voor de volledige
    afweging."""
    term = (term or "").strip().lower()
    if not term:
        return False
    patroon = r"(?<![\w-])" + re.escape(term) + r"(?![\w-])"
    return re.search(patroon, haystack_lower) is not None


def _aquo_treffers(vraag_lower: str, aquo_ref: dict) -> list[dict]:
    """Treffers uit de Aquo-domeintabel: een geldige naam, of een ingetrokken naam met (indien
    aanwezig) haar opvolger. `aquo_ref` is de vorm die `aquo.laad()` teruggeeft.

    **Precedentie, fix-ronde 1, bevinding 2.** 748 namen in de echte bron staan zowel in `geldig`
    als in `vervallen` (bv. "minerale olie": een oude, ingetrokken code naast een nieuwe, geldige).
    Zonder voorrang leverde dit voor zo'n naam *twee* treffers op die elkaar tegenspreken --
    "geldig" en "ingetrokken" over precies dezelfde naam, in één `waarom`-tekst geplakt. `aquo.
    verrijk()` kent dit geval al en laat de geldige code winnen (zie haar eigen test
    `test_een_naam_met_zowel_een_geldige_als_een_ingetrokken_rij_telt_als_geldig`); deze functie
    past nu dezelfde regel toe, in plaats van er een eigen, afwijkende voorrang naast te zetten."""
    uit = []
    geldig = aquo_ref.get("geldig") or {}
    vervallen = aquo_ref.get("vervallen") or {}
    vervangen_door = aquo_ref.get("vervangen_door") or {}
    for naam, code in geldig.items():
        if not _bevat_stofnaam(vraag_lower, naam):
            continue
        uit.append({
            "tekst": f"'{naam.capitalize()}' is in de Aquo-domeintabel Parameter een geldige "
                     f"parameter (code {code}).",
            "vindplaats": f"Aquo-domeintabel Parameter, code {code}, status Geldig",
        })
    for naam, code in vervallen.items():
        if naam in geldig:
            # Zelfde voorrang als `aquo.verrijk()`: voor déze naam bestaat een geldige referentie,
            # dus de ingetrokken code is geen signaal meer waard (zie de docstring hierboven).
            continue
        if not _bevat_stofnaam(vraag_lower, naam):
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


def _bevat_code_hoofdlettergevoelig(vraag: str, code: str) -> bool:
    """Dezelfde woordgrens als `_bevat_stofnaam`, maar hoofdlettergevoelig en zonder de term zelf
    te lowercasen -- voor een **kale Aquo-code zonder bekende naam**.

    Eindreview, bevinding 4. Een handvol Aquo-codes is toevallig ook een gewoon Nederlands woord
    ("Te" (tellurium), "As", "Al", "U", "B", "V"). `_bevat_stofnaam` lowercast zowel de hooiberg
    als de term, dus die matchte "Te" zonder meer op het woord "te" in een zin als "vracht niet
    *te* bepalen" of "vergunning niet *te* vinden" -- met een KRW-norm en een vindplaats als
    bewijs voor een stof die nergens in de vraag aan de orde was. Een Aquo-code wordt altijd in
    zijn eigen schrijfwijze genoteerd (hoofdletter voorop); een gewoon Nederlands woord midden in
    een zin draagt die hoofdletter nooit. Hoofdlettergevoelig matchen tegen de *ongewijzigde*
    vraagtekst (niet tegen `vraag_lower`) sluit deze klasse fouten daarom uit zonder een
    woordenlijst met "gewone woorden" te moeten bijhouden."""
    code = (code or "").strip()
    if not code:
        return False
    patroon = r"(?<![\w-])" + re.escape(code) + r"(?![\w-])"
    return re.search(patroon, vraag) is not None


def _krw_treffers(vraag: str, normenset: dict, aquo_ref: dict) -> list[dict]:
    """Treffers uit de KRW-normen -- alleen de **chemische norm per stof/meetpunt**
    (`kmg.doelen`'s onderscheid met een doel per waterlichaam, zie de moduledocstring). Eén
    treffer per unieke (code, hoedanigheid, grondslag): dezelfde norm staat op meerdere
    meetpunten, en dat is geen tien keer dezelfde vindplaats waard.

    `vraag` is hier de **ongewijzigde** vraagtekst, niet `vraag_lower` (fix-ronde, eindreview
    bevinding 4, zie `_bevat_code_hoofdlettergevoelig`): een bekende stofnaam matcht nog altijd
    hoofdletter-ongevoelig (`_bevat_stofnaam`, net als voorheen), maar een kale code zonder naam
    matcht alleen nog hoofdlettergevoelig tegen de originele tekst."""
    vraag_lower = (vraag or "").lower()
    naam_bij_code = _naam_bij_code(aquo_ref)
    gezien = set()
    uit = []
    for rijen in (normenset.get("normen") or {}).values():
        for n in rijen:
            code = n.get("parameter")
            sleutel = (code, n.get("hoedanigheid"), n.get("grondslag"))
            if sleutel in gezien:
                continue
            naam = naam_bij_code.get(code)
            treft = bool(naam) and _bevat_stofnaam(vraag_lower, naam)
            if not treft and code:
                treft = _bevat_code_hoofdlettergevoelig(vraag, code)
            if not treft:
                continue
            weergavenaam = naam or code
            gezien.add(sleutel)
            uit.append({
                "tekst": f"Voor {weergavenaam} geldt een KRW-norm van {n.get('norm')} "
                         f"{n.get('eenheid')} ({n.get('grondslag')}, hoedanigheid "
                         f"{n.get('hoedanigheid') or 'NVT'}).",
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


def _proclaimer_kopjes() -> list[dict]:
    """De vier kopjes van de /kmg-proclaimer, als bron -- `proclaimer.bouw()` is een zuivere
    functie van haar argumenten (geen bestand, geen netwerk, zie `kmg/proclaimer.py`), dus met
    neutrale invoer (lege dicts, geen doelen) liggen de kopteksten gewoon vast. Lege invoer is hier
    bewust: deze module citeert specifieke, los van de Maas-cijfers staande zinnen uit die tekst
    (zie `_PROCLAIMER_NOTITIES`), niet de hele paragraaf -- die is vol Maas-specifieke getallen
    (afstanden, afvoercijfers) die in een uitleg over een willekeurig signaal niet thuishoren.
    `meetset={"beschikbaar": True}` kiest de kortere, onvoorwaardelijke formulering van het
    "kan bijdragen"-kopje (zonder de "zodra er wel metingen zijn"-inleiding) -- de inhoud van het
    citaat verandert niet, alleen de inleidende bijzin eromheen."""
    return proclaimer_mod.bouw({"beschikbaar": True}, {}, "het DSO", False)["kopjes"]


def _zin_met_fragment(kopjes: list[dict], kop_titel: str, fragment: str) -> str | None:
    """De zin uit kopje `kop_titel` die `fragment` bevat, letterlijk uit de live tekst -- geen
    eigen parafrase (die zou kunnen uiteenlopen van wat `/kmg` zelf zegt). `None` als het kopje of
    het fragment er niet (meer) in staat; `test_proclaimer_notities_vinden_vandaag_hun_fragment_
    in_de_echte_tekst` is de drift-wacht die zou falen zodra dat gebeurt."""
    tekst = next((k.get("tekst") or "" for k in kopjes if k.get("kop") == kop_titel), "")
    for zin in re.split(r"(?<=[.!?])\s+", tekst):
        if fragment.lower() in zin.lower():
            return zin.strip()
    return None


# Elke notitie: welke (eigen, gecontroleerde) triggerwoorden haar activeren, uit welk kopje zij
# komt en welk fragment de zin identificeert. Bewust niet stof-gebonden -- dat doen de andere drie
# bronnen al -- maar gekoppeld aan de signaalkop zelf, want precies de signalen zonder stofnaam in
# hun bewijs (`niet_regime_zuiver`, `norm_overschreden_bovenstrooms`) hebben hier iets aan.
_PROCLAIMER_NOTITIES = (
    {"sleutels": ("regime", "bemonstering"), "kop": "Wat van ons is",
     "fragment": "twee verschillende grootheden"},
    {"sleutels": ("bovenstrooms", "overschreden"), "kop": "Wat u hier niet uit kunt afleiden",
     "fragment": "kan bijdragen"},
)


def _proclaimer_treffers(vraag_lower: str) -> list[dict]:
    """Treffers uit de /kmg-proclaimer -- de vierde bron (fix-ronde 1, bevinding 1), en de enige
    die geen stofnaam nodig heeft. Altijd actief, ook zonder enige geïnjecteerde referentie: zij
    leest geen bestand en doet geen netwerk (`proclaimer.bouw()` is zuiver), dus dit raakt de
    belofte "geen netwerk, geen bestand zonder injectie" niet -- zie `zoek_bronnen`."""
    kopjes = _proclaimer_kopjes()
    uit = []
    for notitie in _PROCLAIMER_NOTITIES:
        if not any(_bevat(vraag_lower, sleutel) for sleutel in notitie["sleutels"]):
            continue
        zin = _zin_met_fragment(kopjes, notitie["kop"], notitie["fragment"])
        if not zin:
            continue
        uit.append({"tekst": zin,
                    "vindplaats": f"usecases/kmg/proclaimer.py (/kmg), kopje '{notitie['kop']}'"})
    return uit


def zoek_bronnen(vraag: str, n: int, *, aquo_ref: dict | None = None,
                  normenset: dict | None = None, catalogus=None) -> list[dict]:
    """De standaard-retrieval: woordgrensmatching over vier bronnen. Drie zijn geïnjecteerd als
    al-geladen referenties (`aquo_ref`, `normenset`) of een connector (`catalogus`) -- zelfde stijl
    als `aquo.verrijk(vestiging, ref)` en `doelen.toets(doelenset, ...)`: deze functie laadt zelf
    niets van schijf en doet zelf geen netwerk, dat is aan de aanroeper (de runner-tool,
    `runner.tool_uitleg_genereren`). Zonder die drie geeft zij voor hén dus terecht niets terug --
    dat is niet een fout van deze functie, maar het eerlijke antwoord op "geen bron aangeleverd".
    De vierde (de /kmg-proclaimer) is intrinsiek en altijd actief, want zij vraagt geen injectie:
    `proclaimer.bouw()` is een zuivere functie, geen bestand en geen netwerk (zie
    `_proclaimer_treffers`).

    Geen rangschikking op relevantie (geen score, geen embedding om op te sorteren): de volgorde
    is Aquo, dan KRW, dan de proclaimer, dan de Stelselcatalogus -- eigen, exacte structuurdata
    eerst, dan de eigen kanttekeningen, en de vrije-tekst-zoekopdracht op een externe bron als
    laatste. `n` knipt simpelweg af."""
    vraag_lower = (vraag or "").lower()
    treffers = _aquo_treffers(vraag_lower, aquo_ref or {})
    # De ongewijzigde `vraag`, niet `vraag_lower` -- `_krw_treffers` heeft de originele hoofdletters
    # zelf nodig voor haar hoofdlettergevoelige kale-code-fallback (zie die functie).
    treffers += _krw_treffers(vraag or "", normenset or {}, aquo_ref or {})
    treffers += _proclaimer_treffers(vraag_lower)
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
    # De poort: geen vindplaats of een verboden woord (in de tekst óf in de vindplaats zelf --
    # fix-ronde 2, bevinding A maakte de vindplaats voor het eerst zichtbaar op de pagina, dus de
    # taalregel moet haar nu net zo goed dekken) betekent "deze treffer telt niet mee". Niet
    # opschonen, zie de moduledocstring.
    treffers = [t for t in ruwe if t.get("vindplaats")
                and _toegestaan(t.get("tekst") or "") and _toegestaan(t.get("vindplaats") or "")]
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
