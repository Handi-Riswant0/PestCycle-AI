
import warnings
import joblib
import numpy as np
import pandas as pd

from pathlib import Path

from sklearn.compose import ColumnTransformer
from sklearn.preprocessing import OneHotEncoder
from sklearn.pipeline import Pipeline
from sklearn.dummy import DummyRegressor
from sklearn.ensemble import (
    RandomForestRegressor,
    ExtraTreesRegressor,
    GradientBoostingRegressor
)
from sklearn.metrics import (
    mean_absolute_error,
    mean_squared_error,
    r2_score
)

warnings.filterwarnings("ignore")

# ============================================================
# PESTCYCLE AI - MODEL TRAINING
# NASA POWER x WBC
# ============================================================

BASE = Path(__file__).resolve().parents[1]
DATA = BASE / "data"
MODELS = BASE / "models"

MODELS.mkdir(exist_ok=True)

INPUT = DATA / "wbc_next_month_ml_dataset_2026.csv"

OUTPUT_METRICS = DATA / "wbc_model_comparison_2026.csv"
OUTPUT_PREDICTIONS = DATA / "wbc_model_predictions_2026.csv"
OUTPUT_AUDIT = DATA / "wbc_model_training_audit.txt"

TARGETS = [
    "WBC_AFFECTED_HA",
    "WBC_PUSO_HA"
]

CATEGORICAL_FEATURES = [
    "REGION_KEY"
]

NUMERIC_FEATURES = [
    "MONTH_SIN",
    "MONTH_COS",
    "T2M_MEAN_LAG1",
    "T2M_MAX_LAG1",
    "T2M_MIN_LAG1",
    "RH2M_MEAN_LAG1",
    "PRECTOTCORR_SUM_LAG1",
    "WEATHER_DAYS_LAG1",
    "WBC_AFFECTED_HA_LAG1",
    "WBC_PUSO_HA_LAG1"
]

FEATURES = (
    CATEGORICAL_FEATURES
    + NUMERIC_FEATURES
)

print("=" * 70)
print("PESTCYCLE AI - MODEL TRAINING")
print("=" * 70)

# ------------------------------------------------------------
# 1. MEMBACA DATA
# ------------------------------------------------------------

print("\n[1] MEMBACA DATASET...")

if not INPUT.exists():
    raise FileNotFoundError(INPUT)

df = pd.read_csv(INPUT)

required = (
    FEATURES
    + TARGETS
    + ["YEAR", "MONTH", "DATA_SPLIT"]
)

missing = [
    c for c in required
    if c not in df.columns
]

if missing:
    raise ValueError(
        f"Kolom tidak ditemukan: {missing}"
    )

if df[required].isna().any().any():
    raise ValueError(
        "Dataset mengandung nilai kosong."
    )

print("Jumlah data:", len(df))
print("Jumlah wilayah:", df["REGION_KEY"].nunique())

# ------------------------------------------------------------
# 2. MEMBAGI TRAIN DAN TEST
# ------------------------------------------------------------

print("\n[2] MEMBAGI DATA TRAIN DAN TEST...")

train = df[df["DATA_SPLIT"] == "TRAIN"].copy()
test = df[df["DATA_SPLIT"] == "TEST"].copy()

if len(train) == 0 or len(test) == 0:
    raise ValueError("Train atau test kosong.")

X_train = train[FEATURES]
X_test = test[FEATURES]

print("TRAIN:", len(train))
print("TEST :", len(test))

# ------------------------------------------------------------
# 3. MEMBENTUK PREPROCESSOR
# ------------------------------------------------------------

print("\n[3] MENYIAPKAN PREPROCESSING...")

preprocessor = ColumnTransformer(
    transformers=[
        (
            "region",
            OneHotEncoder(handle_unknown="ignore"),
            CATEGORICAL_FEATURES
        ),
        (
            "numeric",
            "passthrough",
            NUMERIC_FEATURES
        )
    ]
)

# ------------------------------------------------------------
# 4. MENDEFINISIKAN MODEL
# ------------------------------------------------------------

models = {
    "DUMMY_BASELINE": DummyRegressor(
        strategy="mean"
    ),

    "RANDOM_FOREST": RandomForestRegressor(
        n_estimators=300,
        max_depth=6,
        min_samples_leaf=3,
        random_state=42,
        n_jobs=-1
    ),

    "EXTRA_TREES": ExtraTreesRegressor(
        n_estimators=300,
        max_depth=6,
        min_samples_leaf=3,
        random_state=42,
        n_jobs=-1
    ),

    "GRADIENT_BOOSTING": GradientBoostingRegressor(
        n_estimators=100,
        learning_rate=0.03,
        max_depth=2,
        min_samples_leaf=3,
        loss="huber",
        random_state=42
    )
}

# ------------------------------------------------------------
# 5. TRAINING DAN EVALUASI
# ------------------------------------------------------------

print("\n[4] TRAINING MODEL...")

metrics = []
prediction_results = []
audit_lines = []

