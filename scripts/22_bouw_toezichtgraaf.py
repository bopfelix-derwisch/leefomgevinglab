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
from leefomgevinglab.usecases.kmg import service as kmg_service
from leefomgevinglab.usecases.kmg import toerekening as kmg_toerekening
from leefomgevinglab.usecases.toezicht import aquo as aquo_mod
from leefomgevinglab.usecases.toezicht import context as context_mod
from leefomgevinglab.usecases.toezicht import graaf
from leefomgevinglab.usecases.toezicht import graafbouw
from leefomgevinglab.usecases.toezicht import register as register_mod

# Hetzelfde centrale RD-punt en dezelfde straal als `tests/test_toezicht_live.py`: heel het
# Maasstroomgebied in één keer, in plaats van een straal die een deel van het register zou missen.
_PUNT_X, _PUNT_Y = 170000.0, 390000.0
_STRAAL_M = 250_000


def bouw(x: float, y: float, straal_m: int, cache_dir: str, aquo_pad: str,
        metingen_pad: str | None, normen_pad: str | None, doelen_pad: str | None = None,
        gemeten_codes_pad: str | None = None) -> tuple:
    atlas = SmwkAtlasConnector(cache_dir=cache_dir)
    ruw = atlas.vergunningen_bij_punt(x, y, straal_m=straal_m)
    # **Ontdubbelen, net als de route.** `toezicht.register.voorbereid` haalt de 132 letterlijk
    # herhaalde voorschriften eruit (17% van 782) en legt de identiteit op `locatiecode::kenmerk`.
    # Zonder deze regel bouwde dit script op het rúwe Atlas-antwoord en was het bestand een
    # ándere graaf dan de route in het geheugen maakt -- gemeten: 75.190 tegen 72.682 triples.
    # Dat is dezelfde fout die `graafbouw` in de code moest voorkomen, dan in de data.
    register = register_mod.voorbereid(ruw)
    if not register:
        raise SystemExit(
            f"geen vestigingen gevonden rond ({x}, {y}) binnen {straal_m} m -- is de Atlas "
            "verschoven of onbereikbaar? Niet stil doorgaan met een lege graaf.")

    aquo_ref = aquo_mod.laad(aquo_pad)
    if not aquo_ref.get("beschikbaar"):
        raise SystemExit(f"Aquo-domeintabel niet leesbaar op {aquo_pad}: {aquo_ref.get('reden')}")

    metingen = metingen_mod.laad(metingen_pad) if metingen_pad else {"beschikbaar": False, "punten": []}
    normen = doelen_mod.laad_normen(normen_pad) if normen_pad else {"beschikbaar": False, "normen": {}}

    # **Mét context, dus mét de signalen.** Vóór deze wijziging bouwde dit script
    # `graaf.bouw(...)` zonder context: dat levert een graaf zonder `t:Signaal`, en dus zonder de
    # brug tussen `/wasstraat` en `/toezicht` -- precies de vraag waarvoor de bevraagbare laag
    # bestaat. Een bestand dat stil die halve graaf bevat is erger dan geen bestand, want de route
    # leest het bestand bij voorkeur en zou dan minder kunnen beantwoorden dan live.
    #
    # Het bouwen zelf staat in `toezicht.graafbouw`, dezelfde functie die `/api/toezicht/vraag`
    # gebruikt: één bouwer, twee aanroepers, zodat schijf en geheugen niet uiteen kunnen lopen.
    doelenset = (doelen_mod.laad(doelen_pad) if doelen_pad
                 else {"beschikbaar": False, "waterlichamen": {}})
    getoetst = context_mod.toetsing(metingen_mod.punten(metingen), doelenset, normen)
    gemeten_codes = (metingen_mod.codes_set(metingen_mod.laad_codes(gemeten_codes_pad))
                     if gemeten_codes_pad else set())

    def per_vergunning(reg):
        per_sleutel, _redenen = kmg_service._waterlichaam_per_vergunning(reg, True)
        uit = {}
        for i, post in enumerate(reg):
            sleutel = kmg_toerekening.sleutel_post(post, i)
            if sleutel in per_sleutel:
                uit[(post.get("kenmerk"), post.get("locatiecode"))] = per_sleutel[sleutel]
        return uit

    g, telling = graafbouw.bouw_met_telling(
        register=register, metingen=metingen, normen=normen, aquo_ref=aquo_ref,
        overschrijdingen=context_mod.overschrijdingen(getoetst),
        gemeten_codes=gemeten_codes,
        stoffen_met_norm=graaf.stoffen_met_norm(normen),
        waterlichaam_per_vergunning=per_vergunning)
    return g, register, metingen, normen, telling


def _aangenomen(g) -> int:
    rijen = g.query(f"""
        PREFIX t: <{graaf.T}>
        SELECT (COUNT(?v) AS ?n) WHERE {{ ?v t:zekerheid "aangenomen" }}""")
    return int(next(iter(rijen))[0])


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
    ap.add_argument("--doelen", default=None,
                    help="pad naar de KRW-doelen (scripts/17) -- nodig voor de toetsing, en "
                         "daarmee voor het signaal 'meting boven de norm bovenstrooms'")
    ap.add_argument("--gemeten-codes", default=None,
                    help="pad naar de gemeten Aquo-codes (scripts/21) -- nodig voor het signaal "
                         "'geen onafhankelijke meting'")
    ap.add_argument("--uit", required=True, help="pad voor de Turtle-graaf (op NVMe, niet in de repo)")
    a = ap.parse_args()

    g, register, metingen, normen, telling = bouw(
        a.x, a.y, a.straal, a.cache_dir, a.aquo, a.metingen, a.normen, a.doelen, a.gemeten_codes)

    uit_pad = Path(a.uit)
    store.save_graph(g, str(uit_pad.parent), naam=uit_pad.name)

    print(f"{telling['vestigingen']} vestigingen, {telling['voorschriften']} voorschriften, "
          f"{telling['signalen']} signalen -> {telling['triples']} triples "
          f"({_aangenomen(g)} beweringen als 'aangenomen' gemarkeerd) -> {uit_pad}")
    if not telling["signalen"]:
        print("LET OP: nul signalen in de graaf -- dan ontbreekt de brug tussen /wasstraat en "
              "/toezicht, en kan de vraagweg de interessante vraag niet beantwoorden. Controleer "
              "of --doelen en --gemeten-codes zijn meegegeven.")
    if not metingen.get("beschikbaar"):
        print("let op: geen metingen meegegeven of leesbaar -- de graaf heeft geen t:Meting-knopen")
    if not normen.get("beschikbaar"):
        print("let op: geen normen meegegeven of leesbaar -- de graaf heeft geen t:Norm-knopen")
    return 0


if __name__ == "__main__":
    sys.exit(main())
