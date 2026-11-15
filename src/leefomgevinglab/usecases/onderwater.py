"""De technische anatomie van `/wasstraat` en `/toezicht` -- wat er onder water gebeurt.

**Waarom deze pagina bestaat.** In dit lab is de gegevens*herkomst* zichtbaar (elke pagina noemt
haar bronnen) maar de *bewerking* niet: welke regels vuren waarop, met welke drempel, welke agent
doet wat, waar mag een taalmodel bij komen, en welke configuratiesleutel bepaalt het. Dat staat
verspreid over YAML, een signaalcatalogus, een runner en twee routes. Deze module brengt het bij
elkaar en legt het uit.

**De valkuil van zo'n pagina, en wat deze module daartegen doet.** Een anatomie die haar getallen
intypt gaat liegen zodra de code verschuift -- en juist hier is dat onzichtbaar, want de lezer
heeft niets anders om het tegen te houden. Alles wat te tellen valt wordt daarom **afgeleid**:
de regels uit `signalen.REGELS`, hun drempel en de betekenis van `omvang` uit `signalen.DREMPELS`,
de twee assen uit `Regel.laag` en `signalen.is_voorbehoud`, en de agents en taken uit de YAML die
de runner zelf leest. De teksten in `ONDERDELEN` en `REGELUITLEG` dragen daarom geen aantallen;
`tests/test_onderwater.py` scant daarop.

**Twee assen, en waarom ze niet samengevoegd mogen worden.** `Regel.laag` scheidt papier (de
vergunning klopt niet tegen zichzelf) van werkelijkheid (er is meetdata of stroomrichting nodig)
en bepaalt op wélke pagina een regel landt. `is_voorbehoud` (drempel >= `ALTIJD_LAAG`) scheidt
binnen het papier de bevinding van het voorbehoud. De eindreview van november 2026 liet zien wat
het kost om die twee te verwarren: twee register-brede voorbehouden stonden als bevinding in de
lijst, met een reparatie-instructie die de vergunningverlener niet kon uitvoeren, en
`wasstraat.op_orde` was daardoor dode code.

**Wat deze module expliciet NIET doet.** Zij dumpt geen configuratiesectie. `core/config.yaml`
draagt ook een `submit_token` en api-headernamen, en een publieke pagina die een hele sectie
uitklapt neemt die mee. `CONFIGSLEUTELS` is daarom een witte lijst van sleutels die deze twee
routes werkelijk lezen. En geen enkel absoluut serverpad verlaat deze module: paden worden
afgekort tot hun laatste twee segmenten, dezelfde regel die de eindreview op
`/api/wasstraat/pijplijn` oplegde.
"""
from leefomgevinglab.usecases.toezicht import pijplijn as pijplijn_mod
from leefomgevinglab.usecases.toezicht import signalen as signalen_mod

#: De paden waarop de twee pagina's staan -- één plek, zodat een regel niet naar een route kan
#: wijzen die niet bestaat.
PAD_WASSTRAAT = "/wasstraat"
PAD_TOEZICHT = "/toezicht"


def _kort_pad(pad: str | None) -> str | None:
    """Een pad afgekort tot zijn laatste twee segmenten. Een absoluut serverpad hoort niet op een
    publieke pagina (eindreview, kleinere bevinding 7: `/api/wasstraat/pijplijn` publiceerde
    `/mnt/nvme/workspaces/...`), en deze pagina staat vól paden. Wat de lezer nodig heeft is
    *welk bestand*, niet waar de schijf gemonteerd is."""
    if not pad:
        return None
    delen = [d for d in str(pad).replace("\\", "/").split("/") if d]
    return "/".join(delen[-2:]) if delen else None


# -- Wat elk onderdeel is, waarom het zo is, en waar het staat ----------------------------------
#
# `waarom` is het veld dat deze pagina onderscheidt van een gegenereerde API-referentie: een
# onderdeel zonder reden is documentatie die niemand helpt controleren. Geen aantallen in deze
# teksten -- die komen uit de afgeleide velden ernaast.

