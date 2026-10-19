"""Datu-multzoaren zutabe-izenak (iturri bakarra)."""

# Ereduaren sarrera gordinak: API-k jasotzen dituenak eta ai4i2020_train.csv-n daudenak
NUMERIC_FEATURES = ["air_temp_K", "process_temp_K", "rpm", "torque_Nm", "tool_wear_min"]
CATEGORICAL_FEATURES = ["machine_type"]
RAW_FEATURES = CATEGORICAL_FEATURES + NUMERIC_FEATURES

# features.add_features()-ek sortzen dituenak
ENGINEERED_FEATURES = ["temp_diff_K", "power_W", "wear_torque"]

TARGET = "machine_failure"

# Hutsegite-motak: helburuaren azpimultzoak dira, beraz EZ dira feature gisa erabili behar
# (data leakage: ereduak erantzuna "ikusiko" luke).
FAILURE_SUBTYPES = ["failure_TWF", "failure_HDF", "failure_PWF", "failure_OSF", "failure_RNF"]

MACHINE_TYPES = ["L", "M", "H"]
