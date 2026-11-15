import json
from pathlib import Path
from collections import Counter

path = Path("data/jawa_timur_kabkota.geojson")

with path.open("r", encoding="utf-8-sig") as f:
    geo = json.load(f)

features = geo["features"]

print("=" * 55)
print("AUDIT GEOJSON BATAS ADMINISTRASI JAWA TIMUR")
print("=" * 55)

print("Tipe data:", geo.get("type"))
print("Jumlah fitur:", len(features))

names = [
    str(x["properties"].get("WADMKK", "")).strip()
    for x in features
]

print("Jumlah wilayah unik:", len(set(names)))
print("Geometri:", Counter(
    x["geometry"]["type"] if x.get("geometry") else "KOSONG"
    for x in features
))

print("Geometri kosong:", sum(
    1 for x in features if not x.get("geometry")
))

print("\nDAFTAR WILAYAH:")
for name in sorted(set(names)):
    print("-", name)

print("\nUKURAN FILE:", round(path.stat().st_size / 1024 / 1024, 2), "MB")
print("=" * 55)
