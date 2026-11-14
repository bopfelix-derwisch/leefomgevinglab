"""De terugkoppeling -- een oordeel per antwoord opslaan, en de tien regels rangschikken op
"bleek dit in de praktijk te kloppen?" (plan, §5.6).

Vier oordelen: `bruikbaar`, `niet_bruikbaar`, `signaal_was_juist`, `signaal_was_onjuist`. Elke
registratie draagt de vestiging, het signaal (de regel-id) en de **versie van de regel** die dat
signaal destijds opleverde -- zonder dat laatste is een oordeel over een jaar niet te plaatsen: de
regel kan intussen zijn bijgesteld (een drempel, een omschrijving, de rekenlogica zelf) en dan
zegt "dit signaal was onjuist" niets meer over de regel van vandaag.

**Wat "versie" hier betekent (de tweede open vraag uit de opdracht).** Een hash (sha256, de
eerste 12 hex-tekens) over drie dingen: de regel-id, haar rij in `signalen.DREMPELS` (drempel +
omschrijving van de omvang) en de brontekst van de regelfunctie zelf (`inspect.getsource`). Geen
handmatig bijgehouden versienummer.

Waarom een hash en geen nummer: een nummer dat niemand verhoogt, is een stille leugen -- dit lab
heeft die fout al een keer gemaakt (documentatie die beweerde dat "Zwevende stof" op een geldige
Aquo-code koppelde, terwijl die code ingetrokken was; zie `aquo.py`). Een hash kan niet vergeten
worden: hij wordt bij elke registratie opnieuw berekend uit de code van dat moment, niet uit een
veld dat iemand had moeten bijwerken.

**Het eerlijke nadeel van die keuze, en waarom dat nadeel het veiligere is.** Een broncode-hash
reageert op *alles*: een docstring bijschaven, een variabele hernoemen, een commentaarregel
toevoegen -- geen van drieën verandert wat de regel oplevert, en toch krijgt de regel een nieuwe
versie. Twee inhoudelijk identieke beoordelingen kunnen dus met een andere versie-ID
geregistreerd staan, en een rangschikking die strikt op versie splitst verliest daarmee
vergelijkbaarheid die zij niet had moeten verliezen.

Het alternatief -- een handmatig nummer dat alleen omhoog gaat als iemand eraan denkt -- heeft het
omgekeerde en ernstigere faalpatroon: een bugfix in de rekenlogica die niemand als "nieuwe versie"
markeert, laat een beoordeling van vóór de fix stilzwijgend meetellen na de fix, en dan vergelijk
je twee regels die niet meer dezelfde zijn zonder dat ergens te zien. Over-invalidatie (de hash)
is een zichtbare, herstelbare fout: je verzamelt opnieuw. Onder-invalidatie (het nummer) is een
stille fout: twee verschillende regels delen een versie-ID en niemand merkt het tot iemand de
code naast de data legt. Dat tweede is hier de ergere uitkomst, dus de hash wint.

**Geen online leren (plan, §10).** Deze module stuurt geen regel bij -- zij telt alleen om.
`rangschikking()` levert een leesbaar overzicht, geen wijziging aan `signalen.py`. Een regel
verandert uitsluitend door een commit met een eigen test, zoals elke andere regel in dit lab.

**De cirkel is met open data niet te sluiten (plan, §5.6/§11.7).** Of een signaal in de praktijk
klopte, weet alleen de inspecteur die is gaan kijken. Deze module bouwt de plek waar die uitkomst
instroomt (`registreer()`) en laat zien wanneer die plek leeg is (`rangschikking()`'s
`"status": "geen terugkoppeling"`) -- zichtbaar leeg is zelf de bevinding, niet een fout om te
verbergen.
"""
import hashlib
import inspect
import json
import time
from pathlib import Path

from leefomgevinglab.usecases.toezicht import signalen as signalen_mod

OORDELEN = ("bruikbaar", "niet_bruikbaar", "signaal_was_juist", "signaal_was_onjuist")

_REGEL_BIJ_ID = {regel.id: regel for regel in signalen_mod.REGELS}


class OnbekendOordeel(Exception):
    """Een oordeel buiten `OORDELEN` -- een tikfout moet hier breken, niet stil een vijfde
    categorie aanmaken die `rangschikking()` straks niet herkent en dus niet meetelt."""


class OnbekendeRegel(Exception):
    """Een regel-id die niet in `signalen.REGELS` voorkomt -- er is dan niets om een versie van
    te berekenen, en zwijgend een lege versie teruggeven zou een oordeel aan niets vastmaken."""


class RegelversieNietTeBepalen(Exception):
    """De brontekst van de regelfunctie is niet op te halen (`inspect.getsource` faalt met een
    `OSError` of `TypeError`) -- bijvoorbeeld een bevroren of verpakte deployment zonder
    `.py`-bestanden, of een dynamisch gebouwde functie zonder brontekst. Fix-ronde 1, bevinding 4:
    stil terugvallen op een hash zonder brontekst (bv. alleen regel-id + kop + drempel) zou precies
    de onder-invalidatie reintroduceren die de moduledocstring afwijst -- twee inhoudelijk
    verschillende regels zouden dan een gelijke versie kunnen delen zodra hun brontekst allebei
    onleesbaar is. Beter luid falen, net als `OnbekendeTool`/`OnbekendeRegel` elders in dit lab,
    dan een onbetrouwbare versie aan een beoordeling vastmaken."""


