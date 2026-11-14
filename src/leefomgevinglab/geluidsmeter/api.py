"""FastAPI service op poort 8792."""
import json
import uuid
from pathlib import Path
from datetime import datetime, timezone

from dotenv import load_dotenv

# Laad .env (o.a. DSO_API_KEY) bij import — werkt voor systemd
# (WorkingDirectory=repo-root) en handmatige uvicorn-runs vanaf de repo-root.
load_dotenv()

from fastapi import FastAPI, Header, HTTPException
from fastapi.responses import JSONResponse, HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

import geopandas as gpd
from shapely.geometry import Point as ShapelyPoint
from .config import load_config, load_private_location
from .aggregate import _round_location
from .source_match import get_rivm_lden
from leefomgevinglab.connectors.base import ConnectorError
from leefomgevinglab.connectors.rev import RevConnector
from leefomgevinglab.usecases.rev_viewer import service as rev_service
import os
from leefomgevinglab.connectors.dso import DsoConnector
from leefomgevinglab.connectors.dso_zoek import ZoekConnector
from leefomgevinglab.usecases.vergunningen import service as vergunningen_service
from leefomgevinglab.usecases.vergunningen import resolver as vergunningen_resolver
from leefomgevinglab.usecases.vergunningen import omgevingsplan as omgevingsplan_mod
from leefomgevinglab.usecases.vergunningen import externe_veiligheid as externe_veiligheid_mod
from leefomgevinglab.connectors.externe_veiligheid import ExterneVeiligheidConnector
from leefomgevinglab.usecases import wfs_kwaliteit as wfs_kwaliteit_mod
from leefomgevinglab.usecases import vth_bronnen as vth_bronnen_mod
from leefomgevinglab.usecases import dvth as dvth_mod
from leefomgevinglab.usecases.dvth_keten import motor as dvth_keten_motor
from leefomgevinglab.usecases import lozing as lozing_mod
from leefomgevinglab.usecases import balo as balo_mod
from leefomgevinglab.usecases.gebruiksruimte import service as gebruiksruimte_service
from leefomgevinglab.usecases.evruimte import service as evruimte_service
from leefomgevinglab.usecases.lozing_keten import motor as lozing_keten_motor
from leefomgevinglab.connectors.ozon import OzonConnector
from leefomgevinglab.connectors.stelselcatalogus import StelselcatalogusConnector
from leefomgevinglab.usecases import begrippen as begrippen_mod
from leefomgevinglab.usecases import water_hub as water_hub_mod
from leefomgevinglab.usecases import waterpresentatie as waterpresentatie_mod
from leefomgevinglab.usecases import stoffengraaf as stoffengraaf_mod
from leefomgevinglab.usecases import eindbeeld as eindbeeld_mod
from leefomgevinglab.usecases import maaskaart as maaskaart_mod
from leefomgevinglab.usecases import modellen as modellen_mod
from leefomgevinglab.usecases.kmg import service as kmg_service
from leefomgevinglab.usecases.kmg import doelen as kmg_doelen
from leefomgevinglab.usecases.toezicht import aquo as toezicht_aquo
from leefomgevinglab.usecases.toezicht import pijplijn as toezicht_pijplijn
from leefomgevinglab.usecases.toezicht import runlog as toezicht_runlog
from leefomgevinglab.usecases.toezicht import runner as toezicht_runner
from leefomgevinglab.usecases.toezicht import register as toezicht_register
from leefomgevinglab.usecases.toezicht import graaf as toezicht_graaf
from leefomgevinglab.usecases.wasstraat import dossier as wasstraat_dossier_mod
from functools import partial
from leefomgevinglab.rag.embed import embed_texts
from leefomgevinglab.rag.store import VectorStore
from leefomgevinglab.usecases.vergunningen import chatbot
from leefomgevinglab.semantiek import graph as semantiek_graph
from leefomgevinglab.ld import store as ld_store
from leefomgevinglab.usecases.datavraag import grounding as dv_grounding
from leefomgevinglab.usecases.datavraag import service as dv_service
from leefomgevinglab.usecases.afval import service as afval_service
from leefomgevinglab.usecases.afval import duiding as afval_duiding
from leefomgevinglab.usecases.afval import chat as afval_chat
from leefomgevinglab.afvaldb import store as afvaldb_store


class MobileSubmission(BaseModel):
    dba: float | None = None
    lat: float
    lon: float
    naam: str = "Mobiele meting"


def _location_entry(
    config: dict,
    pub_lat: float,
    pub_lon: float,
    rms_dba: float | None,
    rivm_lden: float | None,
) -> dict:
    norm_lden = 48
    norm_status = None
    if rms_dba is not None:
        norm_status = "binnen_norm" if rms_dba <= norm_lden else "boven_norm"
    loc_cfg = config.get("location", {})
    return {
        "id": loc_cfg.get("public_id", "meetlocatie"),
        "naam": loc_cfg.get("public_name", "Meetlocatie"),
        "lat": pub_lat,
        "lon": pub_lon,
        "precision_m": loc_cfg.get("public_location_precision_m", 100),
        "lden_gemeten": rms_dba,
        "rivm_lden": rivm_lden,
        "norm_lden": norm_lden,
        "norm_status": norm_status,
        "laatste_meting": datetime.now(timezone.utc).isoformat() if rms_dba is not None else None,
        "kwaliteit": config.get("project", {}).get("quality_label", "prototype_indicatief_niet_juridisch"),
        "source": "jetson",
    }


app = FastAPI(title="LeefomgevingLab API", version="0.1.0")
_static_dir = Path(__file__).parent / "static"
app.mount("/static", StaticFiles(directory=str(_static_dir)), name="static")
_config: dict = {}


@app.on_event("startup")
def startup():
    global _config
    _config = load_config()


def _latest_feature() -> dict | None:
    raw_dir = Path(_config["outputs"]["raw_features_dir"])
    today = datetime.now(timezone.utc).strftime("%Y%m%d")
    fp = raw_dir / f"sound_features_{today}.jsonl"
    if not fp.exists():
        return None
    last_line = None
    with open(fp) as f:
        for line in f:
            last_line = line.strip()
    return json.loads(last_line) if last_line else None


def _mobile_location_entries(rivm_gdf=None) -> list[dict]:
    fp_str = _config.get("mobile", {}).get("measurements_file", "")
    if not fp_str:
        return []
    fp = Path(fp_str)
    if not fp.exists():
        return []
    norm_lden = 48
    entries = []
    with open(fp) as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                rec = json.loads(line)
            except json.JSONDecodeError:
                continue
            try:
                dba = rec.get("dba")
                norm_status = None
                if dba is not None:
                    norm_status = "binnen_norm" if dba <= norm_lden else "boven_norm"
                rivm_lden = None
                if rivm_gdf is not None:
                    rivm_lden = get_rivm_lden(ShapelyPoint(rec["lon"], rec["lat"]), rivm_gdf)
                entries.append({
                    "id": rec["id"],
                    "naam": rec.get("naam", "Mobiele meting"),
                    "lat": rec["lat"],
                    "lon": rec["lon"],
                    "precision_m": 20,
                    "lden_gemeten": dba,
                    "rivm_lden": rivm_lden,
                    "norm_lden": norm_lden,
                    "norm_status": norm_status,
                    "laatste_meting": rec["ts"],
                    "kwaliteit": rec.get("kwaliteit", "prototype_indicatief_niet_juridisch"),
                    "source": "mobile",
                })
            except KeyError:
                continue
    return entries


@app.get("/", response_class=HTMLResponse)
def root():
    landing = Path(__file__).parent.parent / "static" / "index.html"
    return landing.read_text()


@app.get("/roadmap", response_class=HTMLResponse)
def roadmap_page():
    return (Path(__file__).parent.parent / "static" / "roadmap.html").read_text()


@app.get("/kwaliteit", response_class=HTMLResponse)
def kwaliteit_page():
    return (Path(__file__).parent.parent / "static" / "kwaliteit.html").read_text()


@app.get("/wfs-kwaliteit", response_class=HTMLResponse)
def wfs_kwaliteit_page():
    return (Path(__file__).parent.parent / "static" / "wfs-kwaliteit.html").read_text()


