# Toezichtsignalen op de Schone Maas — agentisch, configureerbaar, lokaal

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Van de open data van de Atlas voor een Schone Maas een **informatieproduct voor een
toezichthouder** maken: een signaaldossier per vestiging, met per signaal de grondslag, het bewijs,
de zwaarte en een uitleg waarom het signaal aandacht vraagt — plus een bevraagbare laag waarin
diezelfde gegevens in natuurlijke taal te ondervragen zijn.

**Architecture:** Drie lagen, strikt gescheiden. (1) Een **feitenlaag**: de Atlas, het
Waterkwaliteitsportaal, de KRW-normen en de Aquo-domeintabel geharmoniseerd in één
triple-store volgens het bestaande lozingsmodel, met per veld een herkomst en een zekerheid.
(2) Een **signaallaag**: tien signaalregels, elk een gewone Python-functie, deterministisch, met
een test die hem tegen de echte bron narekent. (3) Een **agentlaag**: configureerbare agents die
het signaaldossier samenstellen, uitleggen en bevraagbaar maken — nooit agents die zélf bepalen
of er een signaal is.

**De configuratie is geen inrichtingsdetail maar een doel op zich.** In dit lab gebeurt veel onder
water: de gegevensherkomst is zichtbaar, de bewerking niet. Een leesbare `agents.yaml` plus een
runlog per dossier maken ook het *proces* navraagbaar — zie §4.2, waar vier eisen staan die
voorkomen dat die configuratie documentatie wordt die verouderd.

**Tech Stack:** Python 3.10, FastAPI, pytest, rdflib (bestaande `ld/store.py`), lokale Qwen2.5-32B
op `localhost:8080` (OpenAI-compatibel), bge-m3 op `localhost:8082`, openpyxl voor de
inspectiebijlage. Agentconfiguratie in **CrewAI-compatibele YAML**, uitgevoerd door een eigen
dunne runner — zie §4 voor waarom.

**Spec:** dit document is spec én plan. Het doel is dat **dit lab** een agentische toepassing
opzet: een eigen, configureerbare agentopstelling op een casus die het al goed kent. Die casus is
de **Atlas voor een Schone Maas** — 69 vestigingen en 782 vergunde lozingsvoorschriften, publiek
en live bevraagbaar, waar dit lab via `/kmg`, `/waterruimte`, `/maaskaart` en `/kennisgraaf` al
connectoren, een informatiemodel en een kwaliteitscontrole op heeft staan. De agentlaag is dus geen
nieuw fundament maar een nieuwe manier om op een bestaand fundament te werken.

Dat de doelgroep de **toezichthouder** is, komt uit een gesprek over de vraag wat een
informatieproduct moet zijn: het waterdossier beantwoordt tot nu toe de vraag van de
vergunningverlener, en toezicht heeft een andere behoefte (§1). Dat gesprek is de aanleiding; het
plan is verder op deze casus en deze omgeving gericht.

---

## Global Constraints

- **Taal:** alle code, commentaar, docstrings, commit-berichten en UI-teksten in het **Nederlands**.
- **Testen draaien met:** `cd /mnt/nvme/workspaces/LeefomgevingLab && .venv/bin/python -m pytest` —
  huidige stand **919 passed**. Live-tests met `DSO_API_KEY` gezet.
- **Geen netwerk in gewone tests.** Bronnen worden geïnjecteerd, zoals `regels.regels_op_locatie(_haal=…)`
  en `maaskaart.beeld(_atlas=…)` dat al doen. Live-controles staan in een apart `*_live.py`-bestand
  dat skipt zonder `DSO_API_KEY`.
- **Geen getal wordt getypt.** Elk cijfer op een pagina of in een rapport is afgeleid uit de bron,
  met een test die de afleiding narekent. Dit is de huisregel van dit lab en in deze use-case de
  kern van het product: een toezichthouder moet een signaal kunnen navragen.
- **Commit-trailer:** `Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>` plus de
  `Claude-Session:`-regel. **Niet pushen** zonder expliciete vraag van Bob.
- **`git add` met expliciete paden.** Nooit `git add -A` — er staan drie ongerelateerde untracked
  bestanden in de repo (twee `LeefomgevingLab architectuuropzet v0_*.md`, `notebooks/meting_vs_norm.png`).
- **De Atlas-lagen zijn publiek maar dragen géén expliciete licentie.** Live bevragen met
  bronvermelding, nooit de dataset in de repo kopiëren. Alleen verdichtingen die klein genoeg zijn.
- **De harde taalregel, overgenomen uit `/kmg`:** een signaal is nooit een vaststelling. De woorden
  "overtreding", "veroorzaakt door" en "in strijd met" komen niet in een signaaltekst voor. Wel:
  "vraagt aandacht", "kan duiden op", "niet te controleren". Een test bewaakt dat op de
  gegenereerde tekst, niet alleen op de sjablonen.
- **Geen LLM in de signaalbepaling.** Een taalmodel mag een signaal uitleggen, samenvatten en
  bevraagbaar maken. Het mag nooit bepalen *of* er een signaal is. Zie §4.4.
- **Niets gebeurt buiten de configuratie om.** Elke stap die een dossier vormt, staat in
  `agents.yaml`/`tasks.yaml` en komt in de runlog terecht. Een tool die een agent niet heeft
  verklaard, kan hij niet aanroepen. Een pijplijnplaatje op de pagina wordt uit diezelfde YAML
  gegenereerd en nooit los onderhouden. Dit is geen stijlregel maar de voorwaarde waaronder de
  transparantie van §4.2 waar blijft, en er staan drie tests op.

---

## 1. Waarom toezicht een andere vraag is dan vergunningverlening

Dit lab heeft het waterdossier tot nu toe gebouwd rond de vraag van de **vergunningverlener**:
*wat kan hier nog?* Dat is een vraag naar vrije ruimte — `/gebruiksruimte`, `/waterruimte` en het
eindbeeld rekenen hem uit. Wat in dat kader niet past, werd in het gesprek precies benoemd:

> "we hadden een soort business case vanuit de vergunningverlening, wat kunnen we nog toestaan
> hier aan extra milieubelastende dingen, maar dat is voor een toezichthouder natuurlijk niet zo
> interessant. Die wil dat soort dingen weten waar jij mee bezig bent. Wat zijn signalen?"

Het verschil is niet cosmetisch, het verandert het product:

| | vergunningverlening | toezicht |
|---|---|---|
| de vraag | wat kan hier nog? | waar moet ik gaan kijken? |
| de eenheid | het waterlichaam | de vestiging |
| wat telt | de ruimte tot de norm | de afwijking tussen papier en praktijk |
| de uitkomst | een getal met een marge | een **gerangschikte lijst met bewijs** |
| wanneer goed | de som klopt | de inspecteur vond ter plaatse wat het signaal beloofde |
| onzekerheid | een bandbreedte | een reden om er juist wél heen te gaan |

Twee gevolgen die het hele ontwerp bepalen. **Een gat in de data is voor een toezichthouder zelf
een signaal.** Waar de vergunningverlener een ontbrekend gegeven als beperking ziet, is "deze
grenswaarde is niet te controleren" voor toezicht een bevinding die een bezoek kan rechtvaardigen.
En: **een signaal zonder uitleg is onbruikbaar** — niet iedere toezichthouder is even thuis in
lozingsvoorschriften en Aquo-codes:

> "Niet alle toezichthouder zijn even thuis in deze materie. Ja, dus dan krijgen ze signalen, maar
> dan moet ze ook wel weten, welke vragen, waar moet je dan op letten (...) dan kan die een vraag
> stellen, en die agent die gaat dan op zoek in de wetgeving bij LMA, een aantal vastgestelde
> bronnen van, dit is de reden waarom zo'n signaal naar de aandacht vraagt."

Daarom is "waarom is dit erg?" in dit plan geen bijzaak maar een eigen agent met eigen bronnen (§5.4).

## 2. Het informatieproduct: het signaaldossier

Eén vestiging, één pagina, drie delen. Geen dashboard — een toezichthouder neemt dit mee.

