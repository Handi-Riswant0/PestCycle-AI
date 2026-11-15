
import pandas as pd
import re
from pathlib import Path

# ============================================================
# PESTCYCLE AI
# INTEGRASI NASA POWER DAN DATA AKTUAL WBC
# JAWA TIMUR - 2026
# ============================================================

BASE = Path(__file__).resolve().parents[1]
DATA = BASE / "data"

NASA_FILE = DATA / "nasa_power_daily_38_regions_2020_2026.csv"
WBC_FILE = DATA / "wbc_siperdittan_2026_clean.csv"

OUTPUT = DATA / "nasa_wbc_monthly_integrated_2026.csv"
AUDIT = DATA / "nasa_wbc_integration_audit.txt"

print("=" * 70)
print("PESTCYCLE AI - INTEGRASI NASA POWER DAN WBC")
print("=" * 70)

# ------------------------------------------------------------
# 1. MEMBACA DATA
# ------------------------------------------------------------

print("\n[1] Membaca dataset...")

nasa = pd.read_csv(NASA_FILE, parse_dates=["DATE"])
wbc = pd.read_csv(WBC_FILE)

print("Baris NASA:", len(nasa))
print("Baris WBC:", len(wbc))

# ------------------------------------------------------------
# 2. VALIDASI STRUKTUR
# ------------------------------------------------------------

print("\n[2] Memvalidasi struktur data...")

nasa_required = {
    "DATE", "REGION", "T2M",
    "T2M_MAX", "T2M_MIN",
    "RH2M", "PRECTOTCORR"
}

wbc_required = {
    "kabupaten_kota",
    "tahun",
    "bulan_ke",
    "luas_terkena_T",
    "luas_puso_P"
}

if not nasa_required.issubset(nasa.columns):
    raise ValueError(
        f"Kolom NASA kurang: {nasa_required - set(nasa.columns)}"
    )

if not wbc_required.issubset(wbc.columns):
    raise ValueError(
        f"Kolom WBC kurang: {wbc_required - set(wbc.columns)}"
    )

# ------------------------------------------------------------
# 3. NORMALISASI NAMA WILAYAH
# ------------------------------------------------------------

print("\n[3] Menyamakan nama kabupaten/kota...")

def normalize_region(value):
    value = str(value).strip().upper()
    value = re.sub(r"\s+", " ", value)

    value = re.sub(r"^KABUPATEN\s+", "", value)

    return value

nasa["REGION_KEY"] = nasa["REGION"].apply(normalize_region)

wbc["REGION_KEY"] = wbc["kabupaten_kota"].apply(
    normalize_region
)

# ------------------------------------------------------------
# 4. AGREGASI NASA MENJADI DATA BULANAN
# ------------------------------------------------------------

print("\n[4] Mengagregasikan data cuaca bulanan...")

nasa["YEAR"] = nasa["DATE"].dt.year
nasa["MONTH"] = nasa["DATE"].dt.month

# Fokus periode yang memiliki data aktual WBC
nasa_2026 = nasa[nasa["YEAR"] == 2026].copy()

monthly_weather = (
    nasa_2026.groupby(
        ["REGION_KEY", "YEAR", "MONTH"]
    )
    .agg(
        T2M_MEAN=("T2M", "mean"),
        T2M_MAX=("T2M_MAX", "max"),
        T2M_MIN=("T2M_MIN", "min"),
        RH2M_MEAN=("RH2M", "mean"),
        PRECTOTCORR_SUM=("PRECTOTCORR", "sum"),
        WEATHER_DAYS=("DATE", "nunique")
    )
    .reset_index()
)

print("Data cuaca bulanan:", len(monthly_weather))

# ------------------------------------------------------------
# 5. MENYIAPKAN DATA WBC AKTUAL
# ------------------------------------------------------------

print("\n[5] Menyiapkan data aktual WBC...")

wbc["YEAR"] = pd.to_numeric(wbc["tahun"])
wbc["MONTH"] = pd.to_numeric(wbc["bulan_ke"])

wbc["WBC_AFFECTED_HA"] = pd.to_numeric(
    wbc["luas_terkena_T"], errors="coerce"
)

wbc["WBC_PUSO_HA"] = pd.to_numeric(
    wbc["luas_puso_P"], errors="coerce"
)

wbc_actual = wbc[
    wbc["YEAR"] == 2026
].copy()

wbc_actual = wbc_actual[
    [
        "REGION_KEY",
        "YEAR",
        "MONTH",
        "kabupaten_kota",
        "luas_terkena_T",
        "luas_puso_P",
        "WBC_AFFECTED_HA",
        "WBC_PUSO_HA"
    ]
]

