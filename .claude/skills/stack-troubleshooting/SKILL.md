---
name: stack-troubleshooting
description: Diagnostica por qué no llegan datos o falla el pipeline de CNC Guard (Samba, Filebeat, Kafka, NiFi, Scoring API, Elasticsearch, Kibana, Streamlit, Telegram). Úsala cuando digan "no llegan datos", "el dashboard está vacío", "no hay alertas" o un contenedor falle.
---

# Troubleshooting del pipeline

Flujo: Samba (CSV) → Filebeat → Kafka `cnc-sensors-raw` → NiFi → (Scoring API) → Elasticsearch `cnc-sensors` / `cnc-predictions` → Kibana / Streamlit / Telegram.

**Revisa en este orden y para en la primera capa rota.** Solo lectura salvo que el usuario autorice reiniciar algo.

| # | Capa | Comprobación |
|---|---|---|
| 0 | Contenedores | `docker compose ps` (¿healthy?) |
| 1 | Samba / volumen | `docker compose exec filebeat ls /ruta-del-volumen` ; ver `cnc-stream` en `docker-compose.yml` |
| 2 | Filebeat | `docker compose logs --tail 50 filebeat` |
| 3 | Kafka | `docker compose exec kafka kafka-console-consumer --bootstrap-server localhost:9092 --topic cnc-sensors-raw --max-messages 3 --timeout-ms 5000` |
| 4 | NiFi | UI https://localhost:8443: colas con datos atascados, procesadores en rojo; flujos en `nifi-flows/` |
| 5 | Scoring API | MCP `model_health` o `curl localhost:8000/health` |
| 6 | Elasticsearch | `curl localhost:9200/_cat/indices?v` y `_count` de `cnc-sensors` y `cnc-predictions` |
| 7 | Kibana/Streamlit/Telegram | `docker compose logs --tail 50 <servicio>` |

Ajusta nombres de servicio con `docker compose config --services` si no coinciden.

## Fallos típicos
- **Volumen CIFS/Samba desactualizado**: Filebeat no ve CSV nuevos. Los últimos commits ajustan las opciones de caché CIFS de `cnc-stream`; revisa `docker-compose.yml` y que `SMB_IP`/credenciales de `.env` sean correctos.
- **403/401 en `/predict`**: token JWT caducado (5 min) o `API_PASSWORD` distinta entre `.env` y la configuración OAuth2 de NiFi.
- **`model_loaded: false`**: falta `models/cnc_failure_model.pkl` o versión de sklearn incompatible → skill `retrain-model`.
- **`cnc-sensors` crece pero `cnc-predictions` no**: el fallo está en NiFi→Scoring (rama de predicción), no en la ingesta.
- **Telegram no avisa**: `TELEGRAM_BOT_TOKEN`/`TELEGRAM_CHAT_ID` vacíos, o alertas ya enviadas (estado en `/state/seen.json`).
- **Elasticsearch sin memoria / unhealthy**: el stack necesita ~4 GB libres.

Termina indicando la capa rota, la evidencia (log o salida) y el arreglo propuesto. Pide confirmación antes de `restart`, `down` o borrar volúmenes.
