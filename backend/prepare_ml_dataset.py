
import pandas as pd
import numpy as np

from pathlib import Path

# ============================================================
# PESTCYCLE AI
# NEXT-MONTH WBC PREDICTION DATASET
# FEATURE ENGINEERING
# ============================================================

BASE = Path(__file__).resolve().parents[1]
DATA = BASE / "data"

INPUT = DATA / "nasa_wbc_monthly_integrated_2026.csv"

OUTPUT = DATA / "wbc_next_month_ml_dataset_2026.csv"
AUDIT = DATA / "ml_feature_engineering_audit.txt"

WEATHER_FEATURES = [
    "T2M_MEAN",
    "T2M_MAX",
    "T2M_MIN",
    "RH2M_MEAN",
    "PRECTOTCORR_SUM",
    "WEATHER_DAYS"
]

TARGETS = [
    "WBC_AFFECTED_HA",
    "WBC_PUSO_HA"
]

print("=" * 70)
print("PESTCYCLE AI - FEATURE ENGINEERING")
print("=" * 70)

# ------------------------------------------------------------
# 1. BACA DATA
# ------------------------------------------------------------

print("\n[1] MEMBACA DATASET...")

if not INPUT.exists():
    raise FileNotFoundError(INPUT)

df = pd.read_csv(INPUT)

required = [
    "REGION_KEY",
    "YEAR",
    "MONTH"
] + WEATHER_FEATURES + TARGETS

missing = [
    col for col in required
    if col not in df.columns
]

if missing:
    raise ValueError(
        f"Kolom tidak ditemukan: {missing}"
    )

df["REGION_KEY"] = (
    df["REGION_KEY"]
    .astype(str)
    .str.strip()
    .str.upper()
)

for col in required:
    if col != "REGION_KEY":
        df[col] = pd.to_numeric(
            df[col],
            errors="coerce"
        )

df = df.sort_values(
    ["REGION_KEY", "YEAR", "MONTH"]
).reset_index(drop=True)

print("Baris sumber:", len(df))
print("Wilayah:", df["REGION_KEY"].nunique())

# ------------------------------------------------------------
# 2. VALIDASI URUTAN WAKTU
# ------------------------------------------------------------

print("\n[2] VALIDASI URUTAN WAKTU...")

if df.duplicated(
    ["REGION_KEY", "YEAR", "MONTH"]
).any():
    raise ValueError("Ditemukan duplikasi wilayah-bulan.")

period = (
    df["YEAR"] * 12
    + df["MONTH"]
)

df["_PERIOD"] = period

# ------------------------------------------------------------
# 3. MEMBENTUK FITUR CUACA LAG 1
# ------------------------------------------------------------

print("\n[3] MEMBENTUK FITUR CUACA LAG 1...")

for col in WEATHER_FEATURES:

    df[col + "_LAG1"] = (
        df.groupby("REGION_KEY")[col]
        .shift(1)
    )

# ------------------------------------------------------------
# 4. MEMBENTUK FITUR HISTORIS WBC
# ------------------------------------------------------------

print("\n[4] MEMBENTUK FITUR HISTORIS WBC...")

for col in TARGETS:

    df[col + "_LAG1"] = (
        df.groupby("REGION_KEY")[col]
        .shift(1)
    )

# ------------------------------------------------------------
# 5. VALIDASI KONTINUITAS BULAN
# ------------------------------------------------------------

print("\n[5] VALIDASI KONTINUITAS WAKTU...")

df["_PREV_PERIOD"] = (
    df.groupby("REGION_KEY")["_PERIOD"]
    .shift(1)
)

df["_MONTH_GAP"] = (
    df["_PERIOD"] - df["_PREV_PERIOD"]
)

# Hanya menggunakan pasangan bulan berurutan.
df = df[df["_MONTH_GAP"] == 1].copy()

# ------------------------------------------------------------
# 6. FITUR MUSIMAN
# ------------------------------------------------------------

print("\n[6] MEMBENTUK FITUR MUSIMAN...")

df["MONTH_SIN"] = np.sin(
    2 * np.pi * df["MONTH"] / 12
)

df["MONTH_COS"] = np.cos(
    2 * np.pi * df["MONTH"] / 12
)

# ------------------------------------------------------------
# 7. MENYIAPKAN DATASET FINAL
# ------------------------------------------------------------

print("\n[7] MENYUSUN DATASET FINAL...")

feature_columns = (
    ["REGION_KEY", "YEAR", "MONTH",
     "MONTH_SIN", "MONTH_COS"]
    + [col + "_LAG1" for col in WEATHER_FEATURES]
    + [col + "_LAG1" for col in TARGETS]
)

