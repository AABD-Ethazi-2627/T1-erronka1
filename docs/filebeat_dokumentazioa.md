# Filebeat dokumentazioa

## 1. Deskribapena

Filebeat **CNC Guard** hodiaren sarrera-puntua da. Simuladoreak sortzen dituen
CNC makinen sentsore-datuen CSV fitxategiak irakurri eta **Kafka**-ra bidaltzen ditu.
Handik aurrera NiFi arduratzen da datuak Elasticsearch-era eta Scoring APIra eramateaz.

```text
Simuladorea (Samba) ──CSV──► Filebeat ──► Kafka (cnc-sensors-raw) ──► NiFi ──► ...
```

Filebeat-ek **ez du Elasticsearch-ekin hitz egiten**: Kafka-ra soilik idazten du.
Horregatik, Elasticsearch edo Kibana-ko errore bat ez da Filebeat-etik etorriko.

| Atributua | Balioa |
|---|---|
| Irudia | `docker.elastic.co/beats/filebeat:8.10.2` |
| Konfigurazioa | [filebeat/filebeat.yml](../filebeat/filebeat.yml) |
| Edukiontziaren izena | `cnc-filebeat` (produkzioan; dev-en Compose-k sortutakoa) |
| Sarrera | `/mnt/cnc-stream/*.csv` |
| Irteera | Kafka, `kafka:9092`, `cnc-sensors-raw` topikoa |

## 2. Konfigurazioa

`filebeat/filebeat.yml` fitxategiak hiru atal ditu: sarrera, irteera eta erregistroa.

### 2.1 Sarrera (`filebeat.inputs`)

```yaml
filebeat.inputs:
  - type: filestream
    id: cnc-stream
    paths:
      - /mnt/cnc-stream/*.csv
    exclude_lines: ['^[A-Za-z]']
    file_identity.path: ~
    prospector.scanner.check_interval: 5s
```

| Ezarpena | Zer egiten du | Zergatik |
|---|---|---|
| `type: filestream` | Fitxategiak lerroz lerro irakurtzen ditu. | Filebeat 8-n gomendatutako sarrera-mota (`log` zaharkituta dago). |
| `id: cnc-stream` | Sarreraren identifikatzaile bakarra. | `filestream`-ek beharrezkoa du; registryko egoera horri lotzen zaio. |
| `paths` | Irakurriko diren fitxategiak (`*.csv`). | Simuladoreak CSV berriak sortzen ditu; guztiak hartzen dira. |
| `exclude_lines: ['^[A-Za-z]']` | Letraz hasten diren lerroak baztertzen ditu. | CSV bakoitzaren goiburua (`timestamp,machine_id,...`) letraz hasten da; datu-lerroak data batez (`2026-...`). Goiburua Kafka-ra bidaliko balitz, NiFi-k eta Elasticsearch-ek datu gisa tratatzen saiatuko lirateke. |
| `file_identity.path: ~` | Fitxategiak **bidearen** arabera identifikatzen ditu. | Karpeta sare bidezkoa (CIFS) da eta inodoak ez dira egonkorrak muntatze berrien artean; inodoen arabera identifikatuz gero, fitxategi berdinak berriro irakur litezke. |
| `prospector.scanner.check_interval: 5s` | Fitxategi berriak bilatzeko maiztasuna. | 5 segundoko atzerapena nahikoa da denbora errealeko simulaziorako. |

### 2.2 Irteera (`output.kafka`)

```yaml
output.kafka:
  hosts:
    - kafka:9092
  topic: cnc-sensors-raw
  codec.format:
    string: '%{[message]}'
```

- `hosts: kafka:9092`: Docker sare barneko `kafka` zerbitzu-izena erabiltzen da
  (`cnc-net` sarean izenak hostname gisa funtzionatzen dute).
