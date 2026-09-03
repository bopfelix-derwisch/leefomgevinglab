"""IPLO-ingest: HTML ophalen -> tekst -> chunks -> embeddings -> VectorStore."""
import html as _html
import re
import sys
import time

import httpx

from leefomgevinglab.connectors.base import ConnectorError
from leefomgevinglab.rag.store import VectorStore

# Verwijder eerst hele script/style/head/noscript-blokken (incl. inhoud), strip
# daarna de resterende tags. Robuuster dan html.parser op echte HTML met scripts.
_BLOCK_RE = re.compile(r"(?is)<(script|style|head|noscript)\b[^>]*>.*?</\1>")
_TAG_RE = re.compile(r"(?s)<[^>]+>")


def html_to_text(html: str) -> str:
    s = _BLOCK_RE.sub(" ", html)
    s = _TAG_RE.sub(" ", s)
    s = _html.unescape(s)
    return " ".join(s.split())


def chunk_text(text: str, chunk_chars: int, overlap: int) -> list[str]:
    text = " ".join(text.split())
    if not text:
        return []
    step = max(1, chunk_chars - overlap)
    return [text[i:i + chunk_chars] for i in range(0, len(text), step)]


def fetch_url(url: str, timeout_s: float = 20.0) -> str:
    try:
        resp = httpx.get(url, timeout=timeout_s, follow_redirects=True)
        resp.raise_for_status()
        return resp.text
    except httpx.HTTPError as exc:
        raise ConnectorError(f"IPLO-pagina niet beschikbaar: {url}") from exc


def build_index(urls, embed_fn, chunk_chars: int, overlap: int,
                pauze_s: float = 0.0, pogingen: int = 3) -> VectorStore:
    """Bouw een index uit een lijst URL's.

    `pauze_s` en `pogingen` bestaan omdat deze functie met twee URL's iets anders is
    dan met honderd. Zonder pauze haalt hij de bron in één ruk leeg en gaat die
    afknijpen; zonder herpogingen breekt één tijdelijke fout de hele bouw af, ook
    als de andere negenennegentig pagina's prima binnenkwamen. Overgeslagen URL's
    worden gemeld op stderr, niet stilzwijgend weggelaten.
    """
    chunks: list[dict] = []
    overgeslagen: list[str] = []

    for i, url in enumerate(urls):
        if i and pauze_s:
            time.sleep(pauze_s)
        tekst = None
        for poging in range(pogingen):
            try:
                tekst = html_to_text(fetch_url(url))
                break
            except ConnectorError:
                if poging + 1 < pogingen:
                    time.sleep(1.0 + poging)
        if tekst is None:
            overgeslagen.append(url)
            continue
        for piece in chunk_text(tekst, chunk_chars, overlap):
            chunks.append({"text": piece, "url": url})

    if overgeslagen:
        print(f"ingest: {len(overgeslagen)} van {len(urls)} URL's overgeslagen na "
              f"{pogingen} pogingen:", file=sys.stderr)
        for u in overgeslagen:
            print(f"  - {u}", file=sys.stderr)

    if not chunks:
        return VectorStore.build([], [])
    vectors = embed_fn([c["text"] for c in chunks])
    return VectorStore.build(chunks, vectors)
