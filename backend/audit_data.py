
from pathlib import Path
import pandas as pd

# Lokasi folder proyek
BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"

REPORT_FILE = BASE_DIR / "audit_report.txt"

FILES = [
    "nasa_power_2020_2025_grid.csv",
    "wbc_forecast_bbpt_2022_2025.csv",
    "wbc_siperdittan_2026.csv"
]

report = []

def log(text=""):
    print(text)
    report.append(str(text))

def read_csv_safe(path):
    encodings = ["utf-8", "utf-8-sig", "cp1252", "latin1"]

    for encoding in encodings:
        try:
            return pd.read_csv(path, encoding=encoding, low_memory=False)
        except UnicodeDecodeError:
            continue

    raise ValueError("Encoding CSV tidak dapat dibaca")

log("=" * 75)
log("AUDIT DATA PESTCYCLE AI")
log("=" * 75)
log(f"Folder data: {DATA_DIR}")

if not DATA_DIR.exists():
    raise FileNotFoundError(f"Folder data tidak ditemukan: {DATA_DIR}")

for filename in FILES:
    path = DATA_DIR / filename

    log("\n" + "=" * 75)
    log(f"FILE: {filename}")
    log("=" * 75)

    if not path.exists():
        log("STATUS: FILE TIDAK DITEMUKAN")
        continue

    try:
        df = read_csv_safe(path)

        log(f"Jumlah baris       : {len(df):,}")
        log(f"Jumlah kolom       : {len(df.columns)}")
        log(f"Jumlah duplikat    : {df.duplicated().sum():,}")
        log(f"Ukuran file        : {path.stat().st_size / 1024 / 1024:.2f} MB")

        log("\nDAFTAR KOLOM:")
        for col in df.columns:
            log(f"- {col} ({df[col].dtype})")

        log("\nDATA KOSONG:")
        missing = df.isna().sum()
        for col, count in missing.items():
            if count > 0:
                log(f"- {col}: {count:,} ({count / len(df) * 100:.2f}%)")

        if missing.sum() == 0:
            log("Tidak ditemukan data kosong.")

        log("\nKANDUNGAN DATA UNIK:")
        for col in df.columns:
            if df[col].nunique() <= 45:
                values = df[col].dropna().unique().tolist()
                log(f"- {col}: {values[:45]}")

        # Deteksi kolom tanggal
        date_columns = [
            col for col in df.columns
            if any(word in col.lower()
                   for word in ["date", "tanggal", "time", "tahun"])
        ]

        log("\nPEMERIKSAAN TANGGAL:")
        for col in date_columns:
            parsed = pd.to_datetime(df[col], errors="coerce")
            valid = parsed.dropna()

            if len(valid):
                log(f"- {col}: {valid.min()} sampai {valid.max()}")
            else:
                log(f"- {col}: tidak dapat dikenali sebagai tanggal")

        log("\nCONTOH 5 BARIS DATA:")
        log(df.head(5).to_string(index=False))

    except Exception as e:
        log(f"ERROR MEMBACA FILE: {e}")

log("\n" + "=" * 75)
log("AUDIT SELESAI")
log("=" * 75)

REPORT_FILE.write_text("\n".join(report), encoding="utf-8")

print(f"\nLaporan tersimpan di: {REPORT_FILE}")