- `topic: cnc-sensors-raw`: NiFi-k topiko honetatik kontsumitzen du.
- `codec.format.string: '%{[message]}'`: **lerro gordina** bidaltzen da, ez Beats-en
  gertaera JSON osoa (`@timestamp`, `host`, `log`, `agent`...). Horrela Kafka-ko mezu
  bakoitza CSV lerro hutsa da, adibidez:

```text
2026-04-29T10:57:50Z,CNC-039,L,299.0,308.6,1587,38.6,124,0,0,0,0,0,0
```

### 2.3 Erregistroa

```yaml
logging.level: info
logging.to_files: false
```

Logak ez dira fitxategira idazten; `stderr`-era doaz, eta `docker logs` bidez ikusten
dira (konposeko `command`-ak `-e` aukera gehitzen du).

## 3. Docker Compose integrazioa

Bi ingurunetan zerbitzu bera definitzen da; sarrerako CSV-en iturria bakarrik aldatzen da.

```yaml
filebeat:
  image: docker.elastic.co/beats/filebeat:8.10.2
  user: root
  command: ["filebeat", "-e", "--strict.perms=false"]
  volumes:
    - ./filebeat/filebeat.yml:/usr/share/filebeat/filebeat.yml:ro
    - <CSV iturria>:/mnt/cnc-stream:ro
    - filebeat-data:/usr/share/filebeat/data
  depends_on:
    kafka:
      condition: service_healthy
```

| Elementua | Azalpena |
|---|---|
| `user: root` | Muntatutako karpetak irakurri ahal izateko. |
| `--strict.perms=false` | Filebeat-ek ez du konfigurazio-fitxategiaren jabetza/baimenak zorrozki egiaztatzen (bolumen bidez muntatuta `root`-ena ez da). |
| `-e` | Logak `stderr`-era bidaltzen ditu. |
| `filebeat.yml:ro` | Konfigurazioa irakurtzeko soilik muntatzen da. |
| `/mnt/cnc-stream:ro` | CSV-ak **irakurtzeko soilik** muntatzen dira: Filebeat-ek ez ditu inoiz aldatzen edo ezabatzen. |
| `filebeat-data` | Registry-a gordetzen duen bolumen iraunkorra (ikus 4. atala). |
| `depends_on: kafka (service_healthy)` | Kafka prest egon arte ez da abiatzen. |

### Garapena (`docker-compose.dev.yml`)

Samba gabe. CSV-ak tokiko `./data/stream/` karpetan jarri behar dira:

```yaml
- ./data/stream:/mnt/cnc-stream:ro
```

### Produkzioa (`docker-compose.prod.yml`)

Simuladorea zerbitzari nagusian dago eta CSV-ak **Samba (CIFS)** bidez irakurtzen dira,
`cnc-stream-cifs` bolumenaren bidez:

```yaml
volumes:
  cnc-stream-cifs:
    driver: local
    driver_opts:
      type: cifs
      device: "//${SMB_IP}/cnc-stream"
      o: "addr=${SMB_IP},username=${SMB_USERNAME},password=${SMB_PASSWORD},vers=3.0,ro,actimeo=0,cache=none,nohandlecache,nolease"
```

| Aukera | Zertarako |
|---|---|
| `device: //IP/share` | Formatua `//IP/share` da (ez `smb://`). |
| `addr=${SMB_IP}` | Docker Desktop-en beharrezkoa. |
| `vers=3.0` | SMB 3.0 protokoloa. |
| `ro` | Irakurtzeko soilik. |
| `actimeo=0`, `cache=none`, `nohandlecache`, `nolease` | CIFS cachea desaktibatzen dute, Filebeat-ek zerbitzariak sortutako CSV berriak eta lerro berriak berehala ikus ditzan. Cache aktibatuta, mugak "zaharkituta" geratzen dira eta ez dira datu berriak ikusten. |