ONDERDELEN = [
    {
        "kop": "Twee lezers, één regelset",
        "wat": "Dezelfde signaalregels op hetzelfde Maas-lozingenregister, maar verdeeld over "
               "twee pagina's: de vergunningverlener krijgt wat er aan de vergunning zelf moet "
               "rechtkomen, de toezichthouder krijgt waar hij moet gaan kijken.",
        "waarom": "De twee hebben een andere vraag, en een gat in de data betekent voor hen iets "
                  "anders. Voor de vergunningverlener is een ontbrekend veld werk; voor de "
                  "toezichthouder is het zelf een signaal. Eén pagina voor beiden werd een lijst "
                  "waarin geen van de twee zijn eigen werk terugvond.",
        "waar": "usecases/wasstraat/dossier.py en usecases/toezicht/weergave.py -- twee filters "
                "op één dossier, beide lezend van Regel.laag.",
    },
    {
        "kop": "De regels zijn deterministisch, geen taalmodel",
        "wat": "Elke signaalregel is een gewone functie die rekent, telt of vergelijkt, met een "
               "eigen test. Een taalmodel komt er niet aan te pas.",
        "waarom": "Een signaal dat een model 'zag' is niet navraagbaar: je kunt niet reproduceren "
                  "waarom het er stond, en een toezichthouder kan er niets mee ter plaatse. Een "
                  "regel die vuurt is een regel die vuurt. Het model mag alleen uitleggen, en "
                  "zwijgt zonder benoemde vindplaats.",
        "waar": "usecases/toezicht/signalen.py -- de catalogus; usecases/toezicht/uitleg.py -- "
                "de uitleg erna.",
    },
    {
        "kop": "De agents staan in CrewAI-vorm, en dat is het punt",
        "wat": "Rol, doel, achtergrond, tools en eventueel een taalmodel per agent, in YAML die "
               "de runner zelf leest. Niet een eigen configuratietaal die dit lab erbij verzint.",
        "waarom": "Deze vorm is al gedocumenteerd en te controleren. En belangrijker: de grens "
                  "'agents bepalen geen signalen' staat erin als een afwezig veld -- een agent "
                  "zonder llm-sleutel krijgt er nooit een, ook niet als de run er een meekrijgt. "
                  "Een afwezigheid is te controleren; een belofte in proza niet. CrewAI zelf "
                  "draait hier aantoonbaar maar past niet in deze venv: het eist een oudere "
                  "pydantic dan dit project gebruikt.",
        "waar": "usecases/toezicht/config/agents.yaml en tasks.yaml; "
                "usecases/toezicht/runner.py leest de afwezigheid.",
    },
    {
        "kop": "Mogen en doen zijn twee velden",
        "wat": "Of een agent een taalmodel mag krijgen staat in de configuratie; of er in een run "
               "werkelijk een is aangeroepen staat per stap in de runlog, gemeten met een "
               "tellende omhulling om het model heen.",
        "waarom": "Deze twee liepen eerder door elkaar: de log schreef 'taalmodel' zodra een "
                  "agent er een mócht krijgen, ook als zijn tool het nooit aanriep. Dat maakte "
                  "de belangrijkste belofte van dit lab onmeetbaar. De dossierroutes geven geen "
                  "model door, dus de uitlegger mag wel en doet niet -- en dat verschil hoort "
                  "leesbaar te zijn in plaats van weggepoetst.",
        "waar": "usecases/toezicht/pijplijn.py (mag_llm) tegenover "
                "usecases/toezicht/runlog.py (llm per stap).",
    },
    {
        "kop": "Alles leesbaar, niets schrijfbaar",
        "wat": "Beide pagina's en al hun eindpunten antwoorden alleen op GET. De enige invoer van "
               "een bezoeker is de gekozen vergunning, en die wordt uitsluitend gebruikt om een "
               "post in het register op te zoeken.",
        "waarom": "De configuratie zichtbaar maken is iets anders dan haar laten wijzigen. Wie de "
                  "agents wil veranderen, verandert de YAML in de repo -- dan is de wijziging "
                  "ook terug te vinden in de geschiedenis in plaats van ongezien ingevoerd.",
        "waar": "De routes in geluidsmeter/api.py; de tests eisen 405 en niet 404-of-405, "
                "want met 404 erbij slaagt zo'n test ook als de route helemaal weg is.",
    },
    {
        "kop": "De runlog is een meting, geen verslag",
        "wat": "Per stap: welke agent, welke taak, welke tool, hoeveel rijen erin en eruit, hoe "
               "lang, en of er werkelijk een taalmodel is aangeroepen.",
        "waarom": "De aantallen per stap zijn navraagbaar; een optelling erover was dat niet, "
                  "want de stappen tellen ongelijksoortige dingen -- voorschriften, signalen, "
                  "dossiers, uitleggen. Juist het interessante getal verdween dan in de som.",
        "waar": "usecases/toezicht/runlog.py; de samenvatting in "
                "usecases/wasstraat/dossier.py.",
    },
]