**Deel A — de kaart van de vestiging.** Naam, plaats, locatiecode, KvK-vestigingsnummer,
vergunningkenmerk, besluitdatum, het waterlichaam waarop geloosd wordt, en de link naar het
vergunningdocument. Elk veld met zijn herkomst, en ontbrekende velden expliciet als ontbrekend —
niet weggelaten. Van de 69 vestigingen mist er bij 8 een `url`, bij 6 een `kenmerk` en bij 5 een
`besluitdatum` (geverifieerd, §3).

**Deel B — de signalen, gerangschikt.** Per signaal:

- `signaal` — de regel die vuurde, uit de catalogus van §6
- `zwaarte` — `hoog` / `midden` / `laag`, **afgeleid** uit de regel plus de omvang, nooit getypt
- `bewijs` — de concrete rijen: welk voorschrift, welke meting, welke code, met waarden
- `grondslag` — waarop de koppeling berust: `code`, `ruimtelijk`, `heuristiek` of `geen`
  (hergebruikt uit `maaskaart.GRONDSLAG`)
- `zekerheid` — `uit de bron`, `afgeleid`, `aangenomen` of `ontbreekt`
  (letterlijk hergebruikt uit `lozingsmodel.ZEKERHEDEN`, niet overgeschreven)
- `waarom` — waarom dit aandacht vraagt, met benoemde vindplaats (§5.4)
- `wat te doen` — de vraag die de inspecteur ter plaatse kan stellen
- `stap` — welke agent dit signaal vaststelde, met welke tool en in welke stap van de runlog.
  Dit is de procesherkomst uit §4.2: een inspecteur die op een signaal wordt aangesproken, kan
  terug tot de bewerking die het maakte en niet alleen tot de bronrij.

**Deel C — de inspectiebijlage.** Eén `.xlsx` met een blad per signaal en alle onderliggende rijen,
zodat het dossier offline mee kan. Een werkblad is wat er in de praktijk mee de deur uit gaat, en
het is ook de vorm die een signaal navraagbaar houdt: elke regel in het dossier is terug te vinden
als een rij met haar bron.

**Deel D — de runlog.** Wat er deze keer is gebeurd, in de volgorde waarin het gebeurde: per stap
de agent, de taak, de aangeroepen tools met hun argumenten, hoeveel rijen erin gingen en eruit
kwamen, de duur, en of een taalmodel is gebruikt. Plus welke agents uit stonden. Dit is geen
technisch logboek achteraf maar onderdeel van het product: het is het antwoord op "hoe weet je
dit?" dat verder gaat dan de bron.

**Wat het product uitdrukkelijk níet doet:** het geeft geen oordeel, geen prioritering tussen
vestigingen op risico, en geen voorspelling. Het rangschikt signalen binnen één dossier en
onderbouwt ze. Het oordeel is van het toezicht.

## 3. Brongegevens, geverifieerd 2026-11-13

Alle cijfers hieronder zijn deze dag zelf nageteld, niet uit documentatie overgenomen.

**Atlas voor een Schone Maas** (`connectors/smwk_atlas.py`, live, RD `inSR=28992`), straal 250 km
rond `(170000, 390000)`:

- **69 vestigingen, 782 voorschriften**
- velden per vestiging: `naam`, `plaats`, `locatie`, `locatiecode`, `kenmerk`, `besluitdatum`,
  `url`, `vestigingsnummer_kvk`, `voorschriften`
- velden per voorschrift: `parameter`, `waarde`, `eenheid`, `bemonstering`, `rd`
- leeg: `url` bij **8** vestigingen, `kenmerk` bij **6**, `besluitdatum` bij **5**
- `vestigingsnummer_kvk` is **wél** gevuld (bv. `000020643233`) — de koppelsleutel naar het
  handelsregister bestaat dus
- eenheden: 386 `milligram per liter`, 90 `dimensieloos`, 76 `kilogram per dag`,
  64 `kilogram per jaar`, 59 `microgram per liter`, 21 `kubieke meter per uur`,
  21 `kubieke meter per dag`, 18 `megajoule per seconde`
- **12 bemonsteringsregimes**, waarvan `Verzamelmonster gedurende 24 uur` (341) en `Steekmonster`
  (316) samen 84% dekken — plus **2 voorschriften die er helemaal geen melden**
- **164 gevallen** waarin binnen één vestiging dezelfde parameter meer dan één grenswaarde heeft
- **3 voorschriften zonder `waarde`**, waarvan één zonder `parameter` en één dat letterlijk
  "geen lozingseisen" heet

**Aquo-domeintabel Parameter** (`aquo_parameters.json`, 5760 namen): van de 782 voorschriften
koppelen **677 op een geldige Aquo-code** (56 verschillende stoffen); **105 voorschriften over 13
namen** koppelen niet.

**Waterkwaliteitsportaal 2025** (RWS, ruwe CSV, 384.259 meetwaarden): **492 verschillende
`ParameterCode`s** in het hele bestand; **471** op de 92 meetpunten in de verdichte set.

**De kernvondst van dit plan.** Van de 56 vergunde stoffen met een Aquo-code worden er **18 op geen
enkel van die 92 RWS-meetpunten gemeten** — samen **274 van de 677 voorschriften**:

```
pH 88 · Q 58 · minrlole 47 · WARMTE 26 · smetln6 16 · T 11 · Cl2 5 · NKj 4 · sVBCl 4
VERMGN 2 · smetlglt 2 · BZV5 2 · OVERSFQTE 2 · Bi 2 · VERVLWDE 2 · BZV1 1 · smetln5 1 · sMAK 1
```

**Let op de juiste lezing**, en dit moet op de pagina staan: dit betekent niet dat niemand ze meet.
Zuurgraad, debiet, temperatuur en minerale olie worden doorgaans bij het lozingspunt door de
lozer zelf bemeten, niet door RWS in het ontvangende water. Precies dát is het toezichtsignaal:
voor 274 voorschriften bestaat **geen onafhankelijke meting in het watersysteem** waartegen de
grenswaarde te houden valt. Wie wil controleren, is afhankelijk van de zelfrapportage van de lozer.

**En een gat dat het ontwerp begrenst.** De vergunning schrijft een bemonsteringsregime voor
(24-uursverzamelmonster, steekmonster, volumeproportioneel, …), maar de meting in het WKP meldt
niet hoe zij genomen is: `BemonsteringsapparaatCode` is leeg in **326.718** van de 384.259 rijen en
gevuld alleen bij biologie (fuik, schepnet, boomkor). Een toets van een meetwaarde aan een
grenswaarde is daarom **niet regime-zuiver**. Dat is geen reden om de toets weg te laten, maar wel
om hem als signaal met een voorbehoud te presenteren — en het is zelf signaal 9.

## 4. De architectuurkeuze

### 4.1 CrewAI of zelf bouwen — en wat ik heb nagegaan

De opdracht laat beide open. Ik heb het uitgeprobeerd in plaats van erover te speculeren, in een
wegwerp-venv zodat de projectomgeving ongemoeid bleef:

| nagegaan | uitkomst |
|---|---|
| installeert CrewAI op deze aarch64-Jetson, Python 3.10? | **ja** — `crewai 1.15.41`, importeert schoon |
| past het in de projectomgeving? | **nee** — CrewAI eist `pydantic<2.13,>=2.11.9`; dit project draait op `pydantic 2.13.4` onder FastAPI 0.136.1. De installatie zette pydantic terug naar 2.12.5 |
| praat het met het lokale model? | **ja** — `LLM(model="openai/qwen2.5-32b-instruct", base_url="http://localhost:8080/v1")` gaf op "welke rivier stroomt langs Venlo?" het antwoord `Maas` |
| telemetrie? | **standaard aan**, uit te zetten met één van `OTEL_SDK_DISABLED`, `CREWAI_DISABLE_TELEMETRY`, `CREWAI_DISABLE_TRACKING` (geverifieerd in `crewai_core/telemetry.py:354-359`) |
| kerndependencies | 32, waaronder `chromadb`, `lancedb`, `mcp`, `openai`, `instructor`, drie `opentelemetry`-pakketten |

Dat geeft een helder antwoord: **CrewAI werkt hier en kan volledig lokaal draaien** — op de Jetson,
tegen het model dat al op `:8080` staat, zonder enige externe aanroep. Maar het kan **niet in
dezelfde venv** als dit lab, en het brengt een telemetriekanaal mee dat expliciet dicht moet. Die
twee feiten bepalen de keuze hieronder.

