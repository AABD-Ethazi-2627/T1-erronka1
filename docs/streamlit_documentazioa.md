# Streamlit dokumentazioa

## 1. Deskribapena

Streamlit aplikazioak **CNC Guard** sistemaren web-panela eskaintzen du.
Panelaren bidez CNC makinen mantentze prediktiboa monitoriza daiteke.

Aplikazioak aukera hauek eskaintzen ditu:

- Scoring APIaren egoera kontsultatzea.
- Elasticsearch-en egoera kontsultatzea.
- Metrikak, arriskuak eta alertak bistaratzea.
- Aurreikuspen historikoak aztertzea.
- Eskuzko aurreikuspenak egitea.
- Alertak makina, aldi eta mailaren arabera iragaztea.
- Gai bisuala eta eguneratze automatikoa konfiguratzea.

## 2. Karpeta-egitura

```text
streamlit/
├── app.py                    # Aplikazioaren sarrera-puntua
├── config.py                 # Ingurune-aldagaiak eta konstanteak
├── core/application.py       # Abiaraztea eta nabigazioa
├── views/                    # Aplikazioaren pantailak
│   ├── dashboard.py
│   ├── predicciones.py
│   ├── datos.py
│   └── alertas.py
├── services/                 # APIak eta datuen tratamendua
│   ├── scoring.py
│   ├── elasticsearch.py
│   ├── data.py
│   ├── http.py
│   └── exceptions.py
├── ui/                       # Estiloak, gaiak eta grafikoak
│   ├── charts.py
│   ├── icons.py
│   ├── theme.py
│   └── styles.css
├── Dockerfile
└── requirements.txt
```

`views` karpeta erabiltzen da `pages` izenaren ordez, azken hori Streamlit-en
orrialde anitzeko sistemarentzat erreserbatuta dagoelako.

## 3. Exekuzioa lokalean

`streamlit/` karpetan:

```bash
python -m venv .venv
```

Windows PowerShell-en ingurunea aktibatzeko:

```powershell
.\.venv\Scripts\Activate.ps1
```

Menpekotasunak instalatu eta aplikazioa abiarazteko:

```bash
pip install -r requirements.txt
streamlit run app.py
```

Aplikazioa `http://localhost:8501` helbidean egongo da erabilgarri.

## 4. Docker bidezko exekuzioa

Proiektuaren erro-karpetatik:

```bash
docker compose up -d --build streamlit
```

Egoera eta logak ikusteko:

```bash
docker compose ps streamlit
docker logs cnc-streamlit --tail 100
```

Streamlit-en healthcheck-a:

```text
http://localhost:8501/_stcore/health
```

## 5. Konfigurazioa

| Aldagaia | Balio lehenetsia | Deskribapena |
|---|---|---|
| `API_URL` | `http://scoring-api:8000` | Scoring APIaren URLa. |
| `API_USERNAME` | `nifi` | APIko erabiltzailea. |
| `API_PASSWORD` | hutsik | APIko pasahitza. |
| `ES_URL` | `http://elasticsearch:9200` | Elasticsearch-en URLa. |
| `ES_INDEX` | `cnc-predictions` | Kontsultatutako indizea. |

PowerShell-eko adibidea:

```powershell
$env:API_URL = "http://localhost:8000"
$env:API_USERNAME = "nifi"
$env:API_PASSWORD = "zure pasahitza"
$env:ES_URL = "http://localhost:9200"
$env:ES_INDEX = "cnc-predictions"
streamlit run app.py
```

## 6. Exekuzio-fluxua

```text
app.py
  ↓
core.application.main()
  ↓
configure_app()
  ↓
render_sidebar()
  ↓
views.<pantaila>.render()
  ↓
services eta ui
```

`app.py` fitxategiak sarrera-puntu gisa bakarrik funtzionatzen du. Aplikazioaren
logika `core`, `views`, `services` eta `ui` geruzetan banatuta dago.

## 7. Pantailak

### Dashboard-a

`views/dashboard.py` fitxategiak honako hauek erakusten ditu:

- Makina kopurua.
- Erabilgarritasuna.
- Alerta aktiboak.
- MTBFa.
- Alerta-mailen banaketa.
- Arriskuaren bilakaera.
- Arrisku handiena duten makinak.

Datuak Elasticsearch-etik lortzen dira.

### Aurreikuspenak

`views/predicciones.py` fitxategiak eskuzko aurreikuspenak egiteko formularioa
eskaintzen du. Makinaren identifikatzailea, karga mota, tenperaturak, RPMa,
motor-momentua eta erremintaren higadura erabiltzen ditu.