# -- Per regel: waarom zij bestaat. Eén zin, geen aantallen (die staan afgeleid ernaast). -------

REGELUITLEG = {
    "geen_onafhankelijke_meting":
        "Een stof die vergund is maar nergens in het landelijke meetnet gemeten wordt, is een "
        "grenswaarde zonder onafhankelijke controle -- een feit over het meetnet, niet over de "
        "pen van de vergunningverlener.",
    "vervallen_code":
        "Een voorschrift op een Aquo-code die is ingetrokken, koppelt niet meer aan een meting. "
        "De bron biedt soms geen opvolger, en dan is dat zelf de bevinding.",
    "niet_in_referentie":
        "Een parameternaam die in de Aquo-domeintabel niet voorkomt, is niet machinaal te "
        "koppelen; een latere vergelijking met een meting valt dan stil.",
    "meerdere_grenswaarden":
        "Dezelfde stof met meer dan één grenswaarde in dezelfde vergunning: dan is niet bepaald "
        "welke geldt. Vergeleken wordt binnen dezelfde eenheid, want anders levert een verschil "
        "in tijdseenheid een verhouding op die niets betekent.",
    "vracht_onbepaald":
        "Een grenswaarde als concentratie zonder debietvoorschrift laat de vracht onbepaald: "
        "hoeveel er per jaar uit mag, volgt er niet uit.",
    "norm_overschreden_bovenstrooms":
        "Een stof die benedenstrooms boven de norm is gemeten, met een lozer van die stof "
        "bovenstrooms. Een aanwijzing waar te kijken, nooit een vaststelling -- en binnen één "
        "waterlichaam is de richting niet vastgesteld.",
    "stof_buiten_register":
        "Een stof die gemeten wordt en boven de norm komt, maar in geen enkele vergunning in het "
        "register voorkomt: dan verklaart het register haar niet.",
    "vergunning_niet_te_vinden":
        "Ontbrekende identificerende velden maken de vergunning zelf niet terug te vinden, en "
        "daarmee elke bevinding erover onnavolgbaar.",
    "niet_regime_zuiver":
        "De vergunning schrijft een bemonsteringsregime voor dat de meting niet meldt, dus een "
        "vergelijking is niet regime-zuiver. Dit geldt zodra een voorschrift een regime draagt, "
        "en is daarom een voorbehoud bij elke vergelijking in plaats van een bevinding.",
    "geen_geldigheidsduur":
        "De bron kent geen geldigheidsperiode per voorschrift, alleen een besluitdatum per "
        "vergunning. Dat tekort zit in het register en niet in een afzonderlijke vergunning.",
}

# -- De bronnen. Houder, bevragingswijze, licentiepositie en waar de code haar leest. -----------

BRONNEN = [
    {
        "naam": "Atlas voor een Schone Maas",
        "houder": "Schone Maaswaterketen (samenwerking van waterbeheerders in het Maasgebied)",
        "hoe": "Live bevraagd op een RD-punt met een ruime straal; de connector cachet het "
               "antwoord zodat niet elke pageview het netwerk op gaat.",
        "licentie": "Publiek toegankelijk maar zonder expliciete licentie -- daarom live "
                    "bevragen met bronvermelding, en de dataset nooit in de repo kopiëren.",
        "waar_in_de_code": "connectors/smwk_atlas.py, via usecases/kmg/service.py",
        "levert": "De vergunningen en hun voorschriften: het register waar alles op rust.",
    },
    {
        "naam": "Aquo-domeintabel Parameter",
        "houder": "Informatiehuis Water (aquo.nl)",
        "hoe": "Als CSV opgehaald en lokaal bewaard; geldige én ingetrokken codes worden "
               "ingelezen, want een ingetrokken code is zelf een bevinding.",
        "licentie": "Open standaard, vrij te gebruiken met bronvermelding.",
        "waar_in_de_code": "usecases/toezicht/aquo.py",
        "levert": "De koppeling van een parameternaam in een vergunning aan een code waarop een "
                  "meting te vinden is.",
    },
    {
        "naam": "KRW-toetsresultaten",
        "houder": "Rijkswaterstaat / Informatiehuis Water",
        "hoe": "Uit het Waterkwaliteitsportaal gehaald en lokaal bewaard; de norm per stof en "
               "meetpunt, met het oordeel erbij.",
        "licentie": "Open data van de rijksoverheid.",
        "waar_in_de_code": "usecases/kmg/doelen.py, ingelezen door de toezichtroutes",
        "levert": "De chemische norm waartegen een meting gelegd wordt -- en waar die ontbreekt, "
                  "staat de meting zonder normoordeel in plaats van tegen een verzonnen norm.",
    },
    {
        "naam": "Waterkwaliteitsportaal (meetwaarden)",
        "houder": "Informatiehuis Water",
        "hoe": "Een grote CSV, lokaal verdicht tot mediaan en maximum per meetpunt en stof. "
               "Handmatige momentopname: er is geen open machine-ingang voor de meetwaarden.",
        "licentie": "Open data van de rijksoverheid.",
        "waar_in_de_code": "scripts/13 en scripts/21, ingelezen via usecases/kmg/metingen.py",
        "levert": "Wat er werkelijk gemeten is -- de laag die een vergunning tegen de "
                  "werkelijkheid houdt.",
    },
    {
        "naam": "Stelselcatalogus Omgevingswet",
        "houder": "Ministerie van Binnenlandse Zaken (DSO)",
        "hoe": "Live bevraagd per begrip, met een dagcache; antwoorden komen als HAL+JSON.",
        "licentie": "Open, met een sleutel voor de productieomgeving.",
        "waar_in_de_code": "connectors/stelselcatalogus.py, via usecases/begrippen.py",
        "levert": "De juridische definitie en vindplaats achter een begrip, als de uitlegger "
                  "daar een treffer vindt.",
    },
]