### 4.2 De eerste reden voor configureerbare agents: transparantie

In dit lab gebeurt veel onder water. Een pagina toont een getal, en de bezoeker kan zien waar het
*gegeven* vandaan komt — daar zijn `herkomst`, `zekerheid`, `grondslag` en de live tests voor. Maar
wat de **bewerking** heeft gedaan, is alleen te zien door de code te lezen. Welke stappen zijn er
gezet, in welke volgorde, met welke bronnen, en waar zat een taalmodel in de keten? Dat staat nu in
Python, verspreid over modules, en is voor iedereen behalve de bouwer onzichtbaar.

Dat is precies het gat dat agents-met-configuratie dichten, en het is in het gesprek ook zo
benoemd: *"wat je dus met dat crew doet, is eigenlijk je maakt het transparant van wat al die
dingen doen."* Een `agents.yaml` die je kunt lezen zonder programmeur, waarin staat wie wat doet
met welk gereedschap op welke bron, is **procesherkomst** naast de gegevensherkomst die dit lab al
heeft. Voor een toezichtproduct is dat geen bijkomstigheid: een signaal dat een inspecteur meeneemt
naar een bedrijf moet navraagbaar zijn tot op de stap die het maakte.

Dat stelt vier eisen, want een configuratie die het proces alleen *beschrijft* is documentatie die
gaat verouderen — en dan is de transparantie nep.

**(a) De configuratie bestuurt, zij beschrijft niet.** Een agent krijgt van de runner uitsluitend
het gereedschap dat in zijn `tools` staat. Een aanroep van een tool die bestaat maar voor deze
agent niet is verklaard, faalt. Niet alleen een onbekende tool dus — ook een bekende die niet in
deze rol hoort.

**(b) Elk dossier draagt zijn eigen runlog.** Per stap: welke agent, welke taak, welke tools met
welke argumenten, hoeveel rijen erin en eruit, hoe lang het duurde, en of er een taalmodel aan te
pas kwam. Daarmee is "wat is hier gebeurd?" te beantwoorden zonder de code te openen, en is de
grens uit §4.4 per run aantoonbaar in plaats van in proza beloofd.

**(c) De pagina toont de pijplijn, gegenereerd uit dezelfde YAML die de runner heeft geladen.**
Geen getekende plaat die stil verouderd, net zoals `/modellen` zijn eigen gegevens rendert.

**(d) Aan en uit zetten is zichtbaar in de uitkomst.** Staat een agent uit, dan zegt het dossier
dat die sectie ontbreekt en waarom — in plaats van stil minder te leveren. Dat is het verschil
tussen configureerbaar en onopgemerkt kreupel.

### 4.3 En vervolgens: CrewAI-compatibele configuratie, eigen runner

De agents worden beschreven in twee YAML-bestanden met exact de vorm die CrewAI gebruikt
(`agents.yaml` met `role`/`goal`/`backstory`/`tools`, `tasks.yaml` met
`description`/`expected_output`/`agent`/`context`). Die bestanden worden uitgevoerd door een eigen
dunne runner van zo'n 150 regels in de projectvenv. Daarmee:

- lenen we een **bestaande, gedocumenteerde vorm** in plaats van een eigen configuratietaal te
  verzinnen. Wie de YAML leest, leest iets wat buiten dit lab ook betekenis heeft, en wij hoeven
  geen schema te ontwerpen en te verdedigen.
- vermijden we de pydantic-botsing en 32 extra dependencies in een omgeving die 919 tests groen
  houdt.
- houden we de eigenschap die dit lab onderscheidt: elke stap is te testen, elk getal is afgeleid,
  en een tussenresultaat is een Python-dict en geen vrije tekst.
- houden we de deur open: omdat de configuratie de vorm van een bekend framework heeft, is later
  overstappen een kwestie van een andere runner en niet van herschrijven.

**Let op wat hier de keuze bepaalt.** De eigen runner is te verdedigen omdat de eisen (a) tot (d)
erin af te dwingen zijn en met een test te bewaken. Zou een framework dat beter doen, dan is dat
een reden om te wisselen — de YAML blijft dan gelijk. De configuratie is het blijvende deel, de
runner het vervangbare.

### 4.4 De scherpste ontwerpregel: agents bepalen geen signalen

De verleiding bij een agentopstelling is om de agents het analysewerk te laten doen en voor het
rekenwerk zelf Python te laten schrijven. Dat werkt verrassend goed, en precies daar hoort voor
toezicht een grens te liggen. Een signaal dat
een taalmodel heeft "gezien" is niet navolgbaar: hij kan de volgende keer anders uitvallen, en een
toezichthouder kan er ter plaatse niet op terugvallen. Daarom:

- **de tien signaalregels zijn gewone Python-functies** in `usecases/toezicht/signalen.py`, zonder
  LLM, elk met een test die hem tegen de echte bron narekent;
- **de agents doen het werk eromheen**: het dossier samenstellen, uitleggen, vertalen naar de vraag
  van de gebruiker, een rapport opmaken, een vervolgvraag beantwoorden;
- **geen agent genereert code die wordt uitgevoerd.** Rekenwerk gebeurt in vastgelegde, geteste
  functies die als tool worden aangeboden. Dat is een bewuste beperking ten opzichte van wat
  agentframeworks aanbieden, en zij hoort met de reden erbij op de pagina.

Dat maakt het product reproduceerbaar: twee keer hetzelfde dossier opvragen geeft dezelfde
signalen, en alleen de formulering kan verschillen.

### 4.5 Wat de agentlaag toevoegt — en waar niet

Een eerlijke vraag bij dit plan: dit lab kan de tien signalen ook in één module berekenen en op een
pagina zetten, zoals het `/kmg` en `/maaskaart` heeft gedaan. Wat voegt een agentopstelling dan toe?
Het antwoord is per onderdeel verschillend, en voor één onderdeel is het "niets".

**Niets voor het rekenwerk.** De signalen zijn tien functies. Een agent eromheen maakt ze niet
beter, alleen langzamer. Dat is geen bezwaar tegen dit plan maar een grens erin: zie §4.4.

**Wel voor de ingang.** Een pagina stelt de vragen die de bouwer heeft voorzien. Een
toezichthouder komt met een vraag over één vestiging, en daarna met een vervolgvraag die niemand
in een filter heeft gestopt — "en wat ging er bij die andere locatie van dezelfde houder mis?".
Dat is wat de vraag- en uitlegagent oplossen, en wat een statische pagina principieel niet kan.

**Wel voor het samenstellen.** Een dossier is per vestiging anders: welke signalen vuren, welke
uitleg nodig is, welke bronnen erbij moeten. Dat is orkestratie, en dat is precies waar een
agentopstelling voor bedoeld is.

**Wel, en dat is de belangrijkste, voor de navraagbaarheid van het proces.** Zie §4.2. De tien
functies op een pagina zijn net zo ondoorzichtig als de rest van dit lab: je ziet de uitkomst en
de bron, niet de bewerking. De agentlaag dwingt die bewerking naar een leesbaar bestand en een
runlog. Dat is hier niet de prijs van de opzet — het is de opbrengst.

**En één onverwachte opbrengst om op te letten:** deze opzet maakt het goedkoop om een signaalregel
toe te voegen. Een regel is een functie plus een test plus een regel YAML. Als dat inderdaad zo
uitpakt, is de echte winst niet dit dossier maar het tempo waarin de volgende tien signalen erbij
komen. Of dat klopt, is na taak 6 te zien en hoort in de evaluatie.

## 5. De agents

Zes agents, alle zes geconfigureerd in YAML en los aan of uit te zetten. Elke agent doet één ding
en zegt in zijn configuratie met welk gereedschap hij dat doet.

### 5.1 `vergunninglezer`
Haalt het register live uit de Atlas en dataficeert elk voorschrift volgens het bestaande
`kmg/lozingsmodel.py`, dat al per veld een zekerheid meevoert. Tools:
`atlas.vergunningen_bij_punt`, `lozingsmodel.dataficeer`, `aquo.zoek_code`. **Geen PDF-stap
nodig**, en dat is voor deze casus een pluspunt dat benoemd mag worden: de Atlas publiceert de
voorschriften al als velden met parameter, waarde, eenheid en bemonstering. Waar een vergunning
alleen als pdf bestaat, begint een agentopstelling met een extractiestap die zelf fouten
introduceert; hier begint zij met gegevens.

