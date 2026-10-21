# CNC Guard — Proiektua hutsetik abiarazteko gida

CNC makinen sentsore-datuak (CSV) → Filebeat → Kafka → NiFi → (Scoring API) → Elasticsearch → Kibana.

```
Simuladorea (Samba)
      │ CSV
   Filebeat ──► Kafka (cnc-sensors-raw) ──► NiFi ─┬─► Elasticsearch  cnc-sensors      (zuzenean)
                                                  └─► Scoring API ─► Elasticsearch  cnc-predictions
                                                                          │
                                                                        Kibana
```

## 1. Aurrebaldintzak

- Docker eta Docker Compose v2 (`docker compose version`)
- Simuladorearen Samba karpetarako sarbidea (`//SMB_IP/cnc-stream`) — VM-tik irakurgarri
- ~4 GB RAM libre (Elasticsearch + NiFi + Kafka + Kibana)
- `models/cnc_failure_model.pkl` fitxategia (repoan dago; berria sortzeko ikus 6. atala)

## 2. Konfigurazioa (`.env`)

Sekretuak ez daude `docker-compose.yml`-n, `.env` fitxategian baizik (`.gitignore`-n dago, ez da git-era igotzen).

1. Txantiloia kopiatu:

```bash
cp .env.example .env
```

2. `JWT_SECRET` sortu eta `.env`-n sartu automatikoki:

```bash
sed -i "s/^JWT_SECRET=.*/JWT_SECRET=$(openssl rand -hex 32)/" .env
```

3. Gainerako pasahitzak bete (editorearekin: `nano .env`). Adibidea (aldatu pasahitzak!):

```dotenv
NIFI_USERNAME=admin
NIFI_PASSWORD=PasahitzaLuzea2026!      # >= 12 karaktere

JWT_SECRET=<openssl-ek sortutako 64 karaktere>
API_USERNAME=nifi
API_PASSWORD=BestePasahitza2026!       # NiFi-ren OAuth2 zerbitzuan ere sartuko duzu (4. atala)

SMB_IP=192.168.75.150                  # simuladorearen zerbitzariaren IPa
SMB_USERNAME=cncuser
SMB_PASSWORD=<Samba pasahitza>
```

| Aldagaia | Zertarako |
|---|---|
| `NIFI_USERNAME` / `NIFI_PASSWORD` | NiFi web UI-ra sartzeko. Pasahitzak gutxienez 12 karaktere |
| `JWT_SECRET` | Scoring API-k JWT tokenak sinatzeko |
| `API_USERNAME` / `API_PASSWORD` | NiFi-k API-n autentifikatzeko erabiltzen duen kontua |
| `SMB_IP` / `SMB_USERNAME` / `SMB_PASSWORD` | Simuladorearen Samba karpeta (`//SMB_IP/cnc-stream`) |

Pasahitzak eta `JWT_SECRET` derrigorrezkoak dira: falta bada, `docker compose` errorearekin gelditzen da.

## 3. Zerbitzuak abiarazi

```bash
docker compose up -d --build
docker compose ps
```

6 edukiontzi `Up` egon behar dira; `kafka`, `elasticsearch` eta `scoring-api` `healthy`. NiFi-k ~1-2 minutu behar ditu guztiz abiatzeko.

| Zerbitzua | URLa | Erabiltzailea / Pasahitza |
|---|---|---|
| NiFi | https://localhost:8443 | `.env`-ko `NIFI_USERNAME` / `NIFI_PASSWORD` |
| Kibana | http://localhost:5601 | — |
| Elasticsearch | http://localhost:9200 | — |
| Scoring API | http://localhost:8000/docs | token bidez (ikus 4. atala) |
| Kafka | `kafka:9092` (Docker barnetik), `localhost:29092` (host-etik) | — |

### Egiaztapenak

```bash
curl -s localhost:8000/health                      # API bizirik dago eta eredua kargatuta

# CSV-ak Filebeat-en ikusten dira?
docker exec cnc-filebeat ls /mnt/cnc-stream

# Tokena eskatu (NiFi barnetik, .env-ko API_USERNAME / API_PASSWORD erabiliz)
docker exec cnc-nifi curl -s -X POST http://scoring-api:8000/auth/token \
  -d grant_type=password -d username=<API_USERNAME> -d password='<API_PASSWORD>'
```

## 4. NiFi flow-ak inportatu

Bi flow daude `nifi-flows/` karpetan. Biak elkarrekin exekuta daitezke (Kafka kontsumitzaile-talde desberdinak dituzte).

| Fitxategia | Bidea | Elasticsearch indizea |
|---|---|---|
| `CNC_Guard_Streaming.json` | Kafka → ConvertRecord → **Scoring API** → Elasticsearch | `cnc-predictions` |
| `CNC_Guard_Zuzenean.json` | Kafka → ConvertRecord → Elasticsearch (APIrik gabe) | `cnc-sensors` |

