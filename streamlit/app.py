"""CNC Guard — Streamlit panela."""

import os
import time

import altair as alt
import pandas as pd
import requests
import streamlit as st

API_URL      = os.getenv("API_URL",      "http://scoring-api:8000").rstrip("/")
API_USERNAME = os.getenv("API_USERNAME", "nifi")
API_PASSWORD = os.getenv("API_PASSWORD", "")
ES_URL       = os.getenv("ES_URL",       "http://elasticsearch:9200").rstrip("/")
ES_INDEX     = os.getenv("ES_INDEX",     "cnc-predictions")

MAILAK   = ["OK", "KONTUZ", "LARRIA"]

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
.block-container              { max-width: 1500px; padding: 0 1.5rem 1.5rem !important; }

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
    margin: 0 -1.5rem 1.5rem;
    padding: 1rem 1.5rem;
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
    color: #243a52 !important;
    font-weight: 700 !important;
    font-size: .58rem !important;
    letter-spacing: .12em !important;
    text-transform: uppercase;
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


# ── Helpers API ────────────────────────────────────────────────────────────────
def lortu_tokena(behartu: bool = False) -> str:
    tok = st.session_state.get("token")
    if not behartu and tok and tok["exp"] > time.time() + 10:
        return tok["access"]
    r = requests.post(
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
        r = requests.post(f"{API_URL}/predict", json=datuak,
                          headers={"Authorization": f"Bearer {tok}"}, timeout=10)
        if r.status_code == 401 and i == 0:
            continue
        r.raise_for_status()
        return r.json()
    raise RuntimeError("No se pudo autenticar")


@st.cache_data(ttl=10, show_spinner=False)
def api_egoera() -> tuple[bool, str]:
    try:
        d = requests.get(f"{API_URL}/health", timeout=3).json()
        ok = bool(d.get("model_loaded"))
        return ok, "Modelo OK" if ok else "Sin modelo"
    except Exception:
        return False, "Offline"


# ── Helpers Elasticsearch ──────────────────────────────────────────────────────
def es_bilatu(body: dict) -> dict:
    r = requests.post(f"{ES_URL}/{ES_INDEX}/_search", json=body, timeout=10)
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
        "_source": ["timestamp", "machine_id", "failure_probability", "alert_level"],
    })


def es_egoera() -> tuple[bool, int]:
    try:
        return True, es_count_cached()
    except Exception:
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

    alertas_n = alerta_kopurua()

    nav = [
        ("·", "Inicio",        "Dashboard"),
        ("·", "Datos",         "Datos"),
        ("·", "Predicciones",  "Predicciones"),
        ("·", f"Alertas{'  (' + str(alertas_n) + ')' if alertas_n else ''}", "Alertas"),
    ]

    for icon, label, key in nav:
        active = st.session_state.atal == key
        marker = "▸" if active else "·"
        if st.button(f"{marker}  {label}", key=f"nav_{key}", use_container_width=True,
                     type="primary" if active else "secondary"):
            st.session_state.atal = key
            # Re-renderiza también la barra para que el estado activo cambie
            # en el mismo clic, no en la siguiente interacción.
            st.rerun()

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

    ordu = None


# ── Helpers visualización ──────────────────────────────────────────────────────
def altair_config():
    """Configuración común para gráficos Altair con fondo transparente."""
    return dict(
        configure_view=dict(strokeWidth=0, fill="transparent"),
        configure_axis=dict(
            gridColor="rgba(255,255,255,.05)",
            domainColor="rgba(255,255,255,.08)",
            tickColor="transparent",
            labelColor="#3a5572",
            titleColor="#3a5572",
        ),
        configure_title=dict(color="#3a5572"),
    )


def chart_bar(data, x, y, color_field=None, color_range=None, height=160):
    base = (
        alt.Chart(data)
        .mark_bar(cornerRadiusTopLeft=5, cornerRadiusTopRight=5)
        .encode(
            x=alt.X(x, title=None),
            y=alt.Y(y, title=None),
            **({"color": alt.Color(color_field,
                                   scale=alt.Scale(range=color_range) if color_range else alt.Scale(scheme="blues"),
                                   legend=None)} if color_field else {}),
            tooltip=[x, y],
        )
        .properties(width="container", height=height)
        .configure_view(strokeWidth=0, fill="transparent")
        .configure_axis(
            gridColor="rgba(255,255,255,.05)",
            domainColor="rgba(255,255,255,.08)",
            tickColor="transparent",
            labelColor="#3a5572",
        )
    )
    return base


