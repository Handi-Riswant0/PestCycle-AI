
import pandas as pd
import numpy as np

from pathlib import Path
from scipy.stats import spearmanr

# ============================================================
# PESTCYCLE AI
# MACHINE LEARNING READINESS DIAGNOSTICS
# NASA POWER + WBC
# 38 KABUPATEN/KOTA JAWA TIMUR
# ============================================================

BASE = Path(__file__).resolve().parents[1]
DATA = BASE / "data"

INPUT_FILE = DATA / "nasa_wbc_monthly_integrated_2026.csv"

OUTPUT_REPORT = DATA / "ml_readiness_report.txt"
OUTPUT_FEATURE = DATA / "ml_feature_audit.csv"
OUTPUT_TARGET = DATA / "ml_target_distribution.csv"
OUTPUT_REGION = DATA / "ml_region_coverage.csv"
OUTPUT_CORRELATION = DATA / "ml_feature_correlation.csv"
OUTPUT_LAG = DATA / "ml_lag_readiness.csv"

EXPECTED_REGIONS = 38
EXPECTED_MONTHS = 10

TARGETS = [
    "WBC_AFFECTED_HA",
    "WBC_PUSO_HA"
]

WEATHER_FEATURES = [
    "T2M_MEAN",
    "T2M_MAX",
    "T2M_MIN",
    "RH2M_MEAN",
    "PRECTOTCORR_SUM",
    "WEATHER_DAYS"
]

REQUIRED_COLUMNS = [
    "REGION_KEY",
    "YEAR",
    "MONTH",
    "WBC_AFFECTED_HA",
    "WBC_PUSO_HA"
] + WEATHER_FEATURES

print("=" * 70)
print("PESTCYCLE AI - MACHINE LEARNING READINESS")
print("=" * 70)

# ------------------------------------------------------------
# 1. MEMBACA DATASET
# ------------------------------------------------------------

print("\n[1] MEMBACA DATASET...")

if not INPUT_FILE.exists():
    raise FileNotFoundError(
        f"Dataset tidak ditemukan: {INPUT_FILE}"
    )

df = pd.read_csv(INPUT_FILE)

print("File:", INPUT_FILE.name)
print("Jumlah baris:", len(df))
print("Jumlah kolom:", len(df.columns))

# ------------------------------------------------------------
# 2. VALIDASI STRUKTUR
# ------------------------------------------------------------

print("\n[2] VALIDASI STRUKTUR DATA...")

missing_columns = [
    col for col in REQUIRED_COLUMNS
    if col not in df.columns
]

if missing_columns:
    raise ValueError(
        f"Kolom wajib tidak ditemukan: {missing_columns}"
    )

df["REGION_KEY"] = (
    df["REGION_KEY"]
    .astype(str)
    .str.strip()
    .str.upper()
)

for col in REQUIRED_COLUMNS:
    if col not in ["REGION_KEY"]:
        df[col] = pd.to_numeric(
            df[col],
            errors="coerce"
        )

df = df.sort_values(
    ["REGION_KEY", "YEAR", "MONTH"]
).reset_index(drop=True)

# ------------------------------------------------------------
# 3. VALIDASI WILAYAH DAN PERIODE
# ------------------------------------------------------------

print("\n[3] VALIDASI WILAYAH DAN PERIODE...")

region_count = df["REGION_KEY"].nunique()

month_count = (
    df[["YEAR", "MONTH"]]
    .drop_duplicates()
    .shape[0]
)

expected_rows = region_count * month_count

print("Jumlah wilayah:", region_count)
print("Jumlah kombinasi bulan:", month_count)
print("Jumlah baris ideal:", expected_rows)
print("Jumlah baris aktual:", len(df))

if region_count != EXPECTED_REGIONS:
    print("PERINGATAN: Jumlah wilayah tidak sesuai.")

if len(df) != expected_rows:
    print("PERINGATAN: Struktur panel tidak lengkap.")

# ------------------------------------------------------------
# 4. PEMERIKSAAN DUPLIKASI
# ------------------------------------------------------------

print("\n[4] PEMERIKSAAN DUPLIKASI...")

duplicate_count = df.duplicated(
    subset=["REGION_KEY", "YEAR", "MONTH"]
).sum()

print("Duplikasi wilayah-bulan:", duplicate_count)

# ------------------------------------------------------------
# 5. PEMERIKSAAN DATA KOSONG
# ------------------------------------------------------------

print("\n[5] PEMERIKSAAN DATA KOSONG...")

missing_report = df[REQUIRED_COLUMNS].isna().sum()

print(missing_report.to_string())

total_missing = int(missing_report.sum())

print("Total nilai kosong:", total_missing)

# ------------------------------------------------------------
# 6. AUDIT FITUR MACHINE LEARNING
# ------------------------------------------------------------

print("\n[6] AUDIT FITUR MACHINE LEARNING...")

