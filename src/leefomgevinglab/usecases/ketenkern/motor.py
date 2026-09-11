"""Ketenmotor: voert de stappen van een dossier uit en houdt het spoor bij.

Een dossier levert een CASUS, een lijst STAPPEN (functies), een annotatieset en een
`extra`-haak voor wat alleen voor dat dossier geldt. De motor weet verder niets van
Seveso of van lozingen.
"""
import time
from datetime import datetime, timezone

from . import cim, lhso


def impact(registry: cim.Registry, annotaties: list) -> dict:
    """Waar dekken het CIM en de annotatieset van dit dossier elkaar niet?"""
    geraakt = set(registry.per_type())
    met_annotatie = {a["cim_objecttype"] for a in annotaties if a["cim_objecttype"]}
    return {
        "geannoteerd": len(geraakt & met_annotatie),
        "zonder_annotatie": sorted(geraakt - met_annotatie),
        "annotaties_zonder_objecttype": [a["annotatie"] for a in annotaties
                                         if not a["cim_objecttype"]],
        "toelichting": "Objecttypen zonder annotatie komen wél in de keten voor, maar krijgen geen "
                       "plek in het besluit — ze blijven in het zaaksysteem of bij de toezichthouder "
                       "hangen. Annotaties zonder objecttype zijn eigenschappen die het CIM niet als "
                       "object kent, zoals een identificatie of een geldigheidsdatum.",
    }


def run(dossier, live: bool = True, straal_m: int = 1000, _haal=None) -> dict:
    """Doorloop de keten van één dossier. `live=False` slaat externe bevragingen over."""
    t0 = time.perf_counter()
    ctx = {"casus": dossier.CASUS, "live": live, "straal_m": straal_m, "haal": _haal}
    registry = cim.Registry()
    uit = []

    for fn in dossier.STAPPEN:
        s0 = time.perf_counter()
        s = fn(ctx)
        registry.voeg_toe(s["nr"], s["cim"])
        uit.append(dict(s, duur_ms=round((time.perf_counter() - s0) * 1000, 1),
                        cim=[{"type": o["type"], "id": o["id"]} for o in s["cim"]]))

    cs = ctx.get("contextset", {})
    resultaat = {
        "dossier": dossier.DOSSIER,
        "gestart_op": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "live": live, "straal_m": straal_m,
        "duur_ms": round((time.perf_counter() - t0) * 1000, 1),
        "casus": dossier.CASUS,
        "stappen": uit,
        "objecten": registry.alles(),
        "per_type": registry.per_type(),
        "dekking": registry.dekking(),
        "impact": impact(registry, dossier.ANNOTATIES),
        "bronnen": cs.get("bronnen", []),
        "document": ctx.get("document"),
        "validatie": ctx.get("validatie"),
        "register": ctx.get("register"),
        "matrix": lhso.matrix(),
        "annotatieset": dossier.ANNOTATIES,
    }
    if hasattr(dossier, "extra"):
        resultaat.update(dossier.extra(ctx))
    return resultaat
