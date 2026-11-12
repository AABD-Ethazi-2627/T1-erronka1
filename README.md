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

Zerbitzu guztiak (NiFi, Kibana, Streamlit eta Scoring API) HTTPS bidez ere eskuragarri daude **Caddy** erreverse proxy-aren bidez (ikus 3.1 atala). Gainera, `telegram-notifier`-ek alerta berriak Telegram-era bidaltzen ditu (ikus 6.1 atala).

## 1. Aurrebaldintzak

- Docker eta Docker Compose v2 (`docker compose version`)
- Simuladorearen Samba karpetarako sarbidea (`//SMB_IP/cnc-stream`) — VM-tik irakurgarri
- ~4 GB RAM libre (Elasticsearch + NiFi + Kafka + Kibana)
- 80 eta 443 atakak libre (Caddy, produkzioan)
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

# Aukerakoak
TELEGRAM_BOT_TOKEN=                    # hutsik bada, notifier-ak ez du ezer bidaltzen
TELEGRAM_CHAT_ID=
CNC_DOMAIN=cnc.localhost               # Caddy-ren oinarrizko domeinua (lehenetsia)
CADDY_TLS=internal                     # `internal` (CA lokala) edo ACME-rako posta-helbidea
```

| Aldagaia | Zertarako |
|---|---|
| `NIFI_USERNAME` / `NIFI_PASSWORD` | NiFi web UI-ra sartzeko. Pasahitzak gutxienez 12 karaktere |
| `JWT_SECRET` | Scoring API-k JWT tokenak sinatzeko |
| `API_USERNAME` / `API_PASSWORD` | NiFi-k API-n autentifikatzeko erabiltzen duen kontua |
| `SMB_IP` / `SMB_USERNAME` / `SMB_PASSWORD` | Simuladorearen Samba karpeta (`//SMB_IP/cnc-stream`) |
| `TELEGRAM_BOT_TOKEN` / `TELEGRAM_CHAT_ID` | (Aukerakoa) alertak Telegram-era bidaltzeko |
| `CNC_DOMAIN` | (Aukerakoa, produkzioa) Caddy-ren domeinua. Lehenetsia: `cnc.localhost` |
| `CADDY_TLS` | (Aukerakoa, produkzioa) `internal` = Caddy-ren CA lokala; domeinu publiko bat badago, ACME-rako posta-helbidea |

Pasahitzak eta `JWT_SECRET` derrigorrezkoak dira: falta bada, `docker compose` errorearekin gelditzen da. `.env` **ez** igo inoiz git-era; sekretuak lagun batek igo baditu, aldatu itzazu.

## 3. Zerbitzuak abiarazi

Bi konfigurazio daude:

| Fitxategia | Erabilera |
|---|---|
| `docker-compose.dev.yml` | Garapena: CSV-ak `./data/stream/`-etik (Samba gabe), kodea muntatuta + hot-reload, portu guztiak irekita |
| `docker-compose.prod.yml` | Produkzioa: Samba (CIFS), `restart: always`, log errotazioa, memoria mugak, barne-zerbitzuak `127.0.0.1`-ean, **Caddy** (HTTPS) |

```bash
export COMPOSE_FILE=docker-compose.prod.yml   # edo docker-compose.dev.yml (-f erabili ordez)
docker compose up -d --build
docker compose ps
```

Produkzioan 9 edukiontzi `Up` egon behar dira (`kafka`, `filebeat`, `nifi`, `elasticsearch`, `kibana`, `scoring-api`, `streamlit`, `telegram-notifier`, `caddy`); garapenean 8 (Caddy gabe). `kafka`, `elasticsearch`, `scoring-api` eta `streamlit` `healthy` egon behar dira. NiFi-k ~1-2 minutu behar ditu guztiz abiatzeko.