@app.get("/api/wfs-kwaliteit")
def api_wfs_kwaliteit(refresh: int = 0, bronhouder: str = "", activiteit: str = ""):
    import hashlib
    ll = _config.get("leefomgevinglab", {})
    cfg = ll.get("wfs_kwaliteit", {})
    wfs_url = cfg.get("wfs_url", "")
    cache_dir = Path(ll.get("cache_dir", "/tmp/llab_cache"))
    cache_dir.mkdir(parents=True, exist_ok=True)
    cql = wfs_kwaliteit_mod.bouw_cql(bronhouder or None, activiteit or None)
    sleutel = hashlib.sha256((cql or "basis").encode()).hexdigest()[:16]
    cache = cache_dir / f"wfs_kwaliteit_{sleutel}.json"
    ttl = cfg.get("cache_ttl_s", 86400)
    if not refresh and cache.exists() and (datetime.now(timezone.utc).timestamp() - cache.stat().st_mtime) < ttl:
        data = json.loads(cache.read_text())
        data["uit_cache"] = True
        return data
    lagen = cfg.get("lagen") or wfs_kwaliteit_mod.lagen_uit_capabilities(
        wfs_url, namespace=cfg.get("namespace", "rev_public:"))
    imev = cfg.get("imev_verplichte_velden") or wfs_kwaliteit_mod.IMEV_VERPLICHTE_VELDEN
    data = wfs_kwaliteit_mod.scan_lagen(wfs_url, lagen, sample_n=cfg.get("sample_n", 300),
                                        cql=cql, imev_velden=imev)
    data["filter"] = {"bronhouder": bronhouder, "activiteit": activiteit}
    cache.write_text(json.dumps(data))
    data["uit_cache"] = False
    return data


@app.get("/demo", response_class=HTMLResponse)
def demo_page():
    return (Path(__file__).parent.parent / "static" / "demo.html").read_text()


@app.get("/poc", response_class=HTMLResponse)
def poc_page():
    return (Path(__file__).parent.parent / "static" / "poc.html").read_text()


@app.get("/vth", response_class=HTMLResponse)
def vth_page():
    """Cim-VTH-Flo (Geonovum) als kapstok over de use-cases van het lab, met roadmapvoorstel."""
    return (Path(__file__).parent.parent / "static" / "vth.html").read_text()


@app.get("/vth-bronnen", response_class=HTMLResponse)
def vth_bronnen_page():
    return (Path(__file__).parent.parent / "static" / "vth-bronnen.html").read_text()


def _keten_tab(dossier: str) -> str:
    """Eén template voor alle doelbeeld-tabs; de dossiernaam bepaalt welke API hij bevraagt.

    /lozing hoort bij het waterdossier en krijgt de subnav; /dvth niet — daar wordt de
    placeholder leeg vervangen.

    De twee doelbeelden zijn elkaars spiegeldossier: /dvth wijst naar /lozing en
    andersom, nooit naar zichzelf. Die kruislink staat naast de gedeelde VTH-kapstok/
    Bronnenkaart-links in de header (__KRUISNAV__), los van de waterspecifieke subnav.
    """
    sjabloon = (Path(__file__).parent.parent / "static" / "keten-tab.html").read_text()
    nav = water_hub_mod.subnav_html("keten") if dossier == "lozing" else ""
    tegenhanger = ('<a href="/lozing">Doelbeeld lozing</a>' if dossier == "dvth"
                   else '<a href="/dvth">Doelbeeld D-VTH</a>')
    kruisnav = tegenhanger + '<a href="/kwaliteit">Kwaliteit</a>'
    return (sjabloon.replace("__DOSSIER__", dossier)
            .replace("__WATERNAV__", nav)
            .replace("__KRUISNAV__", kruisnav))


@app.get("/dvth", response_class=HTMLResponse)
def dvth_page():
    return _keten_tab("dvth")


@app.get("/lozing", response_class=HTMLResponse)
def lozing_page():
    return _keten_tab("lozing")


def _stelselcatalogus() -> StelselcatalogusConnector:
    ll = _config.get("leefomgevinglab", {})
    sc = ll.get("stelselcatalogus", {})
    return StelselcatalogusConnector(
        base_url=sc.get("base_url", ""),
        api_key=os.environ.get("DSO_API_KEY_PROD") or os.environ.get("DSO_API_KEY"),
        api_key_header=sc.get("api_key_header", "x-api-key"),
        cache_dir=ll.get("cache_dir", "/tmp/llab_cache"),
        cache_ttl=sc.get("cache_ttl_s", 86400),
    )


@app.get("/begrippen", response_class=HTMLResponse)
def begrippen_page():
    return (Path(__file__).parent.parent / "static" / "begrippen.html").read_text()


@app.get("/api/begrippen")
def api_begrippen():
    """De termen die dit lab gebruikt, opgezocht in de Stelselcatalogus Omgevingswet."""
    return begrippen_mod.los_op(_stelselcatalogus())


@app.get("/api/begrip")
def api_begrip(term: str):
    """Eén term opzoeken in de Stelselcatalogus."""
    try:
        treffers = _stelselcatalogus().zoek(term)
    except ConnectorError as exc:
        raise HTTPException(status_code=503, detail=str(exc))
    return {"term": term, "treffers": treffers, "aantal": len(treffers),
            "bron": "Stelselcatalogus Omgevingswet"}


@app.get("/evruimte", response_class=HTMLResponse)
def evruimte_page():
    return (Path(__file__).parent.parent / "static" / "evruimte.html").read_text()


@app.get("/api/evruimte")
def api_evruimte(locatie: str = "botlek", live: int = 1):
    """Kan hier nog een Seveso-inrichting bij? Contouren, wat eronder valt, en wat er al ligt."""
    try:
        return evruimte_service.beeld(locatie, live=bool(live))
    except KeyError:
        raise HTTPException(status_code=404, detail=f"onbekende locatie: {locatie}")


@app.get("/gebruiksruimte", response_class=HTMLResponse)
def gebruiksruimte_page():
    return _waterpagina("gebruiksruimte.html", "ruimte")


@app.get("/api/gebruiksruimte")
def api_gebruiksruimte(locatie: str = "brummen", debiet: float = 420, live: int = 1):
    """Wat kan hier nog? Regels live uit het DSO, vergunningen uit een synthetisch register."""
    try:
        return gebruiksruimte_service.beeld(locatie, debiet_m3_per_uur=debiet, live=bool(live))
    except KeyError:
        raise HTTPException(status_code=404, detail=f"onbekende locatie: {locatie}")


# Ruime RD-bbox rond Nederland inclusief Noordzee-deel; daarbuiten is een prik een tikfout.
_RD_GRENZEN = (-7000.0, 300000.0, 289000.0, 629000.0)


@app.get("/waterruimte", response_class=HTMLResponse)
def waterruimte_page():
    return _waterpagina("waterruimte.html", "kaart")


@app.get("/api/waterruimte")
def api_waterruimte(x: float, y: float, debiet: float = 420, live: int = 1):
    """Wat kan hier nog, op dit punt? Regels en water live; vergunningen echt waar ze bestaan."""
    xmin, ymin, xmax, ymax = _RD_GRENZEN
    if not (xmin <= x <= xmax and ymin <= y <= ymax):
        raise HTTPException(status_code=400,
                            detail=f"RD-coördinaat buiten Nederland: ({x}, {y})")
    ll = _config.get("leefomgevinglab", {})
    straal = ll.get("smwk_atlas", {}).get("straal_m", 5000)
    return gebruiksruimte_service.beeld_op_punt(x, y, debiet_m3_per_uur=debiet,
                                                live=bool(live), straal_m=straal)


def _kmg_pad() -> str:
    return _config.get("leefomgevinglab", {}).get("kmg", {}).get(
        "metingen_pad", "/mnt/nvme/geluidsmeter/data/external/wkp/metingen_2025.json")


def _kmg_normen_pad() -> str | None:
    """Het pad naar de chemische KRW-normen voor `/api/kmg`.

    Staat NIET onder `leefomgevinglab.kmg` (die sectie kent geen `normen_pad`) maar onder
    `leefomgevinglab.waterpresentatie.normen_pad` -- zie `core/config.yaml` en
    `_toezicht_normenset`, die hetzelfde pad op dezelfde manier leest. Een eigen functie, zodat
    een test deze lezing apart tegen de echte configuratie kan bewijzen (zie
    `test_de_kmg_normen_pad_is_echt_bereikbaar_via_de_configuratie`)."""
    return _config.get("leefomgevinglab", {}).get("waterpresentatie", {}).get("normen_pad")


@app.get("/kmg", response_class=HTMLResponse)
def kmg_page():
    """Kan, mag en gebeurt op het water — de drie lagen over elkaar."""
    return _waterpagina("kmg.html", "kmg")


@app.get("/api/kmg/meetpunten")
def api_kmg_meetpunten():
    return kmg_service.meetpunten(_kmg_pad())


