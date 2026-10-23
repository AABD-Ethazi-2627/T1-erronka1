"""CNC Guard — Streamlit panela."""

import os
import time

import altair as alt
import pandas as pd
import requests
import streamlit as st

from config import (API_PASSWORD, API_URL, API_USERNAME, ES_INDEX, ES_URL,
                    MAILAK, TELEGRAM_CHAT_ID, TELEGRAM_TOKEN)
from ui.theme import apply_theme, current_theme, render_theme_switch

SVG_FACTORY = '<svg viewBox="0 0 24 24" aria-hidden="true"><path fill="currentColor" d="M3 21h18v-2H3v2Zm2-4h3V8H5v9Zm5 0h4V3h-4v14Zm6 0h3v-6h-3v6Z"/></svg>'
SVG_SHIELD = '<svg viewBox="0 0 24 24" aria-hidden="true"><path fill="currentColor" d="M12 2 4 5v6c0 5.2 3.4 9.8 8 11 4.6-1.2 8-5.8 8-11V5l-8-3Zm-1 14-3-3 1.4-1.4L11 13.2l3.6-3.6L16 11l-5 5Z"/></svg>'
SVG_ALERT = '<svg viewBox="0 0 24 24" aria-hidden="true"><path fill="currentColor" d="M12 3 1.8 20h20.4L12 3Zm1 13h-2v-2h2v2Zm0-4h-2V8h2v4Z"/></svg>'
SVG_CLOCK = '<svg viewBox="0 0 24 24" aria-hidden="true"><path fill="currentColor" d="M12 2a10 10 0 1 0 0 20 10 10 0 0 0 0-20Zm1 5h-2v6l5 3 1-1.7-4-2.3V7Z"/></svg>'


class ElasticsearchUnavailable(Exception):
    """El servicio de Elasticsearch no responde."""


class ElasticsearchIndexMissing(Exception):
    """El índice configurado todavía no existe."""