### 5.2 `signaalsteller`
Draait de tien regels uit §6 over één vestiging en levert de gerangschikte lijst met bewijs.
Deterministisch; de "agent" is hier een orkestratiestap zonder LLM. Dat hij in de configuratie
tóch een agent is, is opzettelijk en volgt uit eis (a) van §4.2: wie de YAML leest, ziet de hele
keten in één overzicht, inclusief de stappen waar géén taalmodel aan te pas komt. Zijn
configuratieregel draagt daarom geen `llm`-sleutel, en een test dwingt af dat die er niet komt.

### 5.3 `dossiersteller`
Stelt deel A, B en C samen en schrijft de `.xlsx`. Tools: `dossier.dossier`, `rapport.schrijf`.

### 5.4 `uitlegger` — "waarom is dit erg?"
De agent uit het gesprek. Beantwoordt per signaal waarom het aandacht vraagt, **uitsluitend** uit
een afgebakende bronnenset via de bestaande RAG-infrastructuur (bge-m3 op `:8082`, de
`VectorStore` die `/chatbot` al gebruikt):

- de Aquo-domeintabel, inclusief de status van een code en het veld `Vervangen door`
- de KRW-normen uit `krw_normen.json` plus `doelen.py`, met het onderscheid doel-per-waterlichaam
  versus chemische norm dat die module al maakt
- de begrippen uit de Stelselcatalogus Omgevingswet via `connectors/stelselcatalogus.py`, met
  juridische vindplaats — dus "waarom is zwevende stof hier relevant" komt met een verwijzing naar
  de regeling, niet uit het model zelf
- de proclaimerteksten van `/kmg`, zodat voorbehouden consistent zijn met de rest van het lab

Zonder treffer in die set zegt de agent dat hij het niet weet. Dat is de bestaande
no-hallucination-regel van `/chatbot`, hier verplicht.

### 5.5 `vraagsteller` — de bevraagbare laag
Zet een vraag in natuurlijke taal om in een **SPARQL-query** op de triple-store van §7, langs het
patroon dat `usecases/datavraag/nl2sparql.py` al gebruikt: grounding meegeven, query genereren,
valideren, uitvoeren, antwoord samenvatten met de rijen erbij. De validator is **strenger** dan
`afval/chat.py::valideer_sql`, en op één punt bewust anders: alleen `SELECT` en `ASK`, geen
`INSERT`/`DELETE`/`LOAD`/`DROP`, en een **ontbrekende `LIMIT` wordt geweigerd in plaats van stil
toegevoegd**. Een te grote `LIMIT` wordt wél teruggebracht.

Dat onderscheid is het punt, en deze paragraaf had het eerst fout ("analoog aan `afval/chat.py`",
dat stil een `LIMIT` aanvult). Op een pagina waarvan de hele premisse navraagbaarheid is, geeft een
stil toegevoegde `LIMIT` een afgekapt antwoord dat de lezer niet heeft gevraagd en niet kan zien.
Weigeren maakt de fout van het model zichtbaar; aftoppen begrenst alleen een kostenpost en verbergt
niets. De eerste helft van het gedrag van `afval/chat.py` is hier dus verkeerd en de tweede goed.

Dit is de "deterministisch gemaakt"-gedachte uit het gesprek: het model schrijft de vraag, de store
geeft het antwoord.

### 5.6 `terugkoppelaar`
Slaat per antwoord een beoordeling op (bruikbaar / niet bruikbaar / signaal was juist / signaal was
onjuist) met de vestiging, het signaal en de versie van de regel erbij. **Geen online leren**: de
terugkoppeling is data, geen automatische aanpassing. Wat zij oplevert is een rangschikking van de
tien regels naar "bleek dit in de praktijk te kloppen?".

Dat is de cirkel die het product pas af maakt, en hij is met open data **niet te sluiten**: of een
signaal klopte, weet alleen wie is gaan kijken. Dit plan bouwt de plek waar die uitkomst
ingeplugd wordt en laat op de pagina zien dat zij leeg is. Dat lege vak is zelf het nuttigste
argument over welke data erbij moet.

## 6. De signaalcatalogus

Tien regels. Elke regel is een functie `(vestiging, context) -> list[Signaal]`, deterministisch,
met een eigen test. De kolom "telling nu" is wat de regel vandaag over het hele register oplevert —
geverifieerd waar aangegeven, en anders in taak 3 vast te stellen.

| # | signaal | de regel | zwaarte | telling nu |
|---|---|---|---|---|
| 1 | **geen onafhankelijke meting** | het voorschrift noemt een stof die op geen RWS-meetpunt in de set voorkomt | hoog bij een stof met een KRW-norm, anders midden | **274 voorschriften, 18 stoffen** (geverifieerd) |
| 2 | **grenswaarde op een ingetrokken code** | de Aquo-code van de parameter is `Vervallen` | hoog — er is geen geldige referentie om tegen te toetsen | **90 voorschriften**, waarvan 83 "Zwevende stof" (eerder geverifieerd via `/kennisgraaf`) |
| 3 | **parameter niet in de referentie** | de naam koppelt niet aan Aquo | midden | **105 voorschriften over 13 namen** (geverifieerd) |
| 4 | **welke grenswaarde geldt?** | dezelfde parameter heeft binnen één vestiging meer dan één grenswaarde | hoog als ze meer dan een factor 2 verschillen | **164 gevallen** (geverifieerd) |
| 5 | **vracht niet te bepalen** | concentratievoorschrift zonder debietvoorschrift, dus niet naar een vracht om te rekenen | midden | af te leiden uit `atlas_register`, dat dit al in drie lagen doet |
| 6 | **meting boven de norm, lozer bovenstrooms** | op een benedenstrooms meetpunt is de KRW-norm overschreden en deze vestiging ligt bovenstrooms volgens `toerekening.STROOMVOLGORDE` | hoog | te berekenen; `/kmg` levert de bouwstenen |
| 7 | **gemeten stof die in geen vergunning staat** | een stof die de norm nadert of overschrijdt komt in het hele register niet voor | hoog | PFOA is het bekende geval |
| 8 | **vergunning niet te vinden** | `url`, `kenmerk` of `besluitdatum` ontbreekt | midden; hoog als alle drie ontbreken | **8 / 6 / 5 vestigingen** (geverifieerd) |
| 9 | **toets niet regime-zuiver** | het voorschrift schrijft een bemonsteringsregime voor dat de meting niet meldt | laag, maar altijd als voorbehoud bij signaal 6 | **alle** vergelijkingen; de meting meldt het regime nooit (geverifieerd) |
| 10 | **geen geldigheidsduur** | geen enkel voorschrift draagt een geldigheidsperiode | laag als losstaand signaal, maar het staat één keer per dossier | **alle 782** (eerder geverifieerd via `lozingsmodel`) |

**Zwaarte wordt afgeleid, niet getypt.** `signalen.zwaarte(regel, omvang, norm_aanwezig)` is één
functie met één test per uitkomst. Dat voorkomt wat in dit lab eerder drie keer misging: een
hardgecodeerde bewering die uit de pas loopt met de data eronder.

## 7. De bevraagbare laag

Het gesprek eindigt op de architectuurvraag: kennisgraaf, RAG en linked data als basislaag. Dit lab
heeft de drie bouwstenen al liggen — ze zijn alleen nog niet op deze data gericht:

- `ld/store.py` — rdflib-triple-store, Turtle op NVMe, lokale SPARQL
- `usecases/datavraag/nl2sparql.py` — NL → SPARQL met grounding en een geldigheidscontrole
- `usecases/stoffengraaf.py` — de stoffengraaf op Aquo, met kwaliteitscontrole
- de RAG-pijplijn met bge-m3 die `/chatbot` gebruikt

**Wat erbij komt** is één conversie: `toezicht/graaf.py` zet het register, de metingen, de normen en
de Aquo-codes om in tripels volgens het bestaande lozingsmodel, met herkomst en zekerheid als
expliciete eigenschappen op de uitspraak zelf. Dat laatste is het punt dat een gewone database niet
geeft: je kunt dan vragen *"welke grenswaarden zijn aangenomen in plaats van uit de bron gelezen?"*
— en dat is een toezichtvraag.