@app.get("/waterverhaal", response_class=HTMLResponse)
def waterverhaal_page():
    """Het waterdossier in vijf vragen — de korte doorloop, bedoeld als instap en voor een demo."""
    return _waterpagina("waterverhaal.html", "verhaal")


@app.get("/watermodel", response_class=HTMLResponse)
def watermodel_page():
    """Van vergunning naar vracht — wat een informatiemodel voor lozingen zou opleveren."""
    return _waterpagina("watermodel.html", "model")


@app.get("/waterpresentatie", response_class=HTMLResponse)
def waterpresentatie_page():
    """Het hele dossier in een kwartier, als zelflopende presentatie met spreektekst."""
    return _waterpagina("waterpresentatie.html", "presentatie")


@app.get("/api/waterpresentatie")
def api_waterpresentatie():
    """De dia's met hun duur, beeldspecificatie en spreektekst.

    Inclusief de vindplaats van het pptx, mét de wijzigingstijd in de URL. Die tijd is geen
    opsmuk: zij maakt van elke nieuwe versie een nieuwe cache-sleutel, zodat een tussenliggende
    cache niet de vorige presentatie kan blijven uitserveren.
    """
    ll = _config.get("leefomgevinglab", {})
    pad = Path(ll.get("waterpresentatie", {}).get(
        "pptx_pad", "/mnt/nvme/geluidsmeter/data/external/waterdossier.pptx"))
    pptx = None
    if pad.exists():
        st = pad.stat()
        pptx = {"url": f"/waterpresentatie.pptx?v={int(st.st_mtime)}",
                "bytes": st.st_size,
                "gebouwd_op": datetime.fromtimestamp(st.st_mtime, timezone.utc)
                                      .strftime("%Y-%m-%d %H:%M")}
    return {**waterpresentatie_mod.presentatie(), "pptx": pptx}


@app.get("/waterpresentatie.pptx")
def waterpresentatie_pptx(v: int | None = None):
    """De presentatie als PowerPoint, met de spreektekst in de notitieruimte.

    Het bestand wordt niet bij elke aanvraag gebouwd: dat kost seconden en de inhoud verandert
    alleen als `waterpresentatie.py` verandert. Verversen: scripts/19_bouw_waterpresentatie_pptx.py.

    **Zonder `v` volgt een doorverwijzing naar de versie van vandaag.** Dat is geen sierlijkheid.
    Cloudflare cachet een pptx vier uur op zijn extensie en negeert daarbij een `no-cache` van de
    oorsprong; het gevolg was dat iemand een presentatie van de vorige dag downloadde terwijl de
    site de nieuwe toonde. Een versie in de URL geeft elke nieuwe bouw een eigen cache-sleutel,
    en de kale URL wijst daar altijd naartoe.
    """
    from fastapi.responses import FileResponse

    ll = _config.get("leefomgevinglab", {})
    pad = Path(ll.get("waterpresentatie", {}).get(
        "pptx_pad", "/mnt/nvme/geluidsmeter/data/external/waterdossier.pptx"))
    if not pad.exists():
        raise HTTPException(
            status_code=404,
            detail="het pptx is nog niet gebouwd; draai scripts/19_bouw_waterpresentatie_pptx.py")
    mtime = int(pad.stat().st_mtime)
    if v != mtime:
        return RedirectResponse(f"/waterpresentatie.pptx?v={mtime}", status_code=302)
    return FileResponse(
        str(pad), filename="waterdossier.pptx",
        media_type="application/vnd.openxmlformats-officedocument.presentationml.presentation",
        # Zonder dit cachet Cloudflare het bestand vier uur op zijn extensie, en dan downloadt
        # iemand een presentatie van gisteren terwijl de site de nieuwe toont. Dat is precies
        # gebeurd. `no-cache` laat de rand wél opslaan maar dwingt af dat hij elke keer
        # terugvraagt of de versie nog klopt.
        headers={"Cache-Control": "no-cache, must-revalidate"})


@app.get("/modellen", response_class=HTMLResponse)
def modellen_page():
    """CIM-VTH-Flo, IMEV 3.0 en het GIR-databasemodel naast elkaar."""
    return (Path(__file__).parent.parent / "static" / "modellen.html").read_text()


@app.get("/api/modellen")
def api_modellen():
    """De vergelijking van de drie modellen, met hun tellingen en herkomst."""
    return modellen_mod.analyse()


@app.get("/maaskaart", response_class=HTMLResponse)
def maaskaart_page():
    """De vier lagen samen op het Maasstroomgebied, met de grondslag per koppeling."""
    return _waterpagina("maaskaart.html", "kaartvier")


@app.get("/api/maaskaart")
def api_maaskaart(live: int = 1):
    """Geometrie plus de vier lagen. De Atlas wordt live bevraagd en een dag gecachet."""
    ll = _config.get("leefomgevinglab", {})
    kmg = ll.get("kmg", {})
    return maaskaart_mod.beeld(
        kaart_pad=kmg.get("maaskaart_pad"),
        overzicht_pad=kmg.get("overzicht_pad", ""),
        metingen_pad=_kmg_pad(),
        straal_m=kmg.get("straal_m", 250000),
        live=bool(live))


@app.get("/eindbeeld", response_class=HTMLResponse)
def eindbeeld_page():
    """Hoe een informatieproduct eruitziet als de gaten dicht zijn — volledig synthetisch."""
    return _waterpagina("eindbeeld.html", "eindbeeld")


@app.get("/api/eindbeeld")
def api_eindbeeld():
    """Het synthetische eindbeeld, met zijn aannames en zijn afstand tot vandaag."""
    return eindbeeld_mod.product()


@app.get("/kennisgraaf", response_class=HTMLResponse)
def kennisgraaf_page():
    """De stoffen als graaf: wat relaties toevoegen bovenop het informatiemodel."""
    return _waterpagina("kennisgraaf.html", "kennisgraaf")


@app.get("/api/stoffengraaf")
def api_stoffengraaf():
    """E-PRTR-stoffen, hun CAS-nummers en de Aquo-parameters, met de herkomst per koppeling."""
    kmg = _config.get("leefomgevinglab", {}).get("kmg", {})
    return stoffengraaf_mod.bouw(kmg.get("aquo_csv_pad"))


@app.get("/api/stoffengraaf/controle")
def api_stoffengraaf_controle():
    """De graaf als kwaliteitscontrole over het echte Maas-register.

    Apart eindpunt en niet in `/api/stoffengraaf`: dit bevraagt de Atlas live, en de plaat op de
    pagina hoort niet op die bevraging te wachten.
    """
    ll = _config.get("leefomgevinglab", {})
    kmg = ll.get("kmg", {})
    try:
        register = kmg_service._atlas_standaard(
            *stoffengraaf_mod.MAASPUNT, kmg.get("straal_m", 250000))
    except Exception as exc:                        # noqa: BLE001 — bron mag wegvallen
        return {"beschikbaar": False,
                "reden": f"de Atlas was niet bereikbaar ({type(exc).__name__})"}
    return stoffengraaf_mod.controleer(register, kmg.get("aquo_csv_pad"))


@app.get("/api/kmg/overzicht")
def api_kmg_overzicht():
    """Het voorberekende overzicht over alle Maas-meetpunten.

    Zacht falen als het bestand er niet is: de pagina moet de rest kunnen tonen en zeggen waarom de
    strook ontbreekt, net zoals bij een ontbrekende meetset.
    """
    pad = Path(_config.get("leefomgevinglab", {}).get("kmg", {}).get(
        "overzicht_pad", "/mnt/nvme/geluidsmeter/data/external/wkp/kmg_overzicht.json"))
    if not pad.exists():
        return {"beschikbaar": False,
                "reden": "nog niet voorberekend; draai scripts/14_bouw_kmg_overzicht.py",
                "punten": []}
    try:
        return {"beschikbaar": True, **json.loads(pad.read_text(encoding="utf-8"))}
    except (ValueError, OSError) as exc:
        return {"beschikbaar": False,
                "reden": f"het overzichtsbestand is onleesbaar ({type(exc).__name__})",
                "punten": []}


