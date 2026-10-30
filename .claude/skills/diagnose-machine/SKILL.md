---
name: diagnose-machine
description: Diagnostica el estado y riesgo de una máquina CNC concreta (CNC-039, etc.) o lista las máquinas en alerta. Úsala cuando pregunten por el estado, riesgo, alertas o fallos probables de una máquina, o si "hay alguna máquina en peligro".
---

# Diagnóstico de máquina CNC

Usa las herramientas del servidor MCP `cnc-guard` (ver `.mcp.json`). Si no están disponibles, avisa al usuario de que falta `mcp-server/.venv` (ver README, sección MCP).

## Procedimiento
1. `model_health`. Si `status` es `down` o `model_loaded` es false, para y usa la skill `stack-troubleshooting`.
2. Pregunta general ("¿hay riesgo?"): `list_active_alerts` (por defecto 15 min). Después, `get_machine_status` de las 1-3 máquinas con mayor probabilidad.
3. Máquina concreta: `get_machine_status(machine_id, last_n=20)`.
   - `found: false` → no hay datos: comprueba que el ID existe (formato `CNC-039`) y, si es válido, usa `stack-troubleshooting` (el pipeline puede estar parado).
4. Analiza la **tendencia** (`trend`, `probability_delta`), no solo el último valor. Una máquina en 0.55 y subiendo es peor que una en 0.65 y bajando.
5. Si el usuario da lecturas de sensores hipotéticas, usa `predict_failure` (no guarda nada).

## Umbrales (fuente: `scoring/app/services/model.py`)
| alert_level | probabilidad |
|---|---|
| OK | ≤ 0.5 |
| KONTUZ (advertencia) | 0.5 – 0.8 |
| LARRIA (crítica) | > 0.8 |

## Causas probables (dataset AI4I 2020)
Las predicciones no traen el tipo de fallo; infiérelo de los sensores y márcalo como hipótesis:
- **TWF** desgaste de herramienta: `tool_wear_min` alto (≈ 200-240 min).
- **HDF** disipación de calor: diferencia `process_temp_K - air_temp_K` < 8.6 K con `rpm` < 1380.
- **PWF** potencia: potencia = torque × rpm × 2π/60 fuera de 3500-9000 W.
- **OSF** sobreesfuerzo: `tool_wear_min × torque_Nm` alto (> 11000 en L, 12000 en M, 13000 en H).
- **RNF** aleatorio: sin causa sensorial; no lo atribuyas si no hay otra explicación.

## Formato de respuesta
Estado actual → tendencia → causa probable (como hipótesis) → acción recomendada (revisar herramienta, parar máquina si LARRIA sostenida). Sé breve y cita las probabilidades.