**Eén ontwerpbesluit expliciet.** De graaf is **lokaal en afgeleid**, geen federatieve laag. Het
gesprek stelt terecht de vraag waar je een linked-data-laag bouwt als de data niet bij jou staat.
Dat is een echte open vraag en dit plan beslist hem niet; het bouwt de lokale variant, en benoemt
op de pagina dat federatief een ander ontwerp vergt (§10).

## 8. Beveiliging en plaatsing — wat dit lab wel en niet aantoont

Deze use-case staat of valt bij een toezichthouder niet op de techniek maar op de omgeving waarin
zij draait. Daarom hoort bij een lab-opzet expliciet wat zij wél en níet aantoont. Dit plan draait
volledig op open data, dus de vraag "mag deze data hier staan?" speelt hier niet — en precies
daardoor kan het de rest van de keten wel aantoonbaar maken:

**Wel aantoonbaar, op open data:**
- de hele keten draait **lokaal**: Qwen2.5-32B op een Jetson AGX Orin, geen enkele externe
  LLM-aanroep. Geverifieerd dat ook CrewAI zelf dat kan (§4.1).
- de telemetrie van een agentframework is te identificeren en uit te zetten, met de vlag erbij.
- het rekenwerk is deterministisch en dus auditeerbaar: een signaal is te herleiden tot een regel
  en een bronrij.

**Niet aantoonbaar hier, en dat moet erbij staan:**
- authenticatie, autorisatie en logging op gebruikersniveau. Dit lab heeft geen eHerkenning en
  publiceert op een persoonlijke Cloudflare-tunnel. De `/toezicht`-pagina draait daarom **alleen op
  open data** en krijgt een banner die dat zegt.
- bewaartermijnen, dataminimalisatie en verwerkersafspraken.
- de capaciteitsvraag. Wat wij meten op deze Jetson zegt iets over haalbaarheid, niet over een
  productieomgeving.

Dat onderscheid is zelf een resultaat: het scheidt wat in een lab op te lossen is van wat een
omgeving met toegangsbeveiliging, mandaat en bewaartermijnen vergt. Een agentopstelling die op open
data werkt, is daarmee niet "bijna productie" — zij is het bewijs dat de resterende vragen geen
technische vragen zijn.

## 9. File Structure

```
src/leefomgevinglab/usecases/toezicht/
  __init__.py
  signalen.py      de tien regels + zwaarte(); geen LLM, geen netwerk
  dossier.py       deel A/B/C samenstellen uit signalen + register
  graaf.py         register/metingen/normen/Aquo -> tripels met herkomst
  vraag.py         NL -> SPARQL, validator, uitvoeren, samenvatten
  uitleg.py        RAG over de afgebakende bronnenset
  terugkoppeling.py  beoordelingen opslaan en rangschikken
  rapport.py       de .xlsx-bijlage
  runner.py        de dunne agentrunner die agents.yaml/tasks.yaml uitvoert
  runlog.py        de procesherkomst: per stap agent, taak, tools, rijen in/uit, duur, llm ja/nee
  pijplijn.py      leest agents.yaml/tasks.yaml en levert de keten als gegeven voor de pagina
  config/agents.yaml   CrewAI-compatibel
  config/tasks.yaml    CrewAI-compatibel
src/leefomgevinglab/static/toezicht.html
scripts/21_crew_adapter.py        dezelfde YAML in een eigen venv via CrewAI
scripts/22_bouw_toezichtgraaf.py  de triple-store bouwen
tests/test_toezicht_signalen.py   per regel, met geïnjecteerde bronnen
tests/test_toezicht_dossier.py    taalregels, zwaarte-afleiding, volledigheid
tests/test_toezicht_vraag.py      de SPARQL-validator
tests/test_toezicht_runlog.py     procesherkomst: volledig, en geen onverklaarde toolaanroep
tests/test_toezicht_live.py       de tellingen tegen de echte Atlas; skipt zonder DSO_API_KEY
```

---

## Tasks

### Task 1: De signaalregels, zonder bron en zonder LLM

**Files:**
- Create: `src/leefomgevinglab/usecases/toezicht/__init__.py`
- Create: `src/leefomgevinglab/usecases/toezicht/signalen.py`
- Test: `tests/test_toezicht_signalen.py`

**Interfaces:**
- Produces: `REGELS: list[Regel]` waarin elke `Regel` een `id`, `kop`, `uitleg_sleutel` en een
  `functie(vestiging: dict, context: dict) -> list[dict]` heeft; `zwaarte(regel_id, omvang, norm_aanwezig) -> str`;
  `signalen(vestiging, context) -> list[dict]` gerangschikt op zwaarte en dan omvang.
- Consumes: niets. Alles komt via `vestiging` en `context` binnen, zodat de tests geen netwerk nodig hebben.

- [ ] **Stap 1: Schrijf de falende test voor regel 4 (welke grenswaarde geldt?)**

```python
def test_dezelfde_parameter_met_twee_grenswaarden_geeft_een_signaal():
    v = {"naam": "Testlozer", "voorschriften": [
        {"parameter": "Zink", "waarde": 0.5, "eenheid": "milligram per liter"},
        {"parameter": "Zink", "waarde": 2.0, "eenheid": "milligram per liter"},
        {"parameter": "Lood", "waarde": 0.1, "eenheid": "milligram per liter"}]}
    uit = signalen.regel_meerdere_grenswaarden(v, {})
    assert len(uit) == 1
    s = uit[0]
    assert s["signaal"] == "welke grenswaarde geldt?"
    assert s["zwaarte"] == "hoog", "factor 4 verschil is meer dan 2"
    assert {b["waarde"] for b in s["bewijs"]} == {0.5, 2.0}
    assert "Lood" not in str(s["bewijs"])
```

- [ ] **Stap 2: Draai de test en zie hem falen**

Run: `.venv/bin/python -m pytest tests/test_toezicht_signalen.py -v`
Expected: FAIL met `AttributeError: module ... has no attribute 'regel_meerdere_grenswaarden'`

- [ ] **Stap 3: Implementeer `zwaarte()` en regel 4**

```python
# Per regel: de drempel waarboven het signaal zwaar weegt, en wat `omvang` daar betekent.
# Eén tabel in plaats van zes if-takken, zodat de drempel te zien is zonder de code te lezen.
DREMPELS = {
    "geen_onafhankelijke_meting": (1, "aantal voorschriften zonder meting"),
    "vervallen_code":             (1, "aantal voorschriften op een ingetrokken code"),
    "niet_in_referentie":         (3, "aantal voorschriften met een onbekende naam"),
    "meerdere_grenswaarden":      (2, "verhouding hoogste / laagste grenswaarde"),
    "vracht_onbepaald":           (5, "aantal voorschriften zonder debietvoorschrift"),
    "norm_overschreden_bovenstrooms": (1, "aantal overschreden stoffen benedenstrooms"),
    "stof_buiten_register":       (1, "aantal gemeten stoffen zonder enig voorschrift"),
    "vergunning_niet_te_vinden":  (3, "aantal ontbrekende identificerende velden"),
    "niet_regime_zuiver":         (99, "altijd laag; dit is een voorbehoud, geen bevinding"),
    "geen_geldigheidsduur":       (99, "altijd laag; geldt voor het hele register"),
}


def zwaarte(regel_id: str, omvang: float, norm_aanwezig: bool = False) -> str:
    """Afgeleid, nooit getypt.

    Wat `omvang` betekent verschilt per regel en staat in `DREMPELS` -- bij regel 4 is het de
    verhouding tussen de hoogste en de laagste grenswaarde, bij regel 1 een aantal
    voorschriften. Een onbekende regel werpt een KeyError in plaats van stil `laag` te geven:
    een nieuwe regel zonder drempel is een vergeten keuze, niet een lichte bevinding.
    """
    drempel, _ = DREMPELS[regel_id]
    if omvang >= drempel:
        return "hoog" if norm_aanwezig or drempel < 99 else "midden"
    return "midden" if omvang > 0 else "laag"
```