@app.get("/api/kmg")
def api_kmg(meetpunt: str, live: int = 1):
    try:
        kmg = _config.get("leefomgevinglab", {}).get("kmg", {})
        return kmg_service.beeld(meetpunt, _kmg_pad(), live=bool(live),
                                 straal_m=kmg.get("straal_m", 250000),
                                 doelen_pad=kmg.get("doelen_pad"),
                                 parameters_pad=kmg.get("parameters_pad"),
                                 # Fix (taakrapport): `leefomgevinglab.kmg` draagt geen
                                 # `normen_pad` -- die sectie kent alleen aquo_csv_pad/
                                 # doelen_pad/maaskaart_pad/metingen_pad/overzicht_pad/
                                 # parameters_pad/straal_m/waterlichamen_pad. Het echte pad
                                 # staat onder `leefomgevinglab.waterpresentatie.normen_pad`
                                 # (zie `_kmg_normen_pad` en `core/config.yaml`); dezelfde
                                 # sleutel die `_toezicht_normenset` hieronder al gebruikt. De
                                 # oude lezing gaf altijd `beschikbaar: False` terug, dus de
                                 # chemische KRW-norm (zink, PFOA) bereikte deze route nooit.
                                 normen_pad=_kmg_normen_pad(),
                                 waterlichamen_pad=kmg.get("waterlichamen_pad"))
    except KeyError:
        raise HTTPException(status_code=404, detail=f"onbekend meetpunt: {meetpunt}")


@app.get("/balo", response_class=HTMLResponse)
def balo_page():
    return _waterpagina("balo.html", "knelpunten")


@app.get("/api/balo/overzicht")
def api_balo_overzicht():
    """De twee casussen geplot op redeneerlijn 2 en 3 van de BALO-businessarchitectuur."""
    return balo_mod.overzicht()


def _waterpagina(bestand: str, actief: str | None) -> str:
    """Een waterpagina met de gedeelde subnav erin; zelfde truc als _keten_tab."""
    html = (Path(__file__).parent.parent / "static" / bestand).read_text()
    return html.replace("__WATERNAV__", water_hub_mod.subnav_html(actief))


# -- /toezicht: het signaaldossier op het Maas-lozingenregister (taak 8) -------------------------
#
# Hetzelfde middelpunt/straal als /maaskaart en de live-tests (`test_toezicht_live.py`): heel het
# Maasstroomgebied vanuit één RD-punt, niet de kleinere straal die /waterruimte en /gebruiksruimte
# rond een losse prik gebruiken.
_TOEZICHT_CONFIG_DIR = os.path.join(os.path.dirname(toezicht_runner.__file__), "config")
TOEZICHT_AGENTS_PAD = os.path.join(_TOEZICHT_CONFIG_DIR, "agents.yaml")
TOEZICHT_TASKS_PAD = os.path.join(_TOEZICHT_CONFIG_DIR, "tasks.yaml")
_TOEZICHT_PUNT = (170000.0, 390000.0)
_TOEZICHT_STRAAL_M = 250000


def _toezicht_register() -> list[dict]:
    """Het hele Maas-lozingenregister, live via de Atlas voor een Schone Maas, en al ontdubbeld
    (`toezicht_register.voorbereid`) -- zie die module voor waarom dat hier gebeurt, bij de grens
    waarop het register `toezicht` binnenkomt, en niet in elk van de tien signaalregels apart
    (eindreview, bevinding 3). Gecachet door de connector zelf (`smwk_atlas.cache_ttl_s`, zie
    `kmg_service._atlas_standaard`), dus niet bij elke pageview opnieuw over het netwerk. Een
    eigen, kleine functie (niet rechtstreeks `kmg_service._atlas_standaard` in de routes) zodat
    een test hem in één regel kan vervangen.

    Minor (R20-review): dit hergebruikt een functie van `kmg_service` met een voorloop-underscore
    -- een privé-functie van een andere module. Bewust zo gelaten: `maaskaart.py` doet exact
    hetzelfde (`_haal_atlas` → `kmg_service._atlas_standaard`), dus dit volgt een bestaand
    patroon in dit lab in plaats van er een eigen, derde manier naast te zetten om dezelfde
    connector (cache_dir, cache_ttl, base_url) op te bouwen. `_atlas_standaard` publiek maken zou
    verder dan deze taak reiken: dat is een keuze over de publieke interface van `kmg_service`,
    niet over `/toezicht`."""
    ruw = kmg_service._atlas_standaard(*_TOEZICHT_PUNT, _TOEZICHT_STRAAL_M)
    return toezicht_register.voorbereid(ruw)


def _toezicht_aquo_ref() -> dict:
    """De Aquo-domeintabel Parameter, geldig én vervallen -- dezelfde CSV en hetzelfde
    configuratiesleutel als `/kmg` (`kmg.aquo_csv_pad`), niet een eigen, tweede pad."""
    kmg_cfg = _config.get("leefomgevinglab", {}).get("kmg", {})
    return toezicht_aquo.laad(kmg_cfg.get("aquo_csv_pad", ""))


def _toezicht_normenset() -> dict:
    """De KRW-normen, via `kmg.doelen.laad_normen` -- dezelfde functie en hetzelfde bestand als
    de /kmg-pagina gebruikt voor de chemische norm per stof en meetpunt.

    Fix-ronde 1 (R20-review): het pad staat NIET onder `leefomgevinglab.kmg.normen_pad` (die
    sectie draagt alleen `aquo_csv_pad`/`doelen_pad`/`maaskaart_pad`/`metingen_pad`/
    `overzicht_pad`/`parameters_pad`/`straal_m`/`waterlichamen_pad` -- geen `normen_pad`), maar
    onder `leefomgevinglab.waterpresentatie.normen_pad` (zie `core/config.yaml`). De eerdere
    lezing haalde dus altijd een lege sectie op en gaf permanent `beschikbaar: False` terug --
    precies de KRW-norm-poot van R20 deed in de praktijk niets. Dezelfde foute sleutel stond ook
    op de bestaande `/api/kmg`-route (`api_kmg`); dat is inmiddels in een apart taakrapport
    rechtgezet (live-fixes-report.md, fix 2) -- beide routes lezen nu via `_kmg_normen_pad`
    hetzelfde echte pad."""
    normen_pad = _kmg_normen_pad()
    if not normen_pad:
        return {"beschikbaar": False, "normen": {}, "reden": "geen normen_pad geconfigureerd"}
    return kmg_doelen.laad_normen(normen_pad)


@app.get("/toezicht", response_class=HTMLResponse)
def toezicht_page():
    """Signaaldossier voor de toezichthouder op het Maas-lozingenregister: niet wat hier nog
    mag, maar waar je moet gaan kijken."""
    return _waterpagina("toezicht.html", "toezicht")


@app.get("/api/toezicht/pijplijn")
def api_toezicht_pijplijn():
    """De agents en taken zoals ze in de YAML staan -- geen crew gestart, geen validatie (R4):
    de pagina moet de configuratie kunnen tonen zonder het proces uit te voeren."""
    gegeven = toezicht_pijplijn.als_gegeven(TOEZICHT_AGENTS_PAD, TOEZICHT_TASKS_PAD)
    return {**gegeven, "bron": TOEZICHT_AGENTS_PAD}


@app.get("/api/toezicht/vestigingen")
def api_toezicht_vestigingen():
    """De vestigingen in het register, voor de kiezer op de pagina -- alleen de velden die een
    keuze tonen, niet het volledige dossier per vestiging (dat is een afzonderlijke, zwaardere
    aanroep, zie `api_toezicht_dossier`).

    **Eindreview, bevinding 1.** `id` is niet `locatiecode`: 8 van de 69 locatiecodes dekken twee
    vergunningen van dezelfde vestiging (zie `toezicht_register.identiteiten`), en vóór deze fix
    loste `api_toezicht_dossier` zo'n dubbele code altijd naar de eerste op -- de andere, en elk
    signaal dat zij zou opleveren, was onbereikbaar, zonder dat ergens zichtbaar werd dat hij
    bestond. `id` is wat `api_toezicht_dossier` nu opzoekt; `kenmerk` staat erbij zodat de kiezer
    de twee vergunningen van zo'n vestiging ook echt als twee dingen kan tonen, niet als twee keer
    dezelfde regel."""
    try:
        register = _toezicht_register()
    except ConnectorError as exc:
        raise HTTPException(status_code=503, detail=str(exc))
    ids = toezicht_register.identiteiten(register)
    return [{"id": i, "locatiecode": v.get("locatiecode"), "naam": v.get("naam"),
             "plaats": v.get("plaats"), "kenmerk": v.get("kenmerk")}
            for i, v in zip(ids, register)]