if wbc_actual.duplicated(
    ["REGION_KEY", "YEAR", "MONTH"]
).any():
    raise ValueError("Ada duplikasi data WBC per wilayah dan bulan.")

print("Data aktual WBC:", len(wbc_actual))

# ------------------------------------------------------------
# 6. MENGGABUNGKAN NASA DAN WBC
# ------------------------------------------------------------

print("\n[6] Menggabungkan NASA dan WBC...")

integrated = wbc_actual.merge(
    monthly_weather,
    on=["REGION_KEY", "YEAR", "MONTH"],
    how="left",
    validate="one_to_one",
    indicator=True
)

unmatched = integrated[
    integrated["_merge"] != "both"
]

if len(unmatched) > 0:
    print("\nWilayah/bulan tidak cocok:")
    print(
        unmatched[
            ["kabupaten_kota", "YEAR", "MONTH", "_merge"]
        ].to_string(index=False)
    )
    raise ValueError("Integrasi NASA-WBC belum lengkap.")

integrated.drop(columns="_merge", inplace=True)

# ------------------------------------------------------------
# 7. MEMBUAT FITUR WAKTU
# ------------------------------------------------------------

print("\n[7] Membentuk fitur waktu...")

month_names = {
    1: "Januari",
    2: "Februari",
    3: "Maret",
    4: "April",
    5: "Mei",
    6: "Juni",
    7: "Juli",
    8: "Agustus",
    9: "September",
    10: "Oktober",
    11: "November",
    12: "Desember"
}

integrated["MONTH_NAME"] = integrated["MONTH"].map(
    month_names
)

integrated["DATA_TYPE"] = "ACTUAL_OBSERVATION"
integrated["WBC_SOURCE"] = "SiPerDitTan"

# ------------------------------------------------------------
# 8. VALIDASI AKHIR
# ------------------------------------------------------------

print("\n[8] Validasi dataset terintegrasi...")

if len(integrated) != 380:
    raise ValueError(
        f"Target 380 baris, hasil: {len(integrated)}"
    )

if integrated["REGION_KEY"].nunique() != 38:
    raise ValueError("Jumlah wilayah tidak sama dengan 38.")

if integrated["MONTH"].nunique() != 10:
    raise ValueError("Periode bulan tidak lengkap.")

weather_columns = [
    "T2M_MEAN",
    "T2M_MAX",
    "T2M_MIN",
    "RH2M_MEAN",
    "PRECTOTCORR_SUM"
]

if integrated[weather_columns].isna().any().any():
    raise ValueError("Ada nilai cuaca kosong.")

if integrated.duplicated(
    ["REGION_KEY", "YEAR", "MONTH"]
).any():
    raise ValueError("Ada duplikasi hasil integrasi.")

# ------------------------------------------------------------
# 9. SIMPAN DATASET
# ------------------------------------------------------------

print("\n[9] Menyimpan dataset...")

integrated = integrated.sort_values(
    ["REGION_KEY", "YEAR", "MONTH"]
).reset_index(drop=True)

integrated.to_csv(
    OUTPUT,
    index=False,
    encoding="utf-8-sig"
)

# ------------------------------------------------------------
# 10. AUDIT
# ------------------------------------------------------------

audit = [
    "=" * 70,
    "AUDIT INTEGRASI NASA POWER DAN WBC",
    "=" * 70,
    f"Jumlah wilayah: {integrated['REGION_KEY'].nunique()}",
    f"Jumlah bulan: {integrated['MONTH'].nunique()}",
    f"Jumlah baris: {len(integrated)}",
    f"Tahun: {integrated['YEAR'].unique().tolist()}",
    "",
    "SUMBER DATA:",
    "NASA POWER 2026",
    "SiPerDitTan 2026",
    "",
    "JUMLAH DATA KOSONG:"
]

for col in weather_columns + [
    "WBC_AFFECTED_HA",
    "WBC_PUSO_HA"
]:
    audit.append(
        f"{col}: {integrated[col].isna().sum()}"
    )

audit.extend([
    "",
    "STATUS: BERHASIL",
    "=" * 70
])

AUDIT.write_text(
    "\n".join(audit),
    encoding="utf-8"
)

# ------------------------------------------------------------
# 11. HASIL
# ------------------------------------------------------------

print("\n" + "=" * 70)
print("HASIL INTEGRASI NASA DAN WBC")
print("=" * 70)

print("Jumlah wilayah:", integrated["REGION_KEY"].nunique())
print("Jumlah bulan:", integrated["MONTH"].nunique())
print("Jumlah baris:", len(integrated))

print("\nContoh data:")
print(
    integrated.head(10).to_string(index=False)
)

print("\nFILE OUTPUT:")
print(OUTPUT)
print(AUDIT)

print("\nINTEGRASI NASA-WBC BERHASIL")
print("=" * 70)
