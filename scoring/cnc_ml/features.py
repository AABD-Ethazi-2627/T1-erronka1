"""
Feature engineering. Hutsegite-mota bakoitzaren arrazoi fisikoan oinarrituta:
  - HDF (heat dissipation): prozesu- eta aire-tenperaturen arteko aldea txikia
  - PWF (power):            potentzia mekanikoa = torkea * abiadura angeluarra
  - OSF (overstrain):       tresna-higadura * torkea
"""

import math

import pandas as pd


def add_features(X: pd.DataFrame) -> pd.DataFrame:
    X = X.copy()
    X["temp_diff_K"] = X["process_temp_K"] - X["air_temp_K"]
    X["power_W"] = X["torque_Nm"] * X["rpm"] * 2 * math.pi / 60
    X["wear_torque"] = X["tool_wear_min"] * X["torque_Nm"]
    return X