# -- De witte lijst configuratiesleutels ---------------------------------------------------------
#
# Expliciet, want `core/config.yaml` draagt ook een `submit_token` en api-headernamen: een dump
# van een sectie zou die meenemen naar een publieke pagina. Alleen sleutels die deze twee routes
# werkelijk lezen, elk met de reden waarom zij uitmaakt.

CONFIGSLEUTELS = [
    {
        "sleutel": "leefomgevinglab.kmg.aquo_csv_pad",
        "waarvoor": "Het pad naar de Aquo-domeintabel.",
        "wat_als_hij_mist": "Elke parameternaam lijkt onbekend, dus de regel op ingetrokken "
                            "codes vuurt nergens en het aantal bevindingen valt zichtbaar lager "
                            "uit zonder dat iets omvalt.",
        "pad": True,
    },
    {
        "sleutel": "leefomgevinglab.waterpresentatie.normen_pad",
        "waarvoor": "Het pad naar de chemische KRW-normen.",
        "wat_als_hij_mist": "De normenset blijft leeg en elke meting staat zonder normoordeel. "
                            "Dit is precies één keer echt misgegaan: de routes lazen de sleutel "
                            "onder de verkeerde sectie, en zink stond maanden zonder norm.",
        "pad": True,
    },
    {
        "sleutel": "leefomgevinglab.smwk_atlas.cache_ttl_s",
        "waarvoor": "Hoe lang het antwoord van de Atlas hergebruikt mag worden.",
        "wat_als_hij_mist": "De connector valt terug op haar eigen standaard van een dag.",
        "pad": False,
    },
    {
        "sleutel": "leefomgevinglab.smwk_atlas.base_url",
        "waarvoor": "Het eindpunt van de Atlas-service.",
        "wat_als_hij_mist": "De connector gebruikt haar ingebouwde adres.",
        "pad": False,
    },
    {
        "sleutel": "leefomgevinglab.cache_dir",
        "waarvoor": "Waar bevraagde antwoorden worden bewaard.",
        "wat_als_hij_mist": "De connector cachet in een tijdelijke map, en elke herstart begint "
                            "koud.",
        "pad": True,
    },
]


def _diep(config: dict, sleutel: str):
    """Een puntsleutel opzoeken, met een sentinel voor 'niet aanwezig' -- want een sleutel die
    ontbreekt en een sleutel met de waarde `None` moeten hier verschillend uitpakken."""
    huidig = config
    for deel in sleutel.split("."):
        if not isinstance(huidig, dict) or deel not in huidig:
            return None, False
        huidig = huidig[deel]
    return huidig, True


def _regels() -> list[dict]:
    """De tien regels, volledig afgeleid. Geen eigen lijst regel-id's in deze module: een elfde
    regel in `signalen.REGELS` duikt hier automatisch op, in plaats van stil te ontbreken op de
    pagina die belooft te vertellen wat er gebeurt."""
    uit = []
    for regel in signalen_mod.REGELS:
        drempel, betekenis = signalen_mod.DREMPELS[regel.id]
        voorbehoud = signalen_mod.is_voorbehoud(regel.id)
        uit.append({
            "id": regel.id,
            "kop": regel.kop,
            "laag": regel.laag,
            "is_voorbehoud": voorbehoud,
            "drempel": drempel,
            "omvang_betekent": betekenis,
            "pagina": PAD_TOEZICHT if regel.laag == "werkelijkheid" else PAD_WASSTRAAT,
            "rol": ("voorbehoud" if voorbehoud else "bevinding"),
            "uitleg": REGELUITLEG.get(regel.id, ""),
        })
    return uit


