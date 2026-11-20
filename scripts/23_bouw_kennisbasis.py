#!/usr/bin/env python3
"""Bouw de kennisbasis leefomgeving: documenten controleren, tekst extraheren, index bouwen.

Dossier: **bevindingen VTH**. De vier brondocumenten zijn openbaar gepubliceerd en worden
binnengehaald naar `/mnt/nvme/geluidsmeter/data/external/kennisbasis/` -- buiten de repo, zoals
alle brondata in dit lab.

    python3 scripts/23_bouw_kennisbasis.py --controleer   # citaten tegen de tekst, geen netwerk
    python3 scripts/23_bouw_kennisbasis.py --extract      # pdf -> tekst (pdftotext -layout)
    python3 scripts/23_bouw_kennisbasis.py --index        # embeddings + VectorStore

**`--controleer` is de belangrijkste stand.** Hij doet geen netwerk en geen werk, en zegt of elk
citaat op de pagina staat waar de pagina van dit lab het neerzet. Dat is de enige controle die
scheidt tussen "dit rapport zegt" en "zo las ik dit rapport".

Let op: `pdftotext` moet beschikbaar zijn (poppler-utils) en de embedding-server op 8082 moet
draaien voor `--index` (`systemctl status leefomgevinglab-embed`).
"""
import argparse
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from leefomgevinglab.kennisbasis import bevindingen as bevindingen_mod  # noqa: E402
from leefomgevinglab.kennisbasis import bronnen as bronnen_mod  # noqa: E402
from leefomgevinglab.kennisbasis import graaf as graaf_mod  # noqa: E402
from leefomgevinglab.kennisbasis import index as index_mod  # noqa: E402
from leefomgevinglab.kennisbasis import vindplaats as vindplaats_mod  # noqa: E402


def overzicht() -> int:
    print(f"kennisbasis op {bronnen_mod.BASIS}\n")
    ontbreekt = 0
    for bron in bronnen_mod.overzicht():
        op = bron["op_schijf"]
        mb = f"{op['pdf_bytes'] / 1e6:.1f} MB" if op["pdf_bytes"] else "-"
        print(f"  {bron['id']:<9} {bron['titel'][:34]:<34} {bron['datum']}  "
              f"pdf {'ja ' if op['pdf'] else 'NEE'} {mb:>9}  "
              f"tekst {'ja' if op['tekst'] else 'NEE'}  {op['paginas'] or '-':>3} p.")
        if not op["pdf"]:
            print(f"             haal binnen van {bron['url']}")
            ontbreekt += 1
    print()
    return ontbreekt


def extract() -> int:
    """pdf -> tekst met `pdftotext -layout`. De layout-stand behoudt kolommen; dat is nodig
    omdat sommige rapporten tekstkaders naast de hoofdtekst zetten en die anders door de
    alinea's heen gevlochten raken."""
    fouten = 0
    for bron in bronnen_mod.BRONNEN:
        pdf, txt = bronnen_mod.pad(bron, "bestand"), bronnen_mod.pad(bron, "tekst")
        if not pdf.exists():
            print(f"  {bron['id']}: pdf ontbreekt, overgeslagen", file=sys.stderr)
            fouten += 1
            continue
        subprocess.run(["pdftotext", "-layout", str(pdf), str(txt)], check=True)
        print(f"  {bron['id']}: {bronnen_mod.paginas(bron)} pagina's -> {txt.name}")
    return fouten


def controleer() -> int:
    fout = vindplaats_mod.controleer_alles(bevindingen_mod.BEVINDINGEN)
    totaal = len(bevindingen_mod.BEVINDINGEN)
    if not fout:
        print(f"  alle {totaal} citaten staan op de pagina die de bevinding noemt")
    for f in fout:
        waar = f"gevonden op pagina {f['gevonden_op']}" if f["gevonden_op"] else "NERGENS gevonden"
        print(f"  {f['id']}: citaat staat niet op pagina {f['pagina']} van {f['bron']} "
              f"-- {waar}", file=sys.stderr)
        print(f"      {f['citaat'][:90]}", file=sys.stderr)
    graaf = graaf_mod.bouw()
    print(f"  graaf: {graaf_mod.telling(graaf)}")
    return len(fout)


def bouw_index(base_url: str, model: str) -> int:
    from functools import partial

    from leefomgevinglab.rag.embed import embed_texts
    embed_fn = partial(embed_texts, base_url=base_url, model=model)
    chunks = index_mod.alle_chunks()
    print(f"  {len(chunks)} chunks uit {len(bronnen_mod.BRONNEN)} documenten")
    store = index_mod.bouw(embed_fn, voortgang=index_mod._voortgang_naar_stderr)
    print(file=sys.stderr)
    store.save(index_mod.STORE_DIR)
    print(f"  index met {store.size} chunks opgeslagen in {index_mod.STORE_DIR}")
    print(f"  {index_mod.status()}")
    return 0


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__,
                                formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--extract", action="store_true", help="pdf -> tekst")
    p.add_argument("--controleer", action="store_true", help="citaten tegen de tekst")
    p.add_argument("--index", action="store_true", help="embeddings + VectorStore")
    p.add_argument("--embed-url", default="http://localhost:8082/v1")
    p.add_argument("--embed-model", default="bge-m3")
    a = p.parse_args()

    fouten = overzicht()
    if a.extract:
        print("tekstextractie:")
        fouten += extract()
    if a.controleer or a.index:
        print("citaatcontrole:")
        fouten += controleer()
    if a.index:
        if fouten:
            print("er staan citaten niet op hun pagina -- eerst repareren", file=sys.stderr)
            return 1
        print("index:")
        fouten += bouw_index(a.embed_url, a.embed_model)
    return 1 if fouten else 0


if __name__ == "__main__":
    raise SystemExit(main())