| Zerbitzua | HTTPS (Caddy, produkzioa) | Zuzenean | Erabiltzailea / Pasahitza |
|---|---|---|---|
| Streamlit | https://streamlit.cnc.localhost | http://localhost:8501 | — |
| Kibana | https://kibana.cnc.localhost | http://localhost:5601 (produkzioan: soilik makina honetatik) | — |
| NiFi | https://nifi.cnc.localhost/nifi | https://localhost:8443/nifi (produkzioan: soilik makina honetatik) | `.env`-ko `NIFI_USERNAME` / `NIFI_PASSWORD` |
| Scoring API | https://api.cnc.localhost/docs | http://localhost:8000/docs | `/docs` eta `/health` irekiak; `/predict` token bidez (ikus 3. atalaren egiaztapenak) |
| Elasticsearch | — (ez da Caddy-tik pasatzen) | http://localhost:9200 (produkzioan: soilik makina honetatik) | — |
| Kafka | — | `kafka:9092` (Docker barnetik); garapenean `localhost:29092` (host-etik) | — |

`cnc.localhost` domeinuaren azpidomeinuak (`*.cnc.localhost`) makina berean bakarrik ebazten dira. Beste ekipo batetik sartzeko, erabili `http://<IP>:8501` eta `http://<IP>:8000/docs`, edo gehitu `hosts` fitxategian: `<IP> streamlit.cnc.localhost kibana.cnc.localhost nifi.cnc.localhost api.cnc.localhost`.

### 3.1 HTTPS (Caddy)

`caddy/Caddyfile` fitxategiak Docker sareko zerbitzuak HTTPS bidez argitaratzen ditu (80 eta 443 atakak; 80 → 443 birbideratzen du). Zerbitzu bakoitzak bere azpidomeinua du: `streamlit.`, `kibana.`, `nifi.` eta `api.` + `CNC_DOMAIN` (`cnc.localhost` lehenetsia). `cnc.localhost` Streamlit-era birbideratzen da.

- **Ziurtagiria:** lehenetsian Caddy-ren CA lokala (`CADDY_TLS=internal`); nabigatzaileak abisua erakutsiko du CA fidatu arte:
  ```bash
  docker cp cnc-caddy:/data/caddy/pki/authorities/local/root.crt ./caddy-root.crt
  ```
  Inportatu `caddy-root.crt` nabigatzailean (edo sisteman) CA fidagarri gisa.
- **Domeinu publikoa:** `.env`-n `CNC_DOMAIN=zuredomeinua.eus` eta `CADDY_TLS=zu@posta.eus`; Caddy-k Let's Encrypt erabiliko du (80/443 internetetik irisgarri egon behar dira).
- **NiFi:** Caddy-k `NIFI_WEB_PROXY_HOST` (`nifi.<CNC_DOMAIN>`) erabiltzen du; `docker-compose.prod.yml`-k ezartzen du. Aldatzen bada, NiFi birsortu behar da (`docker compose up -d nifi`; flow-ak gorde baino lehen esportatu).
- **Ez dira argitaratzen:** Elasticsearch (segurtasunik gabe dago) eta Kafka.
- **HTTP lauak:** Streamlit (`8501`) eta Scoring API (`8000`) `0.0.0.0`-n daude oraindik irekita; HTTPS soilik nahi bada, aldatu `127.0.0.1:8501:8501` eta `127.0.0.1:8000:8000` produkzio-compose-ean.
- **Bolumenak:** `caddy-data` ez ezabatu (`down -v` saihestu): CA lokala hor dago eta, galduz gero, nabigatzailean berriro fidatu behar da.

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

- **Iragarpen eskuzkoa:** sentsore-balioak sartu eta Scoring API-ari (`/predict`) galdetu. Alerta-mailaz eta hutsegite-probabilitateaz gain, uneko irakurketaren tenperatura-aldea, potentzia mekanikoa eta higadura × torkea erakusten ditu. Adierazleak ez dira matxuraren kausa baieztatuak.
- **Monitorizazioa:** `cnc-predictions` indizeko azken irakurketak makinaka alderatzen ditu. AI4I datuak snapshot-ak dira: iritsiera-denborak ez du makina baten benetako bilakaera adierazten. Aurreko iragarpenek ez dute zertan adierazle berririk eduki; API eguneratuaren ondoko irakurketek izango dituzte.
- Aldagai fisikoen eta `machine_type`-ren ebaluazio konparatiboa: [scoring/EVALUACION_FEATURES.md](scoring/EVALUACION_FEATURES.md).

