"""CIM-objectbibliotheek: elk ding dat de keten oplevert, is een object uit het Cim-VTH-Flo.

De geldige objecttypen komen uit dezelfde bron als de kapstok (/vth) en de bronnenkaart
(/vth-bronnen), zodat een typefout hier meteen opvalt in plaats van pas in de UI.
"""
from leefomgevinglab.usecases import vth_bronnen as vb

GELDIGE_OBJECTTYPEN = {ot for v in vb.VIEWS for ot in v["objecttypen"]}


class CimFout(ValueError):
    pass


def obj(type: str, id: str, **attributen) -> dict:
    """Eén CIM-object. Het objecttype moet in het informatiemodel voorkomen."""
    if type not in GELDIGE_OBJECTTYPEN:
        raise CimFout(f"'{type}' is geen objecttype in het Cim-VTH-Flo")
    return {"type": type, "id": id, "attributen": attributen}


def view_van(objecttype: str) -> str | None:
    for v in vb.VIEWS:
        if objecttype in v["objecttypen"]:
            return v["naam"]
    return None


class Registry:
    """Verzamelt de objecten die de keten onderweg maakt, met de stap die ze maakte."""

    def __init__(self):
        self.per_stap: dict[int, list] = {}

    def voeg_toe(self, stap: int, objecten: list) -> list:
        self.per_stap.setdefault(stap, []).extend(objecten)
        return objecten

    def alles(self) -> list:
        return [dict(o, stap=nr) for nr in sorted(self.per_stap) for o in self.per_stap[nr]]

    def per_type(self) -> dict:
        uit: dict[str, int] = {}
        for nr in self.per_stap:
            for o in self.per_stap[nr]:
                uit[o["type"]] = uit.get(o["type"], 0) + 1
        return uit

    def dekking(self) -> dict:
        geraakt = set(self.per_type())
        niet = sorted(GELDIGE_OBJECTTYPEN - geraakt)
        return {"totaal": len(GELDIGE_OBJECTTYPEN), "geraakt": len(geraakt),
                "niet_geraakt": niet,
                "per_view": {v["naam"]: sorted(set(v["objecttypen"]) & geraakt) for v in vb.VIEWS}}
