"""De Aquo-domeintabel Parameter -- geldige én ingetrokken codes, voor de regels 1 en 2.

`kmg.lozingsmodel.laad_parameters()` levert alleen geldige codes (`op_naam`, 5630 stuks): een
ingetrokken naam zoals "Zwevende stof" komt daar niet in voor, want die JSON komt uit
`scripts/16`, dat de 1479 ingetrokken codes er bewust uitfiltert om schijnzekerheid te
voorkomen. Voor `signalen.regel_vervallen_code` is dat net het probleem: zonder de ingetrokken
code zelf zou die regel nooit vuren, en vielen alle 90 voorschriften op "Zwevende stof" onterecht
onder `niet_in_referentie` ("parameter niet in de referentie") in plaats van `vervallen_code`
("grenswaarde op een ingetrokken code") -- twee signalen die het plan bewust uit elkaar houdt
(signaal 2 versus signaal 3, §6).

Deze module leest daarom de ruwe bron opnieuw: de Aquo-domeintabel Parameter zelf
(`aquo_Parameter.csv`, puntkomma-gescheiden, `utf-8-sig`, kolom `Codes` -- niet `Code`), in
plaats van de al gefilterde JSON. Beide lezen dezelfde CSV; dit bestand bewaart alleen de kolom
die de andere weglaat.

**Een naam kan twee keer voorkomen**, één keer `Geldig` en één keer `Vervallen` (748 van de 7109
rijen, bv. "minerale olie") -- meestal omdat een oude code is vervangen door een nieuwe onder
dezelfde Nederlandse naam. Dan telt de geldige code: er is een actuele referentie om tegen te
koppelen, en de intrekking van de oude is dan geen signaal meer waard. "Zwevende stof" is het
andere geval: beide rijen zijn `Vervallen` en `Vervangen door` is op geen van beide gevuld, dus
voor die naam bestaat geen weg terug naar een geldige code.
"""
import csv
from datetime import date
from pathlib import Path

_GELDIGE_STATUSSEN = ("Geldig", "Concept, Geldig")


def laad(pad: str) -> dict:
    """De parameterreferentie lezen, met geldige én ingetrokken codes.

    Zacht falen, net als `kmg.lozingsmodel.laad_parameters`: zonder (leesbare) bron blijft
    `verrijk()` mogelijk, alleen doet hij dan niets -- en dat moet deze functie kunnen zeggen.
    """
    p = Path(pad)
    bron = {"naam": "Aquo-domeintabel Parameter", "pad": pad}
    if not p.exists():
        return {"beschikbaar": False, "geldig": {}, "vervallen": {}, "aantal": {}, "bron": bron,
                "reden": f"geen Aquo-domeintabel gevonden op {pad}; download hem van "
                         "https://www.aquo.nl/images/aquo/a/a3/Parameter.csv"}
    try:
        with p.open(encoding="utf-8-sig", newline="") as f:
            rijen = list(csv.DictReader(f, delimiter=";"))
    except (OSError, csv.Error) as exc:
        return {"beschikbaar": False, "geldig": {}, "vervallen": {}, "aantal": {}, "bron": bron,
                "reden": f"de Aquo-domeintabel op {pad} is onleesbaar ({type(exc).__name__})"}

    geldig: dict[str, str] = {}
    vervallen: dict[str, str] = {}
    aantal: dict[str, int] = {}
    for rij in rijen:
        naam = (rij.get("Omschrijving") or "").strip().lower()
        code = (rij.get("Codes") or "").strip()
        status = (rij.get("Status") or "").strip()
        aantal[status] = aantal.get(status, 0) + 1
        if not naam or not code:
            continue
        if status in _GELDIGE_STATUSSEN:
            geldig[naam] = code
        elif status == "Vervallen":
            # `setdefault`: komt een ingetrokken naam met twee verschillende oude codes voor
            # (zelf niet aangetroffen in de bron, maar niet uitgesloten), dan telt de eerst
            # gelezen code. Welke code precies wordt getoond is hier ondergeschikt aan het feit
            # dát de naam ingetrokken is -- dat feit bepaalt het signaal.
            vervallen.setdefault(naam, code)

    return {"beschikbaar": True, "geldig": geldig, "vervallen": vervallen, "aantal": aantal,
            "bron": bron, "gelezen_op": date.today().isoformat(), "reden": None}


def verrijk(vestiging: dict, ref: dict) -> dict:
    """Een kopie van `vestiging` waarin elk voorschrift `aquo` (en zo nodig `aquo_status`)
    draagt, volgens de sentinel die `toezicht.signalen` verwacht:

    - een naam die in `ref["geldig"]` staat krijgt `aquo` = die code, zonder `aquo_status` --
      dezelfde vorm als een handmatig geschreven testvoorschrift met een geldige code;
    - een naam die alleen in `ref["vervallen"]` staat krijgt `aquo` = de ingetrokken code zelf
      én `aquo_status: "Vervallen"`, voor `regel_vervallen_code`;
    - een naam die in geen van beide voorkomt krijgt `aquo: None` -- aanwezig én `None`, want er
      is wél gezocht, alleen zonder resultaat. Dat is precies de sentinel die
      `regel_niet_in_referentie` nodig heeft (`v.get("aquo", _NIET_OPGEZOCHT) is None`): een
      ontbrekende sleutel `aquo` betekent in die regel "niet opgezocht", dus deze functie mag de
      sleutel nooit weglaten.

    Zonder beschikbare referentie (`ref["beschikbaar"]` onwaar) blijft `vestiging` onaangeroerd:
    er is dan niet gezocht, en `aquo` moet dus afwezig blijven -- niet `None`."""
    if not ref.get("beschikbaar"):
        return vestiging
    geldig = ref.get("geldig") or {}
    vervallen = ref.get("vervallen") or {}

    nieuwe_voorschriften = []
    for v in vestiging.get("voorschriften") or []:
        naam = (v.get("parameter") or "").strip().lower()
        nieuw = dict(v)
        nieuw.pop("aquo_status", None)
        if naam in geldig:
            nieuw["aquo"] = geldig[naam]
        elif naam in vervallen:
            nieuw["aquo"] = vervallen[naam]
            nieuw["aquo_status"] = "Vervallen"
        else:
            nieuw["aquo"] = None
        nieuwe_voorschriften.append(nieuw)
    return {**vestiging, "voorschriften": nieuwe_voorschriften}


def register_codes(vestigingen: list[dict]) -> set[str]:
    """Elke Aquo-code die ergens in het register voorkomt -- de bouwsteen die
    `signalen.regel_stof_buiten_register` nodig heeft (`context["register_codes"]`).

    Alleen echte codes tellen mee: een voorschrift met `aquo: None` (niet gevonden) draagt geen
    code om te verzamelen, zie de sentinel in `verrijk()`."""
    codes: set[str] = set()
    for vestiging in vestigingen or []:
        for v in vestiging.get("voorschriften") or []:
            code = v.get("aquo")
            if code:
                codes.add(code)
    return codes