Let op de laatste regel van die functie: hij geeft `hoog` zodra de drempel gehaald is én er een
KRW-norm voor de stof bestaat. Zonder norm valt een gehaalde drempel terug op `midden`, want dan
is er niets om de grenswaarde tegen te houden. Dat onderscheid is de reden dat `norm_aanwezig` een
apart argument is en niet uit de omvang wordt afgeleid.

- [ ] **Stap 4: Draai de test en zie hem slagen**
- [ ] **Stap 5: Herhaal stap 1-4 voor de regels 2, 3, 5, 8, 9 en 10** — deze hebben geen
      meetdata nodig en zijn met één `vestiging`-dict te testen.
- [ ] **Stap 6: Commit**

```bash
git add src/leefomgevinglab/usecases/toezicht/ tests/test_toezicht_signalen.py
git commit -m "feat(toezicht): zeven signaalregels op de vergunning zelf"
```

### Task 2: De regels die meetdata en stroomrichting nodig hebben

**Files:**
- Modify: `src/leefomgevinglab/usecases/toezicht/signalen.py`
- Test: `tests/test_toezicht_signalen.py`

**Interfaces:**
- Consumes: `kmg.metingen.laad`, `kmg.doelen.toets`, `kmg.toerekening.is_bovenstrooms`,
  `kmg.stroomgebied.in_district` — alle vier bestaan al en worden als `context` geïnjecteerd.
- Produces: `regel_geen_onafhankelijke_meting`, `regel_norm_overschreden_bovenstrooms`,
  `regel_stof_buiten_register`.

- [ ] **Stap 1: Test voor regel 1, met een context van twee gemeten codes**

```python
def test_vergunde_stof_die_nergens_gemeten_wordt_geeft_een_signaal():
    v = {"voorschriften": [{"parameter": "Zuurgraad", "waarde": 7.0, "eenheid": "dimensieloos",
                            "aquo": "pH"},
                           {"parameter": "Zink", "waarde": 0.5, "eenheid": "milligram per liter",
                            "aquo": "Zn"}]}
    uit = signalen.regel_geen_onafhankelijke_meting(v, {"gemeten_codes": {"Zn", "Ntot"}})
    assert [s["bewijs"][0]["aquo"] for s in uit] == ["pH"]
    assert "geen onafhankelijke meting" in uit[0]["signaal"]
```

- [ ] **Stap 2: Draai de test, zie hem falen**
- [ ] **Stap 3: Implementeer de drie regels**
- [ ] **Stap 4: Test dat regel 6 nooit "overtreding" of "veroorzaakt door" zegt**

```python
def test_een_signaal_is_nooit_een_vaststelling():
    """Dezelfde taalregel als /kmg, hier op de gegenereerde signaaltekst."""
    for s in signalen.signalen(VESTIGING_MET_ALLES, CONTEXT_MET_ALLES):
        tekst = (s["signaal"] + s.get("waarom", "") + s.get("wat_te_doen", "")).lower()
        for verboden in ("overtreding", "veroorzaakt door", "in strijd met"):
            assert verboden not in tekst, f"{s['signaal']}: {verboden}"
```

- [ ] **Stap 5: Draai alle tests**
- [ ] **Stap 6: Commit**

### Task 3: De live controle — de tellingen tegen de echte Atlas

**Files:**
- Create: `tests/test_toezicht_live.py`

**Interfaces:**
- Consumes: `SmwkAtlasConnector`, `lozingsmodel.laad_parameters`, de ruwe WKP-CSV.

Dit is de taak die in dit lab het meeste oplevert, dus hij komt vóór de pagina. Hij legt de
getallen van §3 vast tegen de bron, zodat een verschuiving in de Atlas luid faalt in plaats van
stil de pagina te veranderen.

- [ ] **Stap 1: Schrijf de test voor de vier gevraagde tellingen**

```python
pytestmark = pytest.mark.skipif(not os.environ.get("DSO_API_KEY"),
                                reason="live-tests uit (DSO_API_KEY niet gezet)")

def test_het_register_heeft_de_omvang_die_de_pagina_noemt(tmp_path):
    c = SmwkAtlasConnector(cache_dir=str(tmp_path))
    alles = c.vergunningen_bij_punt(170000.0, 390000.0, straal_m=250000)
    assert len(alles) == 69, "aantal vestigingen gewijzigd -- pagina en plan bijwerken"
    assert sum(len(v["voorschriften"]) for v in alles) == 782
    leeg = {f: sum(1 for v in alles if not v.get(f)) for f in ("url", "kenmerk", "besluitdatum")}
    assert leeg == {"url": 8, "kenmerk": 6, "besluitdatum": 5}
```

- [ ] **Stap 2: Draai met `DSO_API_KEY` gezet, zie hem slagen**
- [ ] **Stap 3: Voeg de test voor signaal 1 toe (18 stoffen, 274 voorschriften)**
- [ ] **Stap 4: Voeg de test toe dat de meting haar bemonsteringsregime níet meldt** — zodra het
      WKP dat wél gaat leveren, hoort signaal 9 van de pagina af
- [ ] **Stap 5: Commit**

### Task 4: Het dossier en de inspectiebijlage

**Files:**
- Create: `src/leefomgevinglab/usecases/toezicht/dossier.py`
- Create: `src/leefomgevinglab/usecases/toezicht/rapport.py`
- Test: `tests/test_toezicht_dossier.py`

De zekerheidswoorden komen uit `kmg/lozingsmodel.ZEKERHEDEN` — `"uit de bron"`, `"afgeleid"`,
`"aangenomen"`, `"ontbreekt"` — en worden daar geïmporteerd in plaats van opnieuw opgeschreven.
Deze paragraaf zei eerder `"ontbrekend"`; dat was een tweede woord voor hetzelfde begrip in een
belendende module, en dat is precies de drift waartegen dit dossier elders al een test heeft.

**Interfaces:**
- Consumes: `signalen.signalen`
- Produces: `dossier(vestiging, context) -> dict` met `kaart`, `signalen`, `telling`, `voorbehouden`;
  `rapport.schrijf(dossier, pad) -> str`

- [ ] **Stap 1: Test dat deel A ontbrekende velden toont in plaats van weglaat**

```python
def test_een_ontbrekend_veld_staat_in_de_kaart_als_ontbrekend():
    d = dossier.dossier({"naam": "X", "kenmerk": None, "url": None, "voorschriften": []}, {})
    assert d["kaart"]["kenmerk"] == {"waarde": None, "zekerheid": "ontbreekt"}
    assert "kenmerk" in d["kaart"], "weglaten verbergt juist wat voor toezicht het signaal is"
```

- [ ] **Stap 2: Falen, implementeren, slagen**
- [ ] **Stap 3: Test dat het rapport een blad per signaal heeft en de bronrijen meeneemt**
- [ ] **Stap 4: Commit**

### Task 5: De graaf en de bevraagbare laag

**Files:**
- Create: `src/leefomgevinglab/usecases/toezicht/graaf.py`
- Create: `src/leefomgevinglab/usecases/toezicht/vraag.py`
- Create: `scripts/22_bouw_toezichtgraaf.py`
- Test: `tests/test_toezicht_vraag.py`

**Interfaces:**
- Consumes: `ld.store.save_graph/load_graph/run_sparql`, `datavraag.nl2sparql.genereer_sparql`
- Produces: `graaf.bouw(register, metingen, normen, aquo) -> rdflib.Graph`;
  `vraag.valideer_sparql(q) -> str` (werpt `OngeldigeSparql`); `vraag.stel(vraag, graaf, llm) -> dict`

- [ ] **Stap 1: Test de validator vóór alles** — dit is de bewaking, dus hij komt eerst

```python
@pytest.mark.parametrize("q", [
    "INSERT DATA { <a> <b> <c> }",
    "DELETE WHERE { ?s ?p ?o }",
    "LOAD <http://elders/data.ttl>",
    "DROP GRAPH <g>",
    "SELECT * WHERE { ?s ?p ?o }",            # geen LIMIT
])
def test_de_validator_weigert_alles_wat_niet_leest(q):
    with pytest.raises(vraag.OngeldigeSparql):
        vraag.valideer_sparql(q)

def test_een_leesquery_met_limiet_mag():
    assert "LIMIT" in vraag.valideer_sparql("SELECT ?s WHERE { ?s ?p ?o } LIMIT 10")
```