# ── Dashboard ──────────────────────────────────────────────────────────────────
def page_dashboard():
    st.markdown("""
    <div class="page-header pg-in">
      <div>
        <h2>Dashboard · Mantenimiento Predictivo</h2>
        <p>Resumen en tiempo real del estado de las máquinas CNC</p>
      </div>
    </div>
    """, unsafe_allow_html=True)

    # Cargar datos
    try:
        hits = cargar_dashboard()
        df = pd.DataFrame([h["_source"] for h in hits])
    except Exception:
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
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Máquinas",      last["machine_id"].nunique())
    m2.metric("Sin alertas",   int((last["alert_level"] == "OK").sum()))
    m3.metric("Con alerta",    int((last["alert_level"] != "OK").sum()))
    m4.metric("Riesgo máximo", f"{last['failure_probability'].max():.1%}")

    st.markdown("<div style='height:12px'></div>", unsafe_allow_html=True)

    c1, c2 = st.columns(2)
    with c1:
        st.caption("DISTRIBUCIÓN DE ALERTAS")
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
        st.caption("EVOLUCIÓN DEL RIESGO (media 5 min)")
        serie = (df.set_index("timestamp").sort_index()
                   .groupby(pd.Grouper(freq="5min"))["failure_probability"].mean())
        st.line_chart(serie, color="#38bdf8", height=160)

    c3, c4 = st.columns(2)
    with c3:
        st.caption("TOP MÁQUINAS POR RIESGO")
        top_maq = (df.groupby("machine_id", as_index=False)["failure_probability"]
                     .max().nlargest(10, "failure_probability"))
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
            .properties(width="container", height=160)
            .configure_view(strokeWidth=0, fill="transparent")
            .configure_axis(
                gridColor="rgba(255,255,255,.05)",
                domainColor="rgba(255,255,255,.08)",
                tickColor="transparent",
                labelColor="#3a5572",
            )
        )
        st.altair_chart(ch2, use_container_width=True)

    with c4:
        st.caption("DISTRIBUCIÓN DE PROBABILIDADES")
        bins = pd.cut(df["failure_probability"], bins=[0,.2,.4,.6,.8,1], include_lowest=True)
        hdf  = bins.value_counts().sort_index().rename_axis("rango").reset_index(name="n")
        hdf["rango"] = hdf["rango"].astype(str)
        ch3 = chart_bar(hdf, "rango:N", "n:Q", color_field="n:Q")
        st.altair_chart(ch3, use_container_width=True)


