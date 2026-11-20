"""De RAG-index over de vier brondocumenten: chunken per pagina, embeddings, VectorStore.

**Waarom per pagina gechunkt wordt en niet per vast aantal tekens.** De bestaande IPLO-index
(`rag/ingest.py`) hakt een webpagina in stukken van 1200 tekens en onthoudt per stuk de URL. Dat
is daar genoeg: het antwoord verwijst naar een pagina en die pagina is in zijn geheel de bron.
Hier niet. De eenheid waarnaar dit dossier verwijst is de **pagina van een pdf** -- dat is wat
`#page=N` opent en wat `vindplaats.controleer()` natrekt. Een chunk die over een paginagrens
heen loopt kan dus niet eerlijk geciteerd worden: hij staat op twee pagina's, en de helft die het
antwoord draagt is niet te zeggen.

Daarom: eerst splitsen op de form feed die `pdftotext` tussen pagina's zet, dan pas binnen een
pagina verder knippen als zij te lang is. Elke chunk draagt `bron`, `pagina` en `deel`, en dus
een werkende deeplink. Dat kost een paar chunks meer dan nodig -- korte pagina's blijven kort --
en levert op dat elk opgehaald fragment een controleerbare vindplaats heeft.

**Wat deze index niet doet: een antwoord verzinnen.** `zoek()` levert passages met hun
vindplaats; dat is het product. `beantwoord()` laat een taalmodel die passages samenvatten en
is uitdrukkelijk een laag erbovenop: zonder passages zwijgt hij, en de passages staan altijd bij
het antwoord zodat de lezer de samenvatting kan nalopen. Dezelfde grens als in
`usecases/vergunningen/chatbot.py` en als bij de agents op `/toezicht`: het model legt uit, het
model stelt niets vast.
"""
import sys

import httpx

from leefomgevinglab.connectors.base import ConnectorError
from leefomgevinglab.kennisbasis import bronnen as bronnen_mod
from leefomgevinglab.kennisbasis import vindplaats as vindplaats_mod
from leefomgevinglab.rag.ingest import chunk_text
from leefomgevinglab.rag.store import VectorStore

#: Waar de index staat. Naast de documenten, niet in de repo -- de vectoren zijn brondata.
STORE_DIR = str(bronnen_mod.BASIS / "index")

#: Een pagina die langer is dan dit wordt binnen de pagina verder geknipt, met overlap.
#:
#: **Dit getal wordt begrensd door de embedding-server, niet door de leesbaarheid**, en dat kostte
#: hier een mislukte bouw. De grens is níet de contextgrens (`--ctx-size 8192`) maar de *fysieke
#: batchgrens* van llama.cpp, die standaard op 512 tokens staat. Eén invoer die daarboven komt
#: levert `HTTP 500: input (548 tokens) is too large to process. increase the physical batch size
#: (current batch size: 512)`. Met 1800 tekens Nederlandse rapporttekst (~3,3 tekens per token)
#: gebeurde dat vanaf chunk 112. 1200 is de waarde die `rag/ingest.py` voor de IPLO-index al
#: gebruikt -- ongeveer 365 tokens, met marge voor een tabelpagina die dichter tokeniseert. Wie
#: dit omhoog zet, moet de server mee omhoog zetten (`--ubatch-size`), en die server wordt door
#: de IPLO-index gedeeld.
CHUNK_TEKENS = 1200
CHUNK_OVERLAP = 200

#: Een pagina met minder dan dit aan tekst draagt geen inhoud: een titelblad, een lege pagina
#: tussen hoofdstukken, of een pagina die alleen een paginanummer en een voettekst heeft. Die
#: hoort niet in de index, want hij levert wel treffers op maar geen antwoord.
MINIMUM_TEKENS = 120