for target in TARGETS:

    print("\n" + "-" * 65)
    print("TARGET:", target)
    print("-" * 65)

    y_train = train[target].astype(float)
    y_test = test[target].astype(float)

    for model_name, estimator in models.items():

        print("\nTraining:", model_name)

        pipeline = Pipeline([
            ("preprocessor", preprocessor),
            ("model", estimator)
        ])

        # Transformasi log untuk mengurangi pengaruh
        # nilai target yang sangat ekstrem.
        y_train_log = np.log1p(y_train)

        pipeline.fit(
            X_train,
            y_train_log
        )

        prediction_log = pipeline.predict(X_test)

        predictions = np.expm1(
            prediction_log
        )

        predictions = np.maximum(
            predictions,
            0
        )

        mae = mean_absolute_error(
            y_test,
            predictions
        )

        rmse = np.sqrt(
            mean_squared_error(
                y_test,
                predictions
            )
        )

        r2 = r2_score(
            y_test,
            predictions
        )

        nonzero_actual = y_test > 0

        nonzero_count = int(
            nonzero_actual.sum()
        )

        nonzero_mae = (
            mean_absolute_error(
                y_test[nonzero_actual],
                predictions[nonzero_actual]
            )
            if nonzero_count > 0
            else np.nan
        )

        zero_count = int(
            (y_test == 0).sum()
        )

        metrics.append({
            "TARGET": target,
            "MODEL": model_name,
            "TEST_SIZE": len(y_test),
            "MAE": mae,
            "RMSE": rmse,
            "R2": r2,
            "ZERO_COUNT": zero_count,
            "NONZERO_COUNT": nonzero_count,
            "NONZERO_MAE": nonzero_mae
        })

        for index, actual, predicted in zip(
            test.index,
            y_test,
            predictions
        ):

            row = test.loc[index]

            prediction_results.append({
                "REGION_KEY": row["REGION_KEY"],
                "YEAR": row["YEAR"],
                "MONTH": row["MONTH"],
                "TARGET": target,
                "MODEL": model_name,
                "ACTUAL": actual,
                "PREDICTED": predicted,
                "ERROR": actual - predicted,
                "ABS_ERROR": abs(actual - predicted)
            })

        model_path = (
            MODELS /
            f"{model_name.lower()}_{target.lower()}.joblib"
        )

        joblib.dump(
            pipeline,
            model_path
        )

        print("MAE :", round(mae, 5))
        print("RMSE:", round(rmse, 5))
        print("R2  :", round(r2, 5))

        audit_lines.append(
            f"{target} | {model_name} | "
            f"MAE={mae:.6f} | "
            f"RMSE={rmse:.6f} | "
            f"R2={r2:.6f} | "
            f"Nonzero MAE={nonzero_mae}"
        )

# ------------------------------------------------------------
# 6. MENYIMPAN HASIL
# ------------------------------------------------------------

print("\n[5] MENYIMPAN HASIL...")

metrics_df = pd.DataFrame(metrics)

predictions_df = pd.DataFrame(
    prediction_results
)

metrics_df.to_csv(
    OUTPUT_METRICS,
    index=False,
    encoding="utf-8-sig"
)

predictions_df.to_csv(
    OUTPUT_PREDICTIONS,
    index=False,
    encoding="utf-8-sig"
)

# ------------------------------------------------------------
# 7. LAPORAN AUDIT
# ------------------------------------------------------------

report = [
    "=" * 70,
    "PESTCYCLE AI - MODEL TRAINING AUDIT",
    "=" * 70,
    "",
    f"Jumlah TRAIN: {len(train)}",
    f"Jumlah TEST: {len(test)}",
    f"Jumlah wilayah: {df['REGION_KEY'].nunique()}",
    f"Jumlah fitur: {len(FEATURES)}",
    "",
    "FITUR:",
    *FEATURES,
    "",
    "HASIL MODEL:",
    *audit_lines,
    "",
    "CATATAN METODOLOGI:",
    "- Model diuji menggunakan pembagian temporal.",
    "- Target diprediksi secara terpisah.",
    "- Transformasi log1p digunakan saat training.",
    "- Prediksi dikembalikan ke skala hektare.",
    "- Prediksi negatif dibatasi menjadi nol.",
    "- Test set tidak digunakan untuk fitting.",
    "- Hasil belum merupakan validasi lintas tahun.",
    "",
    "FILE OUTPUT:",
    str(OUTPUT_METRICS),
    str(OUTPUT_PREDICTIONS),
    str(MODELS),
    "",
    "=" * 70,
    "MODEL TRAINING SELESAI",
    "=" * 70
]

OUTPUT_AUDIT.write_text(
    "\n".join(report),
    encoding="utf-8"
)

# ------------------------------------------------------------
# 8. TAMPILKAN HASIL AKHIR
# ------------------------------------------------------------

print("\n" + "=" * 70)
print("PERBANDINGAN MODEL")
print("=" * 70)

print(
    metrics_df.sort_values(
        ["TARGET", "MAE"]
    ).to_string(index=False)
)

print("\nFILE OUTPUT:")
print(OUTPUT_METRICS)
print(OUTPUT_PREDICTIONS)
print(OUTPUT_AUDIT)
print(MODELS)

print("\nMODEL TRAINING BERHASIL")
print("=" * 70)