Kodea aldatu ondoren: `docker compose up -d --build streamlit`.

### 6.1 Telegram jakinarazpenak

`telegram-notifier` zerbitzuak 15 segundoz behin (`POLL_SECONDS`) `cnc-predictions` indizea kontsultatzen du eta alerta berriak (`KONTUZ` → ADVERTENCIA, `LARRIA` → CRÍTICA) Telegram-era bidaltzen ditu, panela itxita egon arren. Aktibatzeko `.env`-n `TELEGRAM_BOT_TOKEN` eta `TELEGRAM_CHAT_ID` bete eta `docker compose up -d telegram-notifier`. Hutsik badaude, ez du ezer bidaltzen. Bidalitako alertak `telegram_state` bolumenean gogoratzen ditu, berrabiaraztean ez errepikatzeko.

## 7. Eredua berriro entrenatu (aukerakoa)

Eredua jada `models/cnc_failure_model.pkl`-en dago. Berria sortzeko:

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r scoring/requirements-dev.txt jupyter
jupyter notebook notebooks/02_training_ML.ipynb.ipynb
```

Notebook-ak `models/cnc_failure_model.pkl` idazten du. Beste entrenamendu-esperimentuak `notebooks/lightgbm_Training.ipynb` eta `notebooks/Xgboots_Training.ipynb`-en daude. Notebook-aren dokumentazioa: `docs/ml_eredua_notebook_dokumentazioa.md`. Ondoren API-a berrabiarazi:

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
# (Caddy-ren CA lokala ere ezabatzen da: nabigatzailean berriro fidatu beharko duzu)
docker compose down -v
```

Produkzioan, `docker compose up -d` martxan dagoen NiFi birsortzen da `docker-compose.prod.yml`-ko NiFi-ren ingurune-aldagaiak aldatu badira. Flow-ak mantentzen dira (`conf` bolumen anonimoan daude), baina aurrez esportatzea gomendatzen da: Process Group-aren gainean eskuineko klik → **Download flow definition**.

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
| `cnc-telegram-notifier` | Alertak Telegram-era | `docker logs cnc-telegram-notifier --tail 100` | `ConnectionError`, Telegram-en `401`/`400` (token edo chat ID okerra) |
| `cnc-caddy` | HTTPS erreverse proxy-a (produkzioa) | `docker logs cnc-caddy --tail 100` | `address already in use` (80/443), `no such host`, ziurtagiri-erroreak |

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
| NiFi-n `InvokeHTTP`-ren `Failure, Retry` ilara hazten doa, `cnc-predictions` hutsik | Scoring API-k 503 ematen du: `curl localhost:8000/health` → `model_loaded: false`. Egiaztatu `models/cnc_failure_model.pkl` dagoela eta `docker compose restart scoring-api` |
| Nabigatzaileak ziurtagiri-abisua erakusten du HTTPS-n | Caddy-ren CA lokala ez dago fidatuta (3.1 atala) |
| `*.cnc.localhost` ez da ebazten | Ekipo desberdinetik sartzen ari zara: erabili IPa edo gehitu `hosts` sarrera (3. atala) |
| `https://nifi.cnc.localhost`-ek `421 Invalid Proxy Host` ematen du | NiFi ez da birsortu `NIFI_WEB_PROXY_HOST`-ekin: `docker compose up -d nifi` |
| `https://nifi.cnc.localhost`-ek `400 Invalid SNI` ematen du | `caddy/Caddyfile`-ko NiFi blokea aldatu da (`header_up Host localhost:8443` eta `tls_server_name localhost` mantendu) |
| Caddy ez da abiatzen: `address already in use` | 80 edo 443 atakak beste prozesu batek erabiltzen ditu (`ss -ltnp \| grep -E ':(80\|443) '`) |

## 10. Proiektuko fitxategiak

