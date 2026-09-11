"""Van tellingen naar een antwoord: kan hier nog een Seveso-inrichting bij?

De maatstaf is niet een getal maar een aanwezigheid. Staat er een zeer kwetsbaar gebouw binnen
een brand- of explosieaandachtsgebied, dan is dat in het Bkl geen weegfactor maar een grens.
Binnen het gifwolkaandachtsgebied weegt het zwaar mee in de verantwoording.

Ook hier geldt: indicatief. De echte toets kijkt naar de feitelijke aanwezigheid van personen,
naar maatregelen aan het gebouw en naar het groepsrisico.
"""


def beoordeel(tellingen: dict, bestaand: dict) -> dict:
    """`tellingen`: per contour per klasse een aantal. `bestaand`: REV-tellingen in de omgeving."""
    blokkades, wegingen = [], []

    for soort in ("explosieaandachtsgebied", "brandaandachtsgebied"):
        zk = tellingen.get(soort, {}).get("zeer kwetsbaar", 0) or 0
        if zk:
            blokkades.append({
                "reden": f"{zk} zeer kwetsbaar gebouw{'en' if zk > 1 else ''} binnen het "
                         f"{soort}", "contour": soort, "aantal": zk,
                "toelichting": "Binnen een brand- of explosieaandachtsgebied zijn zeer kwetsbare "
                               "gebouwen niet toelaatbaar zonder ingrijpende maatregelen."})

    gif = tellingen.get("gifwolkaandachtsgebied", {})
    zk_gif = gif.get("zeer kwetsbaar", 0) or 0
    if zk_gif:
        wegingen.append({
            "reden": f"{zk_gif} zeer kwetsbaar gebouw{'en' if zk_gif > 1 else ''} binnen het "
                     "gifwolkaandachtsgebied", "aantal": zk_gif,
            "toelichting": "Weegt zwaar in de verantwoording: dit zijn plekken met verminderd "
                           "zelfredzame mensen die bij een gifwolk niet snel weg kunnen."})
    kw_gif = gif.get("kwetsbaar", 0) or 0
    if kw_gif:
        wegingen.append({
            "reden": f"{kw_gif} kwetsbare gebouwen binnen het gifwolkaandachtsgebied",
            "aantal": kw_gif,
            "toelichting": "Vooral woningen. Bepaalt de omvang van de groep die bij een incident "
                           "moet schuilen of vluchten."})

    n_act = bestaand.get("risicovolle activiteiten") or 0
    if n_act:
        wegingen.append({
            "reden": f"{n_act} bestaande risicovolle activiteiten binnen 1500 m", "aantal": n_act,
            "toelichting": "Aandachtsgebieden stapelen. Voor de omgeving telt de som, niet de "
                           "losse inrichting — en dat is precies wat een register zichtbaar maakt."})

    if blokkades:
        antwoord, kop = "nee, tenzij", "Hier kan het niet zonder ingrijpende maatregelen"
    elif zk_gif or kw_gif > 1500:
        antwoord, kop = "ja, mits", "Het kan, maar er hangt een zware verantwoording aan"
    else:
        antwoord, kop = "ja", "Hier is ruimte"

    return {"antwoord": antwoord, "kop": kop, "blokkades": blokkades, "wegingen": wegingen,
            "indicatief": True}
