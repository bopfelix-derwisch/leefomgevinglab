"""De inspectiebijlage: één `.xlsx` met een blad per signaal en de bronrijen eronder.

Een werkblad is wat er in de praktijk met een inspecteur mee de deur uit gaat, en het is ook de
vorm die een signaal navraagbaar houdt: elke regel in het dossier staat erin terug als een rij met
haar bron (plan, §2 deel C). `openpyxl` is hier een directe import, geen voorwaardelijke --
het bleek bij het bouwen van deze module al in de venv aanwezig (transitief, waarschijnlijk via
`python-pptx`), maar staat voor de duidelijkheid nu ook met zijn eigen regel in
`requirements.txt`.

**Eén blad per signaal, dus botsende namen zijn de normale situatie, geen randgeval.** Signaal 1
(`geen_onafhankelijke_meting`) kan per Aquo-code herhalen binnen één vestiging (taak 2) en draagt
dan tweemaal dezelfde `signaal`-tekst ("geen onafhankelijke meting"). Excel staat bovendien maar
31 tekens toe in een bladnaam en verbiedt `: \\ / ? * [ ]`. De oplossing hier is geen poging om
elke naam uniek te *houden* via de tekst zelf (afknotten kan twee verschillende lange namen
alsnog laten samenvallen) maar een volgnummer vooraan dat de uniciteit garandeert ongeacht wat er
na afknotten overblijft: twee signalen hebben nooit hetzelfde volgnummer.
"""
from pathlib import Path

from openpyxl import Workbook

from leefomgevinglab.usecases.toezicht import signalen as signalen_mod

_MAX_SHEETNAAM = 31
_ONGELDIGE_TEKENS = set(":\\/?*[]")


def _sheetnaam(signaal: dict, index: int) -> str:
    """Een geldige, gegarandeerd unieke bladnaam voor signaal nr. `index` (0-based)."""
    basis = "".join(ch for ch in (signaal.get("signaal") or "onbenoemd")
                     if ch not in _ONGELDIGE_TEKENS)
    voorvoegsel = f"{index + 1} "
    ruimte = max(_MAX_SHEETNAAM - len(voorvoegsel), 0)
    return (voorvoegsel + basis[:ruimte].strip())[:_MAX_SHEETNAAM]


def _cel(waarde):
    """Openpyxl schrijft geen lijsten of dicts als celwaarde (bv. een voorschrift-coördinaat
    `rd: [x, y]`) -- die worden hier leesbaar als tekst weggeschreven in plaats van de hele
    export te laten crashen op één afwijkend veld."""
    if waarde is None or isinstance(waarde, (str, int, float, bool)):
        return waarde
    return str(waarde)


def _schrijf_blad(ws, signaal: dict) -> None:
    regel_id = signaal.get("regel")
    _, omvang_betekenis = signalen_mod.DREMPELS.get(regel_id, (None, "onbekende regel"))
    for rij in (
        ("signaal", signaal.get("signaal")),
        ("zwaarte", signaal.get("zwaarte")),
        ("omvang", signaal.get("omvang")),
        ("omvang betekent", omvang_betekenis),
        ("grondslag", signaal.get("grondslag")),
        ("zekerheid", signaal.get("zekerheid")),
        ("wat te doen", signaal.get("wat_te_doen")),
    ):
        ws.append(rij)
    # `waarom` (taak 7, `uitleg.waarom`) is optioneel: zonder bron in de afgebakende bronnenset
    # ontbreekt het veld, en dan schrijft dit blad er ook geen rij voor -- een lege "waarom"-rij
    # zou een poging suggereren die niets opleverde (zelfde afspraak als het veld zelf, zie
    # `runner.tool_uitleg_genereren`).
    if signaal.get("waarom"):
        ws.append(("waarom", signaal["waarom"]))
        # Fix-ronde 2, bevinding A: de vindplaats moet overal meereizen waar `waarom` ook staat
        # -- het werkblad is wat een inspecteur in de praktijk mee de deur uit neemt (zie de
        # moduledocstring), dus een uitleg zonder bron hier is even "erger dan geen uitleg" als
        # op de pagina.
        vindplaatsen = signaal.get("waarom_vindplaatsen") or []
        if vindplaatsen:
            ws.append(("vindplaats", "; ".join(vindplaatsen)))
    ws.append([])

    bewijs = signaal.get("bewijs") or []
    if not bewijs:
        ws.append(["Geen afzonderlijke bronrijen voor dit signaal -- het geldt voor de hele "
                    "vestiging (zie 'omvang betekent' hierboven)."])
        return

    # Niet elke bewijsrij heeft dezelfde velden (een voorschrift, een overschrijding en een
    # ontbrekend-veld-markering zien er alle drie anders uit) -- de kolomkop volgt daarom de
    # unie van alle sleutels die in dít signaal voorkomen, niet een vast schema.
    kolommen = sorted({sleutel for rij in bewijs for sleutel in rij.keys()})
    ws.append(["bewijs"] + kolommen)
    for rij in bewijs:
        ws.append([""] + [_cel(rij.get(k)) for k in kolommen])


def schrijf(dossier: dict, pad: str) -> str:
    """Schrijft `dossier` als `.xlsx` naar `pad` en geeft `pad` (als string) terug.

    Eén blad per signaal in `dossier["signalen"]`, in dezelfde volgorde (dus al gerangschikt op
    zwaarte). Een dossier zonder signalen krijgt toch een leesbaar bestand met één blad dat dat
    zegt -- een workbook zonder enig blad bestaat niet in het formaat."""
    wb = Workbook()
    wb.remove(wb.active)

    signalen_lijst = dossier.get("signalen") or []
    for index, signaal in enumerate(signalen_lijst):
        ws = wb.create_sheet(title=_sheetnaam(signaal, index))
        _schrijf_blad(ws, signaal)

    if not signalen_lijst:
        ws = wb.create_sheet(title="Geen signalen")
        ws.append(["Dit dossier bevat geen signalen voor deze vestiging."])

    Path(pad).parent.mkdir(parents=True, exist_ok=True)
    wb.save(pad)
    return str(pad)
