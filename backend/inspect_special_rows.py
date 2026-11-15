
from pathlib import Path
import pandas as pd

BASE_DIR = Path(__file__).resolve().parent.parent
FILE = BASE_DIR / "data" / "wbc_forecast_bbpt_2022_2025.csv"

df = pd.read_csv(FILE)

print("\n===== 1. DATA SELAIN PRAKIRAAN =====")

actual = df[
    df["jenis_data"].str.contains(
        "evaluasi|aktual",
        case=False,
        na=False
    )
]

print(actual.to_string(index=False))

print("\n===== 2. DATA PUBLIKASI 2025 =====")

data_2025 = df[df["tahun_publikasi_sumber"] == 2025]

print(data_2025.to_string(index=False))

print("\n===== 3. DISTRIBUSI TINGKAT DATA =====")

print(df.groupby(
    ["tahun_publikasi_sumber", "tingkat_data"]
).size().to_string())

print("\n===== 4. DISTRIBUSI MUSIM TANAM =====")

print(df.groupby(
    ["tahun_publikasi_sumber", "periode_musim_tanam"]
).size().to_string())

print("\nPEMERIKSAAN SELESAI")
