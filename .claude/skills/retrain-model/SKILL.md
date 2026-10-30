---
name: retrain-model
description: Reentrena, valida y despliega el modelo de fallos de CNC Guard (models/cnc_failure_model.pkl). Úsala cuando pidan reentrenar, mejorar o sustituir el modelo, o cuando el modelo cargado falle o dé predicciones raras.
---

# Reentrenar y desplegar el modelo

## Contexto
- Entrenamiento: `notebooks/02_training_ML.ipynb`; datos: `data/ai4i2020_train.csv`.
- El `.pkl` es un **Pipeline completo** (features + clasificador). La API le pasa solo `RAW_FEATURES` (`scoring/cnc_ml/columns.py`); las features derivadas salen de `scoring/cnc_ml/features.py`.
- **No uses `failure_TWF/HDF/PWF/OSF/RNF` como features**: son subconjuntos del objetivo (data leakage, ver `FAILURE_SUBTYPES`).

## Procedimiento
1. **Backup** del modelo actual: copia `models/cnc_failure_model.pkl` a `models/backups/` (ya está en `.gitignore`).
2. Ejecuta el notebook y guarda el pipeline nuevo con `joblib.dump` en un fichero temporal (`models/cnc_failure_model.new.pkl`), no sobre el actual.
3. **Valida** antes de sustituir: recall y F1 de la clase "fallo" sobre datos no vistos (el dataset está desbalanceado; la accuracy engaña). No sustituyas si empeoran respecto al modelo actual; pregunta al usuario.
4. Comprueba compatibilidad: `cd scoring && pytest` (usa `requirements-dev.txt`).
5. Sustituye el fichero y reinicia: `docker compose restart scoring-api`.
6. Verifica con `model_health` (MCP) → `model_loaded: true`, y una `predict_failure` de prueba (ejemplo de `scoring/app/schemas/prediction.py`).

## Cuidados
- La versión de scikit-learn del entrenamiento debe coincidir con `scoring/requirements.txt`, o el `joblib.load` falla (la API arranca igualmente con `model_loaded=false`).
- No hagas commit de `.pkl` nuevos sin que el usuario lo pida: el actual está versionado.
- Si cambian las columnas de entrada, hay que cambiar también `SentsoreSaria`, el flujo de NiFi y Streamlit; avisa antes.
