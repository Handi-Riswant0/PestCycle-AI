
import pandas as pd
from pathlib import Path

BASE = Path(__file__).resolve().parents[1]
DATA = BASE / "data"

SIPER = DATA / "wbc_siperdittan_2026_clean.csv"
FORECAST = DATA / "wbc_bbopt_forecast_clean.csv"

print("=" * 70)
print("PESTCYCLE AI - ANALISIS DISTRIBUSI DATA WBC")
print("=" * 70)

# =========================================================
# 1. ANALISIS SIPERDITTAN
# =========================================================

print("\n[1] MEMBACA SIPERDITTAN 2026")

df = pd.read_csv(SIPER)

print("Jumlah data:", len(df))
print("Jumlah wilayah:", df["REGION"].nunique())

for col in ["luas_terkena_T", "luas_puso_P"]:
    df[col] = pd.to_numeric(df[col], errors="coerce")

print("\n[2] STATISTIK LUAS SERANGAN")

print(df[["luas_terkena_T", "luas_puso_P"]].describe())

for col in ["luas_terkena_T", "luas_puso_P"]:

    print("\nVariabel:", col)

    print("Nilai nol:", (df[col] == 0).sum())
    print("Nilai positif:", (df[col] > 0).sum())
    print("Nilai kosong:", df[col].isna().sum())
    print("Nilai maksimum:", df[col].max())

# =========================================================
# 2. TOTAL SERANGAN PER WILAYAH
# =========================================================

print("\n[3] TOTAL LUAS TERKENA PER WILAYAH")

region_summary = (
    df.groupby("REGION")
    .agg(
        TOTAL_TERKENA=("luas_terkena_T", "sum"),
        TOTAL_PUSO=("luas_puso_P", "sum"),
        BULAN_AKTIF=("luas_terkena_T",
                     lambda x: (x > 0).sum())
    )
    .reset_index()
    .sort_values("TOTAL_TERKENA", ascending=False)
)

print(region_summary.to_string(index=False))

# =========================================================
# 3. TOTAL SERANGAN PER BULAN
# =========================================================

print("\n[4] TOTAL LUAS TERKENA PER BULAN")

monthly = (
    df.groupby(["tahun", "bulan_ke", "bulan"])
    .agg(
        TOTAL_TERKENA=("luas_terkena_T", "sum"),
        TOTAL_PUSO=("luas_puso_P", "sum"),
        WILAYAH_TERKENA=("luas_terkena_T",
                         lambda x: (x > 0).sum())
    )
    .reset_index()
    .sort_values(["tahun", "bulan_ke"])
)

print(monthly.to_string(index=False))

# =========================================================
# 4. ANALISIS PRAKIRAAN BBPOPT
# =========================================================

print("\n[5] ANALISIS DATA PRAKIRAAN BBPOPT")

forecast = pd.read_csv(FORECAST)

print("Jumlah data:", len(forecast))
print("Kolom tersedia:")
print(forecast.columns.tolist())

print("\nJumlah kategori:")
for col in forecast.select_dtypes(
    include=["object"]
).columns:

    print("\n", col)
    print(forecast[col].value_counts().to_string())

print("\nStatistik kolom numerik:")
print(
    forecast.select_dtypes(
        include="number"
    ).describe().to_string()
)

# =========================================================
# 5. SIMPAN HASIL
# =========================================================

region_summary.to_csv(
    DATA / "wbc_2026_region_summary.csv",
    index=False,
    encoding="utf-8-sig"
)

monthly.to_csv(
    DATA / "wbc_2026_monthly_summary.csv",
    index=False,
    encoding="utf-8-sig"
)

print("\n" + "=" * 70)
print("ANALISIS DISTRIBUSI WBC SELESAI")
print("=" * 70)

print("Output:")
print(DATA / "wbc_2026_region_summary.csv")
print(DATA / "wbc_2026_monthly_summary.csv")