@app.get("/api/toezicht/dossier")
def api_toezicht_dossier(vestiging: str):
    """Draait de standaardpijplijn (`lees_vergunning` -> `bepaal_signalen` ->
    `stel_dossier_samen` -> `leg_signalen_uit`) echt, met de drie bronnen voor de uitlegger
    bekabeld (R20): `aquo_ref`, `normenset` en de Stelselcatalogus-connector. Geen taalmodel
    hier (`llm=None`) -- de deterministische treffers uit die drie bronnen zijn al genoeg voor
    een `waarom`, en de pagina mag niet wachten op een externe aanroep naar het lokale model om
    die te tonen.

    `vestiging` is de `id` die `api_toezicht_vestigingen` teruggaf (`toezicht_register.
    identiteiten`), niet de rauwe `locatiecode` -- zie de moduledocstring van `register.py` voor
    waarom `locatiecode` alleen geen bruikbare sleutel is (eindreview, bevinding 1).

    `context` draagt alleen `stoffen_met_norm` (eindreview, optionele eenregelfix): dit lab heeft
    geen betrouwbare, snel te bevragen bron voor `gemeten_codes` (dat vraagt de 142 MB ruwe
    WKP-CSV, zie `test_toezicht_live.py`) of een live waterlichaam-opzoeking per vestiging, maar
    `graaf.stoffen_met_norm(normenset)` leest exact dezelfde `normenset` die hier al wordt
    opgehaald voor de uitlegger, en is al getest (`test_toezicht_graaf.py`). Zonder deze sleutel
    bleef signaal 1 (`geen_onafhankelijke_meting`) permanent op `midden` steken, ook voor een
    stof met een echte KRW-norm -- de escalatie naar `hoog` bestond in `signalen.py` wel, maar was
    vanaf dit eindpunt onbereikbaar. `dossier()` zet elke andere ontbrekende contextsleutel zelf
    om in een expliciet voorbehoud (`d["voorbehouden"]`) in plaats van er iets bij te verzinnen --
    een gat is hier een signaal, geen gebrek dat verstopt moet worden."""
    try:
        register = _toezicht_register()
    except ConnectorError as exc:
        raise HTTPException(status_code=503, detail=str(exc))
    ids = toezicht_register.identiteiten(register)
    v = next((p for i, p in zip(ids, register) if i == vestiging), None)
    if v is None:
        raise HTTPException(status_code=404, detail=f"onbekende vestiging: {vestiging}")

    crew = toezicht_runner.laad(TOEZICHT_AGENTS_PAD, TOEZICHT_TASKS_PAD)
    log = toezicht_runlog.Runlog()
    normenset = _toezicht_normenset()
    invoer = {
        "vestiging": v,
        "context": {"stoffen_met_norm": toezicht_graaf.stoffen_met_norm(normenset)},
        "aquo_ref": _toezicht_aquo_ref(),
        "normenset": normenset,
        "stelselcatalogus": _stelselcatalogus(),
    }
    staat = crew.draai(invoer, llm=None, runlog=log)
    dossier = dict(staat["dossier"])
    # `dossier()` zet zelf al een `runlog`-sleutel, maar dat is een foto vóór haar eigen stap en
    # vóór de uitlegger erna (zie `dossier._signalen_stap`/`dossier.dossier`): op het moment dat
    # `tool_dossier_samenstellen` haar aanroept, heeft de meegegeven `log` alleen de twee stappen
    # ervóór. Hier is de hele run al klaar, dus vervang alleen `stappen` door de volledige, echte
    # log -- `uitgezet` komt uit `dossier()` zelf (zij leest `uit` uit de staat), niet
    # hardgecodeerd: zodra `invoer["uit"]` ooit gevuld wordt, moet die lijst meereizen in plaats
    # van stil te verdwijnen.
    bestaand_runlog = dossier.get("runlog") or {}
    dossier["runlog"] = {"uitgezet": bestaand_runlog.get("uitgezet", []),
                          "stappen": log.als_gegeven()}
    return dossier


# -- /wasstraat: de papierbevindingen op het Maas-lozingenregister -------------------------------
#
# Splitsing van `/toezicht` (plan: `docs/superpowers/plans/2026-11-14-wasstraat-en-toezicht-
# splitsen.md`): zelfde register, zelfde standaardpijplijn, andere lezer. Deze route draait de
# pijplijn opnieuw in plaats van de uitkomst van `api_toezicht_dossier` te hergebruiken -- beide
# routes mogen onafhankelijk van elkaar blijven werken als de een ooit verandert, en `/toezicht`
# blijft daarmee letterlijk ongewijzigd (zie de taakbrief: "zorg alleen dat je wijziging aan
# signalen.py hem niet breekt"). Het echte hergebruik zit in `wasstraat_dossier_mod.
# papier_dossier()`, die op het volledige dossier van `toezicht.dossier.dossier()` filtert in
# plaats van er een tweede samensteller naast te zetten.

@app.get("/wasstraat", response_class=HTMLResponse)
def wasstraat_page():
    """Papierdossier voor de vergunningverlener op het Maas-lozingenregister: niet waar een
    toezichthouder moet gaan kijken, maar wat er aan de vergunning zelf moet rechtkomen."""
    return _waterpagina("wasstraat.html", "wasstraat")


@app.get("/api/wasstraat/pijplijn")
def api_wasstraat_pijplijn():
    """Dezelfde configuratie als `/api/toezicht/pijplijn` -- één pijplijn, twee lezers, dus één
    bron voor de pagina die toont hoe zij is opgebouwd (R4: geen crew gestart, geen validatie)."""
    gegeven = toezicht_pijplijn.als_gegeven(TOEZICHT_AGENTS_PAD, TOEZICHT_TASKS_PAD)
    return {**gegeven, "bron": TOEZICHT_AGENTS_PAD}


@app.get("/api/wasstraat/vestigingen")
def api_wasstraat_vestigingen():
    """Dezelfde vestigingenlijst als `/api/toezicht/vestigingen`, op dezelfde manier
    geïdentificeerd (`toezicht_register.identiteiten`, want `locatiecode` alleen is geen unieke
    sleutel -- zie die module)."""
    try:
        register = _toezicht_register()
    except ConnectorError as exc:
        raise HTTPException(status_code=503, detail=str(exc))
    ids = toezicht_register.identiteiten(register)
    return [{"id": i, "locatiecode": v.get("locatiecode"), "naam": v.get("naam"),
             "plaats": v.get("plaats"), "kenmerk": v.get("kenmerk")}
            for i, v in zip(ids, register)]


@app.get("/api/wasstraat/dossier")
def api_wasstraat_dossier(vergunning: str):
    """Draait de standaardpijplijn echt (`lees_vergunning` -> `bepaal_signalen` ->
    `stel_dossier_samen` -> `leg_signalen_uit`), met dezelfde drie bronnen voor de uitlegger als
    `/api/toezicht/dossier` -- en filtert de uitkomst daarna naar de zeven papiersignalen
    (`wasstraat_dossier_mod.papier_dossier`). Geen taalmodel hier (`llm=None`): dezelfde reden als
    bij `/toezicht` -- de deterministische treffers uit de drie bronnen zijn al genoeg, en de
    pagina mag niet op het lokale model wachten.

    `vergunning` is de `id` die `api_wasstraat_vestigingen` teruggaf, niet de rauwe
    `locatiecode` -- zelfde reden als bij `/toezicht` (zie `toezicht_register.identiteiten`)."""
    try:
        register = _toezicht_register()
    except ConnectorError as exc:
        raise HTTPException(status_code=503, detail=str(exc))
    ids = toezicht_register.identiteiten(register)
    v = next((p for i, p in zip(ids, register) if i == vergunning), None)
    if v is None:
        raise HTTPException(status_code=404, detail=f"onbekende vergunning: {vergunning}")

    crew = toezicht_runner.laad(TOEZICHT_AGENTS_PAD, TOEZICHT_TASKS_PAD)
    log = toezicht_runlog.Runlog()
    normenset = _toezicht_normenset()
    invoer = {
        "vestiging": v,
        "context": {"stoffen_met_norm": toezicht_graaf.stoffen_met_norm(normenset)},
        "aquo_ref": _toezicht_aquo_ref(),
        "normenset": normenset,
        "stelselcatalogus": _stelselcatalogus(),
    }
    staat = crew.draai(invoer, llm=None, runlog=log)
    volledig = dict(staat["dossier"])
    # Zelfde correctie als `api_toezicht_dossier`: `dossier()` zet zelf al een `runlog`-sleutel,
    # maar dat is een foto vóór haar eigen stap en vóór de uitlegger erna. Vervang `stappen` door
    # de volledige, echte log; `uitgezet` komt uit `dossier()` zelf.
    bestaand_runlog = volledig.get("runlog") or {}
    volledig["runlog"] = {"uitgezet": bestaand_runlog.get("uitgezet", []),
                           "stappen": log.als_gegeven()}
    return wasstraat_dossier_mod.papier_dossier(volledig)