feature_rows = []

for col in WEATHER_FEATURES:

    values = df[col].dropna()

    feature_rows.append({
        "FEATURE": col,
        "TOTAL": len(df),
        "VALID": len(values),
        "MISSING": int(df[col].isna().sum()),
        "UNIQUE_VALUES": int(values.nunique()),
        "MIN": values.min() if len(values) else np.nan,
        "MAX": values.max() if len(values) else np.nan,
        "MEAN": values.mean() if len(values) else np.nan,
        "STD": values.std() if len(values) else np.nan,
        "ZERO_PERCENT": (
            (values == 0).mean() * 100
            if len(values) else np.nan
        )
    })

feature_df = pd.DataFrame(feature_rows)

feature_df.to_csv(
    OUTPUT_FEATURE,
    index=False,
    encoding="utf-8-sig"
)

print(feature_df.to_string(index=False))

# ------------------------------------------------------------
# 7. AUDIT TARGET WBC
# ------------------------------------------------------------

print("\n[7] DISTRIBUSI TARGET WBC...")

target_rows = []

for target in TARGETS:

    values = df[target].dropna()

    zero_count = int((values == 0).sum())

    target_rows.append({
        "TARGET": target,
        "TOTAL": len(df),
        "MISSING": int(df[target].isna().sum()),
        "ZERO_COUNT": zero_count,
        "ZERO_PERCENT": (
            zero_count / len(values) * 100
            if len(values) else np.nan
        ),
        "NONZERO_COUNT": int((values > 0).sum()),
        "NONZERO_PERCENT": (
            (values > 0).mean() * 100
            if len(values) else np.nan
        ),
        "MIN": values.min() if len(values) else np.nan,
        "MAX": values.max() if len(values) else np.nan,
        "MEAN": values.mean() if len(values) else np.nan,
        "MEDIAN": values.median() if len(values) else np.nan,
        "STD": values.std() if len(values) else np.nan
    })

target_df = pd.DataFrame(target_rows)

target_df.to_csv(
    OUTPUT_TARGET,
    index=False,
    encoding="utf-8-sig"
)

print(target_df.to_string(index=False))

# ------------------------------------------------------------
# 8. AUDIT KELENGKAPAN PER WILAYAH
# ------------------------------------------------------------

print("\n[8] KELENGKAPAN DATA PER WILAYAH...")

region_df = (
    df.groupby("REGION_KEY")
    .agg(
        TOTAL_RECORDS=("MONTH", "count"),
        FIRST_YEAR=("YEAR", "min"),
        LAST_YEAR=("YEAR", "max"),
        FIRST_MONTH=("MONTH", "min"),
        LAST_MONTH=("MONTH", "max"),
        TOTAL_AFFECTED=("WBC_AFFECTED_HA", "sum"),
        TOTAL_PUSO=("WBC_PUSO_HA", "sum"),
        NONZERO_MONTHS=(
            "WBC_AFFECTED_HA",
            lambda x: int((x > 0).sum())
        )
    )
    .reset_index()
)

region_df["EXPECTED_RECORDS"] = month_count

region_df["COMPLETE"] = (
    region_df["TOTAL_RECORDS"]
    == region_df["EXPECTED_RECORDS"]
)

region_df.to_csv(
    OUTPUT_REGION,
    index=False,
    encoding="utf-8-sig"
)

print(region_df.to_string(index=False))

# ------------------------------------------------------------
# 9. KORELASI SPEARMAN
# CATATAN: KORELASI DIAGNOSTIK, BUKAN BUKTI KAUSALITAS
# ------------------------------------------------------------

print("\n[9] ANALISIS KORELASI FITUR DAN TARGET...")

correlation_rows = []

for feature in WEATHER_FEATURES:

    for target in TARGETS:

        subset = df[
            [feature, target]
        ].dropna()

        if (
            len(subset) < 3
            or subset[feature].nunique() < 2
            or subset[target].nunique() < 2
        ):
            rho = np.nan
            pvalue = np.nan
        else:
            result = spearmanr(
                subset[feature],
                subset[target]
            )

            rho = result.statistic
            pvalue = result.pvalue

        correlation_rows.append({
            "FEATURE": feature,
            "TARGET": target,
            "SAMPLE_SIZE": len(subset),
            "SPEARMAN_RHO": rho,
            "P_VALUE": pvalue
        })

correlation_df = pd.DataFrame(correlation_rows)

correlation_df.to_csv(
    OUTPUT_CORRELATION,
    index=False,
    encoding="utf-8-sig"
)

print(correlation_df.to_string(index=False))

# ------------------------------------------------------------
# 10. AUDIT TIME LAG
# ------------------------------------------------------------

print("\n[10] PEMERIKSAAN TIME LAG...")

lag_rows = []

