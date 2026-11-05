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
    light_css = """
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
        [data-testid="stDialog"][role="dialog"], [data-testid="stDialog"] [role="dialog"], [data-baseweb="modal"] [role="dialog"] { background: #f4f7fb !important; color: #172033 !important; }
        [data-baseweb="modal"] [role="dialog"] > div:first-child { color: #172b46 !important; }
        [data-baseweb="modal"] [role="dialog"] > div:nth-child(2) { color: #294563 !important; }
        [data-testid="stDialog"] h1, [data-testid="stDialog"] h2, [data-testid="stDialog"] h3,
        [data-testid="stDialog"] p, [data-testid="stDialog"] [data-testid="stCaptionContainer"] p { color: #294563 !important; }
        [data-testid="stDialog"] button[aria-label="Close"] svg { color: #294563 !important; fill: #294563 !important; }
        [data-testid="stMetric"], [data-testid="stForm"], [data-testid="stArrowVegaLiteChart"], [data-testid="stAltairChart"], [data-testid="stVegaLiteChart"] { background: #ffffff !important; border-color: #dbe4ef !important; box-shadow: 0 2px 12px rgba(38,72,110,.08) !important; }
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
        .stApp .alert-summary { background: #ffffff !important; border-color: #d6e5f3 !important; border-top-color: var(--accent) !important; }
        .stApp .alert-summary-label { color: #344b63 !important; }
        .stApp .alert-summary-value { color: #17304f !important; }
        .stApp .alert-summary-note { color: #526b84 !important; }
        .fleet-reading { color: #526b84 !important; border-bottom-color: #dbe4ef !important; } .fleet-reading strong { color: #17304f !important; }
        [data-testid="stCaptionContainer"] p { color: #45617c !important; }
        .stTextInput > div > div > input, .stNumberInput > div > div > input, .stSelectbox > div > div, .stMultiSelect > div > div { background: #fff !important; color: #172033 !important; border-color: #cbd9e7 !important; }
        [data-testid="stTextInput"] input::placeholder, [data-testid="stNumberInput"] input::placeholder { color: #70849a !important; opacity: 1 !important; }
        [data-testid="stSelectbox"] svg, [data-testid="stMultiSelect"] svg { color: #526b84 !important; fill: #526b84 !important; }
        [data-testid="stTextInput"] [data-baseweb="input"], [data-testid="stNumberInput"] [data-baseweb="input"] { background: #ffffff !important; border-color: #cbd9e7 !important; }
        .stNumberInput input { background: #ffffff !important; color: #172033 !important; caret-color: #172033 !important; }
        .stNumberInput button { background: #ffffff !important; color: #31516f !important; border-color: #cbd9e7 !important; }
        .stNumberInput button svg { fill: #31516f !important; color: #31516f !important; }
        [data-testid="stRadio"] label { background: #fff !important; color: #52657d !important; border-color: #cbd9e7 !important; }
        [data-testid="stRadio"] label:has(input:checked) { background: #e2f0fb !important; border-color: #78add1 !important; color: #173d5b !important; }
        [data-testid="stRadio"] label:has(input:checked) * { color: #173d5b !important; }
        .stButton > button:not([kind]), [data-testid="stSidebar"] .stButton > button { background: #ffffff !important; color: #31516f !important; border: 1px solid #cbd9e7 !important; }
        .stButton > button:not([kind]) *, [data-testid="stSidebar"] .stButton > button * { color: #31516f !important; }
        .stButton > button:not([kind]):hover, [data-testid="stSidebar"] .stButton > button:hover { background: #edf4fb !important; color: #1769b0 !important; border-color: #8bb8df !important; }
        .stButton > button:not([kind]):hover *, [data-testid="stSidebar"] .stButton > button:hover * { color: #1769b0 !important; }
        [data-testid="stBaseButton-secondary"], [data-testid="stBaseButton-secondary"] * { background: #ffffff !important; color: #31516f !important; border-color: #cbd9e7 !important; }
        [data-testid="stBaseButton-secondary"]:hover, [data-testid="stBaseButton-secondary"]:hover * { background: #edf4fb !important; color: #1769b0 !important; border-color: #8bb8df !important; }
        [class*="st-key-datos_machine_open_"] button, [class*="st-key-datos_machine_open_"] button * { background: #f3f8fd !important; color: #204761 !important; border-color: #c9deec !important; }
        [class*="st-key-datos_machine_open_"] button:hover, [class*="st-key-datos_machine_open_"] button:hover * { background: #e2f1fb !important; color: #1769b0 !important; border-color: #68b7da !important; }
        [data-testid="stSidebar"] .st-key-refresh_snapshot button { background: #dceef9 !important; border-color: #9bc8e1 !important; color: #173d5b !important; white-space: nowrap !important; }
        [data-testid="stSidebar"] .st-key-refresh_snapshot button * { color: #173d5b !important; background: transparent !important; white-space: nowrap !important; font-size: .84rem !important; }
        [data-testid="stSidebar"] .st-key-refresh_snapshot button:hover { background: #c9e5f5 !important; border-color: #67a8cc !important; }
        .stFormSubmitButton > button { background: #dceef9 !important; border-color: #9bc8e1 !important; color: #173d5b !important; }
        .stFormSubmitButton > button * { color: #173d5b !important; }
        .stFormSubmitButton > button:hover { background: #c9e5f5 !important; border-color: #67a8cc !important; color: #173d5b !important; }
        .stFormSubmitButton > button:hover * { color: #173d5b !important; }
        .stApp [class*="st-key-alert_larria_"] button, .stApp [class*="st-key-alert_larria_"] button * { background: #fae5e9 !important; color: #6f2030 !important; border-color: #dc93a0 !important; }
        .stApp [class*="st-key-alert_kontuz_"] button, .stApp [class*="st-key-alert_kontuz_"] button * { background: #fff1cf !important; color: #5b4108 !important; border-color: #ddb961 !important; }
        .stApp [class*="st-key-alert_ok_"] button, .stApp [class*="st-key-alert_ok_"] button * { background: #dff3eb !important; color: #10533e !important; border-color: #8bc7b1 !important; }
        .stApp [class*="st-key-alert_antigua_"] button, .stApp [class*="st-key-alert_antigua_"] button * { background: #e6edf3 !important; color: #35495c !important; border-color: #aabac9 !important; }
        [data-testid="stSidebar"] .stButton > button:focus-visible, .stButton > button:focus-visible { outline: 2px solid #1769b0 !important; outline-offset: 2px; }
        [data-baseweb="popover"] *, [role="listbox"] *, [role="option"] { color: #263f58 !important; }
        [data-baseweb="tooltip"] > div { background: #ffffff !important; border: 1px solid #cbd9e7 !important; }
        [data-baseweb="tooltip"] [data-testid="stTooltipContent"], [data-baseweb="tooltip"] [data-testid="stTooltipContent"] * { color: #263f58 !important; }
        [role="option"][aria-selected="true"] { background: #e5f0fc !important; color: #1769b0 !important; }
        [data-baseweb="popover"], [data-baseweb="menu"], [role="listbox"] { background: #ffffff !important; border-color: #cbd9e7 !important; }
        [data-baseweb="popover"] [role="option"], [data-baseweb="menu"] [role="option"], [role="listbox"] [role="option"] { background: #ffffff !important; color: #263f58 !important; }
        [data-baseweb="popover"] [role="option"] *, [data-baseweb="menu"] [role="option"] *, [role="listbox"] [role="option"] * { color: #263f58 !important; }
        [data-baseweb="popover"] [role="option"]:hover, [data-baseweb="menu"] [role="option"]:hover, [role="listbox"] [role="option"]:hover { background: #edf4fb !important; color: #1769b0 !important; }
        [data-baseweb="popover"] [role="option"][aria-selected="true"], [data-baseweb="menu"] [role="option"][aria-selected="true"] { background: #e5f0fc !important; color: #1769b0 !important; }
        [data-baseweb="menu"] li, [data-baseweb="popover"] li { background: #ffffff !important; color: #263f58 !important; }
        [data-baseweb="menu"] li:hover, [data-baseweb="popover"] li:hover { background: #edf4fb !important; color: #1769b0 !important; }
        </style>
        """
    if current_theme() == "automatic":
        light_css = light_css.replace(
            "<style>",
            "<style>@media (prefers-color-scheme: light) {",
            1,
        ).replace("</style>", "}</style>", 1)
    st.markdown(light_css, unsafe_allow_html=True)