@app.get("/water", response_class=HTMLResponse)
def water_page():
    """Het waterdossier: één ingang voor wat over vier tabs verspreid stond."""
    return _waterpagina("water.html", "overzicht")


@app.get("/api/water/hub")
def api_water_hub():
    """De leden, gedeelde lijnen, dekking en Atlas-positionering van het waterdossier."""
    return water_hub_mod.overzicht()


@app.get("/api/lozing/architectuur")
def api_lozing_architectuur():
    """Doelarchitectuur voor één directe lozing op een rijkswater."""
    return lozing_mod.architectuur()


@app.get("/api/lozing/keten")
def api_lozing_keten(live: int = 1, straal: int = 1000):
    """Doorloop de lozingsketen op de synthetische casus; live bevraagt RWS-KRW en PDOK."""
    straal_m = max(100, min(int(straal), 5000))
    return lozing_keten_motor.run_keten(live=bool(live), straal_m=straal_m)


@app.get("/api/dvth/architectuur")
def api_dvth_architectuur():
    """Doelarchitectuur D-VTH voor één MBA Seveso: componenten, koppelvlakken, keten en roadmap."""
    return dvth_mod.architectuur()


@app.get("/api/dvth/keten")
def api_dvth_keten(live: int = 1, straal: int = 1000):
    """Doorloop de D-VTH-keten op de synthetische Seveso-casus.

    live=1 bevraagt de echte REV-WFS en BAG rond het RD-punt; live=0 slaat dat over.
    De straal is begrensd zodat de publieke bronnen niet onbeperkt bevraagd worden.
    """
    straal_m = max(100, min(int(straal), 5000))
    return dvth_keten_motor.run_keten(live=bool(live), straal_m=straal_m)


@app.get("/api/vth/bronnen")
def api_vth_bronnen():
    """Bronnenlandschap gemapt op de kern-objecttypen van het Cim-VTH-Flo."""
    return vth_bronnen_mod.catalogus()


@app.get("/api/vth/bronnen/check")
async def api_vth_bronnen_check():
    """Roep de endpoints van de catalogus live aan — maakt open/gesloten verifieerbaar."""
    res = await vth_bronnen_mod.check_endpoints()
    return {"gecontroleerd_op": datetime.now(timezone.utc).isoformat(timespec="seconds"),
            "resultaat": res}


@app.get("/health")
def health():
    return {"status": "ok", "project": "geluidsmeter", "ts": datetime.now(timezone.utc).isoformat()}


@app.get("/latest")
def latest():
    feature = _latest_feature()
    if not feature:
        return JSONResponse({"error": "geen data vandaag"}, status_code=404)
    return feature


@app.get("/metadata")
def metadata():
    return {
        "project": _config.get("project", {}),
        "measurement": {k: v for k, v in _config.get("measurement", {}).items() if k != "device_name"},
        "api_port": _config.get("api", {}).get("port", 8792),
    }


@app.get("/summary")
def summary():
    """Dagprofiel + laatste meting voor dashboard."""
    processed_dir = Path(_config["outputs"]["processed_dir"])
    today = datetime.now(timezone.utc).strftime("%Y%m%d")

    profile_path = processed_dir / f"daily_profile_{today}.json"
    profile = json.loads(profile_path.read_text()) if profile_path.exists() else {}

    offset = _config.get("measurement", {}).get("calibration_offset_db", 0)
    feature = _latest_feature()
    rms_dba = None
    if feature:
        rms_dba = round(feature["rms_dbfs"] + offset, 1)

    raw_dir = Path(_config["outputs"]["raw_features_dir"])
    history = []
    for fp in sorted(raw_dir.glob("sound_features_*.jsonl"))[-7:]:
        with open(fp) as f:
            for line in f:
                row = json.loads(line)
                history.append({"ts": row["ts"], "rms_dbfs": row["rms_dbfs"],
                                 "dba_est": round(row["rms_dbfs"] + offset, 1)})

    loc = load_private_location(_config)
    precision_m = _config.get("location", {}).get("public_location_precision_m", 100)
    pub_lat, pub_lon = _round_location(loc["lat"], loc["lon"], precision_m)

    rivm_lden = None
    rivm_path = Path(_config["outputs"]["external_dir"]) / "rivm" / "geluid_buurt.geojson"
    if rivm_path.exists():
        rivm_gdf = gpd.read_file(rivm_path)
        rivm_lden = get_rivm_lden(ShapelyPoint(loc["lon"], loc["lat"]), rivm_gdf)

    return {
        "today": today,
        "rms_dba_latest": rms_dba,
        "calibration_offset_db": offset,
        "calibrated": offset != 0,
        "profile": profile,
        "history": history[-10080:],
        "norm_lden": 48,
        "norm_lnight": 43,
        "rivm_lden": rivm_lden,
        "location": {"lat": pub_lat, "lon": pub_lon, "precision_m": precision_m},
    }


@app.get("/api/locations")
def api_locations():
    offset = _config.get("measurement", {}).get("calibration_offset_db", 0)
    feature = _latest_feature()
    # Zonder kalibratie (offset=0) is rms_dbfs negatief — niet vergelijkbaar met norm in dB(A)
    calibrated = offset != 0
    rms_dba = round(feature["rms_dbfs"] + offset, 1) if (feature and calibrated) else None

    loc = load_private_location(_config)
    precision_m = _config.get("location", {}).get("public_location_precision_m", 100)
    pub_lat, pub_lon = _round_location(loc["lat"], loc["lon"], precision_m)

    rivm_lden = None
    rivm_path = Path(_config["outputs"]["external_dir"]) / "rivm" / "geluid_buurt.geojson"
    if rivm_path.exists():
        rivm_gdf = gpd.read_file(rivm_path)
        rivm_lden = get_rivm_lden(ShapelyPoint(loc["lon"], loc["lat"]), rivm_gdf)

    return [_location_entry(_config, pub_lat, pub_lon, rms_dba, rivm_lden)] + _mobile_location_entries(rivm_gdf if rivm_path.exists() else None)


@app.post("/api/submit", status_code=201)
def api_submit(
    submission: MobileSubmission,
    authorization: str | None = Header(default=None),
):
    submit_token = _config.get("mobile", {}).get("submit_token", "")
    if not submit_token or authorization != f"Bearer {submit_token}":
        raise HTTPException(status_code=401, detail="Ongeldige token")

    record = {
        "id": str(uuid.uuid4()),
        "ts": datetime.now(timezone.utc).isoformat(),
        "lat": submission.lat,
        "lon": submission.lon,
        "naam": submission.naam,
        "dba": submission.dba,
        "source": "mobile",
        "kwaliteit": _config.get("project", {}).get(
            "quality_label", "prototype_indicatief_niet_juridisch"
        ),
    }

    fp = Path(_config["mobile"]["measurements_file"])
    fp.parent.mkdir(parents=True, exist_ok=True)
    with open(fp, "a") as f:
        f.write(json.dumps(record) + "\n")

    return {"id": record["id"], "accepted": True}


@app.get("/geodata/rivm")
def geodata_rivm():
    p = Path(_config["outputs"]["external_dir"]) / "rivm" / "geluid_buurt.geojson"
    if not p.exists():
        return JSONResponse({"type": "FeatureCollection", "features": []})
    return JSONResponse(json.loads(p.read_text()))


@app.get("/geodata/nwb")
def geodata_nwb():
    p = Path(_config["outputs"]["external_dir"]) / "atlas" / "nwb_wegvakken.geojson"
    if not p.exists():
        return JSONResponse({"type": "FeatureCollection", "features": []})
    return JSONResponse(json.loads(p.read_text()))


@app.get("/geodata/bgt")
def geodata_bgt():
    p = Path(_config["outputs"]["external_dir"]) / "bgt" / "bgt_wegdeel.geojson"
    if not p.exists():
        return JSONResponse({"type": "FeatureCollection", "features": []})
    return JSONResponse(json.loads(p.read_text()))


@app.get("/dashboard", response_class=HTMLResponse)
def dashboard():
    return (_static_dir / "dashboard.html").read_text()


@app.get("/public", response_class=HTMLResponse)
def public_page():
    return (_static_dir / "public.html").read_text()


@app.get("/meten", response_class=HTMLResponse)
def meten_page():
    return (_static_dir / "meten.html").read_text()


def _rev_connector() -> RevConnector:
    ll = _config.get("leefomgevinglab", {})
    rev = ll.get("rev", {})
    return RevConnector(
        base_url=rev.get("ogc_base_url", ""),
        collections=rev.get("collections", []),
        max_features=rev.get("max_features", 500),
        cache_dir=ll.get("cache_dir", "/tmp/llab_cache"),
    )


