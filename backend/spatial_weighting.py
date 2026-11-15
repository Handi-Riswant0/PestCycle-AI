
import json
import math
import pandas as pd

from pathlib import Path
from collections import defaultdict
from shapely.geometry import shape, box
from shapely.ops import transform
from geographiclib.geodesic import Geodesic

# ============================================================
# PESTCYCLE AI - SPATIAL WEIGHTING
# NASA POWER x 38 KABUPATEN/KOTA JAWA TIMUR
# ============================================================

BASE = Path(__file__).resolve().parents[1]
DATA = BASE / "data"

GEO_FILE = DATA / "jawa_timur_kabkota_38_repaired.geojson"
NASA_FILE = DATA / "nasa_power_2020_2025_grid.csv"

OUTPUT_WEIGHTS = DATA / "nasa_spatial_weights.csv"
OUTPUT_AUDIT = DATA / "spatial_weighting_audit.txt"

print("=" * 65)
print("PESTCYCLE AI - SPATIAL WEIGHTING")
print("=" * 65)

# ------------------------------------------------------------
# 1. BACA BATAS ADMINISTRASI
# ------------------------------------------------------------

print("\n[1] Membaca GeoJSON...")

with GEO_FILE.open("r", encoding="utf-8-sig") as f:
    geo = json.load(f)

regions = []

for feature in geo["features"]:
    name = str(
        feature["properties"].get("WADMKK", "")
    ).strip()

    if not name:
        continue

    polygon = shape(feature["geometry"])

    if polygon.is_empty or not polygon.is_valid:
        raise ValueError(f"Geometri tidak valid: {name}")

    regions.append((name, polygon))

region_names = [name for name, _ in regions]

if len(regions) != 38 or len(set(region_names)) != 38:
    raise ValueError("GeoJSON harus memiliki 38 wilayah unik.")

print("Wilayah valid:", len(regions))

# ------------------------------------------------------------
# 2. BACA DATA NASA POWER
# ------------------------------------------------------------

print("\n[2] Membaca data NASA POWER...")

weather = pd.read_csv(
    NASA_FILE,
    parse_dates=["DATE"]
)

grid = (
    weather[["LAT", "LON"]]
    .drop_duplicates()
    .sort_values(["LAT", "LON"])
    .reset_index(drop=True)
)

lats = sorted(grid["LAT"].unique())
lons = sorted(grid["LON"].unique())

print("Baris NASA:", len(weather))
print("Titik grid:", len(grid))

# ------------------------------------------------------------
# 3. MEMBENTUK BATAS SEL GRID
# ------------------------------------------------------------

def calculate_edges(values):
    values = sorted(float(x) for x in values)

    if len(values) < 2:
        raise ValueError("Minimal diperlukan dua titik grid.")

    edges = []

    for i in range(len(values) - 1):
        edges.append((values[i] + values[i + 1]) / 2)

    first = values[0] - (values[1] - values[0]) / 2
    last = values[-1] + (values[-1] - values[-2]) / 2

    return values, [first] + edges + [last]


lats, lat_edges = calculate_edges(lats)
lons, lon_edges = calculate_edges(lons)

print("\n[3] Membentuk sel grid...")

# ------------------------------------------------------------
# 4. FUNGSI LUAS GEODESIK
# ------------------------------------------------------------

GEOD = Geodesic.WGS84

def ring_area(coords):
    polygon = GEOD.Polygon()

    for coord in coords:
        lon = float(coord[0])
        lat = float(coord[1])

        polygon.AddPoint(lat, lon)

    _, _, area = polygon.Compute(False, True)

    return abs(area)


def geodesic_area(geometry):
    if geometry.is_empty:
        return 0.0

    geom_type = geometry.geom_type

    if geom_type == "Polygon":
        area = ring_area(geometry.exterior.coords)

        for interior in geometry.interiors:
            area -= ring_area(interior.coords)

        return max(0.0, area)

    if geom_type == "MultiPolygon":
        return sum(
            geodesic_area(part)
            for part in geometry.geoms
        )

    if geom_type == "GeometryCollection":
        return sum(
            geodesic_area(part)
            for part in geometry.geoms
            if part.geom_type in (
                "Polygon",
                "MultiPolygon",
                "GeometryCollection"
            )
        )

    return 0.0


