import json
from pathlib import Path
from collections import Counter

from shapely.geometry import shape, mapping, Polygon, MultiPolygon, GeometryCollection
from shapely import make_valid
from shapely.ops import unary_union

BASE = Path(__file__).resolve().parents[1]
DATA = BASE / "data"

SOURCE = DATA / "jawa_timur_kabkota_38.geojson"
TARGET = DATA / "jawa_timur_kabkota_38_repaired.geojson"

def extract_polygons(geom):
    if geom.geom_type in ("Polygon", "MultiPolygon"):
        return [geom]

    if geom.geom_type == "GeometryCollection":
        parts = []
        for item in geom.geoms:
            parts.extend(extract_polygons(item))
        return parts

    return []

print("=" * 60)
print("PESTCYCLE AI - PERBAIKAN GEOMETRI GEOJSON")
print("=" * 60)

with SOURCE.open("r", encoding="utf-8-sig") as f:
    geo = json.load(f)

repaired_features = []
audit = []

for feature in geo["features"]:
    props = feature.get("properties") or {}
    name = str(props.get("WADMKK") or "").strip()

    original = shape(feature["geometry"])
    original_valid = original.is_valid
    original_area = original.area

    if original_valid:
        repaired = original
        status = "TIDAK PERLU PERBAIKAN"
    else:
        fixed = make_valid(original)
        polygons = extract_polygons(fixed)

        if not polygons:
            raise ValueError(
                f"Tidak ditemukan poligon hasil perbaikan: {name}"
            )

        repaired = unary_union(polygons)

        if repaired.is_empty or not repaired.is_valid:
            raise ValueError(
                f"Geometri masih tidak valid: {name}"
            )

        status = "DIPERBAIKI"

    if repaired.geom_type not in ("Polygon", "MultiPolygon"):
        raise ValueError(
            f"Tipe geometri tidak sesuai: {name} - {repaired.geom_type}"
        )

    if not repaired.is_valid:
        raise ValueError(f"Validasi akhir gagal: {name}")

    area_change = (
        (repaired.area - original_area) / original_area * 100
        if original_area else 0
    )

    new_feature = {
        "type": "Feature",
        "properties": props,
        "geometry": mapping(repaired)
    }

    if "id" in feature:
        new_feature["id"] = feature["id"]

    repaired_features.append(new_feature)

    audit.append({
        "wilayah": name,
        "status": status,
        "tipe_awal": original.geom_type,
        "tipe_akhir": repaired.geom_type,
        "valid_awal": original_valid,
        "valid_akhir": repaired.is_valid,
        "perubahan_luas_persen": round(area_change, 6)
    })

if len(repaired_features) != 38:
    raise ValueError("Jumlah fitur berubah. File tidak disimpan.")

if len({x["properties"]["WADMKK"] for x in repaired_features}) != 38:
    raise ValueError("Ada nama wilayah ganda.")

result = {
    "type": "FeatureCollection",
    "name": "Kabupaten_Kota_Jawa_Timur_Repaired",
    "features": repaired_features
}

with TARGET.open("w", encoding="utf-8") as f:
    json.dump(result, f, ensure_ascii=False)

print("\nHASIL PERBAIKAN:")

for item in audit:
    print(
        f"{item['wilayah']}: {item['status']} | "
        f"{item['tipe_akhir']} | "
        f"Perubahan luas: {item['perubahan_luas_persen']}%"
    )

print("\nRINGKASAN:")
print("Jumlah wilayah:", len(repaired_features))
print("Geometri valid:", sum(x["geometry"] is not None for x in repaired_features))
print("Semua valid:", all(shape(x["geometry"]).is_valid for x in repaired_features))
print("Tipe geometri:", dict(Counter(
    x["geometry"]["type"] for x in repaired_features
)))
print("File baru:", TARGET)
print("Ukuran MB:", round(TARGET.stat().st_size / 1024 / 1024, 2))
print("\nPERBAIKAN SELESAI")
