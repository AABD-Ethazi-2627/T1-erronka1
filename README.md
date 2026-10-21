# CNC Guard — Hasteko Argibideak

## 1. NFS karpeta muntatu (behin bakarrik)

```bash
sudo mkdir -p /mnt/cnc-stream
sudo mount ZERBITZARI_IP:/opt/cnc-stream /mnt/cnc-stream
ls /mnt/cnc-stream/   # CSV fitxategiak ikusi behar dituzu

docker exec cnc-filebeat ls /mnt/cnc-stream
```
Actualizar contenedores
```bash
docker compose up -d --build scoring-api

Para el nuevo flujo de NiFi
```
docker compose down
docker volume ls | grep t1-erronka1                    # mirar los nombres exactos
docker volume rm t1-erronka1_cnc-stream-cifs t1-erronka1_filebeat-data

docker compose up -d --build
docker compose ps        # 6 contenedores "Up"; kafka, elasticsearch y scoring en "healthy"

docker compose ps scoring-api
curl -s localhost:8000/health

docker exec cnc-nifi curl -s -X POST http://scoring-api:8000/auth/token \
  -d grant_type=password -d username=nifi -d password='NexoCNC2026ApiPass!'

docker logs cnc-nifi 2>&1 | grep -A6 "failed to properly initialize" | grep -iE "caused by|exception" | tail -5

```

## 2. Zerbitzuak abiarazi

```bash
docker compose up -d --build
docker compose ps     # 6 zerbitzu "running" ikusi behar dituzu
```

| Zerbitzua | URLa | Erabiltzailea / Pasahitza |
|---|---|---|
| Kafka | kafka:9092 (Docker barnetik) | — |
| NiFi | https://localhost:8443 | admin / adminpassword123 |
| Kibana | http://localhost:5601 | — |
| Elasticsearch | http://localhost:9200 | — |
| Scoring API | http://localhost:8000/docs | — |

## 3. Proiektuko fitxategiak

```
cnc-guard/
├── filebeat/
│   └── filebeat.yml          ← 1. fasea: ZURE ZEREGINA (osatu — Kafka outputera bideratu)
├── scoring/
│   ├── app/                  ← 3. fasea: FastAPI (uvicorn app.main:app)
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
│   └── tests/                ← pytest (cd scoring && pytest)
├── nifi-flows/
│   ├── cnc_fase1_INCOMPLETO.json  ← 1. fasea: NiFi-n inportatu eta osatu (ConsumeKafka jada konfiguratuta)
│   └── fase3_streaming.json  ← 3. fasea (NiFi 2.x): ConsumeKafka → ConvertRecord → InvokeHTTP (scoring-api) → PutElasticsearchJson
│   └── CNC_Guard_ _3._Fasea_(Zuzenean_Kibana).json  ← 3. fasea, API gabe: ConsumeKafka → ConvertRecord → PutElasticsearchJson (cnc-sensors indizea)
├── notebooks/
│   └── 02_training_TEMPLATE.ipynb ← 2. fasea: ZURE ZEREGINA (osatu)
├── models/                   ← 2. fasea: hemen gorde model.pkl
└── data/
    └── ai4i2020_train.csv    ← entrenamendurako datuak
```

## 4. Erronkaren dokumentua

`ENUNTZIATUA.md` irakurri — hiru faseetan zer egin azaltzen du.