Aurreikuspena `services.scoring.predict()` funtzioaren bidez bidaltzen da.

### Datuak

`views/datos.py` fitxategiak datu historikoak iragazteko aukera ematen du:

- Alerta-maila.
- Erregistro kopurua.
- Makina.

Emaitzak `pandas.DataFrame` batean normalizatzen dira.

### Alertak

`views/alertas.py` fitxategiak alertak makina, denbora-tarte eta mailaren arabera
iragazten ditu. Alerta-mailak hauek dira: `OK`, `KONTUZ` eta `LARRIA`.

## 8. Zerbitzuak

### Scoring APIa

`services/scoring.py` moduluak:

1. `/auth/token` endpoint-ean tokena eskatzen du.
2. Tokena Streamlit-en saioan gordetzen du.
3. Tokena iraungi arte berrerabiltzen du.
4. `401` errore baten ondoren eskaera berriro saiatzen du.
5. APIaren egoera `/health` endpoint-aren bidez egiaztatzen du.

### Elasticsearch

`services/elasticsearch.py` moduluak bilaketak, kontagailuak, dashboard-eko
datuak eta Streamlit-en cache-ak kudeatzen ditu.

Salbuespen nagusiak `services/exceptions.py` fitxategian daude:

- `ElasticsearchUnavailable`: zerbitzua ez dago erabilgarri.
- `ElasticsearchIndexMissing`: konfiguratutako indizea ez da existitzen.

## 9. Cache-a eta eguneratze automatikoa

`st.cache_data` erabiltzen da eskaera errepikatuak murrizteko:

- APIaren egoera: 10 segundo.
- Elasticsearch-eko kontagailuak: 15 segundo.
- Dokumentuak eta dashboard-a: 10 segundo.

Eguneratze-botoiek cache-a garbitu eta aplikazioa berriro errendatzen dute.
Alboko barratik eguneratze automatikoa aktiba daiteke edo desaktibatuta utzi.

## 10. Estiloak eta gai bisuala

Estilo globalak `ui/styles.css` fitxategian daude. Aplikazioak fitxategi hori
`<style>...</style>` etiketen barruan kargatzen du.

`ui/theme.py` moduluak gai argia, iluna eta automatikoa kudeatzen ditu.
Grafikoen estilo partekatuak `ui/charts.py` moduluan daude.

## 11. Pantaila berri bat gehitzea

1. Sortu modulua `views/` karpetan.
2. Definitu `render()` funtzioa.
3. Inportatu modulua `core/application.py` fitxategian.
4. Gehitu pantaila `PAGES` hiztegian.

Adibidea:

```python
# views/mantenimiento.py
import streamlit as st


def render() -> None:
    st.title("Mantentzea")
```

## 12. Jardunbide egokiak

- Ez egin HTTP eskaerarik zuzenean views-etatik.
- Mantendu kanpoko integrazioak `services/` karpetan.
- Ez gorde pasahitzik iturburu-kodean.
- Erabili ingurune-aldagaiak kredentzialetarako.
- Berrerabili `ui/`-ko osagaiak.
- Mantendu `render()` funtzio bat pantaila bakoitzeko.
- Garbitu cache-ak datuetan aldaketak egin ondoren.
- Exekutatu `git diff --check` commit bat egin aurretik.

## 13. Ohiko arazoak

### APIa Offline agertzen da

Egiaztatu `scoring-api` zerbitzua abian dagoela, `API_URL` zuzena dela eta
kredentzialak konfiguratuta daudela.

### Elasticsearch Offline agertzen da

Egiaztatu Elasticsearch abian dagoela, `ES_URL` zuzena dela eta Docker sarean
Streamlit edukiontzitik eskuragarri dagoela.

### Ez da daturik agertzen

Egiaztatu NiFi-ren fluxua aktibo dagoela eta datuak `cnc-predictions` indizera
bidaltzen dituela.

### Interfazea estilo gabe agertzen da

Egiaztatu `ui/styles.css` fitxategia existitzen dela eta `<style>...</style>`
barruan kargatzen dela. Ondoren berreraiki zerbitzua:

```bash
docker compose up -d --build streamlit
```

## 14. Egiaztapenak

Proiektuaren erro-karpetatik:

```bash
git diff --check
docker compose config --quiet
```

Docker abian badago:

```bash
docker compose up -d --build streamlit
docker compose ps streamlit
```