def paginachunks(bron_id: str) -> list[dict]:
    """De chunks van één document: per pagina, en binnen een lange pagina verder geknipt.

    `deel` is 0 voor een pagina die in één stuk past, en loopt op bij een gesplitste pagina. Het
    staat erbij zodat twee chunks van dezelfde pagina te onderscheiden zijn zonder dat de pagina
    zelf verandert -- de deeplink blijft `#page=N` voor allebei."""
    bron = bronnen_mod.OP_ID[bron_id]
    uit = []
    for nummer, tekst in enumerate(vindplaats_mod.paginas(bron_id), start=1):
        schoon = vindplaats_mod.normaliseer(tekst)
        if len(schoon) < MINIMUM_TEKENS:
            continue
        stukken = ([schoon] if len(schoon) <= CHUNK_TEKENS
                   else chunk_text(schoon, CHUNK_TEKENS, CHUNK_OVERLAP))
        for deel, stuk in enumerate(stukken):
            uit.append({
                "text": stuk,
                "bron": bron_id,
                "bron_titel": bron["titel"],
                "uitgever": bron["uitgever"],
                "pagina": nummer,
                "deel": deel,
                "url": vindplaats_mod.deeplink(bron_id, nummer),
            })
    return uit


def alle_chunks(bron_ids=None) -> list[dict]:
    """De chunks van alle (of de genoemde) documenten. Een document dat niet binnengehaald is
    laat een `FileNotFoundError` doorkomen -- stil overslaan zou een halve index opleveren die er
    volledig uitziet."""
    ids = bron_ids or [b["id"] for b in bronnen_mod.BRONNEN]
    uit = []
    for bron_id in ids:
        uit.extend(paginachunks(bron_id))
    return uit


def bouw(embed_fn, bron_ids=None, batch: int = 16, voortgang=None) -> VectorStore:
    """De index bouwen. `embed_fn` krijgt een lijst teksten en levert een lijst vectoren.

    **In batches, en dat is geen optimalisatie.** De embedding-server (llama.cpp met bge-m3 op
    8082) krijgt hier ruim duizend chunks aangeboden; in één verzoek loopt dat op de
    contextgrens of de timeout. Per batch is ook te zien hoe ver hij is, wat bij een bouw van
    enkele minuten het verschil is tussen wachten en denken dat het hangt."""
    chunks = alle_chunks(bron_ids)
    vectoren = []
    for i in range(0, len(chunks), batch):
        deel = chunks[i:i + batch]
        try:
            vectoren.extend(embed_fn([c["text"] for c in deel]))
        except ConnectorError:
            # Eén te lange chunk laat het hele verzoek met een 500 omvallen, en `embed_texts`
            # vertaalt dat naar een `ConnectorError` zonder te zeggen welke. Daarom hier
            # stuk-voor-stuk opnieuw: dat wijst de dader aan in plaats van de bouw af te breken
            # met "service niet beschikbaar" terwijl de service prima draait.
            vectoren.extend(_een_voor_een(deel, embed_fn))
        if voortgang:
            voortgang(min(i + batch, len(chunks)), len(chunks))
    return VectorStore.build(chunks, vectoren)


def _een_voor_een(deel: list[dict], embed_fn) -> list[list[float]]:
    """De chunks van een mislukte batch los aanbieden, en luid omvallen op degene die het niet
    haalt -- met bron, pagina en lengte erbij, want dat is wat je nodig hebt om hem te
    repareren."""
    uit = []
    for c in deel:
        try:
            uit.extend(embed_fn([c["text"]]))
        except ConnectorError as exc:
            raise ConnectorError(
                f"chunk van {c['bron']} pagina {c['pagina']} deel {c['deel']} "
                f"({len(c['text'])} tekens) wordt niet geaccepteerd door de embedding-service. "
                f"Waarschijnlijk boven de fysieke batchgrens -- verlaag CHUNK_TEKENS of verhoog "
                f"--ubatch-size op de server.") from exc
    return uit


def laad() -> VectorStore | None:
    """De index van schijf, of `None` als zij niet gebouwd is. De pagina moet kunnen zeggen
    'nog niet gebouwd' in plaats van een zoekvak aan te bieden dat niets vindt."""
    try:
        return VectorStore.load(STORE_DIR)
    except FileNotFoundError:
        return None


