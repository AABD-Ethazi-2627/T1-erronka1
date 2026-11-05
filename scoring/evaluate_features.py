"""Compara variantes del clasificador sin guardar ni sustituir el modelo desplegado.

Ejecutar desde la raíz: PYTHONPATH=scoring python scoring/evaluate_features.py
Los resultados de validación cruzada sirven para comparar, no son una prueba externa.
"""

from pathlib import Path
import argparse

import numpy as np
import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import confusion_matrix, f1_score, precision_score, recall_score
from sklearn.model_selection import StratifiedKFold
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import FunctionTransformer, OneHotEncoder, StandardScaler

from cnc_ml.columns import ENGINEERED_FEATURES, NUMERIC_FEATURES, RAW_FEATURES, TARGET
from cnc_ml.features import add_features


def make_pipeline(engineered: bool, machine_type: bool) -> Pipeline:
    numeric = NUMERIC_FEATURES + (ENGINEERED_FEATURES if engineered else [])
    transformers = [("num", StandardScaler(), numeric)]
    if machine_type:
        transformers.append(("cat", OneHotEncoder(handle_unknown="ignore"), ["machine_type"]))
    return Pipeline([
        ("features", FunctionTransformer(add_features)),
        ("preprocess", ColumnTransformer(transformers)),
        ("model", RandomForestClassifier(n_estimators=100, class_weight="balanced", random_state=42, n_jobs=-1)),
    ])


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--data", type=Path, default=Path("data/ai4i2020_train.csv"))
    args = parser.parse_args()
    df = pd.read_csv(args.data)
    X, y = df[RAW_FEATURES], df[TARGET]
    splits = list(StratifiedKFold(n_splits=3, shuffle=True, random_state=42).split(X, y))
    print("3 particiones estratificadas; umbral de fallo > 0,5; métricas de clase fallo")
    for engineered in (False, True):
        for machine_type in (False, True):
            predictions = np.zeros(len(df), dtype=int)
            for train, validation in splits:
                pipeline = make_pipeline(engineered, machine_type)
                pipeline.fit(X.iloc[train], y.iloc[train])
                predictions[validation] = (pipeline.predict_proba(X.iloc[validation])[:, 1] > 0.5).astype(int)
            tn, fp, fn, tp = confusion_matrix(y, predictions, labels=[0, 1]).ravel()
            print(f"Físicas={engineered}, tipo={machine_type}: "
                  f"recall={recall_score(y, predictions):.3f}, "
                  f"precisión={precision_score(y, predictions, zero_division=0):.3f}, "
                  f"F1={f1_score(y, predictions):.3f}, TN={tn}, FP={fp}, FN={fn}, TP={tp}")


if __name__ == "__main__":
    main()