for col in WEATHER_FEATURES + TARGETS:

    lag_name = col + "_LAG1"

    df[lag_name] = (
        df.groupby("REGION_KEY")[col]
        .shift(1)
    )

    lag_rows.append({
        "VARIABLE": col,
        "TOTAL_RECORDS": len(df),
        "LAG_AVAILABLE": int(df[lag_name].notna().sum()),
        "LAG_MISSING": int(df[lag_name].isna().sum()),
        "LAG_AVAILABILITY_PERCENT": (
            df[lag_name].notna().mean() * 100
        )
    })

lag_df = pd.DataFrame(lag_rows)

lag_df.to_csv(
    OUTPUT_LAG,
    index=False,
    encoding="utf-8-sig"
)

print(lag_df.to_string(index=False))

# ------------------------------------------------------------
# 11. PEMERIKSAAN KEBocORAN DATA
# ------------------------------------------------------------

print("\n[11] PEMERIKSAAN DATA LEAKAGE...")

print(
    "Target utama:",
    ", ".join(TARGETS)
)

print(
    "Fitur cuaca:",
    ", ".join(WEATHER_FEATURES)
)

print(
    "Fitur target bulan berjalan TIDAK boleh "
    "digunakan sebagai input untuk memprediksi "
    "target bulan yang sama."
)

print(
    "Fitur WBC_LAG1 hanya boleh digunakan jika "
    "data WBC bulan sebelumnya sudah tersedia "
    "pada waktu prediksi."
)

# ------------------------------------------------------------
# 12. STATUS KESIAPAN DATASET
# ------------------------------------------------------------

print("\n[12] MENENTUKAN STATUS KESIAPAN...")

target_nonzero = (
    target_df["NONZERO_COUNT"] > 0
).all()

feature_variation = (
    feature_df["UNIQUE_VALUES"] > 1
).all()

region_complete = region_df["COMPLETE"].all()

no_duplicates = duplicate_count == 0

no_missing_core = total_missing == 0

checks = {
    "38 wilayah": region_count == EXPECTED_REGIONS,
    "Panel lengkap": len(df) == expected_rows,
    "Tidak ada duplikasi": no_duplicates,
    "Tidak ada data kosong": no_missing_core,
    "Target memiliki variasi": target_nonzero,
    "Fitur cuaca bervariasi": feature_variation,
    "Cakupan setiap wilayah lengkap": region_complete
}

for name, passed in checks.items():
    print(
        f"{name}: {'LULUS' if passed else 'PERLU PERBAIKAN'}"
    )

ready = all(checks.values())

if ready:
    status = (
        "LOLOS AUDIT STRUKTUR AWAL - "
        "BELUM BERARTI SIAP PRODUKSI ML"
    )
else:
    status = "BELUM LOLOS AUDIT STRUKTUR AWAL"

# ------------------------------------------------------------
# 13. MENYIMPAN LAPORAN
# ------------------------------------------------------------

report = [
    "=" * 70,
    "PESTCYCLE AI - MACHINE LEARNING READINESS REPORT",
    "=" * 70,
    "",
    f"File sumber: {INPUT_FILE.name}",
    f"Jumlah baris: {len(df)}",
    f"Jumlah kolom: {len(df.columns)}",
    f"Jumlah wilayah: {region_count}",
    f"Jumlah kombinasi bulan: {month_count}",
    f"Duplikasi: {duplicate_count}",
    f"Nilai kosong kolom wajib: {total_missing}",
    "",
    "AUDIT KESIAPAN:",
    ""
]

for name, passed in checks.items():
    report.append(
        f"{name}: {'LULUS' if passed else 'PERLU PERBAIKAN'}"
    )

report.extend([
    "",
    "STATUS AKHIR:",
    status,
    "",
    "BATASAN DATA:",
    "- Data aktual WBC yang diperiksa berasal dari 2026.",
    "- Periode yang tersedia adalah Januari-Oktober 2026.",
    "- Jumlah observasi hanya 380.",
    "- Data prakiraan BBPOPT tidak dianggap sebagai aktual.",
    "- Korelasi tidak membuktikan hubungan sebab-akibat.",
    "- Audit ini belum merupakan validasi model prediksi.",
    "",
    "FILE OUTPUT:",
    str(OUTPUT_FEATURE),
    str(OUTPUT_TARGET),
    str(OUTPUT_REGION),
    str(OUTPUT_CORRELATION),
    str(OUTPUT_LAG),
    str(OUTPUT_REPORT),
    "",
    "=" * 70,
    "DIAGNOSTIC SELESAI",
    "=" * 70
])

OUTPUT_REPORT.write_text(
    "\n".join(report),
    encoding="utf-8"
)

print("\n" + "=" * 70)
print("STATUS AKHIR:")
print(status)
print("=" * 70)

print("\nLAPORAN TERSIMPAN:")
print(OUTPUT_REPORT)

print("\nML READINESS DIAGNOSTIC SELESAI")