st.set_page_config(
    page_title="CNC Guard",
    page_icon="🛠️",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── Estilos ────────────────────────────────────────────────────────────────────
st.markdown("""
<style>
/* ── Fuente del sistema (sin petición de red) ── */
*, *::before, *::after {
    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', system-ui,
                 'Helvetica Neue', Arial, sans-serif !important;
    box-sizing: border-box;
}

/* ── Fondo app ── */
.stApp {
    background: #060d1a !important;
    color: #d8e6f3;
}
[data-testid="stHeader"]      { background: transparent !important; }
[data-testid="stToolbar"]     { display: none !important; }
.block-container              { max-width: 1500px; padding: 0 1rem .5rem !important; }

/* ── Sidebar fija, sin colapsar ── */
[data-testid="stSidebar"] {
    background: #07101d !important;
    border-right: 1px solid rgba(255,255,255,.05) !important;
    box-shadow: 3px 0 24px rgba(0,0,0,.45) !important;
    width: 200px !important;
    min-width: 200px !important;
    max-width: 200px !important;
    padding: 0 !important;
    transition: none !important;
}
section[data-testid="stSidebar"]                 { width: 200px !important; }
[data-testid="stSidebar"] > div:first-child       { padding-top: 0 !important; }
[data-testid="stSidebar"] > div                   { overflow: hidden; }

/* Ocultar botón colapsar y handle resize */
[data-testid="stSidebarCollapseButton"],
[data-testid="collapsedControl"],
button[title="Close sidebar"],
button[title="Open sidebar"],
[data-testid="stSidebarNavCollapseIcon"],
div[class*="ResizeHandle"],
div[class*="resizeHandle"] { display: none !important; }

/* Color base texto sidebar */
[data-testid="stSidebar"] * { color: #96b4d0 !important; }

/* ── Brand sidebar ── */
.sb-brand {
    padding: .9rem .85rem .5rem;
    border-bottom: 1px solid rgba(255,255,255,.04);
    margin-bottom: .25rem;
}
.sb-logo {
    font-size: 1.15rem;
    font-weight: 700;
    letter-spacing: -.03em;
    color: #deeeff !important;
    line-height: 1.1;
}
.sb-logo span { color: #4d9cf8 !important; }
.sb-sub {
    font-size: .52rem;
    font-weight: 600;
    letter-spacing: .13em;
    color: #253d58 !important;
    margin-top: .22rem;
    text-transform: uppercase;
}

/* ── Divider sidebar ── */
[data-testid="stSidebar"] hr {
    border-color: rgba(255,255,255,.05) !important;
    margin: .35rem .5rem !important;
}

/* ── Botones nav: todos iguales, alineados izquierda ── */
[data-testid="stSidebar"] .stButton {
    width: 100% !important;
    padding: 1.5px .5rem !important;
    margin: 0 !important;
    display: block !important;
}
[data-testid="stSidebar"] .stButton > button {
    width: 100% !important;
    height: 2.1rem !important;
    min-height: 2.1rem !important;
    max-height: 2.1rem !important;
    border: none !important;
    border-radius: 5px !important;
    background: transparent !important;
    color: #5c7a9a !important;
    text-align: left !important;
    justify-content: flex-start !important;
    padding: 0 .65rem !important;
    font-size: .75rem !important;
    font-weight: 500 !important;
    letter-spacing: .01em;
    transition: background .08s linear, color .08s linear !important;
    white-space: nowrap !important;
    overflow: hidden !important;
}
[data-testid="stSidebar"] .stButton > button:hover {
    background: rgba(255,255,255,.06) !important;
    color: #b8d4ee !important;
}
[data-testid="stSidebar"] .stButton > button[kind="primary"] {
    background: rgba(77,156,248,.11) !important;
    color: #7dbcfc !important;
    font-weight: 600 !important;
    border-left: 2px solid #4d9cf8 !important;
}
/* Streamlit reciente expone el tipo de botón mediante este test id. */
[data-testid="stSidebar"] [data-testid="stBaseButton-primary"] {
    background: rgba(77,156,248,.11) !important;
    color: #7dbcfc !important;
    font-weight: 600 !important;
    border-left: 2px solid #4d9cf8 !important;
}
/* Quitar outline/focus ring en botones */
[data-testid="stSidebar"] .stButton > button:focus {
    box-shadow: none !important;
    outline: none !important;
}

/* ── Panel estado sistema ── */
.sb-status {
    margin: .35rem .5rem .5rem;
    padding: .5rem .6rem;
    background: rgba(255,255,255,.018);
    border: 1px solid rgba(255,255,255,.045);
    border-radius: 6px;
    font-size: .65rem;
}
.sb-stitle {
    font-size: .5rem;
    font-weight: 700;
    letter-spacing: .14em;
    color: #1e3349 !important;
    text-transform: uppercase;
    margin-bottom: .28rem;
}
.sb-row {
    display: flex;
    align-items: center;
    gap: .35rem;
    padding: .15rem 0;
}
.sb-dot {
    width: 5px; height: 5px;
    border-radius: 50%;
    flex-shrink: 0;
}
.sb-dot.on  { background: #34d399; box-shadow: 0 0 5px rgba(52,211,153,.6); }
.sb-dot.off { background: #f87171; box-shadow: 0 0 5px rgba(248,113,113,.6); }
.sb-lbl { font-weight: 600; color: #4a6a88 !important; }
.sb-val { margin-left: auto; color: #3a5572 !important; font-size: .6rem; }

/* ── Header de página ── */
.page-header {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 1rem;
    margin: 0 -1rem .7rem;
    padding: .65rem 1rem;
    background: rgba(4,10,22,.7);
    border-bottom: 1px solid rgba(255,255,255,.05);
    position: sticky;
    top: 0;
    z-index: 100;
}
.page-header h2 {
    margin: 0 !important;
    font-size: 1.05rem !important;
    font-weight: 700 !important;
    color: #e8f3ff !important;
    letter-spacing: -.02em;
}
.page-header p {
    margin: .18rem 0 0 !important;
    color: #2e4d6a !important;
    font-size: .72rem !important;
}
.page-header p { display: none !important; }
.ph-badge {
    font-size: .62rem;
    font-weight: 600;
    color: #34d399 !important;
    white-space: nowrap;
    padding: .22rem .55rem;
    background: rgba(52,211,153,.06);
    border: 1px solid rgba(52,211,153,.12);
    border-radius: 20px;
    flex-shrink: 0;
}

/* ── Métricas ── */
[data-testid="stMetric"] {
    background: rgba(11,20,38,.6);
    border: 1px solid rgba(255,255,255,.06);
    border-radius: 9px;
    padding: .7rem .9rem;
    transition: border-color .1s linear, box-shadow .1s linear;
    box-shadow: 0 2px 14px rgba(0,0,0,.22);
}
[data-testid="stMetric"]:hover {
    border-color: rgba(77,156,248,.2);
    box-shadow: 0 4px 16px rgba(0,0,0,.25);
}
/* Borde superior de color por posición */
[data-testid="stHorizontalBlock"]:has([data-testid="stMetric"]) > div:nth-child(1) [data-testid="stMetric"] { border-top: 2px solid #34d399; }
[data-testid="stHorizontalBlock"]:has([data-testid="stMetric"]) > div:nth-child(2) [data-testid="stMetric"] { border-top: 2px solid #38bdf8; }
[data-testid="stHorizontalBlock"]:has([data-testid="stMetric"]) > div:nth-child(3) [data-testid="stMetric"] { border-top: 2px solid #fb923c; }
[data-testid="stHorizontalBlock"]:has([data-testid="stMetric"]) > div:nth-child(4) [data-testid="stMetric"] { border-top: 2px solid #a78bfa; }
[data-testid="stMetricLabel"] {
    color: #344e6a !important;
    font-size: .6rem !important;
    font-weight: 700 !important;
    letter-spacing: .06em;
    text-transform: uppercase;
}
[data-testid="stMetricValue"] {
    color: #e4f0ff !important;
    font-size: 1.35rem !important;
    font-weight: 700 !important;
}

/* Tarjetas KPI del dashboard */
.dash-kpis {
    display: grid;
    grid-template-columns: repeat(4, minmax(0, 1fr));
    gap: .7rem;
    margin-bottom: 1rem;
}
.dash-kpi {
    position: relative;
    min-width: 0;
    min-height: 4.35rem;
    padding: .85rem 1rem .7rem 1.15rem;
    overflow: hidden;
    border: 1px solid rgba(77,156,248,.09);
    border-radius: 5px;
    background: linear-gradient(135deg, #0a2038, #081a2e);
    box-shadow: 0 3px 12px rgba(0,0,0,.18);
    transition: border-color .1s linear, transform .1s linear;
}
.dash-kpi::before {
    content: "";
    position: absolute;
    inset: 0 auto 0 0;
    width: 3px;
    background: #22c55e;
}
.dash-kpi:hover {
    transform: translateY(-2px);
    border-color: rgba(77,156,248,.35);
}
.dash-kpi.alert::before { background: #ef233c; }
.dash-kpi.blue::before { background: #168cff; }
.dash-kpi-icon { float: left; width: 1.15rem; height: 1.15rem; margin: .05rem .65rem 0 0; color: #38bdf8; }
.dash-kpi-icon svg { width: 100%; height: 100%; }
.dash-kpi-label { color: #b7cbe0; font-size: .62rem; white-space: nowrap; }
.dash-kpi-value { margin-top: .18rem; color: #f3f8ff; font-size: 1.25rem; font-weight: 800; line-height: 1; }
.dash-kpi-value small { color: #c5d5e5; font-size: .65rem; font-weight: 600; }
.dash-kpi-detail { margin-top: .42rem; color: #8ea8c2; font-size: .53rem; }
.dash-kpi-detail strong { color: #34d399; }
@media (max-width: 900px) {
    .dash-kpis { grid-template-columns: repeat(2, minmax(0, 1fr)); }
}
@media (max-width: 560px) {
    .dash-kpis { grid-template-columns: 1fr; }
}

/* ── Gráficos nativos (line_chart, bar_chart) ── */
[data-testid="stArrowVegaLiteChart"],
[data-testid="stAltairChart"],
[data-testid="stVegaLiteChart"] {
    width: 100% !important;
    max-width: 100% !important;
    min-width: 0 !important;
    overflow: hidden !important;
    background: rgba(9,18,34,.55) !important;
    border: 1px solid rgba(255,255,255,.05) !important;
    border-radius: 9px !important;
    padding: .6rem .8rem .3rem !important;
    box-shadow: 0 2px 14px rgba(0,0,0,.2) !important;
}
[data-testid="stArrowVegaLiteChart"] > div,
[data-testid="stAltairChart"] > div,
[data-testid="stVegaLiteChart"] > div {
    max-width: 100% !important;
    overflow: hidden !important;
}
[data-testid="stCaptionContainer"] p {
    color: #d5e5f5 !important;
    font-weight: 700 !important;
    font-size: .72rem !important;
    letter-spacing: .02em !important;
    text-transform: none !important;
}

/* ── Títulos ── */
h1 { font-size: 1.2rem !important; font-weight: 700 !important; color: #e8f3ff !important; }
h2 { font-size: 1rem !important;   font-weight: 600 !important; color: #d4e6f5 !important; }
h3 { font-size: .88rem !important; font-weight: 600 !important; color: #a8c4de !important; }

/* ── Formularios ── */
[data-testid="stForm"] {
    background: rgba(9,18,34,.5) !important;
    border: 1px solid rgba(255,255,255,.055) !important;
    border-radius: 9px !important;
    padding: 1.1rem 1.3rem !important;
}
.stTextInput > div > div > input,
.stNumberInput > div > div > input {
    background: rgba(5,12,25,.7) !important;
    border-color: rgba(255,255,255,.08) !important;
    color: #d8e6f3 !important;
    border-radius: 6px !important;
}
.stTextInput > div > div > input:focus,
.stNumberInput > div > div > input:focus {
    border-color: #4d9cf8 !important;
    box-shadow: 0 0 0 2px rgba(77,156,248,.14) !important;
}
.stSelectbox > div > div {
    background: rgba(5,12,25,.7) !important;
    border-color: rgba(255,255,255,.08) !important;
    border-radius: 6px !important;
    color: #d8e6f3 !important;
}
.stFormSubmitButton > button {
    background: linear-gradient(135deg, #2563eb, #4f46e5) !important;
    border: none !important;
    border-radius: 6px !important;
    color: #fff !important;
    font-weight: 600 !important;
    transition: opacity .08s linear !important;
    box-shadow: 0 3px 12px rgba(37,99,235,.3) !important;
}
.stFormSubmitButton > button:hover {
    opacity: .88 !important;
}

/* ── Multiselect ── */
.stMultiSelect > div > div {
    background: rgba(5,12,25,.7) !important;
    border-color: rgba(255,255,255,.08) !important;
    border-radius: 6px !important;
}
.stMultiSelect span[data-baseweb="tag"] {
    background: rgba(77,156,248,.18) !important;
    border-radius: 4px !important;
}
.st-key-refresh_pause_button button,
[class*="refresh_pause_button"] button {
    display: flex !important;
    justify-content: center !important;
    align-items: center !important;
    padding-left: 0 !important;
    padding-right: 0 !important;
    text-align: center !important;
    font-size: 1.2rem !important;
    line-height: 1 !important;
}

/* Selector de actualización: botones compactos tipo píldora. */
[data-testid="stRadio"] > div[role="radiogroup"] {
    display: flex !important;
    flex-direction: row !important;
    flex-wrap: wrap !important;
    gap: .45rem !important;
}
[data-testid="stRadio"] label {
    width: auto !important;
    min-width: 7rem;
    min-height: 2rem;
    padding: .35rem .85rem !important;
    border: 1px solid rgba(126,164,202,.2) !important;
    border-radius: 7px !important;
    background: rgba(17,31,51,.8) !important;
    color: #a9bed3 !important;
    justify-content: center !important;
    transition: background .1s linear, border-color .1s linear, color .1s linear !important;
}
[data-testid="stRadio"] label:hover {
    border-color: #4d9cf8 !important;
    background: rgba(77,156,248,.12) !important;
    color: #e6f2ff !important;
}
[data-testid="stRadio"] label:has(input:checked) {
    border-color: #4d9cf8 !important;
    background: linear-gradient(135deg, #1769c2, #2453a5) !important;
    color: #fff !important;
    box-shadow: 0 2px 8px rgba(39,111,207,.25);
}
[data-testid="stRadio"] label > div:first-child { display: none !important; }
[data-testid="stRadio"] label > div:last-child {
    width: 100% !important;
    text-align: center !important;
    justify-content: center !important;
}
[data-testid="stSegmentedControl"] {
    width: 100% !important;
}
[data-testid="stSegmentedControl"] [data-baseweb="button-group"],
[data-testid="stSegmentedControl"] [role="group"] {
    display: flex !important;
    flex-direction: column !important;
    gap: .28rem !important;
    width: 100% !important;
}
[data-testid="stSegmentedControl"] button {
    width: 100% !important;
    justify-content: flex-start !important;
    padding-left: .7rem !important;
    border-radius: 7px !important;
    border: 1px solid rgba(126,164,202,.2) !important;
    min-height: 1.85rem !important;
}

/* ── Dataframe ── */
[data-testid="stDataFrame"] { border-radius: 8px; overflow: hidden; }
[data-testid="stDataFrame"] > div { border-radius: 8px; }

/* ── Alertas / info ── */
[data-testid="stAlert"] { border-radius: 7px !important; }

/* ── Progress bar ── */
[data-testid="stProgress"] > div > div > div {
    background: linear-gradient(90deg, #34d399, #fbbf24, #f87171) !important;
    border-radius: 4px;
}

/* ── Scrollbar ── */
::-webkit-scrollbar { width: 4px; height: 4px; }
::-webkit-scrollbar-track { background: transparent; }
::-webkit-scrollbar-thumb { background: rgba(255,255,255,.1); border-radius: 2px; }
::-webkit-scrollbar-thumb:hover { background: rgba(255,255,255,.18); }

/* ── Animación entrada ── */
@keyframes pgFade {
    from { opacity: 0; }
    to   { opacity: 1; }
}
.pg-in {
    animation: pgFade .12s linear both;
    /* Solo se anima opacidad: evita recalcular la posición de todo el layout. */
    will-change: opacity;
}

/* ── Botón actualizar (fuera sidebar) ── */
.stButton > button:not([kind]) {
    background: rgba(255,255,255,.05) !important;
    border: 1px solid rgba(255,255,255,.08) !important;
    border-radius: 6px !important;
    color: #6a8aaa !important;
    font-size: .75rem !important;
    transition: background .08s linear, color .08s linear !important;
}
.stButton > button:not([kind]):hover {
    background: rgba(255,255,255,.09) !important;
    color: #b0cce8 !important;
}

/* Evita animaciones innecesarias en equipos configurados para reducir movimiento. */
@media (prefers-reduced-motion: reduce) {
    *, *::before, *::after {
        animation-duration: 0.01ms !important;
        animation-iteration-count: 1 !important;
        transition-duration: 0.01ms !important;
        scroll-behavior: auto !important;
    }
}
</style>
""", unsafe_allow_html=True)

# El tema claro se aplica después de los estilos base para que sus overrides
# tengan prioridad. El valor se conserva en session_state durante los reruns.
apply_theme()


# ── Helpers API ────────────────────────────────────────────────────────────────
def request_retry(method: str, url: str, attempts: int = 3, **kwargs):
    """Realiza una petición con reintentos breves ante fallos transitorios."""
    last_error = None
    for attempt in range(attempts):
        try:
            return requests.request(method, url, **kwargs)
        except (requests.ConnectionError, requests.Timeout) as exc:
            last_error = exc
            if attempt < attempts - 1:
                time.sleep(0.15 * (attempt + 1))
    raise last_error


def enviar_telegram(texto: str) -> bool:
    """Envía un mensaje solo si Telegram está configurado."""
    if not TELEGRAM_TOKEN or not TELEGRAM_CHAT_ID:
        return False
    try:
        response = request_retry(
            "POST",
            f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage",
            json={"chat_id": TELEGRAM_CHAT_ID, "text": texto},
            timeout=8,
        )
        response.raise_for_status()
        return True
    except requests.RequestException:
        return False


def lortu_tokena(behartu: bool = False) -> str:
    tok = st.session_state.get("token")
    if not behartu and tok and tok["exp"] > time.time() + 10:
        return tok["access"]
    r = request_retry("POST",
        f"{API_URL}/auth/token",
        data={"grant_type": "password", "username": API_USERNAME, "password": API_PASSWORD},
        timeout=5,
    )
    r.raise_for_status()
    d = r.json()
    st.session_state["token"] = {"access": d["access_token"], "exp": time.time() + d["expires_in"]}
    return d["access_token"]


def iragarri(datuak: dict) -> dict:
    for i in range(2):
        tok = lortu_tokena(behartu=i > 0)
        r = request_retry("POST", f"{API_URL}/predict", json=datuak,
                          headers={"Authorization": f"Bearer {tok}"}, timeout=10)
        if r.status_code == 401 and i == 0:
            continue
        r.raise_for_status()
        return r.json()
    raise RuntimeError("No se pudo autenticar")


@st.cache_data(ttl=10, show_spinner=False)
def api_egoera() -> tuple[bool, str]:
    try:
        d = request_retry("GET", f"{API_URL}/health", timeout=3).json()
        ok = bool(d.get("model_loaded"))
        return ok, "Modelo OK" if ok else "Sin modelo"
    except Exception:
        return False, "Offline"


# ── Helpers Elasticsearch ──────────────────────────────────────────────────────
def es_bilatu(body: dict) -> dict:
    try:
        r = request_retry("POST", f"{ES_URL}/{ES_INDEX}/_search", json=body, timeout=10)
    except (requests.ConnectionError, requests.Timeout) as exc:
        raise ElasticsearchUnavailable from exc
    if r.status_code == 404:
        raise ElasticsearchIndexMissing
    r.raise_for_status()
    return r.json()


@st.cache_data(ttl=15, show_spinner=False)
def es_count_cached() -> int:
    return int(es_bilatu({"size": 0, "track_total_hits": True})["hits"]["total"]["value"])


@st.cache_data(ttl=15, show_spinner=False)
def alerta_kopurua_cached() -> int:
    res = es_bilatu({
        "size": 0,
        "track_total_hits": True,
        "query": {"bool": {"must_not": [{"term": {"alert_level.keyword": "OK"}}]}},
    })
    return int(res["hits"]["total"]["value"])


@st.cache_data(ttl=10, show_spinner=False)
def cargar_documentos(body: dict) -> list[dict]:
    return es_bilatu(body)["hits"]["hits"]


@st.cache_data(ttl=10, show_spinner=False)
def cargar_dashboard() -> list[dict]:
    return cargar_documentos({
        "size": 1000,
        "sort": [{"timestamp": "desc"}],
        "_source": ["timestamp", "machine_id", "failure_probability", "alert_level", "failure_predicted"],
    })


def es_egoera() -> tuple[bool, int]:
    try:
        return True, es_count_cached()
    except (ElasticsearchUnavailable, ElasticsearchIndexMissing, requests.RequestException):
        return False, 0


def alerta_kopurua() -> int:
    try:
        return alerta_kopurua_cached()
    except Exception:
        return 0


# ── Sidebar ────────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("""
    <div class="sb-brand">
        <div class="sb-logo"><span>NEXO</span> CNC</div>
        <div class="sb-sub">Smart Maintenance</div>
    </div>
    """, unsafe_allow_html=True)

    if "atal" not in st.session_state:
        st.session_state.atal = "Dashboard"

    nav = [
        ("·", "Dashboard",     "Dashboard"),
        ("·", "Datos",         "Datos"),
        ("·", "Predicciones",  "Predicciones"),
        ("·", "Alertas", "Alertas"),
    ]

    for icon, label, key in nav:
        active = st.session_state.atal == key
        marker = ""
        clicked = st.button(f"{marker}  {label}", key=f"nav_{key}", use_container_width=True,
                            type="primary" if active else "secondary")
        if clicked:
            st.session_state.atal = key
            # Re-renderiza también la barra para que el estado activo cambie
            # en el mismo clic, no en la siguiente interacción.
            st.rerun()

    refresh_options = {
        " ": 0,
        "30 s": 30,
        "1 m": 60,
        "10 m": 600,
        "30 m": 1800,
        "1 h": 3600,
    }
    st.caption("Actualización automática")
    selected_refresh = st.session_state.get("auto_refresh_choice", " ")
    refresh_items = list(refresh_options.items())
    for row_start in range(0, len(refresh_items), 2):
        option_cols = st.columns(2, gap="small")
        for col, (refresh_label, refresh_value) in zip(option_cols, refresh_items[row_start:row_start + 2]):
            with col:
                if refresh_value == 0:
                    with st.container(key="refresh_pause_button"):
                        clicked = st.button(
                            "⏸",
                            key=f"refresh_option_{refresh_value}",
                            use_container_width=True,
                            type="primary" if selected_refresh == refresh_label else "secondary",
                        )
                else:
                    clicked = st.button(
                        refresh_label,
                        key=f"refresh_option_{refresh_value}",
                        use_container_width=True,
                        type="primary" if selected_refresh == refresh_label else "secondary",
                    )
                if clicked:
                    st.session_state["auto_refresh_choice"] = refresh_label
                    st.session_state["auto_refresh_seconds"] = refresh_value
                    st.rerun()
    st.session_state["auto_refresh_seconds"] = refresh_options.get(selected_refresh, 0)

    st.divider()
    st.caption("Apariencia")
    render_theme_switch()

    atala = st.session_state.atal

    st.divider()

    api_ok, api_msg = api_egoera()
    es_ok, es_docs  = es_egoera()
    st.markdown(f"""
    <div class="sb-status">
        <div class="sb-stitle">Sistema</div>
        <div class="sb-row">
            <span class="sb-dot {'on' if api_ok else 'off'}"></span>
            <span class="sb-lbl">API</span>
            <span class="sb-val">{api_msg}</span>
        </div>
        <div class="sb-row">
            <span class="sb-dot {'on' if es_ok else 'off'}"></span>
            <span class="sb-lbl">ES</span>
            <span class="sb-val">{f'{es_docs:,} docs' if es_ok else 'Offline'}</span>
        </div>
    </div>
    """, unsafe_allow_html=True)

    if TELEGRAM_TOKEN and TELEGRAM_CHAT_ID:
        st.checkbox("Notificaciones Telegram", key="telegram_enabled", value=False,
                    help="Envía una notificación cuando aparece una alerta nueva.")
    else:
        st.caption("Telegram no configurado")

    ordu = None


# ── Helpers visualización ──────────────────────────────────────────────────────
def altair_config():
    light = current_theme() != "dark"
    """Configuración común para gráficos Altair con fondo transparente."""
    return dict(
        configure_view=dict(strokeWidth=0, fill="#ffffff" if light else "transparent"),
        configure_axis=dict(
            gridColor="#dbe4ef" if light else "rgba(255,255,255,.05)",
            domainColor="#b9c9d9" if light else "rgba(255,255,255,.08)",
            tickColor="#b9c9d9" if light else "transparent",
            labelColor="#405b75" if light else "#8ea8c2",
            titleColor="#294563" if light else "#c3d5e6",
        ),
        configure_title=dict(color="#3a5572"),
    )


def chart_bar(data, x, y, color_field=None, color_range=None, height=140):
    light = current_theme() != "dark"
    base = (
        alt.Chart(data)
        .mark_bar(cornerRadiusTopLeft=5, cornerRadiusTopRight=5)
        .encode(
            x=alt.X(x, title=None, axis=alt.Axis(labelAngle=0, labelLimit=140)),
            y=alt.Y(y, title=None),
            **({"color": alt.Color(color_field,
                                   scale=alt.Scale(range=color_range) if color_range else alt.Scale(scheme="blues"),
                                   legend=None)} if color_field else {}),
            tooltip=[x, y],
        )
        .properties(width="container", height=height, background="#ffffff" if light else "#0b1018")
        .configure_view(strokeWidth=0, fill="#ffffff" if light else "transparent")
        .configure_axis(
            gridColor="#dbe4ef" if light else "rgba(255,255,255,.05)",
            domainColor="#b9c9d9" if light else "rgba(255,255,255,.08)",
            tickColor="#b9c9d9" if light else "transparent",
            labelColor="#405b75" if light else "#8ea8c2",
        )
    )
    return base


# ── Dashboard ──────────────────────────────────────────────────────────────────
def page_dashboard():
    st.markdown("""
    <div class="page-header pg-in">
      <div>
        <h2>Dashboard · Mantenimiento Predictivo</h2>
      </div>
    </div>
    """, unsafe_allow_html=True)

    # Cargar datos
    try:
        hits = cargar_dashboard()
        df = pd.DataFrame([h["_source"] for h in hits])
    except ElasticsearchIndexMissing:
        st.info(f"El índice `{ES_INDEX}` todavía no existe. Inicia el flujo de NiFi.")
        return
    except ElasticsearchUnavailable:
        st.error("Elasticsearch no está disponible. Comprueba el servicio y la conexión.")
        return
    except Exception as exc:
        st.error(f"No se pudieron cargar los datos: {exc}")
        df = pd.DataFrame()

    needed = {"timestamp", "machine_id", "failure_probability", "alert_level"}
    if df.empty or not needed.issubset(df.columns):
        st.info("Sin datos en el índice `cnc-predictions`. Inicia el flujo NiFi o revisa la conexión con Elasticsearch.")
        return

    df["timestamp"]           = pd.to_datetime(df["timestamp"], errors="coerce")
    df["failure_probability"] = pd.to_numeric(df["failure_probability"], errors="coerce")
    df = df.dropna(subset=["timestamp", "failure_probability"])
    if df.empty:
        st.info("No hay valores válidos para mostrar.")
        return

    last = df.sort_values("timestamp").groupby("machine_id", as_index=False).tail(1)
    machines = int(last["machine_id"].nunique())
    operational = int((last["alert_level"] == "OK").sum())
    maintenance = max(machines - operational, 0)
    uptime = operational / machines if machines else 0
    active_alerts = int((last["alert_level"] != "OK").sum())
    critical = int((last["alert_level"] == "LARRIA").sum())
    warning = int((last["alert_level"] == "KONTUZ").sum())
    failures = df[df["failure_predicted"].isin([True, "true", 1])].sort_values("timestamp")
    intervals = failures.groupby("machine_id")["timestamp"].diff().dt.total_seconds().div(3600).dropna()
    mtbf = intervals.mean() if not intervals.empty else None
    mtbf_text = f"{mtbf:.0f}" if mtbf is not None else "—"
    mtbf_suffix = " h" if mtbf is not None else ""
    st.markdown(f"""
    <div class="dash-kpis">
      <div class="dash-kpi">
        <div class="dash-kpi-icon">{SVG_FACTORY}</div><div class="dash-kpi-label">Máquinas en planta</div>
        <div class="dash-kpi-value">{machines}</div>
        <div class="dash-kpi-detail"><strong>{operational}</strong> operativas &nbsp;|&nbsp; {maintenance} en mantenimiento</div>
      </div>
      <div class="dash-kpi">
        <div class="dash-kpi-icon">{SVG_SHIELD}</div><div class="dash-kpi-label">Disponibilidad (uptime)</div>
        <div class="dash-kpi-value">{uptime:.1%}</div>
        <div class="dash-kpi-detail"><strong>↑ Datos en tiempo real</strong></div>
      </div>
      <div class="dash-kpi alert">
        <div class="dash-kpi-icon">{SVG_ALERT}</div><div class="dash-kpi-label">Alertas activas</div>
        <div class="dash-kpi-value">{active_alerts}</div>
        <div class="dash-kpi-detail"><strong>{critical}</strong> críticas &nbsp;|&nbsp; {warning} advertencias</div>
      </div>
      <div class="dash-kpi blue">
        <div class="dash-kpi-icon">{SVG_CLOCK}</div><div class="dash-kpi-label">MTBF (tiempo medio entre fallos)</div>
        <div class="dash-kpi-value">{mtbf_text}<small>{mtbf_suffix}</small></div>
        <div class="dash-kpi-detail"><strong>↑ Calculado con el histórico disponible</strong></div>
      </div>
    </div>
    """, unsafe_allow_html=True)

    st.markdown("<div style='height:12px'></div>", unsafe_allow_html=True)

    c1, c2 = st.columns(2)
    with c1:
        st.caption("Distribución de alertas")
        dist = (df["alert_level"].value_counts()
                  .reindex(MAILAK).fillna(0)
                  .rename_axis("nivel").reset_index(name="n"))
        ch = chart_bar(
            dist, "nivel:N", "n:Q",
            color_field="nivel:N",
            color_range=["#34d399", "#fbbf24", "#fb7185"],
        )
        st.altair_chart(ch, use_container_width=True)

    with c2:
        st.caption("Evolución del riesgo (media 5 min)")
        serie = (df.set_index("timestamp").sort_index()
                   .groupby(pd.Grouper(freq="5min"))["failure_probability"].mean())
        serie_chart = alt.Chart(serie.reset_index(name="risk")).mark_line(
            color="#087ea4" if current_theme() != "dark" else "#38bdf8"
        ).encode(
            x=alt.X("timestamp:T", title=None),
            y=alt.Y("risk:Q", title=None),
        ).properties(width="container", height=140, background="#ffffff" if current_theme() != "dark" else "#0b1018")
        st.altair_chart(serie_chart.configure_view(strokeWidth=0, fill="#ffffff" if current_theme() != "dark" else "transparent").configure_axis(
            gridColor="#dbe4ef" if current_theme() != "dark" else "rgba(255,255,255,.05)",
            domainColor="#b9c9d9" if current_theme() != "dark" else "rgba(255,255,255,.08)",
            tickColor="#b9c9d9" if current_theme() != "dark" else "transparent",
            labelColor="#405b75" if current_theme() != "dark" else "#8ea8c2",
        ), use_container_width=True)

    c3, c4 = st.columns(2)
    with c3:
        st.caption("Top de máquinas por riesgo")
        top_maq = (df.groupby("machine_id", as_index=False)["failure_probability"]
                     .max().nlargest(10, "failure_probability"))
        light = current_theme() != "dark"
        ch2 = (
            alt.Chart(top_maq)
            .mark_bar(cornerRadiusEnd=5)
            .encode(
                y=alt.Y("machine_id:N", sort="-x", title=None),
                x=alt.X("failure_probability:Q", title=None, axis=alt.Axis(format="%")),
                color=alt.Color("failure_probability:Q",
                                scale=alt.Scale(range=["#38bdf8", "#8b5cf6", "#f43f5e"]),
                                legend=None),
                tooltip=["machine_id:N", alt.Tooltip("failure_probability:Q", format=".1%")],
            )
            .properties(width="container", height=140, background="#ffffff" if light else "#0b1018")
            .configure_view(strokeWidth=0, fill="#ffffff" if light else "transparent")
            .configure_axis(
                gridColor="#dbe4ef" if light else "rgba(255,255,255,.05)",
                domainColor="#b9c9d9" if light else "rgba(255,255,255,.08)",
                tickColor="#b9c9d9" if light else "transparent",
                labelColor="#405b75" if light else "#8ea8c2",
            )
        )
        st.altair_chart(ch2, use_container_width=True)

    with c4:
        st.caption("Predicciones por probabilidad de fallo")
        rangos = ["0–20%", "20–40%", "40–60%", "60–80%", "80–100%"]
        bins = pd.cut(
            df["failure_probability"],
            bins=[0, .2, .4, .6, .8, 1],
            labels=rangos,
            include_lowest=True,
        )
        hdf = bins.value_counts().reindex(rangos, fill_value=0).rename_axis("rango").reset_index(name="n")
        ch3 = chart_bar(hdf, "rango:N", "n:Q", color_field="n:Q")
        st.altair_chart(ch3, use_container_width=True)


# ── Predicciones ──────────────────────────────────────────────────────────────
def page_predicciones():
    st.markdown("""
    <div class="page-header pg-in">
      <div>
        <h2>Predicción Manual</h2>
      </div>
    </div>
    """, unsafe_allow_html=True)

    with st.form("pred_form"):
        st.markdown("**Identificación de máquina**")
        ca, cb = st.columns(2)
        machine_id   = ca.text_input("ID de máquina", "CNC-001")
        machine_type = cb.selectbox("Tipo de carga", ["L", "M", "H"],
                                    help="L = baja · M = media · H = alta")

        st.markdown("**Lecturas de sensores**")
        c1, c2 = st.columns(2)
        air  = c1.number_input("Temperatura aire [K]",    280.0, 330.0, 300.0, 0.1)
        proc = c2.number_input("Temperatura proceso [K]", 290.0, 340.0, 310.0, 0.1)

        c3, c4, c5 = st.columns(3)
        rpm    = c3.number_input("Rotación [rpm]",         0.0, 4000.0, 1500.0, 10.0)
        torque = c4.number_input("Par motor [Nm]",          0.0,  100.0,   40.0,  0.1)
        wear   = c5.number_input("Desgaste herramienta [min]", 0.0, 400.0, 100.0, 1.0)

        submit = st.form_submit_button("Ejecutar predicción", type="primary")

    if submit:
        machine_id = machine_id.strip()
        if not machine_id:
            st.error("Introduce un ID de máquina válido.")
            return
        try:
            res   = iragarri({"machine_id": machine_id, "machine_type": machine_type,
                               "air_temp_K": air, "process_temp_K": proc,
                               "rpm": rpm, "torque_Nm": torque, "tool_wear_min": wear})
            nivel = res["alert_level"]
            prob  = res["failure_probability"]

            historial = st.session_state.setdefault("predicciones_historial", [])
            historial.insert(0, {
                "Máquina": machine_id,
                "Nivel": nivel,
                "Prob. fallo": f"{prob:.1%}",
                "Fallo predicho": "Sí" if res["failure_predicted"] else "No",
            })
            del historial[10:]

            r1, r2, r3 = st.columns(3)
            r1.metric("Nivel de alerta",     nivel)
            r2.metric("Probabilidad fallo",  f"{prob:.1%}")
            r3.metric("Fallo predicho",      "Sí" if res["failure_predicted"] else "No")
            st.progress(float(min(max(prob, 0), 1)))
            {"OK": st.success, "KONTUZ": st.warning, "LARRIA": st.error}[nivel](
                f"{machine_id} → {nivel}  ({prob:.1%})")
            st.caption("Últimas predicciones de esta sesión")
            st.dataframe(
                pd.DataFrame(st.session_state["predicciones_historial"]),
                use_container_width=True,
                hide_index=True,
                height=230,
            )
        except requests.HTTPError as e:
            st.error(f"Error API {e.response.status_code}: {e.response.text[:300]}")
        except Exception as e:
            st.error(f"No se pudo conectar con la API: {e}")


# ── Datos ──────────────────────────────────────────────────────────────────────
def cargar_df(sel: list[str], size: int = 2000) -> pd.DataFrame:
    hits = cargar_documentos({
        "size": size,
        "sort": [{"timestamp": "desc"}],
        "query": {"bool": {"filter": [{"terms": {"alert_level.keyword": sel}}]}},
        "_source": ["timestamp", "machine_id", "failure_probability", "alert_level", "failure_predicted"],
    })
    rows = []
    for hit in hits:
        row = dict(hit["_source"])
        row["event_id"] = hit.get("_id", f'{row.get("timestamp", "")}-{row.get("machine_id", "")}')
        rows.append(row)
    df = pd.DataFrame(rows)
    if not df.empty:
        df["timestamp"] = pd.to_datetime(df["timestamp"], errors="coerce")
        df["failure_probability"] = pd.to_numeric(df["failure_probability"], errors="coerce")
        df = df.dropna(subset=["timestamp", "failure_probability"])
    return df


def page_datos():
    st.markdown(f"""<div class="page-header pg-in"><div><h2>Explorador de datos</h2>
    </div></div>""", unsafe_allow_html=True)
    c1, c2, c3 = st.columns([2, 1, 1])
    with c1:
        st.caption("Niveles")
        nivel_cols = st.columns(3)
        sel = [nivel for col, nivel in zip(nivel_cols, MAILAK)
               if col.checkbox(nivel, value=True, key=f"datos_nivel_{nivel}")]
    limite = c2.selectbox("Registros", [200, 500, 1000, 2000], index=1, key="datos_limite")
    buscar = c3.text_input("Máquina", placeholder="CNC-001", key="datos_maquina").strip()
    if not sel:
        st.warning("Selecciona al menos un nivel."); return
    try:
        df = cargar_df(sel, limite)
    except ElasticsearchIndexMissing:
        st.info(f"El índice `{ES_INDEX}` todavía no existe. Inicia el flujo de NiFi."); return
    except ElasticsearchUnavailable:
        st.error("Elasticsearch no está disponible. Comprueba el servicio y la conexión."); return
    except Exception as e:
        st.error(f"No se pudieron cargar los datos: {e}"); return
    if buscar:
        df = df[df["machine_id"].astype(str).str.contains(buscar, case=False, na=False)]
    if df.empty:
        st.info("No hay registros que coincidan con los filtros."); return
    m1, m2, m3 = st.columns(3)
    m1.metric("Registros mostrados", f"{len(df):,}")
    m2.metric("Máquinas", df["machine_id"].nunique())
    m3.metric("Riesgo medio", f"{df['failure_probability'].mean():.1%}")
    st.caption("Evolución del riesgo y volumen de predicciones")
    serie = df.set_index("timestamp").resample("15min")["failure_probability"].agg(["mean", "count"])
    light = current_theme() != "dark"
    datos_serie = serie.reset_index().rename(columns={"mean": "risk", "count": "predictions"})
    base_chart = alt.Chart(datos_serie).encode(x=alt.X("timestamp:T", title=None))
    volumen = base_chart.mark_bar(color="#b9d7e8" if light else "#24577a", opacity=0.45).encode(
        y=alt.Y("predictions:Q", title="Predicciones")
    )
    riesgo = base_chart.mark_line(color="#087ea4" if light else "#38bdf8", strokeWidth=2.5).encode(
        y=alt.Y("risk:Q", title="Riesgo medio", axis=alt.Axis(format="%"))
    )
    datos_chart = alt.layer(volumen, riesgo).resolve_scale(y="independent").properties(
        width="container", height=180, background="#ffffff" if light else "#0b1018"
    ).configure_view(strokeWidth=0).configure_axis(
        gridColor="#dbe4ef" if light else "rgba(255,255,255,.05)",
        domainColor="#b9c9d9" if light else "rgba(255,255,255,.08)",
        labelColor="#405b75" if light else "#8ea8c2",
        titleColor="#405b75" if light else "#8ea8c2",
    )
    st.altair_chart(datos_chart, use_container_width=True)
    st.markdown(f"**Registros** — {len(df):,}")
    df_show = df.copy()
    df_show["failure_predicted"] = df_show["failure_predicted"].map({True: "Sí", False: "No", "true": "Sí", "false": "No"}).fillna(df_show["failure_predicted"].astype(str))
    st.dataframe(df_show, use_container_width=True, hide_index=True, height=430, column_config={
        "timestamp": st.column_config.DatetimeColumn("Fecha / Hora", format="DD/MM/YYYY HH:mm:ss"),
        "machine_id": st.column_config.TextColumn("Máquina"),
        "failure_probability": st.column_config.ProgressColumn("Prob. fallo", min_value=0.0, max_value=1.0, format="%.2f"),
    })
    if st.button("↺ Actualizar datos", key="refresh_datos"):
        cargar_documentos.clear(); cargar_dashboard.clear(); es_count_cached.clear(); alerta_kopurua_cached.clear(); st.rerun()


# ── Alertas ────────────────────────────────────────────────────────────────────
def page_alertas():
    st.markdown("""<div class="page-header pg-in"><div><h2>Alertas</h2>
    </div></div>""", unsafe_allow_html=True)
    try:
        df = cargar_df(MAILAK, 2000)
    except ElasticsearchIndexMissing:
        st.info(f"El índice `{ES_INDEX}` todavía no existe. Inicia el flujo de NiFi."); return
    except ElasticsearchUnavailable:
        st.error("Elasticsearch no está disponible. Comprueba el servicio y la conexión."); return
    except Exception as e:
        st.error(f"No se pudieron cargar las alertas: {e}"); return
    if df.empty:
        st.success("No hay eventos registrados."); return
    if st.session_state.get("telegram_enabled", False):
        enviados = st.session_state.setdefault("telegram_alertas_enviadas", set())
        for _, alerta in df[df["alert_level"] != "OK"].head(20).iterrows():
            event_id = alerta["event_id"]
            if event_id in enviados:
                continue
            nivel = alerta["alert_level"]
            mensaje = (
                f"🚨 CNC Guard · {nivel}\n"
                f"Máquina: {alerta.get('machine_id', 'N/D')}\n"
                f"Probabilidad de fallo: {float(alerta.get('failure_probability', 0)):.1%}\n"
                f"Fecha: {alerta.get('timestamp', 'N/D')}"
            )
            if enviar_telegram(mensaje):
                enviados.add(event_id)
    f1, f2, f3 = st.columns([1.25, 1.25, 2])
    maquina = f1.selectbox("Máquina", ["Todas las máquinas"] + sorted(df["machine_id"].dropna().unique().tolist()), key="alerta_maquina")
    periodo = f2.selectbox("Periodo", ["Últimos 7 días", "Últimos 30 días", "Todo el histórico"], key="alerta_periodo")
    if maquina != "Todas las máquinas":
        df = df[df["machine_id"] == maquina]
    if periodo != "Todo el histórico" and not df.empty:
        limite = df["timestamp"].max() - pd.Timedelta(days=7 if periodo.startswith("Últimos 7") else 30)
        df = df[df["timestamp"] >= limite]
    criticas = int((df["alert_level"] == "LARRIA").sum())
    advertencias = int((df["alert_level"] == "KONTUZ").sum())
    informativas = int((df["alert_level"] == "OK").sum())
    nivel = st.radio("", [f"Todas ({len(df)})", f"LARRIA ({criticas})", f"KONTUZ ({advertencias})", f"OK ({informativas})"], horizontal=True, key="alerta_nivel_codigo", label_visibility="collapsed")
    nivel = nivel.split(" (")[0]
    nivel_map = {"Todas": None, "LARRIA": "LARRIA", "KONTUZ": "KONTUZ", "OK": "OK"}
    if nivel_map[nivel]:
        df = df[df["alert_level"] == nivel_map[nivel]]
    if df.empty:
        st.info("No hay alertas para los filtros seleccionados."); return
    tabla = df.sort_values("timestamp", ascending=False).copy()
    tabla["Fecha y hora"] = tabla["timestamp"]
    tabla["Máquina"] = tabla["machine_id"]
    tabla["Tipo"] = tabla["alert_level"]
    tabla["Descripción"] = tabla["alert_level"].map({"LARRIA": "Posible fallo crítico · requiere revisión inmediata", "KONTUZ": "Condición anómala · revisar en el próximo mantenimiento", "OK": "Mantenimiento recomendado · sin anomalía crítica"})
    tabla["Valor"] = tabla["failure_probability"].map(lambda value: f"{value:.1%}")
    tabla["Estado"] = "● Activa"
    st.dataframe(tabla[["Fecha y hora", "Máquina", "Tipo", "Descripción", "Valor", "Estado"]], use_container_width=True, hide_index=True, height=430, column_config={
        "Fecha y hora": st.column_config.DatetimeColumn(format="DD/MM/YYYY HH:mm"),
        "Descripción": st.column_config.TextColumn(width="large"),
    })
    if st.button("↺ Actualizar alertas", key="refresh_alertas"):
        cargar_documentos.clear(); cargar_dashboard.clear(); alerta_kopurua_cached.clear(); st.rerun()


# ── Router ─────────────────────────────────────────────────────────────────────
def render_page():
    if atala == "Dashboard":
        page_dashboard()
    elif atala == "Predicciones":
        page_predicciones()
    elif atala == "Datos":
        page_datos()
    elif atala == "Alertas":
        page_alertas()


refresh_seconds = st.session_state.get("auto_refresh_seconds", 0)
if refresh_seconds and hasattr(st, "fragment"):
    @st.fragment(run_every=refresh_seconds)
    def render_auto_refresh():
        render_page()

    render_auto_refresh()
else:
    render_page()
