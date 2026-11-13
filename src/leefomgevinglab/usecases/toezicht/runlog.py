"""De runlog -- procesherkomst als onderdeel van het product (taak 6b).

`signalen.py` maakt de data-herkomst van een bewering navraagbaar (`grondslag`, `zekerheid`,
getest in `test_toezicht_dossier.py`). Wat tot nu toe ontbrak is de herkomst van het *proces*
zelf: welke agent heeft wat gedaan, met welke tool, hoeveel rijen erin en eruit, hoe lang duurde
het, en kwam daar een taalmodel bij te pas? Zonder die vraag te kunnen beantwoorden is de
transparantie die de rest van deze use-case belooft (herkomst per veld, geen stille aanname)
maar half waar: de dáta is navraagbaar, het proces dat de data opleverde niet.

Deze module is bewust klein en dom: een platte lijst stappen, elk een gewoon dict, in de volgorde
waarin ze gebeurden. Geen eigen opslag, geen eigen validatie van wat een "agent" of "tool" mag
zijn -- dat is de taak van `runner.py`, die deze klasse vult. `Runlog` registreert alleen wat hem
wordt aangeleverd en nummert de stappen.

**Drie stappen zijn uitdrukkelijk geen gewone toolaanroep, en krijgen daarom een eigen vlag in
plaats van een losse bewering erover:**

- `uitgezet=True` -- deze agent stond uit (`invoer["uit"]`); er is helemaal geen tool aangeroepen,
  `tool` blijft `None`. Dat onderscheidt een *bewuste* uitschakeling (plan, demand (d)) van een
  tool die simpelweg niet bestaat.
- `niet_beschikbaar=True` -- de tool is verklaard voor deze agent (staat in de YAML) en bestaat
  ook als naam in `runner.GEPLAND`, maar is nog niet gebouwd (bv. `uitlegger` vóór taak 7). `tool`
  draagt hier wél de naam: er *is* een poging, alleen geen uitvoering. Dit is de luide, expliciete
  afhandeling die de opdracht vraagt in plaats van een stille `continue`.
- Een normale stap draagt geen van beide vlaggen (`False`), en `tool` is de naam van de tool die
  echt is aangeroepen.

**Geen getal wordt getypt.** `rijen_in`/`rijen_uit`/`duur` komen uit de aanroeper (`runner.py`
meet ze); deze module plakt er alleen een volgnummer bij en telt ze om in `telling()` -- zij
verzint zelf geen enkel cijfer.
"""
from typing import Any


class Runlog:
    """Eén run, van de eerste tot de laatste stap. `als_gegeven()` is de vorm die zowel de tests
    als de pagina (taak 8) lezen: een platte lijst dicts, geen eigen klasse naar buiten toe."""

    def __init__(self) -> None:
        self._stappen: list[dict[str, Any]] = []

    def stap(self, agent: str, taak: str, tool: str | None, rijen_in: int, rijen_uit: int,
              llm: bool, duur: float | None = None, args: dict | None = None,
              uitgezet: bool = False, niet_beschikbaar: bool = False) -> None:
        """Registreert één stap. `nr` is het volgnummer (1-based, in registratievolgorde) --
        daarmee kan een signaal in `dossier.py` naar precies deze stap terugwijzen zonder de
        inhoud van de stap zelf te dupliceren."""
        self._stappen.append({
            "nr": len(self._stappen) + 1,
            "agent": agent,
            "taak": taak,
            "tool": tool,
            "args": args or {},
            "rijen_in": rijen_in,
            "rijen_uit": rijen_uit,
            "llm": llm,
            "duur": duur,
            "uitgezet": uitgezet,
            "niet_beschikbaar": niet_beschikbaar,
        })

    def als_gegeven(self) -> list[dict]:
        """Een kopie van de stappenlijst -- de aanroeper mag de registratie zelf niet kunnen
        wijzigen door aan de teruggegeven lijst te sleutelen."""
        return [dict(s) for s in self._stappen]

    def telling(self) -> dict:
        """Uitsluitend afgeleide getallen, net als `dossier._telling` -- zelfde huisregel, hier
        toegepast op het proces in plaats van op de signalen."""
        return {
            "aantal_stappen": len(self._stappen),
            "met_taalmodel": sum(1 for s in self._stappen if s["llm"]),
            "uitgezet": sum(1 for s in self._stappen if s["uitgezet"]),
            "niet_beschikbaar": sum(1 for s in self._stappen if s["niet_beschikbaar"]),
            "totale_duur": sum(s["duur"] for s in self._stappen if s["duur"] is not None),
        }