NiFi UI-n (https://localhost:8443), flow bakoitzeko:

1. Canvas-ean, goiko barrako **Process Group** ikonoa kanpora arrastatu → **Import from file** (ikonoa) → aukeratu JSON fitxategia.
2. Process Group-aren gainean eskuineko klik → **Controller Services** (edo Configure → Controller Services): zerbitzu guztiak **Enable** (Kafka, JsonWriter, CSVReader, Elasticsearch).
3. **Soilik `Streaming` flow-an:** `Scoring API — OAuth2 tokenak` zerbitzuan, pasahitza sartu eskuz. NiFi-k ez ditu pasahitzak JSON-ean esportatzen.
   - Token URL: `http://scoring-api:8000/auth/token`
   - Username / Password: `.env`-ko `API_USERNAME` / `API_PASSWORD`
4. Process Group-ean eskuineko klik → **Start**.

Flow-a martxan dagoenean, Filebeat-ek irakurtzen dituen CSV-ak Kafka-ra, NiFi-ra eta Elasticsearch-era iristen dira.

```bash
curl -s 'localhost:9200/_cat/indices/cnc-*?v'      # docs.count igotzen ari da?
```

## 5. Kibana: datuak ikusi

1. **Stack Management → Data Views → Create data view**, bi aldiz:
   - `cnc-predictions` (denbora-eremua: `timestamp`)
   - `cnc-sensors` (denbora-eremua: `timestamp`)
2. **Discover** → aukeratu data view-a. Denbora-tartea nahikoa zabal jarri (adib. *Last 7 days*), bestela ez da ezer agertuko.
3. Iragarpenak iragazteko (`cnc-predictions`):
   - Ondo dauden makinak: `alert_level : "OK"`
   - Alertak: `not alert_level : "OK"` (`KONTUZ`, `LARRIA`)
4. **Dashboard → Create → Visualization** bidez grafikoak:
   - Tarta: `alert_level.keyword` banaketa, metrika `Count`
   - Lerroak: X ardatza `timestamp`, Y ardatza `failure_probability` batez bestekoa, banaketa `machine_id.keyword`
   - Taula: `machine_id.keyword`, `alert_level.keyword`, `failure_probability`

## 6. Eredua berriro entrenatu (aukerakoa)

Eredua jada `models/cnc_failure_model.pkl`-en dago. Berria sortzeko:

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r scoring/requirements-dev.txt jupyter
jupyter notebook notebooks/02_training_ML.ipynb
```

Notebook-ak `models/cnc_failure_model.pkl` idazten du. Ondoren API-a berrabiarazi:

```bash
docker compose restart scoring-api
```

Probak: `cd scoring && pytest`

## 7. Eguneratzeak eta berrabiarazteak

```bash
# Kodea edo requirements aldatu da (scoring)
docker compose up -d --build scoring-api

# .env aldatu da → zerbitzua birsortu
docker compose up -d scoring-api

# Dena gelditu (datuak gordetzen dira bolumenetan)
docker compose down

# Hutsetik hasi: Kafka, NiFi, Elasticsearch eta Filebeat-en egoera ezabatu
docker compose down -v
```

`JWT_SECRET` aldatzen bada, lehendik emandako tokenak baliogabetzen dira; NiFi-k berriak eskatuko ditu.

Soilik CSV-ak berriro irakurrarazteko (Filebeat-ek jada irakurritakoak berriro bidaltzeko):

```bash
docker compose down
docker volume rm t1-erronka1_filebeat-data
docker compose up -d
```

## 8. Arazoak konpontzen

| Sintomak | Zer begiratu |
|---|---|
| `docker compose` errorea: `... falta da .env-n` | `.env` fitxategia sortu duzu? (2. atala) |
| `cnc-scoring` etengabe berrabiarazten | `docker logs cnc-scoring --tail 30` |
| NiFi ez da abiatzen | `docker logs cnc-nifi 2>&1 \| grep -A6 "failed to properly initialize" \| grep -iE "caused by\|exception"` |
| Filebeat-ek ez ditu CSV-ak ikusten | Samba datuak (`SMB_*`) eta sarbidea; `docker exec cnc-filebeat ls /mnt/cnc-stream` |
| Samba bolumena gaizki muntatuta | `docker compose down && docker volume rm t1-erronka1_cnc-stream-cifs`, gero `docker compose up -d` |
| Kibana-n ez da daturik agertzen | Denbora-tartea, data view-aren denbora-eremua, eta `_cat/indices`-en `docs.count` |
| API-k 401 itzultzen du NiFi-tik | OAuth2 zerbitzuan pasahitza sartu da eta zerbitzua enabled dago? |

## 9. Proiektuko fitxategiak

```
cnc-guard/
├── docker-compose.yml        ← zerbitzu guztiak (sekretuak .env-etik)
├── .env.example              ← .env txantiloia
├── Dockerfile                ← Scoring API irudia
├── filebeat/
│   └── filebeat.yml          ← CSV (Samba) → Kafka
├── scoring/
│   ├── app/                  ← FastAPI (uvicorn app.main:app)
│   │   ├── main.py           ←   app + lifespan (eredua abieran kargatu)
│   │   ├── config.py         ←   ingurune-aldagaiak
│   │   ├── core/security.py  ←   JWT tokenak (access + refresh)
│   │   ├── schemas/          ←   Pydantic eskemak (sarrera-balidazioa)
│   │   ├── services/model.py ←   eredua kargatu, iragarri, alerta-maila
│   │   └── api/              ←   endpointak: /auth/token, /health, /predict
│   ├── cnc_ml/               ← notebook-ak ETA API-k partekatzen dute
│   │   ├── columns.py        ←   zutabeak eta leakage zutabeak
│   │   ├── features.py       ←   feature engineering
│   │   └── pipeline.py       ←   sklearn Pipeline (features + kodeketa + eredua)
│   └── tests/                ← pytest
├── nifi-flows/
│   ├── CNC_Guard_Streaming.json  ← Kafka → ConvertRecord → InvokeHTTP (scoring-api) → PutElasticsearchJson (cnc-predictions)
│   └── CNC_Guard_Zuzenean.json   ← Kafka → ConvertRecord → PutElasticsearchJson (cnc-sensors)
├── notebooks/
│   └── 02_training_ML.ipynb  ← eredua entrenatzeko notebook-a
├── models/                   ← cnc_failure_model.pkl
└── data/
    └── ai4i2020_train.csv    ← entrenamendurako datuak
```

## 10. Erronkaren dokumentua

`ENUNTZIATUA.md` irakurri — hiru faseetan zer egin azaltzen du.
