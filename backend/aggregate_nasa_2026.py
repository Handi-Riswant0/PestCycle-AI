
import pandas as pd
from pathlib import Path

BASE = Path(__file__).resolve().parents[1]
DATA = BASE / "data"

NASA_FILE = DATA / "nasa_power_2026_grid.csv"
WEIGHT_FILE = DATA / "nasa_spatial_weights.csv"

OUTPUT = DATA / "nasa_power_daily_38_regions_2026.csv"
AUDIT = DATA / "nasa_2026_aggregation_audit.txt"

VARIABLES = [
    "T2M",
    "T2M_MAX",
    "T2M_MIN",
    "RH2M",
    "PRECTOTCORR"
]

print("=" * 65)
print("PESTCYCLE AI - AGREGASI NASA POWER 2026")
print("=" * 65)

# 1. Membaca data
print("\n[1] Membaca data NASA POWER...")

weather = pd.read_csv(NASA_FILE, parse_dates=["DATE"])
weights = pd.read_csv(WEIGHT_FILE)

# 2. Validasi struktur
print("\n[2] Validasi struktur...")

required_weather = {
    "DATE", "LAT", "LON", *VARIABLES
}

required_weights = {
    "LAT", "LON", "REGION", "WEIGHT"
}

if not required_weather.issubset(weather.columns):
    raise ValueError("Kolom NASA tidak lengkap.")

if not required_weights.issubset(weights.columns):
    raise ValueError("Kolom bobot tidak lengkap.")

if weather.duplicated(["DATE", "LAT", "LON"]).any():
    raise ValueError("Data NASA memiliki duplikasi.")

# 3. Validasi bobot
print("\n[3] Validasi bobot spasial...")

weight_sum = weights.groupby("REGION")["WEIGHT"].sum()

if len(weight_sum) != 38:
    raise ValueError("Jumlah wilayah bobot bukan 38.")

if not weight_sum.apply(
    lambda x: abs(x - 1.0) < 1e-8
).all():
    raise ValueError("Total bobot tidak sama dengan 100%.")

# 4. Menggabungkan data
print("\n[4] Menggabungkan data dengan bobot...")

merged = weather.merge(
    weights[["LAT", "LON", "REGION", "WEIGHT"]],
    on=["LAT", "LON"],
    how="inner",
    validate="many_to_many"
)

if len(merged) == 0:
    raise ValueError("Penggabungan menghasilkan data kosong.")

print("Jumlah baris hasil penggabungan:", len(merged))

# 5. Menghitung rata-rata tertimbang
print("\n[5] Menghitung rata-rata tertimbang...")

for variable in VARIABLES:
    merged[f"{variable}_WEIGHTED"] = (
        merged[variable] * merged["WEIGHT"]
    )

aggregated = (
    merged.groupby(["DATE", "REGION"])
    [[f"{v}_WEIGHTED" for v in VARIABLES]]
    .sum()
    .reset_index()
)

aggregated = aggregated.rename(
    columns={
        f"{v}_WEIGHTED": v
        for v in VARIABLES
    }
)

aggregated["YEAR"] = aggregated["DATE"].dt.year
aggregated["DOY"] = aggregated["DATE"].dt.dayofyear

aggregated = aggregated[
    ["DATE", "REGION", "YEAR", "DOY"] + VARIABLES
]

# 6. Validasi hasil
print("\n[6] Validasi hasil agregasi...")

expected_rows = 304 * 38

if len(aggregated) != expected_rows:
    raise ValueError(
        f"Jumlah baris tidak sesuai: {len(aggregated)}"
    )

if aggregated.duplicated(["DATE", "REGION"]).any():
    raise ValueError("Ada duplikasi tanggal dan wilayah.")

if aggregated[VARIABLES].isna().any().any():
    raise ValueError("Ada nilai kosong.")

if aggregated["REGION"].nunique() != 38:
    raise ValueError("Wilayah tidak lengkap.")

if aggregated["DATE"].nunique() != 304:
    raise ValueError("Tanggal tidak lengkap.")

# 7. Simpan hasil
print("\n[7] Menyimpan dataset...")

aggregated.to_csv(
    OUTPUT,
    index=False,
    encoding="utf-8-sig"
)

# 8. Laporan
lines = [
    "=" * 65,
    "AUDIT AGREGASI NASA POWER 2026",
    "=" * 65,
    f"Jumlah wilayah: {aggregated['REGION'].nunique()}",
    f"Jumlah hari: {aggregated['DATE'].nunique()}",
    f"Jumlah baris: {len(aggregated)}",
    f"Tanggal awal: {aggregated['DATE'].min()}",
    f"Tanggal akhir: {aggregated['DATE'].max()}",
    f"Jumlah variabel: {len(VARIABLES)}",
    "",
    "PEMERIKSAAN DATA KOSONG:"
]

for variable in VARIABLES:
    lines.append(
        f"{variable}: {aggregated[variable].isna().sum()}"
    )

lines.extend([
    "",
    "STATUS: BERHASIL",
    "=" * 65
])

AUDIT.write_text("\n".join(lines), encoding="utf-8")

print("\n[8] HASIL AKHIR")
print("=" * 65)

print("Jumlah wilayah:", aggregated["REGION"].nunique())
print("Jumlah hari:", aggregated["DATE"].nunique())
print("Jumlah baris:", len(aggregated))

print("\nContoh data:")
print(aggregated.head(10).to_string(index=False))

print("\nFILE HASIL:")
print(OUTPUT)
print(AUDIT)

print("\nAGREGASI NASA POWER 2026 BERHASIL")
print("=" * 65)

