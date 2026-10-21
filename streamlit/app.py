"""CNC Guard — Streamlit panela.

  1. Iragarpen eskuzkoa: sentsore-balioak sartu eta Scoring API-ri galdetu (/predict).
  2. Monitorizazioa: NiFi-k Elasticsearch-en (cnc-predictions) utzitako iragarpenak ikusi.
"""

import os
import time

import pandas as pd
import requests
import streamlit as st

API_URL = os.getenv("API_URL", "http://scoring-api:8000").rstrip("/")
API_USERNAME = os.getenv("API_USERNAME", "nifi")
API_PASSWORD = os.getenv("API_PASSWORD", "")
ES_URL = os.getenv("ES_URL", "http://elasticsearch:9200").rstrip("/")
ES_INDEX = os.getenv("ES_INDEX", "cnc-predictions")

MAILAK = ["OK", "KONTUZ", "LARRIA"]
KOLOREAK = {"OK": "#2e7d32", "KONTUZ": "#f9a825", "LARRIA": "#c62828"}

st.set_page_config(page_title="CNC Guard", page_icon="🛠️", layout="wide")


# ── API: autentifikazioa ──────────────────────────────────────────────────────
def lortu_tokena(behartu: bool = False) -> str:
    """Access tokena cachean gordetzen da iraungitzera arte (5 min, 10 s tarte batekin)."""
    tok = st.session_state.get("token")
    if not behartu and tok and tok["iraungitzea"] > time.time() + 10:
        return tok["access"]
    r = requests.post(
        f"{API_URL}/auth/token",
        data={"grant_type": "password", "username": API_USERNAME, "password": API_PASSWORD},
        timeout=5,
    )
    r.raise_for_status()
    d = r.json()
    st.session_state["token"] = {
        "access": d["access_token"],
        "iraungitzea": time.time() + d["expires_in"],
    }
    return d["access_token"]


def iragarri(datuak: dict) -> dict:
    for saiakera in range(2):
        tok = lortu_tokena(behartu=saiakera > 0)
        r = requests.post(
            f"{API_URL}/predict", json=datuak, headers={"Authorization": f"Bearer {tok}"}, timeout=10
        )
        if r.status_code == 401 and saiakera == 0:
            continue
        r.raise_for_status()
        return r.json()
    raise RuntimeError("Ezin izan da autentifikatu")


def api_egoera() -> tuple[bool, str]:
    try:
        d = requests.get(f"{API_URL}/health", timeout=3).json()
        return bool(d.get("model_loaded")), "Eredua kargatuta" if d.get("model_loaded") else "API martxan, eredurik gabe"
    except Exception as e:
        return False, f"API ez dago eskuragarri ({type(e).__name__})"


# ── Elasticsearch ─────────────────────────────────────────────────────────────
def es_bilatu(gorputza: dict) -> dict:
    r = requests.post(f"{ES_URL}/{ES_INDEX}/_search", json=gorputza, timeout=10)
    r.raise_for_status()
    return r.json()


def denbora_iragazkia(ordu: int | None) -> list:
    if ordu is None:
        return []
    return [{"range": {"timestamp": {"gte": f"now-{ordu}h"}}}]


def es_egoera() -> tuple[bool, int]:
    try:
        r = requests.get(f"{ES_URL}/{ES_INDEX}/_count", timeout=3)
        r.raise_for_status()
        return True, r.json()["count"]
    except Exception:
        return False, 0


# ── Albo-barra ────────────────────────────────────────────────────────────────
with st.sidebar:
    st.title("🛠️ CNC Guard")
    ok, mezua = api_egoera()
    st.markdown(f"**Scoring API:** {'🟢' if ok else '🔴'} {mezua}")
    es_ok, dokumentuak = es_egoera()
    st.markdown(
        f"**Elasticsearch:** {'🟢' if es_ok else '🔴'} "
        + (f"`{ES_INDEX}`: {dokumentuak} dok." if es_ok else "ez dago eskuragarri")
    )
    st.divider()
    tartea = st.selectbox(
        "Denbora-tartea",
        ["Guztia", "Azken ordua", "Azken 6 orduak", "Azken 24 orduak", "Azken 7 egunak"],
        help="Datuen timestamp-a simuladoreak jartzen du; hutsik badago, hautatu 'Guztia'.",
    )
    ORDUAK = {"Guztia": None, "Azken ordua": 1, "Azken 6 orduak": 6, "Azken 24 orduak": 24, "Azken 7 egunak": 168}
    ordu = ORDUAK[tartea]
    auto = st.toggle("Auto-eguneratu (10 s)", value=False)

tab_eskuz, tab_monitor = st.tabs(["🔮 Iragarpen eskuzkoa", "📈 Monitorizazioa"])