```
cnc-guard/
├── docker-compose.dev.yml    ← garapena (CSV lokalak, hot-reload, portu guztiak irekita)
├── docker-compose.prod.yml   ← produkzioa (Samba, restart: always, Caddy HTTPS)
├── .env.example              ← .env txantiloia
├── Dockerfile                ← Scoring API irudia
├── caddy/
│   └── Caddyfile             ← HTTPS erreverse proxy-a (streamlit., kibana., nifi., api.)
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
├── streamlit/                ← panela: eskuzko iragarpena + monitorizazioa
├── telegram-notifier/        ← alerta berriak Telegram-era (notifier.py + Dockerfile)
├── mcp-server/               ← MCP zerbitzaria (cnc-guard) Claude Code / Codex-rentzat
├── notebooks/
│   ├── 02_training_ML.ipynb.ipynb  ← eredua entrenatzeko notebook nagusia
│   ├── lightgbm_Training.ipynb     ← LightGBM esperimentua
│   └── Xgboots_Training.ipynb      ← XGBoost esperimentua
├── docs/                     ← zerbitzu bakoitzaren dokumentazioa (+ media/ pantaila-argazkiak)
│   ├── filebeat_dokumentazioa.md, kafka_dokumentazioa.md, nifi_dokumentazioa.md
│   ├── kibana_dokumentazioa.md, streamlit_documentazioa.md
│   └── ml_eredua_notebook_dokumentazioa.md
├── kibana/export.ndjson      ← Kibana saved objects (dashboard-ak, bistaratzeak)
├── models/                   ← cnc_failure_model.pkl
├── data/
│   └── ai4i2020_train.csv    ← entrenamendurako datuak
├── .claude/skills/           ← skills (iturria): euskera-azterketa, pdf-media
├── .agents/skills/           ← .claude/skills-en kopia (Codex)
├── scripts/sync-skills.sh    ← skills sinkronizatu
├── AGENTS.md, CLAUDE.md      ← agenteentzako testuingurua
└── .mcp.json, .codex/        ← MCP konfigurazioa
```

## 11. Dokumentazioa

> **Garrantzitsua:** zerbitzu bakoitzaren dokumentazio zehatza `docs/` karpetan dago. Proiektua ulertzeko, mantentzeko edo ebaluatzeko, irakurri dokumentu hauek:

| Dokumentua | Edukia |
|---|---|
| [`docs/filebeat_dokumentazioa.md`](docs/filebeat_dokumentazioa.md) | Filebeat: CSV fitxategiak irakurri eta Kafka-ra bidaltzea |
| [`docs/kafka_dokumentazioa.md`](docs/kafka_dokumentazioa.md) | Kafka: `cnc-sensors-raw` topikoa eta konfigurazioa |
| [`docs/nifi_dokumentazioa.md`](docs/nifi_dokumentazioa.md) | NiFi: flow-ak, Scoring API deia eta Elasticsearch-en idazketa |
| [`docs/kibana_dokumentazioa.md`](docs/kibana_dokumentazioa.md) | Kibana: dashboard-ak eta bistaratzeak (txosten teknikoa) |
| [`docs/streamlit_documentazioa.md`](docs/streamlit_documentazioa.md) | Streamlit panela: monitorizazioa, alertak eta iragarpenak |
| [`docs/ml_eredua_notebook_dokumentazioa.md`](docs/ml_eredua_notebook_dokumentazioa.md) | ML eredua: entrenamendu-notebook-aren dokumentazioa |

Pantaila-argazkiak `docs/media/` karpetan daude. Kibana-ko dashboard-ak inportatzeko: `kibana/export.ndjson` (Stack Management → Saved Objects → Import).

## 12. Erronkaren dokumentua

`ENUNTZIATUA.md` irakurri — hiru faseetan zer egin azaltzen du.


## 13. MCP eta skills (Claude Code)

CNC Guard Claude Code-rekin kontsultatu daiteke hizkuntza naturalean. Bi pieza daude: **MCP zerbitzaria** (datuak irakurtzeko tresnak) eta **skills** (Claude-k nola arrazoitu behar duen azaltzen duten jarraibideak).

### 13.1 Instalazioa (behin bakarrik)