# ------------------------------------------------------------
# 5. HITUNG IRISAN SEL DAN WILAYAH
# ------------------------------------------------------------

print("\n[4] Menghitung luas irisan geodesik...")

results = []

for i, lat in enumerate(lats):
    for j, lon in enumerate(lons):

        cell = box(
            lon_edges[j],
            lat_edges[i],
            lon_edges[j + 1],
            lat_edges[i + 1]
        )

        cell_area = geodesic_area(cell)

        if cell_area <= 0:
            raise ValueError("Luas sel grid tidak valid.")

        for name, polygon in regions:

            intersection = cell.intersection(polygon)

            if intersection.is_empty:
                continue

            intersection_area = geodesic_area(intersection)

            if intersection_area <= 0:
                continue

            results.append({
                "LAT": lat,
                "LON": lon,
                "REGION": name,
                "CELL_AREA_M2": cell_area,
                "INTERSECTION_AREA_M2": intersection_area,
                "INTERSECTION_PERCENT": (
                    intersection_area / cell_area * 100
                )
            })

result_df = pd.DataFrame(results)

if result_df.empty:
    raise ValueError("Tidak ditemukan irisan grid.")

# ------------------------------------------------------------
# 6. HITUNG BOBOT SETIAP WILAYAH
# ------------------------------------------------------------

print("\n[5] Menghitung bobot spasial...")

result_df["REGION_TOTAL_AREA_M2"] = (
    result_df.groupby("REGION")[
        "INTERSECTION_AREA_M2"
    ].transform("sum")
)

result_df["WEIGHT"] = (
    result_df["INTERSECTION_AREA_M2"]
    / result_df["REGION_TOTAL_AREA_M2"]
)

result_df["WEIGHT_PERCENT"] = (
    result_df["WEIGHT"] * 100
)

# ------------------------------------------------------------
# 7. VALIDASI BOBOT
# ------------------------------------------------------------

summary = (
    result_df.groupby("REGION")
    .agg(
        GRID_CELLS=("LAT", "count"),
        TOTAL_WEIGHT=("WEIGHT", "sum"),
        TOTAL_AREA_M2=("INTERSECTION_AREA_M2", "sum")
    )
    .reset_index()
)

summary["TOTAL_WEIGHT_PERCENT"] = (
    summary["TOTAL_WEIGHT"] * 100
)

if len(summary) != 38:
    raise ValueError("Tidak semua wilayah memiliki bobot.")

if not summary["TOTAL_WEIGHT"].apply(
    lambda x: math.isclose(x, 1.0, abs_tol=1e-9)
).all():
    raise ValueError("Validasi total bobot gagal.")

# ------------------------------------------------------------
# 8. SIMPAN HASIL
# ------------------------------------------------------------

result_df.to_csv(
    OUTPUT_WEIGHTS,
    index=False,
    encoding="utf-8-sig"
)

audit_lines = [
    "=" * 65,
    "LAPORAN SPATIAL WEIGHTING PESTCYCLE AI",
    "=" * 65,
    f"Jumlah wilayah: {len(regions)}",
    f"Jumlah titik grid: {len(grid)}",
    f"Jumlah pasangan sel-wilayah: {len(result_df)}",
    f"Wilayah berhasil dihitung: {len(summary)}",
    "",
    "VALIDASI TOTAL BOBOT:",
    ""
]

for _, row in summary.sort_values("REGION").iterrows():
    audit_lines.append(
        f"{row['REGION']}: "
        f"{row['GRID_CELLS']} sel | "
        f"{row['TOTAL_WEIGHT_PERCENT']:.8f}% | "
        f"Luas: {row['TOTAL_AREA_M2']:.2f} m2"
    )

audit_lines.extend([
    "",
    "=" * 65,
    "SPATIAL WEIGHTING SELESAI",
    "=" * 65
])

OUTPUT_AUDIT.write_text(
    "\n".join(audit_lines),
    encoding="utf-8"
)

print("\n[6] HASIL VALIDASI")
print(summary.sort_values("REGION").to_string(index=False))

print("\nJumlah wilayah:", len(summary))
print("Jumlah pasangan sel-wilayah:", len(result_df))
print("Total bobot setiap wilayah: 100%")

print("\nFILE HASIL:")
print(OUTPUT_WEIGHTS)
print(OUTPUT_AUDIT)

print("\nSPATIAL WEIGHTING SELESAI")