# ── 1. fitxa: iragarpen eskuzkoa ──────────────────────────────────────────────
with tab_eskuz:
    st.subheader("Makina baten hutsegite-probabilitatea")
    with st.form("iragarpena"):
        c1, c2 = st.columns(2)
        machine_id = c1.text_input("Makina ID", "CNC-001")
        machine_type = c2.selectbox("Mota", ["L", "M", "H"], help="L = baxua, M = ertaina, H = altua")
        c3, c4 = st.columns(2)
        air = c3.number_input("Aire tenperatura [K]", 280.0, 330.0, 300.0, 0.1)
        proc = c4.number_input("Prozesu tenperatura [K]", 290.0, 340.0, 310.0, 0.1)
        c5, c6, c7 = st.columns(3)
        rpm = c5.number_input("Biraketa [rpm]", 0.0, 4000.0, 1500.0, 10.0)
        torque = c6.number_input("Momentua [Nm]", 0.0, 100.0, 40.0, 0.1)
        wear = c7.number_input("Erreminta higadura [min]", 0.0, 400.0, 100.0, 1.0)
        bidali = st.form_submit_button("Iragarri", type="primary")

    if bidali:
        try:
            em = iragarri(
                {
                    "machine_id": machine_id,
                    "machine_type": machine_type,
                    "air_temp_K": air,
                    "process_temp_K": proc,
                    "rpm": rpm,
                    "torque_Nm": torque,
                    "tool_wear_min": wear,
                }
            )
            maila = em["alert_level"]
            prob = em["failure_probability"]
            a, b, c = st.columns(3)
            a.metric("Alerta maila", maila)
            b.metric("Hutsegite probabilitatea", f"{prob:.1%}")
            c.metric("Hutsegitea iragarrita", "Bai" if em["failure_predicted"] else "Ez")
            st.progress(min(max(prob, 0.0), 1.0))
            {"OK": st.success, "KONTUZ": st.warning, "LARRIA": st.error}[maila](
                f"{em['machine_id']}: {maila} ({prob:.1%})"
            )
        except requests.HTTPError as e:
            st.error(f"API errorea: {e.response.status_code} — {e.response.text[:300]}")
        except Exception as e:
            st.error(f"Ezin izan da APIarekin konektatu: {e}")


# ── 2. fitxa: monitorizazioa ──────────────────────────────────────────────────
def monitorizazioa():
    iragazkia = denbora_iragazkia(ordu)
    try:
        agg = es_bilatu(
            {
                "size": 0,
                "query": {"bool": {"filter": iragazkia}},
                "aggs": {"maila": {"terms": {"field": "alert_level.keyword", "size": 10}}},
            }
        )
    except requests.HTTPError as e:
        if e.response.status_code == 404:
            st.info(f"`{ES_INDEX}` indizea ez dago oraindik. Abiarazi NiFi-ko Streaming flow-a datuak sortzeko.")
        else:
            st.error(f"Elasticsearch errorea: {e}")
        return
    except Exception as e:
        st.error(f"Ezin izan da Elasticsearch-i galdetu: {e}")
        return

    kopuruak = {b["key"]: b["doc_count"] for b in agg["aggregations"]["maila"]["buckets"]}
    guztira = sum(kopuruak.values())
    if guztira == 0:
        st.info("Ez dago daturik hautatutako denbora-tartean. Probatu 'Guztia'.")
        return

    cols = st.columns(4)
    cols[0].metric("Iragarpenak guztira", guztira)
    for col, m in zip(cols[1:], MAILAK):
        n = kopuruak.get(m, 0)
        col.metric(m, n, f"{n / guztira:.1%}", delta_color="off")

    hautatu = st.multiselect("Iragazi alerta mailaren arabera", MAILAK, default=MAILAK)
    iragazkiak = iragazkia + [{"terms": {"alert_level.keyword": hautatu}}]
    docs = es_bilatu(
        {
            "size": 1000,
            "sort": [{"timestamp": "desc"}],
            "query": {"bool": {"filter": iragazkiak}},
            "_source": ["timestamp", "machine_id", "failure_probability", "alert_level", "failure_predicted"],
        }
    )["hits"]["hits"]
    if not docs:
        st.info("Ez dago daturik iragazki horrekin.")
        return
    df = pd.DataFrame([d["_source"] for d in docs])
    df["timestamp"] = pd.to_datetime(df["timestamp"])

    g1, g2 = st.columns(2)
    with g1:
        st.markdown("**Alerta mailen banaketa**")
        st.bar_chart(pd.Series(kopuruak).reindex(MAILAK).fillna(0), color="#1f77b4")
    with g2:
        st.markdown("**Hutsegite probabilitatea denboran (makinaka)**")
        pivot = df.pivot_table(index="timestamp", columns="machine_id", values="failure_probability", aggfunc="max")
        st.line_chart(pivot)

    st.markdown("**Makinak arriskuaren arabera** (probabilitate maximoa)")
    top = (
        df.groupby("machine_id")
        .agg(max_prob=("failure_probability", "max"), alertak=("alert_level", lambda s: (s != "OK").sum()), azkena=("timestamp", "max"))
        .sort_values("max_prob", ascending=False)
        .head(15)
    )
    st.dataframe(
        top,
        use_container_width=True,
        column_config={"max_prob": st.column_config.ProgressColumn("Probabilitate max.", min_value=0.0, max_value=1.0, format="%.2f")},
    )

    st.markdown("**Azken iragarpenak**")
    st.dataframe(df.head(100), use_container_width=True, hide_index=True)


with tab_monitor:
    st.subheader(f"NiFi → Elasticsearch (`{ES_INDEX}`)")
    if auto:
        st.fragment(monitorizazioa, run_every=10)()
    else:
        monitorizazioa()
        st.button("🔄 Eguneratu")