final_columns = (
    feature_columns
    + TARGETS
)

ml_df = df[final_columns].copy()

# ------------------------------------------------------------
# 8. VALIDASI DATASET
# ------------------------------------------------------------

print("\n[8] VALIDASI DATASET...")

if ml_df.empty:
    raise ValueError("Dataset ML kosong.")

if ml_df.isna().any().any():
    raise ValueError(
        "Masih ditemukan nilai kosong dalam dataset ML."
    )

if not (ml_df[TARGETS] >= 0).all().all():
    raise ValueError("Ditemukan target negatif.")

if ml_df.duplicated(
    ["REGION_KEY", "YEAR", "MONTH"]
).any():
    raise ValueError("Ditemukan duplikasi.")

# ------------------------------------------------------------
# 9. PEMBAGIAN TEMPORAL
# ------------------------------------------------------------

print("\n[9] PEMBAGIAN DATA TRAIN DAN TEST...")

# Februari-Juli untuk pelatihan.
# Agustus-Oktober untuk pengujian temporal.

ml_df["DATA_SPLIT"] = np.where(
    ml_df["MONTH"] <= 7,
    "TRAIN",
    "TEST"
)

# ------------------------------------------------------------
# 10. SIMPAN DATASET
# ------------------------------------------------------------

ml_df.to_csv(
    OUTPUT,
    index=False,
    encoding="utf-8-sig"
)

# ------------------------------------------------------------
# 11. LAPORAN AUDIT
# ------------------------------------------------------------

train = ml_df[
    ml_df["DATA_SPLIT"] == "TRAIN"
]

test = ml_df[
    ml_df["DATA_SPLIT"] == "TEST"
]

report = [
    "=" * 70,
    "PESTCYCLE AI - FEATURE ENGINEERING AUDIT",
    "=" * 70,
    "",
    f"Jumlah observasi sumber: {len(period)}",
    f"Jumlah observasi ML: {len(ml_df)}",
    f"Jumlah wilayah: {ml_df['REGION_KEY'].nunique()}",
    f"Jumlah fitur prediktor: {len(feature_columns)}",
    "",
    "PERIODE TARGET:",
    f"{ml_df['YEAR'].min()} - {ml_df['YEAR'].max()}",
    "",
    "PEMBAGIAN DATA:",
    f"TRAIN: {len(train)} observasi",
    f"TEST: {len(test)} observasi",
    "",
    "TARGET:",
    *[
        f"{col}: mean={ml_df[col].mean():.4f}, "
        f"max={ml_df[col].max():.4f}, "
        f"zero={(ml_df[col] == 0).sum()}"
        for col in TARGETS
    ],
    "",
    "FITUR:",
    *feature_columns,
    "",
    "VALIDASI:",
    f"Duplikasi: {ml_df.duplicated(['REGION_KEY', 'YEAR', 'MONTH']).sum()}",
    f"Nilai kosong: {ml_df.isna().sum().sum()}",
    "",
    "CATATAN:",
    "- Cuaca bulan sebelumnya digunakan sebagai prediktor.",
    "- WBC bulan sebelumnya digunakan sebagai fitur historis.",
    "- Target adalah serangan WBC bulan berjalan.",
    "- Pembagian TRAIN dan TEST berdasarkan waktu.",
    "- DATA TEST tidak digunakan untuk pelatihan.",
    "- Hasil ini merupakan dataset eksperimental.",
    "- Belum dapat dianggap validasi lintas tahun.",
    "",
    "FILE OUTPUT:",
    str(OUTPUT),
    str(AUDIT),
    "",
    "=" * 70,
    "FEATURE ENGINEERING SELESAI",
    "=" * 70
]

AUDIT.write_text(
    "\n".join(report),
    encoding="utf-8"
)

# ------------------------------------------------------------
# 12. TAMPILKAN HASIL
# ------------------------------------------------------------

print("\n" + "=" * 70)
print("HASIL DATASET MACHINE LEARNING")
print("=" * 70)

print("Jumlah observasi:", len(ml_df))
print("Jumlah wilayah:", ml_df["REGION_KEY"].nunique())
print("Jumlah fitur:", len(feature_columns))

print("\nTRAIN:")
print("Observasi:", len(train))

print("\nTEST:")
print("Observasi:", len(test))

print("\nDistribusi target:")
print(
    ml_df[TARGETS].describe().to_string()
)

print("\nContoh dataset:")
print(ml_df.head(10).to_string(index=False))

print("\nFILE OUTPUT:")
print(OUTPUT)
print(AUDIT)

print("\nFEATURE ENGINEERING BERHASIL")
print("=" * 70)
