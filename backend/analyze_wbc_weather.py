
import pandas as pd
import numpy as np
from pathlib import Path

# ============================================================
# PESTCYCLE AI
# ANALISIS HUBUNGAN CUACA DAN SERANGAN WBC
# JAWA TIMUR - 2026
# ============================================================

BASE = Path(__file__).resolve().parents[1]
DATA = BASE / "data"

INPUT = DATA / "nasa_wbc_monthly_integrated_2026.csv"

OUTPUT_CORR = DATA / "wbc_weather_correlation_2026.csv"
OUTPUT_REGION = DATA / "wbc_weather_correlation_by_region.csv"
OUTPUT_LAG = DATA / "wbc_weather_lag_analysis_2026.csv"
OUTPUT_DATA = DATA / "wbc_weather_analysis_dataset_2026.csv"
OUTPUT_AUDIT = DATA / "wbc_weather_analysis_audit.txt"

print("=" * 70)
print("PESTCYCLE AI - ANALISIS CUACA DAN SERANGAN WBC")
print("=" * 70)

# ------------------------------------------------------------
# 1. MEMBACA DATA
# ------------------------------------------------------------

print("\n[1] Membaca dataset...")

df = pd.read_csv(INPUT)

print("Jumlah data:", len(df))
print("Jumlah wilayah:", df["REGION_KEY"].nunique())

# ------------------------------------------------------------
# 2. VALIDASI
# ------------------------------------------------------------

print("\n[2] Validasi dataset...")

weather_vars = [
    "T2M_MEAN",
    "T2M_MAX",
    "T2M_MIN",
    "RH2M_MEAN",
    "PRECTOTCORR_SUM"
]

target_vars = [
    "WBC_AFFECTED_HA",
    "WBC_PUSO_HA"
]

required = weather_vars + target_vars + [
    "REGION_KEY", "YEAR", "MONTH"
]

for col in required:
    if col not in df.columns:
        raise ValueError(f"Kolom tidak ditemukan: {col}")

if df[required].isna().any().any():
    raise ValueError("Terdapat nilai kosong.")

df = df.sort_values(
    ["REGION_KEY", "YEAR", "MONTH"]
).reset_index(drop=True)

# ------------------------------------------------------------
# 3. MEMBUAT FITUR TIME LAG
# ------------------------------------------------------------

print("\n[3] Membentuk fitur time lag...")

for col in weather_vars:
    df[f"{col}_LAG1"] = (
        df.groupby("REGION_KEY")[col].shift(1)
    )

# Cuaca bulan sebelumnya akan dibandingkan
# dengan kejadian WBC bulan berjalan.

lag_vars = [f"{col}_LAG1" for col in weather_vars]

df.to_csv(
    OUTPUT_DATA,
    index=False,
    encoding="utf-8-sig"
)

# ------------------------------------------------------------
# 4. KORELASI SPEARMAN KESELURUHAN
# ------------------------------------------------------------

print("\n[4] Menghitung korelasi Spearman...")

def correlation_table(data, variables, targets, analysis_type):

    records = []

    for weather in variables:
        for target in targets:

            subset = data[
                [weather, target]
            ].dropna()

            if len(subset) < 3:
                continue

            if (
                subset[weather].nunique() < 2
                or subset[target].nunique() < 2
            ):
                rho = np.nan
            else:
                rho = subset[weather].corr(
                    subset[target],
                    method="spearman"
                )

            records.append({
                "ANALYSIS": analysis_type,
                "WEATHER_VARIABLE": weather,
                "WBC_TARGET": target,
                "SAMPLE_SIZE": len(subset),
                "SPEARMAN_RHO": rho,
                "ABSOLUTE_RHO": (
                    abs(rho) if pd.notna(rho) else np.nan
                )
            })

    return pd.DataFrame(records)


overall = correlation_table(
    df,
    weather_vars,
    target_vars,
    "SAME_MONTH"
)

overall.to_csv(
    OUTPUT_CORR,
    index=False,
    encoding="utf-8-sig"
)

# ------------------------------------------------------------
# 5. KORELASI CUACA BULAN SEBELUMNYA
# ------------------------------------------------------------

print("\n[5] Menghitung korelasi time lag 1 bulan...")

lag_data = df.dropna(
    subset=lag_vars
).copy()

lag_result = correlation_table(
    lag_data,
    lag_vars,
    target_vars,
    "LAG_1_MONTH"
)

lag_result.to_csv(
    OUTPUT_LAG,
    index=False,
    encoding="utf-8-sig"
)

