
import json
import pandas as pd
from pathlib import Path

BASE = Path(__file__).resolve().parents[1]
DATA = BASE / "data"

GEO = DATA / "jawa_timur_kabkota_38_repaired.geojson"

FILES = {
    "BBPOPT": DATA / "wbc_forecast_bbpt_2022_2025.csv",
    "SIPERDITTAN": DATA / "wbc_siperdittan_2026.csv"
}

def normalize(value):
    return " ".join(str(value).strip().upper().split())

print("=" * 70)
print("PESTCYCLE AI - AUDIT CAKUPAN WILAYAH WBC")
print("=" * 70)

with open(GEO, encoding="utf-8") as f:
    geo = json.load(f)

regions = {
    normalize(x["properties"]["WADMKK"])
    for x in geo["features"]
}

print("\nJumlah wilayah referensi:", len(regions))

for source, path in FILES.items():

    print("\n" + "=" * 70)
    print("SUMBER:", source)
    print("=" * 70)

    df = pd.read_csv(path, encoding="utf-8-sig")

    df["REGION_NORMALIZED"] = (
        df["kabupaten_kota"].map(normalize)
    )

    found = set(df["REGION_NORMALIZED"].dropna())

    matched = found & regions
    unknown = found - regions
    missing = regions - found

    print("\nJumlah baris:", len(df))
    print("Jumlah wilayah ditemukan:", len(found))
    print("Wilayah cocok:", len(matched))
    print("Wilayah tidak dikenal:", len(unknown))
    print("Wilayah belum tersedia:", len(missing))

    print("\nWILAYAH TIDAK DIKENAL:")
    for name in sorted(unknown):
        print("-", name)

    print("\nWILAYAH BELUM TERSEDIA:")
    for name in sorted(missing):
        print("-", name)

    print("\nJUMLAH DATA PER WILAYAH:")
    print(
        df.groupby("REGION_NORMALIZED")
        .size()
        .sort_index()
        .to_string()
    )

    if source == "BBPOPT":
        print("\nPERIODE MUSIM TANAM:")
        print(df["periode_musim_tanam"].value_counts().to_string())

        print("\nJENIS DATA:")
        print(df["jenis_data"].value_counts().to_string())

        print("\nTINGKAT DATA:")
        print(df["tingkat_data"].value_counts().to_string())

    else:
        print("\nJUMLAH DATA PER BULAN:")
        print(df["bulan_ke"].value_counts().sort_index().to_string())

print("\n" + "=" * 70)
print("AUDIT CAKUPAN WBC SELESAI")
print("=" * 70)
