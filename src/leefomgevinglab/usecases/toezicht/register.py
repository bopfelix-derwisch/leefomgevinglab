"""De grens waarop het Atlas-register `toezicht` binnenkomt -- twee dingen gebeuren hier, en
nergens anders in dit package:

1. **ontdubbelen** van letterlijk herhaalde voorschriften binnen één vestiging
   (`dedupliceer_voorschriften`/`voorbereid`);
2. een **identiteit per vestiging die altijd uniek is** (`identiteiten`), want `locatiecode` is
   dat niet.

Beide horen bij deze grens (`api._toezicht_register`, `api_toezicht_vestigingen`,
`api_toezicht_dossier`), niet verspreid over de tien signaalregels of de route zelf: ontdubbelen
in `signalen.py` zou het tien keer moeten doen, en de identiteit hoort niet bij een los signaal
maar bij de vestiging als geheel.
"""
from collections import Counter


def _norm(s) -> str:
    return (s or "").strip().lower()


def dedupliceer_voorschriften(vestiging: dict) -> dict:
    """Eén vestiging met haar `voorschriften`-lijst ontdubbeld: een rij die in parameter, waarde,
    eenheid én bemonsteringswijze gelijk is aan een eerdere rij in dezelfde vestiging telt maar
    één keer. Het meetpunt (`rd`) telt niet mee in de sleutel -- dat is coördinaatmetadata van de
    meting, geen deel van de eis zelf, en twee anders identieke rijen met een licht andere/lege
    coördinaat zijn in de praktijk dezelfde eis tweemaal opgeslagen (live gemeten: zonder `rd` in
    de sleutel 132 van de 782 voorschriften een duplicaat, mét `rd` maar 130 -- de twee gevallen
    waarin alleen de coördinaat verschilt, zijn juist de duplicaten die hier bedoeld worden).

    Eindreview, bevinding 3: zonder dit telt elk getal op de pagina de brontabel, niet de
    werkelijke eisen -- CORUSNB's eerste vergunning draagt 118 rijen waarvan maar 46 uniek, dus
    "118 voorschriften schrijven een bemonsteringsregime voor" was voor 72 van die 118 een
    letterlijke herhaling van een rij die al meetelde.

    **Waarom niet `gebruiksruimte.atlas_register._dedupe` hergebruikt.** Die functie ontdubbelt op
    `(parameter, waarde, eenheid)` -- genoeg voor haar eigen vraag ("hoeveel vracht staat hier al
    vergund"), waar het bemonsteringsregime niet toe doet: twee rijen met hetzelfde regime maar een
    andere bemonsteringswijze leveren daar toch hetzelfde vrachtgetal op. Voor `toezicht` doet het
    regime er wél toe -- signaal 9 (`niet_regime_zuiver`) gaat juist over wélk regime een
    voorschrift draagt, en twee voorschriften met dezelfde parameter/waarde/eenheid maar een ander
    regime (bv. een steekmonster-eis naast een 24-uursverzamelmonster-eis voor dezelfde stof) zijn
    dan geen duplicaat maar twee verschillende eisen. Ontdubbelen op die drie velden alleen zou ze
    alsnog samenvoegen en het bewijs van dat signaal stilzwijgend verkleinen. Vandaar een eigen,
    strengere sleutel hier, met het bemonsteringsregime erbij."""
    gezien, uniek = set(), []
    for v in vestiging.get("voorschriften") or []:
        sleutel = (_norm(v.get("parameter")), v.get("waarde"), _norm(v.get("eenheid")),
                   _norm(v.get("bemonstering")))
        if sleutel in gezien:
            continue
        gezien.add(sleutel)
        uniek.append(v)
    return {**vestiging, "voorschriften": uniek}


def voorbereid(register: list[dict]) -> list[dict]:
    """Het hele register zoals `toezicht` het verder gebruikt: elke vestiging ontdubbeld. Eén
    keer hier, bij de grens waarop het register binnenkomt, niet in elk van de tien regels
    afzonderlijk."""
    return [dedupliceer_voorschriften(v) for v in register]


def identiteiten(register: list[dict]) -> list[str]:
    """Een gegarandeerd unieke identiteit per positie in `register` -- `locatiecode` is dat niet.

    Eindreview, bevinding 1: live dekken 8 van de 69 locatiecodes twee vergunningen van dezelfde
    vestiging (bv. CORUSNB: Tata Steel Nederland Tubes B.V. draagt zowel RWS-2015/19557, 118
    voorschriften, als RWS/DNB-2012/5083, 12 voorschriften, onder dezelfde locatiecode). Een
    lookup op `locatiecode` alleen vindt dan altijd de eerste van de twee en maakt de andere --
    bij Jan de Poorter B.V. is dat de grótere vergunning -- onbereikbaar, met elk signaal dat zij
    zou opleveren.

    Er is geen gegarandeerd unieke sleutel in de bron zelf (zie de taakbrief): `kenmerk` is leeg
    bij 6 van de 69 vestigingen, en geen van beide velden draagt een documentgarantie. Daarom een
    gelaagde afleiding, elke laag alleen ingeschakeld als de laag erboven niet al uniek is:

      1. `locatiecode` alleen, zolang geen andere vestiging in dit register dezelfde locatiecode
         draagt;
      2. anders `locatiecode` + `kenmerk` -- live (2026-11) altijd uniek zodra laag 1 het niet is:
         geen van de acht dubbele locatiecodes deelt ook nog hetzelfde kenmerk (of hetzelfde
         ontbrekende kenmerk);
      3. blijft het dan nóg niet uniek (geen van de twee velden garandeert dat voor toekomstige
         data) -- een volgnummer binnen die groep, zodat deze functie hoe dan ook nooit twee keer
         dezelfde identiteit teruggeeft. Dat volgnummer is dan geen leesbare identiteit meer, maar
         wel een unieke -- de garantie die deze functie moet geven, staat boven leesbaarheid.

    De identiteiten zijn alleen uniek **binnen deze aanroep** van `register` (dezelfde lijst,
    dezelfde volgorde) -- geen stabiele sleutel die een eerdere pageload overleeft. Dat is hier
    genoeg: `/api/toezicht/vestigingen` en `/api/toezicht/dossier` werken allebei op hetzelfde,
    kort daarna opnieuw opgehaalde (en door de connector gecachete) register."""
    locatiecode_telling = Counter(v.get("locatiecode") for v in register)
    sleutel_telling = Counter((v.get("locatiecode"), v.get("kenmerk")) for v in register)
    volgnummer: dict[tuple, int] = {}
    uit = []
    for v in register:
        lc = v.get("locatiecode")
        if locatiecode_telling[lc] <= 1:
            uit.append(lc)
            continue
        sleutel = (lc, v.get("kenmerk"))
        if sleutel_telling[sleutel] <= 1:
            uit.append(f"{lc}::{v.get('kenmerk') or ''}")
            continue
        n = volgnummer.get(sleutel, 0)
        volgnummer[sleutel] = n + 1
        uit.append(f"{lc}::{v.get('kenmerk') or ''}::{n}")
    return uit
