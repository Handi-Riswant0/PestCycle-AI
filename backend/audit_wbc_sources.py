
import pandas as pd
from pathlib import Path

BASE = Path(__file__).resolve().parents[1]
DATA = BASE / "data"

FILES = [
    "wbc_forecast_bbpt_2022_2025.csv",
    "wbc_siperdittan_2026.csv"
]

print("=" * 70)
print("PESTCYCLE AI - AUDIT SUMBER DATA WBC")
print("=" * 70)

for filename in FILES:

    path = DATA / filename

    print("\n" + "=" * 70)
    print("FILE:", filename)
    print("=" * 70)

    if not path.exists():
        print("FILE TIDAK DITEMUKAN")
        continue

    df = pd.read_csv(
        path,
        encoding="utf-8-sig"
    )

    print("\n[1] STRUKTUR DATA")
    print("Jumlah baris:", len(df))
    print("Jumlah kolom:", len(df.columns))

    print("\n[2] NAMA KOLOM")
    for col in df.columns:
        print("-", col)

    print("\n[3] TIPE DATA")
    print(df.dtypes.to_string())

    print("\n[4] CONTOH 10 BARIS")
    print(df.head(10).to_string(index=False))

    print("\n[5] JUMLAH DATA KOSONG")
    print(df.isna().sum().to_string())

    print("\n[6] CONTOH DATA UNIK")

    for col in df.columns:
        if df[col].dtype == "object":
            print(f"\n{col}:")
            print(df[col].dropna().unique()[:15])

    print("\n[7] DUPLIKASI BARIS")
    print(df.duplicated().sum())

print("\n" + "=" * 70)
print("AUDIT SUMBER WBC SELESAI")
print("=" * 70)