```bash
cd mcp-server && python3 -m venv .venv && .venv/bin/pip install -r requirements.txt
.venv/bin/python -m pytest tests      # probak (19 pasa behar dira)
```

1. Stack-a martxan egon behar da (`docker compose ps`): MCP-k `localhost:8000` (API) eta `localhost:9200` (Elasticsearch) erabiltzen ditu. `API_PASSWORD` `.env`-tik irakurtzen da.
2. Ireki Claude Code proiektuaren erroan (`T1-erronka1/`) eta onartu `cnc-guard` zerbitzaria (`.mcp.json`-ek definitzen du). Ez bada agertzen, berrabiarazi Claude Code / birkargatu VS Code leihoa eta ireki txat berri bat.
3. Egiaztatu: `claude mcp list` → `cnc-guard ... ✔ Connected` (edo `/mcp` txatean, `project` taldean).

### 13.2 MCP tresnak

Ez dira eskuz deitzen: Claude-ri galdetu eta berak aukeratzen du tresna egokia. Guztiak irakurketa/kalkulu soilekoak dira, ez dute ezer aldatzen.

| Tresna | Zertarako | Galdera-adibidea |
|---|---|---|
| `model_health` | Scoring API-a eta modeloa kargatuta dauden egiaztatu | "Modeloa kargatuta dago?" |
| `list_active_alerts` | Azken minutuetako alertak (`KONTUZ`/`LARRIA`) | "Makinaren bat arriskuan dago?" |
| `get_machine_status` | Makina baten azken iragarpenak eta joera | "Zer moduz dago CNC-039?" |
| `predict_failure` | Sentsore-balio hipotetikoekin probabilitatea kalkulatu (ez du ezer gordetzen) | "Zer probabilitate izango luke M motako makina batek 2800 rpm, 60 Nm eta 220 min higadurarekin?" |

Alerta mailak: `OK` (≤ 0.15), `KONTUZ` (0.15–0.8), `LARRIA` (> 0.8).

### 13.3 Skills

`.claude/skills/`-en daude eta Claude-k automatikoki aktibatzen ditu galderak bat datorrenean (ez da komandorik idatzi behar). Behartzeko: `/euskera-azterketa` edo `/pdf-media`.

| Skill | Noiz aktibatzen da | Galdera-adibideak |
|---|---|---|
| `euskera-azterketa` | Dokumentazioaren euskara-maila neurtu edo zuzendu nahi denean | "Zer euskara-maila du README-ak?", "Berrikusi ENUNTZIATUA.md-ren gramatika" |
| `pdf-media` | PDF bat ematen denean eta bere irudiak proiektuan gorde nahi direnean | "Atera PDF honen irudiak eta sartu README-an" |

`euskera-azterketa`-k bost subagente paraleloan jartzen ditu (lexikoa, gramatika, sintaxia, ortografia eta koherentzia), emaitzak bateratzen ditu eta maila (B1/B2/C1) zehazten du, zuzenketa-proposamenekin. Ez du ezer aldatzen zuk eskatu arte.

`pdf-media`-k PDFko irudiak `docs/media/<pdf-izena>/` karpetan gordetzen ditu (`manifest.json`-ekin) eta Markdown dokumentuetan erreferentziatzen ditu bide erlatiboekin. Behar du: `poppler` (`pdfimages`, `pdftoppm`).

### 13.4 Beste agenteak (Codex, Cursor...)

Konfigurazioa ez da Claude Code-rentzat bakarrik:

| Fitxategia | Zertarako |
|---|---|
| `AGENTS.md` | Agente guztientzako testuingurua (Codex, Cursor, Copilot...); `CLAUDE.md`-k inportatzen du |
| `.agents/skills/` | `.claude/skills/`-en kopia erreala, Codex-ek proiektuan irakurtzen duena (iturria `.claude/skills/` da). Skill bat aldatu ondoren: `scripts/sync-skills.sh` |
| `.codex/config.toml` | `cnc-guard` MCP-a Codex-entzat (Codex proiektuaren erroan exekutatu) |
| `.mcp.json` | `cnc-guard` MCP-a Claude Code-rentzat |

