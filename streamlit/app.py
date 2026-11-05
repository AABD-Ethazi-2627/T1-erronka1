"""CNC Guard — Streamlit panela."""

import math
import os
import time

import altair as alt
import numpy as np
import pandas as pd
import requests
import streamlit as st

from config import (API_PASSWORD, API_URL, API_USERNAME, ES_INDEX, ES_SENSOR_INDEX, ES_URL,
                    MAILAK)
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
    page_title="NEXO CNC",
    page_icon="🛠️",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── Estilos ────────────────────────────────────────────────────────────────────
st.markdown("""
<style>
/* ── Fuente del sistema (sin petición de red) ── */
.stApp, button, input, textarea, select, [data-testid="stMarkdownContainer"] {
    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', system-ui,
                 'Helvetica Neue', Arial, sans-serif !important;
    box-sizing: border-box;
}

/* ── Fondo app ── */
.stApp {
    background: #060d1a !important;
    color: #d8e6f3;
}
[data-testid="stHeader"]      { display: none !important; height: 0 !important; }
[data-testid="stToolbar"]     { display: none !important; }
[data-testid="stDecoration"]  { display: none !important; }
[data-testid="stAppViewBlockContainer"] { padding-top: 0 !important; }
[data-testid="stMainBlockContainer"] { padding-top: 0 !important; }
.stMainBlockContainer, .stAppViewBlockContainer { padding-top: 0 !important; }
[data-testid="stAppViewContainer"] { padding-top: 0 !important; }
[data-testid="stAppViewContainer"] > .main { padding-top: 0 !important; }
[data-testid="stAppViewContainer"] > .main > div { padding-top: 0 !important; }
section.main > div { padding-top: 0 !important; }
[data-testid="stAppViewContainer"] main { padding-top: 0 !important; }
[data-testid="stSidebarContent"] { padding: 0 !important; margin: 0 !important; }
[data-testid="stSidebarHeader"] { display: none !important; }
[data-testid="stSidebarUserContent"] { padding: .3rem .65rem .3rem !important; }
[data-testid="stSidebar"] [data-testid="stVerticalBlock"] { gap: .35rem !important; }
.block-container              { max-width: 1500px; padding: 0 1rem .5rem !important; margin-top: -1.5rem !important; }

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
[data-testid="stSidebar"] > div                   { overflow-x: hidden; overflow-y: auto; }

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
    padding: .65rem 0 .5rem;
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
    font-size: .68rem;
    font-weight: 600;
    letter-spacing: .13em;
    color: #253d58 !important;
    margin-top: .22rem;
    text-transform: uppercase;
}

/* ── Divider sidebar ── */
[data-testid="stSidebar"] hr {
    border-color: rgba(255,255,255,.05) !important;
    margin: .3rem 0 !important;
}

/* ── Botones nav: todos iguales, alineados izquierda ── */
[data-testid="stSidebar"] .stButton {
    width: 100% !important;
    padding: 0 !important;
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
    font-size: .9rem !important;
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
/* Mantener visible el foco al navegar con teclado. */
[data-testid="stSidebar"] .stButton > button:focus-visible {
    outline: 2px solid #4d9cf8 !important;
    outline-offset: 2px;
}

[data-testid="stSidebar"] .st-key-refresh_snapshot button {
    background: #124e75 !important;
    border: 1px solid #267fae !important;
    border-radius: 7px !important;
    color: #ffffff !important;
    font-weight: 700 !important;
    justify-content: center !important;
    min-height: 2.15rem !important;
}
[data-testid="stSidebar"] .st-key-refresh_snapshot button * { color: #ffffff !important; }
[data-testid="stSidebar"] .st-key-refresh_snapshot button:hover { background: #176891 !important; }

/* ── Panel estado sistema ── */
.sb-status {
    margin: .25rem 0 .35rem;
    padding: .5rem .6rem;
    background: rgba(255,255,255,.018);
    border: 1px solid rgba(255,255,255,.045);
    border-radius: 6px;
    font-size: .78rem;
}
.sb-stitle {
    font-size: .68rem;
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
.sb-val { margin-left: auto; color: #3a5572 !important; font-size: .75rem; }

/* ── Header de página ── */
.page-header {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 1rem;
    margin: 0 -1rem .3rem;
    padding: .4rem 1rem;
    background: rgba(4,10,22,.7);
    border-bottom: 1px solid rgba(255,255,255,.05);
    position: sticky;
    top: 0;
    z-index: 100;
}
.page-header h2 {
    margin: 0 !important;
    font-size: 1.2rem !important;
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
    color: #91a8c0 !important;
    font-size: .78rem !important;
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
.block-container:has(.dash-kpis) .dash-kpi { border-radius: 10px; min-height: 4.7rem; }
.block-container:has(.dash-kpis) .dash-kpi-label { font-size: .82rem; font-weight: 600; white-space: normal; }
.block-container:has(.dash-kpis) .dash-kpi-value { font-size: 1.55rem; margin-top: .38rem; }
.block-container:has(.dash-kpis) .dash-kpi-detail { font-size: .73rem; }
.dash-kpis.fleet-kpis { grid-template-columns: repeat(5, minmax(0, 1fr)); }
.fleet-kpis .dash-kpi:nth-child(2)::before { background: #ef5571; }
.fleet-kpis .dash-kpi:nth-child(3)::before { background: #38bdf8; }
.fleet-kpis .dash-kpi:nth-child(4)::before { background: #a78bfa; }
.fleet-kpis .dash-kpi:nth-child(5)::before { background: #2dd4bf; }
.fleet-reading { display:flex; justify-content:space-between; gap:1rem; padding:.38rem 0; border-bottom:1px solid rgba(128,160,190,.2); color:#c3d5e6; font-size:.78rem; }
.fleet-reading strong { color:#e7f2ff; white-space:nowrap; }
@media (max-width: 900px) {
    .dash-kpis { grid-template-columns: repeat(2, minmax(0, 1fr)); }
    .dash-kpis.fleet-kpis { grid-template-columns: repeat(2, minmax(0, 1fr)); }
}
@media (max-width: 560px) {
    .dash-kpis { grid-template-columns: 1fr; }
    .dash-kpis.fleet-kpis { grid-template-columns: 1fr; }
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
    font-size: .85rem !important;
    letter-spacing: .02em !important;
    text-transform: none !important;
}

[class*="st-key-datos_machine_open_"] button {
    background: #0d1d31 !important;
    border: 1px solid #294b68 !important;
    border-radius: 8px !important;
    color: #d9edfc !important;
    font-weight: 600 !important;
    min-height: 2.6rem !important;
}
[class*="st-key-datos_machine_open_"] button * { color: #d9edfc !important; }
[class*="st-key-datos_machine_open_"] button:hover { background: #163b58 !important; border-color: #50bce4 !important; }
[class*="st-key-datos_machine_open_"] button:focus-visible { outline: 2px solid #50bce4 !important; outline-offset: 2px; }

/* Reduce los espacios del dashboard sin cambiar el resto de vistas. */
@media (min-width: 901px) {
    .block-container [data-testid="stVerticalBlock"] { gap: .6rem !important; }
    .block-container:has(.dash-kpis) .dash-kpis { margin-bottom: 1rem; }
    .block-container:has(.dash-kpis) .dash-kpi { padding-top: .6rem; padding-bottom: .55rem; }
    .block-container:has(.dash-kpis) [data-testid="stArrowVegaLiteChart"] { padding: .35rem .6rem !important; }
}

/* ── Títulos ── */
h1 { font-size: 1.4rem !important; font-weight: 700 !important; color: #e8f3ff !important; }
h2 { font-size: 1.2rem !important; font-weight: 600 !important; color: #d4e6f5 !important; }
h3 { font-size: 1.05rem !important; font-weight: 600 !important; color: #a8c4de !important; }

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
/* El refresco se controla mediante el deslizador; se ocultan los controles
   auxiliares heredados para evitar duplicar la interfaz. */
[class*="st-key-refresh_option_"] { display: none !important; }

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
.stApp,
[data-testid="stSidebar"],
[data-testid="stHeader"],
.page-header,
[data-testid="stMetric"],
[data-testid="stForm"],
[data-testid="stAltairChart"],
[data-testid="stVegaLiteChart"],
.dash-kpi,
button,
input,
[data-baseweb="select"] > div {
    transition: background-color .35s ease, color .35s ease,
                border-color .35s ease, box-shadow .35s ease !important;
}

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
def es_bilatu(body: dict, index: str = ES_INDEX) -> dict:
    try:
        r = request_retry("POST", f"{ES_URL}/{index}/_search", json=body, timeout=10)
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


def cargar_dashboard() -> list[dict]:
    snapshot = obtener_instantanea()
    if snapshot is not None:
        return snapshot["predictions"][:1000]
    return cargar_documentos({
        "size": 1000,
        "sort": [{"timestamp": "desc"}],
        "_source": ["timestamp", "machine_id", "failure_probability", "alert_level", "failure_predicted",
                    "temp_diff_K", "power_W", "wear_torque"],
    })


@st.cache_data(ttl=10, show_spinner=False)
def cargar_telemetria_live() -> list[dict]:
    return es_bilatu({
        "size": 1000,
        "sort": [{"timestamp": "desc"}],
        "_source": ["timestamp", "machine_id", "machine_type", "air_temp_K", "process_temp_K",
                    "rpm", "torque_Nm", "tool_wear_min"],
    }, index=ES_SENSOR_INDEX)["hits"]["hits"]


def cargar_telemetria_dashboard() -> list[dict]:
    snapshot = obtener_instantanea()
    if snapshot is not None:
        if snapshot["sensor_error"] == "missing":
            raise ElasticsearchIndexMissing
        if snapshot["sensor_error"] == "unavailable":
            raise ElasticsearchUnavailable
        return snapshot["sensors"]
    return cargar_telemetria_live()


def capturar_instantanea() -> None:
    """Fija los datos de esta sesión hasta que se solicite una actualización."""
    snapshot = {"predictions": [], "sensors": [], "sensor_error": None,
                "error": None, "count": 0, "captured_at": pd.Timestamp.now(tz="UTC").isoformat()}
    try:
        snapshot["count"] = int(es_bilatu({"size": 0, "track_total_hits": True})["hits"]["total"]["value"])
        for level in MAILAK:
            result = es_bilatu({
                "size": 2000, "sort": [{"timestamp": "desc"}],
                "query": {"bool": {"filter": [{"terms": {"alert_level.keyword": [level]}}]}},
                "_source": ["timestamp", "machine_id", "failure_probability", "alert_level",
                            "failure_predicted", "temp_diff_K", "power_W", "wear_torque"],
            })
            snapshot["predictions"].extend(result["hits"]["hits"])
        def sort_key(hit):
            timestamp = pd.to_datetime(hit.get("_source", {}).get("timestamp"), errors="coerce", utc=True)
            return timestamp.value if pd.notna(timestamp) else -9223372036854775808
        snapshot["predictions"].sort(key=sort_key, reverse=True)
    except ElasticsearchIndexMissing:
        snapshot["error"] = "missing"
    except (ElasticsearchUnavailable, requests.RequestException):
        snapshot["error"] = "unavailable"
    if snapshot["error"] is None:
        try:
            snapshot["sensors"] = es_bilatu({
                "size": 1000, "sort": [{"timestamp": "desc"}],
                "_source": ["timestamp", "machine_id", "machine_type", "air_temp_K",
                            "process_temp_K", "rpm", "torque_Nm", "tool_wear_min"],
            }, index=ES_SENSOR_INDEX)["hits"]["hits"]
        except ElasticsearchIndexMissing:
            snapshot["sensor_error"] = "missing"
        except (ElasticsearchUnavailable, requests.RequestException):
            snapshot["sensor_error"] = "unavailable"
    st.session_state["frozen_data_snapshot"] = snapshot


def obtener_instantanea():
    snapshot = st.session_state.get("frozen_data_snapshot")
    if snapshot is not None:
        if snapshot["error"] == "missing":
            raise ElasticsearchIndexMissing
        if snapshot["error"] == "unavailable":
            raise ElasticsearchUnavailable
    return snapshot


def actualizar_datos_manualmente():
    st.session_state.pop("frozen_data_snapshot", None)
    cargar_documentos.clear()
    cargar_telemetria_live.clear()
    es_count_cached.clear()
    alerta_kopurua_cached.clear()


def es_egoera() -> tuple[bool, int]:
    try:
        snapshot = obtener_instantanea()
        if snapshot is not None:
            return True, snapshot["count"]
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
    selected_refresh = st.select_slider(
        "Actualización automática",
        options=list(refresh_options),
        format_func=lambda value: "Desactivado" if value == " " else value,
        value=st.session_state.get("auto_refresh_choice", " "),
        key="auto_refresh_choice",
        help="Actualiza el contenido automáticamente sin recargar la barra lateral.",
    )
    st.session_state["auto_refresh_seconds"] = refresh_options.get(selected_refresh, 0)
    if st.session_state["auto_refresh_seconds"]:
        st.session_state.pop("frozen_data_snapshot", None)
    elif "frozen_data_snapshot" not in st.session_state:
        capturar_instantanea()
    if st.session_state["auto_refresh_seconds"] == 0:
        st.caption("Datos pausados")
    if st.button("↻ Actualizar datos", key="refresh_snapshot", use_container_width=True,
                 help="Actualiza los datos de todas las secciones"):
        actualizar_datos_manualmente()
        st.rerun()

    st.divider()
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



# ── Helpers visualización ──────────────────────────────────────────────────────
def altair_config():
    light = current_theme() == "light"
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


def dashboard_chart_style(chart, height=135):
    """Aplica los mismos márgenes y colores a todos los gráficos del panel."""
    light = current_theme() == "light"
    return (chart.properties(width="container", height=height,
                             background="#ffffff" if light else "transparent",
                             autosize=alt.AutoSizeParams(type="fit", contains="padding"),
                             padding={"left": 10, "right": 30, "top": 8, "bottom": 8})
            .configure_view(strokeWidth=0, fill="#ffffff" if light else "transparent")
            .configure_axis(
                gridColor="#dbe4ef" if light else "rgba(255,255,255,.05)",
                domainColor="#b9c9d9" if light else "rgba(255,255,255,.08)",
                tickColor="#b9c9d9" if light else "transparent",
                labelColor="#405b75" if light else "#8ea8c2",
                titleColor="#294563" if light else "#c3d5e6",
                labelPadding=6, titlePadding=10, labelFlush=True, labelFlushOffset=3,
                labelFontSize=12, titleFontSize=12,
            )
            .configure_legend(labelColor="#405b75" if light else "#c3d5e6",
                              titleColor="#294563" if light else "#c3d5e6"))


def chart_bar(data, x, y, color_field=None, color_range=None, height=140):
    light = current_theme() == "light"
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
        .properties(width="container", height=height, background="#ffffff" if light else "transparent")
        .configure_view(strokeWidth=0, fill="#ffffff" if light else "transparent")
        .configure_axis(
            gridColor="#dbe4ef" if light else "rgba(255,255,255,.05)",
            domainColor="#b9c9d9" if light else "rgba(255,255,255,.08)",
            tickColor="#b9c9d9" if light else "transparent",
            labelColor="#405b75" if light else "#8ea8c2",
        )
    )
    return base


def rangos_estables_indicador(field, values):
    """Mantiene los ejes y los intervalos por sesión, ampliándolos solo si es necesario."""
    values = pd.to_numeric(values, errors="coerce").replace([np.inf, -np.inf], np.nan).dropna()
    if values.empty:
        return None
    minimum, maximum = float(values.min()), float(values.max())
    ranges = st.session_state.setdefault("dashboard_indicator_ranges", {})
    saved = ranges.get(field)
    if saved is None:
        span = max(maximum - minimum, abs(maximum) * .05, 1e-6)
        raw_step = span / 6
        magnitude = 10 ** math.floor(math.log10(raw_step))
        step = next(multiplier * magnitude for multiplier in (1, 2, 5, 10)
                    if multiplier * magnitude >= raw_step)
        saved = {"step": step, "lower": (math.floor(minimum / step) - 1) * step,
                 "upper": (math.ceil(maximum / step) + 1) * step, "count_max": 5}
        ranges[field] = saved
    step = saved["step"]
    if minimum < saved["lower"]:
        saved["lower"] = (math.floor(minimum / step) - 1) * step
    if maximum > saved["upper"]:
        saved["upper"] = (math.ceil(maximum / step) + 1) * step
    # Un valor excepcional no debe crear miles de intervalos vacíos.
    if (saved["upper"] - saved["lower"]) / step > 40:
        ranges.pop(field)
        return rangos_estables_indicador(field, values)
    bin_count = max(1, round((saved["upper"] - saved["lower"]) / step))
    edges = saved["lower"] + np.arange(bin_count + 1) * step
    counts, _ = np.histogram(values.to_numpy(), bins=edges)
    saved["count_max"] = max(saved["count_max"], math.ceil(int(counts.max()) / 5) * 5)
    return saved, pd.DataFrame({"inicio": edges[:-1], "fin": edges[1:], "maquinas": counts})


# ── Dashboard ──────────────────────────────────────────────────────────────────
def seleccionar_maquina(chart_key):
    """Recoge la selección del gráfico antes de volver a dibujar la página."""
    selection = st.session_state[chart_key].get("selection", {}).get("maquina", [])
    if selection and selection[0].get("machine_id") is not None:
        st.session_state["dashboard_dialog_machine"] = selection[0]["machine_id"]


@st.dialog("Detalle de la máquina", width="large")
def mostrar_maquina(machine_id, latest, selected_row=None):
    rows = latest[latest["machine_id"] == machine_id]
    if rows.empty and selected_row is None:
        st.info("Esta máquina ya no está entre las lecturas disponibles. Actualiza el panel.")
        return
    row = pd.Series(selected_row) if selected_row is not None else rows.iloc[-1]
    timestamp = pd.to_datetime(row["timestamp"], errors="coerce", utc=True)
    st.subheader(str(machine_id))
    label = "Lectura seleccionada" if selected_row is not None else "Última lectura disponible"
    st.caption(f"{label}: {timestamp.strftime('%d/%m/%Y %H:%M:%S')} UTC" if pd.notna(timestamp) else f"{label}: fecha no disponible")
    level, risk = st.columns(2)
    level.metric("Nivel de alerta", str(row["alert_level"]))
    risk.metric("Probabilidad de fallo estimada", f"{row['failure_probability']:.1%}")
    st.progress(float(max(0, min(1, row["failure_probability"]))))
    st.caption("Indicadores de esta lectura · referencia: mediana de las máquinas con datos")
    indicator_columns = st.columns(3)
    indicators = (
        ("temp_diff_K", "Diferencia térmica", "°C"),
        ("power_W", "Potencia mecánica", "W"),
        ("wear_torque", "Desgaste × par", "min·Nm"),
    )
    for column, (field, label, unit) in zip(indicator_columns, indicators):
        with column:
            value = pd.to_numeric(row.get(field), errors="coerce")
            median = pd.to_numeric(latest[field], errors="coerce").median() if field in latest else float("nan")
            st.metric(label, f"{value:,.1f} {unit}" if pd.notna(value) else "Sin datos")
            st.caption(f"Mediana: {median:,.1f} {unit}" if pd.notna(median) else "Mediana no disponible")
    st.caption("Los indicadores describen una lectura individual y no confirman la causa de una avería.")


def seleccionar_fila(widget_key, rows):
    selected = st.session_state[widget_key].get("selection", {}).get("rows", [])
    if selected and 0 <= selected[0] < len(rows):
        st.session_state["table_dialog_row"] = rows[selected[0]]


def abrir_detalle_tabla():
    selected = st.session_state.pop("table_dialog_row", None)
    if selected is None:
        return
    try:
        latest = pd.DataFrame([hit["_source"] for hit in cargar_dashboard()])
        latest["timestamp"] = pd.to_datetime(latest["timestamp"], errors="coerce", utc=True)
        latest = latest.dropna(subset=["timestamp", "machine_id"])
        for field in ("temp_diff_K", "power_W", "wear_torque"):
            if field in latest:
                latest[field] = pd.to_numeric(latest[field], errors="coerce")
        latest = latest.sort_values("timestamp").groupby("machine_id", as_index=False).tail(1)
    except (ElasticsearchIndexMissing, ElasticsearchUnavailable, KeyError):
        st.warning("No se pudo cargar la comparación con las demás máquinas.")
        return
    mostrar_maquina(selected["machine_id"], latest, selected_row=selected)


def page_dashboard():
    st.markdown('<div class="page-header pg-in"><div><h2>NEXO CNC · Estado de las máquinas</h2></div></div>', unsafe_allow_html=True)
    try:
        predictions = pd.DataFrame([hit["_source"] for hit in cargar_dashboard()])
    except ElasticsearchIndexMissing:
        st.info(f"El índice `{ES_INDEX}` todavía no existe. Inicia el flujo de NiFi.")
        return
    except ElasticsearchUnavailable:
        st.error("Elasticsearch no está disponible. Comprueba el servicio y la conexión.")
        return
    except Exception:
        st.error("No se pudieron cargar las predicciones.")
        return
    required = {"timestamp", "machine_id", "failure_probability", "alert_level"}
    if predictions.empty or not required.issubset(predictions.columns):
        st.info("No hay predicciones disponibles.")
        return
    predictions["timestamp"] = pd.to_datetime(predictions["timestamp"], errors="coerce", utc=True)
    for field in ("failure_probability", "temp_diff_K", "power_W", "wear_torque"):
        if field in predictions:
            predictions[field] = pd.to_numeric(predictions[field], errors="coerce")
    predictions = predictions.dropna(subset=["timestamp", "machine_id", "failure_probability"])
    if predictions.empty:
        st.info("No hay predicciones válidas para mostrar.")
        return
    latest = predictions.sort_values("timestamp").groupby("machine_id", as_index=False).tail(1)
    latest = latest.sort_values("machine_id").reset_index(drop=True)
    try:
        sensors = pd.DataFrame([hit["_source"] for hit in cargar_telemetria_dashboard()])
    except ElasticsearchIndexMissing:
        sensors = pd.DataFrame()
        st.warning("El índice de telemetría aún no existe; se muestran las predicciones disponibles.")
    except Exception:
        sensors = pd.DataFrame()
        st.warning("No se pudo cargar la telemetría; se muestran las predicciones disponibles.")
    fields = ["air_temp_K", "process_temp_K", "rpm", "torque_Nm", "tool_wear_min"]
    if not sensors.empty and {"timestamp", "machine_id"}.issubset(sensors.columns):
        sensors["timestamp"] = pd.to_datetime(sensors["timestamp"], errors="coerce", utc=True)
        sensors = sensors.dropna(subset=["timestamp", "machine_id"])
        for field in fields:
            if field in sensors:
                sensors[field] = pd.to_numeric(sensors[field], errors="coerce")
        sensors = sensors.sort_values("timestamp").groupby("machine_id", as_index=False).tail(1)
        sensors = sensors.rename(columns={"timestamp": "sensor_timestamp"})
    else:
        sensors = pd.DataFrame(columns=["machine_id", "sensor_timestamp", "machine_type"] + fields)
    fleet = latest.merge(sensors, on="machine_id", how="left")
    for field in fields:
        if field not in fleet:
            fleet[field] = float("nan")
    if "machine_type" not in fleet:
        fleet["machine_type"] = None
    fleet["air_C"] = fleet["air_temp_K"] - 273.15
    fleet["process_C"] = fleet["process_temp_K"] - 273.15
    count = len(fleet)
    ok = int((fleet["alert_level"] == "OK").sum())
    alerts = int(fleet["alert_level"].isin(["KONTUZ", "LARRIA"]).sum())
    mean_risk = fleet["failure_probability"].mean()
    mean_air = fleet["air_C"].mean()
    ambient = f"{mean_air:.1f} °C" if pd.notna(mean_air) else "—"
    st.markdown(f"""
    <div class="dash-kpis">
      <div class="dash-kpi"><div class="dash-kpi-label">Máquinas con datos</div><div class="dash-kpi-value">{count}</div><div class="dash-kpi-detail">{ok} sin alerta en la última predicción</div></div>
      <div class="dash-kpi alert"><div class="dash-kpi-label">Máquinas con alerta</div><div class="dash-kpi-value">{alerts}</div><div class="dash-kpi-detail">KONTUZ y LARRIA</div></div>
      <div class="dash-kpi blue"><div class="dash-kpi-label">Riesgo medio estimado</div><div class="dash-kpi-value">{mean_risk:.1%}</div><div class="dash-kpi-detail">Última predicción por máquina</div></div>
      <div class="dash-kpi"><div class="dash-kpi-label">Temperatura media del aire</div><div class="dash-kpi-value">{ambient}</div><div class="dash-kpi-detail">Últimas lecturas de sensores</div></div>
    </div>
    """, unsafe_allow_html=True)
    priority_col, status_col = st.columns([1.4, 1])
    with priority_col:
        st.caption("01 · MÁQUINAS A REVISAR")
        priority = latest.nlargest(6, "failure_probability")
        chart = alt.Chart(priority).mark_bar(cornerRadiusEnd=5, size=13).encode(
            y=alt.Y("machine_id:N", sort="-x", title=None, axis=alt.Axis(labelOverlap=False)),
            x=alt.X("failure_probability:Q", title="Probabilidad de fallo estimada", scale=alt.Scale(domain=[0, 1]), axis=alt.Axis(format="%", tickCount=6)),
            color=alt.Color("alert_level:N", scale=alt.Scale(domain=["OK", "KONTUZ", "LARRIA"],
                            range=["#32a991", "#e5a63c", "#e36a7d"]), legend=None),
            tooltip=[alt.Tooltip("machine_id:N", title="Máquina"), alt.Tooltip("alert_level:N", title="Nivel"),
                     alt.Tooltip("failure_probability:Q", title="Probabilidad", format=".1%"),
                     alt.Tooltip("timestamp:T", title="Recepción")],
        ).add_params(alt.selection_point(name="maquina", fields=["machine_id"], on="click"))
        st.altair_chart(dashboard_chart_style(chart), use_container_width=True, key="dashboard_machine_risk",
                        on_select=lambda: seleccionar_maquina("dashboard_machine_risk"), selection_mode="maquina")
    with status_col:
        st.caption("02 · ESTADO DE LA FLOTA")
        counts = pd.DataFrame({"nivel": ["LARRIA", "KONTUZ", "OK"],
                               "maquinas": [int((latest["alert_level"] == value).sum()) for value in ("LARRIA", "KONTUZ", "OK")]})
        chart = alt.Chart(counts).mark_bar(cornerRadiusEnd=5, size=18).encode(
            y=alt.Y("nivel:N", sort=["LARRIA", "KONTUZ", "OK"], title=None),
            x=alt.X("maquinas:Q", title="Número de máquinas", axis=alt.Axis(format="d", tickMinStep=1)),
            color=alt.Color("nivel:N", scale=alt.Scale(domain=["OK", "KONTUZ", "LARRIA"],
                            range=["#32a991", "#e5a63c", "#e36a7d"]), legend=None),
            tooltip=[alt.Tooltip("nivel:N", title="Nivel"), alt.Tooltip("maquinas:Q", title="Máquinas")],
        )
        st.altair_chart(dashboard_chart_style(chart), use_container_width=True)
    heading, control = st.columns([1.4, 1])
    with heading:
        st.caption("03 · ANÁLISIS DE LA LECTURA")
    with control:
        measures = {"Diferencia de temperatura (°C)": "temp_diff_K",
                    "Potencia mecánica (W)": "power_W",
                    "Desgaste × par (min·Nm)": "wear_torque"}
        measure = st.selectbox("Indicador para ambos gráficos", list(measures), key="dashboard_indicator")
        field = measures[measure]
    stable_range = rangos_estables_indicador(field, latest[field]) if field in latest else None
    relation_col, distribution_col = st.columns([1.4, 1])
    with relation_col:
        st.caption("Indicador físico y riesgo de cada máquina")
        if stable_range is not None:
            bounds, histogram = stable_range
            points = latest.replace({field: {np.inf: np.nan, -np.inf: np.nan}}).dropna(subset=[field])
            chart = alt.Chart(points).mark_circle(size=85, opacity=0.85).encode(
                x=alt.X(f"{field}:Q", title=measure, scale=alt.Scale(domain=[bounds["lower"], bounds["upper"]], nice=False, zero=False)),
                y=alt.Y("failure_probability:Q", title="Probabilidad estimada", scale=alt.Scale(domain=[0, 1], nice=False), axis=alt.Axis(format="%", tickCount=5)),
                color=alt.Color("alert_level:N", title="Nivel", scale=alt.Scale(domain=["OK", "KONTUZ", "LARRIA"],
                                range=["#32a991", "#e5a63c", "#e36a7d"]), legend=None),
                tooltip=[alt.Tooltip("machine_id:N", title="Máquina"), alt.Tooltip(f"{field}:Q", title=measure, format=".2f"),
                         alt.Tooltip("failure_probability:Q", title="Probabilidad", format=".1%"),
                         alt.Tooltip("alert_level:N", title="Nivel"), alt.Tooltip("timestamp:T", title="Recepción")],
            ).add_params(alt.selection_point(name="maquina", fields=["machine_id"], on="click"))
            st.altair_chart(dashboard_chart_style(chart), use_container_width=True, key="dashboard_machine_scatter",
                            on_select=lambda: seleccionar_maquina("dashboard_machine_scatter"), selection_mode="maquina")
        else:
            st.info("No hay lecturas con este indicador entre las últimas predicciones.")
    with distribution_col:
        st.caption("Distribución del indicador entre máquinas")
        if stable_range is not None:
            bounds, histogram = stable_range
            chart = alt.Chart(histogram).mark_bar(color="#569db5", cornerRadiusTopLeft=3, cornerRadiusTopRight=3).encode(
                x=alt.X("inicio:Q", title=measure, scale=alt.Scale(domain=[bounds["lower"], bounds["upper"]], nice=False, zero=False)),
                x2=alt.X2("fin:Q"),
                y=alt.Y("maquinas:Q", title="Número de máquinas", scale=alt.Scale(domain=[0, bounds["count_max"]], nice=False), axis=alt.Axis(format="d", tickMinStep=1)),
                tooltip=[alt.Tooltip("inicio:Q", title="Desde", format=".2f"),
                         alt.Tooltip("fin:Q", title="Hasta", format=".2f"),
                         alt.Tooltip("maquinas:Q", title="Máquinas")],
            )
            st.altair_chart(dashboard_chart_style(chart), use_container_width=True)
        else:
            st.info("No hay lecturas suficientes para mostrar esta distribución.")
    selected_machine = st.session_state.pop("dashboard_dialog_machine", None)
    if selected_machine is not None:
        mostrar_maquina(selected_machine, latest)
    abrir_detalle_tabla()

def page_predicciones():
    st.markdown("""
    <div class="page-header pg-in">
      <div>
        <h2>Predicción Manual</h2>
      </div>
    </div>
    """, unsafe_allow_html=True)

    form_col, result_col = st.columns([1, 1])
    with form_col:
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
            wear   = c5.number_input("Desgaste [min]", 0.0, 400.0, 100.0, 1.0)

            submit = st.form_submit_button("Ejecutar predicción", type="primary")
    with result_col:
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
                if all(key in res for key in ("temp_diff_K", "power_W", "wear_torque")):
                    st.markdown("**Indicadores físicos de esta lectura**")
                    i1, i2, i3 = st.columns(3)
                    i1.metric("Diferencia de temperatura", f"{res['temp_diff_K']:.1f} °C")
                    i2.metric("Potencia mecánica", f"{res['power_W']:.0f} W")
                    i3.metric("Desgaste × par", f"{res['wear_torque']:.0f} min·Nm")
                    st.caption("Para investigar el riesgo, revisa la diferencia de temperatura y las rpm para disipación de calor; la potencia para fallo de potencia; y el desgaste × par para sobrecarga. Son indicadores, no causas confirmadas ni contribuciones explicadas del modelo.")
                else:
                    st.info("La API aún no devuelve indicadores físicos para esta predicción.")
                with st.expander("Últimas predicciones de esta sesión"):
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
    snapshot = obtener_instantanea()
    if snapshot is not None:
        hits = [hit for hit in snapshot["predictions"]
                if hit.get("_source", {}).get("alert_level") in sel][:size]
    else:
        hits = cargar_documentos({
            "size": size,
            "sort": [{"timestamp": "desc"}],
            "query": {"bool": {"filter": [{"terms": {"alert_level.keyword": sel}}]}},
            "_source": ["timestamp", "machine_id", "failure_probability", "alert_level", "failure_predicted",
                        "temp_diff_K", "power_W", "wear_torque"],
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


def tabla_estilo(df: pd.DataFrame):
    """Estilo explícito para que las tablas sigan el tema claro."""
    if current_theme() == "dark":
        return df
    return df.style.set_properties(
        **{
            "background-color": "#ffffff",
            "color": "#263f58",
            "border-color": "#dbe4ef",
        }
    ).set_table_styles([
        {"selector": "th", "props": [("background-color", "#edf4fb"), ("color", "#294563"), ("font-weight", "600")]},
        {"selector": "tr:hover td", "props": [("background-color", "#f4f8fc")]},
    ])


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
    machines_col, distribution_col = st.columns([1.4, 1], gap="large")
    with machines_col:
        st.markdown("**Abrir datos de una máquina**")
        st.caption("Pulsa un nombre para consultar su lectura más reciente entre los registros filtrados.")
        machine_names = sorted(df["machine_id"].dropna().astype(str).unique().tolist())
        pages = max(1, (len(machine_names) + 19) // 20)
        page = min(max(st.session_state.get("datos_machine_page_number", 1), 1), pages)
        st.session_state["datos_machine_page_number"] = page
        previous, position, following, _ = st.columns([1, 2, 1, 6])
        if previous.button("←", key="datos_machine_prev", disabled=page == 1, help="Página anterior"):
            st.session_state["datos_machine_page_number"] = page - 1
            st.rerun()
        position.markdown(f"**Página {page} de {pages}**")
        if following.button("→", key="datos_machine_next", disabled=page == pages, help="Página siguiente"):
            st.session_state["datos_machine_page_number"] = page + 1
            st.rerun()
        machine_columns = st.columns(5)
        for index, name in enumerate(machine_names[(page - 1) * 20:page * 20]):
            if machine_columns[index % 5].button(name, key=f"datos_machine_open_{name}", use_container_width=True):
                row = df[df["machine_id"].astype(str) == name].sort_values("timestamp").iloc[-1]
                st.session_state["table_dialog_row"] = row.to_dict()
    with distribution_col:
        st.markdown("**Distribución del riesgo**")
        st.caption("Número de lecturas en cada intervalo de probabilidad.")
        ranges = ["0–20%", "20–40%", "40–60%", "60–80%", "80–100%"]
        buckets = pd.cut(df["failure_probability"], bins=[0, .2, .4, .6, .8, 1], labels=ranges, include_lowest=True)
        counts = buckets.value_counts().reindex(ranges, fill_value=0).rename_axis("rango").reset_index(name="lecturas")
        chart = alt.Chart(counts).mark_bar(color="#38bdf8", size=19, cornerRadiusEnd=4).encode(
            y=alt.Y("rango:N", sort=ranges, title=None, axis=alt.Axis(labelAngle=0)),
            x=alt.X("lecturas:Q", title="Lecturas", axis=alt.Axis(format="d", tickMinStep=1)),
            tooltip=[alt.Tooltip("rango:N", title="Probabilidad"),
                     alt.Tooltip("lecturas:Q", title="Lecturas", format="d")],
        )
        st.altair_chart(dashboard_chart_style(chart, height=210), use_container_width=True)
    abrir_detalle_tabla()


# ── Alertas ────────────────────────────────────────────────────────────────────
def page_alertas():
    st.markdown('<div class="page-header pg-in"><div><h2>Centro de alertas</h2></div></div>', unsafe_allow_html=True)
    try:
        df = cargar_df(MAILAK, 2000)
    except ElasticsearchIndexMissing:
        st.info(f"El índice `{ES_INDEX}` todavía no existe. Inicia el flujo de NiFi.")
        return
    except ElasticsearchUnavailable:
        st.error("Elasticsearch no está disponible. Comprueba el servicio y la conexión.")
        return
    except Exception:
        st.error("No se pudieron cargar las predicciones.")
        return
    if df.empty:
        st.info("No hay lecturas disponibles. Comprueba el flujo de datos antes de asumir que no hay riesgo.")
        return
    latest = df.dropna(subset=["machine_id"]).copy()
    latest["timestamp"] = pd.to_datetime(latest["timestamp"], errors="coerce", utc=True)
    latest = latest.dropna(subset=["timestamp"]).sort_values("timestamp").groupby("machine_id", as_index=False).tail(1).copy()
    if latest.empty:
        st.info("No hay máquinas con lecturas válidas.")
        return
    snapshot = obtener_instantanea()
    reference = pd.to_datetime(snapshot.get("captured_at"), utc=True) if snapshot and snapshot.get("captured_at") else pd.Timestamp.now(tz="UTC")
    st.markdown("""
    <style>
    .alert-overview { display:grid; grid-template-columns:repeat(4,minmax(0,1fr)); gap:.7rem; margin:.35rem 0 .7rem; }
    .alert-summary { background:#0c1a2e; border:1px solid #1e344a; border-radius:10px; padding:.8rem 1rem; border-top:3px solid var(--accent); }
    .alert-summary-label { color:#b9cde0; font-size:.85rem; font-weight:700; }
    .alert-summary-value { color:#f3f8ff; font-size:1.5rem; font-weight:750; margin-top:.25rem; }
    .alert-summary-note { color:#94aac0; font-size:.75rem; margin-top:.15rem; }
    [class*="st-key-alert_larria_"] button, [class*="st-key-alert_larria_"] button * { background:#9e3041 !important; color:#fff !important; border-color:#bb4758 !important; }
    [class*="st-key-alert_kontuz_"] button, [class*="st-key-alert_kontuz_"] button * { background:#e2b242 !important; color:#20210e !important; border-color:#f0c45c !important; }
    [class*="st-key-alert_ok_"] button, [class*="st-key-alert_ok_"] button * { background:#16775f !important; color:#fff !important; border-color:#28987b !important; }
    [class*="st-key-alert_antigua_"] button, [class*="st-key-alert_antigua_"] button * { background:#47596d !important; color:#fff !important; border-color:#718498 !important; }
    [class*="st-key-alert_larria_"] button:hover, [class*="st-key-alert_kontuz_"] button:hover, [class*="st-key-alert_ok_"] button:hover, [class*="st-key-alert_antigua_"] button:hover { filter:brightness(1.14); }
    @media (max-width:900px) { .alert-overview { grid-template-columns:repeat(2,minmax(0,1fr)); } }
    @media (max-width:560px) { .alert-overview { grid-template-columns:1fr; } }
    </style>
    """, unsafe_allow_html=True)
    search_col, level_col, freshness_col = st.columns([1.4, 1, 1])
    with search_col:
        search = st.text_input("Buscar máquina", placeholder="CNC-001", key="alert_search").strip()
    with level_col:
        selected_level = st.selectbox("Nivel", ["Todas", "LARRIA", "KONTUZ", "OK", "Lectura antigua"], key="alert_filter_level")
    with freshness_col:
        freshness = st.selectbox("Avisar si no hay lectura durante", [5, 15, 30, 60], index=1,
                                 format_func=lambda minutes: f"{minutes} minutos", key="alert_freshness_minutes")
    latest["_antigua"] = (reference - latest["timestamp"]) > pd.Timedelta(minutes=freshness)
    latest["_categoria"] = latest["alert_level"].where(~latest["_antigua"], "Lectura antigua")
    counts = latest["_categoria"].value_counts()
    critical, warning, ok, stale = (int(counts.get(name, 0)) for name in ("LARRIA", "KONTUZ", "OK", "Lectura antigua"))
    st.markdown(f"""
    <div class="alert-overview">
      <div class="alert-summary" style="--accent:#ed7185"><div class="alert-summary-label">● LARRIA</div><div class="alert-summary-value">{critical}</div><div class="alert-summary-note">Atención prioritaria</div></div>
      <div class="alert-summary" style="--accent:#eab64c"><div class="alert-summary-label">● KONTUZ</div><div class="alert-summary-value">{warning}</div><div class="alert-summary-note">Revisión recomendada</div></div>
      <div class="alert-summary" style="--accent:#43b79f"><div class="alert-summary-label">● OK</div><div class="alert-summary-value">{ok}</div><div class="alert-summary-note">Sin alerta estimada</div></div>
      <div class="alert-summary" style="--accent:#90a2b6"><div class="alert-summary-label">● LECTURA ANTIGUA</div><div class="alert-summary-value">{stale}</div><div class="alert-summary-note">Sin actualización reciente</div></div>
    </div>
    """, unsafe_allow_html=True)
    st.caption(f"Última predicción por máquina entre las 2.000 consultadas. Una lectura se considera antigua tras {freshness} minutos; esto no confirma una desconexión. No se incluyen máquinas sin predicciones en ese conjunto.")
    if search:
        latest = latest[latest["machine_id"].astype(str).str.contains(search, case=False, regex=False, na=False)]
    if selected_level != "Todas":
        latest = latest[latest["_categoria"] == selected_level]
    if latest.empty:
        st.info("No hay máquinas que coincidan con los filtros. Comprueba la llegada de datos si esperabas ver alguna.")
        return
    latest["_orden"] = latest["_categoria"].map({"LARRIA": 0, "KONTUZ": 1, "Lectura antigua": 2, "OK": 3}).fillna(4)
    latest = latest.sort_values(["_orden", "failure_probability", "machine_id"], ascending=[True, False, True]).reset_index(drop=True)
    st.markdown("**Máquinas · ordenadas por prioridad**")
    pages = max(1, (len(latest) + 11) // 12)
    page = min(max(st.session_state.get("alert_machine_page", 1), 1), pages)
    st.session_state["alert_machine_page"] = page
    previous, position, following, _ = st.columns([1, 2, 1, 6])
    if previous.button("←", key="alert_machine_prev", disabled=page == 1, help="Página anterior"):
        st.session_state["alert_machine_page"] = page - 1
        st.rerun()
    position.markdown(f"**Página {page} de {pages}**")
    if following.button("→", key="alert_machine_next", disabled=page == pages, help="Página siguiente"):
        st.session_state["alert_machine_page"] = page + 1
        st.rerun()
    columns = st.columns(3)
    for index, (_, row) in enumerate(latest.iloc[(page - 1) * 12:page * 12].iterrows()):
        name = str(row["machine_id"])
        level = "antigua" if row["_antigua"] else str(row["alert_level"]).lower()
        status = f"ANTIGUA · último {row['alert_level']}" if row["_antigua"] else str(row["alert_level"])
        label = f"{status}  ·  {name}  ·  {row['failure_probability']:.1%}"
        with columns[index % 3]:
            with st.container(key=f"alert_{level}_{index}"):
                if st.button(label, key=f"alert_machine_open_{index}_{name}", use_container_width=True,
                             help=f"Última lectura: {row['timestamp'].strftime('%d/%m/%Y %H:%M:%S')} UTC"):
                    st.session_state["table_dialog_row"] = row.to_dict()
    abrir_detalle_tabla()


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
if hasattr(st, "fragment"):
    # Conserva la misma estructura de página al activar o desactivar el temporizador.
    @st.fragment(run_every=refresh_seconds or None)
    def render_auto_refresh():
        render_page()

    render_auto_refresh()
else:
    render_page()
