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
- `models/cnc_failure_model.pkl` fitxategia (repoan dago; berria sortzeko ikus 7. atala)

## 2. Konfigurazioa (`.env`)

Sekretuak ez daude `docker-compose.*.yml`-n, `.env` fitxategian baizik (`.gitignore`-n dago, ez da git-era igotzen).

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

Bi konfigurazio daude:

| Fitxategia | Erabilera |
|---|---|
| `docker-compose.dev.yml` | Garapena: CSV-ak `./data/stream/`-etik (Samba gabe), kodea muntatuta + hot-reload, portu guztiak irekita |
| `docker-compose.prod.yml` | Produkzioa: Samba (CIFS), `restart: always`, log errotazioa, memoria mugak, barne-zerbitzuak `127.0.0.1`-ean |

```bash
export COMPOSE_FILE=docker-compose.prod.yml   # edo docker-compose.dev.yml (-f erabili ordez)
docker compose up -d --build
docker compose ps
```

7 edukiontzi `Up` egon behar dira; `kafka`, `elasticsearch`, `scoring-api` eta `streamlit` `healthy`. NiFi-k ~1-2 minutu behar ditu guztiz abiatzeko.

| Zerbitzua | URLa | Erabiltzailea / Pasahitza |
|---|---|---|
| NiFi | https://localhost:8443 | `.env`-ko `NIFI_USERNAME` / `NIFI_PASSWORD` |
| Kibana | http://localhost:5601 | — |
| Elasticsearch | http://localhost:9200 | — |
| Scoring API | http://localhost:8000/docs | token bidez (ikus 4. atala) |
| Streamlit | http://localhost:8501 | — |
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

## 6. Streamlit panela

http://localhost:8501 — `.env`-ko `API_USERNAME` / `API_PASSWORD` erabiltzen ditu APIan autentifikatzeko (ez du ezer gehiago konfiguratu behar).

- **Iragarpen eskuzkoa:** sentsore-balioak sartu eta Scoring API-ari (`/predict`) galdetu. Alerta maila (`OK` / `KONTUZ` / `LARRIA`) eta hutsegite-probabilitatea erakusten ditu.
- **Monitorizazioa:** `cnc-predictions` indizeko datuak (NiFi-ren *Streaming* flow-ak idazten ditu): alerta mailen kopuruak, probabilitatea denboran, arriskuko makinak eta azken iragarpenak.
  Indizea oraindik ez badago, mezu bat agertzen da; flow-a abiarazi eta datuak iristean agertuko dira.
  Datuak hutsik agertzen badira, albo-barrako denbora-tartea `Guztia` jarri (timestamp-a simuladoreak jartzen du).

Kodea aldatu ondoren: `docker compose up -d --build streamlit`.

## 7. Eredua berriro entrenatu (aukerakoa)

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

## 8. Eguneratzeak eta berrabiarazteak

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

## 9. Arazoak konpontzen

### Lehenengo urratsa: logak irakurri

Zerbait huts egiten badu, **lehenik logak irakurri** eta errore-mezua bilatu. Gehienetan mezuak berak esaten du zer dagoen gaizki.

```bash
# Zein zerbitzu dabiltza? (Restarting / Exited / unhealthy = arazoa)
docker compose ps

# Zerbitzu baten azken logak
docker logs cnc-<izena> --tail 100

# Denbora errealean jarraitu (Ctrl+C irteteko)
docker logs cnc-<izena> -f

# Errore-lerroak soilik iragazi
docker logs cnc-<izena> 2>&1 | grep -iE "error|exception|failed|caused by"

# Zerbitzu guztien logak batera
docker compose logs --tail 50
```

| Edukiontzia | Zer egiten du | Log-komandoa | Zer bilatu |
|---|---|---|---|
| `cnc-kafka` | Mezularitza | `docker logs cnc-kafka --tail 100` | `ERROR`, `Exception`, kontrolatzailea ez abiatzea |
| `cnc-filebeat` | CSV → Kafka | `docker logs cnc-filebeat --tail 100` | `ERROR`, `Failed to connect`, `no such file`; `docker exec cnc-filebeat ls /mnt/cnc-stream` |
| `cnc-nifi` | Fluxuak | `docker logs cnc-nifi --tail 100` | `failed to properly initialize`, `Caused by` (NiFi astiro abiatzen da: itxaron 1-2 min) |
| `cnc-elasticsearch` | Biltegiratzea | `docker logs cnc-elasticsearch --tail 100` | `UnknownHostException`, `OutOfMemory`, `max virtual memory`, `disk watermark` |
| `cnc-kibana` | Bistaratzea | `docker logs cnc-kibana --tail 100` | `Unable to connect to Elasticsearch`, `500` |
| `cnc-scoring` | ML API | `docker logs cnc-scoring --tail 100` | `Traceback`, modeloa ez da aurkitu (`./models/cnc_failure_model.pkl`), `JWT_SECRET` |
| `cnc-streamlit` | Panela | `docker logs cnc-streamlit --tail 100` | `Traceback`, `ConnectionError` (scoring-api edo Elasticsearch erortuta) |

