# CNC Guard — Segurtasuna eta araudiaren betetzea

Dokumentu honek CNC Guard-en segurtasun-neurriak (sekretuak, autentifikazioa, MCP arnesa) eta Europako araudiarekiko betetzea biltzen ditu: **AI Act** (2024/1689 Erregelamendua) eta **DBEO / RGPD** (2016/679 Erregelamendua).

> Aldez aurretiko oharra: hau proiektuaren auto-ebaluazio teknikoa da, ez aholku juridikoa. Produkzioan jarri aurretik, erakundeko datuen babeserako ordezkariak (DPO) edo aholkulari juridikoak berretsi beharko luke.

## 1. Sekretuen kudeaketa (`.env`)

Sekretuak ez daude kodean ez eta `docker-compose.*.yml`-n: `.env` fitxategian daude (`.gitignore`-n dago, ez da git-era igotzen). Txantiloia `.env.example` da, balio errealik gabe.

| Aldagaia | Zertarako |
|---|---|
| `JWT_SECRET` | Scoring API-k JWT tokenak sinatzeko (`openssl rand -hex 32`-rekin sortua) |
| `API_USERNAME` / `API_PASSWORD` | NiFi-k (eta MCP zerbitzariak) API-n autentifikatzeko erabiltzen duen kontua |
| `NIFI_USERNAME` / `NIFI_PASSWORD` | NiFi web UI-ra sartzeko (gutxienez 12 karaktere) |
| `SMB_IP` / `SMB_USERNAME` / `SMB_PASSWORD` | Simuladorearen Samba karpeta |
| `TELEGRAM_BOT_TOKEN` / `TELEGRAM_CHAT_ID` | (Aukerakoa) alertak Telegram-era bidaltzeko |

Pasahitzak eta `JWT_SECRET` derrigorrezkoak dira: falta badira, `docker compose` errorearekin gelditzen da.

## 2. NiFi → Scoring API autentifikazioa (API tokena)

`/predict` endpoint-a babestuta dago; NiFi-k tokena lortu behar du aurrena:

1. NiFi-ko `Scoring API — OAuth2 tokenak` controller service-ak (`StandardOauth2AccessTokenProvider`) `POST http://scoring-api:8000/auth/token` deitzen du, `Grant Type = password` eta `.env`-ko `API_USERNAME` / `API_PASSWORD` erabilita.
2. Scoring API-k kredentzialak egiaztatzen ditu eta `JWT_SECRET`-ekin sinatutako JWT bat itzultzen du.
3. `InvokeHTTP — scoring-api /predict` prozesadoreak token hori bidaltzen du (`Authorization: Bearer ...`) eta iragarpena jasotzen du.
4. Emaitza Elasticsearch-eko `cnc-predictions` indizean gordetzen da.

NiFi-k ez ditu pasahitzak flow-en JSON-ean esportatzen; horregatik, `nifi-flows/CNC_Guard_Streaming.json` inportatu ondoren, `API_PASSWORD` eskuz sartu behar da controller service-an. Xehetasunak: [`nifi_dokumentazioa.md`](nifi_dokumentazioa.md).

## 3. MCP zerbitzaria eta segurtasun-arnesa

Eredua Claude Code-tik kontsultatzeko `cnc-guard` MCP zerbitzaria (irakurketa-soilik) dago: `model_health`, `list_active_alerts`, `get_machine_status` eta `predict_failure`. Datu sentikorrak modelora ez iristeko, bi geruzako arnesa jarri dugu:

1. **`mcp-server/guard.py`** — tresna guztien irteera hemendik pasatzen da:
   - Eremu ezagunen zerrenda zuria (gainerakoa baztertzen da).
   - Akatsetan kodeak soilik itzultzen dira (`http_401`, `timeout`...), inoiz salbuespenen testua, URLak edo kredentzialak ez.
   - Ezkutatzea (`[REDACTED]`): JWT, `Bearer`, Telegram tokenak, pasahitzak, posta-helbideak, IPak eta sekretuen balio literalak.
   - `machine_id` eta zenbakien sarrera-balidazioa.
   - *Fail closed*: irteerak eskema betetzen ez badu, `blocked_by_guard` itzultzen da.
2. **Claude Code hook-a (`.claude/settings.json` + `.claude/hooks/block_secrets.py`)** — agenteak ezin ditu sekretuak beste bideetatik irakurri: `.env*` fitxategiak (`.env.example` izan ezik), gako pribatuak, `printenv`, `docker inspect`, `docker compose config`, etab. blokeatzen dira.

Mugak:

- Sentsore-datuak eta alertak modelora **iristen dira** (MCP-ren helburua horixe da).
- Hook-a ahalegin onenekoa da, ez bermea.
- Elkarrizketan dagoeneko agertu den informazioa ezin da atzera bota.

Dokumentazio osoa: `README.md`, 13.5 atala.

