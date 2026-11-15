
import pandas as pd
import numpy as np
from pathlib import Path

# ============================================================
# PESTCYCLE AI
# DIAGNOSTIK KESALAHAN PREDIKSI WBC
# ============================================================

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"

INPUT_FILE = DATA_DIR / "wbc_model_predictions_2026.csv"

OUTPUT_METRICS = DATA_DIR / "wbc_prediction_diagnostic_metrics.csv"
OUTPUT_MONTHLY = DATA_DIR / "wbc_prediction_diagnostic_monthly.csv"
OUTPUT_REGION = DATA_DIR / "wbc_prediction_diagnostic_region.csv"
OUTPUT_ERRORS = DATA_DIR / "wbc_prediction_largest_errors.csv"
OUTPUT_AUDIT = DATA_DIR / "wbc_prediction_diagnostic_audit.txt"

print("=" * 70)
print("PESTCYCLE AI - DIAGNOSTIK PREDIKSI WBC")
print("=" * 70)

# ------------------------------------------------------------
# 1. MEMBACA DATA
# ------------------------------------------------------------

df = pd.read_csv(INPUT_FILE)

required = [
    "TARGET", "MODEL", "ACTUAL",
    "PREDICTED", "MONTH"
]

missing = [c for c in required if c not in df.columns]

if missing:
    raise ValueError(f"Kolom wajib tidak tersedia: {missing}")

if "REGION_KEY" not in df.columns:
    raise ValueError("Kolom REGION_KEY tidak ditemukan.")

for col in ["ACTUAL", "PREDICTED", "MONTH"]:
    df[col] = pd.to_numeric(df[col], errors="coerce")

if df[["ACTUAL", "PREDICTED", "MONTH"]].isna().any().any():
    raise ValueError("Terdapat nilai kosong pada kolom evaluasi.")

df["ABS_ERROR"] = (
    df["ACTUAL"] - df["PREDICTED"]
).abs()

df["ERROR"] = (
    df["PREDICTED"] - df["ACTUAL"]
)

df["ACTUAL_NONZERO"] = df["ACTUAL"] > 0
df["PREDICTED_NONZERO"] = df["PREDICTED"] > 0

print("\n[1] STRUKTUR DATA")
print("Jumlah baris:", len(df))
print("Jumlah target:", df["TARGET"].nunique())
print("Jumlah model:", df["MODEL"].nunique())
print("Jumlah wilayah:", df["REGION_KEY"].nunique())

# ------------------------------------------------------------
# 2. METRIK EVALUASI
# ------------------------------------------------------------

def calculate_metrics(group):

    actual = group["ACTUAL"].to_numpy()
    predicted = group["PREDICTED"].to_numpy()

    error = predicted - actual

    mae = np.mean(np.abs(error))
    rmse = np.sqrt(np.mean(error ** 2))

    denominator = np.sum(
        (actual - np.mean(actual)) ** 2
    )

    r2 = (
        1 - np.sum(error ** 2) / denominator
        if denominator > 0 else np.nan
    )

    actual_positive = actual > 0
    predicted_positive = predicted > 0

    tp = np.sum(actual_positive & predicted_positive)
    fp = np.sum(~actual_positive & predicted_positive)
    fn = np.sum(actual_positive & ~predicted_positive)

    precision = tp / (tp + fp) if tp + fp else 0
    recall = tp / (tp + fn) if tp + fn else 0

    f1 = (
        2 * precision * recall / (precision + recall)
        if precision + recall else 0
    )

    positive_mae = (
        np.mean(np.abs(error[actual_positive]))
        if actual_positive.any() else np.nan
    )

    return pd.Series({
        "SAMPLE_SIZE": len(actual),
        "ACTUAL_TOTAL": actual.sum(),
        "PREDICTED_TOTAL": predicted.sum(),
        "MAE": mae,
        "RMSE": rmse,
        "R2": r2,
        "BIAS": np.mean(error),
        "ZERO_ACTUAL": np.sum(~actual_positive),
        "NONZERO_ACTUAL": np.sum(actual_positive),
        "TRUE_POSITIVE": tp,
        "FALSE_POSITIVE": fp,
        "FALSE_NEGATIVE": fn,
        "PRECISION": precision,
        "RECALL": recall,
        "F1_SCORE": f1,
        "POSITIVE_ONLY_MAE": positive_mae
    })


