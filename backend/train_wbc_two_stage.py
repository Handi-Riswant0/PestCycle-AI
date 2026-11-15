
from pathlib import Path
import warnings
import joblib
import numpy as np
import pandas as pd

from sklearn.compose import ColumnTransformer
from sklearn.preprocessing import OneHotEncoder
from sklearn.impute import SimpleImputer
from sklearn.pipeline import Pipeline

from sklearn.dummy import DummyClassifier, DummyRegressor
from sklearn.ensemble import (
    ExtraTreesClassifier,
    RandomForestClassifier,
    ExtraTreesRegressor,
    RandomForestRegressor
)

from sklearn.metrics import (
    accuracy_score,
    precision_score,
    recall_score,
    f1_score,
    roc_auc_score,
    average_precision_score,
    mean_absolute_error,
    mean_squared_error,
    r2_score
)

warnings.filterwarnings("ignore")

# ==========================================================
# 1. KONFIGURASI
# ==========================================================

BASE = Path(__file__).resolve().parent.parent
DATA = BASE / "data"
MODELS = BASE / "models" / "two_stage"

MODELS.mkdir(parents=True, exist_ok=True)

INPUT_FILE = DATA / "wbc_next_month_ml_dataset_2026.csv"

print("=" * 70)
print("PESTCYCLE AI - TWO STAGE MACHINE LEARNING")
print("=" * 70)

# ==========================================================
# 2. MEMBACA DATASET
# ==========================================================

print("\n[1] MEMBACA DATASET...")

df = pd.read_csv(INPUT_FILE)