## 4. AI Act (2024/1689 Erregelamendua) betetzea

### 4.1 Sailkapena

CNC Guard-ek Random Forest eredu bat erabiltzen du CNC makinen hutsegiteak iragartzeko (mantentze prediktiboa). AI Act-eko definizioaren arabera, **AA sistema** da (2. artikulua), eta bere erabilera:

| Galdera | Ebaluazioa |
|---|---|
| Debekatutako praktika al da (5. artikulua)? | **Ez.** Ez du manipulaziorik, puntuazio sozialik, biometriarik edo pertsonen emozioen inferentziarik egiten. |
| Arrisku handiko sistema al da (6. artikulua, III. eranskina)? | **Ez dirudi.** III. eranskinak aipatzen dituen eremuetan (biometria, hezkuntza, enplegua, funtsezko zerbitzuak, legea betearaztea...) ez dago sartuta. Makinen mantentze-lanerako tresna da, ez pertsonen inguruko erabakietarako. |
| Segurtasun-osagai al da (I. eranskina, makinen araudia)? | **Ez.** Ez du makina kontrolatzen ezta gelditzen ere: alerta bat jaulkitzen du, eta mantentze-teknikariak erabakitzen du. Makinaren segurtasun-funtziorik ez du betetzen. |
| Gardentasun-betebeharrak (50. artikulua)? | **Ez dagozkio.** Ez da txat-bot-a, ez ditu eduki sintetikoak sortzen eta ez du pertsonen emozioak detektatzen. |

Ondorioz, **arrisku minimoko** sistema gisa sailkatzen dugu: ez du konformitate-ebaluaziorik, CE markarik edo EBko datu-baseko erregistrorik behar.

> Sailkapena aldatuko litzateke sistema segurtasun-funtzio batera lotuko balitz (adib. makina automatikoki gelditzea alertaren arabera) edo langileen errendimendua ebaluatzeko erabiliko balitz (III. eranskineko 4. puntua, enplegua). Kasu horretan, berriro aztertu beharko litzateke.

### 4.2 Aplikatzen diren betebeharrak eta neurriak

| Betebeharra | Nola betetzen dugun |
|---|---|
| **AA alfabetatzea (4. artikulua)** — sistema erabiltzen duten pertsonek nahikoa ezagutza izatea | Eredua, atalaseak eta mugak dokumentatuta daude ([`ml_eredua_notebook_dokumentazioa.md`](ml_eredua_notebook_dokumentazioa.md)): 0,15 atalasea, recall 0,89, alarma faltsuen kopurua eta detektatzen ez diren hutsegiteak (TWF). |
| **Giza gainbegiratzea** (arrisku handiko sistemetan derrigorrezkoa, hemen praktika onena) | Sistemak ez du ekintzarik automatikoki egiten. Alertak (`KONTUZ` / `LARRIA`) pertsona batek erabakitzeko bakarrik dira; MCP tresnak irakurketa-soilekoak dira. |
| **Gardentasuna eta azalgarritasuna** | Alerta-mailak argiak dira (OK ≤ 0,15, KONTUZ 0,15–0,8, LARRIA > 0,8) eta `scoring/app/services/model.py`-n daude. Erabilitako aldagaiak (sentsoreak eta haietatik eratorritakoak) dokumentatuta daude. |
| **Datuen kalitatea eta alborapena** | Datu-leakage-a saihesten da: `failure_TWF/HDF/PWF/OSF/RNF` ez dira features gisa erabiltzen. Balidazioa datu-multzo bereizian egiten da (1.600 erregistro). Datuak makinenak dira, ez pertsonenak. |
| **Zehaztasuna eta mugak jakinaraztea** | Dokumentazioak argi esaten du eredua ez dela perfektua: 54 hutsegitetik 6 ez dira detektatzen, eta 0 alertak ez du "arriskurik ez" esan nahi (datuak ez badira iristen, ere 0 alerta izango dira). |
| **Segurtasun informatikoa (kiberseguritatea)** | Autentifikazioa JWT bidez, sekretuak `.env`-n, HTTPS Caddy-rekin (produkzioan) eta MCP arnesa (ikus 1–3 atalak). |
| **Erregistroak eta trazabilitatea** | Iragarpen guztiak Elasticsearch-eko `cnc-predictions` indizean gordetzen dira denbora-markarekin; ereduaren aurreko bertsioak `models/backups/` karpetan daude. |

### 4.3 Egiteko dagoena

- Ereduaren aldaketen erregistro formala mantentzea (zein bertsio zein egunetan jarri zen produkzioan).
- Erabiltzaileei (mantentze-teknikariak) AA alfabetatze-prestakuntza laburra ematea, ereduaren mugei buruz.
- Ereduaren errendimendua aldizka berrikustea (datu berriekin *drift*-a detektatzeko).

## 5. DBEO / RGPD (2016/679 Erregelamendua) betetzea