def regelversie(regel_id: str) -> str:
    """De versie van deze regel, nu -- zie de moduledocstring voor wat dat betekent en welk
    nadeel die keuze bewust accepteert. Werpt `RegelversieNietTeBepalen` in plaats van een kale
    `OSError`/`TypeError` als `inspect.getsource` faalt (fix-ronde 1, bevinding 4) -- een
    genoemde fout, zoals de rest van dit lab die ook geeft, in plaats van een toevallige
    Python-uitzondering die een aanroeper niet op naam kan opvangen."""
    if regel_id not in _REGEL_BIJ_ID:
        raise OnbekendeRegel(f"onbekende regel '{regel_id}' (niet in signalen.REGELS)")
    regel = _REGEL_BIJ_ID[regel_id]
    drempel = signalen_mod.DREMPELS.get(regel_id)
    try:
        bron = inspect.getsource(regel.functie)
    except (OSError, TypeError) as exc:
        raise RegelversieNietTeBepalen(
            f"de brontekst van regel '{regel_id}' is niet op te halen ({type(exc).__name__}); "
            "zonder brontekst is er geen betrouwbare versie te berekenen"
        ) from exc
    payload = "|".join((regel.id, regel.kop, repr(drempel), bron))
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()[:12]


def registreer(vestiging_id: str, regel_id: str, oordeel: str, *,
               opmerking: str | None = None, nu: float | None = None) -> dict:
    """Eén beoordeling, met de regelversie van dit moment erbij. Geeft de registratie terug als
    gewoon dict -- opslag is een losse stap (`opslaan`), zodat een aanroeper (bv. de runner-tool)
    zelf kan beslissen of en wanneer hij wegschrijft."""
    if oordeel not in OORDELEN:
        raise OnbekendOordeel(f"onbekend oordeel '{oordeel}' (verwacht een van {OORDELEN})")
    return {
        "vestiging_id": vestiging_id,
        "regel_id": regel_id,
        "regelversie": regelversie(regel_id),
        "oordeel": oordeel,
        "opmerking": opmerking,
        "geregistreerd_op": nu if nu is not None else time.time(),
    }


def opslaan(beoordelingen: list[dict], pad: str) -> None:
    """Toevoegen aan een JSONL-bestand op `pad` -- nooit overschrijven. Terugkoppeling komt
    stuk voor stuk binnen, niet als één batch die de vorige vervangt (ander patroon dan
    `rag.store.VectorStore.save`, dat wél een hele store herschrijft -- hier is elke regel een
    eigen, onafhankelijke registratie)."""
    p = Path(pad)
    p.parent.mkdir(parents=True, exist_ok=True)
    with p.open("a", encoding="utf-8") as f:
        for b in beoordelingen:
            f.write(json.dumps(b, ensure_ascii=False) + "\n")


def laden(pad: str) -> list[dict]:
    """Alles wat ooit is opgeslagen -- een leeg bestand (of geen bestand) is geen fout maar de
    normale, lege staat van een terugkoppelplek die nog niemand gebruikt heeft."""
    p = Path(pad)
    if not p.exists():
        return []
    with p.open(encoding="utf-8") as f:
        return [json.loads(regel) for regel in f if regel.strip()]


def rangschikking(beoordelingen: list[dict]) -> list[dict]:
    """Per regel uit `signalen.REGELS`: hoe vaak beoordeeld, en van wat beoordeeld is, hoe vaak
    'juist'. Elke regel komt hier voor, ook zonder enige beoordeling -- met expliciet
    `"status": "geen terugkoppeling"`, in plaats van stil te ontbreken (zie de moduledocstring).

    Sortering: regels met een aandeel-juist eerst (hoog naar laag), dan bij gelijk aandeel de
    meest beoordeelde eerst; regels zonder enig oordeel over juistheid staan achteraan, niet
    vooraan als toevallige "beste" regel."""
    per_regel: dict[str, list[dict]] = {regel.id: [] for regel in signalen_mod.REGELS}
    for b in beoordelingen:
        per_regel.setdefault(b["regel_id"], []).append(b)

    uit = []
    for regel in signalen_mod.REGELS:
        rijen = per_regel.get(regel.id, [])
        juist = sum(1 for r in rijen if r["oordeel"] == "signaal_was_juist")
        onjuist = sum(1 for r in rijen if r["oordeel"] == "signaal_was_onjuist")
        bruikbaar = sum(1 for r in rijen if r["oordeel"] == "bruikbaar")
        niet_bruikbaar = sum(1 for r in rijen if r["oordeel"] == "niet_bruikbaar")
        beoordeeld_op_juistheid = juist + onjuist
        uit.append({
            "regel_id": regel.id,
            "signaal": regel.kop,
            "aantal_beoordelingen": len(rijen),
            "juist": juist,
            "onjuist": onjuist,
            "bruikbaar": bruikbaar,
            "niet_bruikbaar": niet_bruikbaar,
            "aandeel_juist": (juist / beoordeeld_op_juistheid) if beoordeeld_op_juistheid else None,
            "status": "beoordeeld" if rijen else "geen terugkoppeling",
            "versies": sorted({r["regelversie"] for r in rijen}),
        })
    uit.sort(key=lambda r: (r["aandeel_juist"] is None, -(r["aandeel_juist"] or 0.0),
                            -r["aantal_beoordelingen"]))
    return uit