@app.get("/api/rev/features")
def api_rev_features(bbox: str):
    try:
        return _rev_connector().features(bbox)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    except ConnectorError as exc:
        raise HTTPException(status_code=503, detail=str(exc))


class DuidingRequest(BaseModel):
    properties: dict


@app.post("/api/duiding")
def api_duiding(req: DuidingRequest):
    ll = _config.get("leefomgevinglab", {})
    llm = ll.get("llm", {})
    try:
        return rev_service.duiding(
            req.properties,
            llm_base_url=llm.get("base_url", "http://localhost:8080/v1"),
            model=llm.get("model", "qwen2.5-32b"),
            timeout_s=llm.get("timeout_s", 60),
        )
    except ConnectorError as exc:
        raise HTTPException(status_code=503, detail=str(exc))


@app.get("/viewer", response_class=HTMLResponse)
def viewer_page():
    viewer_html = Path(__file__).parent.parent / "viewer" / "static" / "viewer.html"
    return viewer_html.read_text()


def _dso_env_key(env: str) -> str | None:
    """Productie- of pre-key uit .env op basis van de gekozen omgeving."""
    return os.environ.get("DSO_API_KEY_PROD") if env == "prod" else os.environ.get("DSO_API_KEY")


def _dso_base_url(dso: dict, endpoint: str, env: str) -> str:
    """Base-URL voor een endpoint (zoek|rtr|uitvoeren) in de gekozen omgeving (pre|prod)."""
    return dso.get(env, {}).get(f"{endpoint}_base_url", "")


def _zoek_connector() -> ZoekConnector:
    ll = _config.get("leefomgevinglab", {})
    dso = ll.get("dso", {})
    env = dso.get("zoek_env", "pre")
    return ZoekConnector(
        base_url=_dso_base_url(dso, "zoek", env),
        api_key=_dso_env_key(env),
        api_key_header=dso.get("api_key_header", "x-api-key"),
        cache_dir=ll.get("cache_dir", "/tmp/llab_cache"),
    )


def _dso_connector() -> DsoConnector:
    ll = _config.get("leefomgevinglab", {})
    dso = ll.get("dso", {})
    rtr_env = dso.get("rtr_env", "pre")
    uitv_env = dso.get("uitvoeren_env", "pre")
    return DsoConnector(
        rtr_base_url=_dso_base_url(dso, "rtr", rtr_env),
        uitvoeren_base_url=_dso_base_url(dso, "uitvoeren", uitv_env),
        rtr_api_key=_dso_env_key(rtr_env),
        uitvoeren_api_key=_dso_env_key(uitv_env),
        api_key_header=dso.get("api_key_header", "x-api-key"),
        cache_dir=ll.get("cache_dir", "/tmp/llab_cache"),
    )


def _ozon_connector() -> OzonConnector:
    ll = _config.get("leefomgevinglab", {})
    ozon = ll.get("ozon", {})
    env = ozon.get("environment", "pre")
    return OzonConnector(
        base_url=ozon.get(env, {}).get("base_url", ""),
        api_key=_dso_env_key(env),
        api_key_header=ozon.get("api_key_header", "x-api-key"),
        cache_dir=ll.get("cache_dir", "/tmp/llab_cache"),
    )


def _ev_connector() -> ExterneVeiligheidConnector:
    ll = _config.get("leefomgevinglab", {})
    ev = ll.get("externe_veiligheid", {})
    return ExterneVeiligheidConnector(
        wfs_url=ev.get("wfs_url", ""),
        cache_dir=ll.get("cache_dir", "/tmp/llab_cache"),
    )


def _llm_cfg() -> dict:
    llm = _config.get("leefomgevinglab", {}).get("llm", {})
    return {
        "llm_base_url": llm.get("base_url", "http://localhost:8080/v1"),
        "model": llm.get("model", "qwen2.5-32b"),
        "timeout_s": llm.get("timeout_s", 60),
    }


class RegelsRequest(BaseModel):
    activiteit: str
    locatie: dict | None = None


@app.post("/api/regels")
def api_regels(req: RegelsRequest):
    if not req.locatie or "lat" not in req.locatie or "lon" not in req.locatie:
        raise HTTPException(status_code=422, detail="locatie met lat en lon is verplicht")
    return vergunningen_service.regels_opzoeken(
        req.activiteit, req.locatie, _zoek_connector(), _dso_connector(), _llm_cfg()
    )


def _rag_embed_fn():
    rag = _config.get("leefomgevinglab", {}).get("rag", {})
    emb = rag.get("embed", {})
    return partial(embed_texts, base_url=emb.get("base_url", ""), model=emb.get("model", ""))


def _rag_store():
    rag = _config.get("leefomgevinglab", {}).get("rag", {})
    try:
        return VectorStore.load(rag.get("store_dir", ""))
    except FileNotFoundError:
        return None


class ChatRequest(BaseModel):
    vraag: str
    locatie: dict | None = None


@app.post("/api/chat")
def api_chat(req: ChatRequest):
    store = _rag_store()
    if store is None:
        return {
            "vraag": req.vraag, "antwoord": None, "bronnen": [], "regels": None, "omgevingsplan": None,
            "externe_veiligheid": None,
            "onzekerheid": True, "disclaimer": chatbot.DISCLAIMER, "vangnet": chatbot.VANGNET,
            "beschikbaar": False,
        }
    rag = _config.get("leefomgevinglab", {}).get("rag", {})
    llm = _config.get("leefomgevinglab", {}).get("llm", {})
    ozon_cfg = _config.get("leefomgevinglab", {}).get("ozon", {})

    def regels_fn(vraag: str, locatie: dict) -> dict:
        activiteit = vergunningen_resolver.extract_activiteit(
            vraag, llm.get("base_url", "http://localhost:8080/v1"),
            llm.get("model", "qwen2.5-32b"), llm.get("timeout_s", 60),
        )
        return vergunningen_service.regels_opzoeken(
            activiteit, locatie, _zoek_connector(), _dso_connector(), _llm_cfg()
        )

    def omgevingsplan_fn(locatie: dict):
        return omgevingsplan_mod.omgevingsplan_op_locatie(
            locatie, _ozon_connector(),
            max_regelingen=ozon_cfg.get("max_regelingen", 3),
            max_regelteksten=ozon_cfg.get("max_regelteksten", 5),
        )

    ev_cfg = _config.get("leefomgevinglab", {}).get("externe_veiligheid", {})

    def ev_fn(locatie: dict):
        return externe_veiligheid_mod.check_aandachtsgebieden(
            locatie, _ev_connector(), ev_cfg.get("lagen", {}), max_n=ev_cfg.get("max_features", 5))

    return chatbot.beantwoord(
        req.vraag, store, _rag_embed_fn(),
        llm_base_url=llm.get("base_url", "http://localhost:8080/v1"),
        model=llm.get("model", "qwen2.5-32b"),
        top_k=rag.get("top_k", 4), timeout_s=llm.get("timeout_s", 60),
        locatie=req.locatie, regels_fn=regels_fn, omgevingsplan_fn=omgevingsplan_fn,
        ev_fn=ev_fn,
    )


@app.get("/chatbot", response_class=HTMLResponse)
def chatbot_page():
    return (Path(__file__).parent.parent / "static" / "chat.html").read_text()


def _semantiek_graph():
    sem = _config.get("leefomgevinglab", {}).get("semantiek", {})
    return semantiek_graph.load_graph(sem.get("store_dir", ""))


@app.get("/api/semantiek/graph")
def api_semantiek_graph(zoekTerm: str | None = None, bron: str | None = None):
    graph = _semantiek_graph()
    if graph is None:
        return {"elements": {"nodes": [], "edges": []}, "bronnen": [], "beschikbaar": False}
    nodes, edges = graph["nodes"], graph["edges"]
    if bron:
        keep = {n["data"]["id"] for n in nodes if n["data"]["bron"] in (bron, "IMX-Geo")}
        nodes = [n for n in nodes if n["data"]["id"] in keep]
        edges = [e for e in edges if e["data"]["source"] in keep and e["data"]["target"] in keep]
    if zoekTerm:
        z = zoekTerm.lower()
        match = {n["data"]["id"] for n in nodes
                 if z in n["data"]["label"].lower() or z in (n["data"].get("definitie") or "").lower()}
        keep = set(match)
        for e in edges:
            if e["data"]["source"] in match:
                keep.add(e["data"]["target"])
            if e["data"]["target"] in match:
                keep.add(e["data"]["source"])
        nodes = [n for n in nodes if n["data"]["id"] in keep]
        edges = [e for e in edges if e["data"]["source"] in keep and e["data"]["target"] in keep]
    return {"elements": {"nodes": nodes, "edges": edges}, "bronnen": graph["bronnen"], "beschikbaar": True}


