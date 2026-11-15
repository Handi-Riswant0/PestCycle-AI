
import json
import pandas as pd
from pathlib import Path

BASE = Path(__file__).resolve().parents[1]
DATA = BASE / "data"

GEO = DATA / "jawa_timur_kabkota_38_repaired.geojson"

BBPOPT = DATA / "wbc_forecast_bbpt_2022_2025.csv"
SIPER = DATA / "wbc_siperdittan_2026.csv"

OUT_FORECAST = DATA / "wbc_bbopt_forecast_clean.csv"
OUT_ACTUAL = DATA / "wbc_bbopt_actual_clean.csv"
OUT_PROVINCE = DATA / "wbc_bbopt_province_separate.csv"
OUT_SIPER = DATA / "wbc_siperdittan_2026_clean.csv"
OUT_REPORT = DATA / "wbc_preparation_report.txt"

def normalize(value):
    return " ".join(str(value).strip().upper().split())

print("=" * 65)
print("PESTCYCLE AI - PERSIAPAN DATA WBC")
print("=" * 65)

# 1. Referensi wilayah
with open(GEO, encoding="utf-8-sig") as f:
    geo = json.load(f)

regions = {
    normalize(x["properties"]["WADMKK"])
    for x in geo["features"]
}

if len(regions) != 38:
    raise ValueError("Referensi wilayah bukan 38.")

# 2. Membaca BBPOPT
print("\n[1] Membaca data BBPOPT...")

bb = pd.read_csv(BBPOPT, encoding="utf-8-sig")

bb["REGION"] = bb["kabupaten_kota"].map(normalize)

province_data = bb[
    bb["tingkat_data"].str.strip().str.upper() == "PROVINSI"
].copy()

district_data = bb[
    bb["tingkat_data"].str.strip().str.upper() == "KABUPATEN/KOTA"
].copy()

unknown = set(district_data["REGION"]) - regions

if unknown:
    raise ValueError(f"Wilayah BBPOPT tidak dikenal: {unknown}")

if len(district_data) != 152:
    raise ValueError("Jumlah data kabupaten BBPOPT tidak sesuai.")

forecast = district_data[
    district_data["jenis_data"].str.contains(
        "Prakiraan serangan", case=False, na=False
    )
].copy()

actual = district_data[
    district_data["jenis_data"].str.contains(
        "Evaluasi kejadian aktual", case=False, na=False
    )
].copy()

forecast.to_csv(
    OUT_FORECAST, index=False, encoding="utf-8-sig"
)

actual.to_csv(
    OUT_ACTUAL, index=False, encoding="utf-8-sig"
)

province_data.to_csv(
    OUT_PROVINCE, index=False, encoding="utf-8-sig"
)

print("BBPOPT kabupaten:", len(district_data))
print("Data prakiraan:", len(forecast))
print("Data evaluasi aktual:", len(actual))
print("Data provinsi terpisah:", len(province_data))

# 3. Membaca SiPerDitTan
print("\n[2] Membaca data SiPerDitTan...")

siper = pd.read_csv(SIPER, encoding="utf-8-sig")

siper["REGION"] = siper["kabupaten_kota"].map(normalize)

unknown_siper = set(siper["REGION"]) - regions

if unknown_siper:
    raise ValueError(
        f"Wilayah SiPerDitTan tidak dikenal: {unknown_siper}"
    )

if siper.duplicated(
    ["REGION", "tahun", "bulan_ke"]
).any():
    raise ValueError("Ditemukan duplikasi data bulanan.")

if len(siper) != 380:
    raise ValueError("Jumlah data SiPerDitTan tidak sesuai.")

siper.to_csv(
    OUT_SIPER, index=False, encoding="utf-8-sig"
)

print("Data SiPerDitTan:", len(siper))
print("Wilayah:", siper["REGION"].nunique())
print("Tahun:", sorted(siper["tahun"].unique()))

# 4. Laporan
lines = [
    "=" * 65,
    "LAPORAN PERSIAPAN DATA WBC",
    "=" * 65,
    f"Wilayah referensi: {len(regions)}",
    f"BBPOPT kabupaten: {len(district_data)}",
    f"BBPOPT prakiraan: {len(forecast)}",
    f"BBPOPT evaluasi aktual: {len(actual)}",
    f"BBPOPT tingkat provinsi: {len(province_data)}",
    f"SiPerDitTan: {len(siper)}",
    f"Wilayah SiPerDitTan: {siper['REGION'].nunique()}",
    "",
    "FILE OUTPUT:",
    str(OUT_FORECAST),
    str(OUT_ACTUAL),
    str(OUT_PROVINCE),
    str(OUT_SIPER),
    "",
    "Pemisahan data selesai."
]

OUT_REPORT.write_text(
    "\n".join(lines), encoding="utf-8"
)

print("\n".join(lines))
print("\nPERSIAPAN DATA WBC BERHASIL")