### Errore ohikoenak

- **`500 Internal Server Error`**: erantzuna ematen duen zerbitzuak huts egin du, ez bezeroak. Begiratu zein URLri dagokion eta zerbitzu horren logak (adib. `:5601` → `cnc-kibana`, `:9200` → `cnc-elasticsearch`, `:8000` → `cnc-scoring`). Filebeat-ek ez du Elasticsearch-ekin hitz egiten (Kafka-ra bidaltzen du), beraz 500 bat ez da Filebeat-etik datorrena.
- **`401 Unauthorized`**: tokena iraungita edo `.env`-ko `API_USERNAME` / `API_PASSWORD` gaizki daude.
- **Zerbitzua `Restarting` dago**: `docker logs` begiratu; edukiontzia berrabiarazten ari da abioan huts egiten duelako.
- **`unhealthy`**: `docker inspect cnc-<izena> --format '{{json .State.Health}}'` komandoak azken healthcheck-aren irteera erakusten du.
- **Diskoa beteta**: `df -h` eta `docker system df`. Elasticsearch-ek idazketak blokeatzen ditu diskoa beteta dagoenean.
- **Konfigurazioa aldatu ondoren ez dabil**: `docker compose up -d <zerbitzua>` (birsortu), ez soilik `restart`.

Irakasleari galdetu aurretik: (1) `docker compose ps`, (2) hutsegiten duen zerbitzuaren logak, (3) errore-lerroa bilatu eta bilatzailean/dokumentazioan begiratu. Galdetzen baduzu, erantsi errore-lerro **zehatza**.

### Sintoma azkarren taula

| Sintomak | Zer begiratu |
|---|---|
| `docker compose` errorea: `... falta da .env-n` | `.env` fitxategia sortu duzu? (2. atala) |
| `cnc-scoring` etengabe berrabiarazten | `docker logs cnc-scoring --tail 30` |
| NiFi ez da abiatzen | `docker logs cnc-nifi 2>&1 \| grep -A6 "failed to properly initialize" \| grep -iE "caused by\|exception"` |
| Filebeat-ek ez ditu CSV-ak ikusten | Samba datuak (`SMB_*`) eta sarbidea; `docker exec cnc-filebeat ls /mnt/cnc-stream` |
| Samba bolumena gaizki muntatuta | `docker compose down && docker volume rm t1-erronka1_cnc-stream-cifs`, gero `docker compose up -d` |
| Kibana-n ez da daturik agertzen | Denbora-tartea, data view-aren denbora-eremua, eta `_cat/indices`-en `docs.count` |
| API-k 401 itzultzen du NiFi-tik | OAuth2 zerbitzuan pasahitza sartu da eta zerbitzua enabled dago? |

## 10. Proiektuko fitxategiak

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
├── streamlit/
│   ├── app.py                ← panela: eskuzko iragarpena (/predict) + monitorizazioa (Elasticsearch)
│   ├── requirements.txt
│   └── Dockerfile
├── notebooks/
│   └── 02_training_ML.ipynb  ← eredua entrenatzeko notebook-a
├── models/                   ← cnc_failure_model.pkl
└── data/
    └── ai4i2020_train.csv    ← entrenamendurako datuak