Beste MCP bezero batek: komandoa `mcp-server/.venv/bin/python mcp-server/server.py` (stdio), `API_URL` eta `ES_URL` ingurune-aldagaiekin.

### 13.5 Segurtasun-arnesa (datu sentikorrak ez dira modelora iristen)

MCP tresnek eta agenteak irakurtzen duten guztia modeloaren testuinguruan sartzen da (eta hornitzailearen APIra joaten da). Hori mugatzeko bi geruza daude.

**1. MCP zerbitzaria (`mcp-server/guard.py`)** — tresna guztien irteera hemendik pasatzen da, ezgaitu ezin den moduan:

| Neurria | Zer egiten du |
|---|---|
| Zerrenda zuria | Eremu ezagunak soilik pasatzen dira (`machine_id`, `timestamp`, `failure_probability`, `alert_level`, `status`...), mota eta formatu zehatzekin. Gainerakoa baztertzen da, API edo Elasticsearch-ek eremu berriak gehitzen badituzte ere. |
| Akatsak | Salbuespenen testua ez da inoiz itzultzen (URLak, goiburuak edo kredentzialak izan ditzake): `http_401`, `timeout`, `service_unreachable`... kodeak soilik. `api_url` eta `es_url` ere ez dira itzultzen. |
| Ezkutatzea | Balio guztietan JWT, `Bearer`, Telegram tokenak, `pasahitza=...`, `user:pass@host`, posta-helbideak, IPak, token luzeak eta `.env`-ko sekretuen balio literalak `[REDACTED]` bihurtzen dira. |
| Sarrera-balidazioa | `machine_id` (`[A-Za-z0-9_-]{1,32}`) eta zenbakiak egiaztatzen dira eskaerarik egin aurretik. |
| Fail closed | Irteerak eskema betetzen ez badu, `blocked_by_guard` itzultzen da, ezer filtratu gabe. |

Stderr-era kontagailuak soilik idazten dira (`guard[...]: ezkutatuak=N baztertuak=M`), inoiz edukirik ez.

**2. Claude Code (`.claude/settings.json` + `.claude/hooks/block_secrets.py`)** — agenteak ezin ditu sekretuak beste bideetatik irakurri. Blokeatzen dira: `.env*` fitxategiak (`.env.example` izan ezik), gako eta ziurtagiri pribatuak, `~/.ssh`, `cat .env`, `printenv`, `docker inspect`, `docker compose config`, `docker exec ... env` eta antzekoak.

Mugak (garrantzitsua):

- Sentsore-datuak eta alertak (makina, probabilitatea, maila) modelora **iristen dira**: MCP-ren helburua horixe da. Hori ere saihestu nahi bada, ez erabili MCP zerbitzaria.
- Hook-a ahalegin onenekoa da, ez bermea: ez ditu leku guztiak estaltzen (adib. sekretuak beste fitxategi batean idatzita badaude). Ez gorde sekretuak agenteak ikus ditzakeen fitxategietan.
- Codex-ek MCP geruza bera erabiltzen du (zerbitzari bera), baina `.claude/settings.json` ez da Codex-entzat: konfiguratu bere sandbox- eta onarpen-politika.
- Elkarrizketan dagoeneko agertu den informazioa ezin da atzera bota.

### 13.6 Arazoak

| Sintoma | Konponbidea |
|---|---|
| `cnc-guard` ez da `/mcp`-n agertzen | Birkargatu leihoa eta ireki txat berri bat (zerbitzariak txata hasten denean kargatzen dira) |
| `Pending approval` | Onartu `/mcp`-tik edo gehitu `.claude/settings.local.json`-en `{"enabledMcpjsonServers": ["cnc-guard"]}` |
| Tresnek errorea ematen dute | Egiaztatu `docker compose ps`, `curl localhost:8000/health` eta `API_PASSWORD` `.env`-n |
| `found: false` makina batean | ID formatua `CNC-039` izan behar da; baliozkoa bada, pipeline-a geldituta egon daiteke |
