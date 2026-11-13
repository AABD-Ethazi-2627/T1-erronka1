"""
sklearn Pipeline osoa: feature engineering + kodeketa + eredua.

Pipeline osoa gordetzen da .pkl-an, beraz API-k sarrera gordinak (RAW_FEATURES)
bidaltzen dizkio eta ez du aurreprozesaketarik errepikatu behar.

KONTUZ: pickle-ak `cnc_ml.features.add_features`-erako erreferentzia gordetzen du;
API-ren edukiontzian `cnc_ml` inportagarri egon behar da (Dockerfile-ak kopiatzen du).
"""

from sklearn.base import BaseEstimator
from sklearn.compose import ColumnTransformer
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import FunctionTransformer, OneHotEncoder, StandardScaler

from .columns import CATEGORICAL_FEATURES, ENGINEERED_FEATURES, MACHINE_TYPES, NUMERIC_FEATURES
from .features import add_features


def build_pipeline(estimator: BaseEstimator) -> Pipeline:
    preprocess = ColumnTransformer(
        [
            ("cat", OneHotEncoder(categories=[MACHINE_TYPES],handle_unknown="ignore"), CATEGORICAL_FEATURES),
            ("num", StandardScaler(), NUMERIC_FEATURES + ENGINEERED_FEATURES),
        ]
    )
    return Pipeline(
        [
            ("features", FunctionTransformer(add_features)),
            ("preprocess", preprocess),
            ("model", estimator),
        ]
    )
