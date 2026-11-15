
from pathlib import Path
import pandas as pd

BASE_DIR = Path(__file__).resolve().parent.parent
FILE = BASE_DIR / "data" / "wbc_forecast_bbpt_2022_2025.csv"

df = pd.read_csv(FILE)

print("\n" + "=" * 65)
print("PEMERIKSAAN DATA BBPOPT 2022-2025")
print("=" * 65)

print("\n1. UKURAN DATA")
print("Jumlah baris:", len(df))
print("Jumlah kolom:", len(df.columns))

print("\n2. DISTRIBUSI TAHUN")
print(df["tahun_publikasi_sumber"].value_counts().sort_index())

print("\n3. JENIS DATA")
print(df["jenis_data"].value_counts(dropna=False))

print("\n4. KELENGKAPAN DATA")
print(df.isna().sum())

print("\n5. LUAS PRAKIRAAN SERANGAN")
print(df["luas_prakiraan_serangan_wbc_ha"].describe())

print("\n6. LUAS KEJADIAN AKTUAL")
print(df["luas_kejadian_aktual_wbc_ha"].describe())

print("\n7. JUMLAH KABUPATEN/KOTA")
print(df["kabupaten_kota"].nunique())

print("\n8. DAFTAR WILAYAH")
print(sorted(df["kabupaten_kota"].dropna().unique()))

print("\n9. PERIODE MUSIM TANAM")
print(df["periode_musim_tanam"].value_counts(dropna=False))

print("\n10. CONTOH DATA")
print(df.head(10).to_string(index=False))

print("\nPEMERIKSAAN SELESAI")
