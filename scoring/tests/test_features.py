import math

import pandas as pd

from cnc_ml.columns import RAW_FEATURES
from cnc_ml.features import add_features


def test_features():
    X = pd.DataFrame([{"machine_type": "L", "air_temp_K": 298.0, "process_temp_K": 308.0,
                       "rpm": 1500, "torque_Nm": 40.0, "tool_wear_min": 100}])[RAW_FEATURES]
    X = add_features(X)
    assert X.loc[0, "temp_diff_K"] == 10.0
    assert X.loc[0, "power_W"] == 40.0 * 1500 * 2 * math.pi / 60
    assert X.loc[0, "wear_torque"] == 4000.0