# ------------------------------------------------------------
# 3. EVALUASI SETIAP MODEL
# ------------------------------------------------------------

print("\n[2] EVALUASI SETIAP MODEL")

metrics = (
    df.groupby(["TARGET", "MODEL"])
    .apply(calculate_metrics, include_groups=False)
    .reset_index()
)

print(metrics.to_string(index=False))

metrics.to_csv(
    OUTPUT_METRICS,
    index=False,
    encoding="utf-8-sig"
)

# ------------------------------------------------------------
# 4. EVALUASI PER BULAN
# ------------------------------------------------------------

print("\n[3] EVALUASI PER BULAN")

monthly = (
    df.groupby(["TARGET", "MODEL", "MONTH"])
    .apply(calculate_metrics, include_groups=False)
    .reset_index()
)

print(monthly.to_string(index=False))

monthly.to_csv(
    OUTPUT_MONTHLY,
    index=False,
    encoding="utf-8-sig"
)

# ------------------------------------------------------------
# 5. EVALUASI PER WILAYAH
# ------------------------------------------------------------

print("\n[4] EVALUASI PER WILAYAH")

region = (
    df.groupby(["TARGET", "MODEL", "REGION_KEY"])
    .apply(calculate_metrics, include_groups=False)
    .reset_index()
)

print(region.sort_values(
    ["TARGET", "MODEL", "MAE"],
    ascending=[True, True, False]
).head(30).to_string(index=False))

region.to_csv(
    OUTPUT_REGION,
    index=False,
    encoding="utf-8-sig"
)

# ------------------------------------------------------------
# 6. KESALAHAN TERBESAR
# ------------------------------------------------------------

print("\n[5] 30 KESALAHAN PREDIKSI TERBESAR")

detail_columns = [
    "TARGET", "MODEL", "REGION_KEY",
    "MONTH", "ACTUAL", "PREDICTED",
    "ERROR", "ABS_ERROR"
]

errors = df.sort_values(
    "ABS_ERROR",
    ascending=False
)

errors[detail_columns].head(30).to_csv(
    OUTPUT_ERRORS,
    index=False,
    encoding="utf-8-sig"
)

print(errors[detail_columns].head(30).to_string(index=False))

# ------------------------------------------------------------
# 7. VALIDASI KONSISTENSI
# ------------------------------------------------------------

print("\n[6] VALIDASI")

print("Prediksi negatif:", (df["PREDICTED"] < 0).sum())
print("Aktual negatif:", (df["ACTUAL"] < 0).sum())
print("Duplikasi:", df.duplicated(
    ["TARGET", "MODEL", "REGION_KEY", "MONTH"]
).sum())

# ------------------------------------------------------------
# 8. LAPORAN AUDIT
# ------------------------------------------------------------

lines = [
    "=" * 70,
    "PESTCYCLE AI - PREDICTION DIAGNOSTIC REPORT",
    "=" * 70,
    f"Total prediksi: {len(df)}",
    f"Wilayah: {df['REGION_KEY'].nunique()}",
    f"Model: {df['MODEL'].nunique()}",
    f"Target: {df['TARGET'].nunique()}",
    "",
    "HASIL EVALUASI MODEL:",
    metrics.to_string(index=False),
    "",
    "PREDIKSI NEGATIF:",
    str((df["PREDICTED"] < 0).sum()),
    "",
    "DUPLIKASI:",
    str(df.duplicated(
        ["TARGET", "MODEL", "REGION_KEY", "MONTH"]
    ).sum()),
    "",
    "=" * 70,
    "DIAGNOSTIK SELESAI",
    "=" * 70
]

OUTPUT_AUDIT.write_text(
    "\n".join(lines),
    encoding="utf-8"
)

print("\nFILE OUTPUT:")
for path in [
    OUTPUT_METRICS,
    OUTPUT_MONTHLY,
    OUTPUT_REGION,
    OUTPUT_ERRORS,
    OUTPUT_AUDIT
]:
    print(path)

print("\nDIAGNOSTIK PREDIKSI WBC SELESAI")