def _paginas(regels: list[dict], agents: list[dict], taken: list[dict]) -> list[dict]:
    """De twee pagina's met hun eigen aantallen, geteld uit `regels` -- het soort getal dat op
    een uitlegpagina fout gaat ("zeven papierregels" blijft staan nadat er een achtste bij komt).
    """
    papier = [r for r in regels if r["laag"] == "papier"]
    return [
        {
            "pad": PAD_WASSTRAAT,
            "label": "Wasstraat vergunningen",
            "lezer": "de vergunningverlener",
            "vraag": "Wat moet er aan de vergunning zelf rechtkomen?",
            "aantal_bevindingen": len([r for r in papier if not r["is_voorbehoud"]]),
            "aantal_voorbehouden": len([r for r in papier if r["is_voorbehoud"]]),
            "toont_configuratie": True,
            "toont_runlog": True,
        },
        {
            "pad": PAD_TOEZICHT,
            "label": "Toezicht",
            "lezer": "de toezichthouder",
            "vraag": "Waar moet ik gaan kijken?",
            "aantal_signalen": len([r for r in regels if r["laag"] == "werkelijkheid"]),
            "toont_configuratie": False,
            "toont_gedraaide_agents": True,
        },
    ]


def _grens(agents: list[dict]) -> dict:
    """De taalmodelgrens, afgelezen uit dezelfde afwezigheid die de runner leest -- niet als
    belofte in proza herhaald."""
    return {
        "mag_wel": [a["id"] for a in agents if a["mag_llm"]],
        "mag_niet": [a["id"] for a in agents if not a["mag_llm"]],
        # Beide dossierroutes geven `llm=None` door. Staat hier ooit True, dan is dat een echte
        # verandering in wat deze pagina's doen en geen detail.
        "in_de_dossierroutes_aangeroepen": False,
        "waar_gemeten": "usecases/toezicht/runlog.py -- per stap, via een tellende omhulling om "
                        "het model heen.",
    }


def _config_uit(config: dict) -> list[dict]:
    """De witte lijst, met per sleutel of hij aanwezig is en wat zijn waarde is. Een ontbrekende
    sleutel wordt als ontbrekend getoond en niet stil weggelaten: dat zou de ergste vorm zijn
    die deze pagina kan hebben -- zij verbergt dan precies de misconfiguratie die zij hoort te
    laten zien."""
    uit = []
    for item in CONFIGSLEUTELS:
        waarde, aanwezig = _diep(config, item["sleutel"])
        if aanwezig and item["pad"]:
            waarde = _kort_pad(waarde)
        uit.append({**{k: v for k, v in item.items() if k != "pad"},
                     "aanwezig": aanwezig,
                     "waarde": waarde if aanwezig else None})
    return uit


def anatomie(agents_pad: str, tasks_pad: str, config: dict) -> dict:
    """De hele anatomie in één gegeven: de twee pagina's, de regels, de agents en taken, de
    taalmodelgrens, de bronnen, de configuratiesleutels en de uitgelegde onderdelen.

    `config` is de volledige geladen configuratie; alleen de sleutels in `CONFIGSLEUTELS` worden
    eruit gelezen."""
    gegeven = pijplijn_mod.als_gegeven(agents_pad, tasks_pad)
    taken = gegeven["tasks"]
    # Welke taken een agent heeft, afgeleid uit de taken zelf. Zonder dit leest een lezer zes
    # agents en vier taken zonder te zien welke agent niets doet -- en dat twee agents geen taak
    # hebben is een feit over de pijplijn dat deze pagina moet laten zien, niet verbergen.
    agents = [{**a, "taken": [t["id"] for t in taken if t["agent"] == a["id"]]}
              for a in gegeven["agents"]]
    regels = _regels()
    return {
        "paginas": _paginas(regels, agents, taken),
        "regels": regels,
        "agents": agents,
        "taken": taken,
        "grens": _grens(agents),
        "bronnen": BRONNEN,
        "config": _config_uit(config),
        "onderdelen": ONDERDELEN,
    }
