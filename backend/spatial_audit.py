import json
import pandas as pd
from pathlib import Path
from shapely.geometry import shape, Point
from collections import Counter

BASE = Path(__file__).resolve().parents[1]
DATA = BASE / "data"

GEO_FILE = DATA / "jawa_timur_kabkota_38_repaired.geojson"
NASA_FILE = DATA / "nasa_power_2020_2025_grid.csv"

OUTPUT_MAPPING = DATA / "nasa_grid_region_mapping.csv"
OUTPUT_AUDIT = DATA / "spatial_audit_report.txt"

print("=" * 65)
print("PESTCYCLE AI - AUDIT INTEGRASI SPASIAL")
print("=" * 65)

# 1. Membaca GeoJSON
print("\n[1] Membaca batas administrasi BIG...")

with GEO_FILE.open("r", encoding="utf-8-sig") as f:
    geo = json.load(f)

regions = []

for feature in geo["features"]:
    properties = feature.get("properties") or {}
    name = str(properties.get("WADMKK") or "").strip()
    geometry = feature.get("geometry")

    if not name:
        continue

    if not geometry:
        raise ValueError(f"Geometri kosong: {name}")

    polygon = shape(geometry)

    if polygon.is_empty:
        raise ValueError(f"Geometri kosong: {name}")

    regions.append({
        "name": name,
        "geometry": polygon,
        "valid": polygon.is_valid
    })

region_names = [r["name"] for r in regions]

if len(regions) != 38 or len(set(region_names)) != 38:
    raise ValueError("GeoJSON tidak memiliki tepat 38 wilayah unik.")

print("Wilayah terbaca:", len(regions))
print("Geometri tidak valid:", sum(not r["valid"] for r in regions))

if any(not r["valid"] for r in regions):
    raise ValueError(
        "Ada geometri tidak valid. Periksa geometri sebelum analisis."
    )

# 2. Membaca NASA POWER
print("\n[2] Membaca titik grid NASA POWER...")

weather = pd.read_csv(NASA_FILE)

required = {"LAT", "LON", "DATE", "T2M", "RH2M", "PRECTOTCORR"}

missing_columns = required - set(weather.columns)

if missing_columns:
    raise ValueError(f"Kolom NASA tidak tersedia: {missing_columns}")

grid = (
    weather[["LAT", "LON"]]
    .drop_duplicates()
    .sort_values(["LAT", "LON"])
    .reset_index(drop=True)
)

print("Jumlah baris NASA:", len(weather))
print("Jumlah titik grid:", len(grid))

# 3. Menguji titik terhadap poligon
print("\n[3] Melakukan pengujian point-in-polygon...")

mapping = []
region_counter = Counter()

for _, row in grid.iterrows():
    lat = float(row["LAT"])
    lon = float(row["LON"])

    point = Point(lon, lat)

    matched = [
        r["name"]
        for r in regions
        if r["geometry"].covers(point)
    ]

    for name in matched:
        region_counter[name] += 1

    mapping.append({
        "LAT": lat,
        "LON": lon,
        "MATCH_COUNT": len(matched),
        "REGIONS": "; ".join(matched),
        "STATUS": (
            "MATCHED" if len(matched) == 1
            else "MULTIPLE_MATCHES" if len(matched) > 1
            else "UNMATCHED"
        )
    })

mapping_df = pd.DataFrame(mapping)
mapping_df.to_csv(OUTPUT_MAPPING, index=False, encoding="utf-8-sig")

# 4. Ringkasan wilayah
covered = [
    name for name in region_names
    if region_counter[name] > 0
]

uncovered = [
    name for name in region_names
    if region_counter[name] == 0
]

unmatched = mapping_df[
    mapping_df["STATUS"] == "UNMATCHED"
]

multiple = mapping_df[
    mapping_df["STATUS"] == "MULTIPLE_MATCHES"
]

# 5. Laporan
lines = [
    "=" * 65,
    "LAPORAN AUDIT SPASIAL PESTCYCLE AI",
    "=" * 65,
    f"Jumlah baris NASA: {len(weather)}",
    f"Jumlah titik grid: {len(grid)}",
    f"Jumlah poligon: {len(regions)}",
    f"Titik terpetakan: {len(mapping_df) - len(unmatched)}",
    f"Titik tidak terpetakan: {len(unmatched)}",
    f"Titik dengan beberapa wilayah: {len(multiple)}",
    f"Wilayah terwakili: {len(covered)}",
    f"Wilayah belum terwakili: {len(uncovered)}",
    "",
    "JUMLAH TITIK GRID PER WILAYAH:"
]

for name in sorted(region_names):
    lines.append(f"{name}: {region_counter[name]}")

lines.extend(["", "WILAYAH BELUM TERWAKILI:"])

lines.extend(
    [f"- {name}" for name in sorted(uncovered)]
    if uncovered else ["Tidak ada."]
)

lines.extend(["", "TITIK GRID TIDAK TERPETAKAN:"])

for _, row in unmatched.iterrows():
    lines.append(f"LAT={row['LAT']}, LON={row['LON']}")

lines.extend(["", "=" * 65])

report = "\n".join(lines)

OUTPUT_AUDIT.write_text(report, encoding="utf-8")

print("\n[4] HASIL AUDIT")
print(report)

print("\nFile hasil:")
print(OUTPUT_MAPPING)
print(OUTPUT_AUDIT)

print("\nAUDIT SPASIAL SELESAI")