numeric_features = [
    "YEAR",
    "MONTH",
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

categorical_features = ["REGION_KEY"]

features = numeric_features + categorical_features

required = (
    features
    + ["WBC_AFFECTED_HA", "DATA_SPLIT"]
)

missing = [c for c in required if c not in df.columns]

if missing:
    raise ValueError(f"Kolom tidak ditemukan: {missing}")

df["WBC_AFFECTED_HA"] = pd.to_numeric(
    df["WBC_AFFECTED_HA"],
    errors="coerce"
)

df = df.dropna(
    subset=["WBC_AFFECTED_HA", "DATA_SPLIT"]
).copy()

df["TARGET_OCCURRENCE"] = (
    df["WBC_AFFECTED_HA"] > 0
).astype(int)

train = df[df["DATA_SPLIT"] == "TRAIN"].copy()
test = df[df["DATA_SPLIT"] == "TEST"].copy()

if train.empty or test.empty:
    raise ValueError("Data TRAIN atau TEST kosong.")

if train["TARGET_OCCURRENCE"].nunique() != 2:
    raise ValueError("TRAIN harus memiliki kelas positif dan negatif.")

X_train = train[features]
X_test = test[features]

y_train = train["TARGET_OCCURRENCE"]
y_test = test["TARGET_OCCURRENCE"]

print("Total data :", len(df))
print("Train      :", len(train))
print("Test       :", len(test))

print("\nDistribusi target:")
print(df.groupby("DATA_SPLIT")["TARGET_OCCURRENCE"].value_counts())

# ==========================================================
# 3. PREPROCESSOR INDEPENDEN
# ==========================================================

def make_preprocessor():

    return ColumnTransformer(
        transformers=[
            (
                "numeric",
                SimpleImputer(strategy="median"),
                numeric_features
            ),
            (
                "categorical",
                Pipeline([
                    (
                        "imputer",
                        SimpleImputer(
                            strategy="most_frequent"
                        )
                    ),
                    (
                        "encoder",
                        OneHotEncoder(
                            handle_unknown="ignore"
                        )
                    )
                ]),
                categorical_features
            )
        ]
    )

print("\n[2] PREPROCESSING SIAP...")
print("Setiap model akan menggunakan preprocessor independen.")

# ==========================================================
# 4. STAGE 1 - CLASSIFICATION
# ==========================================================

print("\n[3] TRAINING STAGE 1 - CLASSIFICATION...")

classifiers = {
    "DUMMY_CLASSIFIER": DummyClassifier(
        strategy="prior"
    ),

    "EXTRA_TREES_CLASSIFIER": ExtraTreesClassifier(
        n_estimators=400,
        min_samples_leaf=2,
        max_features="sqrt",
        class_weight="balanced",
        random_state=42,
        n_jobs=-1
    ),

    "RANDOM_FOREST_CLASSIFIER": RandomForestClassifier(
        n_estimators=400,
        min_samples_leaf=2,
        max_features="sqrt",
        class_weight="balanced",
        random_state=42,
        n_jobs=-1
    )
}

trained_classifiers = {}
classification_results = []

for name, model in classifiers.items():

    print(f"\nTraining: {name}")

    # PREPROCESSOR BARU UNTUK SETIAP MODEL
    pipe = Pipeline([
        ("preprocessor", make_preprocessor()),
        ("model", model)
    ])

    pipe.fit(X_train, y_train)

    probability = pipe.predict_proba(X_test)[:, 1]

    predicted = (
        probability >= 0.5
    ).astype(int)

    result = {
        "MODEL": name,
        "TEST_SIZE": len(test),
        "ACCURACY": accuracy_score(
            y_test, predicted
        ),
        "PRECISION": precision_score(
            y_test, predicted,
            zero_division=0
        ),
        "RECALL": recall_score(
            y_test, predicted,
            zero_division=0
        ),
        "F1": f1_score(
            y_test, predicted,
            zero_division=0
        ),
        "ROC_AUC": roc_auc_score(
            y_test, probability
        ),
        "PR_AUC": average_precision_score(
            y_test, probability
        )
    }

    classification_results.append(result)
    trained_classifiers[name] = pipe

    joblib.dump(
        pipe,
        MODELS / f"{name.lower()}.joblib"
    )

    print(
        f"Accuracy: {result['ACCURACY']:.4f} | "
        f"F1: {result['F1']:.4f} | "
        f"PR-AUC: {result['PR_AUC']:.4f}"
    )

# ==========================================================
# 5. STAGE 2 - REGRESSION
# ==========================================================

print("\n[4] TRAINING STAGE 2 - REGRESSION...")

positive_train = train[
    train["WBC_AFFECTED_HA"] > 0
].copy()

positive_test = test[
    test["WBC_AFFECTED_HA"] > 0
].copy()

if len(positive_train) < 10:
    raise ValueError("Data positif TRAIN terlalu sedikit.")

if len(positive_test) < 2:
    raise ValueError("Data positif TEST terlalu sedikit untuk evaluasi.")

X_positive_train = positive_train[features]
X_positive_test = positive_test[features]

y_positive_train = positive_train["WBC_AFFECTED_HA"]
y_positive_test = positive_test["WBC_AFFECTED_HA"]

print("Positive TRAIN:", len(positive_train))
print("Positive TEST :", len(positive_test))

regressors = {
    "DUMMY_REGRESSOR": DummyRegressor(
        strategy="mean"
    ),

    "EXTRA_TREES_REGRESSOR": ExtraTreesRegressor(
        n_estimators=400,
        min_samples_leaf=2,
        max_features=0.8,
        random_state=42,
        n_jobs=-1
    ),

    "RANDOM_FOREST_REGRESSOR": RandomForestRegressor(
        n_estimators=400,
        min_samples_leaf=2,
        max_features=0.8,
        random_state=42,
        n_jobs=-1
    )
}

trained_regressors = {}
regression_results = []

for name, model in regressors.items():

    print(f"\nTraining: {name}")

    # PREPROCESSOR BARU KHUSUS REGRESI
    pipe = Pipeline([
        ("preprocessor", make_preprocessor()),
        ("model", model)
    ])

    pipe.fit(
        X_positive_train,
        y_positive_train
    )

    prediction = np.maximum(
        pipe.predict(X_positive_test),
        0
    )

    result = {
        "MODEL": name,
        "POSITIVE_TEST_SIZE": len(positive_test),
        "MAE_POSITIVE": mean_absolute_error(
            y_positive_test,
            prediction
        ),
        "RMSE_POSITIVE": np.sqrt(
            mean_squared_error(
                y_positive_test,
                prediction
            )
        ),
        "R2_POSITIVE": (
            r2_score(
                y_positive_test,
                prediction
            )
            if y_positive_test.nunique() > 1
            else np.nan
        )
    }

    regression_results.append(result)
    trained_regressors[name] = pipe

    joblib.dump(
        pipe,
        MODELS / f"{name.lower()}.joblib"
    )

    print(
        f"MAE: {result['MAE_POSITIVE']:.4f} | "
        f"RMSE: {result['RMSE_POSITIVE']:.4f} | "
        f"R2: {result['R2_POSITIVE']:.4f}"
    )

# ==========================================================
# 6. EVALUASI TWO-STAGE GABUNGAN
# ==========================================================

print("\n[5] EVALUASI TWO-STAGE GABUNGAN...")

actual = test["WBC_AFFECTED_HA"].to_numpy()

combined_results = []
prediction_frames = []

for cname, classifier in trained_classifiers.items():

    probability = classifier.predict_proba(
        X_test
    )[:, 1]

    for rname, regressor in trained_regressors.items():

        conditional_prediction = np.maximum(
            regressor.predict(X_test),
            0
        )

        expected_prediction = (
            probability * conditional_prediction
        )

        result = {
            "CLASSIFIER": cname,
            "REGRESSOR": rname,
            "TEST_SIZE": len(test),
            "MAE_ALL": mean_absolute_error(
                actual,
                expected_prediction
            ),
            "RMSE_ALL": np.sqrt(
                mean_squared_error(
                    actual,
                    expected_prediction
                )
            ),
            "R2_ALL": (
                r2_score(
                    actual,
                    expected_prediction
                )
                if len(test) > 1
                else np.nan
            )
        }

        combined_results.append(result)

        prediction_frames.append(
            pd.DataFrame({
                "REGION_KEY": test["REGION_KEY"].values,
                "YEAR": test["YEAR"].values,
                "MONTH": test["MONTH"].values,
                "ACTUAL_HA": actual,
                "PROBABILITY": probability,
                "CONDITIONAL_HA": conditional_prediction,
                "EXPECTED_HA": expected_prediction,
                "CLASSIFIER": cname,
                "REGRESSOR": rname
            })
        )

# ==========================================================
# 7. MENYIMPAN HASIL
# ==========================================================

print("\n[6] MENYIMPAN HASIL...")

classification_df = pd.DataFrame(
    classification_results
)

regression_df = pd.DataFrame(
    regression_results
)

combined_df = pd.DataFrame(
    combined_results
)

predictions_df = pd.concat(
    prediction_frames,
    ignore_index=True
)

classification_df.to_csv(
    DATA / "wbc_two_stage_classification_metrics.csv",
    index=False
)

regression_df.to_csv(
    DATA / "wbc_two_stage_regression_metrics.csv",
    index=False
)

combined_df.to_csv(
    DATA / "wbc_two_stage_combined_metrics.csv",
    index=False
)

predictions_df.to_csv(
    DATA / "wbc_two_stage_predictions.csv",
    index=False
)

# ==========================================================
# 8. AUDIT
# ==========================================================

audit = []

audit.append(
    "PESTCYCLE AI - TWO STAGE MODEL AUDIT"
)

audit.append("=" * 70)

audit.append(f"Total data: {len(df)}")
audit.append(f"TRAIN: {len(train)}")
audit.append(f"TEST: {len(test)}")

audit.append(
    f"Positive TRAIN: {len(positive_train)}"
)

audit.append(
    f"Positive TEST: {len(positive_test)}"
)

audit.append("\nCLASSIFICATION")
audit.append(classification_df.to_string(index=False))

audit.append("\nREGRESSION")
audit.append(regression_df.to_string(index=False))

audit.append("\nCOMBINED")
audit.append(combined_df.to_string(index=False))

audit.append(
    "\nCatatan: Evaluasi ini masih eksploratif."
)

audit.append(
    "Model belum dinyatakan siap produksi."
)

audit.append(
    "EXPECTED_HA = probabilitas serangan x luas "
    "serangan bersyarat."
)

(DATA / "wbc_two_stage_audit.txt").write_text(
    "\n".join(audit),
    encoding="utf-8"
)

# ==========================================================
# 9. HASIL AKHIR
# ==========================================================

print("\n" + "=" * 70)
print("HASIL CLASSIFICATION")
print("=" * 70)

print(classification_df.to_string(index=False))

print("\n" + "=" * 70)
print("HASIL REGRESSION")
print("=" * 70)

print(regression_df.to_string(index=False))

print("\n" + "=" * 70)
print("HASIL TWO-STAGE GABUNGAN")
print("=" * 70)

print(combined_df.to_string(index=False))

print("\nFILE OUTPUT:")

print(DATA / "wbc_two_stage_classification_metrics.csv")
print(DATA / "wbc_two_stage_regression_metrics.csv")
print(DATA / "wbc_two_stage_combined_metrics.csv")
print(DATA / "wbc_two_stage_predictions.csv")
print(DATA / "wbc_two_stage_audit.txt")

print(MODELS)

print("\nTWO-STAGE TRAINING SELESAI")
print("=" * 70)