- [ ] **Stap 2: Falen, implementeren, slagen**
- [ ] **Stap 3: Test dat de graaf herkomst op de uitspraak zet**

```python
def test_een_aangenomen_grenswaarde_is_als_aanname_te_bevragen():
    g = graaf.bouw(REGISTER_FIXTURE, {}, {}, AQUO_FIXTURE)
    rijen = store.run_sparql(g, """
        PREFIX t: <https://leefomgevinglab.felixisfelix.com/toezicht#>
        SELECT ?v WHERE { ?v t:zekerheid "aangenomen" } LIMIT 50""")
    assert rijen, "zonder dit is de graaf niet meer dan een database"
```

- [ ] **Stap 4: Commit**

### Task 6: De agentrunner en de CrewAI-compatibele configuratie

**Files:**
- Create: `src/leefomgevinglab/usecases/toezicht/runner.py`
- Create: `src/leefomgevinglab/usecases/toezicht/config/agents.yaml`
- Create: `src/leefomgevinglab/usecases/toezicht/config/tasks.yaml`
- Test: `tests/test_toezicht_runner.py`

**Interfaces:**
- Produces: `runner.laad(agents_pad, tasks_pad) -> Crew`; `Crew.draai(invoer, llm=None) -> dict`
- Consumes: de modules uit taak 1-5 als tools, via een registry `TOOLS: dict[str, Callable]`

- [ ] **Stap 1: Test dat een onbekende tool in de YAML luid faalt**

```python
def test_een_agent_die_een_onbekende_tool_vraagt_faalt_bij_het_laden():
    with pytest.raises(runner.OnbekendeTool) as f:
        runner.laad_uit_dict({"a": {"role": "x", "goal": "y", "tools": ["bestaat_niet"]}}, {})
    assert "bestaat_niet" in str(f.value)
```

Waarom deze eerst: een agent die stil zonder tool doorgaat, geeft een plausibel ogend antwoord
zonder bron. Dat is in deze use-case de ergste fout die er is.

- [ ] **Stap 2: Test dat een agent een bestaande tool die hij niet heeft verklaard, niet mag
      aanroepen** — eis (a) van §4.2, en de scherpere helft ervan

```python
def test_een_agent_mag_alleen_zijn_eigen_verklaarde_gereedschap_gebruiken():
    """Een onbekende tool weigeren is niet genoeg. Zou een agent een bestaande tool mogen
    aanroepen die niet in zijn `tools` staat, dan beschrijft de YAML het proces in plaats van
    het te besturen -- en dan is de transparantie die zij belooft niet waar."""
    crew = runner.laad_uit_dict(
        {"leesagent": {"role": "x", "goal": "y", "tools": ["atlas_vergunningen"]}},
        {"t1": {"description": "d", "expected_output": "e", "agent": "leesagent"}})
    with pytest.raises(runner.NietVerklaardeTool) as f:
        crew.tools_voor("leesagent")["signalen_stellen"]
    assert "signalen_stellen" in str(f.value)
    assert "leesagent" in str(f.value)
```

- [ ] **Stap 3: Test dat de runner zonder LLM werkt voor de deterministische agents**
- [ ] **Stap 4: Implementeer de runner (sequentieel, `context` doorgeven, per stap naar de runlog)**
- [ ] **Stap 5: Test dat de YAML de CrewAI-velden gebruikt** — `role`, `goal`, `backstory`,
      `tools`, en bij taken `description`, `expected_output`, `agent`, `context`
- [ ] **Stap 6: Commit**

### Task 6b: De runlog — procesherkomst als onderdeel van het product

**Files:**
- Create: `src/leefomgevinglab/usecases/toezicht/runlog.py`
- Test: `tests/test_toezicht_runlog.py`

**Interfaces:**
- Produces: `Runlog.stap(agent, taak, tool, rijen_in, rijen_uit, llm) -> None`;
  `Runlog.als_gegeven() -> list[dict]`; `Runlog.telling() -> dict`
- Consumes: wordt door `runner.Crew.draai` gevuld en door `dossier.dossier` meegegeven als deel D

- [ ] **Stap 1: Test dat elke toolaanroep in de runlog staat**

```python
def test_elke_toolaanroep_komt_in_de_runlog():
    """Een stap die niet gelogd wordt, is een stap die onder water gebeurt."""
    crew, log = runner.laad(AGENTS, TASKS), runlog.Runlog()
    crew.draai({"vestiging": VESTIGING_FIXTURE}, runlog=log)
    aangeroepen = {s["tool"] for s in log.als_gegeven() if s["tool"]}
    assert aangeroepen == crew.verwachte_tools(), \
        "de runlog en de configuratie lopen uiteen"
```

- [ ] **Stap 2: Test dat de runlog de LLM-grens van §4.4 aantoonbaar maakt**

```python
def test_tijdens_de_signaalbepaling_komt_er_geen_taalmodel_aan_te_pas():
    """De belofte uit §4.4, per run bewezen in plaats van in proza beloofd.

    Dit is de test die de hele transparantieclaim draagt: wie hem weghaalt, houdt een
    configuratie over die iets zegt wat niemand meer narekent.
    """
    log = runlog.Runlog()
    runner.laad(AGENTS, TASKS).draai({"vestiging": VESTIGING_FIXTURE}, runlog=log)
    for s in log.als_gegeven():
        if s["agent"] in ("vergunninglezer", "signaalsteller"):
            assert s["llm"] is False, f"{s['agent']} gebruikte een taalmodel in stap {s['nr']}"
```

- [ ] **Stap 3: Test dat een uitgezette agent zichtbaar is in plaats van stil weg te vallen**
      — eis (d) van §4.2

```python
def test_een_uitgezette_agent_staat_als_uitgezet_in_het_dossier():
    d = dossier.dossier(VESTIGING_FIXTURE, CONTEXT, uit={"uitlegger"})
    assert d["runlog"]["uitgezet"] == ["uitlegger"]
    assert all(not s.get("waarom") for s in d["signalen"])
    assert "uitlegger stond uit" in d["voorbehouden"][0]
```

- [ ] **Stap 4: Falen, implementeren, slagen**
- [ ] **Stap 5: Commit**

### Task 7: De uitlegger en de terugkoppeling

**Files:**
- Create: `src/leefomgevinglab/usecases/toezicht/uitleg.py`
- Create: `src/leefomgevinglab/usecases/toezicht/terugkoppeling.py`
- Test: `tests/test_toezicht_uitleg.py`

- [ ] **Stap 1: Test dat de uitlegger zwijgt zonder treffer**

```python
def test_zonder_bron_zegt_de_uitlegger_dat_hij_het_niet_weet():
    uit = uitleg.waarom("onbekend signaal", _zoek=lambda q, n: [])
    assert uit["beschikbaar"] is False
    assert uit["vindplaatsen"] == []
    assert "geen" in uit["reden"].lower()
```

- [ ] **Stap 2: Test dat elke uitleg minstens één benoemde vindplaats draagt**
- [ ] **Stap 3: Implementeren**
- [ ] **Stap 4: Test dat de terugkoppeling de regelversie meeschrijft** — zonder dat is een
      beoordeling over een jaar niet te plaatsen
- [ ] **Stap 5: Commit**

### Task 8: De pagina en het eindpunt

**Files:**
- Create: `src/leefomgevinglab/static/toezicht.html`
- Modify: `src/leefomgevinglab/geluidsmeter/api.py`
- Modify: `src/leefomgevinglab/usecases/water_hub.py` (nieuw lid)
- Test: `tests/test_api_toezicht.py`

- [ ] **Stap 1: Test dat de pagina de open-data-banner draagt** — zonder die banner suggereert
      zij een bevoegdheid die dit lab niet heeft
- [ ] **Stap 2: Test dat de pagina de taalregel haalt op de echte HTML**
- [ ] **Stap 3: Test dat de pagina de pijplijn uit de YAML rendert en niet uit een tweede lijst**
      — eis (c) van §4.2

