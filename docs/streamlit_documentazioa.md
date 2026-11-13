# NEXO CNC — Streamlit Panela

CNC makinen denbora errealeko egoera monitorizatzeko, sentsoreen telemetria bistaratzeko, alertak kudeatzeko eta Machine Learning bidezko iragarpenak eskuz simulatzeko web aplikazio interaktiboa, **Streamlit** erabiliz garatua.

---

## Funtzionalitateak eta Atal Nagusiak

Aplikazioak alboko barratik eskuragarri dauden 4 atal nagusi ditu:

### 1. Aginte-panela (Makinen egoera)
* **KPI orokorrak**: Monitorizatutako makina kopurua, alerta aktiboak, flotaren batez besteko arrisku-maila eta giro-tenperatura.
* **Makinen lehentasun-zerrenda**: Azken iragarpenaren arabera huts egiteko arriskurik handiena duten makinak lehenetsita.
* **Makinaren xehetasuna**: Makina bat hautatzean, honako datuak erakusten dira:
  * Grafiko tenporal interaktiboak (erremintaren higadura, motorraren torkea, tenperaturak).
  * Lan-eremu egonkorrak uneko balioen aurrean.
  * Torkearen eta higaduraren arteko erlazioa (`wear_torque`) eta jauzi termikoa (`temp_diff_K`).

### 2. Eskuzko Iragarpena (Simulagailua)
* Makina baten parametro operatiboak eskuz sartzeko formulario interaktiboa:
  * Makina mota (`L`, `M`, `H`)
  * Giro-tenperatura eta prozesu-tenperatura (K)
  * Errotazio-abiadura (RPM)
  * Torkea (Nm)
  * Erremintaren higadura (min)
* Scoring API-a kontsultatuz, huts egiteko probabilitatea eta dagokion alerta-maila denbora errealean kalkulatzen ditu.

### 3. Datuen Esploratzailea
* Elasticsearch-en gordetako iragarpenen eta telemetriaren erregistroen taula interaktiboa.
* Iragazkiak alerta-mailaren arabera (`OK`, `KONTUZ`, `LARRIA`) eta denbora-leihoaren arabera.
* Erregistro bakoitzaren datu zehatzak taula formatuan kontsultatzeko aukera.

### 4. Alerta Zentroa
* Gorabehera aktiboetara bideratutako atala, bi larritasun-mailatan sailkatuta:
  * **KONTUZ** (Arrisku ertaina / prebentziozko higadura)
  * **LARRIA** (Arrisku kritikoa / berehalako geldialdia gomendatua)
* Mantentze-lanetako taldearentzako gertakari anomaloen erregistro historikoa.

---

## Datu-iturburuak

Streamlit aplikazioak bi zerbitzutatik jasotzen ditu datuak:

| Zerbitzua | Helmuga lehenetsia | Erabilera aplikazioan |
|---|---|---|
| **Elasticsearch** | `http://elasticsearch:9200` | Aginte-panela, grafikoak, taulak eta alertak elikatzeko:<br>• `cnc-predictions` (ML iragarpenak eta alerta-mailak)<br>• `cnc-sensors` (sentsoreen telemetria gordina) |
| **Scoring API** | `http://scoring-api:8000` | • `GET /health`: Modeloaren egoera alboko barran egiaztatzea.<br>• `POST /predict`: Eskuzko formularioaren denbora errealeko inferentzia. |

---

## Ingurune-aldagaiak eta Konfigurazioa

Konfigurazioa `.env` fitxategian edo sistemaren ingurune-aldagaietan definitzen da (`config.py` fitxategiaren bidez kudeatua):

| Aldagaia | Balio lehenetsia | Deskribapena |
|---|---|---|
| `ES_URL` | `http://elasticsearch:9200` | Elasticsearch zerbitzariaren helbidea |
| `ES_INDEX` | `cnc-predictions` | Huts-egiteen iragarpenen indizea |
| `ES_SENSOR_INDEX` | `cnc-sensors` | Sentsoreen datu gordinen indizea |
| `API_URL` | `http://scoring-api:8000` | FastAPI inferentzia-zerbitzuaren helbidea |
| `API_USERNAME` | `nifi` | APIra konektatzeko zerbitzu-erabiltzailea |
| `API_PASSWORD` | *(hutsik)* | APIra konektatzeko pasahitza |

---

## Abiarazte Gida

### Docker Compose bidez

```bash
# Streamlit zerbitzua bakarrik abiarazteko
docker compose -f docker-compose.dev.yml up -d streamlit
```
Nabigatzailetik sartzeko helbidea: **`http://localhost:8501`**

### Lokalean (Docker gabe)

```bash
# 1. Beharrezko liburutegiak instalatu
pip install -r streamlit/requirements.txt

# 2. Ingurune-aldagaiak ezarri (beharrezkoa bada)
export ES_URL="http://localhost:9200"
export API_URL="http://localhost:8000"
export API_PASSWORD="zure_pasahitza"

# 3. Streamlit abiarazi
streamlit run streamlit/app.py
```

---

## Ezaugarri Gehigarriak

* **Gai Iluna / Argia**: Alboko barran aldagarria den itxura-hautatzailea, saioan zehar hautatutako egoera mantentzen duena.
* **Datuen Argazkia (Instantánea)**: Datuen eguneraketa automatikoa aldi baterako gelditzeko aukera, gertakari baten azterketa estatikoa egiteko taulak mugitu gabe.
* **Katxe Optimizatua**: `@st.cache_data` dekoratzailearen bidezko kontsultak, Elasticsearch gainkargatu gabe erantzun-denbora azkarrak bermatzeko.

---

## Moduluaren Egitura

```text
streamlit/
├── app.py              # Sarrera nagusia, nabigazio-bideratzailea eta orriak
├── config.py           # Ingurune-aldagaien irakurketa eta konstanteak
├── requirements.txt    # Python menpekotasunak (streamlit, requests, altair, pandas...)
├── Dockerfile          # Edukiontzia sortzeko fitxategia
├── ui/
│   ├── __init__.py
│   └── theme.py        # CSS estiloak eta gai ilun/argiaren kudeaketa
└── README.md           # Moduluaren dokumentazio teknikoa
```