`SMB_IP`, `SMB_USERNAME` eta `SMB_PASSWORD` aldagaiak `.env` fitxategian daude
(`.env.example` ikusi). Fitxategi hori ez da git-era igotzen; pasahitza ez idatzi
fitxategi bertsionatuetan.

## 4. Registry-a eta berrirakurketa

Filebeat-ek fitxategi bakoitzean zein byte/lerro irakurri duen gogoratzen du
`/usr/share/filebeat/data` karpetako **registry**-an. Karpeta hori `filebeat-data`
bolumenean dago, beraz:

- Edukiontzia berrabiarazi edo birsortzen bada, **ez da dena berriro bidaltzen**;
  gelditu zen tokitik jarraitzen du.
- `docker compose down` erabiliz gero, bolumena mantentzen da; `down -v` erabiliz gero
  ezabatu egiten da eta CSV guztiak **berriro irakurriko dira** (Kafka-n bikoizketak
  sortuz, Kafka-ren datuak ere ezabatu ez badira).

CSV-ak nahita berriro irakurrarazteko:

```bash
docker compose down
docker volume rm <proiektua>_filebeat-data   # adib. t1-erronka1_filebeat-data
docker compose up -d
```

## 5. Egiaztapena eta arazoak konpontzea

```bash
# Filebeat-ek CSV-ak ikusten ditu?
docker exec cnc-filebeat ls /mnt/cnc-stream

# Logak
docker logs cnc-filebeat --tail 100

# Aldaketak aplikatu filebeat.yml editatu ondoren
docker compose restart filebeat
```

Kafka-n mezuak iristen ari diren egiaztatzeko:

```bash
docker exec cnc-kafka kafka-console-consumer --bootstrap-server kafka:9092 \
  --topic cnc-sensors-raw --from-beginning --max-messages 5
```

| Sintomak | Arrazoi probablea | Konponbidea |
|---|---|---|
| `ls /mnt/cnc-stream` hutsik edo errorea | Samba ez dago muntatuta edo kredentzial okerrak. | `SMB_IP`, `SMB_USERNAME`, `SMB_PASSWORD` egiaztatu `.env`-n; sarbidea zerbitzari nagusira. |
| Fitxategiak ikusten dira baina CSV berriak ez | CIFS cache zaharkitua. | `docker-compose.prod.yml`-ko `cnc-stream-cifs` aukerak (`cache=none`, `actimeo=0`...) egiaztatu. |
| `Failed to connect` / `dial tcp ... kafka:9092` | Kafka ez dago prest edo sare okerra. | `docker compose ps kafka`; Filebeat-ek Kafka `healthy` egon arte itxaron behar du. |
| `no such file` logetan | `paths` ez dator bat muntatutako bidearekin. | `/mnt/cnc-stream/*.csv` eta bolumen-muntaketa alderatu. |
| Datuak ez dira berriro bidaltzen | Registry-ak jada irakurrita gisa markatu ditu. | 4. ataleko `filebeat-data` bolumena ezabatu. |
| Kafka-n goiburu-lerroak agertzen dira | `exclude_lines` aldatu da edo goiburua letraz ez hasten. | `exclude_lines: ['^[A-Za-z]']` berrezarri. |

## 6. Datu-fluxuan duen lekua

1. Simuladoreak CSV fitxategiak sortzen ditu (Samba karpetan, edo `data/stream/` garapenean).
2. **Filebeat-ek** 5 segundoro karpeta aztertzen du, lerro berriak irakurtzen ditu eta goiburuak baztertzen ditu.
3. Lerro bakoitza mezu gordin gisa argitaratzen da Kafka-ko `cnc-sensors-raw` topikoan.
4. NiFi-k topikoa kontsumitzen du, CSV lerroak parseatzen ditu eta Elasticsearch-era (`cnc-sensors`) eta Scoring APIra bidaltzen ditu (`cnc-predictions`).
5. Kibana, Streamlit eta Telegram-ek emaitzak erakusten dituzte.
