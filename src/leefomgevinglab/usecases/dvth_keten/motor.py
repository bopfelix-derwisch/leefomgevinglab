"""Ketenmotor: voert de acht stappen uit en houdt het spoor bij.

Levert één payload waarin alles staat wat de tab moet tonen — de stappen met hun payloads,
alle CIM-objecten die onderweg ontstonden, de dekking over het informatiemodel, de impact
van de TPOD-annotatieset en de status van elke bevraagde bron.
"""
import time
from datetime import datetime, timezone

from . import cim, lhso, stappen, tpod
from .casus import CASUS


def _impact(registry: cim.Registry) -> dict:
    """Waar dekken het CIM en de TPOD-annotatieset elkaar niet?"""
    geraakt = set(registry.per_type())
    met_annotatie = {a["cim_objecttype"] for a in tpod.ANNOTATIES if a["cim_objecttype"]}
    return {
        "geannoteerd": len(geraakt & met_annotatie),
        "zonder_annotatie": sorted(geraakt - met_annotatie),
        "annotaties_zonder_objecttype": [a["annotatie"] for a in tpod.ANNOTATIES
                                         if not a["cim_objecttype"]],
        "toelichting": "Objecttypen zonder annotatie komen wél in de keten voor, maar krijgen geen "
                       "plek in het besluit — ze blijven in het zaaksysteem of in GIR hangen. "
                       "Annotaties zonder objecttype zijn eigenschappen die het CIM niet als object "
                       "kent, zoals een identificatie of een geldigheidsdatum.",
    }


def run_keten(live: bool = True, straal_m: int = 1000, _haal=None) -> dict:
    """Doorloop de keten. `live=False` slaat de externe bevragingen over (reproduceerbaar)."""
    t0 = time.perf_counter()
    ctx = {"casus": CASUS, "live": live, "straal_m": straal_m, "haal": _haal}
    registry = cim.Registry()
    uit = []

    for fn in stappen.ALLE:
        s0 = time.perf_counter()
        s = fn(ctx)
        registry.voeg_toe(s["nr"], s["cim"])
        s = dict(s, duur_ms=round((time.perf_counter() - s0) * 1000, 1),
                 cim=[{"type": o["type"], "id": o["id"]} for o in s["cim"]])
        uit.append(s)

    cs = ctx.get("contextset", {})
    return {
        "gestart_op": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "live": live, "straal_m": straal_m,
        "duur_ms": round((time.perf_counter() - t0) * 1000, 1),
        "casus": CASUS,
        "stappen": uit,
        "objecten": registry.alles(),
        "per_type": registry.per_type(),
        "dekking": registry.dekking(),
        "impact": _impact(registry),
        "bronnen": cs.get("bronnen", []),
        "document": ctx.get("document"),
        "validatie": ctx.get("validatie"),
        "rev": ctx.get("rev"),
        "matrix": lhso.matrix(),
        "annotatieset": tpod.ANNOTATIES,
    }
