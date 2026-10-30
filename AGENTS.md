# CNC Guard — guía para agentes de IA

Mantenimiento predictivo de máquinas CNC: CSV (Samba) → Filebeat → Kafka `cnc-sensors-raw` → NiFi → Scoring API (FastAPI + modelo ML) → Elasticsearch (`cnc-sensors`, `cnc-predictions`) → Kibana / Streamlit / Telegram. Documentación completa en `README.md` (euskera).

## Entornos
- Desarrollo: `docker compose -f docker-compose.dev.yml up -d --build`
- Producción: `docker compose -f docker-compose.prod.yml up -d --build`
- Los secretos están en `.env` (no se sube a git). No los imprimas ni los escribas en ficheros versionados.

## MCP `cnc-guard` (solo lectura)
Herramientas: `model_health`, `list_active_alerts`, `get_machine_status`, `predict_failure`.
- Claude Code: configurado en `.mcp.json`.
- Codex: configurado en `.codex/config.toml`.
- Otros clientes: comando `mcp-server/.venv/bin/python mcp-server/server.py` (stdio), con `API_URL=http://localhost:8000` y `ES_URL=http://localhost:9200`.
- Instalación: `cd mcp-server && python3 -m venv .venv && .venv/bin/pip install -r requirements.txt`.
- Un resultado de 0 alertas no significa "sin riesgo": puede ser que no lleguen datos. Compruébalo con `stack-troubleshooting`.

## Skills
Están en `.claude/skills/<nombre>/SKILL.md` (también visibles en `.agents/skills/`). Si tu agente no las carga solo, lee el `SKILL.md` correspondiente cuando la tarea encaje:

| Skill | Cuándo |
|---|---|
| `diagnose-machine` | Estado, riesgo o alertas de una máquina CNC; "¿hay alguna máquina en peligro?" |
| `stack-troubleshooting` | "No llegan datos", dashboard vacío, un contenedor falla |
| `retrain-model` | Reentrenar, validar o desplegar `models/cnc_failure_model.pkl` |

## Convenciones
- Los umbrales de alerta (OK ≤ 0.5, KONTUZ 0.5–0.8, LARRIA > 0.8) viven en `scoring/app/services/model.py`.
- No uses `failure_TWF/HDF/PWF/OSF/RNF` como features del modelo (data leakage).
- Tests: `mcp-server/.venv/bin/python -m pytest mcp-server/tests`.
