import json
import pandas as pd
from pathlib import Path
from shapely.geometry import shape, box

BASE = Path(__file__).resolve().parents[1]
DATA = BASE / "data"

GEO_FILE = DATA / "jawa_timur_kabkota_38_repaired.geojson"
NASA_FILE = DATA / "nasa_power_2020_2025_grid.csv"

OUTPUT = DATA / "nasa_grid_cell_intersections.csv"

print("=" * 65)
print("PESTCYCLE AI - AUDIT INTERSEKSI SEL GRID")
print("=" * 65)

# Membaca batas wilayah
with GEO_FILE.open("r", encoding="utf-8-sig") as f:
    geo = json.load(f)

regions = []

for feature in geo["features"]:
    name = str(
        feature["properties"].get("WADMKK", "")
    ).strip()

    polygon = shape(feature["geometry"])

    if not polygon.is_valid:
        raise ValueError(f"Geometri tidak valid: {name}")

    regions.append((name, polygon))

# Membaca titik NASA POWER
weather = pd.read_csv(NASA_FILE)

grid = (
    weather[["LAT", "LON"]]
    .drop_duplicates()
    .sort_values(["LAT", "LON"])
    .reset_index(drop=True)
)

def calculate_edges(values):
    values = sorted(set(float(x) for x in values))

    if len(values) < 2:
        raise ValueError("Grid membutuhkan minimal dua koordinat.")

    edges = []

    edges.append(
        values[0] - (values[1] - values[0]) / 2
    )

    for i in range(len(values) - 1):
        edges.append((values[i] + values[i + 1]) / 2)

    edges.append(
        values[-1] + (values[-1] - values[-2]) / 2
    )

    return values, edges

lats, lat_edges = calculate_edges(grid["LAT"])
lons, lon_edges = calculate_edges(grid["LON"])

print("\nJumlah titik grid:", len(grid))
print("Jumlah wilayah:", len(regions))

print("\nResolusi grid:")
print("Jarak latitude:", sorted(set(round(lats[i+1]-lats[i], 5) for i in range(len(lats)-1))))
print(
    "Jarak longitude:",
    sorted(set(
        round(lons[i+1] - lons[i], 5)
        for i in range(len(lons)-1)
    ))
)

results = []

# Membentuk sel grid berdasarkan titik pusat
for i, lat in enumerate(lats):
    for j, lon in enumerate(lons):

        cell = box(
            lon_edges[j],
            lat_edges[i],
            lon_edges[j+1],
            lat_edges[i+1]
        )

        cell_area = cell.area

        for name, polygon in regions:
            intersection = cell.intersection(polygon)

            if intersection.is_empty or intersection.area <= 0:
                continue

            percentage = (
                intersection.area / cell_area * 100
            )

            results.append({
                "LAT": lat,
                "LON": lon,
                "REGION": name,
                "INTERSECTION_PERCENT": round(percentage, 4),
                "INTERSECTION_AREA_DEG2": round(
                    intersection.area, 8
                )
            })

result_df = pd.DataFrame(results)

if result_df.empty:
    raise ValueError("Tidak ditemukan irisan sel grid dengan wilayah.")

result_df.to_csv(
    OUTPUT,
    index=False,
    encoding="utf-8-sig"
)

# Ringkasan cakupan
summary = (
    result_df.groupby("REGION")
    .agg(
        GRID_CELLS=("LAT", "count"),
        MAX_CELL_INTERSECTION=("INTERSECTION_PERCENT", "max")
    )
    .reset_index()
)

covered = set(summary["REGION"])
all_regions = {name for name, polygon in regions}
uncovered = all_regions - covered

print("\n" + "=" * 65)
print("HASIL AUDIT INTERSEKSI")
print("=" * 65)

print("Jumlah titik pusat grid:", len(grid))
print("Jumlah sel grid beririsan:", result_df[["LAT", "LON"]].drop_duplicates().shape[0])
print("Jumlah pasangan sel-wilayah:", len(result_df))
print("Wilayah yang terjangkau sel grid:", len(covered))
print("Wilayah tanpa irisan sel grid:", len(uncovered))

print("\nJUMLAH SEL GRID PER WILAYAH:")
print(
    summary.sort_values("REGION").to_string(index=False)
)

print("\nWILAYAH TANPA IRISAN:")
for name in sorted(uncovered):
    print("-", name)

print("\nFILE HASIL:")
print(OUTPUT)

print("\nAUDIT INTERSEKSI SELESAI")
print("=" * 65)