### 5.1 Tratatzen diren datuak

| Datu-mota | Datu pertsonala al da? | Oharra |
|---|---|---|
| Makinen sentsore-datuak (tenperatura, bibrazioa, potentzia, higadura...) | **Ez** | Makina bakoitzaren identifikatzailea (`CNC-039`) ekipo industrial bat da, ez pertsona bat. |
| Iragarpenak eta alertak (`cnc-predictions`) | **Ez** | Makinen probabilitateak dira. |
| NiFi, API eta Samba erabiltzaile-izenak, saio-tokenak | **Bai** (pertsona identifikagarriak izan daitezke) | Sistema administratzen duten pertsonen kredentzialak. |
| Telegram `chat_id` (aukerakoa) | **Bai** | Alertak jasotzen dituen pertsona edo taldea identifikatzen du. |
| IP helbideak eta zerbitzuen logak | **Bai** (IP helbideak datu pertsonaltzat hartzen dira) | Docker logetan eta Caddy-n azaltzen dira. |
| Taldeko kideen izenak dokumentazioan | **Bai** | Proiektuaren egile gisa agertzen dira. |

Ondorioa: sistemaren zati nagusia (sentsoreak eta iragarpenak) **ez da DBEO-ren eremuan sartzen**, baina bai erabiltzaileen eta administrazioaren datu txikiak.

### 5.2 Printzipioak eta neurriak

| Printzipioa / artikulua | Nola betetzen dugun |
|---|---|
| **Gutxieneko datuak (5.1.c)** | Ez da langileen daturik biltzen. Operadoreen izenik, txandarik edo errendimendu-daturik ez dago sentsore-fluxuan. |
| **Helburuaren mugaketa (5.1.b)** | Datuak mantentze prediktiborako bakarrik erabiltzen dira. |
| **Segurtasuna (32. artikulua)** | Autentifikazioa (JWT), sekretuen kudeaketa `.env`-n, HTTPS (Caddy), NiFi-rako sarbide-kredentzialak, eta MCP arnesa (pasahitzak, IPak eta posta-helbideak modelora ez bidaltzeko). |
| **Diseinuz eta lehenespenez babesa (25. artikulua)** | MCP-k eremuen zerrenda zuria erabiltzen du; sarrera berriak lehenespenez blokeatuta daude (*fail closed*). Telegram aukerakoa da eta lehenespenez desgaituta dago (`TELEGRAM_BOT_TOKEN` hutsik). |
| **Legezko oinarria (6. artikulua)** | Erakundearen interes legitimoa (6.1.f): ekipoen mantentze-lanak eta ekoizpen-jarraitutasuna. |
| **Pertsonei buruzko erabaki automatizatuak (22. artikulua)** | Ez dago. Sistemak makinei buruz erabakitzen du, ez pertsonei buruz. |

### 5.3 Hirugarrenak eta nazioarteko transferentziak

| Zerbitzua | Zer jasotzen duen | Neurria |
|---|---|---|
| **Telegram** (aukerakoa) | Alerta-mezuak (makina eta maila) eta `chat_id` | Aukerakoa; alerta-mezuek ez dute datu pertsonalik izan behar. Telegram EBtik kanpo dago: erabiltzen bada, transferentzia kontuan hartu behar da (V. kapitulua). |
| **Claude / Anthropic** (MCP bidez, garapenean) | MCP tresnen irteera (iragarpenak eta alertak) | `guard.py`-k datu sentikorrak ezkutatzen ditu eta hook-ak sekretuak irakurtzea blokeatzen du. Produkzioko datu pertsonalak ez dira bidaltzen. |

### 5.4 Egiteko dagoena

- **Atxikipen-epeak definitzea**: Elasticsearch-eko indizeen (`cnc-sensors`, `cnc-predictions`) eta logen gordetze-epea zehaztea eta ILM politikaren bidez automatizatzea (5.1.e). Ez dago oraindik zehaztuta.
- **Tratamendu-jardueren erregistroa (30. artikulua)** osatzea, erakundeak eskatzen badu.
- Datu pertsonalak daudela egiaztatzea benetako instalazioan (adib. operadoreen izenak makinen identifikatzaileetan sartzen badira, datu horiek DBEO-ren eremuan sartuko lirateke).
- Telegram erabiltzen bada, hornitzailearekin transferentziak aztertzea (28. eta 44-49. artikuluak).

## 6. Laburpena

| Araudia | Egoera |
|---|---|
| AI Act | **Arrisku minimoa.** Giza gainbegiratzea, dokumentazioa eta kiberseguritatea bete dira; AA alfabetatzea eta bertsioen erregistroa hobetu daitezke. |
| DBEO / RGPD | **Datu pertsonal gutxi.** Sentsore-datuak ez dira pertsonalak; kredentzialak, IPak eta Telegram `chat_id` babestuta daude. Atxikipen-epeak definitu behar dira. |
