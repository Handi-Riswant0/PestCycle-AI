
import time
import requests
import pandas as pd

from pathlib import Path
from datetime import datetime

BASE = Path(__file__).resolve().parents[1]
DATA = BASE / "data"

SOURCE = DATA / "nasa_power_2020_2025_grid.csv"
OUTPUT = DATA / "nasa_power_2026_grid.csv"

API = "https://power.larc.nasa.gov/api/temporal/daily/point"

PARAMETERS = [
    "T2M",
    "T2M_MAX",
    "T2M_MIN",
    "RH2M",
    "PRECTOTCORR"
]

START = "20260101"
END = "20261031"

EXPECTED_DAYS = len(
    pd.date_range("2026-01-01", "2026-10-31")
)

print("=" * 65)
print("PESTCYCLE AI - DOWNLOAD NASA POWER 2026")
print("=" * 65)

# 1. Membaca koordinat grid lama
print("\n[1] Membaca koordinat grid...")

old = pd.read_csv(SOURCE)

grid = (
    old[["LAT", "LON"]]
    .drop_duplicates()
    .sort_values(["LAT", "LON"])
    .reset_index(drop=True)
)

if len(grid) != 24:
    raise ValueError("Jumlah titik grid harus 24.")

print("Jumlah titik grid:", len(grid))
print("Target tanggal:", EXPECTED_DAYS)

# 2. Mengunduh data NASA
print("\n[2] Mengunduh data NASA POWER...")

session = requests.Session()
records = []

for index, row in grid.iterrows():

    lat = float(row["LAT"])
    lon = float(row["LON"])

    print(
        f"\nTitik {index + 1}/24 "
        f"| LAT={lat} | LON={lon}"
    )

    params = {
        "parameters": ",".join(PARAMETERS),
        "community": "AG",
        "longitude": lon,
        "latitude": lat,
        "start": START,
        "end": END,
        "format": "JSON"
    }

    success = False

    for attempt in range(1, 4):

        try:
            response = session.get(
                API,
                params=params,
                timeout=120
            )

            response.raise_for_status()
            result = response.json()

            values = result[
                "properties"
            ]["parameter"]

            point_records = []

            for parameter in PARAMETERS:

                if parameter not in values:
                    raise ValueError(
                        f"Parameter tidak ditemukan: {parameter}"
                    )

                for date, value in values[parameter].items():

                    point_records.append({
                        "DATE": pd.to_datetime(
                            date,
                            format="%Y%m%d"
                        ),
                        "LAT": lat,
                        "LON": lon,
                        "PARAMETER": parameter,
                        "VALUE": (
                            None if value == -999
                            else float(value)
                        )
                    })

            point_df = pd.DataFrame(point_records)

            wide = point_df.pivot(
                index=["DATE", "LAT", "LON"],
                columns="PARAMETER",
                values="VALUE"
            ).reset_index()

            wide.columns.name = None

            if len(wide) != EXPECTED_DAYS:
                raise ValueError(
                    f"Jumlah tanggal tidak sesuai: {len(wide)}"
                )

            records.extend(
                wide.to_dict("records")
            )

            print("Berhasil:", len(wide), "hari")
            success = True
            break

        except Exception as error:

            print(
                f"Percobaan {attempt}/3 gagal: {error}"
            )

            if attempt < 3:
                time.sleep(5)

    if not success:
        raise RuntimeError(
            f"Download gagal pada LAT={lat}, LON={lon}. "
            "File final tidak disimpan."
        )

    time.sleep(1)

# 3. Membentuk dataset
print("\n[3] Menyusun dataset...")

df = pd.DataFrame(records)

df = df.sort_values(
    ["DATE", "LAT", "LON"]
).reset_index(drop=True)

df["YEAR"] = df["DATE"].dt.year
df["DOY"] = df["DATE"].dt.dayofyear

columns = [
    "DATE", "LAT", "LON",
    "YEAR", "DOY",
    "T2M", "T2M_MAX", "T2M_MIN",
    "RH2M", "PRECTOTCORR"
]

df = df[columns]

# 4. Validasi
print("\n[4] Validasi dataset...")

if df.duplicated(["DATE", "LAT", "LON"]).any():
    raise ValueError("Ditemukan duplikasi.")

if len(df) != 24 * EXPECTED_DAYS:
    raise ValueError(
        f"Jumlah baris salah: {len(df)}"
    )

if df["DATE"].min() != pd.Timestamp("2026-01-01"):
    raise ValueError("Tanggal awal salah.")

if df["DATE"].max() != pd.Timestamp("2026-10-31"):
    raise ValueError("Tanggal akhir salah.")

missing = df[PARAMETERS].isna().sum()

print("Jumlah baris:", len(df))
print("Jumlah grid:", df[["LAT", "LON"]].drop_duplicates().shape[0])
print("Tanggal awal:", df["DATE"].min())
print("Tanggal akhir:", df["DATE"].max())

print("\nNilai kosong:")
print(missing.to_string())

# 5. Simpan
df.to_csv(
    OUTPUT,
    index=False,
    encoding="utf-8-sig"
)

print("\n" + "=" * 65)
print("DOWNLOAD NASA POWER 2026 BERHASIL")
print("=" * 65)

print("File:", OUTPUT)
print("Ukuran MB:", round(OUTPUT.stat().st_size / 1024 / 1024, 2))
