"""Gestión del tema visual de CNC Guard.

El estado se guarda en ``st.session_state`` para que el tema se conserve
durante la navegación y los reruns de Streamlit.
"""

import streamlit as st


THEMES = {"automatic": "Automático", "dark": "Oscuro", "light": "Claro"}


def current_theme() -> str:
    return st.session_state.get("theme", "automatic")


def render_theme_switch() -> None:
    """Pinta un menú para seleccionar el tema claro u oscuro."""
    theme = current_theme()
    options = THEMES
    selected = st.selectbox(
        "Tema",
        options=list(options),
        format_func=options.get,
        index=list(options).index(theme),
        key="theme_selector",
    )
    if selected != theme:
        st.session_state.theme = selected
        st.rerun()


def apply_theme() -> None:
    """Aplica los overrides de color sobre los estilos base de la aplicación."""
    # Automático utiliza la paleta clara por defecto para mantener una
    # interfaz legible también cuando el navegador no expone su preferencia.
    if current_theme() == "dark":
        return
    st.markdown(
        """
        <style>
        .stApp { background: #f4f7fb !important; color: #172033 !important; }
        [data-testid="stSidebar"] { background: #ffffff !important; border-right-color: #dbe4ef !important; box-shadow: 3px 0 20px rgba(30,55,90,.08) !important; }
        [data-testid="stSidebar"] * { color: #52657d !important; }
        .sb-logo, .sb-logo span { color: #17304f !important; }
        .sb-sub, .sb-stitle { color: #7890a9 !important; }
        [data-testid="stSidebar"] .stButton > button { color: #536b85 !important; }
        [data-testid="stSidebar"] .stButton > button:hover { background: #edf4fb !important; color: #1f5f9f !important; }
        [data-testid="stSidebar"] [data-testid="stBaseButton-primary"], [data-testid="stSidebar"] .stButton > button[kind="primary"] { background: #e5f0fc !important; color: #1769b0 !important; }
        .page-header { background: rgba(244,247,251,.92) !important; border-bottom-color: #dbe4ef !important; }
        .page-header h2, h1 { color: #172b46 !important; }
        h2 { color: #294563 !important; } h3 { color: #49637f !important; }
        [data-testid="stMetric"], [data-testid="stForm"], [data-testid="stAltairChart"], [data-testid="stVegaLiteChart"] { background: #ffffff !important; border-color: #dbe4ef !important; box-shadow: 0 2px 12px rgba(38,72,110,.08) !important; }
        [data-testid="stMetricLabel"] { color: #60758e !important; } [data-testid="stMetricValue"] { color: #17304f !important; }
        [data-testid="stMarkdownContainer"], [data-testid="stMarkdownContainer"] p, [data-testid="stMarkdownContainer"] li, label, .stCaption, [data-testid="stCaptionContainer"] { color: #344b63 !important; }
        [data-testid="stTextInputRootElement"] label, [data-testid="stNumberInputRootElement"] label, [data-testid="stSelectbox"] label, [data-testid="stMultiSelect"] label { color: #344b63 !important; }
        [data-testid="stDataFrame"] { border-color: #dbe4ef !important; }
        [data-testid="stDataFrame"] * { color: #263f58 !important; }
        [data-testid="stAlert"] { color: #263f58 !important; }
        [data-testid="stAlert"] p { color: #263f58 !important; }
        [data-testid="stProgressBar"] { background: #dce7f1 !important; }
        [data-testid="stRadio"] label { color: #344b63 !important; }
        [data-testid="stCheckbox"] label { color: #344b63 !important; }
        .sb-lbl { color: #48627d !important; } .sb-val { color: #607b96 !important; }
        .sb-status { background: #f5f8fb !important; border-color: #dbe4ef !important; }
        .dash-kpi { background: linear-gradient(135deg,#fff,#edf5fd) !important; border-color: #d6e5f3 !important; }
        .dash-kpi-label { color: #526b84 !important; } .dash-kpi-value { color: #17304f !important; } .dash-kpi-detail { color: #647c95 !important; }
        [data-testid="stCaptionContainer"] p { color: #45617c !important; }
        .stTextInput > div > div > input, .stNumberInput > div > div > input, .stSelectbox > div > div, .stMultiSelect > div > div { background: #fff !important; color: #172033 !important; border-color: #cbd9e7 !important; }
        .stNumberInput input { background: #ffffff !important; color: #172033 !important; caret-color: #172033 !important; }
        .stNumberInput button { background: #ffffff !important; color: #31516f !important; border-color: #cbd9e7 !important; }
        .stNumberInput button svg { fill: #31516f !important; color: #31516f !important; }
        [data-testid="stRadio"] label { background: #fff !important; color: #52657d !important; border-color: #cbd9e7 !important; }
        [data-testid="stRadio"] label:has(input:checked) { background: linear-gradient(135deg,#1769c2,#2453a5) !important; border-color: #1769c2 !important; color: #fff !important; }
        [data-testid="stRadio"] label:has(input:checked) * { color: #fff !important; }
        .stButton > button:not([kind]), [data-testid="stSidebar"] .stButton > button { background: #ffffff !important; color: #31516f !important; border: 1px solid #cbd9e7 !important; }
        .stButton > button:not([kind]) *, [data-testid="stSidebar"] .stButton > button * { color: #31516f !important; }
        .stButton > button:not([kind]):hover, [data-testid="stSidebar"] .stButton > button:hover { background: #edf4fb !important; color: #1769b0 !important; border-color: #8bb8df !important; }
        .stButton > button:not([kind]):hover *, [data-testid="stSidebar"] .stButton > button:hover * { color: #1769b0 !important; }
        [data-testid="stBaseButton-secondary"], [data-testid="stBaseButton-secondary"] * { background: #ffffff !important; color: #31516f !important; border-color: #cbd9e7 !important; }
        [data-testid="stBaseButton-secondary"]:hover, [data-testid="stBaseButton-secondary"]:hover * { background: #edf4fb !important; color: #1769b0 !important; border-color: #8bb8df !important; }
        .st-key-refresh_alertas button, .st-key-refresh_datos button { background: #ffffff !important; color: #31516f !important; border: 1px solid #cbd9e7 !important; }
        .st-key-refresh_alertas button *, .st-key-refresh_datos button * { color: #31516f !important; }
        .st-key-refresh_alertas button:hover, .st-key-refresh_datos button:hover { background: #edf4fb !important; color: #1769b0 !important; }
        .st-key-refresh_alertas button:hover *, .st-key-refresh_datos button:hover * { color: #1769b0 !important; }
        .stFormSubmitButton > button { background: linear-gradient(135deg,#1769c2,#2453a5) !important; color: #fff !important; }
        .stFormSubmitButton > button * { color: #fff !important; }
        .stFormSubmitButton > button:hover { background: linear-gradient(135deg,#12589f,#1e4288) !important; color: #fff !important; }
        .stFormSubmitButton > button:hover * { color: #fff !important; }
        [data-baseweb="popover"] *, [role="listbox"] *, [role="option"] { color: #263f58 !important; }
        [role="option"][aria-selected="true"] { background: #e5f0fc !important; color: #1769b0 !important; }
        </style>
        """,
        unsafe_allow_html=True,
    )
