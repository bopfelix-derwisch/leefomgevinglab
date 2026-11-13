#!/usr/bin/env python3
"""Het register, de metingen, de normen en de Aquo-referentie bouwen tot één bevraagbare RDF-graaf.

Vier bronnen, drie live en één lokaal bestand -- dezelfde vier als `tests/test_toezicht_live.py`:

  * `SmwkAtlasConnector` -- het vergunningenregister, live opgehaald (geen kopie in de repo,
    zelfde licentievoorbehoud als elders in dit lab).
  * de Aquo-domeintabel Parameter (`toezicht.aquo.laad`), lokaal op
    `/mnt/nvme/geluidsmeter/data/external/wkp/aquo_Parameter.csv`.
  * de verdichte WKP-meetset (`kmg.metingen.laad`, `scripts/13`) en de KRW-normen
    (`kmg.doelen.laad_normen`, `scripts/17`), beide optioneel -- zonder metingen/normen bouwt dit
    script toch een graaf, alleen zonder `t:Meting`/`t:Norm`-knopen.

De Turtle komt op NVMe terecht, nooit in de repo (zelfde regel als elke andere brondata in dit
lab).

Draaien:

    PYTHONPATH=src .venv/bin/python scripts/22_bouw_toezichtgraaf.py \\
        --aquo /mnt/nvme/geluidsmeter/data/external/wkp/aquo_Parameter.csv \\
        --metingen /mnt/nvme/geluidsmeter/data/external/wkp/metingen_2025.json \\
        --normen /mnt/nvme/geluidsmeter/data/external/wkp/krw_normen.json \\
        --uit /mnt/nvme/geluidsmeter/data/external/toezicht/toezicht.ttl
"""
import argparse
import sys
from pathlib import Path

from leefomgevinglab.connectors.smwk_atlas import SmwkAtlasConnector
from leefomgevinglab.ld import store
from leefomgevinglab.usecases.kmg import doelen as doelen_mod
from leefomgevinglab.usecases.kmg import metingen as metingen_mod
from leefomgevinglab.usecases.toezicht import aquo as aquo_mod
from leefomgevinglab.usecases.toezicht import graaf

# Hetzelfde centrale RD-punt en dezelfde straal als `tests/test_toezicht_live.py`: heel het
# Maasstroomgebied in één keer, in plaats van een straal die een deel van het register zou missen.
_PUNT_X, _PUNT_Y = 170000.0, 390000.0
_STRAAL_M = 250_000


def bouw(x: float, y: float, straal_m: int, cache_dir: str, aquo_pad: str,
        metingen_pad: str | None, normen_pad: str | None) -> tuple:
    atlas = SmwkAtlasConnector(cache_dir=cache_dir)
    register = atlas.vergunningen_bij_punt(x, y, straal_m=straal_m)
    if not register:
        raise SystemExit(
            f"geen vestigingen gevonden rond ({x}, {y}) binnen {straal_m} m -- is de Atlas "
            "verschoven of onbereikbaar? Niet stil doorgaan met een lege graaf.")

    aquo_ref = aquo_mod.laad(aquo_pad)
    if not aquo_ref.get("beschikbaar"):
        raise SystemExit(f"Aquo-domeintabel niet leesbaar op {aquo_pad}: {aquo_ref.get('reden')}")

    metingen = metingen_mod.laad(metingen_pad) if metingen_pad else {"beschikbaar": False, "punten": []}
    normen = doelen_mod.laad_normen(normen_pad) if normen_pad else {"beschikbaar": False, "normen": {}}

    g = graaf.bouw(register, metingen, normen, aquo_ref)
    return g, register, metingen, normen


def _telling(g, register: list[dict]) -> dict:
    aangenomen = g.query(f"""
        PREFIX t: <{graaf.T}>
        SELECT (COUNT(?v) AS ?n) WHERE {{ ?v t:zekerheid "aangenomen" }}""")
    return {
        "vestigingen": len(register),
        "voorschriften": sum(len(v.get("voorschriften") or []) for v in register),
        "triples": len(g),
        "aangenomen_beweringen": int(next(iter(aangenomen))[0]),
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--x", type=float, default=_PUNT_X, help="RD x-coördinaat van het middelpunt")
    ap.add_argument("--y", type=float, default=_PUNT_Y, help="RD y-coördinaat van het middelpunt")
    ap.add_argument("--straal", type=int, default=_STRAAL_M, help="straal in meter")
    ap.add_argument("--cache-dir", default="/mnt/nvme/geluidsmeter/data/external/atlas_cache",
                    help="cache-map voor de Atlas-connector")
    ap.add_argument("--aquo", required=True, help="pad naar aquo_Parameter.csv")
    ap.add_argument("--metingen", default=None, help="pad naar de verdichte WKP-meetset (scripts/13)")
    ap.add_argument("--normen", default=None, help="pad naar het KRW-normenbestand (scripts/17)")
    ap.add_argument("--uit", required=True, help="pad voor de Turtle-graaf (op NVMe, niet in de repo)")
    a = ap.parse_args()

    g, register, metingen, normen = bouw(a.x, a.y, a.straal, a.cache_dir, a.aquo, a.metingen, a.normen)

    uit_pad = Path(a.uit)
    store.save_graph(g, str(uit_pad.parent), naam=uit_pad.name)

    t = _telling(g, register)
    print(f"{t['vestigingen']} vestigingen, {t['voorschriften']} voorschriften -> "
          f"{t['triples']} triples ({t['aangenomen_beweringen']} als 'aangenomen' gemarkeerd) "
          f"-> {uit_pad}")
    if not metingen.get("beschikbaar"):
        print("let op: geen metingen meegegeven of leesbaar -- de graaf heeft geen t:Meting-knopen")
    if not normen.get("beschikbaar"):
        print("let op: geen normen meegegeven of leesbaar -- de graaf heeft geen t:Norm-knopen")
    return 0


if __name__ == "__main__":
    sys.exit(main())
