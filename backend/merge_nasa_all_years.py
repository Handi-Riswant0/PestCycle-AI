
import pandas as pd
from pathlib import Path

BASE = Path(__file__).resolve().parents[1]
DATA = BASE / "data"

FILE_OLD = DATA / "nasa_power_daily_38_regions.csv"
FILE_2026 = DATA / "nasa_power_daily_38_regions_2026.csv"

OUTPUT = DATA / "nasa_power_daily_38_regions_2020_2026.csv"
AUDIT = DATA / "nasa_complete_aggregation_audit.txt"

VARIABLES = [
    "T2M",
    "T2M_MAX",
    "T2M_MIN",
    "RH2M",
    "PRECTOTCORR"
]

print("=" * 65)
print("PESTCYCLE AI - MERGE NASA POWER 2020-2026")
print("=" * 65)

# 1. Membaca dataset
print("\n[1] Membaca dataset NASA POWER...")

old = pd.read_csv(FILE_OLD, parse_dates=["DATE"])
new = pd.read_csv(FILE_2026, parse_dates=["DATE"])

# 2. Menyamakan struktur
print("\n[2] Menyamakan struktur kolom...")

required = ["DATE", "REGION"] + VARIABLES

for label, df in [("2020-2025", old), ("2026", new)]:
    missing = set(required) - set(df.columns)
    if missing:
        raise ValueError(
            f"Kolom hilang pada {label}: {missing}"
        )

old = old[required].copy()
new = new[required].copy()

# 3. Menggabungkan
print("\n[3] Menggabungkan dataset...")

combined = pd.concat(
    [old, new],
    ignore_index=True
)

combined["DATE"] = pd.to_datetime(combined["DATE"])

combined = combined.sort_values(
    ["DATE", "REGION"]
).reset_index(drop=True)

combined["YEAR"] = combined["DATE"].dt.year
combined["DOY"] = combined["DATE"].dt.dayofyear

# 4. Validasi
print("\n[4] Validasi dataset...")

if combined.duplicated(["DATE", "REGION"]).any():
    raise ValueError("Terdapat duplikasi tanggal dan wilayah.")

if combined["REGION"].nunique() != 38:
    raise ValueError("Jumlah wilayah bukan 38.")

expected_dates = pd.date_range(
    "2020-01-01",
    "2026-10-31",
    freq="D"
)

expected_regions = set(combined["REGION"].unique())

expected_rows = len(expected_dates) * 38

if len(combined) != expected_rows:
    raise ValueError(
        f"Jumlah baris salah: {len(combined)} "
        f"seharusnya {expected_rows}"
    )

if set(combined["DATE"].unique()) != set(expected_dates):
    raise ValueError("Ada tanggal yang hilang.")

if combined[VARIABLES].isna().any().any():
    raise ValueError("Ada nilai kosong.")

for variable in VARIABLES:
    if not pd.to_numeric(
        combined[variable], errors="coerce"
    ).notna().all():
        raise ValueError(f"Nilai tidak valid: {variable}")

# 5. Validasi kelengkapan per wilayah
coverage = (
    combined.groupby("REGION")
    .agg(
        TOTAL_DAYS=("DATE", "nunique"),
        FIRST_DATE=("DATE", "min"),
        LAST_DATE=("DATE", "max")
    )
    .reset_index()
)

if not (coverage["TOTAL_DAYS"] == len(expected_dates)).all():
    raise ValueError("Ada wilayah dengan tanggal tidak lengkap.")

# 6. Simpan
print("\n[5] Menyimpan dataset final...")

columns = [
    "DATE", "REGION", "YEAR", "DOY"
] + VARIABLES

combined = combined[columns]

combined.to_csv(
    OUTPUT,
    index=False,
    encoding="utf-8-sig"
)

# 7. Laporan audit
lines = [
    "=" * 65,
    "AUDIT NASA POWER 2020-2026",
    "=" * 65,
    f"Jumlah wilayah: {combined['REGION'].nunique()}",
    f"Jumlah tanggal: {combined['DATE'].nunique()}",
    f"Jumlah baris: {len(combined)}",
    f"Tanggal awal: {combined['DATE'].min()}",
    f"Tanggal akhir: {combined['DATE'].max()}",
    f"Jumlah variabel cuaca: {len(VARIABLES)}",
    f"Duplikasi: {combined.duplicated(['DATE','REGION']).sum()}",
    f"Nilai kosong: {combined[VARIABLES].isna().sum().sum()}",
    "",
    "KELENGKAPAN DATA PER TAHUN:"
]

for year, group in combined.groupby("YEAR"):
    lines.append(
        f"{year}: {group['DATE'].nunique()} hari | "
        f"{len(group)} baris"
    )

lines.extend([
    "",
    "KELENGKAPAN PER WILAYAH:",
    f"Wilayah lengkap: {len(coverage)}",
    "",
    "STATUS: BERHASIL",
    "=" * 65
])

AUDIT.write_text(
    "\n".join(lines),
    encoding="utf-8"
)

print("\n[6] HASIL AKHIR")
print("\nJumlah wilayah:", combined["REGION"].nunique())
print("Jumlah tanggal:", combined["DATE"].nunique())
print("Jumlah baris:", len(combined))
print("Duplikasi:", combined.duplicated(
    ["DATE", "REGION"]
).sum())
print("Nilai kosong:", combined[VARIABLES].isna().sum().sum())

print("\nKelengkapan per tahun:")
print(
    combined.groupby("YEAR")["DATE"]
    .nunique()
    .to_string()
)

print("\nContoh data:")
print(combined.head(10).to_string(index=False))

print("\nFILE OUTPUT:")
print(OUTPUT)
print(AUDIT)

print("\nMERGE NASA POWER BERHASIL")
print("=" * 65)