# ── Predicciones ──────────────────────────────────────────────────────────────
def page_predicciones():
    st.markdown("""
    <div class="page-header pg-in">
      <div>
        <h2>Predicción Manual</h2>
        <p>Introduce los valores de los sensores para obtener la probabilidad de fallo</p>
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
        try:
            res   = iragarri({"machine_id": machine_id, "machine_type": machine_type,
                               "air_temp_K": air, "process_temp_K": proc,
                               "rpm": rpm, "torque_Nm": torque, "tool_wear_min": wear})
            nivel = res["alert_level"]
            prob  = res["failure_probability"]

            r1, r2, r3 = st.columns(3)
            r1.metric("Nivel de alerta",     nivel)
            r2.metric("Probabilidad fallo",  f"{prob:.1%}")
            r3.metric("Fallo predicho",      "Sí" if res["failure_predicted"] else "No")
            st.progress(float(min(max(prob, 0), 1)))
            {"OK": st.success, "KONTUZ": st.warning, "LARRIA": st.error}[nivel](
                f"{machine_id} → {nivel}  ({prob:.1%})")
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
    df = pd.DataFrame([h["_source"] for h in hits])
    if not df.empty:
        df["timestamp"] = pd.to_datetime(df["timestamp"], errors="coerce")
        df["failure_probability"] = pd.to_numeric(df["failure_probability"], errors="coerce")
        df = df.dropna(subset=["timestamp", "failure_probability"])
    return df


def page_datos():
    st.markdown(f"""<div class="page-header pg-in"><div><h2>Explorador de datos</h2>
    <p>Consulta, filtra y revisa las predicciones almacenadas · {ES_INDEX}</p></div></div>""", unsafe_allow_html=True)
    c1, c2, c3 = st.columns([2, 1, 1])
    sel = c1.multiselect("Niveles", MAILAK, default=MAILAK, key="datos_niveles")
    limite = c2.selectbox("Registros", [200, 500, 1000, 2000], index=1, key="datos_limite")
    buscar = c3.text_input("Máquina", placeholder="CNC-001", key="datos_maquina").strip()
    if not sel:
        st.warning("Selecciona al menos un nivel."); return
    try:
        df = cargar_df(sel, limite)
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
    st.caption("EVOLUCIÓN DEL RIESGO Y VOLUMEN DE PREDICCIONES")
    serie = df.set_index("timestamp").resample("15min")["failure_probability"].agg(["mean", "count"])
    st.line_chart(serie.rename(columns={"mean": "Riesgo medio", "count": "Predicciones"}), height=180)
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
    st.markdown("""<div class="page-header pg-in"><div><h2>Centro de alertas</h2>
    <p>Prioriza incidencias y localiza rápidamente las máquinas con mayor riesgo</p></div>
    <span class="ph-badge">CONSULTA OPTIMIZADA · 10 s</span></div>""", unsafe_allow_html=True)
    try:
        df = cargar_df(["KONTUZ", "LARRIA"], 2000)
    except Exception as e:
        st.error(f"No se pudieron cargar las alertas: {e}"); return
    if df.empty:
        st.success("No hay alertas activas en los registros recientes."); return
    criticas = int((df["alert_level"] == "LARRIA").sum())
    afectadas = df.loc[df["alert_level"] != "OK", "machine_id"].nunique()
    riesgo = df["failure_probability"].max()
    a1, a2, a3, a4 = st.columns(4)
    a1.metric("Alertas visibles", len(df)); a2.metric("Críticas", criticas)
    a3.metric("Máquinas afectadas", afectadas); a4.metric("Riesgo máximo", f"{riesgo:.1%}")
    left, right = st.columns([1, 2])
    with left:
        st.caption("SEVERIDAD")
        severidad = (df["alert_level"].value_counts()
                     .reindex(["LARRIA", "KONTUZ"]).fillna(0)
                     .rename_axis("nivel").reset_index(name="n"))
        st.altair_chart(
            chart_bar(severidad, "nivel:N", "n:Q", color_field="nivel:N",
                      color_range=["#fb7185", "#fbbf24"], height=190),
            use_container_width=True,
        )
    with right:
        st.caption("MÁQUINAS QUE REQUIEREN ATENCIÓN")
        top = df.groupby("machine_id", as_index=False).agg(
            riesgo_max=("failure_probability", "max"), eventos=("alert_level", "size"), ultima=("timestamp", "max")
        ).sort_values(["riesgo_max", "eventos"], ascending=False).head(15)
        st.dataframe(top, use_container_width=True, hide_index=True, height=220, column_config={
            "riesgo_max": st.column_config.ProgressColumn("Riesgo máx.", min_value=0.0, max_value=1.0, format="%.1%"),
            "ultima": st.column_config.DatetimeColumn("Último evento", format="DD/MM/YYYY HH:mm"),
        })
    st.caption("ÚLTIMOS EVENTOS · ordenados por riesgo")
    recientes = df.sort_values(["failure_probability", "timestamp"], ascending=False).head(100)
    st.dataframe(recientes, use_container_width=True, hide_index=True, height=300, column_config={
        "timestamp": st.column_config.DatetimeColumn("Fecha / Hora", format="DD/MM/YYYY HH:mm:ss"),
        "failure_probability": st.column_config.ProgressColumn("Prob. fallo", min_value=0.0, max_value=1.0, format="%.1%"),
    })
    if st.button("↺ Actualizar alertas", key="refresh_alertas"):
        cargar_documentos.clear(); cargar_dashboard.clear(); alerta_kopurua_cached.clear(); st.rerun()


# ── Router ─────────────────────────────────────────────────────────────────────
if atala == "Dashboard":
    page_dashboard()
elif atala == "Predicciones":
    page_predicciones()
elif atala == "Datos":
    page_datos()
elif atala == "Alertas":
    page_alertas()