```python
def test_de_pijplijn_op_de_pagina_komt_uit_dezelfde_configuratie_als_de_runner():
    """Een getekende keten naast een draaiende keten gaat uiteenlopen; dan toont de pagina
    een proces dat niet meer bestaat. Daarom één bron voor beide."""
    uit_api = _client(monkeypatch).get("/api/toezicht/pijplijn").json()
    uit_runner = runner.laad(AGENTS_PAD, TASKS_PAD).als_gegeven()
    assert [a["naam"] for a in uit_api["agents"]] == [a["naam"] for a in uit_runner["agents"]]
    assert uit_api["bron"].endswith("agents.yaml")
```

- [ ] **Stap 4: Test dat de pagina per agent toont of er een taalmodel in zit** — dat is wat een
      lezer het eerst wil weten en wat in code onzichtbaar is
- [ ] **Stap 5: Route toevoegen, hub-lid toevoegen, pagina bouwen** — met de pijplijn en de
      runlog van het laatst opgevraagde dossier zichtbaar, niet weggestopt achter een knop
- [ ] **Stap 4: Draai de hele suite** — `919 passed` plus de nieuwe
- [ ] **Stap 5: Herstart en verifieer live én publiek, op inhoud en niet op statuscode**
- [ ] **Stap 6: Commit**

### Task 9 (optioneel, pas na taak 8): CrewAI als controle op de eigen runner

**Deze taak is geen onderdeel van het product.** Zij staat erin omdat de opdracht de keuze tussen
CrewAI en zelf bouwen openliet, en omdat één vraag na taak 6 blijft hangen: doet onze runner iets
eigenaardigs? Dezelfde YAML door een echt framework halen is de goedkoopste manier om dat te
weten. Waarom ná taak 8: eerst moet het product werken, anders vergelijk je twee onvoltooide dingen.
Levert zij niets op, dan wordt zij weggegooid en is dat ook een uitkomst.

**Files:**
- Create: `scripts/21_crew_controle.py`
- Create: `docs/toezicht-runner-vs-crewai.md`

- [ ] **Stap 1: Zet een eigen venv op met `crewai`, mét de telemetrie uit**

```bash
python3 -m venv /mnt/nvme/geluidsmeter/venvs/crew
/mnt/nvme/geluidsmeter/venvs/crew/bin/pip install 'crewai==1.15.41'
export OTEL_SDK_DISABLED=true CREWAI_DISABLE_TELEMETRY=true CREWAI_DISABLE_TRACKING=true
```

De versie wordt gepind: de pydantic-eis van CrewAI schuift op, en een vergelijking zonder
vastgelegde versie zegt over een half jaar niets.

- [ ] **Stap 2: Laad dezelfde `agents.yaml`/`tasks.yaml` in CrewAI tegen het model op `:8080`**
- [ ] **Stap 3: Draai één vestiging door beide en leg de verschillen vast** — niet welke "beter"
      is, maar of de deterministische signalen identiek zijn (dat moeten ze, en zo niet is dat een
      bug in onze runner) en waar de geformuleerde delen uiteenlopen
- [ ] **Stap 4: Commit**

---

## 10. Wat dit plan uitdrukkelijk niet doet

- **Geen agent die code genereert en uitvoert.** Zie §4.4. De reden staat op de pagina.
- **Geen federatieve graaf.** De graaf is lokaal en afgeleid. Waar je een linked-data-laag bouwt
  als de data niet bij jou staat, is een open vraag uit het gesprek die dit plan niet beslecht.
- **Geen bedrijfsgevoelige data.** Alleen de Atlas, het WKP, de KRW-normen en Aquo — alle vier
  openbaar. Wat authenticatie en bewaartermijnen betreft doet dit lab geen uitspraak (§8).
- **Geen online leren.** De terugkoppeling is data; de regels wijzigen alleen door een commit met
  een test.
- **Geen rangschikking tussen vestigingen.** Signalen worden binnen één dossier gerangschikt. Een
  risicoranking over 69 vestigingen is een handhavingsinstrument en vergt een mandaat.
- **Geen transparantie over het redeneren van het model.** Dit is de belangrijkste grens van de
  hele opzet en hij hoort op de pagina. De configuratie en de runlog maken de **bedrading**
  zichtbaar: welke stap, welke bron, welk gereedschap, met of zonder taalmodel. Zij maken niet
  zichtbaar *waarom* het model een bepaalde uitleg gaf. Voor de signalen is dat geen probleem — die
  komen uit geteste functies, niet uit een model. Voor de uitleg en de vraagfunctie is het dat wel,
  en de enige verdediging daar is de harde eis dat elk antwoord een benoemde vindplaats draagt en
  anders zwijgt (§5.4). Wie na deze opzet zegt "de agents zijn transparant", moet erbij zeggen
  waarover.

## 10a. Twee getallen in §3 waren fout, en hoe dat bleek

Taak 3 — de live controle, die in dit plan bewust vóór de pagina staat — weerlegde twee cijfers
die in §3 stonden. Beide waren van mij, niet van de bron:

- **"165 gevallen"** van meerdere grenswaarden was **164**. Mijn telling rekende een paar mee
  waarvan één van de twee waarden leeg was, en een ontbrekende waarde is geen concurrerende
  grenswaarde. De regel in `signalen.py` deed het al goed (zij filtert lege waarden weg voor zij
  telt), dus hier was de plantekst fout en de code juist — precies omgekeerd aan wat je verwacht.
- **"13 bemonsteringsregimes"** waren **12**. De dertiende sleutel was de lege waarde: er zijn
  2 voorschriften die geen enkel bemonsteringsregime melden.

Daarbij viel nog iets op dat §3 helemaal niet noemde: **3 voorschriften hebben geen `waarde`**,
één daarvan heeft zelfs geen `parameter`, en één heet letterlijk "geen lozingseisen". Een
grenswaarde zonder waarde is het scherpste geval van "niet te controleren" dat dit register kent.
Dat is géén elfde signaal in deze bouw — de tien staan vast — maar het staat hier zodat het niet
verdwijnt.

De les is de les van het hele plan, nu op het plan zelf toegepast: de getallen die ik met de hand
uit een bron haalde, hielden geen stand tegen een test die ze opnieuw ophaalde. Daarom staan ze
nu in `tests/test_toezicht_live.py` en niet alleen in dit document.

## 11. Risico's en open punten

1. **De Atlas kan verschuiven.** 69 en 782 zijn van vandaag. Taak 3 laat dat luid falen in plaats
   van stil de pagina veranderen. Wel betekent het dat de live-tests af en toe rood staan om de
   goede reden; dat is eerder gebeurd en hoort geen aanleiding te zijn de assertie te verslappen.
2. **Signaal 1 vraagt om een zorgvuldige lezing.** "Wordt niet gemeten door RWS in het
   watersysteem" is niet "wordt niet gemeten". De formulering op de pagina is daarmee onderdeel van
   het product en wordt door een test bewaakt.
3. **Qwen2.5-32B is traag voor interactief gebruik** op deze machine, en een agentopstelling doet
   meerdere aanroepen per dossier. De deterministische kern werkt zonder model, dus signalen en
   dossier zijn er meteen; alleen de uitleg en de vraagfunctie laten wachten. Meet de duur per
   stap in taak 6b — de runlog houdt hem al bij — en noem hem op de pagina.
4. **CrewAI's pydantic-eis kan opschuiven.** Vandaag `<2.13`. Taak 9 pint de versie en de
   vergelijking vermeldt de datum.
5. **Een signaal dat altijd vuurt, is geen signaal.** Regel 10 geldt voor alle 782 voorschriften.
   Daarom staat hij één keer per dossier als voorbehoud en niet per voorschrift. Taak 4 bewaakt dat.
6. **Een configuratie die niemand narekent, is erger dan geen configuratie.** Zij wekt vertrouwen
   dat zij niet verdient. De drie tests uit taak 6, 6b en 8 zijn daarom geen bijkomstigheid: zij
   zijn wat het verschil maakt tussen besturende en decoratieve configuratie. Dit lab heeft eerder
   precies deze fout gemaakt — een documentatieregel die beweerde dat `Zwevende stof` op een
   Aquo-code koppelde, terwijl die code was ingetrokken. Een `agents.yaml` die niet afgedwongen
   wordt, is dezelfde fout op procesniveau.
7. **De cirkel is niet te sluiten met open data.** Of een signaal klopte, weet alleen de
   inspecteur. De terugkoppelplek is er; dat zij leeg is, is zelf de bevinding voor het gesprek
   over welke data erbij moet.
