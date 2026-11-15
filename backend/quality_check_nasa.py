
import pandas as pd
import numpy as np

from pathlib import Path

BASE = Path(__file__).resolve().parents[1]
DATA = BASE / "data"

INPUT = DATA / "nasa_power_daily_38_regions.csv"
OUTPUT = DATA / "nasa_quality_audit.txt"

VARIABLES = [
    "T2M",
    "T2M_MAX",
    "T2M_MIN",
    "RH2M",
    "PRECTOTCORR"
]

print("=" * 65)
print("PESTCYCLE AI - QUALITY CHECK NASA POWER")
print("=" * 65)

df = pd.read_csv(INPUT, parse_dates=["DATE"])

print("\n[1] STRUKTUR DATA")
print("Jumlah baris:", len(df))
print("Jumlah kolom:", len(df.columns))
print("Jumlah wilayah:", df["REGION"].nunique())
print("Jumlah tanggal:", df["DATE"].nunique())

print("\n[2] PEMERIKSAAN DUPLIKASI")

duplicates = df.duplicated(["DATE", "REGION"]).sum()

print("Duplikasi:", duplicates)

print("\n[3] PEMERIKSAAN DATA KOSONG")

missing = df[VARIABLES].isna().sum()

print(missing.to_string())

print("\nTotal nilai kosong:", missing.sum())

print("\n[4] PEMERIKSAAN RENTANG NILAI")

ranges = {
    "T2M": (-10, 50),
    "T2M_MAX": (-10, 55),
    "T2M_MIN": (-10, 50),
    "RH2M": (0, 100),
    "PRECTOTCORR": (0, 1000)
}

range_results = []

for variable, (lower, upper) in ranges.items():

    invalid = df[
        (df[variable] < lower) |
        (df[variable] > upper)
    ]

    range_results.append({
        "VARIABLE": variable,
        "MIN": df[variable].min(),
        "MAX": df[variable].max(),
        "INVALID": len(invalid)
    })

range_df = pd.DataFrame(range_results)

print(range_df.to_string(index=False))

print("\n[5] KONSISTENSI SUHU")

invalid_temperature = df[
    (df["T2M_MIN"] > df["T2M_MAX"]) |
    (df["T2M"] < df["T2M_MIN"]) |
    (df["T2M"] > df["T2M_MAX"])
]

print("Ketidaksesuaian suhu:", len(invalid_temperature))

print("\n[6] KELENGKAPAN DATA PER WILAYAH")

region_summary = (
    df.groupby("REGION")
    .agg(
        TOTAL_DAYS=("DATE", "count"),
        FIRST_DATE=("DATE", "min"),
        LAST_DATE=("DATE", "max")
    )
    .reset_index()
)

print(region_summary.to_string(index=False))

# ------------------------------------------------------------
# LAPORAN
# ------------------------------------------------------------

report = [
    "=" * 65,
    "LAPORAN QUALITY CHECK NASA POWER",
    "=" * 65,
    f"Total baris: {len(df)}",
    f"Total wilayah: {df['REGION'].nunique()}",
    f"Total tanggal: {df['DATE'].nunique()}",
    f"Duplikasi: {duplicates}",
    f"Nilai kosong: {missing.sum()}",
    f"Ketidaksesuaian suhu: {len(invalid_temperature)}",
    "",
    "RENTANG VARIABEL:"
]

for _, row in range_df.iterrows():
    report.append(
        f"{row['VARIABLE']}: "
        f"Min={row['MIN']:.4f}, "
        f"Max={row['MAX']:.4f}, "
        f"Invalid={row['INVALID']}"
    )

report.extend([
    "",
    "KELENGKAPAN WILAYAH:"
])

for _, row in region_summary.iterrows():
    report.append(
        f"{row['REGION']}: {row['TOTAL_DAYS']} hari"
    )

report.extend([
    "",
    "=" * 65,
    "QUALITY CHECK SELESAI",
    "=" * 65
])

OUTPUT.write_text(
    "\n".join(report),
    encoding="utf-8"
)

print("\nFILE AUDIT:")
print(OUTPUT)

print("\nQUALITY CHECK SELESAI")
print("=" * 65)