@app.get("/api/semantiek/node")
def api_semantiek_node(uri: str):
    graph = _semantiek_graph()
    if graph is None:
        raise HTTPException(status_code=404, detail="Geen graaf beschikbaar")
    by_id = {n["data"]["id"]: n for n in graph["nodes"]}
    node = by_id.get(uri)
    if node is None:
        raise HTTPException(status_code=404, detail="Node niet gevonden")
    buren = []
    for e in graph["edges"]:
        if e["data"]["source"] == uri and e["data"]["target"] in by_id:
            buren.append({"node": by_id[e["data"]["target"]], "relatie": e["data"]["relatie"]})
        elif e["data"]["target"] == uri and e["data"]["source"] in by_id:
            buren.append({"node": by_id[e["data"]["source"]], "relatie": e["data"]["relatie"]})
    return {"node": node, "buren": buren}


@app.get("/semantiek", response_class=HTMLResponse)
def semantiek_page():
    return (Path(__file__).parent.parent / "static" / "semantiek.html").read_text()


def _ld_graph():
    ld = _config.get("leefomgevinglab", {}).get("ld", {})
    return ld_store.load_graph(ld.get("store_dir", ""))


class LdSparqlRequest(BaseModel):
    query: str


@app.post("/api/ld/sparql")
def api_ld_sparql(req: LdSparqlRequest):
    g = _ld_graph()
    if g is None:
        return {"rows": [], "beschikbaar": False}
    try:
        return {"rows": ld_store.run_sparql(g, req.query), "beschikbaar": True}
    except Exception as exc:
        raise HTTPException(status_code=400, detail=f"Ongeldige SPARQL: {exc}")


def _dv_graph():
    ld = _config.get("leefomgevinglab", {}).get("ld", {})
    return ld_store.load_graph(ld.get("store_dir", ""))


def _dv_grounding():
    shapes = Path(__file__).parent.parent / "leefomgevinglab" / "ld" / "shapes.ttl"
    txt = shapes.read_text() if shapes.exists() else ""
    return dv_grounding.build_grounding(txt)


class DatavraagRequest(BaseModel):
    vraag: str


@app.post("/api/datavraag")
def api_datavraag(req: DatavraagRequest):
    g = _dv_graph()
    ll = _config.get("leefomgevinglab", {})
    llm = ll.get("llm", {})
    ld = ll.get("ld", {})
    return dv_service.beantwoord(
        req.vraag, g, _dv_grounding(),
        llm_base_url=llm.get("base_url", "http://localhost:8080/v1"),
        model=llm.get("model", "qwen2.5-32b"), timeout_s=llm.get("timeout_s", 60),
        kkg_endpoint=ld.get("kkg_endpoint", ""), provincie=ld.get("provincie", "Zuid-Holland"),
        straal_m=ld.get("nabijheid_straal_m", 500))


@app.get("/datavraag", response_class=HTMLResponse)
def datavraag_page():
    return (Path(__file__).parent.parent / "static" / "datavraag.html").read_text()


def _afval_data_dir() -> str:
    return _config.get("leefomgevinglab", {}).get("afval", {}).get(
        "data_dir", "/mnt/nvme/geluidsmeter/data/external/afval")


def _afvaldb_path() -> str:
    return _config.get("leefomgevinglab", {}).get("afvaldb", {}).get(
        "db_path", "/mnt/nvme/geluidsmeter/data/external/afval/afval.duckdb")


@app.get("/api/afval/forecast")
def api_afval_forecast(regio: str, afvalstroom: str):
    if not Path(_afvaldb_path()).exists():
        raise HTTPException(status_code=503, detail="Afval-database nog niet gevuld")
    return afval_service.forecast(_afvaldb_path(), regio, afvalstroom)


@app.get("/afval", response_class=HTMLResponse)
def afval_page():
    return (Path(__file__).parent.parent / "static" / "afval.html").read_text()


@app.get("/api/afval/meta")
def api_afval_meta():
    try:
        return afval_service.meta(_afval_data_dir())
    except FileNotFoundError:
        raise HTTPException(status_code=503, detail="Afval-aggregaat nog niet ingeladen")


@app.get("/api/afval/choropleth")
def api_afval_choropleth(afvalstroom: str, jaar: int, indicator: str = "volume"):
    try:
        return afval_service.choropleth(_afval_data_dir(), afvalstroom, jaar, indicator)
    except FileNotFoundError:
        raise HTTPException(status_code=503, detail="Afval-aggregaat nog niet ingeladen")


@app.get("/api/afval/trend")
def api_afval_trend(regio: str, afvalstroom: str):
    try:
        return afval_service.trend(_afval_data_dir(), regio, afvalstroom)
    except FileNotFoundError:
        raise HTTPException(status_code=503, detail="Afval-aggregaat nog niet ingeladen")


class AfvalDuidingRequest(BaseModel):
    regio: str
    afvalstroom: str
    jaar: int


@app.post("/api/afval/duiding")
def api_afval_duiding(req: AfvalDuidingRequest):
    ll = _config.get("leefomgevinglab", {})
    llm = ll.get("llm", {})
    try:
        ctx = afval_service.stroom_context(_afval_data_dir(), req.regio, req.afvalstroom, req.jaar)
    except FileNotFoundError:
        raise HTTPException(status_code=503, detail="Afval-aggregaat nog niet ingeladen")
    if Path(_afvaldb_path()).exists():
        try:
            fc = afval_service.forecast(_afvaldb_path(), req.regio, req.afvalstroom)
            ctx["forecast"] = fc["forecast"][-1] if fc["forecast"] else None
            ctx["extra"] = afval_service.extra_context(_afvaldb_path(), req.afvalstroom)
        except Exception:
            ctx["forecast"] = None
            ctx["extra"] = None
    else:
        ctx["forecast"] = None
        ctx["extra"] = None
    try:
        out = afval_duiding.duiding(
            ctx["naam"], req.afvalstroom, req.jaar, ctx,
            llm_base_url=llm.get("base_url", "http://localhost:8080/v1"),
            model=llm.get("model", "qwen2.5-32b"),
            timeout_s=llm.get("timeout_s", 60),
        )
    except ConnectorError:
        # LLM offline: de kerncijfers blijven waardevol, dus context wél teruggeven.
        out = {"duiding": None, "bron": afval_duiding.BRON, "disclaimer": afval_duiding.DISCLAIMER}
    out["context"] = ctx
    return out


_AFVAL_BRON_OMSCHRIJVING = {
    "cbs-": "Gemeentelijke afvalstoffen per provincie en jaar (CBS StatLine 83558NED).",
    "clo-": "Huishoudelijk afval per inwoner, lange tijdreeks (Compendium voor de Leefomgeving).",
    "afvalfonds-": "Recyclingpercentages per verpakkingsmateriaal (Afvalfonds Verpakkingen/Verpact).",
    "lma-rws-": "Nationale afvalcijfers per Euralcode en verwerking (LMA/RWS, openbaar).",
}


def _afval_bron_omschrijving(bron_id: str) -> str:
    for prefix, tekst in _AFVAL_BRON_OMSCHRIJVING.items():
        if bron_id.startswith(prefix):
            return tekst
    return ""


@app.get("/api/afval/bronnen")
def api_afval_bronnen():
    if not Path(_afvaldb_path()).exists():
        raise HTTPException(status_code=503, detail="Afval-database nog niet gevuld")
    con = afvaldb_store.open_readonly(_afvaldb_path())
    try:
        rows = afvaldb_store.bronnen(con)
    finally:
        if hasattr(con, "close"):
            con.close()
    for r in rows:
        r["omschrijving"] = _afval_bron_omschrijving(r["bron_id"])
    return rows


class AfvalChatRequest(BaseModel):
    vraag: str


@app.post("/api/afval/chat")
def api_afval_chat(req: AfvalChatRequest):
    llm = _config.get("leefomgevinglab", {}).get("llm", {})
    return afval_chat.beantwoord(
        req.vraag, _afvaldb_path(),
        llm_base_url=llm.get("base_url", "http://localhost:8080/v1"),
        model=llm.get("model", "qwen2.5-32b"),
        timeout_s=llm.get("timeout_s", 60),
    )
