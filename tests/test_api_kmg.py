from fastapi.testclient import TestClient

import leefomgevinglab.geluidsmeter.api as api
from leefomgevinglab.usecases import water_hub as wh


def _client(monkeypatch):
    monkeypatch.setattr(api, "load_config", lambda *a, **k: api._config)
    return TestClient(api.app)


def test_meetpunten_endpoint(monkeypatch):
    r = _client(monkeypatch).get("/api/kmg/meetpunten")
    assert r.status_code == 200
    assert isinstance(r.json(), list)


def test_onbekend_meetpunt_geeft_404(monkeypatch):
    r = _client(monkeypatch).get("/api/kmg?meetpunt=BESTAAT_NIET&live=0")
    assert r.status_code == 404


def test_pagina_geeft_200_met_de_subnav(monkeypatch):
    r = _client(monkeypatch).get("/kmg")
    assert r.status_code == 200
    assert 'class="waternav"' in r.text
    assert r.text.count('aria-current="page"') == 1
    assert "__WATERNAV__" not in r.text
    assert "/api/kmg" in r.text


def test_de_pagina_stelt_niet_vast_wie_een_overschrijding_teweegbrengt(monkeypatch):
    """De harde regel uit spec 5.3, bewaakt op de plek waar de woorden bij een lezer komen.

    Deze test bestond niet terwijl CLAUDE.md beweerde van wel. De bestaande woordtests zitten op
    het toerekeningsmodel en op de proclaimertekst; de HTML -- de enige laag die de lezer echt
    ziet -- was onbewaakt.
    """
    h = _client(monkeypatch).get("/kmg").text.lower()
    assert "veroorzaakt door" not in h
    # Een ontkenning als "niet dat zij heeft bijgedragen" is juist gewenst, en met een deelstring
    # niet van een bewering te onderscheiden -- daarom toetsen we niet op die woorden, maar erop
    # dat de pagina het voorbehoud zélf uitspreekt. Vermijden is niet genoeg.
    assert "bovengrens" in h
    assert "kan bijdragen" in h
    assert "nooit een vaststelling" in h


def test_het_dossier_kent_de_twee_nieuwe_leden():
    """Niet alleen tellen maar benoemen: een telling blijft kloppen als een lid vervangen wordt."""
    assert wh.lid("kmg")["pad"] == "/kmg"
    assert wh.lid("model")["pad"] == "/watermodel"


def test_het_nieuwe_lid_verantwoordt_zijn_bronnen():
    l = wh.lid("kmg")
    assert "Waterkwaliteitsportaal" in " ".join(l["live"] + l["synthetisch"])


def test_de_informatiemodelpagina_geeft_200_met_de_subnav(monkeypatch):
    r = _client(monkeypatch).get("/watermodel")
    assert r.status_code == 200
    assert 'class="waternav"' in r.text
    assert r.text.count('aria-current="page"') == 1
    assert "__WATERNAV__" not in r.text
    # De cijfers worden live opgehaald; de pagina mag ze niet hardcoderen.
    assert "/api/kmg/overzicht" in r.text



def test_de_verhaalpagina_geeft_200_met_de_subnav(monkeypatch):
    r = _client(monkeypatch).get("/waterverhaal")
    assert r.status_code == 200
    assert 'class="waternav"' in r.text
    assert r.text.count('aria-current="page"') == 1
    assert "__WATERNAV__" not in r.text
    # De cijfers worden live opgehaald, niet in de tekst gezet.
    assert "/api/kmg/overzicht" in r.text


def test_het_verhaal_staat_vooraan_in_het_dossier():
    """Het is de instap, dus het hoort meteen na het overzicht te staan."""
    ids = [l["id"] for l in wh.LEDEN]
    assert ids[0] == "overzicht"
    assert ids[1] == "verhaal"


def test_de_kmg_normen_pad_is_echt_bereikbaar_via_de_configuratie(monkeypatch):
    """Fix 2 (taakrapport): `_kmg_normen_pad` las eerder `leefomgevinglab.kmg.normen_pad`, een
    sleutel die niet bestaat (die sectie kent alleen aquo_csv_pad/doelen_pad/maaskaart_pad/
    metingen_pad/overzicht_pad/parameters_pad/straal_m/waterlichamen_pad). Het echte pad staat
    onder `leefomgevinglab.waterpresentatie.normen_pad`. Deze test roept de functie ongepatcht
    aan tegen de echte `core/config.yaml`, zodat een hernoemde of verschoven sleutel hier luid
    faalt in plaats van stilzwijgend een lege normenset op te leveren -- precies zoals
    `test_de_normenset_is_echt_bereikbaar_via_de_configuratie` dat al voor `/toezicht` bewaakt."""
    from pathlib import Path

    from leefomgevinglab.geluidsmeter.config import load_config

    monkeypatch.setattr(api, "_config", load_config())
    pad = api._kmg_normen_pad()
    assert pad, "geen normen_pad gevonden -- controleer leefomgevinglab.waterpresentatie.normen_pad"
    assert Path(pad).exists(), f"het geconfigureerde normenbestand bestaat niet: {pad}"


def test_een_stof_met_een_echte_chemische_norm_krijgt_die_norm(monkeypatch):
    """De kern van fix 2: zink op NL80_BELFBVN heeft een echte KRW-norm (7,80 ug/l, opgeloste
    fractie, zie CLAUDE.md) -- vóór de fix kwam die nooit aan, omdat `normen_pad` een niet-
    bestaande configuratiesleutel las en de normenset dus altijd leeg was.

    `_config` wordt hier net als in `test_de_kmg_normen_pad_is_echt_bereikbaar_via_de_configuratie`
    expliciet op de echte configuratie gezet: `app`'s `startup`-hook vult hem anders alleen als
    de TestClient als contextmanager wordt gebruikt, en zonder die vulling leest elke `kmg`-sleutel
    stil terug als "niet meegegeven" in plaats van de configuratiefout te laten zien."""
    from leefomgevinglab.geluidsmeter.config import load_config

    monkeypatch.setattr(api, "_config", load_config())
    monkeypatch.setattr(api, "load_config", lambda *a, **k: api._config)
    r = _client(monkeypatch).get("/api/kmg?meetpunt=NL80_BELFBVN&live=0")
    assert r.status_code == 200
    bijdragen = r.json()["bijdragen"]
    zn = [b for b in bijdragen if b["stof"] == "Zn" and b.get("doel", {}).get("beschikbaar")]
    assert zn, "geen enkele Zn-reeks op dit meetpunt kreeg een beschikbare norm"
    doel = zn[0]["doel"]
    assert doel["soort"] == "chemische norm"
    assert doel["goed_tot"] == 7.8
    assert doel["hoedanigheid"] == "nf"


def test_de_laag_mag_zegt_zelf_wat_zij_niet_toont(monkeypatch):
    """Twee uitspraken die een lezer van "mag" nodig heeft, en die niet uit de data volgen.

    Het register gaat alleen over lozingen op de Maas zelf; de route via het riool kan er
    structureel niet in staan. En buiten de vergunningen om geldt de specifieke zorgplicht, dus
    een stof die hier niet genoemd wordt is daarmee niet toegestaan. Zonder deze twee zinnen
    leest de laag als een volledige opsomming van wat mag, en dat is zij niet.
    """
    h = _client(monkeypatch).get("/kmg").text.lower()
    assert "riool" in h
    assert "een leeg veld is geen toestemming" in h
    assert "zorgplicht" in h