def status() -> dict:
    """Of de index er is en wat erin zit, zonder haar te laden als dat niet hoeft."""
    store = laad()
    if store is None:
        return {"gebouwd": False, "chunks": 0, "per_bron": {}}
    per_bron = {}
    for c in store.chunks:
        per_bron[c.get("bron", "?")] = per_bron.get(c.get("bron", "?"), 0) + 1
    return {"gebouwd": True, "chunks": store.size, "per_bron": per_bron,
            "store_dir": STORE_DIR}


def zoek(vraag: str, store: VectorStore, embed_fn, top_k: int = 5,
         bron_ids=None) -> list[dict]:
    """De passages die bij de vraag passen, elk met zijn vindplaats.

    `bron_ids` filtert op document. Dat gebeurt **na** het zoeken en met een ruimere k, want de
    VectorStore kent geen filter; zou het ervoor gebeuren, dan moest er een index per document
    zijn. De ruimere k voorkomt dat een filter op één document een lege lijst oplevert terwijl er
    passages zijn."""
    k = top_k if not bron_ids else top_k * len(bronnen_mod.BRONNEN)
    treffers = store.search(embed_fn([vraag])[0], k)
    if bron_ids:
        treffers = [t for t in treffers if t.get("bron") in set(bron_ids)]
    return treffers[:top_k]


DISCLAIMER = ("Een samenvatting van de getoonde passages door een taalmodel, geen uitspraak van "
              "dit lab en geen citaat uit de rapporten. De passages staan erbij om na te lezen.")

#: Begrensd om dezelfde reden als in `vergunningen/chatbot.py`: een lange prompt zonder cap loopt
#: op de Orin over de timeout, en dan degradeert de laag stil naar leeg.
ANTWOORD_MAX_TOKENS = 600


def prompt(vraag: str, passages: list[dict]) -> str:
    context = "\n\n".join(
        f"[{p['bron_titel']}, pagina {p['pagina']}]\n{p['text']}" for p in passages)
    return (
        "Je vat passages uit openbare rapporten over de Omgevingswet samen. Antwoord alleen op "
        "grond van de passages hieronder. Verzin niets; staat het antwoord er niet in, zeg dan "
        "dat deze passages het niet zeggen. Noem bij elke bewering het rapport en de pagina "
        "waar zij staat. Geef geen eigen oordeel over het stelsel.\n\n"
        f"Passages:\n{context}\n\nVraag: {vraag}"
    )


def beantwoord(vraag: str, store: VectorStore, embed_fn, llm_base_url: str, model: str,
               top_k: int = 5, timeout_s: float = 60.0, bron_ids=None) -> dict:
    """Zoeken en laten samenvatten. **Zonder passages geen antwoord** -- dan is er niets om op te
    baseren en zou het model uit zijn eigen gewichten gaan praten, precies wat een kennisbasis
    niet moet doen."""
    basis = {"vraag": vraag, "passages": [], "antwoord": None, "disclaimer": DISCLAIMER,
             "reden": None}
    try:
        passages = zoek(vraag, store, embed_fn, top_k=top_k, bron_ids=bron_ids)
    except ConnectorError as exc:
        return {**basis, "reden": f"de embedding-service antwoordde niet: {exc}"}
    if not passages:
        return {**basis, "reden": "geen passage in de index past bij deze vraag"}
    basis["passages"] = passages
    try:
        resp = httpx.post(
            f"{llm_base_url.rstrip('/')}/chat/completions",
            json={"model": model, "max_tokens": ANTWOORD_MAX_TOKENS, "temperature": 0.1,
                  "messages": [{"role": "user", "content": prompt(vraag, passages)}]},
            timeout=timeout_s,
        )
        resp.raise_for_status()
        tekst = resp.json()["choices"][0]["message"]["content"].strip()
    except (httpx.HTTPError, KeyError, IndexError, ValueError) as exc:
        return {**basis, "reden": f"het taalmodel antwoordde niet ({type(exc).__name__}); "
                                  "de passages staan er wel"}
    return {**basis, "antwoord": tekst}


def _voortgang_naar_stderr(gedaan: int, totaal: int) -> None:
    print(f"\r  embeddings: {gedaan}/{totaal}", end="", file=sys.stderr, flush=True)