# ------------------------------------------------------------
# 6. ANALISIS PER WILAYAH
# ------------------------------------------------------------

print("\n[6] Analisis korelasi setiap wilayah...")

region_records = []

for region, group in df.groupby("REGION_KEY"):

    for weather in weather_vars:
        for target in target_vars:

            subset = group[
                [weather, target]
            ].dropna()

            if len(subset) < 5:
                continue

            if (
                subset[weather].nunique() < 2
                or subset[target].nunique() < 2
            ):
                rho = np.nan
            else:
                rho = subset[weather].corr(
                    subset[target],
                    method="spearman"
                )

            region_records.append({
                "REGION": region,
                "WEATHER_VARIABLE": weather,
                "WBC_TARGET": target,
                "SAMPLE_SIZE": len(subset),
                "SPEARMAN_RHO": rho
            })

region_result = pd.DataFrame(region_records)

region_result.to_csv(
    OUTPUT_REGION,
    index=False,
    encoding="utf-8-sig"
)

# ------------------------------------------------------------
# 7. VALIDASI DAN RINGKASAN
# ------------------------------------------------------------

print("\n[7] Menyusun ringkasan...")

def interpret(rho):

    if pd.isna(rho):
        return "Tidak dapat dihitung"

    value = abs(rho)

    if value < 0.20:
        strength = "Sangat lemah"
    elif value < 0.40:
        strength = "Lemah"
    elif value < 0.60:
        strength = "Sedang"
    elif value < 0.80:
        strength = "Kuat"
    else:
        strength = "Sangat kuat"

    direction = (
        "Positif" if rho > 0 else "Negatif"
    )

    return f"{strength} ({direction})"


for table in [overall, lag_result]:
    table["INTERPRETATION"] = (
        table["SPEARMAN_RHO"].apply(interpret)
    )

overall.to_csv(
    OUTPUT_CORR,
    index=False,
    encoding="utf-8-sig"
)

lag_result.to_csv(
    OUTPUT_LAG,
    index=False,
    encoding="utf-8-sig"
)

# ------------------------------------------------------------
# 8. AUDIT
# ------------------------------------------------------------

audit = [
    "=" * 70,
    "AUDIT ANALISIS CUACA DAN SERANGAN WBC",
    "=" * 70,
    f"Jumlah observasi: {len(df)}",
    f"Jumlah wilayah: {df['REGION_KEY'].nunique()}",
    f"Periode: {df['MONTH'].min()}-{df['MONTH'].max()}",
    "",
    "METODE:",
    "Korelasi Spearman",
    "Analisis cuaca bulan yang sama",
    "Analisis time lag 1 bulan",
    "Analisis per kabupaten/kota",
    "",
    "CATATAN:",
    "Hasil korelasi tidak membuktikan hubungan sebab-akibat.",
    "Time lag menggunakan cuaca bulan sebelumnya.",
    "Data 2026 hanya Januari-Oktober.",
    "Analisis bersifat eksploratif.",
    "",
    "OUTPUT:",
    str(OUTPUT_CORR),
    str(OUTPUT_LAG),
    str(OUTPUT_REGION),
    str(OUTPUT_DATA),
    "",
    "ANALISIS SELESAI",
    "=" * 70
]

OUTPUT_AUDIT.write_text(
    "\n".join(audit),
    encoding="utf-8"
)

# ------------------------------------------------------------
# 9. MENAMPILKAN HASIL
# ------------------------------------------------------------

print("\n" + "=" * 70)
print("HASIL KORELASI CUACA DAN WBC")
print("=" * 70)

print("\nA. CUACA BULAN YANG SAMA")

print(
    overall[
        [
            "WEATHER_VARIABLE",
            "WBC_TARGET",
            "SAMPLE_SIZE",
            "SPEARMAN_RHO",
            "INTERPRETATION"
        ]
    ].to_string(index=False)
)

print("\nB. CUACA BULAN SEBELUMNYA (LAG 1)")

print(
    lag_result[
        [
            "WEATHER_VARIABLE",
            "WBC_TARGET",
            "SAMPLE_SIZE",
            "SPEARMAN_RHO",
            "INTERPRETATION"
        ]
    ].to_string(index=False)
)

print("\nC. ANALISIS PER WILAYAH")

print("Jumlah hasil:", len(region_result))

print("\nFILE OUTPUT:")
print(OUTPUT_CORR)
print(OUTPUT_LAG)
print(OUTPUT_REGION)
print(OUTPUT_DATA)
print(OUTPUT_AUDIT)

print("\nANALISIS KORELASI SELESAI")
print("=" * 70)
