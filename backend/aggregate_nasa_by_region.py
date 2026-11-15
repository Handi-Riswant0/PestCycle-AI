
import pandas as pd
import numpy as np

from pathlib import Path

# ============================================================
# PESTCYCLE AI
# AGREGASI NASA POWER KE 38 KABUPATEN/KOTA JAWA TIMUR
# PERIODE JANUARI 2020 - DESEMBER 2025
# ============================================================

BASE = Path(__file__).resolve().parents[1]
DATA = BASE / "data"

NASA_FILE = DATA / "nasa_power_2020_2025_grid.csv"
WEIGHT_FILE = DATA / "nasa_spatial_weights.csv"

OUTPUT_FILE = DATA / "nasa_power_daily_38_regions.csv"
AUDIT_FILE = DATA / "nasa_regional_aggregation_audit.txt"

VARIABLES = [
    "T2M",
    "T2M_MAX",
    "T2M_MIN",
    "RH2M",
    "PRECTOTCORR"
]

print("=" * 65)
print("PESTCYCLE AI - NASA POWER REGIONAL AGGREGATION")
print("=" * 65)

# ------------------------------------------------------------
# 1. MEMBACA DATA
# ------------------------------------------------------------

print("\n[1] Membaca data NASA POWER...")

weather = pd.read_csv(NASA_FILE)

weights = pd.read_csv(WEIGHT_FILE)

print("Baris data NASA:", len(weather))
print("Jumlah titik grid:", weather[["LAT", "LON"]].drop_duplicates().shape[0])

# ------------------------------------------------------------
# 2. VALIDASI KOLOM
# ------------------------------------------------------------

print("\n[2] Validasi struktur data...")

required_weather = {
    "DATE", "LAT", "LON", *VARIABLES
}

required_weights = {
    "LAT", "LON", "REGION", "WEIGHT"
}

if not required_weather.issubset(weather.columns):
    raise ValueError(
        f"Kolom NASA kurang: {required_weather - set(weather.columns)}"
    )

if not required_weights.issubset(weights.columns):
    raise ValueError(
        f"Kolom bobot kurang: {required_weights - set(weights.columns)}"
    )

weather["DATE"] = pd.to_datetime(
    weather["DATE"], errors="raise"
)

weather["LAT"] = weather["LAT"].astype(float)
weather["LON"] = weather["LON"].astype(float)

weights["LAT"] = weights["LAT"].astype(float)
weights["LON"] = weights["LON"].astype(float)

# ------------------------------------------------------------
# 3. VALIDASI BOBOT SPASIAL
# ------------------------------------------------------------

print("\n[3] Memvalidasi bobot spasial...")

weight_summary = (
    weights.groupby("REGION")["WEIGHT"].sum()
)

if len(weight_summary) != 38:
    raise ValueError("Jumlah wilayah bukan 38.")

if not np.allclose(
    weight_summary.values,
    1.0,
    atol=1e-8
):
    raise ValueError("Total bobot wilayah tidak sama dengan 1.")

if (weights["WEIGHT"] < 0).any():
    raise ValueError("Ditemukan bobot negatif.")

print("Jumlah wilayah:", len(weight_summary))
print("Semua bobot wilayah valid.")

# ------------------------------------------------------------
# 4. MENGGABUNGKAN DATA GRID DENGAN BOBOT
# ------------------------------------------------------------

print("\n[4] Menggabungkan data NASA dengan bobot...")

merged = weather.merge(
    weights[["LAT", "LON", "REGION", "WEIGHT"]],
    on=["LAT", "LON"],
    how="inner",
    validate="many_to_many"
)

if merged.empty:
    raise ValueError("Tidak ada data yang cocok dengan bobot.")

print("Jumlah baris hasil penggabungan:", len(merged))

# ------------------------------------------------------------
# 5. MENGHITUNG RATA-RATA TERTIMBANG
# ------------------------------------------------------------

print("\n[5] Menghitung rata-rata tertimbang...")

for variable in VARIABLES:
    merged[f"{variable}_WEIGHTED"] = (
        merged[variable] * merged["WEIGHT"]
    )

weighted_columns = [
    f"{variable}_WEIGHTED"
    for variable in VARIABLES
]

daily = (
    merged.groupby(["DATE", "REGION"])[weighted_columns]
    .sum(min_count=1)
    .reset_index()
)

daily = daily.rename(
    columns={
        f"{variable}_WEIGHTED": variable
        for variable in VARIABLES
    }
)

daily = daily.sort_values(
    ["DATE", "REGION"]
).reset_index(drop=True)

# ------------------------------------------------------------
# 6. VALIDASI KELENGKAPAN DATA
# ------------------------------------------------------------

print("\n[6] Memvalidasi hasil agregasi...")

expected_days = pd.date_range(
    start="2020-01-01",
    end="2025-12-31",
    freq="D"
)

expected_regions = sorted(weights["REGION"].unique())

expected_rows = len(expected_days) * len(expected_regions)

if len(daily) != expected_rows:
    raise ValueError(
        f"Jumlah baris tidak sesuai. "
        f"Target: {expected_rows}, aktual: {len(daily)}"
    )

if daily.duplicated(["DATE", "REGION"]).any():
    raise ValueError("Ditemukan tanggal dan wilayah duplikat.")

if not daily[VARIABLES].notna().all().all():
    raise ValueError("Ditemukan nilai cuaca kosong.")

# ------------------------------------------------------------
# 7. MENYIMPAN DATA
# ------------------------------------------------------------

print("\n[7] Menyimpan dataset regional...")

daily.to_csv(
    OUTPUT_FILE,
    index=False,
    encoding="utf-8-sig"
)

# ------------------------------------------------------------
# 8. MEMBUAT LAPORAN AUDIT
# ------------------------------------------------------------

audit = [
    "=" * 65,
    "AUDIT AGREGASI NASA POWER PESTCYCLE AI",
    "=" * 65,
    f"Periode: {daily['DATE'].min().date()} sampai {daily['DATE'].max().date()}",
    f"Jumlah wilayah: {daily['REGION'].nunique()}",
    f"Jumlah hari: {daily['DATE'].nunique()}",
    f"Jumlah baris: {len(daily)}",
    f"Jumlah variabel: {len(VARIABLES)}",
    "",
    "VARIABEL:",
]

audit.extend(VARIABLES)

audit.extend([
    "",
    "VALIDASI:",
    f"Tanggal unik: {daily['DATE'].nunique()}",
    f"Wilayah unik: {daily['REGION'].nunique()}",
    f"Duplikasi: {daily.duplicated(['DATE', 'REGION']).sum()}",
    f"Nilai kosong: {daily[VARIABLES].isna().sum().sum()}",
    "",
    "JUMLAH DATA PER WILAYAH:"
])

for region, group in daily.groupby("REGION"):
    audit.append(
        f"{region}: {len(group)} hari"
    )

audit.extend([
    "",
    "=" * 65,
    "AGREGASI SELESAI",
    "=" * 65
])

AUDIT_FILE.write_text(
    "\n".join(audit),
    encoding="utf-8"
)

print("\n[8] HASIL AKHIR")
print("=" * 65)

print("Jumlah wilayah:", daily["REGION"].nunique())
print("Jumlah hari:", daily["DATE"].nunique())
print("Jumlah baris:", len(daily))
print("Jumlah variabel:", len(VARIABLES))

print("\nContoh hasil:")
print(daily.head(10).to_string(index=False))

print("\nFILE HASIL:")
print(OUTPUT_FILE)
print(AUDIT_FILE)

print("\nNASA POWER REGIONAL AGGREGATION BERHASIL")
print("=" * 65)