```

## 11. Erronkaren dokumentua

`ENUNTZIATUA.md` irakurri — hiru faseetan zer egin azaltzen du.


## 12. MCP eta skills (Claude Code)

CNC Guard Claude Code-rekin kontsultatu daiteke hizkuntza naturalean. Bi pieza daude: **MCP zerbitzaria** (datuak irakurtzeko tresnak) eta **skills** (Claude-k nola arrazoitu behar duen azaltzen duten jarraibideak).

### 12.1 Instalazioa (behin bakarrik)

```bash
cd mcp-server && python3 -m venv .venv && .venv/bin/pip install -r requirements.txt
.venv/bin/python -m pytest tests      # probak (6 pasa behar dira)
```

1. Stack-a martxan egon behar da (`docker compose ps`): MCP-k `localhost:8000` (API) eta `localhost:9200` (Elasticsearch) erabiltzen ditu. `API_PASSWORD` `.env`-tik irakurtzen da.
2. Ireki Claude Code proiektuaren erroan (`T1-erronka1/`) eta onartu `cnc-guard` zerbitzaria (`.mcp.json`-ek definitzen du). Ez bada agertzen, berrabiarazi Claude Code / birkargatu VS Code leihoa eta ireki txat berri bat.
3. Egiaztatu: `claude mcp list` → `cnc-guard ... ✔ Connected` (edo `/mcp` txatean, `project` taldean).

### 12.2 MCP tresnak

Ez dira eskuz deitzen: Claude-ri galdetu eta berak aukeratzen du tresna egokia. Guztiak irakurketa/kalkulu soilekoak dira, ez dute ezer aldatzen.

| Tresna | Zertarako | Galdera-adibidea |
|---|---|---|
| `model_health` | Scoring API-a eta modeloa kargatuta dauden egiaztatu | "Modeloa kargatuta dago?" |
| `list_active_alerts` | Azken minutuetako alertak (`KONTUZ`/`LARRIA`) | "Makinaren bat arriskuan dago?" |
| `get_machine_status` | Makina baten azken iragarpenak eta joera | "Zer moduz dago CNC-039?" |
| `predict_failure` | Sentsore-balio hipotetikoekin probabilitatea kalkulatu (ez du ezer gordetzen) | "Zer probabilitate izango luke M motako makina batek 2800 rpm, 60 Nm eta 220 min higadurarekin?" |

Alerta mailak: `OK` (≤ 0.5), `KONTUZ` (0.5–0.8), `LARRIA` (> 0.8).

### 12.3 Skills

`.claude/skills/`-en daude eta Claude-k automatikoki aktibatzen ditu galderak bat datorrenean (ez da komandorik idatzi behar). Behartzeko: `/diagnose-machine`, `/retrain-model` edo `/stack-troubleshooting`.

| Skill | Noiz aktibatzen da | Galdera-adibideak |
|---|---|---|
| `diagnose-machine` | Makina baten egoera, arriskua edo alertak | "Makinaren bat arriskuan dago?", "Diagnostikatu CNC-039", "Zergatik dago CNC-012 alertan?" |
| `stack-troubleshooting` | Datuak ez dira iristen edo edukiontzi bat huts egiten du | "Ez dira datuak iristen", "Dashboard-a hutsik dago", "Ez dago alertarik" |
| `retrain-model` | Modeloa berrentrenatu, hobetu edo ordezkatu | "Berrentrenatu modeloa", "Iragarpenak arraroak dira" |

`diagnose-machine`-ek honela jokatzen du: `model_health` → alertak/egoera kontsultatu → **joera** aztertu (ez soilik azken balioa) → kausa probableak (TWF, HDF, PWF, OSF, RNF, **hipotesi gisa**) → gomendatutako ekintza. Modeloa `down` badago, `stack-troubleshooting`-era pasatzen da.

### 12.4 Beste agenteak (Codex, Cursor...)

Konfigurazioa ez da Claude Code-rentzat bakarrik:

| Fitxategia | Zertarako |
|---|---|
| `AGENTS.md` | Agente guztientzako testuingurua (Codex, Cursor, Copilot...); `CLAUDE.md`-k inportatzen du |
| `.agents/skills/` | `.claude/skills/`-en esteka sinbolikoa: skill berak, kopiarik gabe |
| `.codex/config.toml` | `cnc-guard` MCP-a Codex-entzat (Codex proiektuaren erroan exekutatu) |
| `.mcp.json` | `cnc-guard` MCP-a Claude Code-rentzat |

Beste MCP bezero batek: komandoa `mcp-server/.venv/bin/python mcp-server/server.py` (stdio), `API_URL` eta `ES_URL` ingurune-aldagaiekin.

### 12.5 Arazoak

| Sintoma | Konponbidea |
|---|---|
| `cnc-guard` ez da `/mcp`-n agertzen | Birkargatu leihoa eta ireki txat berri bat (zerbitzariak txata hasten denean kargatzen dira) |
| `Pending approval` | Onartu `/mcp`-tik edo gehitu `.claude/settings.local.json`-en `{"enabledMcpjsonServers": ["cnc-guard"]}` |
| Tresnek errorea ematen dute | Egiaztatu `docker compose ps`, `curl localhost:8000/health` eta `API_PASSWORD` `.env`-n |
| `found: false` makina batean | ID formatua `CNC-039` izan behar da; baliozkoa bada, pipeline-a geldituta egon daiteke |
