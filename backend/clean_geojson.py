import json
from pathlib import Path
from collections import Counter

source = Path("data/jawa_timur_kabkota.geojson")
target = Path("data/jawa_timur_kabkota_38.geojson")

print("Membaca GeoJSON BIG...")

with source.open("r", encoding="utf-8-sig") as f:
    geo = json.load(f)

valid = []

for feature in geo["features"]:
    props = feature.get("properties") or {}
    name = str(props.get("WADMKK") or "").strip()
    geometry = feature.get("geometry")

    if not name:
        continue

    if not geometry or not geometry.get("coordinates"):
        raise ValueError(f"Geometri kosong: {name}")

    feature["properties"]["WADMKK"] = name
    valid.append(feature)

names = [x["properties"]["WADMKK"] for x in valid]

if len(valid) != 38:
    raise ValueError(f"Jumlah fitur tidak sesuai: {len(valid)}")

if len(set(names)) != 38:
    raise ValueError("Ditemukan nama wilayah ganda.")

clean_geo = {
    "type": "FeatureCollection",
    "name": "Kabupaten_Kota_Jawa_Timur",
    "features": valid
}

with target.open("w", encoding="utf-8") as f:
    json.dump(clean_geo, f, ensure_ascii=False)

print("\nPEMBERSIHAN SELESAI")
print("Fitur awal:", len(geo["features"]))
print("Fitur dibersihkan:", len(valid))
print("Nama wilayah unik:", len(set(names)))
print("Geometri:", dict(Counter(
    x["geometry"]["type"] for x in valid
)))
print("File:", target)
print("Ukuran MB:", round(target.stat().st_size / 1024 / 1024, 2))
